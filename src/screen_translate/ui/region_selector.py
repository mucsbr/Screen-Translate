"""Interactive screen region selector implemented with PySide6."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, QEventLoop, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RegionSelector(QWidget):
    """Full-screen translucent overlay that captures a rectangular selection."""

    selectionFinished = Signal(QRect)

    def __init__(self, prompt: str = "请拖拽选择区域", parent: Optional[QWidget] = None) -> None:
        parent = parent or QGuiApplication.focusWindow()
        super().__init__(parent)
        self._prompt_text = prompt
        self._loop: Optional[QEventLoop] = None
        self._result: QRect = QRect()
        self._begin: Optional[QPoint] = None
        self._end: Optional[QPoint] = None
        self._prompt_label: Optional[QLabel] = None
        self._selected_rect: Optional[QRect] = None
        self._is_selecting: bool = False

        self._configure_window()
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def exec(self) -> QRect:
        """Display selector and block until user finishes selection.

        Returns:
            QRect describing the selected area in global screen coordinates.
            Returns an empty QRect when the user cancels.
        """
        if self._loop is not None:  # Prevent re-entrancy
            return QRect()

        self._result = QRect()
        self._selected_rect = None
        self._loop = QEventLoop()
        self.selectionFinished.connect(self._store_result)

        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        self._loop.exec()

        self.selectionFinished.disconnect(self._store_result)
        self._loop = None
        return self._result

    # ------------------------------------------------------------------
    # QWidget overrides
    # ------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if event.button() != Qt.LeftButton:
            return
        self._begin = event.position().toPoint()
        self._end = self._begin
        self._is_selecting = True
        if self._prompt_label:
            self._prompt_label.setText(self._prompt_text)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if self._begin is None:
            return
        self._end = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: D401 - Qt override
        if event.button() != Qt.LeftButton or self._begin is None:
            return
        self._end = event.position().toPoint()

        rect = self._current_rect()
        if rect.width() < 5 or rect.height() < 5:
            if self._prompt_label:
                self._prompt_label.setText(f"区域太小，请重新选择")
            self._begin = None
            self._end = None
            self._selected_rect = None
            self._is_selecting = False
            self.update()
            return

        self._selected_rect = rect
        self._is_selecting = False
        if self._prompt_label:
            self._prompt_label.setText(f"已选择: {rect.width()}x{rect.height()} - 正在确认...")
        self.update()

        global_rect = self._to_global(self._selected_rect)
        self.selectionFinished.emit(global_rect)

        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self.close)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: D401 - Qt override
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self.selectionFinished.emit(QRect())
            self.close()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, _) -> None:  # noqa: D401 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self._is_selecting and self._selected_rect is not None:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 30))
            painter.setPen(QPen(QColor(0, 174, 255, 255), 3, Qt.SolidLine))
            painter.setBrush(QColor(0, 174, 255, 50))
            painter.drawRect(self._selected_rect)
            painter.fillRect(self._selected_rect, QColor(0, 174, 255, 20))
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        if self._is_selecting:
            current_rect = self._current_rect()
            if not current_rect.isNull():
                painter.setPen(QPen(QColor(0, 174, 255), 2))
                painter.fillRect(current_rect, QColor(0, 174, 255, 60))
                painter.drawRect(current_rect)

    def closeEvent(self, event) -> None:  # noqa: D401 - Qt override
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()
        return super().closeEvent(event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _configure_window(self) -> None:
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        geometry = self._screen_geometry()
        self.setGeometry(geometry)

    def _screen_geometry(self) -> QRect:
        if self.parentWidget():
            screen = self.parentWidget().screen()
        else:
            screen = QGuiApplication.primaryScreen()
        return screen.geometry() if screen else self._virtual_geometry()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch()

        self._prompt_label = QLabel(self._prompt_text, self)
        self._prompt_label.setStyleSheet(
            "color: white; font-size: 20px; background-color: rgba(0, 0, 0, 120);"
            "padding: 8px 16px; border-radius: 6px;"
        )
        layout.addWidget(self._prompt_label, alignment=Qt.AlignLeft | Qt.AlignTop)

    def _current_rect(self) -> QRect:
        if self._begin is None or self._end is None:
            return QRect()
        return QRect(self._begin, self._end).normalized()

    def _to_global(self, rect: QRect) -> QRect:
        if rect.isNull():
            return rect
        global_top_left = self.mapToGlobal(rect.topLeft())
        global_bottom_right = self.mapToGlobal(rect.bottomRight())
        return QRect(global_top_left, global_bottom_right).normalized()

    @staticmethod
    def _virtual_geometry() -> QRect:
        geometry = QRect()
        for screen in QGuiApplication.screens():
            geometry = geometry.united(screen.geometry())
        return geometry

    def _store_result(self, rect: QRect) -> None:
        self._result = rect
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()
