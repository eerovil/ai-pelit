"""Hiihto v4 (#61): the speed at the top, and a rhythm meter that shows when to tap."""

import pytest

from conftest import ROOT
from test_hiihto import BOT, EMPTY

URL = "games/hiihto/v4/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    page.errors = errors
    return page


@pytest.mark.parametrize("st,full", [("perinteinen", 0.37), ("luistelu", 0.32)])
def test_the_meter_turns_green_at_the_fastest_rhythm(site, context, st, full):
    page = open_game(site, context)
    page.evaluate(f"style = '{st}'; newRace()")
    page.evaluate(EMPTY.replace("bestWax(course.weather.T)", "bestFor(style, course.weather.T)"), 1)
    # (Each check in one evaluate: the page's own frames keep the race going in between.)
    beats = page.evaluate("full => [0, full / 2, full].map(d => { P.lastKick = 5; P.t = 5 + d; return beat(P); })", full)
    assert beats[0] == 0 and 0.45 < beats[1] < 0.55 and beats[2] == 1
    # Taps in the meter's rhythm drive the skier faster than taps far quicker or far slower.
    run = """gap => { P.z = 20; P.v = 0; P.t = 0; P.lastKick = -9; P.side = 1;
      let next = 0; for (let i = 0; i < 60 * 8; i++) {
        if (P.t >= next) { if (P.style === 'luistelu') push(P, -P.side); else kick(P); next = P.t + gap; }
        physics(P, 1 / 60); }
      return P.z; }"""
    page.evaluate("course.grade.fill(0); course.y.fill(0); mode = 'wax'")
    at_beat = page.evaluate(run, full + 1 / 60)
    assert at_beat > page.evaluate(run, full * 0.5)
    assert at_beat > page.evaluate(run, full * 1.8)
    # A tap long before the meter is full says so.
    early = "P.t = 50; P.lastKick = 49.95; P.sameT = 0; P.fallT = 0; P.slipT = 0; P.style === 'luistelu' ? push(P, -P.side) : kick(P); P.slipT = 0; mode = 'race'; hint()[0]"
    assert page.evaluate(early) == "Liian tiheään: odota vihreää"
    # The warning lasts only until the next full-strength moment: then the meter is green again.
    states = page.evaluate("""full => [0.1, full - 0.01, full + 0.005].map(d => {
      P.t = 50 + d; return [meter(P), (hint() || [''])[0]]; })""", full)
    assert states[0] == ["early", "Liian tiheään: odota vihreää"]
    assert states[1][0] == "early"
    assert states[2][0] == "ready" and states[2][1] != "Liian tiheään: odota vihreää"
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844)])
def test_a_race_draws_the_speed_and_the_meter(site, browser, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx)
    r = page.evaluate(BOT.replace("mode === 'race'; i++)", "mode === 'race' && P.z < 150; i++)", 1))
    assert r["mode"] == "race"
    page.evaluate("draw()")
    bar = page.evaluate("rhythmBar()")
    assert 0 <= bar["x"] and bar["x"] + bar["w"] + 40 <= w
    # Under the hint line, above the trail, clear of the corner chips.
    assert page.evaluate("SAFE_T + 18 + 34 + 34 + 20") < bar["y"] < h / 3
    # Classic still plays to the end and saves as before.
    r = page.evaluate(BOT)
    assert r["mode"] == "done" and r["stars"] >= 1, r
    assert page.errors == []
    ctx.close()
