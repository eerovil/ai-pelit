import base64
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402

BACK = build.BACK_SCRIPT
# A 3 x 4 WebP, every test game's shelf picture.
THUMB = base64.b64decode("UklGRjwAAABXRUJQVlA4IDAAAADwAQCdASoDAAQAAUAmJaACdLoB+AAETAAA/uxw3/0mzxNnibPkkf/OwbEu14AAAAA=")


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
