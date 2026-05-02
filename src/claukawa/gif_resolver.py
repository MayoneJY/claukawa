from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

from . import platform_paths

_log = logging.getLogger(__name__)

CATEGORIES = (
    "session_start",
    "thinking",
    "editing",
    "reading",
    "bashing",
    "web",
    "subagent",
    "mcp",
    "waiting_input",
    "idle",
    "compacting",
)


def _bundled_default_dir() -> Path:
    """Return path to the bundled default GIF directory.

    Works both in source layout and PyInstaller --onefile (sys._MEIPASS).
    """
    base_meipass = getattr(sys, "_MEIPASS", None)
    if base_meipass:
        candidate = Path(base_meipass) / "claukawa" / "assets" / "gifs" / "default"
        if candidate.exists():
            return candidate
        candidate = Path(base_meipass) / "assets" / "gifs" / "default"
        if candidate.exists():
            return candidate
    here = Path(__file__).resolve().parent
    return here / "assets" / "gifs" / "default"


# Search order: PNG (full RGBA, preferred) before GIF (palette, animated).
_EXTENSIONS = ("png", "gif")


def ensure_user_gifs_seeded() -> None:
    """Copy bundled defaults to the user data dir on first run (idempotent).

    Existing files are not overwritten so user customizations survive upgrades.
    """
    dst_dir = platform_paths.gifs_path()
    src_dir = _bundled_default_dir()
    if not src_dir.exists():
        _log.warning("bundled asset dir not found: %s", src_dir)
        return
    for name in CATEGORIES:
        # Already seeded for this category?
        if any((dst_dir / f"{name}.{ext}").exists() for ext in _EXTENSIONS):
            continue
        for ext in _EXTENSIONS:
            src = src_dir / f"{name}.{ext}"
            if src.exists():
                try:
                    shutil.copy2(src, dst_dir / f"{name}.{ext}")
                except OSError as exc:
                    _log.warning("failed to seed %s.%s: %s", name, ext, exc)
                break


def resolve(category: str, overrides: dict[str, str] | None = None) -> Path | None:
    """Resolve an asset path for the given category, honoring user overrides.

    Prefers PNG (no palette quantization) over GIF.
    """
    if not category:
        return None
    overrides = overrides or {}
    override = overrides.get(category)
    if override:
        p = Path(override)
        if p.exists():
            return p
        _log.warning("override asset missing for %s: %s", category, p)
    user_dir = platform_paths.gifs_path()
    for ext in _EXTENSIONS:
        candidate = user_dir / f"{category}.{ext}"
        if candidate.exists():
            return candidate
    bundled_dir = _bundled_default_dir()
    for ext in _EXTENSIONS:
        candidate = bundled_dir / f"{category}.{ext}"
        if candidate.exists():
            return candidate
    return None
