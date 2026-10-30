"""Kaahari v3: the race played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/kaahari/v3/"
SIDEWAYS = [(740, 360), (844, 390), (640, 360)]


def open_game(site, browser, width, height):
    shutil.copytree(ROOT / "games" / "kaahari", site.games / "kaahari")
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
    boxes = [page.locator(selector).nth(i).bounding_box() for i in range(page.locator(selector).count())]
    assert boxes
    for b in boxes:
        assert b is not None
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= vw and b["y"] + b["height"] <= vh, (selector, b)


def finish(page):
    page.evaluate("""() => {
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150 });
    }""")


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_the_menu_and_the_end_screen_fit_without_scrolling(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    for sel in ["#menu h1", ".track", "#go", "#multi", "#stats", ".help.short"]:
        inside(page, sel)
    assert not page.locator(".help.long").is_visible()
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight")
    # The track buttons are tappable: the last one is picked and saved.
    page.locator(".track").nth(2).click()
    assert page.evaluate("localStorage.getItem('ai-pelit:kaahari:rata')") == "2"
    page.click("#go")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    finish(page)
    page.wait_for_function("race.phase === 'over'", timeout=6000)
    assert page.inner_text("#result") == "🏆 Voitit kisan!"
    for sel in ["#result", "#table div", ".track", "#go", "#multi"]:
        inside(page, sel)
    assert page.evaluate("menu.scrollHeight <= menu.clientHeight")
    assert page.errors == []
    ctx.close()


def test_sideways_the_race_runs_with_a_wider_view_and_thumb_buttons(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    page.click("#go")
    page.wait_for_function("race.phase === 'run' && me.prog > 60", timeout=8000)
    # The picture is as tall as upright is wide, and wider: same size karts, more track.
    assert page.evaluate("[FH, FW > 200, SCALE]") == [200, True, 1.8]
    # Arrows in the lower left, the slide and item buttons in the lower right, all on the screen.
    b = page.evaluate("layout(), BTN")
    assert b["left"]["x"] >= 0 and b["right"]["x"] + b["right"]["w"] < 740 / 2
    assert b["left"]["y"] + b["left"]["h"] <= 360 and b["left"]["y"] > 360 / 2
    assert b["drift"]["cx"] - b["drift"]["r"] > 740 / 2 and b["drift"]["cx"] + b["drift"]["r"] <= 740
    assert b["drift"]["cy"] + b["drift"]["r"] <= 360 and b["item"]["cy"] - b["item"]["r"] > 360 / 2
    # A tap on the right arrow steers.
    page.touchscreen.tap(b["right"]["x"] + 30, b["right"]["y"] + 40)
    assert page.errors == []
    ctx.close()


def test_turning_the_phone_mid_race_keeps_the_race_going(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    page.click("#go")
    page.wait_for_function("race.phase === 'run' && race.t > 1", timeout=8000)
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    page.wait_for_timeout(200)
    t, prog = page.evaluate("[race.t, me.prog]")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("FW === 200 && FH > 200", timeout=3000)
    page.wait_for_timeout(300)
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("FH === 200", timeout=3000)
    page.wait_for_timeout(300)
    assert page.evaluate("race.phase") == "run"
    assert page.evaluate("race.t") > t and page.evaluate("me.prog") > prog
    assert page.errors == []
    ctx.close()


def test_upright_the_menu_is_as_in_v2(site, browser):
    ctx, page = open_game(site, browser, 360, 740)
    assert page.locator(".help.long").is_visible() and not page.locator(".help.short").is_visible()
    assert page.evaluate("[FW, SCALE]") == [200, 1.8]
    for sel in [".track", "#go", "#multi"]:
        inside(page, sel)
    ctx.close()
