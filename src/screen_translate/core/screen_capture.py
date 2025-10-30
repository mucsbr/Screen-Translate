"""Screen capture utilities based on mss."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import mss
import numpy as np
from PySide6.QtCore import QRect


@dataclass
class CaptureResult:
    """Container for captured frame data."""

    image: np.ndarray
    bbox: QRect


class ScreenCapturer:
    """Capture a region of the screen into a numpy array."""

    def __init__(self) -> None:
        self._sct: Optional[mss.mss] = None

    def start(self) -> None:
        if self._sct is None:
            self._sct = mss.mss()

    def stop(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None

    def capture(self, rect: QRect) -> Optional[CaptureResult]:
        if self._sct is None:
            self.start()
        if self._sct is None or rect.isNull():
            return None

        monitor = {
            "left": rect.x(),
            "top": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
        }
        raw = self._sct.grab(monitor)
        image = np.array(raw)
        return CaptureResult(image=image, bbox=rect)
