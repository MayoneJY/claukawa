from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

from . import APP_AUTHOR, APP_NAME

_dirs = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)


def data_dir() -> Path:
    p = Path(_dirs.user_data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return data_dir() / "config.json"


def gifs_path() -> Path:
    p = data_dir() / "gifs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def lock_path() -> Path:
    return data_dir() / "claukawa.lock"


def claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def claude_settings_backup_path(timestamp: str) -> Path:
    return claude_settings_path().with_name(
        f"settings.json.claukawa-backup-{timestamp}"
    )
