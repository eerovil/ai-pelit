#!/usr/bin/env python3
"""Fail when a change edits a game version that is already published.

    python3 scripts/check_immutable.py origin/main

A published version is a `games/<slug>/v<N>/` folder that exists at the base ref. Its files
may not change, and its entry in game.json may not change either; new versions are appended.
A shared library's file under `public/lib/` (three.js, #99) that exists at the base ref may not
change either: games load it from there for good, so a new release goes in a new folder.

The one way out is WITHDRAWN: a version Eero asked, in so many words, to take out of production.
Such a version may only be deleted whole (its folder and its game.json entry), never edited.
"""

import json
import os
import re
import subprocess
import sys

VERSION_FILE = re.compile(r"^games/([^/]+)/(v\d+)/")

# Versions removed by the owner's explicit decision, each with where he said so.
WITHDRAWN = {
    "games/puhelinkoppi/v3/",  # eerovil/ai-pelit#9: "palataan vain takaisin v2 ja poistetaan tuotannosta v3+ versiot"
    "games/puhelinkoppi/v4/",  # (same decision, "Allow once" in the question box)
}


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def problems(base: str, cwd: str | None = None, withdrawn: set[str] = WITHDRAWN) -> list[str]:
    found = []
    published = set(
        line for line in git("ls-tree", "-r", "--name-only", base, "--", "games", cwd=cwd).splitlines()
    )
    published_dirs = {m.group(0) for p in published if (m := VERSION_FILE.match(p))}
    changed = git("diff", "--name-status", "--no-renames", base, "--", "games", cwd=cwd).splitlines()
    for line in changed:
        status, path = line.split("\t", 1)
        m = VERSION_FILE.match(path)
        if m and m.group(0) in published_dirs:
            if status == "D" and m.group(0) in withdrawn:
                # Only the whole version may go: a file deleted from a folder that stays is an edit.
                if not os.path.isdir(f"{cwd or '.'}/{m.group(0)}"):
                    continue
                found.append(f"{path}: {m.group(1)} {m.group(2)} is withdrawn; delete it whole, not file by file")
                continue
            found.append(f"{path}: {m.group(1)} {m.group(2)} is published; make a new version instead")
        if path.endswith("/game.json") and status != "A" and path in published:
            old = json.loads(git("show", f"{base}:{path}", cwd=cwd))["versions"]
            try:
                with open(path if cwd is None else f"{cwd}/{path}") as f:
                    new = json.load(f)["versions"]
            except FileNotFoundError:
                found.append(f"{path}: a published game cannot be removed")
                continue
            slug = path.split("/")[1]
            gone = {v.get("n") for v in old if f"games/{slug}/v{v.get('n')}/" in withdrawn
                    and not os.path.isdir(f"{cwd or '.'}/games/{slug}/v{v.get('n')}")}
            old = [v for v in old if v.get("n") not in gone]
            if new[: len(old)] != old:
                found.append(f"{path}: published versions' entries changed; only append new ones")
    lib = git("diff", "--name-status", "--no-renames", base, "--", "public/lib", cwd=cwd).splitlines()
    for line in lib:
        status, path = line.split("\t", 1)
        if status != "A":
            found.append(f"{path}: a published library file never changes; add a new folder for a new release")
    # A withdrawn number is never used again: phones keep the old version in their offline cache
    # for good, so a new game at the same address would never reach them.
    for d in sorted(withdrawn - published_dirs):
        if os.path.isdir(f"{cwd or '.'}/{d}"):
            found.append(f"{d}: this version was withdrawn; its number is never used again, take the next unused one")
    # A withdrawn version's folder and its game.json entry go together, even when game.json
    # itself was left as it was.
    for d in sorted(withdrawn & published_dirs):
        if os.path.isdir(f"{cwd or '.'}/{d}"):
            continue
        slug, n = d.split("/")[1], int(d.split("/")[2][1:])
        meta = f"{cwd or '.'}/games/{slug}/game.json"
        if os.path.isfile(meta):
            with open(meta) as f:
                if any(v.get("n") == n for v in json.load(f)["versions"]):
                    found.append(f"games/{slug}/game.json: v{n} is withdrawn and its folder is gone; remove its entry too")
    return found


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    found = problems(base)
    for p in found:
        print(f"check_immutable: {p}", file=sys.stderr)
    if not found:
        print(f"check_immutable: no published version changed since {base}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
