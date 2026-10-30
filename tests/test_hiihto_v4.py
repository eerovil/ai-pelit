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
    # Faster taps, down to mashing the screen, and slower ones all lose to the meter's rhythm.
    for gap in [0.05, 0.08, 0.1, full * 0.5, full * 0.8, full * 1.3, full * 1.8]:
        assert at_beat > page.evaluate(run, gap), gap
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


def test_the_road_is_on_odd_levels_from_three(site, context):
    page = open_game(site, context)
    roads = page.evaluate("[1, 2, 3, 4, 5, 6].map(n => { level = n; newRace(); return !!course.road; })")
    assert roads == [False, False, True, False, True, False]
    page.evaluate("level = 3; newRace()")
    # Flat on and around the road, so nobody slides on to it down a hill.
    assert page.evaluate("[-20, 0, 4, 8, 20].every(d => Math.abs(gradeAt(course.road.z0 + d)) < 0.005)")


CROSS = """(st) => { level = 3; style = st; newRace(); chooseWax(bestFor(style, course.weather.T)); mode = 'race';
  npcs = []; nextVasta = nextSkate = 1e9; P.clog = 3; P.z = course.road.z0 - 6; P.v = 3; }"""
RUN = "s => { for (let i = 0; i < s * 60; i++) step(1 / 60); }"
TAP = "() => { down(5, W / 2, H / 2); up(5); }"


@pytest.mark.parametrize("st", ["perinteinen", "luistelu"])
def test_crossing_the_road(site, context, st):
    page = open_game(site, context)
    page.evaluate(CROSS, st)
    page.evaluate(RUN, 3)
    # Stopped at the edge, skis still on, nobody knocked down.
    assert page.evaluate("[P.road, P.v, falls, hint()[0]]") == ["edge", 0, 0, "Tie! Napauta: sukset pois"]
    assert page.evaluate("P.z < course.road.z0")
    page.evaluate(TAP)
    page.evaluate(RUN, 1)
    assert page.evaluate("P.road") == "walk"
    # A step in the rhythm moves on; one straight after it slips on the ice.
    page.evaluate(TAP)
    z = page.evaluate("P.z")
    page.evaluate(RUN, 0.1)
    page.evaluate(TAP)
    assert page.evaluate("[falls, P.fallT > 0, P.z]") == [1, True, z]
    page.evaluate(RUN, 1.2)
    # Steps on green get across.
    for _ in range(12):
        if page.evaluate("P.road") != "walk":
            break
        page.evaluate(TAP)
        page.evaluate(RUN, 0.5)
    assert page.evaluate("[P.road, P.z > course.road.z1]") == ["skison", True]
    # Snow in the bindings: three knocks, then the skis go on and the race goes on.
    page.evaluate(TAP)
    assert page.evaluate("[P.road, hint()[0]]") == ["clog", "Lunta siteissä! Kopistele: 3 ×"]
    for _ in range(3):
        page.evaluate(TAP)
    page.evaluate(RUN, 1)
    assert page.evaluate("P.road") == "done"
    z = page.evaluate("P.z")
    for _ in range(6):
        page.evaluate("st => st === 'luistelu' ? push(P, -P.side) : kick(P)", st)
        page.evaluate(RUN, 0.4)
    assert page.evaluate("P.z") > z + 2
    assert page.errors == []


def test_coming_in_fast_is_a_fall(site, context):
    page = open_game(site, context)
    page.evaluate(CROSS, "perinteinen")
    page.evaluate("P.v = 7")
    page.evaluate(RUN, 1.5)
    assert page.evaluate("[falls, P.road, P.z < course.road.z0]") == [1, "edge", True]


def test_a_whole_race_with_a_road(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:hiihto:taso', '3'); maxLevel = 3; level = 3; newRace()")
    assert page.evaluate("!!course.road")
    # The time limit counts the crossing, but only as long as it takes: a few seconds more than
    # the same course with no road.
    with_road = page.evaluate("course.ideal")
    no_road = page.evaluate("(() => { const r = course.road; course.road = null; const t = idealTime(); course.road = r; return t; })()")
    assert no_road + 4 < with_road < no_road + 15
    r = page.evaluate(BOT)
    assert r["mode"] == "done" and r["t"] < r["par"], r
    assert page.evaluate("P.road") == "done"
    assert page.errors == []
