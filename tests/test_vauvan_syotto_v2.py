"""Vauvan syöttäminen v2: the same game played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/vauvan-syotto/v2/"
SIDEWAYS = [(740, 360), (844, 390), (640, 360)]
RUN = "s => { for (let i = 0; i < s * 50; i++) step(0.02); }"


def open_game(site, browser, width, height):
    # Only this game is built, so another game's half-made version cannot break the test.
    shutil.copytree(ROOT / "games" / "vauvan-syotto", site.games / "vauvan-syotto")
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
    """Starts a round. back.js goes fullscreen on the first tap, and Chromium will not resize a
    fullscreen window, so the test leaves fullscreen at once."""
    page.click("#go")
    page.wait_for_timeout(300)
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_function("!document.fullscreenElement && innerWidth === W")
    assert page.evaluate("state") == "play"


MENU = ["#menu h1", "#lvl", "#go", ".help"]


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_the_menu_and_the_end_screen_fit_without_scrolling(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    for sel in MENU:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight && menu.scrollWidth <= menu.clientWidth")
    page.click("#go", trial=True)  # nothing covers it
    page.evaluate("lastResult = 'win'; lastStars = 2; stars = {1: 3, 2: 2}; showMenu()")
    for sel in MENU + ["#result", "#stars", "#total"]:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight")
    page.click("#go", trial=True)
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_a_round_plays_with_the_controls_on_screen(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    start(page)
    assert page.evaluate("wide") is True
    # Power buttons down the left, the bowl in the lower right, all on screen and clear of the baby.
    ok = page.evaluate("""() => {
      const g = G, inScreen = (px, py, r) => px - r >= 0 && py - r >= 0 && px + r <= W && py + r <= H;
      const trayL = g.hx - g.R * 1.55, trayR = g.hx + g.R * 1.55;
      return g.btns.every(b => inScreen(b.x, b.y, b.r) && b.x + b.r < trayL)
        && inScreen(g.bowl.x, g.bowl.y, g.bowl.r) && g.bowl.x - g.bowl.r > trayR
        && g.bar.x + g.bar.w < trayL && g.floorY < H;
    }""")
    assert ok
    # The back chip stays above the bars.
    chip = page.locator("a", has_text="Pelit").first.bounding_box()
    assert chip["y"] + chip["height"] <= page.evaluate("safeT + 44")
    # A real drag from the bowl to an open mouth feeds the baby.
    page.evaluate("""() => {
      mood = 100; Math.random = () => 0.9;
      for (let i = 0; i < 2000 && !(baby.act === 'open' && baby.mouth > 0.8); i++) step(0.02);
      baby.dur = 99;
    }""")
    bx, by, mx, my = page.evaluate("[G.bowl.x, G.bowl.y, mouthPos().x, mouthPos().y + TIP]")
    page.mouse.move(bx, by)
    page.mouse.down()
    page.mouse.move(mx, my, steps=5)
    page.mouse.up()
    assert page.evaluate("[tummy, misses, state]") == [1, 0, "play"]
    page.evaluate(RUN, 1)
    assert page.evaluate("state") == "play"
    assert page.errors == []
    ctx.close()


def test_turning_the_phone_mid_round_keeps_the_round(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    start(page)
    page.evaluate("tummy = 3; misses = 1; mood = 70; power.video = 2; spoon.where = 'floor'; spoon.x = 700; spoon.y = G.floorY")
    before = page.evaluate("[level, goal, tummy, misses, power.video, state]")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("W === 360 && H === 740")
    assert page.evaluate("wide") is False
    assert page.evaluate("[level, goal, tummy, misses, power.video, state]") == before
    # The dropped spoon is moved onto the narrower floor, where it can still be tapped and washed.
    assert page.evaluate("spoon.where === 'floor' && spoon.x <= W - 30 && spoon.y === G.floorY")
    page.evaluate("down(spoon.x, spoon.y); up(spoon.x, spoon.y)")
    assert page.evaluate("spoon.where") == "wash"
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("W === 740 && H === 360")
    assert page.evaluate("[wide, state, tummy]") == [True, "play", 3]
    assert page.errors == []
    ctx.close()
