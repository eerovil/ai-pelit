"""A game removed whole (#469, Ottelu): phones that cached it drop its files and go to the shelf."""

import shutil
import time

import build
from playwright.sync_api import Error as PlaywrightError
from conftest import ROOT, game_page, make_game, wait_for_worker

SHELL_CATALOG = ("caches.keys().then(k => Promise.all(k.filter(n => n.startsWith('ai-pelit-shell-'))"
                 ".map(n => caches.open(n).then(c => c.match('catalog.json')).then(r => r.json()))))")


def until(page, js, timeout=10.0):
    # page.wait_for_function takes a returned promise as true at once; page.evaluate awaits it.
    # The shelf reloads once when the new worker takes over, which may cut a check short.
    end = time.monotonic() + timeout
    while True:
        try:
            if page.evaluate(js):
                return
        except PlaywrightError:
            pass
        assert time.monotonic() < end, js
        page.wait_for_timeout(100)


GAME_FILES = "caches.open('ai-pelit-games').then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname))"


def test_a_removed_game_goes_to_the_shelf_and_its_cached_files_go(site, context):
    make_game(site.games, "vanha", [game_page("Vanha")])
    make_game(site.games, "pysyy", [game_page("Pysyy")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/vanha/v1/")
    page.goto(f"{site.url}games/pysyy/v1/")
    assert sorted(page.evaluate(GAME_FILES)) == ["/games/pysyy/v1/", "/games/vanha/v1/"]

    # The game is removed: its folder goes, and the catalog names it.
    shutil.rmtree(site.games / "vanha")
    build.build(site.games, ROOT / "public", site.out, removed={"vanha": "#469"})
    page.goto(site.url)
    until(page, SHELL_CATALOG + ".then(cs => cs.length === 1 && (cs[0].removed || []).includes('vanha'))")
    # The new worker drops the removed game's files as it takes over.
    until(page, GAME_FILES + ".then(p => p.length === 1)")
    assert page.evaluate(GAME_FILES) == ["/games/pysyy/v1/"]

    # A saved shortcut to it opens the shelf, online and offline.
    page.goto(f"{site.url}games/vanha/v1/")
    assert page.url == site.url
    page.wait_for_selector('.shelf-row[data-slug="pysyy"]')
    context.set_offline(True)
    try:
        page.goto(f"{site.url}games/vanha/v1/index.html")
        assert page.url == site.url
        page.goto(f"{site.url}games/pysyy/v1/")
        assert page.title() == "Pysyy"
    finally:
        context.set_offline(False)

    # A game the cached catalog does not list yet, but that is not removed, still opens.
    (site.out / "games" / "uusi" / "v1").mkdir(parents=True)
    (site.out / "games" / "uusi" / "v1" / "index.html").write_text(game_page("Uusi"))
    page.goto(f"{site.url}games/uusi/v1/")
    assert page.title() == "Uusi"
