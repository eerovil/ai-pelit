"""Pallorata v2 (#95): v1's 3D ball run, also played sideways."""

import shutil

import pytest

from conftest import ROOT

URL = "games/pallorata/v2/"
LANDSCAPE = {"width": 740, "height": 360}


def open_game(site, browser, viewport):
    # Only this game is built: other games' half-made versions cannot break the build.
    shutil.copytree(ROOT / "games" / "pallorata", site.games / "pallorata")
    site.build()
    ctx = browser.new_context(viewport=viewport, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    # Headless Chromium draws WebGL in software (SwiftShader); without it the page says so instead.
    if page.evaluate("window.noWebgl === true"):
        ctx.close()
        pytest.skip("this Chromium has no WebGL")
    return ctx, page, errors


@pytest.fixture
def landscape(site, browser):
    ctx, page, errors = open_game(site, browser, LANDSCAPE)
    yield page, errors
    ctx.close()


def inside(page, selector):
    box = page.locator(selector).bounding_box()
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    assert box, selector
    assert box["x"] >= 0 and box["y"] >= 0, selector
    assert box["x"] + box["width"] <= vw and box["y"] + box["height"] <= vh, selector
    return box


def overlaps(a, b):
    return not (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])


def keep_on_the_track(page):
    page.evaluate("window.keep = setInterval(() => { ball.aimX = row(Math.floor(-ball.z / 2)).cx; }, 16)")


def leave_fullscreen(page):
    # back.js goes full screen on the first tap, and Chromium will not resize a full-screen window.
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")


@pytest.mark.parametrize("size", [(740, 360), (640, 360), (844, 390)])
def test_the_sideways_menu_fits_without_scrolling(site, browser, size):
    ctx, page, errors = open_game(site, browser, {"width": size[0], "height": size[1]})
    try:
        page.evaluate("localStorage.setItem('ai-pelit:pallorata:ennatys', '1234')")
        page.reload()
        page.wait_for_function("window.drawn === true", timeout=15000)
        assert page.evaluate("document.documentElement.scrollHeight") == size[1]
        for sel in ["#menu h1", "#menu p:not(#paras)", "#paras", "#aloita", "#ai-pelit-back"]:
            inside(page, sel)
        # Two columns: the button sits beside the help text, not below it.
        assert overlaps({**inside(page, "#menu p:not(#paras)"), "x": 0, "width": 1}, {**inside(page, "#aloita"), "x": 0, "width": 1})
        assert not overlaps(inside(page, "#aloita"), inside(page, "#ai-pelit-back"))
        page.click("#aloita")
        page.wait_for_function("round.phase === 'run'", timeout=2000)
        assert errors == []
    finally:
        ctx.close()


def test_the_portrait_menu_stays_as_it_was(site, browser):
    ctx, page, _ = open_game(site, browser, {"width": 360, "height": 640})
    try:
        assert page.evaluate("getComputedStyle(document.getElementById('menu')).display") == "flex"
        assert page.locator("#aloita").bounding_box()["y"] > page.locator("#paras").bounding_box()["y"]
        inside(page, "#aloita")
    finally:
        ctx.close()


def test_a_round_runs_sideways_with_the_hud_clear_of_the_back_chip(landscape):
    page, errors = landscape
    page.click("#aloita")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    keep_on_the_track(page)
    page.wait_for_function("-ball.z > 10", timeout=5000)
    assert page.evaluate("round.phase") == "run"
    assert page.evaluate("[camera.aspect, renderer.domElement.width / renderer.domElement.height]") == \
        pytest.approx([740 / 360, 740 / 360], rel=0.01)
    hud = inside(page, "#hud")
    assert not overlaps(hud, inside(page, "#ai-pelit-back"))
    assert errors == []


def test_turning_the_phone_mid_round_keeps_the_round(landscape):
    page, errors = landscape
    page.click("#aloita")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    keep_on_the_track(page)
    page.evaluate("round.stars = 3")
    page.wait_for_function("-ball.z > 8", timeout=5000)
    leave_fullscreen(page)
    for w, h in [(360, 740), (740, 360)]:
        before = page.evaluate("[-ball.z, round.t]")
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_function(f"innerWidth === {w} && Math.abs(camera.aspect - {w / h}) < 0.01", timeout=3000)
        page.wait_for_function(f"-ball.z > {before[0] + 3}", timeout=5000)
        assert page.evaluate("round.phase") == "run"
        assert page.evaluate("round.stars") == 3
        assert page.evaluate("round.t") > before[1]
        assert page.evaluate("renderer.domElement.width / renderer.domElement.height") == pytest.approx(w / h, rel=0.01)
        inside(page, "#hud")
    assert errors == []


def test_the_end_screen_fits_sideways(site, browser):
    ctx, page, _ = open_game(site, browser, {"width": 640, "height": 360})
    try:
        page.click("#aloita")
        page.wait_for_function("round.phase === 'run' && -ball.z > 4", timeout=5000)
        page.evaluate("ball.aimX = 50")
        page.wait_for_function("round.phase === 'over'", timeout=5000)
        for sel in ["#loppu h1", "#tulos", "#ennatys", "#uudestaan"]:
            inside(page, sel)
        page.click("#uudestaan")
        page.wait_for_function("round.phase === 'run' && ball.z > -2", timeout=2000)
    finally:
        ctx.close()
