"""Whisper-based audio processor for speech recognition."""

from __future__ import annotations

import io
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pyaudio
import whisper
import torch
from loguru import logger

from ..config.schemas import WhisperConfig, AudioDeviceConfig


@dataclass
class AudioResult:
    """Result of audio speech recognition."""
    text: str
    confidence: float


class WhisperProcessor:
    """Audio-based speech recognition using OpenAI Whisper."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024) -> None:
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._model: Optional[whisper.Whisper] = None
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self._running: bool = False
        self._last_transcription: str = ""
        self._last_transcription_time: float = 0
        self._audio_buffer: List[bytes] = []
        self._buffer_duration: float = 3.0  # 3秒音频缓冲
        self._config: Optional[WhisperConfig] = None

    def start(self, config: WhisperConfig, device_config: AudioDeviceConfig, device_index: Optional[int] = None) -> None:
        """Start audio recording and transcription."""
        if self._running:
            return

        self._running = True
        self._config = config

        # 加载Whisper模型
        try:
            logger.info(f"加载Whisper模型: {config.model}")
            self._model = whisper.load_model(config.model)

            # 根据芯片选择最优的设备
            if torch.backends.mps.is_available():
                logger.info("使用MPS加速 (Apple Silicon)")
                self._model = self._model.to("mps")
            elif torch.cuda.is_available():
                logger.info("使用CUDA加速")
                self._model = self._model.to("cuda")
            else:
                logger.info("使用CPU模式")
        except Exception as e:
            self._running = False
            raise RuntimeError(f"Whisper模型加载失败: {str(e)}") from e

        # 初始化PyAudio
        self._pyaudio = pyaudio.PyAudio()

        try:
            if device_index is None:
                # 尝试找到BlackHole设备
                device_index = self._find_blackhole_device()
                if device_index is None:
                    self._running = False
                    raise RuntimeError(
                        "未找到 BlackHole 虚拟音频设备。\n\n"
                        "请确保：\n"
                        "1. 已安装 BlackHole：brew install blackhole-2ch\n"
                        "2. 在系统设置中已将音频输出切换到 BlackHole\n"
                        "3. 播放音频以确保有音频流过 BlackHole"
                    )

            device_info = self._pyaudio.get_device_info_by_index(device_index)
            if device_info['maxInputChannels'] < 1:
                self._running = False
                raise RuntimeError(f"设备 {device_index} 不支持音频输入")

            # 创建音频流
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self._chunk_size,
                stream_callback=self._audio_callback
            )

            self._thread = threading.Thread(target=self._process_audio, daemon=True)
            self._thread.start()

            logger.info(f"Whisper音频处理已启动，设备: {device_info['name']}")

        except Exception as e:
            self._running = False
            raise RuntimeError(f"音频流启动失败: {str(e)}") from e

    def stop(self) -> None:
        """Stop audio recording and transcription."""
        if not self._running:
            return

        self._running = False

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

        self._model = None
        self._audio_buffer.clear()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def _find_blackhole_device(self) -> Optional[int]:
        """Find BlackHole virtual audio device."""
        if not self._pyaudio:
            return None

        for i in range(self._pyaudio.get_device_count()):
            device_info = self._pyaudio.get_device_info_by_index(i)
            device_name = device_info.get('name', '').lower()
            if 'blackhole' in device_name and device_info['maxInputChannels'] > 0:
                logger.info(f"找到BlackHole设备: {device_info['name']} (索引: {i})")
                return i
        return None

    def _audio_callback(self, in_data: bytes, frame_count: int, time_info: Dict[str, Any], status: Any) -> tuple[None, Any]:
        """Callback for PyAudio stream."""
        if self._running and in_data and len(in_data) > 0:
            try:
                self._audio_queue.put_nowait(in_data)
            except queue.Full:
                pass
        return (None, pyaudio.paContinue)

    def _process_audio(self) -> None:
        """Process audio data in a separate thread."""
        while self._running:
            try:
                audio_data = self._audio_queue.get(timeout=0.1)
                if audio_data and len(audio_data) > 0:
                    self._audio_buffer.append(audio_data)

                    # 检查缓冲区是否达到指定时长
                    buffer_duration = len(self._audio_buffer) * self._chunk_size / self._sample_rate
                    if buffer_duration >= self._buffer_duration:
                        self._transcribe_buffer()
                        self._audio_buffer.clear()

            except queue.Empty:
                continue
            except Exception:
                break

    def _transcribe_buffer(self) -> None:
        """Transcribe accumulated audio buffer."""
        if not self._model or not self._audio_buffer:
            return

        try:
            # 合并音频数据
            audio_data = b''.join(self._audio_buffer)

            # 转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # 根据配置决定语言设置
            if self._config and self._config.language:
                language = self._config.language
                logger.info(f"使用指定语言: {language}")
            else:
                language = None  # 自动检测
                logger.info("自动检测语言")

            # 使用Whisper进行转录
            result = self._model.transcribe(
                audio_array,
                language=language,
                initial_prompt="",
                temperature=0.0,
                best_of=1,
                beam_size=1,
                word_timestamps=False,
                condition_on_previous_text=True
            )

            transcribed_text = result.get('text', '').strip()

            if transcribed_text:
                self._last_transcription = transcribed_text
                self._last_transcription_time = time.time()
                detected_language = result.get('language', 'unknown')
                logger.info(f"Whisper识别[{detected_language}]: {transcribed_text}")

        except Exception as e:
            logger.warning(f"Whisper转录失败: {str(e)}")

    def read_text(self) -> List[AudioResult]:
        """Get transcribed text from audio."""
        results = []
        current_time = time.time()

        # 返回最近的转录结果，但避免重复
        if (self._last_transcription and
            current_time - self._last_transcription_time < 10.0):  # 10秒内的结果有效

            results.append(AudioResult(
                text=self._last_transcription,
                confidence=0.9  # Whisper置信度通常较高
            ))

            # 清除结果，避免重复返回
            self._last_transcription = ""

        return results

    def list_audio_devices(self) -> Dict[int, str]:
        """List available audio input devices."""
        devices = {}
        pa = pyaudio.PyAudio()
        try:
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices[i] = f"{device_info['name']} (输入通道: {device_info['maxInputChannels']})"
        finally:
            pa.terminate()
        return devices

    @property
    def is_running(self) -> bool:
        """Check if Whisper processor is running."""
        return self._running