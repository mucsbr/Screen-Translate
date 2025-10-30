"""OCR processing using EasyOCR."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

try:
    import easyocr
except ImportError:  # pragma: no cover
    easyocr = None


@dataclass
class OCRResult:
    """Container for OCR text and confidence."""

    text: str
    confidence: float


class OCRProcessor:
    """Wrap EasyOCR reader for subtitle extraction."""

    def __init__(self, languages: Optional[List[str]] = None) -> None:
        self._languages = languages or ["ja", "en"]
        self._reader: Optional[easyocr.Reader] = None

        project_root = Path(__file__).parent.parent.parent
        self._model_dir = project_root / ".easyocr_models"
        self._model_dir.mkdir(exist_ok=True)

    def set_languages(self, languages: List[str]) -> None:
        """Update OCR languages. Requires restart() to take effect."""
        if self._reader is not None:
            raise RuntimeError("Cannot change languages while OCR is running. Call stop() first.")
        self._languages = languages

    def start(self) -> None:
        if easyocr is None:
            raise RuntimeError("EasyOCR 未安装，请先安装依赖 easyocr。")
        if self._reader is None:
            self._reader = easyocr.Reader(
                self._languages,
                model_storage_directory=str(self._model_dir),
                download_enabled=True,
                detector=True,
                recognizer=True
            )

    def stop(self) -> None:
        self._reader = None

    def read_text(self, image: np.ndarray) -> List[OCRResult]:
        if self._reader is None:
            self.start()
        if self._reader is None:
            return []
        results = self._reader.readtext(image)
        return [OCRResult(text=text, confidence=conf) for _, text, conf in results]
