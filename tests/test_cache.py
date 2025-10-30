"""Tests for translation cache behavior."""

from __future__ import annotations

import time

from screen_translate.core.cache import TranslationCache


def test_cache_prevents_duplicate_within_ttl(monkeypatch) -> None:
    cache = TranslationCache(ttl_seconds=1.0)

    assert cache.should_translate("hello") is True
    assert cache.should_translate("hello") is False

    original_monotonic = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: original_monotonic() + 2)
    assert cache.should_translate("hello") is True


def test_cache_allows_different_text() -> None:
    cache = TranslationCache(ttl_seconds=5.0)

    assert cache.should_translate("foo") is True
    assert cache.should_translate("bar") is True


def test_cache_ignores_empty_text() -> None:
    cache = TranslationCache(ttl_seconds=5.0)

    assert cache.should_translate("   ") is False
