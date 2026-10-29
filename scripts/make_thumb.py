#!/usr/bin/env python3
"""Make a game's shelf picture (#33) from a mid-play screenshot.

    python3 scripts/make_thumb.py <slug> <screenshot.png>

Crops the middle of the screenshot to 3:4 and writes a 360 x 480 WebP to
games/<slug>/thumb.webp, beside game.json. Needs Pillow.
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SIZE = (360, 480)


def make_thumb(screenshot: Path, out: Path) -> None:
    img = Image.open(screenshot).convert("RGB")
    w, h = img.size
    # The widest 3:4 box that fits, centred.
    cw, ch = (w, w * 4 // 3) if w * 4 // 3 <= h else (h * 3 // 4, h)
    left, top = (w - cw) // 2, (h - ch) // 2
    img = img.crop((left, top, left + cw, top + ch)).resize(SIZE, Image.LANCZOS)
    img.save(out, "WEBP", quality=80)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    slug, screenshot = sys.argv[1], Path(sys.argv[2])
    game_dir = ROOT / "games" / slug
    if not (game_dir / "game.json").is_file():
        print(f"make_thumb: no game {slug}", file=sys.stderr)
        return 1
    make_thumb(screenshot, game_dir / "thumb.webp")
    print(f"make_thumb: games/{slug}/thumb.webp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
