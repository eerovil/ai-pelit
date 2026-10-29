#!/usr/bin/env python3
"""Build the site: check every game, write catalog.json, copy the shell and the games.

    python3 scripts/build.py                     # games/ + public/ -> _site/
    python3 scripts/build.py --games X --out Y   # what the tests use

The service worker gets a build id made from everything it serves except the games,
so each deploy that changes the shell or the catalog is a new worker and phones update.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACK_SCRIPT = '<script src="../../../back.js"></script>'
# The chip may sit in another corner: <script src="../../../back.js" data-corner="bottom-left">.
BACK_SCRIPT_RE = re.compile(r'<script src="\.\./\.\./\.\./back\.js"[^>]*></script>')
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Each game's picture for the shelf (#33), beside game.json; scripts/make_thumb.py makes it.
THUMB = "thumb.webp"


class GameError(Exception):
    pass


def load_game(game_dir: Path) -> dict:
    slug = game_dir.name
    if not SLUG.match(slug):
        raise GameError(f"{slug}: a game folder name is lowercase letters, digits and dashes")
    meta_path = game_dir / "game.json"
    if not meta_path.is_file():
        raise GameError(f"{slug}: game.json is missing")
    meta = json.loads(meta_path.read_text())
    for key in ("title", "description", "versions"):
        if not meta.get(key):
            raise GameError(f"{slug}: game.json needs {key}")
    versions = meta["versions"]
    for i, v in enumerate(versions, start=1):
        if v.get("n") != i:
            raise GameError(f"{slug}: versions must be numbered 1, 2, 3… in order (found {v.get('n')} at {i})")
        if not DATE.match(str(v.get("date", ""))):
            raise GameError(f"{slug} v{i}: date must be YYYY-MM-DD")
        if not v.get("note"):
            raise GameError(f"{slug} v{i}: note is missing")
        page = game_dir / f"v{i}" / "index.html"
        if not page.is_file():
            raise GameError(f"{slug} v{i}: v{i}/index.html is missing")
        if not BACK_SCRIPT_RE.search(page.read_text()):
            raise GameError(f"{slug} v{i}: index.html must include {BACK_SCRIPT}")
    thumb = game_dir / THUMB
    if not thumb.is_file():
        raise GameError(f"{slug}: {THUMB} is missing (python3 scripts/make_thumb.py {slug} <screenshot.png>)")
    folders = {p.name for p in game_dir.iterdir() if p.is_dir() and re.match(r"^v\d+$", p.name)}
    extra = folders - {f"v{i}" for i in range(1, len(versions) + 1)}
    if extra:
        raise GameError(f"{slug}: folders without a game.json version: {', '.join(sorted(extra))}")
    return {
        "slug": slug,
        "title": meta["title"],
        "description": meta["description"],
        # A new picture gets a new name, so no phone keeps showing an old one from its cache.
        "thumb": f"thumbs/{slug}-{hashlib.sha256(thumb.read_bytes()).hexdigest()[:8]}.webp",
        "versions": [
            {"n": v["n"], "date": v["date"], "note": v["note"], "issue": v.get("issue")}
            for v in versions
        ],
    }


def build_catalog(games_dir: Path) -> dict:
    games = [load_game(d) for d in sorted(games_dir.iterdir()) if d.is_dir()]
    # Newest version first, so a fresh game or version is at the top of the shelf.
    games.sort(key=lambda g: (g["versions"][-1]["date"], g["slug"]), reverse=True)
    return {"games": games}


def build(games_dir: Path, public_dir: Path, out_dir: Path) -> dict:
    catalog = build_catalog(games_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(public_dir, out_dir)
    shutil.copytree(games_dir, out_dir / "games", ignore=shutil.ignore_patterns("game.json", THUMB))
    (out_dir / "thumbs").mkdir()
    for game in catalog["games"]:
        shutil.copyfile(games_dir / game["slug"] / THUMB, out_dir / game["thumb"])
    catalog_text = json.dumps(catalog, ensure_ascii=False, indent=1) + "\n"
    (out_dir / "catalog.json").write_text(catalog_text)

    digest = hashlib.sha256(catalog_text.encode())
    for path in sorted(public_dir.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(public_dir).as_posix().encode())
            digest.update(path.read_bytes())
    sw = out_dir / "sw.js"
    sw.write_text(sw.read_text().replace("__BUILD_ID__", digest.hexdigest()[:12]))
    return catalog


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=Path, default=ROOT / "games")
    ap.add_argument("--public", type=Path, default=ROOT / "public")
    ap.add_argument("--out", type=Path, default=ROOT / "_site")
    args = ap.parse_args()
    try:
        catalog = build(args.games, args.public, args.out)
    except GameError as e:
        print(f"build: {e}", file=sys.stderr)
        return 1
    n = sum(len(g["versions"]) for g in catalog["games"])
    print(f"build: {len(catalog['games'])} games, {n} versions -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
