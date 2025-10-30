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


class AppConfig(BaseModel):
    """Root configuration model for the application."""

    source_region: WindowConfig = WindowConfig()
    target_region: WindowConfig = WindowConfig(width=800, height=250)
    translation: TranslationConfig = TranslationConfig()
    api: ApiConfig = ApiConfig()
    overlay_style: OverlayStyle = OverlayStyle()
