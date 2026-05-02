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
    platform_paths,
)
from .dispatcher import Dispatcher
from .http_gateway import Gateway
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
        self.window_manager = WindowManager(self.settings)
        self.dispatcher = Dispatcher(self.window_manager, self.settings)
        self.gateway = Gateway()
        self.gateway.signals.eventReceived.connect(
            self.dispatcher.on_event, Qt.QueuedConnection
        )
        self.tray = Tray()
        self.tray.open_settings_requested.connect(self.show_settings)
        self.tray.quit_requested.connect(self.quit)
        self._settings_window: SettingsWindow | None = None

    def _icon_path(self) -> str:
        from .tray import _icon_path as resolve

        return str(resolve())

    def can_run(self) -> bool:
        if not self.lock.tryLock(50):
            QMessageBox.information(
                None,
                APP_NAME,
                f"{APP_NAME}이(가) 이미 실행 중입니다.",
            )
            return False
        if not _port_available():
            QMessageBox.critical(
                None,
                APP_NAME,
                f"포트 {GATEWAY_PORT}을(를) 사용할 수 없습니다.\n"
                f"점유 중인 프로세스를 종료한 뒤 다시 실행해주세요.",
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
                f"{APP_NAME} — Hook 등록",
                "Claude Code 작업 상태를 표시하려면\n"
                "~/.claude/settings.json 에 hook을 등록해야 합니다.\n\n"
                "기존 hook은 보존되며, 변경 전 자동 백업됩니다.\n\n"
                "지금 등록하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if choice == QMessageBox.Yes:
                try:
                    backup = hook_installer.install()
                    if backup:
                        self.tray.show_message(
                            APP_NAME, f"Hook 등록 완료. 백업: {backup.name}"
                        )
                    else:
                        self.tray.show_message(APP_NAME, "Hook이 등록되었습니다.")
                except Exception as exc:
                    _log.exception("first-run install failed")
                    QMessageBox.warning(
                        None, APP_NAME, f"Hook 등록 실패: {exc}\n설정 → Hook 탭에서 다시 시도하세요."
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
                f"HTTP 게이트웨이 시작 실패 (포트 {GATEWAY_PORT}): {exc}",
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
