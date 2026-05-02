"""Install the bundled Chiikawa scene PNGs (originals, untouched) as the
default per-category asset pack.

This is just a copy with category-renamed filenames — no resize, no
squaring, no quantization. Display-time scaling in QPixmap.scaled
(SmoothTransformation, KeepAspectRatio) handles render quality.

Also clears the user-data asset cache so the new pack takes effect on next
app launch.

    python tools/build_chibi_default_pack.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "claukawa" / "assets" / "scenes" / "chibi"
DST = ROOT / "src" / "claukawa" / "assets" / "gifs" / "default"

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


def clear_user_cache() -> None:
    """Wipe %APPDATA%\\Claukawa\\gifs (or macOS equivalent) so the new
    bundled pack reseeds on next launch."""
    try:
        # platform_paths uses platformdirs, so resolve via the same path
        sys.path.insert(0, str(ROOT / "src"))
        from claukawa import platform_paths  # type: ignore[import-not-found]

        gif_dir = platform_paths.gifs_path()
    except Exception as exc:
        print(f"could not resolve user cache dir ({exc}); skipping clear")
        return
    if not gif_dir.exists():
        return
    removed = 0
    for pattern in ("*.gif", "*.png"):
        for f in gif_dir.glob(pattern):
            try:
                os.unlink(f)
                removed += 1
            except OSError:
                pass
    print(f"cleared {removed} cached image(s) from {gif_dir}")


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    # Drop only stale chibi PNGs we wrote previously; LEAVE *.gif placeholders
    # alone — they are the public/MIT-safe defaults that ship to GitHub.
    # The resolver tries PNG before GIF, so a local chibi PNG sitting next
    # to the placeholder GIF wins automatically while the GIF remains the
    # tracked default.
    for category in MAPPING.keys():
        stale_png = DST / f"{category}.png"
        if stale_png.exists():
            stale_png.unlink()
    missing: list[str] = []
    for category, slug in MAPPING.items():
        png = SRC / f"{slug}.png"
        if not png.exists():
            missing.append(f"{category}: {png}")
            continue
        out = DST / f"{category}.png"
        shutil.copy2(png, out)
        size = png.stat().st_size
        print(f"wrote {out}  ({size // 1024}KB, original)")
    if missing:
        print("MISSING SOURCES:")
        for m in missing:
            print(f"  {m}")
        return 1
    clear_user_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
