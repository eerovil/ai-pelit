"""Curling v2: upright, a full pull back fits on the screen below the stone (#293).

In v1 the stone sat 74 px above the bottom edge, so upright only guards could be thrown.
"""

import pytest

from conftest import ROOT, turn

URL = "games/curling/v3/"
RUN = "() => { window.run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += DT) update(DT); }; }"


def aiming(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.evaluate("hammer = 1; startEnd()")
    return ctx, page


# Pulls straight down from the stone by `pull` px, never past the screen's edge, and lets go.
def pull_and_throw(page, pull):
    px, py, h = page.evaluate("[pad.x, pad.y, H]")
    end = py + pull
    assert end <= h - 1, "the pull would leave the screen"
    page.mouse.move(px, py)
    page.mouse.down()
    page.mouse.move(px, end, steps=10)
    name = page.evaluate("weightName(aim.w)")
    page.mouse.up()
    assert page.evaluate("phase") == "slide"
    page.evaluate("run(() => phase === 'slide')")
    return name


@pytest.mark.parametrize("size", [(360, 740), (390, 844), (360, 640)])
def test_upright_a_full_pull_fits_below_the_stone(site, browser, size):
    ctx, page = aiming(site, browser, size)
    room = page.evaluate("H - safeB - pad.y - pad.pull")
    # The finger reaches full weight with room to spare for the stone under it.
    assert room >= 22
    # The turn buttons and the house stay on the screen.
    assert page.evaluate("spinBtns.every(b => b.y >= 0 && b.y + b.h <= H)")
    page.evaluate("camY = farY() - viewLen() / 2")
    assert page.evaluate("P(0, TEE + HOUSE)[1] >= safeT && P(0, TEE - HOUSE)[1] < Math.min(...spinBtns.map(b => b.y))")
    ctx.close()


@pytest.mark.parametrize("size", [(360, 740), (390, 844)])
def test_upright_a_pull_on_the_screen_draws_into_the_house(site, browser, size):
    ctx, page = aiming(site, browser, size)
    # Straight down, the weight that stops on the tee: it bends about a metre, still in the house.
    pull = page.evaluate("weightFor(TEE) * pad.pull")
    assert pull_and_throw(page, pull) == "Pesään"
    stone = page.evaluate("(() => { const s = stones[0]; return { out: s.out, d: Math.hypot(s.x, s.y - TEE), lim: HOUSE + RS }; })()")
    assert stone["out"] is False and stone["d"] < stone["lim"]
    assert page.errors == []
    ctx.close()


@pytest.mark.parametrize("size", [(360, 740), (390, 844)])
def test_upright_a_full_pull_on_the_screen_takes_a_stone_out(site, browser, size):
    ctx, page = aiming(site, browser, size)
    page.evaluate("stones.push(stone(1, 0, TEE))")
    assert pull_and_throw(page, page.evaluate("pad.pull + 5")) == "Poistolyönti"
    assert page.evaluate("stones.find(s => s.t === 1).out") is True
    assert page.errors == []
    ctx.close()


def test_turned_sideways_and_back_the_full_pull_still_fits(site, browser):
    ctx, page = aiming(site, browser, (360, 740))
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide === true")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("wide === false")
    assert page.evaluate("[phase, H - safeB - pad.y - pad.pull >= 22]") == ["aim", True]
    page.evaluate("stones.push(stone(1, 0, TEE))")
    assert pull_and_throw(page, page.evaluate("pad.pull + 5")) == "Poistolyönti"
    assert page.evaluate("stones.find(s => s.t === 1).out") is True
    ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/curling/v3")
