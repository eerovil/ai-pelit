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


def test_every_real_version_loads_without_errors(site, context, changed_games_only):
    catalog = site.build(ROOT / "games")
    # The test server has no /api/: answer the play counts (#26) every page sends as the real one does.
    context.route("**/api/plays", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"ok": true}' if route.request.method == "POST" else '{"games": {}}'))
    # ...and each game's no. 1 the shelf cards show (#25).
    context.route("**/api/scores/top", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"games": {}}'))
    page = context.new_page()
    found = errors_on(page)
    for game in catalog["games"]:
        if changed_games_only is not None and game["slug"] not in changed_games_only:
            continue
        # Back to the shelf for each game: the loop below leaves the page on a game.
        # A game in a shelf group (#153) has its card on the group's page.
        page.goto(site.url + ("#/" + game["group"] if game.get("group") else ""))
        # The shelf draws its cards after fetching catalog.json: wait for the card, a busy runner
        # can take longer than the page's load event (#123).
        page.wait_for_selector(f'.card[data-slug="{game["slug"]}"]', state="visible")
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
    page.wait_for_function("document.querySelector('.card[data-slug=\"pomppu\"] img.thumb')?.naturalWidth > 0")
    assert page.locator("textarea").count() == 0
    # The round play button opens the latest version (#33, layout D).
    assert page.get_attribute('.card[data-slug="pomppu"] a.play', "href") == "games/pomppu/v2/"
    page.click('.card[data-slug="pomppu"] .card-main')
    page.wait_for_selector(".version")
    assert page.locator(".version").count() == 2
    assert page.locator(".version").first.get_attribute("data-n") == "2"
    # The game's picture shows at the top; the copy-text box is gone (#33).
    page.wait_for_function("document.querySelector('img.thumb.big')?.naturalWidth > 0")
    assert page.locator("textarea").count() == 0
    page.click('.version[data-n="1"] a')
    page.wait_for_url("**/games/pomppu/v1/")
    page.click("#ai-pelit-back")
    page.wait_for_selector("h1")
    assert page.url == f"{site.url}#/pomppu"
    assert page.locator("h1").inner_text() == "Pomppu"


