from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import APP_NAME
from .i18n import t

_log = logging.getLogger(__name__)


def _icon_path() -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        # PyInstaller bundle: datas land at <_MEIPASS>/claukawa/assets/...
        assets = Path(base) / "claukawa" / "assets"
    else:
        assets = Path(__file__).resolve().parent / "assets"

    if sys.platform == "darwin":
        tpl = assets / "tray_icon_template.png"
        if tpl.exists():
            return tpl
    ico = assets / "tray_icon.ico"
    if ico.exists():
        return ico
    return assets / "tray_icon.png"


class Tray(QObject):
    open_settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon = QIcon(str(_icon_path()))
        self._tray = QSystemTrayIcon(self._icon)
        self._tray.setToolTip(APP_NAME)
        self._build_menu()
        self._tray.show()

    def _build_menu(self) -> None:
        menu = QMenu()

        act_settings = QAction(t("tray.open_settings"), menu)
        act_settings.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_quit = QAction(t("tray.quit"), menu)
        act_quit.triggered.connect(self.quit_requested.emit)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._menu = menu  # keep reference

    def show_message(self, title: str, body: str) -> None:
        self._tray.showMessage(title, body, self._icon, 5000)

    def hide(self) -> None:
        self._tray.hide()
