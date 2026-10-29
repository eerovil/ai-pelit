#!/usr/bin/env python3
"""Fail when a change edits a game version that is already published.

    python3 scripts/check_immutable.py origin/main

A published version is a `games/<slug>/v<N>/` folder that exists at the base ref. Its files
may not change, and its entry in game.json may not change either; new versions are appended.
"""

import json
import re
import subprocess
import sys

VERSION_FILE = re.compile(r"^games/([^/]+)/(v\d+)/")


def git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


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
            found.append(f"{path}: {m.group(1)} {m.group(2)} is published; make a new version instead")
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
