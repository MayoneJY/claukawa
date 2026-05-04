from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from . import i18n


def pick_language(default: str | None = None) -> str:
    """Show a tiny modal asking the user to pick Korean or English.

    Returns the selected language code ("ko" | "en"). The dialog never
    returns None — closing without choosing falls back to `default` (or
    `i18n.DEFAULT_LANGUAGE`).
    """
    fallback = default or i18n.DEFAULT_LANGUAGE
    box = QMessageBox()
    box.setWindowTitle(i18n.t("lang.picker.title"))
    box.setText(i18n.t("lang.picker.body"))
    btn_ko = box.addButton(i18n.t("lang.korean"), QMessageBox.AcceptRole)
    btn_en = box.addButton(i18n.t("lang.english"), QMessageBox.AcceptRole)
    if fallback == "en":
        box.setDefaultButton(btn_en)
    else:
        box.setDefaultButton(btn_ko)
    box.exec()
    if box.clickedButton() is btn_en:
        return "en"
    if box.clickedButton() is btn_ko:
        return "ko"
    return fallback
