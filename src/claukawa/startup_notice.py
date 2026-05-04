from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QMouseEvent,
    QMovie,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, GATEWAY_PORT
from . import gif_resolver
from .i18n import t

_BG = QColor(28, 30, 38, 235)
_BORDER = QColor(255, 255, 255, 60)
_RADIUS = 14
_PADDING = 16
_GIF_SIZE = 96
_VISIBLE_MS = 3500
_FADE_MS = 600


class StartupNotice(QWidget):
    """Center-screen, frameless, fades out after a few seconds."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.PointingHandCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_PADDING, _PADDING, _PADDING, _PADDING)
        outer.setSpacing(0)

        row = QHBoxLayout()
        row.setSpacing(14)

        self._gif_label = QLabel()
        self._gif_label.setFixedSize(QSize(_GIF_SIZE, _GIF_SIZE))
        self._gif_label.setAlignment(Qt.AlignCenter)
        self._movie: QMovie | None = None
        asset_path = gif_resolver.resolve("session_start") or gif_resolver.resolve(
            "idle"
        )
        if asset_path is not None and Path(asset_path).exists():
            suffix = Path(asset_path).suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                pixmap = QPixmap(str(asset_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(
                        QSize(_GIF_SIZE, _GIF_SIZE),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self._gif_label.setPixmap(scaled)
            else:
                movie = QMovie(str(asset_path))
                movie.setScaledSize(QSize(_GIF_SIZE, _GIF_SIZE))
                self._gif_label.setMovie(movie)
                movie.start()
                self._movie = movie
        row.addWidget(self._gif_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title = QLabel(t("startup.title", app=APP_NAME))
        title.setStyleSheet(
            "color: #ffffff; font-size: 16px; font-weight: 700;"
        )
        text_col.addWidget(title)

        subtitle = QLabel(t("startup.subtitle", port=GATEWAY_PORT))
        subtitle.setStyleSheet("color: #c9ccd6; font-size: 11px;")
        subtitle.setWordWrap(True)
        text_col.addWidget(subtitle)

        row.addLayout(text_col)
        outer.addLayout(row)

        self.adjustSize()
        self.setMinimumWidth(360)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(_FADE_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self.close)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._begin_fade_out)

    def show_centered(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geom = screen.availableGeometry()
            self.move(
                geom.center().x() - self.width() // 2,
                geom.center().y() - self.height() // 2,
            )
        self.show()
        self._fade_in.start()
        self._dismiss_timer.start(_VISIBLE_MS)

    def _begin_fade_out(self) -> None:
        self._fade_out.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        # click anywhere to dismiss immediately
        self._dismiss_timer.stop()
        self._begin_fade_out()
        event.accept()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), _RADIUS, _RADIUS)
        painter.fillPath(path, _BG)
        painter.setPen(_BORDER)
        painter.drawPath(path)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._movie is not None:
            self._movie.stop()
        super().closeEvent(event)