def test_back_from_a_game_goes_up_to_its_page_then_the_shelf_then_out(site, context):
    # The chip and the phone's back both go up, never back into the game (#68).
    make_game(site.games, "pomppu", [game_page("v1"), game_page("v2")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.click('.card[data-slug="pomppu"] .card-main')
    page.click('.version[data-n="1"] a')
    page.wait_for_url("**/games/pomppu/v1/")
    # A reload in the game (the phone woke it, or the app restarted) still knows its page is below.
    page.reload()
    page.wait_for_selector("#ai-pelit-back")
    page.click("#ai-pelit-back")
    page.wait_for_url(f"{site.url}#/pomppu")
    assert page.locator("h1").inner_text() == "Pomppu"
    page.go_forward()
    page.wait_for_url("**/games/pomppu/v1/")
    page.go_back()
    page.wait_for_url(f"{site.url}#/pomppu")
    page.go_back()
    page.wait_for_selector('.card[data-slug="pomppu"]')
    assert "#/pomppu" not in page.url
    page.go_back()
    assert page.url == "about:blank"


def test_a_group_is_one_card_on_the_shelf_and_its_games_go_up_to_it(site, context):
    # Shelf groups (#153): the group's card sits where its newest game would, and each level's
    # back goes one step up: game -> its page -> the group -> the shelf -> out.
    make_game(site.games, "vanha", [game_page("v1")], dates=["2026-01-01"])
    make_game(site.games, "keihas", [game_page("v1")], dates=["2026-02-01"], group="yleisurheilu", title="Keihäs")
    make_game(site.games, "hyppy", [game_page("v1")], dates=["2026-03-01"], group="yleisurheilu", title="Hyppy")
    make_game(site.games, "uusi", [game_page("v1")], dates=["2026-04-01"])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    assert page.eval_on_selector_all(".cards > .card", "cs => cs.map(c => c.dataset.slug)") == ["uusi", "yleisurheilu", "vanha"]
    assert page.locator('.card[data-slug="yleisurheilu"] .desc').inner_text() == "Hyppy, Keihäs"
    page.click('.card[data-slug="yleisurheilu"] .card-main')
    page.wait_for_url(f"{site.url}#/yleisurheilu")
    assert page.locator("h1").inner_text() == "Yleisurheilu"
    assert page.eval_on_selector_all(".card", "cs => cs.map(c => c.dataset.slug)") == ["hyppy", "keihas"]
    page.click('.card[data-slug="keihas"] .card-main')
    page.wait_for_selector(".version")
    assert page.locator("a.back").inner_text() == "‹ Yleisurheilu"
    page.click('.version[data-n="1"] a')
    page.wait_for_url("**/games/keihas/v1/")
    page.click("#ai-pelit-back")
    page.wait_for_url(f"{site.url}#/keihas")
    page.click("a.back")
    page.wait_for_url(f"{site.url}#/yleisurheilu")
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="uusi"]')
    page.go_back()
    assert page.url == "about:blank"


def test_a_game_played_from_its_groups_page_goes_back_through_its_own_page(site, context):
    make_game(site.games, "hyppy", [game_page("v1")], group="yleisurheilu", title="Hyppy")
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.click('.card[data-slug="yleisurheilu"] a.play')
    page.wait_for_url(f"{site.url}#/yleisurheilu")
    page.click('.card[data-slug="hyppy"] a.play')
    page.wait_for_url("**/games/hyppy/v1/")
    page.go_back()
    page.wait_for_url(f"{site.url}#/hyppy")
    page.go_back()
    page.wait_for_url(f"{site.url}#/yleisurheilu")


def test_a_groups_game_opened_from_a_link_goes_up_to_the_group(site, context):
    make_game(site.games, "hyppy", [game_page("v1")], group="yleisurheilu", title="Hyppy")
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}#/hyppy")
    page.click("a.back")
    page.wait_for_url(f"{site.url}#/yleisurheilu")
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="yleisurheilu"]')


@pytest.mark.parametrize("width", [360, 390])
def test_a_group_page_fits_a_small_phone(site, context, width):
    for slug in ("pitka", "toinen"):
        make_game(site.games, slug, [game_page("v1")], group="yleisurheilu", title="Hyvin pitkä pelin nimi " + slug)
    site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": 740})
    for hash_ in ("", "#/yleisurheilu"):
        page.goto(site.url + hash_)
        page.wait_for_selector(".card")
        assert page.evaluate("document.documentElement.scrollWidth") <= width


def test_a_game_joining_a_group_moves_into_its_card_on_an_open_shelf(site, context):
    make_game(site.games, "keihas", [game_page("v1")], group="yleisurheilu")
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector('.card[data-slug="hyppy"]')
    # A reload on the group's page keeps it.
    page.click('.card[data-slug="yleisurheilu"] .card-main')
    page.wait_for_url(f"{site.url}#/yleisurheilu")
    page.reload()
    page.wait_for_selector('.card[data-slug="keihas"]')
    assert page.locator("h1").inner_text() == "Yleisurheilu"
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="hyppy"]')
    make_game(site.games, "hyppy", [game_page("v1")], group="yleisurheilu")
    site.build()
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_selector('.card[data-slug="hyppy"]', state="detached", timeout=10000)
    assert page.locator('.card[data-slug="yleisurheilu"] .meta').inner_text().startswith("2 peliä")


