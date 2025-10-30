"""Display overlay implementation using PySide6."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics, QMouseEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..config.schemas import OverlayStyle


class DisplayOverlay(QWidget):
    """Frameless window that floats above all windows to show translated text."""

    def __init__(self, style: Optional[OverlayStyle] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._style = style or OverlayStyle()
        self._dragging: bool = False
        self._drag_start_position: QPoint = QPoint()

        self._configure_window()
        self._build_ui()
        self.apply_style(self._style)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_text(self, text: str) -> None:
        """Update the overlay text content."""
        self._label.setText(text)
        self._adjust_font_size()

    def _adjust_font_size(self) -> None:
        """Adjust font size to fit within the overlay area."""
        text = self._label.text()
        if not text:
            return

        min_font_size = 10
        max_font_size = max(48, self._style.font_size)
        available_width = self.width() - 16
        available_height = self.height() - 16

        if available_width <= 0 or available_height <= 0:
            return

        best_size = min_font_size

        for size in range(max_font_size, min_font_size - 1, -1):
            font = self._label.font()
            font.setPointSize(size)
            metrics = QFontMetrics(font)

            lines = text.split('\n')
            max_line_width = 0
            total_text_height = 0

            for line in lines:
                line_width = metrics.horizontalAdvance(line)
                max_line_width = max(max_line_width, line_width)
                line_height = metrics.height()
                total_text_height += line_height

            if len(lines) > 1:
                total_text_height += (len(lines) - 1) * metrics.leading()

            if max_line_width <= available_width and total_text_height <= available_height:
                best_size = size
                break

        rgba = QColor(self._style.background_color)
        bg_color = rgba.name(QColor.HexArgb) if rgba.isValid() else "#33000000"

        self._label.setStyleSheet(
            f"color: {self._style.text_color};"
            f"font-family: '{self._style.font_family}';"
            f"font-size: {best_size}px;"
            "padding: 8px;"
            f"background-color: {bg_color};"
        )
        self._label.update()

    def apply_style(self, style: OverlayStyle) -> None:
        """Apply overlay style settings."""
        self._style = style
        stylesheet = (
            f"color: {style.text_color};"
            f"font-family: '{style.font_family}';"
            f"font-size: {style.font_size}px;"
            "padding: 8px;"
        )
        rgba = QColor(style.background_color)
        if rgba.isValid():
            stylesheet += f"background-color: {rgba.name(QColor.HexArgb)};"
        self._label.setStyleSheet(stylesheet)

    def set_geometry(self, rect: QRect) -> None:
        """Set overlay window geometry."""
        if not rect.isNull():
            self.move(rect.x(), rect.y())
            self.setFixedSize(rect.width(), rect.height())
            self._adjust_font_size()

    def resizeEvent(self, event) -> None:  # noqa: D401 - Qt override
        super().resizeEvent(event)
        self._adjust_font_size()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel("…", self)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        label.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(label)
        self._label = label

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if event.button() == Qt.LeftButton:
            self._dragging = True
            if hasattr(event, 'globalPosition'):
                self._drag_start_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                self._drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if self._dragging and event.buttons() == Qt.LeftButton:
            if hasattr(event, 'globalPosition'):
                self.move(event.globalPosition().toPoint() - self._drag_start_position)
            else:
                self.move(event.globalPos() - self._drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
