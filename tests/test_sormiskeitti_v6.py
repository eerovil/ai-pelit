"""Sormiskeitti v6: played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/sormiskeitti/v6/"
SIDEWAYS = [(740, 360), (844, 390), (640, 360)]


def open_game(site, browser, width, height):
    shutil.copytree(ROOT / "games" / "sormiskeitti", site.games / "sormiskeitti")
    site.build()
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-back")
    return ctx, page


def inside(page, box):
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    assert box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= vw and box["y"] + box["height"] <= vh, box


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_the_chips_fit_clear_of_the_hud_and_work(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    back = page.locator("#ai-pelit-back")
    scores = page.get_by_text("Tulokset")
    for chip in (back, scores):
        box = chip.bounding_box()
        inside(page, box)
        # The HUD (level, ceiling, record on the left; speed bar on the right) ends at y = 140.
        assert box["y"] > 140, box
    # The Tulokset chip opens its list, and the game is still on its start screen.
    scores.click()
    page.get_by_text("Sulje").click()
    assert page.evaluate("st") == "ready"
    # The start text sits inside the room, under the level-1 ceiling, and above the board.
    ty, ceiling, ground = page.evaluate("""() => {
        const scale = Math.min(W / 420, H / 520);
        return [H * 0.36, H * 0.82 - (LIP_Y + ceilH()) * scale, H * 0.82];
    }""")
    assert ceiling < ty - 26 and ty + 106 < ground - 30
    assert page.errors == []
    ctx.close()


def test_sideways_a_round_runs_and_survives_turning_the_phone(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    page.mouse.click(370, 200)
    assert page.evaluate("st") == "roll"
    for _ in range(12):
        page.evaluate("tap()")
        page.wait_for_timeout(30)
    page.wait_for_function("s > 100")
    before = page.evaluate("({ st, s, level })")
    assert before["st"] == "roll"
    # Turn the phone upright mid-round: the round goes on where it was.
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_function("W === 360 && H === 740")
    after = page.evaluate("({ st, s, level })")
    assert after["st"] in ("roll", "air") and after["s"] >= before["s"] and after["level"] == before["level"]
    # And back sideways; the round still finishes normally.
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_function("W === 740 && H === 360")
    assert page.evaluate("st") != "ready"
    page.wait_for_function("st === 'end'", timeout=15000)
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("width,height", [(360, 740), (360, 640)])
def test_upright_v6_draws_exactly_what_v5_draws(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    frames = []
    for version in ("v5", "v6"):
        page.goto(site.url + f"games/sormiskeitti/{version}/")
        # The start screen, then a moment on the ramp, drawn with no camera shake.
        frames.append(page.evaluate("""() => {
            const shots = [];
            draw(); shots.push(c.toDataURL());
            st = 'roll'; s = L + 120; v = 8; draw(); shots.push(c.toDataURL());
            return shots;
        }"""))
    assert frames[0] == frames[1]
    assert page.errors == []
    ctx.close()
