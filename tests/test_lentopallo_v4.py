"""Lentopallo v4: playable with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/lentopallo/v4/"
LANDSCAPE = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def phone(site, browser):
    # Only this game is built, so another game's unfinished folder cannot break the build.
    shutil.copytree(ROOT / "games" / "lentopallo", site.games / "lentopallo")
    site.build()
    contexts = []

    def open_at(width, height):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.evaluate("localStorage.setItem('ai-pelit:lentopallo:kaverit', '{\"voitot\":2,\"haviot\":1}')")
        page.reload()
        return page

    yield open_at
    for ctx in contexts:
        ctx.close()


def inside(box, width, height):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height


@pytest.mark.parametrize("size", LANDSCAPE)
def test_menu_fits_sideways(phone, size):
    w, h = size
    page = phone(w, h)
    # The end-of-match menu is the longest one.
    page.evaluate("showMenu('Voitit 11–9! 🏆', 'win')")
    for sel in ("#menu h1", "#result", "#foe", "#m1", "#m2", "#go", "#multi", "#stats", "#menu .help.short", "#ai-pelit-back"):
        box = page.locator(sel).bounding_box()
        assert box and inside(box, w, h), (sel, box)
    assert not page.locator("#menu .help.long").is_visible()
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    chip, title = page.locator("#ai-pelit-back").bounding_box(), page.locator("#menu h1").bounding_box()
    assert chip["y"] + chip["height"] <= title["y"] or chip["x"] + chip["width"] <= title["x"]
    # The buttons are clickable (nothing covers them).
    page.click("#m2")
    assert page.evaluate("mode") == "2v2"
    page.click("#m1")
    page.click("#multi")
    page.wait_for_selector("#aipr-create", state="visible")
    assert page.errors == []


def test_portrait_keeps_v3s_layout(phone):
    page = phone(360, 740)
    assert page.locator("#menu .help.long").is_visible()
    assert not page.locator("#menu .help.short").is_visible()
    page.click("#go")
    assert page.evaluate("[Math.round(sc * 100), Math.round(groundY), Math.round(ctrlTop), buttons.map(b => [Math.round(b.x), Math.round(b.y), Math.round(b.r)])]") == \
        [3462, 528, 562, [[62, 655, 46], [172, 655, 46], [287, 655, 58]]]


def test_a_match_runs_sideways_and_survives_turning_the_phone(phone):
    page = phone(740, 360)
    page.click("#m2")
    page.click("#go")
    # The court, the buttons and the scoreboard all fit, and the buttons sit in the lower corners
    # below the sand line, clear of the players.
    assert page.evaluate("""sx(-EDGE) > buttons[1].x && sx(EDGE) < W
      && buttons.every(b => b.x - b.r >= 0 && b.x + b.r <= W && b.y + b.r <= H && b.y - b.r >= groundY)
      && buttons[1].x < W / 3 && buttons[2].x > W * 2 / 3""")
    # Steer and serve through the on-screen buttons.
    page.touchscreen.tap(*page.evaluate("[buttons[2].x, buttons[2].y]"))
    page.wait_for_function("crossings >= 1", timeout=4000)
    page.evaluate("score = [3, 2]")
    players = page.evaluate("players.length")
    # Turn the phone mid-match (back.js went fullscreen on the tap; Chromium cannot resize that).
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_function("W === 360 && !wide")
    page.wait_for_timeout(300)
    assert page.evaluate("[score[0] + score[1] >= 5, players.length, state !== 'menu' && state !== 'done']") == [True, players, True]
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_function("W === 740 && wide")
    page.wait_for_timeout(300)
    assert page.evaluate("[score[0] + score[1] >= 5, state !== 'menu' && state !== 'done']") == [True, True]
    assert page.evaluate("document.getElementById('menu').classList.contains('hidden')")
    assert page.errors == []
