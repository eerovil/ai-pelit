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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_immutable import WITHDRAWN  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BACK_SCRIPT = '<script src="../../../back.js"></script>'
# The chip may sit in another corner: <script src="../../../back.js" data-corner="bottom-left">.
BACK_SCRIPT_RE = re.compile(r'<script src="\.\./\.\./\.\./back\.js"[^>]*></script>')
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Each game's picture for the shelf (#33), beside game.json; scripts/make_thumb.py makes it.
THUMB = "thumb.webp"
THUMB_SIZE = (360, 480)
# A shared library a version loads from public/lib/ (#99), e.g. '../../../lib/three-r187/three.module.js'.
LIB_REF = re.compile(r"""['"]\.\./\.\./\.\./lib/([^'"?#]+)""")
LIB_DIR = ROOT / "public" / "lib"
# Shelf groups (#153): a game.json with "group": "<key>" shows inside that group's card, and the
# group's page lists its games. A key is a shelf address like a game's slug, so no game may take it.
GROUPS = {
    "yleisurheilu": {
        "title": "Yleisurheilu",
        "description": "Juoksut, hypyt ja heitot, jokainen omana pelinään.",
    },
}


def webp_size(data: bytes) -> tuple[int, int] | None:
    """Width and height of a WebP image, read from its header; None when it is not one.

    A file cut short is not one either: the RIFF header gives the whole file's length.
    tests/test_build.py decodes every real game's picture with Pillow as well."""
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    if int.from_bytes(data[4:8], "little") + 8 != len(data):
        return None
    kind = data[12:16]
    if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if kind == b"VP8L" and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
    return None


class GameError(Exception):
    pass


def load_game(game_dir: Path, withdrawn: set[str] | None = None, lib_dir: Path = LIB_DIR) -> dict:
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
    # Numbered 1, 2, 3… in order; a number withdrawn (check_immutable.WITHDRAWN) is skipped for good.
    skip = {int(d.split("/")[2][1:]) for d in (WITHDRAWN if withdrawn is None else withdrawn) if d.split("/")[1] == slug}
    expected = 1
    for v in versions:
        while v.get("n") != expected and expected in skip:
            expected += 1
        if v.get("n") != expected:
            raise GameError(f"{slug}: versions must be numbered 1, 2, 3… in order (found {v.get('n')} where {expected} was due)")
        i = expected
        expected += 1
        if not DATE.match(str(v.get("date", ""))):
            raise GameError(f"{slug} v{i}: date must be YYYY-MM-DD")
        if not v.get("note"):
            raise GameError(f"{slug} v{i}: note is missing")
        page = game_dir / f"v{i}" / "index.html"
        if not page.is_file():
            raise GameError(f"{slug} v{i}: v{i}/index.html is missing")
        html = page.read_text()
        if not BACK_SCRIPT_RE.search(html):
            raise GameError(f"{slug} v{i}: index.html must include {BACK_SCRIPT}")
        for ref in LIB_REF.findall(html):
            if not (lib_dir / ref).is_file():
                raise GameError(f"{slug} v{i}: index.html loads lib/{ref}, which is not in public/lib/")
    thumb = game_dir / THUMB
    if not thumb.is_file():
        raise GameError(f"{slug}: {THUMB} is missing (python3 scripts/make_thumb.py {slug} <screenshot.png>)")
    size = webp_size(thumb.read_bytes())
    if size != THUMB_SIZE:
        found = "not a WebP image" if size is None else f"{size[0]} x {size[1]}"
        raise GameError(f"{slug}: {THUMB} must be a 360 x 480 WebP, found {found} (python3 scripts/make_thumb.py)")
    folders = {p.name for p in game_dir.iterdir() if p.is_dir() and re.match(r"^v\d+$", p.name)}
    extra = folders - {f"v{v['n']}" for v in versions}
    if extra:
        raise GameError(f"{slug}: folders without a game.json version: {', '.join(sorted(extra))}")
    group = meta.get("group")
    if group is not None and group not in GROUPS:
        raise GameError(f"{slug}: game.json names an unknown group {group!r} (GROUPS in scripts/build.py)")
    return {
        "slug": slug,
        "title": meta["title"],
        "description": meta["description"],
        **({"group": group} if group else {}),
        # A new picture gets a new name, so no phone keeps showing an old one from its cache.
        "thumb": f"thumbs/{slug}-{hashlib.sha256(thumb.read_bytes()).hexdigest()[:8]}.webp",
        "versions": [
            {"n": v["n"], "date": v["date"], "note": v["note"], "issue": v.get("issue")}
            for v in versions
        ],
    }


def build_catalog(games_dir: Path, lib_dir: Path = LIB_DIR) -> dict:
    games = [load_game(d, lib_dir=lib_dir) for d in sorted(games_dir.iterdir()) if d.is_dir()]
    # Newest version first, so a fresh game or version is at the top of the shelf.
    games.sort(key=lambda g: (g["versions"][-1]["date"], g["slug"]), reverse=True)
    taken = {g["slug"] for g in games} & set(GROUPS)
    if taken:
        raise GameError(f"{', '.join(sorted(taken))}: a game's slug is a group's address (GROUPS in scripts/build.py)")
    used = {g["group"] for g in games if "group" in g}
    groups = [{"slug": k, **v} for k, v in GROUPS.items() if k in used]
    return {"games": games, "groups": groups}


def build(games_dir: Path, public_dir: Path, out_dir: Path) -> dict:
    catalog = build_catalog(games_dir, public_dir / "lib")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(public_dir, out_dir)
    # The picture is skipped beside game.json only: a version may have a file of the same name.
    def skip(folder, names):
        return [n for n in names if n == "game.json" or (n == THUMB and Path(folder).parent == games_dir)]

    shutil.copytree(games_dir, out_dir / "games", ignore=skip)
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
