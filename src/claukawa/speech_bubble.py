from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

_BG = QColor(28, 30, 36, 235)
_BORDER = QColor(255, 255, 255, 50)
_TEXT = QColor(240, 242, 248)
_RADIUS = 8
_PADDING = 8
_TAIL = 6


class SpeechBubble(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._label = QLabel(self)
        self._label.setStyleSheet(
            f"color: rgba({_TEXT.red()},{_TEXT.green()},{_TEXT.blue()},255);"
            "font-size: 11px; font-weight: 500;"
        )
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_PADDING, _PADDING, _PADDING, _PADDING + _TAIL)
        layout.addWidget(self._label)
        self._burst_timer = QTimer(self)
        self._burst_timer.setSingleShot(True)
        self._burst_timer.timeout.connect(self.hide)

    def set_text(self, text: str) -> None:
        self._label.setText(text or "")
        self._label.adjustSize()
        self.adjustSize()

    def show_burst(self, ms: int = 3000) -> None:
        self.show()
        self._burst_timer.start(ms)

    def show_persistent(self) -> None:
        self._burst_timer.stop()
        self.show()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if sys.platform == "darwin" and not getattr(self, "_macos_pinned", False):
            try:
                from .gif_window import _pin_macos_panel

                _pin_macos_panel(int(self.winId()))
                self._macos_pinned = True
            except Exception:  # pragma: no cover
                pass

    def position_above(self, anchor: QWidget) -> None:
        if not anchor.isVisible():
            return
        ag = anchor.frameGeometry()
        bw, bh = self.width(), self.height()
        x = ag.center().x() - bw // 2
        y = ag.top() - bh - 4
        self.move(max(0, x), max(0, y))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        body = self.rect().adjusted(0, 0, -1, -_TAIL - 1)
        path = QPainterPath()
        path.addRoundedRect(body, _RADIUS, _RADIUS)
        # tail (small triangle pointing down)
        cx = self.width() // 2
        bottom = body.bottom()
        path.moveTo(cx - 5, bottom)
        path.lineTo(cx, bottom + _TAIL)
        path.lineTo(cx + 5, bottom)
        path.closeSubpath()
        painter.fillPath(path, _BG)
        pen = QPen(_BORDER, 1)
        painter.setPen(pen)
        painter.drawPath(path)
