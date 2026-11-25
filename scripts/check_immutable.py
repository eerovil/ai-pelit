"""Fail when a change edits a game version that is already published.

    python3 scripts/check_immutable.py origin/main

The base is where the branch left the given ref (`git merge-base HEAD origin/main`), so versions
main published since are not blamed on the branch (#555); the ref itself when git cannot tell.
A new version's number is still checked against the ref's tip as well, so a number main took
since is not used again.
A published version is a `games/<slug>/v<N>/` folder that exists at the base. Its files
may not change, and its entry in game.json may not change either; new versions are appended.
A shared library's file under `public/lib/` (three.js, #99) that exists at the base may not
change either: games load it from there for good, so a new release goes in a new folder.

Only each game's newest version is kept (#346, Eero's choice). A new version is the newest
folder moved to the next number (`git mv`) and changed there, so the old folder goes whole: a
published folder may be deleted, all of it, once the game has a newer folder. A new folder takes
a number above every one the game has had, as phones may keep an old version's files cached.

A game the owner removed (scripts/removed_games.py, Ottelu in #469) may go, but only whole: every
folder and its game.json.
"""

import json
import os
import re
import subprocess
import sys

from removed_games import REMOVED

VERSION_FILE = re.compile(r"^games/([^/]+)/(v\d+)/")


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def folders_now(slug: str, cwd: str | None) -> set[int]:
    d = f"{cwd or '.'}/games/{slug}"
    return {int(n[1:]) for n in os.listdir(d) if re.fullmatch(r"v\d+", n)} if os.path.isdir(d) else set()


def numbers_at(ref: str, cwd: str | None) -> dict[str, set[int]]:
    """Every version number each game has had at `ref`: its game.json entries and its folders."""
    had: dict[str, set[int]] = {}
    for p in git("ls-tree", "-r", "--name-only", ref, "--", "games", cwd=cwd).splitlines():
        parts = p.split("/")
        if len(parts) == 3 and parts[2] == "game.json":
            vs = json.loads(git("show", f"{ref}:{p}", cwd=cwd))["versions"]
            had.setdefault(parts[1], set()).update(v["n"] for v in vs if isinstance(v.get("n"), int))
        elif len(parts) > 3 and re.fullmatch(r"v\d+", parts[2]):
            had.setdefault(parts[1], set()).add(int(parts[2][1:]))
    return had


def problems(base: str, cwd: str | None = None, removed=REMOVED, tip: str | None = None) -> list[str]:
    found = []
    # A removed game goes whole: nothing of it is left under games/<slug>/.
    gone = {s for s in removed if not os.path.exists(f"{cwd or '.'}/games/{s}")}
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
                if slug in gone:
                    continue
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
                if path.split("/")[1] in gone:
                    continue
                found.append(f"{path}: a published game cannot be removed")
                continue
            if new[: len(old)] != old:
                found.append(f"{path}: published versions' entries changed; only append new ones")
    # A number is never used again: phones keep an old version in their offline cache for good,
    # so a new version at the same address would never reach them.
    # The numbers the base ref took after the branch left it (`tip`, #555) count too.
    numbers = numbers_at(base, cwd)
    if tip and tip != base:
        for slug, ns in numbers_at(tip, cwd).items():
            numbers.setdefault(slug, set()).update(ns)
    for slug in sorted(numbers):
        had = numbers[slug]
        for k in sorted(folders_now(slug, cwd)):
            if f"games/{slug}/v{k}/" not in published_dirs and k <= max(had, default=0):
                found.append(f"games/{slug}/v{k}/: a new version takes a number above v{max(had)}, never an old one")
    lib = git("diff", "--name-status", "--no-renames", base, "--", "public/lib", cwd=cwd).splitlines()
    for line in lib:
        status, path = line.split("\t", 1)
        if status != "A":
            found.append(f"{path}: a published library file never changes; add a new folder for a new release")
    return found


def merge_base(ref: str, cwd: str | None = None) -> str | None:
    """The commit this branch left `ref` at, or None when git cannot tell (#555).

    Comparing with `ref`'s current tip would blame the branch for every version `ref` published
    since: a release landing on main while a branch's check runs failed it. On a pull request in
    CI, HEAD is GitHub's merge commit, whose merge base with the base branch is the tip it was
    built on, so CI compares as before. `problems()` also reads the numbers at `ref`'s tip.
    """
    try:
        return git("merge-base", "HEAD", ref, cwd=cwd).strip() or None
    except subprocess.CalledProcessError:
        return None


def main() -> int:
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    found_base = merge_base(ref)
    # No merge base (an unknown ref, unrelated history): compare with the ref itself, as before.
    base = found_base or ref
    found = problems(base, tip=ref)
    for p in found:
        print(f"check_immutable: {p}", file=sys.stderr)
    if not found:
        since = f"merge base {found_base[:12]}" if found_base else "no merge base found, compared with it"
        print(f"check_immutable: no published version changed since {ref} ({since})")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
