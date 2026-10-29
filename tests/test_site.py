"""The app in a phone-sized Chromium: the shelf, playing, installing, updating, offline, saves."""

import json

import pytest

from conftest import ROOT, game_page, make_game, wait_for_worker

SAVE_V1 = "localStorage.setItem('ai-pelit:tallennus:paras', '7'); document.title = 'tallennettu';"
SAVE_V2 = "document.title = 'paras ' + localStorage.getItem('ai-pelit:tallennus:paras');"


def errors_on(page):
    found = []
    page.on("console", lambda m: m.type == "error" and found.append(m.text))
    page.on("pageerror", lambda e: found.append(str(e)))
    return found


def test_every_real_version_loads_without_errors(site, context):
    catalog = site.build(ROOT / "games")
    # The test server has no /api/: answer the play counts (#26) every page sends as the real one does.
    context.route("**/api/plays", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"ok": true}' if route.request.method == "POST" else '{"games": {}}'))
    page = context.new_page()
    found = errors_on(page)
    for game in catalog["games"]:
        # Back to the shelf for each game: the loop below leaves the page on a game.
        page.goto(site.url)
        assert page.locator(f'.card[data-slug="{game["slug"]}"]').is_visible()
        for v in game["versions"]:
            page.goto(f'{site.url}games/{game["slug"]}/v{v["n"]}/')
            page.wait_for_selector("#ai-pelit-back")
            page.wait_for_timeout(300)
    assert found == []


def test_shelf_game_page_and_back_chip(site, context):
    make_game(site.games, "pomppu", [game_page("v1"), game_page("v2")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.click('.card[data-slug="pomppu"] .card-main')
    page.wait_for_selector(".version")
    assert page.locator(".version").count() == 2
    assert page.locator(".version").first.get_attribute("data-n") == "2"
    assert "Pomppu v3 (pomppu): " in page.locator(".copy textarea").input_value()
    page.click('.version[data-n="1"] a')
    page.wait_for_url("**/games/pomppu/v1/")
    page.click("#ai-pelit-back")
    page.wait_for_selector("h1")
    assert page.url == f"{site.url}#/pomppu"
    assert page.locator("h1").inner_text() == "Pomppu"


@pytest.mark.parametrize("path", ["games/pomppu/v1/", "games/pomppu/v1/index.html"])
def test_back_chip_finds_the_game_from_either_address(site, context, path):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url + path)
    assert page.get_attribute("#ai-pelit-back", "href") == f"{site.url}#/pomppu"


def test_a_tap_on_the_back_chip_never_reaches_the_game(site, context):
    events = ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"]
    listen = "window.seen = []; " + "".join(
        f"window.addEventListener('{e}', () => window.seen.push('{e}'));" for e in events
    )
    make_game(site.games, "pomppu", [game_page("v1", script=listen)])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    # Stop the navigation so the game page can still be asked what it saw.
    page.evaluate("document.getElementById('ai-pelit-back').addEventListener('click', e => e.preventDefault())")
    page.tap("#ai-pelit-back")
    page.click("#ai-pelit-back")
    assert page.evaluate("window.seen") == []


def test_a_tap_in_a_game_makes_it_full_screen_but_a_tap_on_the_chip_does_not(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.evaluate("document.getElementById('ai-pelit-back').addEventListener('click', e => e.preventDefault())")
    page.tap("#ai-pelit-back")
    assert page.evaluate("document.fullscreenElement") is None
    page.touchscreen.tap(180, 400)
    page.wait_for_function("document.fullscreenElement === document.documentElement")


def test_the_installed_app_opens_full_screen(site):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    manifest = json.loads((site.root / "manifest.webmanifest").read_text())
    assert manifest["display"] == "fullscreen"


def test_a_game_can_move_the_back_chip(site, context):
    page_html = game_page("x").replace('back.js"></script>', 'back.js" data-corner="bottom-left"></script>')
    make_game(site.games, "kulma", [page_html])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/kulma/v1/")
    box = page.locator("#ai-pelit-back").bounding_box()
    assert box["x"] < 20 and box["y"] > 600


def test_chrome_can_install_it(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    cdp = context.new_cdp_session(page)
    errors = cdp.send("Page.getInstallabilityErrors")["installabilityErrors"]
    assert errors == []
    manifest = cdp.send("Page.getAppManifest")
    assert not manifest.get("errors")


def test_a_new_game_shows_without_reinstalling_and_a_game_is_not_reloaded(site, context):
    make_game(site.games, "eka", [game_page("eka")])
    site.build()
    shelf = context.new_page()
    shelf.goto(site.url)
    wait_for_worker(shelf)
    game = context.new_page()
    game.goto(f"{site.url}games/eka/v1/")
    game.evaluate("window.kesken = true")

    make_game(site.games, "toka", [game_page("toka")])
    site.build()
    # Coming back to the screen is what a phone does when the app is reopened.
    shelf.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    shelf.wait_for_selector('.card[data-slug="toka"]', timeout=10000)
    # The new worker takes over; the shelf reloads for it, the game in progress does not.
    shelf.wait_for_function(
        "caches.keys().then(k => k.filter(n => n.startsWith('ai-pelit-shell-')).length === 1)", timeout=10000
    )
    shelf.wait_for_selector('.card[data-slug="toka"]')
    assert game.evaluate("window.kesken") is True


def test_a_played_version_and_the_shelf_work_offline(site, context):
    make_game(site.games, "pomppu", [game_page("Pomppu yksi")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/pomppu/v1/")
    context.set_offline(True)
    try:
        page.goto(f"{site.url}games/pomppu/v1/")
        assert page.title() == "Pomppu yksi"
        page.goto(site.url)
        page.wait_for_selector('.card[data-slug="pomppu"]')
    finally:
        context.set_offline(False)


def test_a_new_version_keeps_the_save_and_an_update_does_not_touch_it(site, context):
    make_game(site.games, "tallennus", [game_page("v1", script=SAVE_V1), game_page("v2", script=SAVE_V2)])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(f"{site.url}games/tallennus/v1/")
    assert page.title() == "tallennettu"

    make_game(site.games, "uusi", [game_page("uusi")])
    site.build()
    page.goto(site.url)
    page.wait_for_selector('.card[data-slug="uusi"]', timeout=10000)
    page.goto(f"{site.url}games/tallennus/v2/")
    assert page.title() == "paras 7"


@pytest.mark.parametrize("width", [360])
def test_shelf_fits_a_small_phone(site, context, width):
    make_game(site.games, "pitka-nimi", [game_page("x")], title="Hyvin pitkä pelin nimi joka jatkuu ja jatkuu")
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    assert page.evaluate("document.documentElement.scrollWidth") <= width
