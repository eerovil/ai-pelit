"""Orava v2: the same squirrel game, also played sideways (#95)."""

import shutil

import pytest
from conftest import ROOT

URL = "games/orava/v2/"
LAND = {"width": 740, "height": 360}


def open_game(site, browser, viewport, level=None):
    # Only this game, so another game's half-done version cannot break the build.
    shutil.copytree(ROOT / "games" / "orava", site.games / "orava")
    site.build()
    ctx = browser.new_context(viewport=viewport, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    if level:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('ai-pelit:orava:taso', '{level}')")
    page.goto(site.url + URL)
    return ctx, page


def inside(box, w, h):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and \
        a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


@pytest.mark.parametrize("size", [(740, 360), (640, 360), (844, 390)])
def test_the_sideways_menu_fits_without_scrolling(site, browser, size):
    w, h = size
    ctx, page = open_game(site, browser, {"width": w, "height": h}, level=3)
    try:
        assert page.evaluate("document.scrollingElement.scrollHeight") <= h
        boxes = page.evaluate("""() => [...document.querySelectorAll('#menu > *')].filter(e => e.offsetParent)
            .map(e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; })""")
        assert len(boxes) == 6   # title, level, dangers, button, stats, help
        for b in boxes:
            assert inside(b, w, h)
        chips = [page.locator(s).bounding_box() for s in ("#ai-pelit-back", "#ai-pelit-tulokset-nappi")]
        for b in boxes:
            assert not any(overlap(b, c) for c in chips)
        go = page.locator("#go")
        assert inside(go.bounding_box(), w, h)
        go.tap()
        assert page.evaluate("phase") == "play"
    finally:
        ctx.close()


def test_a_round_runs_sideways_with_the_controls_in_the_lower_corners(site, browser):
    ctx, page = open_game(site, browser, LAND)
    try:
        page.locator("#go").tap()
        stick, jump = page.locator("#stick").bounding_box(), page.locator("#jump").bounding_box()
        assert inside(stick, 740, 360) and inside(jump, 740, 360)
        assert stick["x"] + stick["width"] < 200 and jump["x"] > 540
        assert stick["y"] > 180 and jump["y"] > 180
        # The floor is near the bottom, and at the start the squirrel stands clear of the stick.
        page.wait_for_timeout(600)
        assert page.evaluate("sy(0)") > 300
        assert page.evaluate("sx(S.x)") > stick["x"] + stick["width"]
        # The HUD bar sits between the corner chips, not under them.
        back, tul = page.locator("#ai-pelit-back").bounding_box(), page.locator("#ai-pelit-tulokset-nappi").bounding_box()
        hud = page.evaluate("layout()")
        assert hud["hudL"] >= back["x"] + back["width"] and hud["hudR"] <= tul["x"]
        # The stick drives the squirrel, and the round's clock runs.
        t0 = page.evaluate("timeLeft")
        cx, cy = stick["x"] + stick["width"] / 2, stick["y"] + stick["height"] / 2
        page.mouse.move(cx, cy)
        page.mouse.down()
        page.mouse.move(cx + 50, cy, steps=3)
        x0 = page.evaluate("S.x")
        page.wait_for_timeout(500)
        assert page.evaluate("input.right") is True and page.evaluate("S.x") > x0 + 30
        page.mouse.up()
        assert page.evaluate("timeLeft") < t0
        assert page.evaluate("phase") == "play"
    finally:
        ctx.close()


def test_turning_the_phone_mid_round_keeps_the_round(site, browser):
    ctx, page = open_game(site, browser, {"width": 360, "height": 740})
    try:
        page.locator("#go").tap()
        page.evaluate("""() => {
            const k = cones[0]; Object.assign(S, { mode: 'air', x: k.x, y: k.y - 9, vx: 0, vy: 0 }); eat();
            hearts = 2; toTrunk(1, 200);
        }""")
        before = page.evaluate("[phase, eaten, points, hearts, cones.length, S.mode, S.tree]")
        assert before == ["play", 1, 10, 2, 10, "trunk", 1]
        page.evaluate("document.fullscreenElement && document.exitFullscreen()")
        page.wait_for_timeout(200)
        page.set_viewport_size(LAND)
        page.wait_for_timeout(500)
        assert page.evaluate("[W, H, LAND]") == [740, 360, True]
        assert page.evaluate("[phase, eaten, points, hearts, cones.length, S.mode, S.tree]") == before
        # The camera has caught up: the squirrel is on the screen, above the floor line.
        sx, sy = page.evaluate("[sx(S.x), sy(S.y)]")
        assert 0 < sx < 740 and 40 < sy < 340
        page.set_viewport_size({"width": 360, "height": 740})
        page.wait_for_timeout(500)
        assert page.evaluate("[W, LAND, floorY()]") == [360, False, 740 - 150]
        assert page.evaluate("[phase, eaten, points, hearts, cones.length, S.mode, S.tree]") == before
    finally:
        ctx.close()


def test_upright_the_layout_is_as_in_v1(site, browser):
    ctx, page = open_game(site, browser, {"width": 360, "height": 740})
    try:
        page.locator("#go").tap()
        assert page.evaluate("[LAND, floorY(), viewH()]") == [False, 590, 590 - 96]
        assert page.evaluate("layout()") == {"padL": 0, "padR": 0, "padTop": 740, "hudL": 8, "hudR": 352}
        stick, jump = page.locator("#stick").bounding_box(), page.locator("#jump").bounding_box()
        assert stick["width"] == 154 and jump["width"] == 108   # 150 px and a 2 px border, as in v1
    finally:
        ctx.close()
