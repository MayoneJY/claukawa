from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, QTimer, Slot

from .event_mapping import classify, truncate
from .settings_store import SettingsStore
from .window_manager import WindowManager

_log = logging.getLogger(__name__)

# If a PreToolUse arrives in a permission-gated mode and the matching
# PostToolUse doesn't show up within this many milliseconds, we assume the
# user is staring at a permission popup and flip the GIF to waiting_input.
_PERMISSION_WATCHDOG_MS = 1500


class Dispatcher(QObject):
    def __init__(
        self,
        window_manager: WindowManager,
        settings: SettingsStore,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._wm = window_manager
        self._settings = settings
        # tool_use_id -> watchdog QTimer
        self._pending: dict[str, QTimer] = {}

    @Slot(dict)
    def on_event(self, payload: dict[str, Any]) -> None:
        sid = payload.get("session_id") or "unknown"
        event = payload.get("hook_event_name") or ""
        cls = classify(payload)
        max_chars = int(self._settings.get("bubble", "max_chars", default=60))
        bubble = truncate(cls.bubble_text, max_chars)
        try:
            self._wm.update_or_create(
                session_id=sid,
                category=cls.category,
                bubble_text=bubble,
                is_idle=cls.is_idle,
                payload=payload,
            )
        except Exception:  # pragma: no cover
            _log.exception("dispatcher failed for sid=%s", sid)

        # Permission-popup watchdog: arm on Pre, resolve on Post.
        if event == "PreToolUse":
            self._maybe_arm_watchdog(sid, payload, cls.category, bubble, max_chars)
        elif event == "PostToolUse":
            tid = payload.get("tool_use_id")
            if tid:
                self._resolve_pending(tid)

    def _maybe_arm_watchdog(
        self,
        sid: str,
        payload: dict[str, Any],
        original_category: str | None,
        original_bubble: str,
        max_chars: int,
    ) -> None:
        pmode = payload.get("permission_mode") or ""
        # Bypass mode auto-approves everything — no popup expected.
        if pmode == "bypassPermissions":
            return
        # Don't double-arm for tool calls happening inside a subagent: the
        # parent Agent call already gets a normal classification.
        if payload.get("agent_id"):
            return
        tid = payload.get("tool_use_id")
        if not tid or tid in self._pending:
            return
        tool_name = payload.get("tool_name") or "tool"
        wait_bubble = truncate(f"권한 대기: {tool_name}", max_chars)

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(_PERMISSION_WATCHDOG_MS)

        entry: dict[str, Any] = {
            "timer": timer,
            "sid": sid,
            "payload": payload,
            "original_category": original_category,
            "original_bubble": original_bubble,
            "fired": False,
        }
        self._pending[tid] = entry

        def fire(_tid: str = tid, _sid: str = sid, _bubble: str = wait_bubble) -> None:
            e = self._pending.get(_tid)
            if e is None:
                return
            e["fired"] = True
            try:
                self._wm.update_or_create(
                    session_id=_sid,
                    category="waiting_input",
                    bubble_text=_bubble,
                    is_idle=False,
                    payload=e["payload"],
                )
            except Exception:  # pragma: no cover
                _log.exception("permission watchdog failed for tid=%s", _tid)

        timer.timeout.connect(fire)
        timer.start()

    def _resolve_pending(self, tool_use_id: str) -> None:
        """Called on PostToolUse. If the watchdog had already promoted the
        window to waiting_input, swing it back to the original tool category
        so the user sees the action complete instead of the GIF freezing on
        the question-mark Chiikawa.
        """
        entry = self._pending.pop(tool_use_id, None)
        if entry is None:
            return
        timer = entry["timer"]
        timer.stop()
        timer.deleteLater()
        if not entry["fired"]:
            return
        original = entry["original_category"]
        if original is None:
            return
        try:
            self._wm.update_or_create(
                session_id=entry["sid"],
                category=original,
                bubble_text=entry["original_bubble"],
                is_idle=False,
                payload=entry["payload"],
            )
        except Exception:  # pragma: no cover
            _log.exception(
                "post-permission restore failed for tid=%s", tool_use_id
            )
