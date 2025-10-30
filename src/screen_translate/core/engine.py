"""Translation engine thread skeleton for Screen Translate."""

from __future__ import annotations

import threading
import time
from typing import List, Optional

from PySide6.QtCore import QObject, QRect, Signal

from ..config.schemas import AppConfig
from .cache import TranslationCache
from .ocr_processor import OCRProcessor
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
        self._cache = TranslationCache(ttl_seconds=2.0)
        self._translator: Optional[Translator] = None

    def start(self, config: Optional[AppConfig] = None) -> None:  # type: ignore[override]
        if self._running.is_set():
            return
        self._running.set()
        self._stop_event.clear()

        self._active_config = config or self._config_manager.config

        ocr_languages = self._get_ocr_languages(self._active_config.translation.source_language)
        self._ocr.set_languages(ocr_languages)

        self._capturer.start()
        self._ocr.start()
        api_config = self._active_config.api
        self._translator = Translator(api_config, logger=lambda msg: self.log_message.emit(f"[翻译器] {msg}"))

        self._interval = self._active_config.translation.interval_ms / 1000.0

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
            except Exception as exc:  # pragma: no cover
                error_msg = f"发生错误: {str(exc)}"
                self.log_message.emit(error_msg)
                self.engine_error.emit(error_msg)
            finally:
                self._sleep_interval()

        self.log_message.emit("翻译引擎已停止")

    def _sleep_interval(self) -> None:
        time.sleep(self._interval)

    def stop(self) -> None:
        if not self._running.is_set():
            return
        self._stop_event.set()
        self._running.clear()
        self._capturer.stop()
        self._ocr.stop()
        if self.is_alive():
            self.join(timeout=2)

    @property
    def is_running(self) -> bool:
        return self._running.is_set()
