"""Settings dialog for configuring translation service."""

from __future__ import annotations

from typing import Optional, List

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
    QCheckBox,
    QPushButton,
    QMessageBox,
    QLabel,
)

from ..config.schemas import ApiConfig, TranslationConfig, AudioConfig, AudioDeviceConfig, VoskConfig
from ..core.audio_processor import AudioProcessor, AudioDeviceInfo


class SettingsDialog(QDialog):
    """Settings dialog allowing users to configure translation API and language settings."""

    def __init__(self, api_config: ApiConfig, translation_config: TranslationConfig, audio_config: AudioConfig, parent=None) -> None:
        super().__init__(parent)
        self._original_api_config = api_config
        self._original_translation_config = translation_config
        self._original_audio_config = audio_config
        self._edited_api_config = api_config.model_copy()
        self._edited_translation_config = translation_config.model_copy()
        self._edited_audio_config = audio_config.model_copy()
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

        # 添加提示：音频模式下不需要区域选择
        self._audio_mode_hint = QLabel("💡 音频模式下无需选择区域，直接处理系统音频", self)
        self._audio_mode_hint.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        self._audio_mode_hint.setWordWrap(True)

        # 根据当前音频状态设置提示显示
        self._audio_mode_hint.setVisible(self._edited_audio_config.enabled)

        translation_layout.addRow("", self._audio_mode_hint)

        tab_widget.addTab(translation_tab, "翻译设置")

        audio_tab = QWidget()
        audio_layout = QFormLayout(audio_tab)
        audio_layout.setSpacing(10)

        self._audio_enabled_checkbox = QCheckBox("启用音频输入模式", self)
        self._audio_enabled_checkbox.setChecked(self._edited_audio_config.enabled)
        self._audio_enabled_checkbox.toggled.connect(self._on_audio_enabled_toggled)
        audio_layout.addRow("", self._audio_enabled_checkbox)

        audio_layout.addRow("输入设备", QWidget())

        self._physical_output_combo = QComboBox(self)
        self._refresh_output_devices()
        audio_layout.addRow("物理输出设备", self._physical_output_combo)

        self._virtual_input_combo = QComboBox(self)
        self._refresh_virtual_devices()
        audio_layout.addRow("虚拟输入设备", self._virtual_input_combo)

        btn_setup_blackhole = QPushButton("设置BlackHole虚拟音频驱动", self)
        btn_setup_blackhole.clicked.connect(self._on_setup_blackhole)
        audio_layout.addRow("", btn_setup_blackhole)

        # STT引擎选择
        self._stt_engine_combo = QComboBox(self)
        self._stt_engine_combo.addItem("Whisper (推荐)", "whisper")
        self._stt_engine_combo.addItem("Vosk", "vosk")
        current_index = self._stt_engine_combo.findData(self._edited_audio_config.stt_engine)
        if current_index >= 0:
            self._stt_engine_combo.setCurrentIndex(current_index)
        self._stt_engine_combo.currentTextChanged.connect(self._on_stt_engine_changed)
        audio_layout.addRow("语音识别引擎", self._stt_engine_combo)

        # Whisper配置
        whisper_group = QWidget()
        whisper_layout = QFormLayout(whisper_group)

        self._whisper_model_combo = QComboBox(self)
        self._whisper_model_combo.addItem("Tiny (最快，准确度较低)", "tiny")
        self._whisper_model_combo.addItem("Base (平衡)", "base")
        self._whisper_model_combo.addItem("Small (较好)", "small")
        self._whisper_model_combo.addItem("Medium (很好)", "medium")
        self._whisper_model_combo.addItem("Large (最好，最慢)", "large")
        current_index = self._whisper_model_combo.findData(self._edited_audio_config.whisper.model)
        if current_index >= 0:
            self._whisper_model_combo.setCurrentIndex(current_index)
        whisper_layout.addRow("Whisper模型", self._whisper_model_combo)

        self._whisper_lang_combo = QComboBox(self)
        self._whisper_lang_combo.addItem("自动检测", "auto")
        self._whisper_lang_combo.addItem("英语", "en")
        self._whisper_lang_combo.addItem("中文", "zh")
        self._whisper_lang_combo.addItem("日语", "ja")
        self._whisper_lang_combo.addItem("韩语", "ko")
        whisper_lang = self._edited_audio_config.whisper.language or "auto"
        current_index = self._whisper_lang_combo.findData(whisper_lang)
        if current_index >= 0:
            self._whisper_lang_combo.setCurrentIndex(current_index)
        whisper_layout.addRow("音频语言", self._whisper_lang_combo)

        audio_layout.addRow("Whisper配置", whisper_group)

        # Vosk配置
        vosk_group = QWidget()
        vosk_layout = QFormLayout(vosk_group)

        self._vosk_model_edit = QLineEdit(self._edited_audio_config.vosk.model_path, self)
        vosk_layout.addRow("模型路径", self._vosk_model_edit)

        btn_download_model = QPushButton("下载默认模型", self)
        btn_download_model.clicked.connect(self._on_download_model)
        vosk_layout.addRow("", btn_download_model)

        audio_layout.addRow("Vosk配置", vosk_group)

        tab_widget.addTab(audio_tab, "音频设置")

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

    def get_audio_config(self) -> AudioConfig:
        self._edited_audio_config.enabled = self._audio_enabled_checkbox.isChecked()

        physical_device_data = self._physical_output_combo.currentData()
        if physical_device_data is not None:
            self._edited_audio_config.device.physical_output_device = physical_device_data

        virtual_device_data = self._virtual_input_combo.currentData()
        if virtual_device_data is not None:
            self._edited_audio_config.device.virtual_input_device = virtual_device_data

        # STT Engine
        self._edited_audio_config.stt_engine = self._stt_engine_combo.currentData()

        # Vosk配置
        self._edited_audio_config.vosk.model_path = self._vosk_model_edit.text().strip()

        # Whisper配置
        self._edited_audio_config.whisper.model = self._whisper_model_combo.currentData()
        whisper_lang = self._whisper_lang_combo.currentData()
        self._edited_audio_config.whisper.language = whisper_lang if whisper_lang != "auto" else None

        return self._edited_audio_config

    def _refresh_output_devices(self) -> None:
        """Refresh the list of physical output devices."""
        try:
            processor = AudioProcessor()
            devices = processor.list_audio_devices()
            self._physical_output_combo.clear()
            self._physical_output_combo.addItem("默认设备", None)

            original_index = self._original_audio_config.device.physical_output_device

            for device in devices:
                if device.max_output_channels > 0:
                    self._physical_output_combo.addItem(
                        f"{device.name} (Index: {device.index})",
                        device.index
                    )

            if original_index is not None:
                index = self._physical_output_combo.findData(original_index)
                if index >= 0:
                    self._physical_output_combo.setCurrentIndex(index)
        except Exception as e:
            self._physical_output_combo.clear()
            self._physical_output_combo.addItem(f"获取设备失败: {str(e)}", None)

    def _refresh_virtual_devices(self) -> None:
        """Refresh the list of virtual input devices."""
        try:
            processor = AudioProcessor()
            devices = processor.list_audio_devices()
            self._virtual_input_combo.clear()
            self._virtual_input_combo.addItem("自动检测 BlackHole", None)

            original_index = self._original_audio_config.device.virtual_input_device

            for device in devices:
                if device.max_input_channels > 0:
                    display_name = device.name
                    if 'blackhole' in device.name.lower() or 'black hole' in device.name.lower():
                        display_name += " ★"
                    self._virtual_input_combo.addItem(
                        f"{display_name} (Index: {device.index})",
                        device.index
                    )

            if original_index is not None:
                index = self._virtual_input_combo.findData(original_index)
                if index >= 0:
                    self._virtual_input_combo.setCurrentIndex(index)
        except Exception as e:
            self._virtual_input_combo.clear()
            self._virtual_input_combo.addItem(f"获取设备失败: {str(e)}", None)

    def _on_audio_enabled_toggled(self, enabled: bool) -> None:
        """Handle audio enabled checkbox toggled."""
        # 显示/隐藏音频模式提示
        self._audio_mode_hint.setVisible(enabled)

    def _on_stt_engine_changed(self, text: str) -> None:
        """Handle STT engine selection change."""
        is_whisper = self._stt_engine_combo.currentData() == "whisper"
        # 根据选择启用/禁用相应的配置组
        # 这里可以进一步优化UI显示

    def _on_setup_blackhole(self) -> None:
        """Handle setup BlackHole button clicked."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("设置 BlackHole 虚拟音频驱动")
        msg.setText(
            "请按照以下步骤设置 BlackHole：\n\n"
            "1. 安装 BlackHole：\n"
            "   brew install blackhole-2ch\n\n"
            "2. 在 macOS 系统偏好设置 > 声音 > 输出 中选择 BlackHole\n\n"
            "3. 在应用程序的音频输出设置中，\n"
            "   选择 BlackHole 作为输出设备\n\n"
            "详细说明请访问：https://github.com/ExistentialAudio/BlackHole"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def _on_download_model(self) -> None:
        """Handle download model button clicked."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("下载 Vosk 模型")
        msg.setText(
            "请手动下载 Vosk 模型：\n\n"
            "1. 访问 https://alphacephei.com/vosk/models\n"
            "2. 下载适合您语言的模型（如 vosk-model-small-en-us-0.15）\n"
            "3. 解压到项目的 models 目录\n"
            "4. 更新上方模型路径"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
