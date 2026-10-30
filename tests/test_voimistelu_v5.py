"""Voimistelu v5: the arms turn towards a nearby bar almost at once (#84)."""

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


def open_game(site, context, v=5):
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
    # Just caught, the body hangs on a joint at the shoulders until it is in line with the arms, then
    # swings as one piece; the hands are on the bar all the while.
    on, worst, left = page.evaluate("""() => { const on = !!jt; let worst = 0;
      for (let t = 0; t < 1.6; t += 1 / 240) { step(1 / 240); const h = bodyPoints().hand;
        worst = Math.max(worst, Math.hypot(h[0] - BARS[bar][0], h[1] - BARS[bar][1])); }
      return [on, worst, jt]; }""")
    assert on
    assert worst < 0.01
    assert left is None


def test_a_legs_first_catch_swings_on_the_shoulder_joint_without_a_jump(site, context):
    page = open_game(site, context)
    # Body flat, head first to the left, flying right past the low bar feet first.
    worst, arms, got = page.evaluate("""() => { newRoutine(); launchAir({ from: 0, x: 0.6, y: -0.2, vx: 3.5, vy: 0.5, phi: 2 });
      flight.t = 1; let prev = bodyPoints(), worst = 0, arms = 0, on = false;
      for (let t = 0; t < 1.5; t += 1 / 240) { const m = mode; step(1 / 240); if (m === 'air' && mode === 'bar') on = t;
        const q = bodyPoints();
        for (const n of ['head', 'hip', 'foot']) worst = Math.max(worst, Math.hypot(q[n][0] - prev[n][0], q[n][1] - prev[n][1]));
        arms = Math.max(arms, Math.hypot(q.hand[0] - q.sh[0], q.hand[1] - q.sh[1]));
        prev = q; if (on !== false && !jt) break; }
      return [worst, arms, [mode, bar]]; }""")
    assert got == ["bar", 1]
    # No point moves more than 8 cm in a 1/240 s step (v4 jumped about 40 cm), and the arms are never longer
    # than they were reaching for the bar.
    assert worst < 0.08
    assert arms < 0.85


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


def test_the_arms_turn_almost_at_once(site, context):
    page = open_game(site, context)
    # The high bar just below the shoulders, behind the raised arms: they swing nearly a half turn round to
    # it, in no more than about 0.06 s.
    turn, took = page.evaluate("""() => { newRoutine(); launchAir({ x: 0.2, y: 0.3, phi: 0 }); flight.t = 1;
      let t = 0;
      while (t < 1) { aim(true, () => true, 1 / 240); t += 1 / 240; if (armT && Math.abs(wrap(arm - armT)) < 0.01) break; }
      return [armT, t]; }""")
    assert abs(turn) > 2.5
    assert took < 0.06


def test_letting_go_on_the_joint_keeps_the_spin(site, context):
    page = open_game(site, context)
    got = page.evaluate("""() => { newRoutine(); launchAir({ from: 0, x: 0.6, y: -0.2, vx: 3.5, vy: 0.5, phi: 2 }); flight.t = 1;
      while (mode === 'air') step(1 / 240);
      for (let i = 0; i < 20; i++) step(1 / 240);
      const wb = jt.wb; release(); return [mode, jt, Math.abs(L / icAir(s) - wb)]; }""")
    assert got[0] == "air" and got[1] is None
    assert got[2] < 1e-9


def test_the_shoulder_lock_keeps_the_swing_and_turns_either_way(site, context):
    page = open_game(site, context)
    lost, ways = page.evaluate("""() => { let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const Ej = () => { const mF = 1 - J_MS; return 0.5 * (J_MS * (jt.vS[0] ** 2 + jt.vS[1] ** 2) + mF * (jt.vF[0] ** 2 + jt.vF[1] ** 2)) + G * (J_MS * jt.S[1] + mF * jt.F[1]); };
      let lost = 0; const ways = [0, 0];
      for (let n = 0; n < 60; n++) { newRoutine(); launchAir({ from: 0, x: -0.5 + rnd() * 2.8, y: 1.6, vx: 2 * rnd() - 1, phi: rnd() * TAU, w: 4 * rnd() - 2 }); flight.t = 1;
        while (mode === 'air') step(1 / 240);
        if (!jt) continue;
        let before = null, last = 0;
        while (jt) { if (jt.lock === undefined || before === null) before = Ej(); last = Ej(); step(1 / 240); }
        lost = Math.max(lost, before - last);
        for (let i = 0; i < 24; i++) step(1 / 240);
        ways[barOmega() > 0 ? 0 : 1]++; }
      return [lost, ways]; }""")
    # Locking the body in line with the arms takes no swing away (it took about 12 J/kg in a typical catch
    # before), and the body goes round the bar either way.
    assert lost < 0.5
    assert min(ways) > 10
