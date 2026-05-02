from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (
    QMouseEvent,
    QMovie,
    QPixmap,
)
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .color_util import color_for
from .speech_bubble import SpeechBubble


def _strip_win11_chrome(hwnd: int) -> None:
    """Disable Windows 11 Mica backdrop, rounded corners, and border color
    on the given top-level HWND. Qt's translucent window paints under DWM's
    chrome, so we have to ask DWM to skip drawing it.
    """
    try:
        dwm = ctypes.windll.dwmapi
    except (AttributeError, OSError):
        return
    h = ctypes.c_void_p(hwnd)

    # 38 = DWMWA_SYSTEMBACKDROP_TYPE, 1 = DWMSBT_NONE (no Mica/Acrylic)
    val = ctypes.c_int(1)
    dwm.DwmSetWindowAttribute(h, 38, ctypes.byref(val), ctypes.sizeof(val))

    # 33 = DWMWA_WINDOW_CORNER_PREFERENCE, 1 = DWMWCP_DONOTROUND
    val = ctypes.c_int(1)
    dwm.DwmSetWindowAttribute(h, 33, ctypes.byref(val), ctypes.sizeof(val))

    # 34 = DWMWA_BORDER_COLOR, 0xFFFFFFFE = DWMWA_COLOR_NONE (no visible border)
    val = ctypes.c_uint(0xFFFFFFFE)
    dwm.DwmSetWindowAttribute(h, 34, ctypes.byref(val), ctypes.sizeof(val))

GIF_SIZE = 96
LABEL_HEIGHT = 18
WINDOW_PADDING = 6
TOTAL_WIDTH = GIF_SIZE + WINDOW_PADDING * 2
TOTAL_HEIGHT = GIF_SIZE + LABEL_HEIGHT + WINDOW_PADDING * 2 + 4


class GifWindow(QWidget):
    dismissed = Signal(str)  # session_id
    moved = Signal(str)  # session_id (for persisting position)

    def __init__(
        self,
        session_id: str,
        cwd: str,
        gif_resolver: Callable[[str], Path | None],
        bubble_trigger: str = "hover_only",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sid = session_id
        self._cwd = cwd
        self._resolver = gif_resolver
        self._bubble_trigger = bubble_trigger
        self._current_category: str | None = None
        self._is_idle = False
        self._last_event_at = time.monotonic()
        self._movie: QMovie | None = None
        self._drag_origin: QPoint | None = None

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(QSize(TOTAL_WIDTH, TOTAL_HEIGHT))
        self.setMouseTracking(True)
        # Hard-kill any inherited default background. Qt's translucent attr
        # alone doesn't always defeat child-widget native fills on Windows.
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            WINDOW_PADDING, WINDOW_PADDING, WINDOW_PADDING, WINDOW_PADDING
        )
        layout.setSpacing(2)

        self._gif_label = QLabel(self)
        self._gif_label.setFixedSize(QSize(GIF_SIZE, GIF_SIZE))
        self._gif_label.setAlignment(Qt.AlignCenter)
        self._gif_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._gif_label, 0, Qt.AlignHCenter)

        self._cwd_label = QLabel(self)
        self._cwd_label.setFixedHeight(LABEL_HEIGHT)
        self._cwd_label.setAlignment(Qt.AlignCenter)
        r, g, b = color_for(cwd)
        text = self._format_cwd(cwd)
        self._cwd_label.setText(text)
        self._cwd_label.setStyleSheet(
            f"color: rgba({r},{g},{b},255);"
            "font-size: 10px; font-weight: 600;"
            "background: rgba(20,22,28,160); border-radius: 6px;"
            "padding: 1px 6px;"
        )
        layout.addWidget(self._cwd_label, 0, Qt.AlignHCenter)

        # X button overlay (hidden by default, shown on hover)
        self._close_btn = QPushButton("✕", self)
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.move(TOTAL_WIDTH - 22, 4)
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(
            "QPushButton {"
            " color: white; background: rgba(0,0,0,160);"
            " border-radius: 9px; font-size: 11px; padding: 0;"
            "}"
            "QPushButton:hover { background: rgba(220,60,60,220); }"
        )
        self._close_btn.hide()
        self._close_btn.clicked.connect(self._on_close_clicked)

        self._bubble = SpeechBubble()

    @staticmethod
    def _format_cwd(cwd: str) -> str:
        if not cwd:
            return "(no cwd)"
        base = os.path.basename(os.path.normpath(cwd))
        if not base:
            base = cwd
        return base[:18]

    @property
    def session_id(self) -> str:
        return self._sid

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    @property
    def last_event_at(self) -> float:
        return self._last_event_at

    @property
    def current_category(self) -> str | None:
        return self._current_category

    def set_bubble_trigger(self, trigger: str) -> None:
        self._bubble_trigger = trigger
        if trigger == "always":
            self._bubble.show_persistent()
            self._bubble.position_above(self)
        elif trigger == "off":
            self._bubble.hide()

    def update_state(
        self,
        category: str | None,
        bubble_text: str,
        is_idle: bool,
    ) -> None:
        self._last_event_at = time.monotonic()
        if category and category != self._current_category:
            self._set_gif(category)
            self._current_category = category
        self._is_idle = is_idle
        # Only overwrite the bubble when the new event actually has text.
        # Events like PostToolUse / SubagentStop carry empty bubble_text and
        # should leave the previous meaningful message in place.
        text_changed = bool(bubble_text)
        if text_changed:
            self._bubble.set_text(bubble_text)
        if self._bubble_trigger == "always":
            self._bubble.show_persistent()
            self._bubble.position_above(self)
        elif self._bubble_trigger == "event_burst" and text_changed:
            self._bubble.position_above(self)
            self._bubble.show_burst()
        elif self._bubble_trigger == "hover_only":
            # Refresh visibility based on hover state; do NOT clear text.
            if self.underMouse():
                self._bubble.position_above(self)
                self._bubble.show_persistent()
            else:
                self._bubble.hide()

    def _set_gif(self, category: str) -> None:
        path = self._resolver(category)
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None
        self._gif_label.clear()
        if path is None or not Path(path).exists():
            self._gif_label.setText(category.upper())
            return
        suffix = Path(path).suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._gif_label.setText(category.upper())
                return
            scaled = pixmap.scaled(
                QSize(GIF_SIZE, GIF_SIZE),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._gif_label.setPixmap(scaled)
            return
        movie = QMovie(str(path))
        movie.setScaledSize(QSize(GIF_SIZE, GIF_SIZE))
        self._gif_label.setMovie(movie)
        movie.start()
        self._movie = movie

    def _on_close_clicked(self) -> None:
        self.dismissed.emit(self._sid)

    # ---- mouse / hover ----------------------------------------------------

    def enterEvent(self, event) -> None:  # noqa: N802
        self._close_btn.show()
        if self._bubble_trigger == "hover_only":
            self._bubble.position_above(self)
            self._bubble.show_persistent()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._close_btn.hide()
        if self._bubble_trigger == "hover_only":
            self._bubble.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_origin
            self.move(new_pos)
            self._bubble.position_above(self)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_origin is not None:
            self._drag_origin = None
            self.moved.emit(self._sid)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._movie is not None:
            self._movie.stop()
        self._bubble.hide()
        self._bubble.deleteLater()
        super().closeEvent(event)

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        if self._bubble.isVisible():
            self._bubble.position_above(self)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if sys.platform == "win32" and not getattr(self, "_chrome_stripped", False):
            try:
                _strip_win11_chrome(int(self.winId()))
                self._chrome_stripped = True
            except Exception:  # pragma: no cover
                pass
