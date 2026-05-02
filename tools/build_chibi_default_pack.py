"""Install the local Chiikawa scene PNGs into the per-user runtime cache as
overrides for the shipped MIT-safe default pack.

Writes to %APPDATA%\\Claukawa\\gifs (or the macOS equivalent), NOT into
the tracked source tree, so:
  - the public/MIT-safe pack at src/claukawa/assets/gifs/default/*.png
    is never modified,
  - and the user's local Chiikawa override survives `git pull` cleanly.

The resolver searches the user dir first, so the chibi PNGs win at
runtime for this user without leaking into the repo.

    python tools/build_chibi_default_pack.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from claukawa import platform_paths  # noqa: E402

SRC = ROOT / "src" / "claukawa" / "assets" / "scenes" / "chibi"
DST = platform_paths.gifs_path()

# category -> source PNG name (without extension)
MAPPING: dict[str, str] = {
    "session_start": "greeting",
    "thinking": "writing_then_thinking",
    "editing": "writing",
    "reading": "reading_book",
    "bashing": "typing",
    "web": "mousing",
    "subagent": "cup_phone",
    "mcp": "scene_12",
    "waiting_input": "question",
    "idle": "sleeping",
    "compacting": "recalling",
}


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for category, slug in MAPPING.items():
        png = SRC / f"{slug}.png"
        if not png.exists():
            missing.append(f"{category}: {png}")
            continue
        out = DST / f"{category}.png"
        shutil.copy2(png, out)
        size = png.stat().st_size
        print(f"wrote {out}  ({size // 1024}KB)")
    if missing:
        print("MISSING SOURCES (run tools/extract_chibi_scenes.py first):")
        for m in missing:
            print(f"  {m}")
        return 1
    print(
        "\nDone. Restart Claukawa to see the new pack — the resolver picks "
        "user-cache overrides on next event."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
