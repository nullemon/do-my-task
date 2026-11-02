"""Generate TabNap's toolbar/store icons (16, 32, 48, 128 px).

Design: a cream crescent moon on an indigo rounded square, with two small
sparkles on the larger sizes. Drawn at 8x and downscaled for clean edges.

Usage (needs Pillow):  python tools/make_icons.py
Writes icons/icon{16,32,48,128}.png next to this folder.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SIZES = (16, 32, 48, 128)
SCALE = 8
TOP_LEFT = (124, 108, 255)     # #7c6cff
BOTTOM_RIGHT = (52, 40, 150)   # #342896
MOON = (255, 232, 163, 255)    # #ffe8a3
SPARKLE = (255, 244, 214, 255)

OUT = Path(__file__).resolve().parent.parent / "icons"


def gradient(size):
    """Diagonal gradient from TOP_LEFT to BOTTOM_RIGHT."""
    small = Image.new("RGB", (64, 64))
    px = small.load()
    for y in range(64):
        for x in range(64):
            t = (x + y) / 126
            px[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(TOP_LEFT, BOTTOM_RIGHT))
    return small.resize((size, size), Image.BICUBIC)


def circle_mask(size, cx, cy, r):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    return mask


def sparkle(draw, cx, cy, r):
    """Four-pointed star."""
    w = r * 0.28
    draw.polygon(
        [(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w),
         (cx, cy + r), (cx - w, cy + w), (cx - r, cy), (cx - w, cy - w)],
        fill=SPARKLE,
    )


def render(px):
    s = px * SCALE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    # Rounded-square background (a little inset on the big icon, as Chrome
    # Web Store icons are expected to have some padding).
    inset = round(s * (0.06 if px >= 48 else 0.0))
    radius = round((s - 2 * inset) * 0.24)
    bg_mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(bg_mask).rounded_rectangle(
        (inset, inset, s - inset - 1, s - inset - 1), radius=radius, fill=255
    )
    img.paste(gradient(s), (0, 0), bg_mask)

    # Crescent = big disc minus an offset disc.
    big = s - 2 * inset
    cx = inset + big * (0.46 if px >= 32 else 0.48)
    cy = inset + big * (0.54 if px >= 32 else 0.52)
    r = big * (0.30 if px >= 32 else 0.34)
    disc = circle_mask(s, cx, cy, r)
    bite = circle_mask(s, cx + r * 0.52, cy - r * 0.40, r * 0.86)
    crescent = ImageChops.subtract(disc, bite)
    moon = Image.new("RGBA", (s, s), MOON)
    img.paste(moon, (0, 0), crescent)

    if px >= 32:
        d = ImageDraw.Draw(img)
        sparkle(d, inset + big * 0.72, inset + big * 0.30, big * 0.085)
        sparkle(d, inset + big * 0.80, inset + big * 0.52, big * 0.05)

    return img.resize((px, px), Image.LANCZOS)


def main():
    OUT.mkdir(exist_ok=True)
    for px in SIZES:
        path = OUT / f"icon{px}.png"
        render(px).save(path, optimize=True)
        print("wrote", path)


if __name__ == "__main__":
    main()
