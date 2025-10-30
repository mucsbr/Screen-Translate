"""Core controller coordinating UI and translation engine."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QRect, Signal

from ..config.manager import ConfigManager
from ..config.schemas import AppConfig, WindowConfig
from ..ui.display_overlay import DisplayOverlay
from ..ui.region_selector import RegionSelector
from ..ui.settings_dialog import SettingsDialog
from .engine import TranslationEngine


class MainController(QObject):
    """Glue layer between UI widgets and the translation engine."""

    status_changed = Signal(str)
    log_message = Signal(str)
    source_region_changed = Signal(QRect)
    target_region_changed = Signal(QRect)

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config_manager = config_manager
        self._engine = None
        self._overlay = DisplayOverlay(style=config_manager.config.overlay_style)
        self._source_overlay = self._create_source_overlay()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def bind_main_window(self, window) -> None:  # noqa: ANN001
        self._main_window = window
        window.source_region_requested.connect(self.select_source_region)
        window.target_region_requested.connect(self.select_target_region)
        window.toggle_requested.connect(self.toggle_translation)
        window.settings_requested.connect(self.open_settings)
        self.log_message.connect(window.append_log)
        self.status_changed.connect(window.update_status)

        self.log_message.emit("应用程序已启动，请选择源区域和目标区域")

    def select_source_region(self) -> None:
        rect = RegionSelector("请选择字幕区域", parent=self._main_window).exec()
        if rect.isNull():
            self._emit_status("源区域选择已取消")
            return
        window = rect_to_window(rect)
        self._config_manager.update(source_region=window)
        self.source_region_changed.emit(rect)
        self._emit_status("源区域已更新")

        self._source_overlay.set_geometry(rect)
        self._source_overlay.show()
        self.log_message.emit(f"源区域已选择：{rect.width()}x{rect.height()}（蓝色覆盖层表示OCR识别区域）")

        target_region = self._config_manager.config.target_region
        if target_region.width > 0 and target_region.height > 0:
            target_rect = rect_from_window(target_region)
            self._overlay.set_geometry(target_rect)
            self._overlay.show()
            self.log_message.emit(f"目标区域已设置（灰色覆盖层表示显示区域）")

    def select_target_region(self) -> None:
        rect = RegionSelector("请选择显示区域", parent=self._main_window).exec()
        if rect.isNull():
            self._emit_status("目标区域选择已取消")
            return
        window = rect_to_window(rect)
        self._config_manager.update(target_region=window)
        self._overlay.set_geometry(rect)
        self._overlay.show()
        self.target_region_changed.emit(rect)
        self._emit_status("目标区域已更新")
        self.log_message.emit(f"目标区域覆盖层已显示：{rect.width()}x{rect.height()}（灰色半透明区域）")

    def open_settings(self) -> None:
        dlg = SettingsDialog(
            self._config_manager.config.api,
            self._config_manager.config.translation,
            parent=self._main_window
        )
        if dlg.exec():
            new_api = dlg.get_api_config()
            new_translation = dlg.get_translation_config()
            self._config_manager.update(api=new_api, translation=new_translation)
            self._emit_status("设置已保存")

    def start_translation(self) -> None:
        if self._engine is not None and self._engine.is_running:
            return

        self._engine = TranslationEngine(config_manager=self._config_manager)
        config = self._config_manager.config
        self._overlay.set_geometry(rect_from_window(config.target_region))
        self._overlay.show()
        self._source_overlay.hide()

        self._engine.translation_ready.connect(self._handle_translation)
        self._engine.log_message.connect(self.log_message.emit)
        self._engine.ocr_text_detected.connect(lambda text: self.log_message.emit(f"检测到文本: {text[:50]}{'...' if len(text) > 50 else ''}"))
        self._engine.translation_requested.connect(
            lambda text, src, tgt: self.log_message.emit(f"请求翻译: {text[:50]}{'...' if len(text) > 50 else ''} ({src}→{tgt})")
        )
        self._engine.translation_received.connect(
            lambda text: self.log_message.emit(f"收到翻译: {text[:50]}{'...' if len(text) > 50 else ''}")
        )
        self._engine.language_detected.connect(
            lambda lang: self.log_message.emit(f"识别语言: {lang}")
        )
        self._engine.engine_error.connect(self._handle_error)

        self._engine.start(config)
        self._emit_status("运行中")

    def stop_translation(self) -> None:
        if self._engine is None or not self._engine.is_running:
            return
        self._engine.translation_ready.disconnect(self._handle_translation)
        self._engine.log_message.disconnect()
        self._engine.ocr_text_detected.disconnect()
        self._engine.translation_requested.disconnect()
        self._engine.translation_received.disconnect()
        self._engine.language_detected.disconnect()
        self._engine.engine_error.disconnect(self._handle_error)
        self._engine.stop()
        self._engine = None
        self._overlay.hide()
        self._source_overlay.show()
        self.log_message.emit("翻译已停止，源区域覆盖层已恢复显示")
        self._emit_status("已停止")

    def toggle_translation(self) -> None:
        if self._engine is not None and self._engine.is_running:
            self.stop_translation()
        else:
            self.start_translation()

    def _handle_error(self, error_msg: str) -> None:
        self._emit_status(f"错误: {error_msg}")

    @property
    def engine(self) -> TranslationEngine:
        """Expose translation engine for UI wiring."""
        if self._engine is None:
            self._engine = TranslationEngine(config_manager=self._config_manager)
        return self._engine

    @property
    def overlay(self) -> DisplayOverlay:
        return self._overlay

    @property
    def config_manager(self) -> ConfigManager:
        """Expose configuration manager."""
        return self._config_manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _create_source_overlay(self) -> DisplayOverlay:
        from ..config.schemas import OverlayStyle
        style = OverlayStyle(
            background_color="#5500A0FF",
            text_color="#00000000"
        )
        overlay = DisplayOverlay(style=style)
        overlay.hide()
        return overlay

    def _handle_translation(self, text: str) -> None:
        self._overlay.update_text(text)
        self.log_message.emit(f"收到翻译：{text}")

    def _emit_status(self, status: str) -> None:
        self.status_changed.emit(status)
        self.log_message.emit(status)


def rect_to_window(rect: QRect) -> WindowConfig:
    return WindowConfig(x=rect.x(), y=rect.y(), width=rect.width(), height=rect.height())


def rect_from_window(window_config: WindowConfig) -> QRect:
    return QRect(window_config.x, window_config.y, window_config.width, window_config.height)
