import base64
import functools
import http.server
import json
import re
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402

BACK = build.BACK_SCRIPT
# A plain 360 x 480 WebP, every test game's shelf picture.
THUMB = base64.b64decode("UklGRi4AAABXRUJQVlA4TCEAAAAvZ8F3AAdQvKIUuf8BAkmb98+/7RH9z93/+3//7//9ZwwA")

# A pull request runs a game's own tests only when it touches that game (#37): every version folder
# is self-contained, so a change to one game cannot break another. A change outside games/
# (public/, scripts/, server/, the tests' own helpers...) runs only the shared tests, the ones tied
# to no game: the full suite never runs in CI (#65, Eero's choice), it took about 6 minutes.
# A game's tests are tests/test_<slug>.py or tests/test_<slug>_<more>.py (dashes as underscores),
# or any test module that says `pytestmark = pytest.mark.games("<slug>", ...)`.
# Within a game, a test file runs only for the versions it tests (#116): a published version never
# changes, so a new v9 does not run v1-v8's tests again. A file's versions are the _v<N> in its name
# and every games/<slug>/v<N> written in it. Everything of the game runs when one of its test files
# changes (they import each other's helpers), when a file under games/<slug>/ other than a version
# folder, game.json or thumb.webp changes, or when a changed version is named by no test file.
CHANGES = pytest.StashKey["Changes"]()
REAL_GAMES = sorted((p.name for p in (ROOT / "games").iterdir() if p.is_dir()), key=len, reverse=True)
# Files beside a game's version folders that scripts/build.py already checks: changing only them
# runs none of the game's browser tests.
GAME_FILES_BUILD_CHECKS = {"game.json", build.THUMB}


class Changes:
    """What a pull request changes, as far as choosing its tests goes."""

    def __init__(self, paths: list[str], new: list[str] = ()):
        self.games = changed_games(paths)
        self.versions = changed_versions(paths)
        # A test file new on this branch runs itself only: no other test imports it yet, and a new
        # version always brings one (#116). An edited test file may be imported, so it runs its game.
        self.whole_games = whole_games_changed([p for p in paths if p not in set(new)])
        self.test_files = {p.split("/")[1] for p in paths if p.startswith("tests/") and p.count("/") == 1}


def pytest_addoption(parser):
    parser.addoption(
        "--changed-since", metavar="REF",
        help="run each game's own tests only if the changes since REF (and uncommitted ones) touch that game",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "games(*slugs): the games whose folders these tests play")
    config.addinivalue_line("markers", "alone: a heavy 3D test that runs one at a time, never beside others")
    ref = config.getoption("--changed-since")
    if ref:
        config.stash[CHANGES] = Changes(changed_paths(ref), changed_paths(ref, only_new=True))


