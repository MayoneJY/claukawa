"""Generate the bundled placeholder GIF pack.

Run once during development; commit the resulting files.

    python tools/generate_placeholder_gifs.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parents[1] / "src" / "claukawa" / "assets" / "gifs" / "default"
SIZE = 128

# (label, hue) per category. Hue 0-360.
CATEGORIES = [
    ("session_start", "START", 200, False),
    ("thinking", "THINK", 280, False),
    ("editing", "EDIT", 130, False),
    ("reading", "READ", 50, False),
    ("bashing", "BASH", 0, False),
    ("web", "WEB", 220, False),
    ("subagent", "AGENT", 310, False),
    ("mcp", "MCP", 175, False),
    ("waiting_input", "INPUT", 30, False),
    ("idle", "IDLE", 240, True),  # static
    ("compacting", "COMPACT", 100, False),
]


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    c = v * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))


def _font(size: int) -> ImageFont.ImageFont:
    candidates = ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _frame(label: str, hue: int, dots: int, pulse: float) -> Image.Image:
    bg = _hsv_to_rgb(hue, 0.55, 0.22)  # dim
    panel = _hsv_to_rgb(hue, 0.65, 0.95)
    text_color = (245, 245, 248)

    img = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(img)

    # Outer ring (slight pulse)
    pad = 6
    ring_w = 2 + int(round(pulse * 1.5))
    draw.rectangle((pad, pad, SIZE - pad - 1, SIZE - pad - 1), outline=panel, width=ring_w)

    # Label
    label_font = _font(20 if len(label) <= 5 else 16)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((SIZE - tw) // 2, (SIZE - th) // 2 - 8), label, fill=text_color, font=label_font)

    # Dot ellipsis
    dot_r = 4
    gap = 12
    total_w = 3 * (dot_r * 2) + 2 * (gap - dot_r * 2)
    start_x = (SIZE - total_w) // 2 + dot_r
    y = SIZE - 28
    for i in range(3):
        cx = start_x + i * gap
        on = i < dots
        color = panel if on else _hsv_to_rgb(hue, 0.30, 0.40)
        draw.ellipse((cx - dot_r, y - dot_r, cx + dot_r, y + dot_r), fill=color)
    return img


def build_gif(label: str, hue: int, static: bool) -> list[Image.Image]:
    if static:
        return [_frame(label, hue, 0, 0.0)]
    frames: list[Image.Image] = []
    n = 12
    for i in range(n):
        t = i / n
        dots = (i // 3) % 4  # 0,0,0,1,1,1,2,2,2,3,3,3
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
        frames.append(_frame(label, hue, dots, pulse))
    return frames


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for slug, label, hue, static in CATEGORIES:
        frames = build_gif(label, hue, static)
        out = OUTPUT / f"{slug}.gif"
        if static:
            frames[0].save(out, format="GIF", optimize=True)
        else:
            frames[0].save(
                out,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=80,
                loop=0,
                optimize=True,
                disposal=2,
            )
        print(f"wrote {out}  ({len(frames)} frame{'s' if len(frames) != 1 else ''})")


if __name__ == "__main__":
    main()
