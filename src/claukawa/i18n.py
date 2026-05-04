"""Tiny in-process i18n. Hierarchical string keys, dict lookup, format()
substitution. Falls back to the key itself if a translation is missing so
nothing crashes on a typo.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

LANGUAGES = ("ko", "en")
DEFAULT_LANGUAGE = "ko"

STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        # tray
        "tray.open_settings": "설정 열기",
        "tray.quit": "종료",
        # startup notice
        "startup.title": "{app} 실행 중",
        "startup.subtitle": (
            "포트 {port}에서 Claude Code 이벤트 대기 중\n"
            "트레이(작업표시줄 ∧ 영역)에서 설정/종료 가능"
        ),
        # single-instance / port conflict
        "app.already_running": "{app}이(가) 이미 실행 중입니다.",
        "app.port_unavailable": (
            "포트 {port}을(를) 사용할 수 없습니다.\n"
            "점유 중인 프로세스를 종료한 뒤 다시 실행해주세요."
        ),
        "app.gateway_failed": "HTTP 게이트웨이 시작 실패 (포트 {port}): {error}",
        # first-run hook prompt
        "firstrun.hook.title": "{app} — Hook 등록",
        "firstrun.hook.body": (
            "Claude Code 작업 상태를 표시하려면\n"
            "~/.claude/settings.json 에 hook을 등록해야 합니다.\n\n"
            "기존 hook은 보존되며, 변경 전 자동 백업됩니다.\n\n"
            "지금 등록하시겠습니까?"
        ),
        "firstrun.hook.installed_with_backup": "Hook 등록 완료. 백업: {backup}",
        "firstrun.hook.installed": "Hook이 등록되었습니다.",
        "firstrun.hook.install_failed": (
            "Hook 등록 실패: {error}\n설정 → Hook 탭에서 다시 시도하세요."
        ),
        "firstrun.tray.welcome": "포트 {port}에서 Claude Code 이벤트 수신 대기 중",
        # language picker
        "lang.picker.title": "Claukawa — 언어 선택 / Language",
        "lang.picker.body": (
            "사용할 언어를 선택해주세요.\n"
            "Please pick your preferred language."
        ),
        "lang.korean": "한국어",
        "lang.english": "English",
        # settings — common
        "settings.title": "{app} 설정",
        "settings.tab.general": "일반",
        "settings.tab.bubble": "말풍선",
        "settings.tab.gif": "GIF",
        "settings.tab.hook": "Hook",
        # settings — general
        "settings.policy.group": "슬롯 정책 (5개 다 찼을 때)",
        "settings.policy.idle_only": "idle 세션만 대체 (권장)",
        "settings.policy.lru": "가장 오래된 세션 대체 (LRU)",
        "settings.policy.reject": "새 세션 거부",
        "settings.autostart.group": "자동 시작",
        "settings.autostart.label": "로그인 시 자동 시작",
        "settings.autostart.unsupported": "로그인 시 자동 시작 (이 OS에서는 미지원)",
        "settings.autostart.error": "자동 시작 설정 실패: {error}",
        "settings.language.group": "언어",
        "settings.language.label": "언어 / Language",
        "settings.language.note": "변경한 언어는 다음 실행부터 모든 화면에 적용됩니다.",
        # settings — bubble
        "settings.bubble.trigger.group": "표시 트리거",
        "settings.bubble.trigger.hover_only": "마우스를 올렸을 때만 (기본)",
        "settings.bubble.trigger.event_burst": "이벤트 발생 시 3초 표시 후 숨김",
        "settings.bubble.trigger.always": "항상 표시",
        "settings.bubble.trigger.off": "표시 안 함",
        "settings.bubble.maxchars.group": "글자 수 제한",
        "settings.bubble.maxchars.option": "{n}자",
        "settings.bubble.maxchars.label": "최대 길이",
        # settings — gif
        "settings.gif.change": "변경…",
        "settings.gif.default": "기본값",
        "settings.gif.picker_title": "{category} 이미지 선택",
        "settings.gif.picker_filter": "이미지 (*.png *.gif *.jpg *.jpeg *.webp *.bmp)",
        "settings.gif.no_image": "(이미지 없음)",
        # settings — hook
        "settings.hook.installed": "현재 상태: ✅ 등록됨",
        "settings.hook.not_installed": "현재 상태: ⛔ 미등록",
        "settings.hook.install_btn": "Hook 등록",
        "settings.hook.uninstall_btn": "Hook 해제",
        "settings.hook.info": (
            "Claude Code의 ~/.claude/settings.json에 Claukawa 전용 hook 항목을\n"
            "별도 matcher 그룹으로 추가합니다. 기존 hook은 보존됩니다.\n"
            "변경 전 자동으로 백업 파일이 생성됩니다."
        ),
        "settings.hook.installed_msg": "Hook이 등록되었습니다.",
        "settings.hook.uninstalled_msg": "Hook이 해제되었습니다.",
        "settings.hook.backup_suffix": "\n백업: {backup}",
        "settings.hook.install_failed": "등록 실패: {error}",
        "settings.hook.uninstall_failed": "해제 실패: {error}",
        # generic dialog
        "dialog.ok": "확인",
        "dialog.error": "오류",
        "dialog.done": "완료",
        # event_mapping bubble strings
        "bubble.session_start": "세션 시작 ({source})",
        "bubble.thinking": "생각 중",
        "bubble.response_done": "응답 완료",
        "bubble.session_end": "세션 종료 ({reason})",
        "bubble.compacting": "컨텍스트 압축 ({trigger})",
        "bubble.notification.fallback": "입력 대기",
        # permission watchdog
        "bubble.permission_wait": "권한 대기: {tool}",
        # gif window
        "gifwin.no_cwd": "(no cwd)",
    },
    "en": {
        "tray.open_settings": "Open settings",
        "tray.quit": "Quit",
        "startup.title": "{app} is running",
        "startup.subtitle": (
            "Listening for Claude Code events on port {port}\n"
            "Settings & quit are in the tray (overflow area on Windows)"
        ),
        "app.already_running": "{app} is already running.",
        "app.port_unavailable": (
            "Port {port} is unavailable.\n"
            "Quit the process using it and relaunch."
        ),
        "app.gateway_failed": "HTTP gateway failed to start (port {port}): {error}",
        "firstrun.hook.title": "{app} — Install hooks",
        "firstrun.hook.body": (
            "To display Claude Code activity, hooks must be installed into\n"
            "~/.claude/settings.json.\n\n"
            "Existing hooks are preserved and the file is backed up first.\n\n"
            "Install now?"
        ),
        "firstrun.hook.installed_with_backup": "Hooks installed. Backup: {backup}",
        "firstrun.hook.installed": "Hooks installed.",
        "firstrun.hook.install_failed": (
            "Hook install failed: {error}\nTry again from Settings → Hook."
        ),
        "firstrun.tray.welcome": "Waiting for Claude Code events on port {port}",
        "lang.picker.title": "Claukawa — Language / 언어 선택",
        "lang.picker.body": (
            "Please pick your preferred language.\n"
            "사용할 언어를 선택해주세요."
        ),
        "lang.korean": "한국어",
        "lang.english": "English",
        "settings.title": "{app} Settings",
        "settings.tab.general": "General",
        "settings.tab.bubble": "Bubble",
        "settings.tab.gif": "GIF",
        "settings.tab.hook": "Hook",
        "settings.policy.group": "Slot policy (when all 5 windows are taken)",
        "settings.policy.idle_only": "Replace idle sessions only (recommended)",
        "settings.policy.lru": "Replace the oldest (LRU)",
        "settings.policy.reject": "Reject new sessions",
        "settings.autostart.group": "Auto-start",
        "settings.autostart.label": "Launch on login",
        "settings.autostart.unsupported": "Launch on login (not supported on this OS)",
        "settings.autostart.error": "Auto-start toggle failed: {error}",
        "settings.language.group": "Language",
        "settings.language.label": "Language / 언어",
        "settings.language.note": "Language changes take effect on next launch.",
        "settings.bubble.trigger.group": "Display trigger",
        "settings.bubble.trigger.hover_only": "Only on hover (default)",
        "settings.bubble.trigger.event_burst": "Flash for 3 seconds on event",
        "settings.bubble.trigger.always": "Always visible",
        "settings.bubble.trigger.off": "Hidden",
        "settings.bubble.maxchars.group": "Character limit",
        "settings.bubble.maxchars.option": "{n} chars",
        "settings.bubble.maxchars.label": "Max length",
        "settings.gif.change": "Change…",
        "settings.gif.default": "Default",
        "settings.gif.picker_title": "Choose image for {category}",
        "settings.gif.picker_filter": "Images (*.png *.gif *.jpg *.jpeg *.webp *.bmp)",
        "settings.gif.no_image": "(no image)",
        "settings.hook.installed": "Status: ✅ Installed",
        "settings.hook.not_installed": "Status: ⛔ Not installed",
        "settings.hook.install_btn": "Install hooks",
        "settings.hook.uninstall_btn": "Uninstall hooks",
        "settings.hook.info": (
            "Adds a Claukawa hook entry into ~/.claude/settings.json as a\n"
            "separate matcher group. Existing hooks are preserved and\n"
            "the file is backed up before any change."
        ),
        "settings.hook.installed_msg": "Hooks installed.",
        "settings.hook.uninstalled_msg": "Hooks uninstalled.",
        "settings.hook.backup_suffix": "\nBackup: {backup}",
        "settings.hook.install_failed": "Install failed: {error}",
        "settings.hook.uninstall_failed": "Uninstall failed: {error}",
        "dialog.ok": "OK",
        "dialog.error": "Error",
        "dialog.done": "Done",
        "bubble.session_start": "Session started ({source})",
        "bubble.thinking": "Thinking",
        "bubble.response_done": "Response complete",
        "bubble.session_end": "Session ended ({reason})",
        "bubble.compacting": "Compacting context ({trigger})",
        "bubble.notification.fallback": "Awaiting input",
        "bubble.permission_wait": "Awaiting permission: {tool}",
        "gifwin.no_cwd": "(no cwd)",
    },
}

_current = DEFAULT_LANGUAGE


def set_language(lang: str | None) -> None:
    """Set the active language; falls back to default if unknown/None."""
    global _current
    if lang in LANGUAGES:
        _current = lang
    else:
        _current = DEFAULT_LANGUAGE


def current_language() -> str:
    return _current


def t(key: str, **kwargs: object) -> str:
    """Resolve a translation key. Falls back through:
    current language → English → the key itself.
    """
    raw = (
        STRINGS.get(_current, {}).get(key)
        or STRINGS["en"].get(key)
        or key
    )
    if not kwargs:
        return raw
    try:
        return raw.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        _log.debug("i18n format error for key=%s", key)
        return raw


def detect_system_language() -> str:
    """Best-effort autodetect from Qt's locale. Returns one of LANGUAGES."""
    try:
        from PySide6.QtCore import QLocale  # type: ignore[import-not-found]

        name = QLocale.system().name()  # e.g. "ko_KR", "en_US"
    except Exception:
        return DEFAULT_LANGUAGE
    if name.startswith("ko"):
        return "ko"
    return "en"
