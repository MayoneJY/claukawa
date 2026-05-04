from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
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

from . import APP_NAME, autostart, gif_resolver, hook_installer, i18n
from .gif_resolver import CATEGORIES
from .i18n import t
from .settings_store import SettingsStore

_log = logging.getLogger(__name__)


class SettingsWindow(QDialog):
    quit_requested = Signal()

    def __init__(
        self,
        settings: SettingsStore,
        on_bubble_trigger_changed: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._on_bubble_trigger_changed = on_bubble_trigger_changed
        self.setWindowTitle(t("settings.title", app=APP_NAME))
        self.setMinimumSize(520, 460)
        self._build_ui()

    def _build_ui(self) -> None:
        tabs = QTabWidget(self)
        tabs.addTab(self._tab_general(), t("settings.tab.general"))
        tabs.addTab(self._tab_bubble(), t("settings.tab.bubble"))
        tabs.addTab(self._tab_gif(), t("settings.tab.gif"))
        tabs.addTab(self._tab_hook(), t("settings.tab.hook"))

        # Bottom action row: Quit on the left, Close on the right.
        actions = QHBoxLayout()
        btn_quit = QPushButton(t("settings.quit"))
        btn_quit.setStyleSheet(
            "QPushButton {"
            " color: #ffffff; background: rgba(180, 60, 60, 220);"
            " padding: 6px 14px; border-radius: 6px; font-weight: 600;"
            "}"
            "QPushButton:hover { background: rgba(210, 70, 70, 240); }"
        )
        btn_quit.clicked.connect(self._on_quit_clicked)
        actions.addWidget(btn_quit)
        actions.addStretch(1)
        btn_close = QPushButton(t("settings.close"))
        btn_close.clicked.connect(self.close)
        actions.addWidget(btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addLayout(actions)

    def _on_quit_clicked(self) -> None:
        confirm = QMessageBox.question(
            self,
            t("settings.quit.confirm_title"),
            t("settings.quit.confirm_body"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.quit_requested.emit()
            self.close()

    # ---- general tab ------------------------------------------------------
    def _tab_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        gb = QGroupBox(t("settings.policy.group"), w)
        v = QVBoxLayout(gb)
        self._policy_group = QButtonGroup(gb)
        for value, label_key in [
            ("idle_only", "settings.policy.idle_only"),
            ("lru", "settings.policy.lru"),
            ("reject", "settings.policy.reject"),
        ]:
            rb = QRadioButton(t(label_key))
            rb.setProperty("policy", value)
            if self._settings.get("slot_policy") == value:
                rb.setChecked(True)
            self._policy_group.addButton(rb)
            v.addWidget(rb)
        self._policy_group.buttonClicked.connect(self._on_policy_changed)
        layout.addWidget(gb)

        gb2 = QGroupBox(t("settings.autostart.group"), w)
        v2 = QVBoxLayout(gb2)
        self._autostart_cb = QCheckBox(t("settings.autostart.label"))
        if autostart.is_supported():
            self._autostart_cb.setChecked(autostart.is_enabled())
            self._autostart_cb.toggled.connect(self._on_autostart_toggled)
        else:
            self._autostart_cb.setEnabled(False)
            self._autostart_cb.setText(t("settings.autostart.unsupported"))
        v2.addWidget(self._autostart_cb)
        layout.addWidget(gb2)

        gb3 = QGroupBox(t("settings.language.group"), w)
        form3 = QFormLayout(gb3)
        self._lang_combo = QComboBox()
        self._lang_combo.addItem(t("lang.korean"), "ko")
        self._lang_combo.addItem(t("lang.english"), "en")
        idx = self._lang_combo.findData(self._settings.get("language") or i18n.current_language())
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        form3.addRow(t("settings.language.label"), self._lang_combo)
        note = QLabel(t("settings.language.note"))
        note.setStyleSheet("color: #888; font-size: 10px;")
        note.setWordWrap(True)
        form3.addRow(note)
        layout.addWidget(gb3)

        layout.addStretch(1)
        return w

    def _on_language_changed(self, _idx: int) -> None:
        self._settings.set(
            "language", value=str(self._lang_combo.currentData())
        )

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
            QMessageBox.warning(
                self,
                t("dialog.error"),
                t("settings.autostart.error", error=exc),
            )
            self._autostart_cb.blockSignals(True)
            self._autostart_cb.setChecked(autostart.is_enabled())
            self._autostart_cb.blockSignals(False)

    # ---- bubble tab -------------------------------------------------------
    def _tab_bubble(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        gb = QGroupBox(t("settings.bubble.trigger.group"), w)
        v = QVBoxLayout(gb)
        self._trigger_group = QButtonGroup(gb)
        for value, label_key in [
            ("hover_only", "settings.bubble.trigger.hover_only"),
            ("event_burst", "settings.bubble.trigger.event_burst"),
            ("always", "settings.bubble.trigger.always"),
            ("off", "settings.bubble.trigger.off"),
        ]:
            rb = QRadioButton(t(label_key))
            rb.setProperty("trigger", value)
            if self._settings.get("bubble", "trigger") == value:
                rb.setChecked(True)
            self._trigger_group.addButton(rb)
            v.addWidget(rb)
        self._trigger_group.buttonClicked.connect(self._on_trigger_changed)
        layout.addWidget(gb)

        gb2 = QGroupBox(t("settings.bubble.maxchars.group"), w)
        form = QFormLayout(gb2)
        self._max_chars = QComboBox()
        for n in (30, 60, 100):
            self._max_chars.addItem(t("settings.bubble.maxchars.option", n=n), n)
        cur = int(self._settings.get("bubble", "max_chars", default=60))
        idx = self._max_chars.findData(cur)
        if idx >= 0:
            self._max_chars.setCurrentIndex(idx)
        self._max_chars.currentIndexChanged.connect(self._on_maxchars_changed)
        form.addRow(t("settings.bubble.maxchars.label"), self._max_chars)
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

            btn = QPushButton(t("settings.gif.change"))
            btn.clicked.connect(lambda _, c=cat: self._pick_gif(c))
            grid.addWidget(btn, row, 3)

            reset = QPushButton(t("settings.gif.default"))
            reset.clicked.connect(lambda _, c=cat: self._reset_gif(c))
            grid.addWidget(reset, row, 4)

        layout.addStretch(1)
        return w

    @staticmethod
    def _format_path(p: Path | None) -> str:
        if p is None:
            return t("settings.gif.no_image")
        return str(p)

    def _pick_gif(self, category: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("settings.gif.picker_title", category=category),
            "",
            t("settings.gif.picker_filter"),
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
        btn_install = QPushButton(t("settings.hook.install_btn"))
        btn_install.clicked.connect(self._on_install_hooks)
        btn_uninstall = QPushButton(t("settings.hook.uninstall_btn"))
        btn_uninstall.clicked.connect(self._on_uninstall_hooks)
        row.addWidget(btn_install)
        row.addWidget(btn_uninstall)
        row.addStretch(1)
        layout.addLayout(row)

        info = QLabel(t("settings.hook.info"))
        info.setStyleSheet("color: #888;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch(1)
        self._refresh_hook_status()
        return w

    def _refresh_hook_status(self) -> None:
        installed = hook_installer.is_installed()
        self._hook_status.setText(
            t("settings.hook.installed") if installed else t("settings.hook.not_installed")
        )

    def _on_install_hooks(self) -> None:
        try:
            backup = hook_installer.install()
            msg = t("settings.hook.installed_msg")
            if backup:
                msg += t("settings.hook.backup_suffix", backup=backup)
            QMessageBox.information(self, t("dialog.done"), msg)
        except Exception as exc:
            _log.exception("install failed")
            QMessageBox.critical(
                self, t("dialog.error"), t("settings.hook.install_failed", error=exc)
            )
        self._refresh_hook_status()

    def _on_uninstall_hooks(self) -> None:
        try:
            backup = hook_installer.uninstall()
            msg = t("settings.hook.uninstalled_msg")
            if backup:
                msg += t("settings.hook.backup_suffix", backup=backup)
            QMessageBox.information(self, t("dialog.done"), msg)
        except Exception as exc:
            _log.exception("uninstall failed")
            QMessageBox.critical(
                self, t("dialog.error"), t("settings.hook.uninstall_failed", error=exc)
            )
        self._refresh_hook_status()
