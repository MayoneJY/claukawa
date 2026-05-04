from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication

from . import MAX_SLOTS
from . import gif_resolver
from .gif_window import GifWindow, TOTAL_HEIGHT, TOTAL_WIDTH
from .settings_store import SettingsStore

_log = logging.getLogger(__name__)

SLOT_GAP = 12
SCREEN_MARGIN = 24


class WindowManager(QObject):
    settings_requested = Signal()

    def __init__(self, settings: SettingsStore, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._windows: dict[str, GifWindow] = {}
        self._slot_assignments: dict[str, int] = {}  # session_id -> slot index

    @property
    def windows(self) -> dict[str, GifWindow]:
        return self._windows

    def update_or_create(
        self,
        session_id: str,
        category: str | None,
        bubble_text: str,
        is_idle: bool,
        payload: dict[str, Any],
    ) -> None:
        win = self._windows.get(session_id)
        if win is None:
            # Don't pop a window into existence just to display an idle/end
            # state — if the user already dismissed it (or it never existed),
            # let Stop/SessionEnd pass silently. Reviving only happens on
            # genuinely new activity.
            if is_idle:
                return
            if not self._make_room():
                _log.info("slot full + reject policy: dropping sid=%s", session_id)
                return
            win = self._create(session_id, payload)
        # If this is a brand-new sid and the very first event has no category,
        # default to a sensible starting GIF so the window has something to show.
        effective_category = category
        if win.current_category is None and effective_category is None:
            effective_category = "session_start"
        win.update_state(effective_category, bubble_text, is_idle)

    def dismiss(self, session_id: str) -> None:
        win = self._windows.pop(session_id, None)
        self._slot_assignments.pop(session_id, None)
        if win is not None:
            win.close()
            win.deleteLater()

    def shutdown(self) -> None:
        for sid in list(self._windows.keys()):
            self.dismiss(sid)

    # ---- internals --------------------------------------------------------

    def _make_room(self) -> bool:
        if len(self._windows) < MAX_SLOTS:
            return True
        policy = self._settings.get("slot_policy", default="idle_only")
        if policy == "reject":
            return False
        if policy == "idle_only":
            target = self._oldest_idle()
            if target is None:
                return False
            self.dismiss(target)
            return True
        # lru
        target = self._oldest_lru()
        if target is None:
            return False
        self.dismiss(target)
        return True

    def _oldest_idle(self) -> str | None:
        idle = [
            (w.last_event_at, sid) for sid, w in self._windows.items() if w.is_idle
        ]
        if not idle:
            return None
        idle.sort()
        return idle[0][1]

    def _oldest_lru(self) -> str | None:
        if not self._windows:
            return None
        items = sorted(self._windows.items(), key=lambda kv: kv[1].last_event_at)
        return items[0][0]

    def _next_free_slot(self) -> int:
        used = set(self._slot_assignments.values())
        for i in range(MAX_SLOTS):
            if i not in used:
                return i
        return 0  # fallback (shouldn't happen because _make_room enforces capacity)

    def _slot_default_position(self, slot: int) -> tuple[int, int]:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return (100 + slot * (TOTAL_WIDTH + SLOT_GAP), 100)
        geom = screen.availableGeometry()
        right = geom.right() - SCREEN_MARGIN
        bottom = geom.bottom() - SCREEN_MARGIN
        x = right - TOTAL_WIDTH - slot * (TOTAL_WIDTH + SLOT_GAP)
        y = bottom - TOTAL_HEIGHT
        return (x, y)

    def _resolve_position(self, slot: int) -> tuple[int, int]:
        positions = self._settings.get("window_positions", default={}) or {}
        saved = positions.get(str(slot))
        if isinstance(saved, list) and len(saved) == 2:
            try:
                return (int(saved[0]), int(saved[1]))
            except (TypeError, ValueError):
                pass
        return self._slot_default_position(slot)

    def _create(self, session_id: str, payload: dict[str, Any]) -> GifWindow:
        slot = self._next_free_slot()
        self._slot_assignments[session_id] = slot
        cwd = payload.get("cwd") or ""
        overrides = self._settings.get("gif_overrides", default={}) or {}

        def _resolver(cat: str):
            return gif_resolver.resolve(cat, overrides)

        bubble_trigger = self._settings.get("bubble", "trigger", default="hover_only")
        win = GifWindow(
            session_id=session_id,
            cwd=cwd,
            gif_resolver=_resolver,
            bubble_trigger=bubble_trigger,
        )
        x, y = self._resolve_position(slot)
        win.move(x, y)
        win.dismissed.connect(self.dismiss)
        win.moved.connect(self._persist_position)
        win.settings_requested.connect(self.settings_requested.emit)
        win.show()
        self._windows[session_id] = win
        return win

    def _persist_position(self, session_id: str) -> None:
        win = self._windows.get(session_id)
        slot = self._slot_assignments.get(session_id)
        if win is None or slot is None:
            return
        positions = dict(self._settings.get("window_positions", default={}) or {})
        positions[str(slot)] = [win.x(), win.y()]
        self._settings.set("window_positions", value=positions)

    def apply_bubble_trigger(self, trigger: str) -> None:
        for win in self._windows.values():
            win.set_bubble_trigger(trigger)
