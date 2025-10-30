"""Tests for SettingsDialog GUI."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from screen_translate.config.schemas import ApiConfig
from screen_translate.ui.settings_dialog import SettingsDialog


def test_settings_dialog_fields(qtbot: QtBot) -> None:
    api_config = ApiConfig(
        endpoint="https://example.com/v1/chat/completions",
        api_key="test-key",
        model="gpt-4",
        system_prompt="Test prompt",
    )
    dlg = SettingsDialog(api_config)

    assert dlg._endpoint_edit.text() == "https://example.com/v1/chat/completions"
    assert dlg._api_key_edit.text() == "test-key"
    assert dlg._model_edit.text() == "gpt-4"
    assert dlg._system_prompt_edit.toPlainText() == "Test prompt"

    dlg._endpoint_edit.setText("https://new-endpoint.com")
    dlg._model_edit.setText("new-model")

    with qtbot.waitSignal(dlg.accepted, timeout=100):
        dlg.accept()

    updated = dlg.get_config()
    assert updated.endpoint == "https://new-endpoint.com"
    assert updated.api_key == "test-key"
    assert updated.model == "new-model"
    assert updated.system_prompt == "Test prompt"


def test_settings_dialog_empty_api_key(qtbot: QtBot) -> None:
    api_config = ApiConfig(endpoint="https://example.com/v1/chat/completions")

    dlg = SettingsDialog(api_config)
    dlg._api_key_edit.clear()

    with qtbot.waitSignal(dlg.accepted, timeout=100):
        dlg.accept()

    updated = dlg.get_config()
    assert updated.api_key is None