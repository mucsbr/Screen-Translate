"""Application entry point for Screen Translate."""

from __future__ import annotations

from typing import Optional

from .config.manager import ConfigManager
from .core.controller import MainController
from .infra.logging import setup_logging
from .ui.main_window import MainWindow

try:
    from PySide6 import QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None  # type: ignore


def main(argv: Optional[list[str]] = None) -> int:
    """Launch the Screen Translate desktop application.

    Args:
        argv: Optional command line arguments (reserved for future use).

    Returns:
        Process exit code.
    """
    setup_logging()

    if QtWidgets is None:
        raise RuntimeError("PySide6 is not installed. Please install project dependencies.")

    app = QtWidgets.QApplication(argv or [])

    config_manager = ConfigManager()
    controller = MainController(config_manager=config_manager)
    main_window = MainWindow(controller=controller)
    controller.bind_main_window(main_window)
    main_window.show()

    exit_code = app.exec()
    controller.stop_translation()
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