def changed_paths(ref: str, only_new: bool = False) -> list[str]:
    """Every path changed on this branch since it left REF, committed or not; none if git can't say.
    With only_new, just the paths that did not exist at REF (added, or not yet known to git)."""
    paths = []
    added = ["--diff-filter=A"] if only_new else []
    # -z: names as they are, never split at a space or quoted for a letter like ä.
    for cmd in (["diff", "-z", "--name-only", *added, f"{ref}...HEAD"], ["diff", "-z", "--name-only", *added, "HEAD"],
                ["ls-files", "-z", "--others", "--exclude-standard"]):
        run = subprocess.run(["git", *cmd], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        if run.returncode != 0:
            return []
        paths += [p for p in run.stdout.split("\0") if p]
    return paths


def _split(paths: list[str]):
    for path in paths:
        parts = path.split("/")
        if "__pycache__" not in parts:
            yield parts


def changed_games(paths: list[str]) -> set[str]:
    """The games these paths touch; a path outside any one game adds none."""
    games = set()
    for parts in _split(paths):
        if parts[0] == "games" and len(parts) > 2:
            games.add(parts[1])
        elif parts[0] == "tests" and len(parts) == 2 and (game := game_of_test_file(parts[1])):
            games.add(game)
    return games


def changed_versions(paths: list[str]) -> dict[str, set[int]]:
    """Each game's version folders these paths touch: {"hiihto": {9}}."""
    versions: dict[str, set[int]] = {}
    for parts in _split(paths):
        if parts[0] == "games" and len(parts) > 3 and (m := re.fullmatch(r"v(\d+)", parts[2])):
            versions.setdefault(parts[1], set()).add(int(m[1]))
    return versions


def whole_games_changed(paths: list[str]) -> set[str]:
    """The games whose every test runs: one of their test files changed, or a file of the game
    outside its version folders that the build does not check."""
    games = set()
    for parts in _split(paths):
        if parts[0] == "tests" and len(parts) == 2 and (game := game_of_test_file(parts[1])):
            games.add(game)
        elif (parts[0] == "games" and len(parts) > 2 and not re.fullmatch(r"v\d+", parts[2])
              and not (len(parts) == 3 and parts[2] in GAME_FILES_BUILD_CHECKS)):
            games.add(parts[1])
    return games


def game_of_test_file(name: str) -> str | None:
    stem = name.removesuffix(".py").removeprefix("test_")
    for slug in REAL_GAMES:
        under = slug.replace("-", "_")
        if stem == under or stem.startswith(under + "_"):
            return slug
    return None


@functools.cache
def versions_of_test_file(path: Path, slug: str) -> frozenset[int]:
    """The versions of SLUG a test file tests: the _v<N> in its name, and every games/<slug>/v<N> in it."""
    rest = path.name.removesuffix(".py").removeprefix("test_")[len(slug):]
    versions = {int(m[1])} if (m := re.match(r"_v(\d+)(?:_|$)", rest)) else set()
    versions |= {int(n) for n in re.findall(rf"games/{re.escape(slug)}/v(\d+)", path.read_text(encoding="utf-8"))}
    return frozenset(versions)


def versions_with_tests(tests: Path, slug: str) -> frozenset[int]:
    """Every version of SLUG that some test file of it in TESTS names."""
    return frozenset().union(*(versions_of_test_file(p, slug) for p in tests.glob("test_*.py")
                               if game_of_test_file(p.name) == slug))


def games_of(item) -> set[str]:
    marker = item.get_closest_marker("games")
    if marker:
        return set(marker.args)
    game = game_of_test_file(item.path.name)
    return {game} if game else set()


def runs(item, changes: Changes) -> bool:
    """Whether a pull request with these changes runs this test."""
    games = games_of(item)
    if not games:
        return True  # a shared test
    if item.get_closest_marker("games"):
        return bool(games & changes.games)
    (slug,) = games
    if slug in changes.whole_games or item.path.name in changes.test_files:
        return True
    changed = changes.versions.get(slug, set())
    if not changed:
        return False  # nothing of the game, or only its game.json or thumbnail
    mine = versions_of_test_file(item.path, slug)
    return not mine or bool(mine & changed) or bool(changed - versions_with_tests(item.path.parent, slug))


@functools.cache
def is_3d(path: Path, slug: str) -> bool:
    """Whether a game's test file plays a version drawn with three.js (one that loads lib/three)."""
    versions = versions_of_test_file(path, slug) or {
        int(d.name[1:]) for d in (ROOT / "games" / slug).glob("v*") if d.name[1:].isdigit()}
    return any("lib/three" in page.read_text(encoding="utf-8")
               for v in versions if (page := ROOT / "games" / slug / f"v{v}" / "index.html").exists())


# Tests of 3D games run alone, never beside other tests (#116): software WebGL on CI's four cores
# leaves too few frames for their timed races when other Chromiums run at the same time. CI runs
# `-m "not alone"` on four workers, then `-m alone` one at a time.
@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        if not item.get_closest_marker("games") and (slug := game_of_test_file(item.path.name)) \
                and is_3d(item.path, slug):
            item.add_marker("alone")
    if CHANGES not in config.stash:
        return
    changes = config.stash[CHANGES]
    keep, drop = [], []
    for item in items:
        (keep if runs(item, changes) else drop).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


def pytest_terminal_summary(terminalreporter, config):
    # A summary line, not a report header: `pytest -q`, as CI runs it, leaves the header out.
    if not config.getoption("--changed-since"):
        return
    changes = config.stash[CHANGES]
    games = [
        f"{g} ({', '.join(f'v{v}' for v in sorted(changes.versions[g]))})" if changes.versions.get(g) else g
        for g in sorted(changes.games)
    ]
    terminalreporter.write_line(
        f"games changed: {', '.join(games) or 'none'}; other games' and versions' own tests were skipped")


@pytest.fixture
def changed_games_only(request):
    """The games a --changed-since run tests, or None for all of them."""
    changes = request.config.stash.get(CHANGES, None)
    return changes.games if changes else None


def game_page(title: str, body: str = "", script: str = "") -> str:
    return (
        f'<!doctype html><html lang="fi"><head><meta charset="utf-8"><title>{title}</title></head>'
        f"<body>{body}<script>{script}</script>\n{BACK}\n</body></html>\n"
    )


def make_game(games: Path, slug: str, pages: list[str], title: str | None = None, dates=None, group: str | None = None) -> None:
    d = games / slug
    d.mkdir(parents=True, exist_ok=True)
    versions = []
    for i, page in enumerate(pages, start=1):
        (d / f"v{i}").mkdir(exist_ok=True)
        (d / f"v{i}" / "index.html").write_text(page)
        date = dates[i - 1] if dates else f"2026-10-{i:02d}"
        versions.append({"n": i, "date": date, "note": f"Versio {i}", "request": "", "issue": None})
    meta = {"title": title or slug.capitalize(), "description": f"Peli {slug}", "versions": versions}
    if group:
        meta["group"] = group
    (d / "game.json").write_text(json.dumps(meta))
    (d / build.THUMB).write_bytes(THUMB)


class Site:
    """A built site served at the root of http://127.0.0.1:<port>/, as pelit.vilpponen.fi serves it."""

    def __init__(self, tmp: Path):
        self.games = tmp / "games"
        self.games.mkdir()
        self.out = tmp / "www"
        self.root = self.out
        handler = functools.partial(QuietHandler, directory=str(self.root))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"

    def build(self, games: Path | None = None) -> dict:
        return build.build(games or self.games, ROOT / "public", self.out)

    def close(self) -> None:
        self.server.shutdown()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".webmanifest": "application/manifest+json"}

    def send_head(self):
        # The stdlib compares If-Modified-Since in whole seconds, so a rebuild in the same second
        # would answer 304 with the old file. GitHub Pages compares ETags and has no such gap.
        del self.headers["If-Modified-Since"]
        return super().send_head()

    def end_headers(self):
        # GitHub Pages sends max-age=600; the app must update in spite of it.
        self.send_header("Cache-Control", "max-age=600")
        super().end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def site(tmp_path):
    s = Site(tmp_path)
    yield s
    s.close()


