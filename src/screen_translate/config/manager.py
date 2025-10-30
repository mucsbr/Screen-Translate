"""Configuration manager for Screen Translate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schemas import AppConfig


@dataclass
class ConfigManager:
    """Load, manage, and persist application configuration."""

    config_path: Path = field(default_factory=lambda: Path.home() / ".screen_translate" / "config.json")
    _config: AppConfig = field(init=False)

    def __post_init__(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config = self._load_or_default()

    @property
    def config(self) -> AppConfig:
        """Return the current configuration model."""
        return self._config

    def update(self, **kwargs: Any) -> None:
        """Update configuration fields and persist to disk."""
        self._config = self._config.model_copy(update=kwargs)
        self.save()

    def save(self) -> None:
        """Persist configuration to disk."""
        self.config_path.write_text(self._config.model_dump_json(indent=2, ensure_ascii=False))

    def _load_or_default(self) -> AppConfig:
        if self.config_path.exists():
            return AppConfig.model_validate_json(self.config_path.read_text())
        config = AppConfig()
        self.config_path.write_text(config.model_dump_json(indent=2, ensure_ascii=False))
        return config
