"""Pydantic schemas for application configuration."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class WindowConfig(BaseModel):
    """Geometry configuration for selectable regions."""

    x: int = Field(0, ge=0)
    y: int = Field(0, ge=0)
    width: int = Field(640, ge=1)
    height: int = Field(200, ge=1)


class TranslationConfig(BaseModel):
    """Parameters controlling translation behavior."""

    source_language: Literal["auto", "en", "ja", "ko"] = "auto"
    target_language: Literal["zh"] = "zh"
    interval_ms: int = Field(800, ge=100, le=5000)


class ApiConfig(BaseModel):
    """Credentials and endpoint configuration for translation API."""

    endpoint: str = "https://api.openai.com/v1/chat/completions"
    api_key: Optional[str] = Field(default=None, repr=False)
    model: str = "gpt-3.5-turbo"
    system_prompt: Optional[str] = Field(default=None)


class OverlayStyle(BaseModel):
    """Styling options for overlay window."""

    font_family: str = "Arial"
    font_size: int = Field(20, ge=8, le=96)
    text_color: str = "#FFFFFF"
    background_color: str = "#33000000"


class AudioDeviceConfig(BaseModel):
    """Configuration for audio input/output devices."""

    physical_output_device: Optional[int] = Field(default=None, description="Physical output device index")
    virtual_input_device: Optional[int] = Field(default=None, description="Virtual input device index (BlackHole)")
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    chunk_size: int = Field(default=1024, ge=512, le=8192)


class VoskConfig(BaseModel):
    """Configuration for Vosk speech recognition."""

    model_path: str = Field(default="models/vosk-model-small-en-us-0.15", description="Path to Vosk model")
    language: Literal["en", "zh", "ja", "ko", "auto"] = "auto"


class WhisperConfig(BaseModel):
    """Configuration for Whisper speech recognition."""

    model: Literal["tiny", "base", "small", "medium", "large"] = Field(default="base", description="Whisper model size")
    language: Optional[Literal["en", "zh", "ja", "ko"]] = Field(default=None, description="Audio language (None for auto-detect)")
    engine: Literal["openai", "whisper"] = Field(default="openai", description="Whisper implementation (openai or whisper)")


class AudioConfig(BaseModel):
    """Configuration for audio-based translation."""

    enabled: bool = Field(default=False, description="Enable audio input mode")
    device: AudioDeviceConfig = AudioDeviceConfig()
    vosk: VoskConfig = VoskConfig()
    whisper: WhisperConfig = WhisperConfig()
    stt_engine: Literal["vosk", "whisper"] = Field(default="whisper", description="Speech recognition engine")


class AppConfig(BaseModel):
    """Root configuration model for the application."""

    source_region: WindowConfig = WindowConfig()
    target_region: WindowConfig = WindowConfig(width=800, height=250)
    translation: TranslationConfig = TranslationConfig()
    api: ApiConfig = ApiConfig()
    overlay_style: OverlayStyle = OverlayStyle()
    audio: AudioConfig = AudioConfig()
