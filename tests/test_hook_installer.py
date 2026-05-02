from __future__ import annotations

import json
from pathlib import Path

import pytest

from claukawa import HOOK_MARKER, hook_installer


@pytest.fixture
def settings_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate filesystem effects of hook_installer to tmp_path."""
    p = tmp_path / "settings.json"

    def fake_claude_settings_path() -> Path:
        return p

    backup_dir = tmp_path
    def fake_backup_path(ts: str) -> Path:
        return backup_dir / f"settings.json.claukawa-backup-{ts}"

    monkeypatch.setattr(hook_installer.platform_paths, "claude_settings_path", fake_claude_settings_path)
    monkeypatch.setattr(hook_installer.platform_paths, "claude_settings_backup_path", fake_backup_path)
    return p


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_install_into_empty(settings_path: Path) -> None:
    hook_installer.install()
    data = _read(settings_path)
    assert "hooks" in data
    for ev in hook_installer.HOOK_EVENTS:
        assert ev in data["hooks"]
        groups = data["hooks"][ev]
        assert any(
            HOOK_MARKER in h["command"]
            for grp in groups
            for h in grp.get("hooks", [])
        )


def test_install_preserves_existing_hook(settings_path: Path) -> None:
    existing = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "echo discord-original", "timeout": 15}
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(existing), encoding="utf-8")
    hook_installer.install()
    data = _read(settings_path)
    stop_groups = data["hooks"]["Stop"]
    cmds = [h["command"] for grp in stop_groups for h in grp["hooks"]]
    assert "echo discord-original" in cmds
    assert any(HOOK_MARKER in c for c in cmds)


def test_install_is_idempotent(settings_path: Path) -> None:
    hook_installer.install()
    first = _read(settings_path)
    hook_installer.install()
    second = _read(settings_path)
    assert first == second


def test_is_installed_detects(settings_path: Path) -> None:
    assert hook_installer.is_installed() is False
    hook_installer.install()
    assert hook_installer.is_installed() is True


def test_uninstall_only_removes_claukawa_entries(settings_path: Path) -> None:
    existing = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "echo discord-original", "timeout": 15}
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(existing), encoding="utf-8")
    hook_installer.install()
    hook_installer.uninstall()
    data = _read(settings_path)
    cmds = [h["command"] for grp in data["hooks"]["Stop"] for h in grp["hooks"]]
    assert "echo discord-original" in cmds
    assert all(HOOK_MARKER not in c for c in cmds)
    assert hook_installer.is_installed() is False


def test_uninstall_drops_empty_event_arrays(settings_path: Path) -> None:
    hook_installer.install()
    hook_installer.uninstall()
    data = _read(settings_path)
    assert data.get("hooks", {}) == {} or "hooks" not in data


def test_install_creates_backup_when_existing(settings_path: Path, tmp_path: Path) -> None:
    settings_path.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    backup = hook_installer.install()
    assert backup is not None
    assert backup.exists()
