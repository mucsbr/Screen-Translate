"""Tests for settings dialog and configuration updates."""

from __future__ import annotations

from pathlib import Path

from screen_translate.config.manager import ConfigManager
from screen_translate.config.schemas import ApiConfig


def test_settings_update_persists(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    manager = ConfigManager(config_path=config_dir / "config.json")

    assert manager.config.api.endpoint == "https://api.openai.com/v1/chat/completions"
    assert manager.config.api.api_key is None
    assert manager.config.api.model == "gpt-3.5-turbo"

    new_api = ApiConfig(
        endpoint="https://example.com/v1/chat/completions",
        api_key="test-key",
        model="gpt-4",
        system_prompt="Custom prompt",
    )
    manager.update(api=new_api)

    assert manager.config.api.endpoint == "https://example.com/v1/chat/completions"
    assert manager.config.api.api_key == "test-key"
    assert manager.config.api.model == "gpt-4"
    assert manager.config.api.system_prompt == "Custom prompt"

    manager2 = ConfigManager(config_path=config_dir / "config.json")
    assert manager2.config.api.endpoint == "https://example.com/v1/chat/completions"
    assert manager2.config.api.api_key == "test-key"
    assert manager2.config.api.model == "gpt-4"
    assert manager2.config.api.system_prompt == "Custom prompt"