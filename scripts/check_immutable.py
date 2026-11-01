"""Fail when a change edits a game version that is already published.

    python3 scripts/check_immutable.py origin/main

A published version is a `games/<slug>/v<N>/` folder that exists at the base ref. Its files
may not change, and its entry in game.json may not change either; new versions are appended.
A shared library's file under `public/lib/` (three.js, #99) that exists at the base ref may not
change either: games load it from there for good, so a new release goes in a new folder.

Only each game's newest version is kept (#346, Eero's choice). A new version is the newest
folder moved to the next number (`git mv`) and changed there, so the old folder goes whole: a
published folder may be deleted, all of it, once the game has a newer folder. A new folder takes
a number above every one the game has had, as phones may keep an old version's files cached.
"""

import json
import os
import re
import subprocess
import sys

VERSION_FILE = re.compile(r"^games/([^/]+)/(v\d+)/")


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def folders_now(slug: str, cwd: str | None) -> set[int]:
    d = f"{cwd or '.'}/games/{slug}"
    return {int(n[1:]) for n in os.listdir(d) if re.fullmatch(r"v\d+", n)} if os.path.isdir(d) else set()


def problems(base: str, cwd: str | None = None) -> list[str]:
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
            slug, n = m.group(1), int(m.group(2)[1:])
            if status == "D" and not os.path.isdir(f"{cwd or '.'}/{m.group(0)}"):
                if not any(k > n for k in folders_now(slug, cwd)):
                    found.append(f"{path}: {slug} {m.group(2)} may go only when the game has a newer version folder")
                continue
            if status == "D":
                # Only the whole version may go: a file deleted from a folder that stays is an edit.
                found.append(f"{path}: {slug} {m.group(2)} is published; delete it whole, or make a new version")
                continue
            found.append(f"{path}: {slug} {m.group(2)} is published; make a new version instead")
        if path.endswith("/game.json") and status != "A" and path in published:
            old = json.loads(git("show", f"{base}:{path}", cwd=cwd))["versions"]
            try:
                with open(path if cwd is None else f"{cwd}/{path}") as f:
                    new = json.load(f)["versions"]
            except FileNotFoundError:
                found.append(f"{path}: a published game cannot be removed")
                continue
            if new[: len(old)] != old:
                found.append(f"{path}: published versions' entries changed; only append new ones")
    # A number is never used again: phones keep an old version in their offline cache for good,
    # so a new version at the same address would never reach them.
    for p in sorted(published):
        if p.endswith("/game.json") and p.count("/") == 2:
            slug = p.split("/")[1]
            had = {v.get("n") for v in json.loads(git("show", f"{base}:{p}", cwd=cwd))["versions"]}
            had |= {int(d.split("/")[2][1:]) for d in published_dirs if d.split("/")[1] == slug}
            for k in sorted(folders_now(slug, cwd)):
                if f"games/{slug}/v{k}/" not in published_dirs and k <= max(had, default=0):
                    found.append(f"games/{slug}/v{k}/: a new version takes a number above v{max(had)}, never an old one")
    lib = git("diff", "--name-status", "--no-renames", base, "--", "public/lib", cwd=cwd).splitlines()
    for line in lib:
        status, path = line.split("\t", 1)
        if status != "A":
            found.append(f"{path}: a published library file never changes; add a new folder for a new release")
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
