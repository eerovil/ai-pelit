"""Voimistelu v4: in the air the arms turn towards a nearby bar, so a near miss is still caught (#84)."""

from conftest import ROOT

FLY = """(seconds) => { for (let t = 0; t < seconds && mode === 'air'; t += 1 / 240) step(1 / 240); return mode; }"""

# A flight from the high bar towards a catch on the low bar, aimed (dx, dy) metres off the place where
# straight arms would have the hands on it.
NEAR_MISS = """([dx, dy]) => {
  const r = R_EXT, A = BARS[0], B = BARS[1], T = 0.5, a1 = 0.9, a2 = -0.3;
  const x1 = A[0] + r * Math.sin(a1), y1 = A[1] - r * Math.cos(a1);
  const x2 = B[0] + r * Math.sin(a2) + dx, y2 = B[1] - r * Math.cos(a2) + dy;
  newRoutine(); elements = [];
  launchAir({ from: 0, x: x1, y: y1, vx: (x2 - x1) / T, vy: (y2 - y1) / T + G * T / 2, phi: a1, w: (a2 - a1) / T }); }"""


def open_game(site, context, v=4):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/voimistelu/v{v}/")
    return page


# Each of these lands on the mat in v3 with straight arms.
MISSES = [[-0.3, 0], [0, -0.3], [0.45, 0.2], [-0.4, -0.3], [0, -0.6], [0.6, 0.4]]


def test_near_misses_with_straight_arms_are_caught_by_reaching_arms(site, context):
    v3 = open_game(site, context, 3)
    for miss in MISSES:
        v3.evaluate(NEAR_MISS, miss)
        assert v3.evaluate(FLY, 2) == "land", miss
    page = open_game(site, context)
    for miss in MISSES:
        page.evaluate(NEAR_MISS, miss)
        assert page.evaluate(FLY, 2) == "bar", miss
        assert page.evaluate("[bar, elements.map(e => e.name)]") == [1, ["Siirto alatangolle"]], miss


def test_the_arms_turn_towards_the_bar_and_the_hands_stay_on_it_after_the_catch(site, context):
    page = open_game(site, context)
    page.evaluate(NEAR_MISS, [0, -0.3])
    turned = page.evaluate("""() => { let most = 0;
      for (let t = 0; t < 2 && mode === 'air'; t += 1 / 240) { step(1 / 240); most = Math.max(most, Math.abs(arm)); }
      return most; }""")
    assert turned > 0.3
    # Just caught with the arms turned, the body eases into line with them within half a second; the hands
    # are on the bar all the while.
    off, worst, left = page.evaluate("""() => { const off = Math.abs(snap); let worst = 0;
      for (let t = 0; t < 0.5; t += 1 / 240) { step(1 / 240); const h = bodyPoints().hand;
        worst = Math.max(worst, Math.hypot(h[0] - BARS[bar][0], h[1] - BARS[bar][1])); }
      return [off, worst, snap]; }""")
    assert off > 0.1
    assert worst < 0.01
    assert abs(left) < 0.01


def test_a_far_flight_still_lands_and_the_arms_go_back_in_line(site, context):
    page = open_game(site, context)
    page.evaluate(NEAR_MISS, [-0.6, 0])
    assert page.evaluate(FLY, 2) == "land"
    assert page.evaluate("[arm, armK]") == [0, 1]


def test_the_arms_do_not_reach_while_tucked_or_for_the_bar_just_let_go_of_on_the_way_up(site, context):
    page = open_game(site, context)
    # Tucked through a near miss: no reach and no catch.
    page.evaluate(NEAR_MISS, [0, -0.3])
    page.evaluate("s = 1; hold = true")
    assert page.evaluate("""() => { let most = 0;
      for (let t = 0; t < 2 && mode === 'air'; t += 1 / 240) { step(1 / 240); most = Math.max(most, Math.abs(arm)); }
      return [mode, most]; }""") == ["land", 0]
    # Let go of the high bar going up: the arms leave it alone until the body falls.
    page.evaluate("newRoutine(); th = 2.6; Lb = 6 * (icBar(0) + R_EXT * R_EXT); syncBar(); release()")
    early = page.evaluate("""() => { let most = 0;
      for (let t = 0; t < 2 && mode === 'air' && vel[1] > 0; t += 1 / 240) { step(1 / 240); most = Math.max(most, Math.abs(arm)); }
      return most; }""")
    assert early == 0
