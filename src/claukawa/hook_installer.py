from __future__ import annotations

import datetime as _dt
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from . import HOOK_MARKER, platform_paths

_log = logging.getLogger(__name__)

HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "Stop",
    "SubagentStop",
    "SessionEnd",
    "PreCompact",
)

HOOK_COMMAND = (
    'curl -s -X POST -H "Content-Type: application/json" '
    '--data-binary @- http://127.0.0.1:17135/event'
)


def _claukawa_entry() -> dict[str, Any]:
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": HOOK_COMMAND,
                "timeout": 5,
            }
        ],
    }


def _is_claukawa_entry(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    for h in hooks:
        if isinstance(h, dict):
            cmd = h.get("command")
            if isinstance(cmd, str) and HOOK_MARKER in cmd:
                return True
    return False


def is_installed(settings_path: Path | None = None) -> bool:
    path = settings_path or platform_paths.claude_settings_path()
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    hooks_section = data.get("hooks")
    if not isinstance(hooks_section, dict):
        return False
    for event in HOOK_EVENTS:
        groups = hooks_section.get(event)
        if not isinstance(groups, list):
            return False
        if not any(_is_claukawa_entry(g) for g in groups):
            return False
    return True


def install(settings_path: Path | None = None) -> Path | None:
    """Idempotent install. Returns backup path (or None if no backup needed)."""
    path = settings_path or platform_paths.claude_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.error("settings.json unreadable: %s", exc)
            raise
        backup = _backup(path)
    else:
        data = {}
        backup = None

    if not isinstance(data, dict):
        raise ValueError("settings.json root is not an object")
    hooks_section = data.setdefault("hooks", {})
    if not isinstance(hooks_section, dict):
        raise ValueError("settings.json 'hooks' is not an object")

    changed = False
    for event in HOOK_EVENTS:
        groups = hooks_section.get(event)
        if not isinstance(groups, list):
            groups = []
            hooks_section[event] = groups
        if not any(_is_claukawa_entry(g) for g in groups):
            groups.append(_claukawa_entry())
            changed = True

    if changed:
        _atomic_write(path, data)
    return backup


def uninstall(settings_path: Path | None = None) -> Path | None:
    path = settings_path or platform_paths.claude_settings_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.error("settings.json unreadable on uninstall: %s", exc)
        raise
    backup = _backup(path)

    hooks_section = data.get("hooks")
    if not isinstance(hooks_section, dict):
        return backup

    for event in list(hooks_section.keys()):
        groups = hooks_section.get(event)
        if not isinstance(groups, list):
            continue
        kept = [g for g in groups if not _is_claukawa_entry(g)]
        if kept:
            hooks_section[event] = kept
        else:
            del hooks_section[event]

    if not hooks_section:
        del data["hooks"]
    _atomic_write(path, data)
    return backup


def _backup(path: Path) -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = platform_paths.claude_settings_backup_path(ts)
    shutil.copy2(path, dst)
    return dst


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)
