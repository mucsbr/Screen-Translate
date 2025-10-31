"""Audio processing using PyAudio + Vosk for speech recognition."""

from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np

try:
    import pyaudio
except ImportError:  # pragma: no cover
    pyaudio = None

try:
    from vosk import Model, KaldiRecognizer
except ImportError:  # pragma: no cover
    Model = None
    KaldiRecognizer = None


@dataclass
class AudioResult:
    """Container for audio recognition text and confidence."""

    text: str
    confidence: float


@dataclass
class AudioDeviceInfo:
    """Information about an audio device."""

    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float


class AudioProcessor:
    """Wrap PyAudio + Vosk for speech recognition."""

    def __init__(self, sample_rate: int = 16000, chunk_size: int = 1024) -> None:
        self._sample_rate = sample_rate
        self._chunk_size = chunk_size
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._model: Optional[Model] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._model_path: Optional[str] = None
        self._last_partial_text: str = ""

    def list_audio_devices(self) -> List[AudioDeviceInfo]:
        """List all available audio devices."""
        if pyaudio is None:
            raise RuntimeError("PyAudio 未安装，请先安装依赖 pyaudio。")

        devices = []
        p = pyaudio.PyAudio()
        try:
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                devices.append(AudioDeviceInfo(
                    index=i,
                    name=device_info['name'],
                    max_input_channels=int(device_info['maxInputChannels']),
                    max_output_channels=int(device_info['maxOutputChannels']),
                    default_sample_rate=device_info['defaultSampleRate']
                ))
        finally:
            p.terminate()
        return devices

    def find_blackhole_device(self) -> Optional[int]:
        """Find BlackHole virtual audio device index."""
        devices = self.list_audio_devices()
        for device in devices:
            if 'blackhole' in device.name.lower() or 'black hole' in device.name.lower():
                if device.max_input_channels > 0:
                    return device.index
        return None

    def start(self, model_path: str, device_index: Optional[int] = None) -> None:
        """Start audio capture and speech recognition."""
        if pyaudio is None:
            raise RuntimeError("PyAudio 未安装，请先安装依赖 pyaudio。")
        if Model is None:
            raise RuntimeError("Vosk 未安装，请先安装依赖 vosk。")

        if self._running:
            return

        self._running = True

        if not os.path.exists(model_path):
            self._running = False
            raise RuntimeError(f"Vosk 模型未找到: {model_path}")

        try:
            self._model = Model(model_path)
        except Exception as e:
            error_msg = (
                f"Vosk 模型加载失败: {str(e)}\n\n"
                "这可能是由于以下原因：\n"
                "1. M1/M2 芯片兼容性问题\n"
                "2. 模型文件损坏或不完整\n"
                "3. Vosk 版本与模型版本不匹配\n\n"
                "解决方案：\n"
                "1. 尝试使用不同的 Vosk 版本：pip install vosk==0.3.42\n"
                "2. 确保模型文件完整（检查 models 目录大小应为 ~50MB）\n"
                "3. 重新下载模型文件\n"
                "4. 使用 Rosetta 模式运行：arch -x86_64 python -m screen_translate.app"
            )
            self._running = False
            raise RuntimeError(error_msg) from e

        self._pyaudio = pyaudio.PyAudio()

        try:
            if device_index is None:
                device_index = self.find_blackhole_device()
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

            if device_info.get('defaultSampleRate', 0) == 0:
                self._running = False
                raise RuntimeError(f"设备 {device_index} 采样率无效")

            self._recognizer = KaldiRecognizer(self._model, self._sample_rate)

            self._recognizer.SetWords(True)

            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self._chunk_size,
                stream_callback=self._audio_callback
            )

            self._stream.start_stream()

            time.sleep(0.1)
            if not self._stream.is_active():
                self._running = False
                raise RuntimeError("音频流未成功启动，请检查音频设备连接")

            self._thread = threading.Thread(target=self._process_audio, daemon=True)
            self._thread.start()

        except Exception as e:
            error_msg = (
                f"音频设备初始化失败: {str(e)}\n\n"
                "检查清单：\n"
                "1. 确保 BlackHole 已安装并配置：brew install blackhole-2ch\n"
                "2. 在系统设置中将音频输出切换到 BlackHole\n"
                "3. 播放音频内容（必须有声音流入 BlackHole）\n"
                "4. 确保应用程序有麦克风访问权限\n"
                "5. 重启应用程序后重试"
            )
            self._running = False
            self.stop()
            raise RuntimeError(error_msg) from e

    def stop(self) -> None:
        """Stop audio capture and speech recognition."""
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
        self._recognizer = None
        self._last_partial_text = ""

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

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
        silence = bytes(self._chunk_size * 2)

        if self._recognizer:
            try:
                self._recognizer.AcceptWaveform(silence)
            except Exception:
                pass

        while self._running:
            try:
                audio_data = self._audio_queue.get(timeout=0.1)
                if self._recognizer and audio_data and len(audio_data) > 0:
                    try:
                        self._recognizer.AcceptWaveform(audio_data)
                    except Exception:
                        continue
            except queue.Empty:
                continue
            except Exception:
                break

    def read_text(self) -> List[AudioResult]:
        """Get recognized text from audio."""
        results = []

        if self._recognizer and self._running:
            try:
                final_result = self._recognizer.Result()
                if final_result:
                    import json
                    try:
                        result_json = json.loads(final_result)
                        current_text = result_json.get('text', '').strip()

                        if current_text and current_text != self._last_partial_text:
                            # 使用FinalResult而不是PartialResult，避免累积问题
                            results.append(AudioResult(text=current_text, confidence=0.9))
                            self._last_partial_text = current_text
                    except (json.JSONDecodeError, KeyError):
                        pass
                else:
                    # 如果没有最终结果，检查PartialResult但更保守
                    partial_result = self._recognizer.PartialResult()
                    if partial_result:
                        import json
                        try:
                            result_json = json.loads(partial_result)
                            current_text = result_json.get('partial', '').strip()

                            if current_text and current_text != self._last_partial_text:
                                # 检查是否有明显的句子结束符
                                if current_text.endswith(('.', '!', '?', '。', '！', '？', ' ', '。', '！', '？')):
                                    results.append(AudioResult(text=current_text, confidence=0.7))
                                    self._last_partial_text = current_text
                        except (json.JSONDecodeError, KeyError):
                            pass
            except Exception:
                pass

        return results

    @property
    def is_running(self) -> bool:
        """Check if audio processor is running."""
        return self._running
