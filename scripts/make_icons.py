#!/usr/bin/env python3
"""Draw the app icons (a game pad on the app colours). Run once; the PNGs are committed."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "public" / "icons"
BG = (27, 30, 43)
PAD = (255, 183, 3)
INK = (27, 30, 43)


def draw(size: int, safe: float) -> Image.Image:
    s = size * 4  # draw large, shrink for smooth edges
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)
    w = s * safe
    x0, y0 = (s - w) / 2, s / 2 - w * 0.3
    d.rounded_rectangle([x0, y0, x0 + w, y0 + w * 0.6], radius=w * 0.28, fill=PAD)
    u = w / 10
    cx, cy = x0 + w * 0.28, y0 + w * 0.3
    d.rectangle([cx - u * 1.5, cy - u * 0.5, cx + u * 1.5, cy + u * 0.5], fill=INK)
    d.rectangle([cx - u * 0.5, cy - u * 1.5, cx + u * 0.5, cy + u * 1.5], fill=INK)
    for bx, by in ((0.68, 0.24), (0.8, 0.36)):
        px, py = x0 + w * bx, y0 + w * by
        d.ellipse([px - u * 0.7, py - u * 0.7, px + u * 0.7, py + u * 0.7], fill=INK)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, 0.78).save(OUT / "icon-192.png")
    draw(512, 0.78).save(OUT / "icon-512.png")
    draw(180, 0.78).save(OUT / "apple-touch-icon.png")
    # Maskable: the launcher may crop to a circle, so keep the pad inside the middle 80 %.
    draw(512, 0.6).save(OUT / "icon-maskable-512.png")


if __name__ == "__main__":
    main()
