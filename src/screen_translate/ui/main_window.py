"""Main window UI skeleton."""

from __future__ import annotations

from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.controller import MainController


class MainWindow(QMainWindow):
    """Primary application window for Screen Translate."""

    source_region_requested = Signal()
    target_region_requested = Signal()
    toggle_requested = Signal()
    settings_requested = Signal()

    def __init__(self, controller: MainController) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Screen Translate")
        self.resize(520, 360)

        self._status_label: QLabel
        self._log_output: QTextEdit

        self._build_ui()
        self._connect_signals()
        self.update_status("准备就绪")

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self._status_label = QLabel(self)
        self._status_label.setAlignment(Qt.AlignLeft)

        button_layout = QHBoxLayout()
        btn_select_source = QPushButton("选择字幕区域", self)
        btn_select_target = QPushButton("选择显示区域", self)
        btn_toggle = QPushButton("开始/停止", self)
        btn_settings = QPushButton("设置", self)
        button_layout.addWidget(btn_select_source)
        button_layout.addWidget(btn_select_target)
        button_layout.addWidget(btn_toggle)
        button_layout.addWidget(btn_settings)

        log_output = QTextEdit(self)
        log_output.setReadOnly(True)
        log_output.setPlaceholderText("运行日志将在此显示……")
        self._log_output = log_output

        layout.addWidget(self._status_label)
        layout.addLayout(button_layout)
        layout.addWidget(self._log_output)

        self._btn_select_source = btn_select_source
        self._btn_select_target = btn_select_target
        self._btn_toggle = btn_toggle
        self._btn_settings = btn_settings

    def _connect_signals(self) -> None:
        self._btn_toggle.clicked.connect(self.toggle_requested.emit)
        self._btn_select_source.clicked.connect(self.source_region_requested.emit)
        self._btn_select_target.clicked.connect(self.target_region_requested.emit)
        self._btn_settings.clicked.connect(self.settings_requested.emit)

    @Slot(str)
    def update_status(self, status: str) -> None:
        self._status_label.setText(f"状态：{status}")
        self.append_log(f"状态更新为：{status}")

    @Slot(str)
    def append_log(self, message: str) -> None:
        self._log_output.append(message)
