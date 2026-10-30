"""Puhelinkoppi v5: the game played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/puhelinkoppi/v5/"
SIDEWAYS = [(740, 360), (844, 390), (640, 360)]
FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""


def open_game(site, browser, width, height):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    # A nickname, so the first catch does not open the scores panel's name question.
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-tulokset-nappi")
    page.evaluate("noise = 0")
    return ctx, page


def inside(page, selector):
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    b = page.locator(selector).bounding_box()
    assert b is not None
    assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= vw and b["y"] + b["height"] <= vh, (selector, b)
    # Nothing lies on top of it: a tap at its middle reaches it.
    assert page.evaluate(
        "([s, x, y]) => document.querySelector(s).contains(document.elementFromPoint(x, y))",
        [selector, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2])
    return b


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_the_chips_fit_and_the_words_keep_clear_of_the_hand(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    assert page.evaluate("LAND")
    inside(page, "#ai-pelit-back")
    inside(page, "#ai-pelit-tulokset-nappi")
    # The words go down the left side, and the hand and the phone keep the middle.
    left, col = page.evaluate("sideCol()")
    hand_left = page.evaluate("project(handPt(-0.09, 0, 0))[0]")
    assert left + col < hand_left - 20
    # The phone is big enough to aim a grab at its end or its side.
    assert page.evaluate("PW / (project(pos)[2] / focal())") >= 28
    # The Tulokset chip opens its panel and the panel closes again.
    page.click("#ai-pelit-tulokset-nappi")
    assert page.locator("#ai-pelit-tulokset").is_visible()
    page.get_by_text("Sulje").click()
    assert not page.locator("#ai-pelit-tulokset").is_visible()
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("width,height", SIDEWAYS)
def test_sideways_a_flick_throws_and_the_result_band_leaves_the_hand_in_view(site, browser, width, height):
    ctx, page = open_game(site, browser, width, height)
    px, py = page.evaluate("phoneOnScreen().slice(0, 2)")
    page.mouse.move(px, py)
    page.mouse.down()
    for i in range(1, 6):
        page.mouse.move(px, py - 30 * i)
    page.mouse.up()
    assert page.evaluate("state") == "air"
    assert page.evaluate(FLY, 4) == "result"
    assert page.evaluate("result.kind") == "win"
    # Caught at the hand's resting height, the band ends above the fingertips (the hand stays in
    # view), and below the goal text. (The flick above raised the hand.)
    page.evaluate("level = 1; newRound(); launch({ v0: 3 })")
    assert page.evaluate(FLY, 4) == "result"
    page.evaluate("for (let i = 0; i < 60; i++) step(1 / 60)")  # the camera settles
    band = page.evaluate("SAFE_T + 60")
    assert band + 108 < page.evaluate("project(handPt(0, 0.12, 0.012))[1]") - 10
    assert band > page.evaluate("SAFE_T + 12 + 38")  # under the Paras line
    page.evaluate("resultT = -1e9")  # past the half second that guards against a stray tap
    page.mouse.click(width / 2, height / 2)
    assert page.evaluate("[state, level]") == ["ready", 2]
    assert page.errors == []
    ctx.close()


def test_turning_the_phone_mid_throw_keeps_the_round(site, browser):
    ctx, page = open_game(site, browser, 740, 360)
    page.evaluate("launch({ v0: 5, wx: 6 }); for (let i = 0; i < 20; i++) step(1 / 60)")
    before = page.evaluate("[state, level, halfFlips, pos[1], vel[1]]")
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!LAND")
    now = page.evaluate("[state, level, halfFlips]")
    assert now[0] == "air" and now[1] == before[1] and now[2] >= before[2]
    # It flies on and lands in the hand, in portrait now, and back to sideways.
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND")
    assert page.evaluate("state") in ("air", "drop", "settle", "result")
    assert page.evaluate(FLY, 4) == "result"
    assert page.evaluate("result.level") == 1
    assert page.errors == []
    ctx.close()


def test_upright_the_layout_is_as_before(site, context):
    shutil.copytree(ROOT / "games" / "puhelinkoppi", site.games / "puhelinkoppi")
    site.build()
    page = context.new_page()
    page.goto(site.url + URL)
    assert page.evaluate("[LAND, focal(), phoneOnScreen()[1]]") == page.evaluate(
        "[false, Math.min(W * 3, H * 1.45), H * 0.6 - dot(sub(pos, camPos()), CU) * focal() / dot(sub(pos, camPos()), CF)]")