@pytest.mark.parametrize("start, target, ups", [
    ("vanha", "hyppy", ["#/hyppy", "#/yleisurheilu", ""]),
    ("hyppy", "vanha", ["#/vanha", ""]),
    ("hyppy", "keihas", ["#/keihas", "#/yleisurheilu", ""]),
])
def test_a_room_code_for_another_game_keeps_that_games_own_way_up(site, context, start, target, ups):
    # rooms.js steps back to the first game's page and leaves this note (moninpeli.md); the page
    # below becomes the target game's, under its own group's page when it has one.
    make_game(site.games, "vanha", [game_page("v1")])
    make_game(site.games, "hyppy", [game_page("v1")], group="yleisurheilu")
    make_game(site.games, "keihas", [game_page("v1")], group="yleisurheilu")
    site.build()
    page = context.new_page()
    page.goto(site.url)
    if start != "vanha":
        page.click('.card[data-slug="yleisurheilu"] .card-main')
        page.wait_for_url(f"{site.url}#/yleisurheilu")
    page.click(f'.card[data-slug="{start}"] .card-main')
    page.wait_for_url(f"{site.url}#/{start}")
    page.evaluate("""([s, t]) => sessionStorage.setItem('ai-pelit:_avaa',
        JSON.stringify({ from: '#/' + s, page: '#/' + t, game: 'games/' + t + '/v1/' }))""", [start, target])
    page.reload()
    page.wait_for_url(f"**/games/{target}/v1/")
    for hash_ in ups:
        page.go_back()
        page.wait_for_url(site.url + hash_)
    page.wait_for_selector(".card")
    page.go_back()
    assert page.url == "about:blank"


def test_a_ctrl_click_opens_the_link_in_a_new_tab_as_before(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    for link, url in [(".card-main", f"{site.url}#/pomppu"), ("a.play", f"{site.url}games/pomppu/v1/")]:
        with context.expect_page() as tab:
            page.click(f'.card[data-slug="pomppu"] {link}', modifiers=["Control"])
        tab.value.wait_for_url(url)
        assert page.url == site.url
        tab.value.close()


def test_the_header_link_goes_up_too(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.click('.card[data-slug="pomppu"] .card-main')
    page.wait_for_selector(".version")
    page.click("a.brand")
    page.wait_for_selector('.card[data-slug="pomppu"]')
    page.go_back()
    assert page.url == "about:blank"


def test_back_from_a_game_opened_with_the_play_button_goes_to_its_page(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    page.click('.card[data-slug="pomppu"] a.play')
    page.wait_for_url("**/games/pomppu/v1/")
    page.go_back()
    page.wait_for_selector("h1")
    assert page.url == f"{site.url}#/pomppu"
    assert page.locator("h1").inner_text() == "Pomppu"
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="pomppu"]')
    page.go_back()
    assert page.url == "about:blank"


def test_the_chip_on_a_game_opened_from_a_link_never_leads_back_into_it(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.click("#ai-pelit-back")
    page.wait_for_url(f"{site.url}#/pomppu")
    page.wait_for_selector("h1")
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="pomppu"]')
    page.go_back()
    assert page.url == "about:blank"


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
    page.evaluate("window.addEventListener('click', e => e.preventDefault(), true)")
    page.tap("#ai-pelit-back")
    page.click("#ai-pelit-back")
    assert page.evaluate("window.seen") == []


def test_a_tap_in_a_game_makes_it_full_screen_but_a_tap_on_the_chip_does_not(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.evaluate("window.addEventListener('click', e => e.preventDefault(), true)")
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


def test_every_game_picture_shows_offline_also_after_an_update(site, context):
    make_game(site.games, "eka", [game_page("eka")])
    site.build()
    page = context.new_page()
    page.goto(site.url)
    wait_for_worker(page)
    make_game(site.games, "toka", [game_page("toka")])
    site.build()
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function(
        "caches.keys().then(k => k.filter(n => n.startsWith('ai-pelit-shell-')).length === 1)", timeout=10000
    )
    # The new worker cached every picture on install, also one the shelf has not shown yet.
    page.wait_for_function("caches.open('ai-pelit-thumbs').then(c => c.keys()).then(k => k.length === 2)", timeout=10000)
    context.set_offline(True)
    try:
        page.goto(site.url)
        page.wait_for_selector('.card[data-slug="toka"]')
        page.wait_for_function(
            "[...document.querySelectorAll('img.thumb')].every(i => i.complete && i.naturalWidth > 0)"
        )
        assert page.locator("img.thumb").count() == 2
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