@pytest.fixture(scope="session")
def _playwright():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


# A fresh Chromium for each test file (#95). With one browser for the whole run, the 3D games'
# WebGL pages (Hiihto from v7, Pallorata) slowed it down for every file after them on CI, until
# their rounds timed out.
@pytest.fixture(scope="module")
def browser(_playwright):
    b = _playwright.chromium.launch()
    yield b
    b.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    yield ctx
    ctx.close()


def turn(page, size: dict) -> None:
    """Turns the phone: resizes the page's window to size, {"width": ..., "height": ...} (#95).

    back.js puts the page in full screen on the first tap, and Chromium refuses to resize a
    full-screen window. Leaving it from the page (document.exitFullscreen()) finishes some time
    later, too late on a busy machine; so the window is set back to normal through the browser
    itself first, which takes effect before the resize.
    """
    cdp = page.context.new_cdp_session(page)
    try:
        win = cdp.send("Browser.getWindowForTarget")["windowId"]
        if cdp.send("Browser.getWindowBounds", {"windowId": win})["bounds"].get("windowState") != "normal":
            cdp.send("Browser.setWindowBounds", {"windowId": win, "bounds": {"windowState": "normal"}})
    finally:
        cdp.detach()
    page.set_viewport_size(size)


def wait_for_worker(page) -> None:
    page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=10000)
