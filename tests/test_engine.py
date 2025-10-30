"""Tests for the TranslationEngine core loop with mocked dependencies."""

from __future__ import annotations

import time
from typing import List
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QRect

from screen_translate.config.schemas import AppConfig, WindowConfig
from screen_translate.core.engine import TranslationEngine


class DummyCapturer:
    def __init__(self, frames: List[bytes]) -> None:
        self.frames = frames
        self.calls = 0

    def start(self) -> None:  # noqa: D401 - simple stub
        pass

    def stop(self) -> None:
        pass

    def capture(self, rect: QRect):
        if not self.frames:
            return None
        self.calls += 1
        return SimpleNamespace(image=self.frames.pop(0))


class DummyOCR:
    def __init__(self, texts: List[List[str]]) -> None:
        self.texts = texts

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def read_text(self, image):  # noqa: D401 - stub
        if not self.texts:
            return []
        words = self.texts.pop(0)
        return [SimpleNamespace(text=word, confidence=0.9) for word in words]


class DummyTranslator:
    def __init__(self, outputs: List[str], fail: bool = False) -> None:
        self.outputs = outputs
        self.fail = fail

    def translate(self, text: str):
        if self.fail:
            raise RuntimeError("translation failed")
        if not self.outputs:
            return None
        content = self.outputs.pop(0)
        return type("TranslationResult", (), {"text": content})


class DummyConfig:
    def __init__(self) -> None:
        self.config = AppConfig(
            translation=AppConfig().translation.model_copy(update={"interval_ms": 100}),
            source_region=WindowConfig(x=0, y=0, width=100, height=50),
            target_region=WindowConfig(x=0, y=0, width=100, height=50),
        )


@pytest.fixture
def app(qapp: QCoreApplication):
    return qapp


@pytest.fixture
def engine(monkeypatch):
    config = DummyConfig()
    engine = TranslationEngine(config_manager=config)

    engine._capturer = DummyCapturer(frames=[b"frame1"])
    engine._ocr = DummyOCR(texts=[["Hello"]])

    translator = DummyTranslator(outputs=["你好"])
    monkeypatch.setattr("screen_translate.core.engine.Translator", lambda *_: translator)

    return engine, config


def test_engine_emits_translation_ready(app, engine, monkeypatch):
    engine_instance, config = engine
    received = []

    def on_translation(text: str) -> None:
        received.append(text)
        engine_instance._stop_event.set()
        engine_instance._running.clear()

    monkeypatch.setattr(engine_instance, "_sleep_interval", lambda: None)

    engine_instance.translation_ready.connect(on_translation)
    engine_instance.start(config.config)

    while engine_instance.is_running:
        app.processEvents()
        time.sleep(0.01)

    engine_instance.stop()
    assert received == ["你好"]


def test_engine_emits_error(app, monkeypatch):
    config = DummyConfig()
    engine = TranslationEngine(config_manager=config)

    engine._capturer = DummyCapturer(frames=[b"frame1"])
    engine._ocr = DummyOCR(texts=[["text"]])

    translator = DummyTranslator(outputs=[], fail=True)
    monkeypatch.setattr("screen_translate.core.engine.Translator", lambda *_: translator)

    monkeypatch.setattr(engine, "_sleep_interval", lambda: None)

    errors = []
    engine.engine_error.connect(errors.append)
    engine.start(config.config)

    while engine.is_running:
        app.processEvents()
        time.sleep(0.01)

    engine.stop()
    assert errors
