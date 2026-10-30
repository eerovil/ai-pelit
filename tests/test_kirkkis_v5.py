"""Kirkkis v5: the same game played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/kirkkis/v5/"
SIDEWAYS = [(740, 360), (844, 390), (640, 360)]
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"


def open_game(site, browser, width, height):
    # Only this game is built, so another game's half-made version cannot break the test.
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis")
    site.build()
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return ctx, page


def inside(page, selector):
    """Every element matching `selector` is visible and wholly on the screen."""
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    loc = page.locator(selector)
    assert loc.count()
    for i in range(loc.count()):
        b = loc.nth(i).bounding_box()
        assert b is not None, selector
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= vw and b["y"] + b["height"] <= vh, (selector, b)


def start(page):
    """Starts a round as the player hides. back.js goes fullscreen on the first tap, and Chromium
    will not resize a fullscreen window, so the test leaves fullscreen at once."""
    page.click("#hide")
    page.wait_for_timeout(300)
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_function("!document.fullscreenElement && innerWidth === W")


MENU = ["#menu h1", "#sub", "#hide", "#seek", "#multi", ".help.short"]


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_the_menu_and_the_end_screen_fit_without_scrolling(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    for sel in MENU:
        inside(page, sel)
    assert not page.locator(".help.long").is_visible()
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight && menu.scrollWidth <= menu.clientWidth")
    for sel in ["#hide", "#seek", "#multi"]:
        page.click(sel, trial=True)  # nothing covers them
    # The end screen, with a result, the next seeker and the totals.
    page.evaluate("stats.kierrokset = 12; newRound('hide'); played = true; nextSeeker = bots[1]; showMenu()")
    for sel in MENU + ["#result", "#info", "#total"]:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight")
    assert page.errors == []
    ctx.close()


def test_sideways_a_round_runs_at_the_upright_size_with_the_hud_in_the_corner(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    start(page)
    page.wait_for_function("phase === 'count' && timer < 9.5", timeout=4000)
    page.evaluate(RUN, 10.5)
    assert page.evaluate("phase") == "seek"
    # Things are as big as upright (30 px a metre on a 360 px wide phone), and more yard shows across.
    assert page.evaluate("[wide, S]") == [True, 30]
    # The HUD is a panel in the top-right corner, clear of the back chip in the top-left.
    chip = page.locator("#ai-pelit-back").bounding_box()
    hud_x = page.evaluate("W - safeR - 8 - Math.min(290, W - safeR - 100)")
    assert hud_x > 740 / 2 and chip["x"] + chip["width"] < hud_x
    # A drag moves the player.
    x0, y0 = page.evaluate("[player.x, player.y]")
    page.mouse.move(200, 250)
    page.mouse.down()
    page.mouse.move(200, 200, steps=3)  # up, away from the base pole beside the player
    page.wait_for_timeout(1000)
    page.mouse.up()
    assert page.evaluate(f"Math.hypot(player.x - {x0}, player.y - {y0})") > 1
    assert page.errors == []
    ctx.close()


def test_turning_the_phone_mid_round_keeps_the_round(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    start(page)
    page.evaluate(RUN, 12)
    before = page.evaluate("[phase, timer, player.x, player.y, people.indexOf(seeker)]")
    assert before[0] == "seek"
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!wide && S === 30 && W === 360", timeout=3000)
    after = page.evaluate("[phase, timer, player.x, player.y, people.indexOf(seeker)]")
    assert after[0] == "seek" and before[1] - 2 < after[1] <= before[1]
    assert after[2:] == pytest.approx(before[2:], abs=0.5)
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide", timeout=3000)
    assert page.evaluate("phase") == "seek"
    assert page.errors == []
    ctx.close()


def test_upright_it_looks_as_v4(site, browser):
    ctx, page = open_game(site, browser, 360, 640)
    assert page.locator(".help.long").is_visible() and not page.locator(".help.short").is_visible()
    for sel in ["#menu h1", "#hide", "#seek", "#multi"]:
        inside(page, sel)
    assert page.evaluate("[wide, S]") == [False, 30]
    assert page.errors == []
    ctx.close()
