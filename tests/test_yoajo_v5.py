"""Yöajo v5 (#206): a car's speedometer at the top of the screen (a round dial with a needle)."""

import math

import pytest

from conftest import ROOT, turn
from test_yoajo_v4 import BOT

URL = "games/yoajo/v5/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"]) for r in legs]
    assert page.errors == []


def test_the_needle_shows_the_speed(site, context):
    page = open_game(site, context)
    # 0 at the lower left, 100 straight up, 200 at the lower right, as on a car's dial.
    a0, a100, a200, over = page.evaluate("[needleAngle(0), needleAngle(100), needleAngle(200), needleAngle(260)]")
    assert a0 == pytest.approx(math.pi * 0.75) and a100 == pytest.approx(math.pi * 1.5)
    assert a200 == pytest.approx(math.pi * 2.25) and over == a200
    # The dial is drawn with the car's own speed and the limit of the road where it is.
    got = page.evaluate("""() => { HOLD = true; newLeg(1); P.v = 25; let got;
      const real = speedometer; speedometer = (...a) => { got = a.slice(1); real(...a); };
      draw(); speedometer = real; return [got, limitAt(P.s)]; }""")
    (v, kmh, lim, over), road_lim = got
    assert v == pytest.approx(90) and kmh == 90 and lim == road_lim and over is (90 > road_lim + 5)
    assert page.errors == []


@pytest.mark.parametrize("size", [{"width": 360, "height": 640}, {"width": 390, "height": 844}, {"width": 740, "height": 360}])
def test_the_speedometer_sits_at_the_top_and_everything_beside_it_fits(site, context, size):
    page = open_game(site, context)
    turn(page, size)
    page.wait_for_function(f"W === {size['width']} && H === {size['height']}")
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); draw();
      const sp = speedoBox(), pause = btns.find(b => b.id === 'pause'), home = stickHome();
      x.font = '600 11px system-ui,sans-serif'; const vireys = x.measureText('Vireys').width;
      x.font = '600 14px system-ui,sans-serif'; const time = x.measureText('10:00 / 10:00').width;
      return { sp, pause, top: SAFE_T, stickTop: home.y - STICK, thumbTop: thumbTop(),
        leftEdge: sp.cx - sp.r - 14 - Math.max(58 + 6 + vireys, time), rightEdge: sp.cx + sp.r + 14 + 38,
        lights: btns.find(b => b.id === 'lights') }; }""")
    sp = r["sp"]
    # In the top part of the screen, under the trip line, clear of the pause button and the back chip.
    assert sp["cy"] - sp["r"] >= 40 and sp["cy"] + sp["r"] < size["height"] * 0.45
    p = r["pause"]
    assert sp["cx"] + sp["r"] < p["x"] or sp["cy"] - sp["r"] > p["y"] + p["h"]
    assert sp["cy"] - sp["r"] > 40
    # The time, distance and alertness on the left and the points and limit on the right fit.
    assert r["leftEdge"] >= 0 and r["rightEdge"] <= size["width"]
    # The stick and the lights stay below it, and no thumb starts on it.
    assert r["thumbTop"] > sp["cy"] + sp["r"] and r["stickTop"] > r["thumbTop"]
    assert r["lights"]["y"] > sp["cy"] + sp["r"]
    assert page.errors == []


def test_a_thumb_on_the_speedometer_does_not_drive(site, context):
    page = open_game(site, context)
    page.evaluate("HOLD = true; newLeg(1); draw()")
    sp = page.evaluate("speedoBox()")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": sp["cx"], "y": sp["cy"], "id": 1}]})
    page.wait_for_timeout(100)
    assert page.evaluate("thumbs.size") == 0
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 150, "y": 600, "id": 2}]})
    page.wait_for_function("thumbs.size === 1")
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    assert page.errors == []


def test_v4_saves_carry_over(site, context):
    page = open_game(site, context)
    page.evaluate("""() => { localStorage.setItem('ai-pelit:yoajo:taso', '4');
      localStorage.setItem('ai-pelit:yoajo:ohjaus', 'kaksi'); }""")
    page.reload()
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    assert page.evaluate("[maxLeg, controls]") == [4, "kaksi"]
    assert page.errors == []
