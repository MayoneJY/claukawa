from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, autostart, gif_resolver, hook_installer
from .gif_resolver import CATEGORIES
from .settings_store import SettingsStore

_log = logging.getLogger(__name__)


class SettingsWindow(QDialog):
    def __init__(
        self,
        settings: SettingsStore,
        on_bubble_trigger_changed: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._on_bubble_trigger_changed = on_bubble_trigger_changed
        self.setWindowTitle(f"{APP_NAME} 설정")
        self.setMinimumSize(520, 460)
        self._build_ui()

    def _build_ui(self) -> None:
        tabs = QTabWidget(self)
        tabs.addTab(self._tab_general(), "일반")
        tabs.addTab(self._tab_bubble(), "말풍선")
        tabs.addTab(self._tab_gif(), "GIF")
        tabs.addTab(self._tab_hook(), "Hook")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

    # ---- general tab ------------------------------------------------------
    def _tab_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        gb = QGroupBox("슬롯 정책 (5개 다 찼을 때)", w)
        v = QVBoxLayout(gb)
        self._policy_group = QButtonGroup(gb)
        for value, label in [
            ("idle_only", "idle 세션만 대체 (권장)"),
            ("lru", "가장 오래된 세션 대체 (LRU)"),
            ("reject", "새 세션 거부"),
        ]:
            rb = QRadioButton(label)
            rb.setProperty("policy", value)
            if self._settings.get("slot_policy") == value:
                rb.setChecked(True)
            self._policy_group.addButton(rb)
            v.addWidget(rb)
        self._policy_group.buttonClicked.connect(self._on_policy_changed)
        layout.addWidget(gb)

        gb2 = QGroupBox("자동 시작", w)
        v2 = QVBoxLayout(gb2)
        self._autostart_cb = QCheckBox("로그인 시 자동 시작")
        if autostart.is_supported():
            self._autostart_cb.setChecked(autostart.is_enabled())
            self._autostart_cb.toggled.connect(self._on_autostart_toggled)
        else:
            self._autostart_cb.setEnabled(False)
            self._autostart_cb.setText("로그인 시 자동 시작 (이 OS에서는 미지원)")
        v2.addWidget(self._autostart_cb)
        layout.addWidget(gb2)

        layout.addStretch(1)
        return w

    def _on_policy_changed(self) -> None:
        btn = self._policy_group.checkedButton()
        if btn is None:
            return
        self._settings.set("slot_policy", value=btn.property("policy"))

    def _on_autostart_toggled(self, checked: bool) -> None:
        try:
            if checked:
                autostart.enable()
            else:
                autostart.disable()
            self._settings.set("auto_start", value=checked)
        except Exception as exc:
            _log.exception("autostart toggle failed")
            QMessageBox.warning(self, "오류", f"자동 시작 설정 실패: {exc}")
            self._autostart_cb.blockSignals(True)
            self._autostart_cb.setChecked(autostart.is_enabled())
            self._autostart_cb.blockSignals(False)

    # ---- bubble tab -------------------------------------------------------
    def _tab_bubble(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        gb = QGroupBox("표시 트리거", w)
        v = QVBoxLayout(gb)
        self._trigger_group = QButtonGroup(gb)
        for value, label in [
            ("hover_only", "마우스를 올렸을 때만 (기본)"),
            ("event_burst", "이벤트 발생 시 3초 표시 후 숨김"),
            ("always", "항상 표시"),
            ("off", "표시 안 함"),
        ]:
            rb = QRadioButton(label)
            rb.setProperty("trigger", value)
            if self._settings.get("bubble", "trigger") == value:
                rb.setChecked(True)
            self._trigger_group.addButton(rb)
            v.addWidget(rb)
        self._trigger_group.buttonClicked.connect(self._on_trigger_changed)
        layout.addWidget(gb)

        gb2 = QGroupBox("글자 수 제한", w)
        form = QFormLayout(gb2)
        self._max_chars = QComboBox()
        for n in (30, 60, 100):
            self._max_chars.addItem(f"{n}자", n)
        cur = int(self._settings.get("bubble", "max_chars", default=60))
        idx = self._max_chars.findData(cur)
        if idx >= 0:
            self._max_chars.setCurrentIndex(idx)
        self._max_chars.currentIndexChanged.connect(self._on_maxchars_changed)
        form.addRow("최대 길이", self._max_chars)
        layout.addWidget(gb2)

        layout.addStretch(1)
        return w

    def _on_trigger_changed(self) -> None:
        btn = self._trigger_group.checkedButton()
        if btn is None:
            return
        value = btn.property("trigger")
        self._settings.set("bubble", "trigger", value=value)
        if self._on_bubble_trigger_changed:
            self._on_bubble_trigger_changed(value)

    def _on_maxchars_changed(self, _idx: int) -> None:
        self._settings.set(
            "bubble", "max_chars", value=int(self._max_chars.currentData())
        )

    # ---- gif tab ----------------------------------------------------------
    def _tab_gif(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        grid = QGridLayout()
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)

        self._gif_movies: list[QMovie] = []  # keep refs alive
        self._gif_path_labels: dict[str, QLabel] = {}
        for row, cat in enumerate(CATEGORIES):
            preview = QLabel()
            preview.setFixedSize(40, 40)
            preview.setStyleSheet("background: #1a1a1f; border-radius: 4px;")
            path = gif_resolver.resolve(
                cat, self._settings.get("gif_overrides", default={}) or {}
            )
            if path and Path(path).exists():
                suffix = path.suffix.lower()
                if suffix in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                    pix = QPixmap(str(path)).scaled(
                        preview.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    preview.setPixmap(pix)
                else:
                    movie = QMovie(str(path))
                    movie.setScaledSize(preview.size())
                    preview.setMovie(movie)
                    movie.start()
                    self._gif_movies.append(movie)
            grid.addWidget(preview, row, 0)

            label = QLabel(cat)
            label.setMinimumWidth(110)
            grid.addWidget(label, row, 1)

            path_label = QLabel(self._format_path(path))
            path_label.setStyleSheet("color: #888; font-size: 10px;")
            self._gif_path_labels[cat] = path_label
            grid.addWidget(path_label, row, 2)

            btn = QPushButton("변경…")
            btn.clicked.connect(lambda _, c=cat: self._pick_gif(c))
            grid.addWidget(btn, row, 3)

            reset = QPushButton("기본값")
            reset.clicked.connect(lambda _, c=cat: self._reset_gif(c))
            grid.addWidget(reset, row, 4)

        layout.addStretch(1)
        return w

    @staticmethod
    def _format_path(p: Path | None) -> str:
        if p is None:
            return "(GIF 없음)"
        return str(p)

    def _pick_gif(self, category: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"{category} 이미지 선택",
            "",
            "Images (*.png *.gif *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        overrides = dict(self._settings.get("gif_overrides", default={}) or {})
        overrides[category] = path
        self._settings.set("gif_overrides", value=overrides)
        self._gif_path_labels[category].setText(path)

    def _reset_gif(self, category: str) -> None:
        overrides = dict(self._settings.get("gif_overrides", default={}) or {})
        if category in overrides:
            del overrides[category]
            self._settings.set("gif_overrides", value=overrides)
        path = gif_resolver.resolve(category)
        self._gif_path_labels[category].setText(self._format_path(path))

    # ---- hook tab ---------------------------------------------------------
    def _tab_hook(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self._hook_status = QLabel()
        layout.addWidget(self._hook_status)

        row = QHBoxLayout()
        btn_install = QPushButton("Hook 등록")
        btn_install.clicked.connect(self._on_install_hooks)
        btn_uninstall = QPushButton("Hook 해제")
        btn_uninstall.clicked.connect(self._on_uninstall_hooks)
        row.addWidget(btn_install)
        row.addWidget(btn_uninstall)
        row.addStretch(1)
        layout.addLayout(row)

        info = QLabel(
            "Claude Code의 ~/.claude/settings.json에 Claukawa 전용 hook 항목을\n"
            "별도 matcher 그룹으로 추가합니다. 기존 hook은 보존됩니다.\n"
            "변경 전 자동으로 백업 파일이 생성됩니다."
        )
        info.setStyleSheet("color: #888;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch(1)
        self._refresh_hook_status()
        return w

    def _refresh_hook_status(self) -> None:
        installed = hook_installer.is_installed()
        self._hook_status.setText(
            "현재 상태: ✅ 등록됨" if installed else "현재 상태: ⛔ 미등록"
        )

    def _on_install_hooks(self) -> None:
        try:
            backup = hook_installer.install()
            msg = "Hook이 등록되었습니다."
            if backup:
                msg += f"\n백업: {backup}"
            QMessageBox.information(self, "완료", msg)
        except Exception as exc:
            _log.exception("install failed")
            QMessageBox.critical(self, "오류", f"등록 실패: {exc}")
        self._refresh_hook_status()

    def _on_uninstall_hooks(self) -> None:
        try:
            backup = hook_installer.uninstall()
            msg = "Hook이 해제되었습니다."
            if backup:
                msg += f"\n백업: {backup}"
            QMessageBox.information(self, "완료", msg)
        except Exception as exc:
            _log.exception("uninstall failed")
            QMessageBox.critical(self, "오류", f"해제 실패: {exc}")
        self._refresh_hook_status()
