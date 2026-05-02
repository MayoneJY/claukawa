from __future__ import annotations

import json
from pathlib import Path

from claukawa.settings_store import DEFAULTS, SettingsStore


def test_first_load_writes_defaults(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    s = SettingsStore(p)
    assert p.exists()
    assert s.get("slot_policy") == DEFAULTS["slot_policy"]


def test_set_and_persist(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    s = SettingsStore(p)
    s.set("slot_policy", value="lru")
    s.set("bubble", "max_chars", value=30)

    s2 = SettingsStore(p)
    assert s2.get("slot_policy") == "lru"
    assert s2.get("bubble", "max_chars") == 30


def test_partial_user_config_merges_with_defaults(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"slot_policy": "reject"}), encoding="utf-8")
    s = SettingsStore(p)
    assert s.get("slot_policy") == "reject"
    # Defaults still present
    assert s.get("bubble", "trigger") == DEFAULTS["bubble"]["trigger"]


def test_corrupt_json_falls_back_to_defaults(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text("{not valid", encoding="utf-8")
    s = SettingsStore(p)
    assert s.get("slot_policy") == DEFAULTS["slot_policy"]
