"""Settings dialog for configuring translation service."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QSpinBox,
    QTabWidget,
    QWidget,
)

from ..config.schemas import ApiConfig, TranslationConfig


class SettingsDialog(QDialog):
    """Settings dialog allowing users to configure translation API and language settings."""

    def __init__(self, api_config: ApiConfig, translation_config: TranslationConfig, parent=None) -> None:
        super().__init__(parent)
        self._original_api_config = api_config
        self._original_translation_config = translation_config
        self._edited_api_config = api_config.model_copy()
        self._edited_translation_config = translation_config.model_copy()
        self.setWindowTitle("翻译设置")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self) -> None:
        tab_widget = QTabWidget(self)

        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        api_layout.setSpacing(10)

        self._endpoint_edit = QLineEdit(self._edited_api_config.endpoint, self)
        api_layout.addRow("Endpoint", self._endpoint_edit)

        self._api_key_edit = QLineEdit(self._edited_api_config.api_key or "", self)
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key", self._api_key_edit)

        self._model_edit = QLineEdit(self._edited_api_config.model, self)
        api_layout.addRow("Model", self._model_edit)

        self._system_prompt_edit = QTextEdit(self)
        self._system_prompt_edit.setPlaceholderText("可选：系统提示词")
        self._system_prompt_edit.setMaximumHeight(100)
        if self._edited_api_config.system_prompt:
            self._system_prompt_edit.setText(self._edited_api_config.system_prompt)
        api_layout.addRow("System Prompt", self._system_prompt_edit)

        tab_widget.addTab(api_tab, "API 配置")

        translation_tab = QWidget()
        translation_layout = QFormLayout(translation_tab)
        translation_layout.setSpacing(10)

        self._source_lang_combo = QComboBox(self)
        self._source_lang_combo.addItem("自动检测", "auto")
        self._source_lang_combo.addItem("英语", "en")
        self._source_lang_combo.addItem("日语", "ja")
        self._source_lang_combo.addItem("韩语", "ko")
        current_index = self._source_lang_combo.findData(self._edited_translation_config.source_language)
        if current_index >= 0:
            self._source_lang_combo.setCurrentIndex(current_index)
        translation_layout.addRow("源语言", self._source_lang_combo)

        self._target_lang_combo = QComboBox(self)
        self._target_lang_combo.addItem("中文", "zh")
        current_index = self._target_lang_combo.findData(self._edited_translation_config.target_language)
        if current_index >= 0:
            self._target_lang_combo.setCurrentIndex(current_index)
        translation_layout.addRow("目标语言", self._target_lang_combo)

        self._interval_spinbox = QSpinBox(self)
        self._interval_spinbox.setRange(100, 5000)
        self._interval_spinbox.setSingleStep(100)
        self._interval_spinbox.setValue(self._edited_translation_config.interval_ms)
        self._interval_spinbox.setSuffix(" ms")
        translation_layout.addRow("检测间隔", self._interval_spinbox)

        tab_widget.addTab(translation_tab, "翻译设置")

        layout = QFormLayout(self)
        layout.addRow(tab_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_api_config(self) -> ApiConfig:
        self._edited_api_config.endpoint = self._endpoint_edit.text().strip()
        self._edited_api_config.api_key = self._api_key_edit.text().strip() or None
        self._edited_api_config.model = self._model_edit.text().strip()
        system_prompt = self._system_prompt_edit.toPlainText().strip()
        self._edited_api_config.system_prompt = system_prompt or None
        return self._edited_api_config

    def get_translation_config(self) -> TranslationConfig:
        source_lang = self._source_lang_combo.currentData()
        target_lang = self._target_lang_combo.currentData()
        interval = self._interval_spinbox.value()
        self._edited_translation_config.source_language = source_lang
        self._edited_translation_config.target_language = target_lang
        self._edited_translation_config.interval_ms = interval
        return self._edited_translation_config
