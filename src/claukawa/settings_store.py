from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

from . import platform_paths

_log = logging.getLogger(__name__)

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "slot_policy": "idle_only",  # idle_only | lru | reject
    "auto_start": False,
    "first_run_done": False,
    "language": None,  # ko | en | None (=> picker on first run)
    "bubble": {
        "trigger": "hover_only",  # hover_only | event_burst | always | off
        "max_chars": 60,  # 30 | 60 | 100
        "detail": "context",
    },
    "gif_overrides": {},
    "window_positions": {},
}


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or platform_paths.config_path()
        self._data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def load(self) -> None:
        if not self._path.exists():
            self.save()
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("settings load failed (%s); using defaults", exc)
            return
        merged = copy.deepcopy(DEFAULTS)
        _deep_merge(merged, raw)
        self._data = merged

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, *keys: str, value: Any) -> None:
        if not keys:
            raise ValueError("at least one key required")
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value
        self.save()


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    for k, v in overlay.items():
        if (
            k in base
            and isinstance(base[k], dict)
            and isinstance(v, dict)
        ):
            _deep_merge(base[k], v)
        else:
            base[k] = v
