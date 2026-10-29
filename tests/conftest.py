import functools
import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402

BACK = build.BACK_SCRIPT

# A pull request runs a game's own tests only when it touches that game (#37): every version folder
# is self-contained, so a change to one game cannot break another. A change anywhere outside
# games/ (public/, scripts/, server/, the tests' own helpers...) can, and runs everything.
# A game's tests are tests/test_<slug>.py or tests/test_<slug>_<more>.py (dashes as underscores),
# or any test module that says `pytestmark = pytest.mark.games("<slug>", ...)`.
CHANGED_GAMES = pytest.StashKey[set | None]()
REAL_GAMES = sorted((p.name for p in (ROOT / "games").iterdir() if p.is_dir()), key=len, reverse=True)


def pytest_addoption(parser):
    parser.addoption(
        "--changed-since", metavar="REF",
        help="run each game's own tests only if the changes since REF (and uncommitted ones) touch that game",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "games(*slugs): the games whose folders these tests play")
    ref = config.getoption("--changed-since")
    config.stash[CHANGED_GAMES] = changed_games(changed_paths(ref)) if ref else None


def changed_paths(ref: str) -> list[str] | None:
    """Every path changed on this branch since it left REF, committed or not; None if git can't say."""
    paths = []
    for cmd in (["diff", "--name-only", f"{ref}...HEAD"], ["diff", "--name-only", "HEAD"],
                ["ls-files", "--others", "--exclude-standard"]):
        run = subprocess.run(["git", *cmd], cwd=ROOT, capture_output=True, text=True)
        if run.returncode != 0:
            return None
        paths += run.stdout.split()
    return paths


def changed_games(paths: list[str] | None) -> set[str] | None:
    """The games these paths touch, or None when a path outside any one game means test everything."""
    if paths is None:
        return None
    games = set()
    for path in paths:
        parts = path.split("/")
        if parts[0] == "games" and len(parts) > 2:
            games.add(parts[1])
        elif parts[0] == "tests" and len(parts) == 2 and (game := game_of_test_file(parts[1])):
            games.add(game)
        elif not (parts[0] == "docs" or path.endswith(".md")):
            return None
    return games


def game_of_test_file(name: str) -> str | None:
    stem = name.removesuffix(".py").removeprefix("test_")
    for slug in REAL_GAMES:
        under = slug.replace("-", "_")
        if stem == under or stem.startswith(under + "_"):
            return slug
    return None


def games_of(item) -> set[str]:
    marker = item.get_closest_marker("games")
    if marker:
        return set(marker.args)
    game = game_of_test_file(item.path.name)
    return {game} if game else set()


def pytest_collection_modifyitems(config, items):
    changed = config.stash[CHANGED_GAMES]
    if changed is None:
        return
    keep, drop = [], []
    for item in items:
        games = games_of(item)
        (drop if games and not games & changed else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


def pytest_report_header(config):
    if not config.getoption("--changed-since"):
        return None
    changed = config.stash[CHANGED_GAMES]
    if changed is None:
        return "changed outside games/ (or git could not say): testing every game"
    return f"games changed: {', '.join(sorted(changed)) or 'none'}; other games' own tests are skipped"


@pytest.fixture
def changed_games_only(request):
    """The games a --changed-since run tests, or None for all of them."""
    return request.config.stash[CHANGED_GAMES]


def game_page(title: str, body: str = "", script: str = "") -> str:
    return (
        f'<!doctype html><html lang="fi"><head><meta charset="utf-8"><title>{title}</title></head>'
        f"<body>{body}<script>{script}</script>\n{BACK}\n</body></html>\n"
    )


def make_game(games: Path, slug: str, pages: list[str], title: str | None = None, dates=None) -> None:
    d = games / slug
    d.mkdir(parents=True, exist_ok=True)
    versions = []
    for i, page in enumerate(pages, start=1):
        (d / f"v{i}").mkdir(exist_ok=True)
        (d / f"v{i}" / "index.html").write_text(page)
        date = dates[i - 1] if dates else f"2026-10-{i:02d}"
        versions.append({"n": i, "date": date, "note": f"Versio {i}", "request": "", "issue": None})
    meta = {"title": title or slug.capitalize(), "description": f"Peli {slug}", "versions": versions}
    (d / "game.json").write_text(json.dumps(meta))


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
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    yield ctx
    ctx.close()


def wait_for_worker(page) -> None:
    page.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller !== null", timeout=10000)
