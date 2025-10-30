"""Tests for configuration manager."""

from __future__ import annotations

from pathlib import Path

from screen_translate.config.manager import ConfigManager


def test_config_manager_loads_defaults(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_path=config_dir / "config.json")

    assert manager.config.translation.interval_ms == 800
    assert manager.config.api.endpoint.startswith("https://")
