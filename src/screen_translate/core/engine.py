"""Translation engine thread skeleton for Screen Translate."""

from __future__ import annotations

import threading
import time
from typing import List, Optional

from PySide6.QtCore import QObject, QRect, Signal

from ..config.schemas import AppConfig
from .cache import TranslationCache
from .ocr_processor import OCRProcessor, OCRResult
from .audio_processor import AudioProcessor, AudioResult
from .whisper_processor import WhisperProcessor
from .screen_capture import ScreenCapturer
from .translator import Translator


class TranslationEngine(QObject, threading.Thread):
    """Thread managing capture → OCR → translation loop."""

    translation_ready = Signal(str)
    engine_error = Signal(str)
    ocr_text_detected = Signal(str)
    translation_requested = Signal(str, str, str)
    translation_received = Signal(str)
    language_detected = Signal(str)
    log_message = Signal(str)

    def __init__(self, config_manager) -> None:  # noqa: ANN001 - will refine type later
        QObject.__init__(self)
        threading.Thread.__init__(self, name="TranslationEngine", daemon=True)
        self._config_manager = config_manager
        self._running = threading.Event()
        self._stop_event = threading.Event()

        self._capturer = ScreenCapturer()
        self._ocr = OCRProcessor()
        self._audio = None
        self._cache = TranslationCache(ttl_seconds=2.0)
        self._translator: Optional[Translator] = None

    def start(self, config: Optional[AppConfig] = None) -> None:  # type: ignore[override]
        if self._running.is_set():
            return
        self._running.set()
        self._stop_event.clear()

        self._active_config = config or self._config_manager.config

        if self._active_config.audio.enabled:
            self.log_message.emit("初始化音频输入模式")
            audio_config = self._active_config.audio

            if audio_config.stt_engine == "whisper":
                self.log_message.emit("使用Whisper语音识别")
                self._audio = WhisperProcessor(
                    sample_rate=audio_config.device.sample_rate,
                    chunk_size=audio_config.device.chunk_size
                )
            else:  # vosk
                self.log_message.emit("使用Vosk语音识别")
                self._audio = AudioProcessor(
                    sample_rate=audio_config.device.sample_rate,
                    chunk_size=audio_config.device.chunk_size
                )

            self._ocr = None
        else:
            self.log_message.emit("初始化OCR模式")
            ocr_languages = self._get_ocr_languages(self._active_config.translation.source_language)
            self._ocr.set_languages(ocr_languages)
            self._ocr.start()
            self._audio = None

        if not self._active_config.audio.enabled:
            self._capturer.start()

        api_config = self._active_config.api
        self._translator = Translator(api_config, logger=lambda msg: self.log_message.emit(f"[翻译器] {msg}"))

        self._interval = self._active_config.translation.interval_ms / 1000.0

        # 设置缓存模式
        if self._active_config.audio.enabled:
            self._cache.set_mode("audio")
            self.log_message.emit("启用音频模式缓存策略")
        else:
            self._cache.set_mode("ocr")
            self.log_message.emit("启用OCR模式缓存策略")

        if not self.is_alive():
            threading.Thread.start(self)

    def _get_ocr_languages(self, source_language: str) -> List[str]:
        """Get OCR language list based on translation source language."""
        if source_language == "ja":
            return ["ja", "en"]
        elif source_language == "ko":
            return ["ko", "en"]
        elif source_language == "en":
            return ["en"]
        else:
            return ["ja", "en"]

    def run(self) -> None:  # noqa: D401 - threading override
        self.log_message.emit("翻译引擎已启动")

        if self._active_config.audio.enabled:
            self._run_audio_mode()
        else:
            self._run_ocr_mode()

        self.log_message.emit("翻译引擎已停止")

    def _run_ocr_mode(self) -> None:
        """Run OCR-based translation loop."""
        while self._running.is_set() and not self._stop_event.is_set():
            try:
                rect = self._active_config.source_region
                self.log_message.emit(f"正在捕获屏幕区域: ({rect.x}, {rect.y}) {rect.width}x{rect.height}")
                capture = self._capturer.capture(
                    QRect(rect.x, rect.y, rect.width, rect.height)
                )
                if capture is None:
                    self.log_message.emit("捕获失败，区域可能不可见")
                    self._sleep_interval()
                    continue

                self.log_message.emit("正在执行OCR识别...")
                ocr_results = self._ocr.read_text(capture.image)

                self.log_message.emit(f"OCR结果数量: {len(ocr_results)}")
                for i, result in enumerate(ocr_results):
                    self.log_message.emit(f"  结果{i}: '{result.text}' (置信度: {result.confidence:.3f})")

                text = " ".join(r.text for r in ocr_results).strip()
                self.log_message.emit(f"合并后的文本: '{text}' (长度: {len(text)})")

                if ocr_results:
                    self.log_message.emit(f"OCR识别到文本 (置信度: {ocr_results[0].confidence:.2f})")

                if not text:
                    self.log_message.emit("未检测到文本内容")
                    self._sleep_interval()
                    continue

                should_translate = self._cache.should_translate(text)
                self.log_message.emit(f"缓存检查: {'需要翻译' if should_translate else '跳过翻译'}")
                if not should_translate:
                    self.log_message.emit(f"文本未变化 ({text[:30]}{'...' if len(text) > 30 else ''})，跳过翻译，避免重复API调用")
                    self._sleep_interval()
                    continue

                self.log_message.emit(f"原始文本: {text[:100]}{'...' if len(text) > 100 else ''}")
                self.ocr_text_detected.emit(text)

                source_lang = self._active_config.translation.source_language
                target_lang = self._active_config.translation.target_language
                self.log_message.emit(f"翻译方向: {source_lang} → {target_lang}")
                self.language_detected.emit(source_lang)

                if self._translator:
                    self.log_message.emit("正在调用翻译API...")
                    self.translation_requested.emit(text, source_lang, target_lang)

                    translated = self._translator.translate(text)
                    if translated:
                        self.log_message.emit(f"翻译完成: {translated.text[:100]}{'...' if len(translated.text) > 100 else ''}")
                        self.translation_received.emit(translated.text)
                        self.translation_ready.emit(translated.text)
                    else:
                        self.log_message.emit("翻译失败：未收到响应")
                else:
                    self.log_message.emit("警告：翻译器未初始化")
            except Exception as exc:
                error_msg = f"发生错误: {str(exc)}"
                self.log_message.emit(error_msg)
                self.engine_error.emit(error_msg)
            finally:
                self._sleep_interval()

    def _run_audio_mode(self) -> None:
        """Run audio-based translation loop."""
        audio_config = self._active_config.audio
        try:
            if audio_config.stt_engine == "whisper":
                self._audio.start(
                    config=audio_config.whisper,
                    device_config=audio_config.device,
                    device_index=audio_config.device.virtual_input_device
                )
                self.log_message.emit("Whisper音频录制已开始，等待语音输入...")
            else:  # vosk
                self._audio.start(
                    model_path=audio_config.vosk.model_path,
                    device_index=audio_config.device.virtual_input_device
                )
                self.log_message.emit("Vosk音频录制已开始，等待语音输入...")
        except Exception as exc:
            error_msg = f"音频启动失败: {str(exc)}"
            self.log_message.emit(error_msg)
            self.engine_error.emit(error_msg)
            return

        while self._running.is_set() and not self._stop_event.is_set():
            try:
                audio_results = self._audio.read_text()

                if audio_results:
                    result = audio_results[0]
                    self.log_message.emit(f"语音识别结果: '{result.text}' (置信度: {result.confidence:.3f})")

                    text = result.text.strip()
                    if not text:
                        self._sleep_interval()
                        continue

                    should_translate = self._cache.should_translate(text)
                    self.log_message.emit(f"缓存检查: {'需要翻译' if should_translate else '跳过翻译'}")
                    if not should_translate:
                        self.log_message.emit(f"文本未变化 ({text[:30]}{'...' if len(text) > 30 else ''})，跳过翻译")
                        self._sleep_interval()
                        continue

                    self.log_message.emit(f"原始文本: {text[:100]}{'...' if len(text) > 100 else ''}")
                    self.ocr_text_detected.emit(text)

                    source_lang = self._active_config.translation.source_language
                    target_lang = self._active_config.translation.target_language
                    self.log_message.emit(f"翻译方向: {source_lang} → {target_lang}")
                    self.language_detected.emit(source_lang)

                    if self._translator:
                        self.log_message.emit("正在调用翻译API...")
                        self.translation_requested.emit(text, source_lang, target_lang)

                        translated = self._translator.translate(text)
                        if translated:
                            self.log_message.emit(f"翻译完成: {translated.text[:100]}{'...' if len(translated.text) > 100 else ''}")
                            self.translation_received.emit(translated.text)
                            self.translation_ready.emit(translated.text)
                        else:
                            self.log_message.emit("翻译失败：未收到响应")
                    else:
                        self.log_message.emit("警告：翻译器未初始化")
                else:
                    time.sleep(0.1)

            except Exception as exc:
                error_msg = f"发生错误: {str(exc)}"
                self.log_message.emit(error_msg)
                self.engine_error.emit(error_msg)
                time.sleep(1)

    def _sleep_interval(self) -> None:
        time.sleep(self._interval)

    def stop(self) -> None:
        if not self._running.is_set():
            return
        self._stop_event.set()
        self._running.clear()

        if not self._active_config.audio.enabled:
            self._capturer.stop()
            if self._ocr:
                self._ocr.stop()
        else:
            if self._audio:
                self._audio.stop()

        if self.is_alive():
            self.join(timeout=2)

    @property
    def is_running(self) -> bool:
        return self._running.is_set()
