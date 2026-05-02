from __future__ import annotations

import hashlib
import os


def color_for(cwd: str) -> tuple[int, int, int]:
    """Map a cwd path to a stable RGB color.

    Same cwd -> same color across runs. Hue derived from sha1, S/V fixed.
    """
    norm = os.path.normcase(os.path.normpath(cwd or ""))
    digest = hashlib.sha1(norm.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return _hsv_to_rgb(hue, 0.70, 0.85)


def _hsv_to_rgb(h: int, s: float, v: float) -> tuple[int, int, int]:
    c = v * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = v - c
    if h < 60:
        r1, g1, b1 = c, x, 0.0
    elif h < 120:
        r1, g1, b1 = x, c, 0.0
    elif h < 180:
        r1, g1, b1 = 0.0, c, x
    elif h < 240:
        r1, g1, b1 = 0.0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0.0, c
    else:
        r1, g1, b1 = c, 0.0, x
    return (
        round((r1 + m) * 255),
        round((g1 + m) * 255),
        round((b1 + m) * 255),
    )
