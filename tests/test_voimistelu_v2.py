"""Voimistelu v2: a second, lower bar as on the uneven bars, and a camera that keeps the gymnast on screen."""

import json

from conftest import ROOT

FLY = """(seconds) => { for (let t = 0; t < seconds && mode === 'air'; t += 1 / 240) step(1 / 240); return mode; }"""

# A flight from one bar to a place where the hands are on the other: COM at angle a1 about bar `from`,
# to angle a2 about bar `to`, in T seconds, with `turns` whole turns more on the way.
BETWEEN = """([from, a1, to, a2, T, turns]) => {
  const r = R_EXT, A = BARS[from], B = BARS[to];
  const x1 = A[0] + r * Math.sin(a1), y1 = A[1] - r * Math.cos(a1), x2 = B[0] + r * Math.sin(a2), y2 = B[1] - r * Math.cos(a2);
  newRoutine(); elements = [];
  launchAir({ from, x: x1, y: y1, vx: (x2 - x1) / T, vy: (y2 - y1) / T + G * T / 2, phi: a1,
              w: (a2 - a1 + turns * TAU) / T }); }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/voimistelu/v2/")
    return page


def test_flying_from_the_high_bar_to_the_low_bar_catches_it(site, context):
    page = open_game(site, context)
    page.evaluate(BETWEEN, [0, 0.9, 1, -0.3, 0.5, 0])
    assert page.evaluate(FLY, 2) == "bar"
    assert page.evaluate("[bar, elements.map(e => e.name)]") == [1, ["Siirto alatangolle"]]
    # With a backward salto on the way it is a Pak salto.
    page.evaluate(BETWEEN, [0, 1.2, 1, 0.3, 0.8, -1])
    assert page.evaluate(FLY, 2) == "bar"
    assert page.evaluate("[bar, elements.map(e => e.name)]") == [1, ["Pak-voltti"]]


def test_flying_up_from_the_low_bar_catches_the_high_bar_as_a_shaposhnikova(site, context):
    page = open_game(site, context)
    page.evaluate(BETWEEN, [1, -1.6, 0, 0.6, 0.6, 0])
    assert page.evaluate(FLY, 2) == "bar"
    assert page.evaluate("[bar, elements.map(e => e.name)]") == [0, ["Shaposhnikova"]]
    # Caught, it swings about the high bar.
    assert page.evaluate("Math.hypot(pos[0], pos[1])") < 1.1


def test_a_real_low_bar_swing_can_reach_the_high_bar(site, context):
    page = open_game(site, context)
    # Swinging towards the high bar, let go under it and tuck a moment, as a player would.
    got = page.evaluate("""() => { newRoutine(); bar = 1; th = 2.4; Lb = 0; s = 0; syncBar(); let g = 0;
      while (g++ < 20000) { step(0.002); if (barOmega() < -0.3 && Math.abs(wrap(th) + 1.57) < 0.03) break; }
      release(); hold = true;
      for (let t = 0; t < 3 && mode === 'air'; t += 1 / 240) { if (t > 0.3) hold = false; step(1 / 240); }
      return [mode, bar]; }""")
    assert got == ["bar", 0]


def test_the_low_bar_swing_does_not_grow_by_itself_and_the_feet_clear_the_floor(site, context):
    page = open_game(site, context)
    a, low = page.evaluate("""() => { newRoutine(); bar = 1; th = 1.2; Lb = 0; syncBar(); let a = 0, low = 0;
      for (let t = 0; t < 20; t += 1 / 60) { hold = false; step(1 / 60);
        if (t > 15) a = Math.max(a, Math.abs(wrap(th)));
        if (t > 1) { const b = bodyPoints(); for (const k in b) low = Math.min(low, b[k][1]); } }
      return [a, low]; }""")
    assert a < 1.2
    assert low > page.evaluate("FLOOR")


def test_the_camera_keeps_a_far_flight_on_screen(site, context):
    page = open_game(site, context)
    page.wait_for_function("S > 0")
    page.evaluate("launchAir({ x: 1, y: 0.5, vx: 5, vy: 7 })")
    worst = page.evaluate("""() => new Promise(done => { let worst = 0, n = 0;
      (function check() {
        const [px, py] = sc(pos);
        worst = Math.max(worst, -px, px - W, -py, py - H);
        if (mode === 'air' && n++ < 200) requestAnimationFrame(check); else done(worst);
      })(); })""")
    assert worst <= 0


def test_v1_progress_carries_on_into_the_new_bar_tasks(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:voimistelu:taso', '11'); localStorage.setItem('ai-pelit:voimistelu:paras', '11.2')")
    page.reload()
    assert page.evaluate("[level, best, taskText(level)]") == [11, 11.2, "Siirry alatangolle"]
    meta = json.loads((ROOT / "games/voimistelu/game.json").read_text())
    assert [v["n"] for v in meta["versions"]] == [1, 2]
