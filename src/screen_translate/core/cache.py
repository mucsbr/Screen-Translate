"""Translation text cache to avoid duplicate OCR/translation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CacheEntry:
    text: str
    timestamp: float


class TranslationCache:
    """Store last translated text to prevent duplicate translations."""

    def __init__(self, ttl_seconds: float = 5.0) -> None:
        self._ttl = ttl_seconds
        self._entry: Optional[CacheEntry] = None

    def should_translate(self, text: str) -> bool:
        import re
        normalized = text.strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        if not normalized:
            return False

        current_time = time.monotonic()
        if self._entry is None:
            self._entry = CacheEntry(text=normalized, timestamp=current_time)
            return True

        if (
            normalized != self._entry.text
            or current_time - self._entry.timestamp > self._ttl
        ):
            self._entry = CacheEntry(text=normalized, timestamp=current_time)
            return True

        return False
