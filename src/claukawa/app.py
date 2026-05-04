from __future__ import annotations

import logging
import socket
import sys

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import (
    APP_NAME,
    GATEWAY_HOST,
    GATEWAY_PORT,
    autostart,
    gif_resolver,
    hook_installer,
    i18n,
    platform_paths,
)
from .dispatcher import Dispatcher
from .http_gateway import Gateway
from .i18n import t
from .language_picker import pick_language
from .settings_store import SettingsStore
from .settings_window import SettingsWindow
from .startup_notice import StartupNotice
from .tray import Tray
from .window_manager import WindowManager

_log = logging.getLogger(__name__)


def _port_available() -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind((GATEWAY_HOST, GATEWAY_PORT))
        return True
    except OSError:
        return False
    finally:
        s.close()


class ClaukawaApp:
    def __init__(self, argv: list[str]) -> None:
        self.qapp = QApplication(argv)
        self.qapp.setApplicationName(APP_NAME)
        self.qapp.setQuitOnLastWindowClosed(False)
        if sys.platform == "darwin":
            self.qapp.setAttribute(Qt.AA_DontShowIconsInMenus, False)
        self.qapp.setWindowIcon(QIcon(self._icon_path()))

        self.lock = QLockFile(str(platform_paths.lock_path()))
        self.lock.setStaleLockTime(0)
        self.settings = SettingsStore()

        # Resolve UI language BEFORE building any GUI so menus/dialogs
        # render in the user's chosen tongue from the very first frame.
        self._init_language()

        self.window_manager = WindowManager(self.settings)
        self.window_manager.settings_requested.connect(self.show_settings)
        self.dispatcher = Dispatcher(self.window_manager, self.settings)
        self.gateway = Gateway()
        self.gateway.signals.eventReceived.connect(
            self.dispatcher.on_event, Qt.QueuedConnection
        )
        self.tray = Tray()
        self.tray.open_settings_requested.connect(self.show_settings)
        self.tray.quit_requested.connect(self.quit)
        self._settings_window: SettingsWindow | None = None

    def _init_language(self) -> None:
        saved = self.settings.get("language")
        if saved in i18n.LANGUAGES:
            i18n.set_language(saved)
            return
        # First run (or wiped settings): seed with the OS locale, then ask
        # the user to confirm or change.
        i18n.set_language(i18n.detect_system_language())
        chosen = pick_language(default=i18n.current_language())
        i18n.set_language(chosen)
        self.settings.set("language", value=chosen)

    def _icon_path(self) -> str:
        from .tray import _icon_path as resolve

        return str(resolve())

    def can_run(self) -> bool:
        if not self.lock.tryLock(50):
            QMessageBox.information(
                None,
                APP_NAME,
                t("app.already_running", app=APP_NAME),
            )
            return False
        if not _port_available():
            QMessageBox.critical(
                None,
                APP_NAME,
                t("app.port_unavailable", port=GATEWAY_PORT),
            )
            return False
        return True

    def first_run_setup(self) -> None:
        gif_resolver.ensure_user_gifs_seeded()
        if self.settings.get("first_run_done"):
            return
        if not hook_installer.is_installed():
            choice = QMessageBox.question(
                None,
                t("firstrun.hook.title", app=APP_NAME),
                t("firstrun.hook.body"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if choice == QMessageBox.Yes:
                try:
                    backup = hook_installer.install()
                    if backup:
                        self.tray.show_message(
                            APP_NAME,
                            t("firstrun.hook.installed_with_backup", backup=backup.name),
                        )
                    else:
                        self.tray.show_message(APP_NAME, t("firstrun.hook.installed"))
                except Exception as exc:
                    _log.exception("first-run install failed")
                    QMessageBox.warning(
                        None,
                        APP_NAME,
                        t("firstrun.hook.install_failed", error=exc),
                    )
        self.settings.set("first_run_done", value=True)
        if self.settings.get("auto_start") and autostart.is_supported():
            try:
                autostart.enable()
            except Exception:
                _log.warning("autostart enable failed", exc_info=True)

    def show_settings(self) -> None:
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(
                self.settings,
                on_bubble_trigger_changed=self.window_manager.apply_bubble_trigger,
            )
            self._settings_window.quit_requested.connect(self.quit)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def run(self) -> int:
        try:
            self.gateway.start()
        except OSError as exc:
            _log.error("gateway start failed: %s", exc)
            QMessageBox.critical(
                None,
                APP_NAME,
                t("app.gateway_failed", port=GATEWAY_PORT, error=exc),
            )
            return 2
        self.first_run_setup()
        self._startup_notice = StartupNotice()
        self._startup_notice.show_centered()
        return self.qapp.exec()

    def quit(self) -> None:
        try:
            self.gateway.stop()
        finally:
            self.window_manager.shutdown()
            self.tray.hide()
            self.qapp.quit()
