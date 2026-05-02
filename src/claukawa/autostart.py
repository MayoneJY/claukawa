from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from . import APP_NAME

_log = logging.getLogger(__name__)
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_PLIST_LABEL = "com.claukawa"


def _exe_path() -> str:
    """Path to invoke for autostart.

    PyInstaller frozen build -> sys.executable points at the packaged exe.
    Source run -> use python + module form. (We do not autostart from source.)
    """
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" -m claukawa'


def is_supported() -> bool:
    return sys.platform in ("win32", "darwin")


def is_enabled() -> bool:
    if sys.platform == "win32":
        return _win_is_enabled()
    if sys.platform == "darwin":
        return _mac_plist_path().exists()
    return False


def enable() -> None:
    if sys.platform == "win32":
        _win_enable()
    elif sys.platform == "darwin":
        _mac_enable()
    else:
        raise RuntimeError(f"autostart not supported on {sys.platform}")


def disable() -> None:
    if sys.platform == "win32":
        _win_disable()
    elif sys.platform == "darwin":
        _mac_disable()
    else:
        raise RuntimeError(f"autostart not supported on {sys.platform}")


# ---- Windows ---------------------------------------------------------------

def _win_is_enabled() -> bool:
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False


def _win_enable() -> None:
    import winreg  # type: ignore[import-not-found]

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _exe_path())


def _win_disable() -> None:
    import winreg  # type: ignore[import-not-found]

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass


# ---- macOS -----------------------------------------------------------------

def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_PLIST_LABEL}.plist"


def _mac_enable() -> None:
    plist = _mac_plist_path()
    plist.parent.mkdir(parents=True, exist_ok=True)
    program = _exe_path()
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{_PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{program}</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><false/>
</dict>
</plist>
"""
    plist.write_text(body, encoding="utf-8")
    os.chmod(plist, 0o644)


def _mac_disable() -> None:
    p = _mac_plist_path()
    try:
        p.unlink()
    except FileNotFoundError:
        pass
