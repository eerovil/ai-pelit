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


def test_the_camera_keeps_the_whole_body_on_screen_in_fast_flights(site, browser):
    site.build(ROOT / "games")
    for size in ({"width": 360, "height": 740}, {"width": 360, "height": 640}):
        ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(f"{site.url}games/voimistelu/v2/")
        page.wait_for_function("S > 0")
        # Fast sideways with the body flat, fast up and all the way down again, and both, frame by frame
        # through the game's own loop, until the body lands.
        for launch in ("{ x: 1, y: 0.3, vx: 8, vy: 3, phi: Math.PI / 2 }", "{ x: 0, y: 0.5, vy: 11, phi: Math.PI }",
                       "{ x: 0.5, y: 0.5, vy: 22 }", "{ x: -1, y: 0.5, vx: -6, vy: 9, phi: -Math.PI / 2, w: 3 }"):
            page.evaluate(f"newRoutine(); launchAir({launch})")
            worst = page.evaluate("""() => new Promise(done => { let worst = -Infinity, n = 0;
              (function check() {
                const b = bodyPoints();
                // From the first frame the game has drawn since the launch.
                if (n > 0) for (const k in b) { const [px, py] = sc(b[k]); worst = Math.max(worst, -px, px - W, SAFE_T - py, py - (H - SAFE_B)); }
                if (mode === 'air' && n++ < 600) requestAnimationFrame(check); else done(worst);
              })(); })""")
            assert worst <= 0, (size, launch)
        ctx.close()


def test_flights_between_the_bars_are_named_by_their_turns(site, context):
    page = open_game(site, context)
    for turns, T, name in ((0, 0.8, "Siirto alatangolle"), (-1, 0.8, "Pak-voltti"), (-2, 1.2, "Kaksoisvoltti alatangolle")):
        page.evaluate(BETWEEN, [0, 1.2, 1, 0.3, T, turns])
        assert page.evaluate(FLY, 2) == "bar"
        assert page.evaluate("[bar, elements.map(e => e.name)]") == [1, [name]], turns
    for a1, turns, name in ((-1.6, 0, "Shaposhnikova"), (-1.9, 1, "Voltti ylätangolle"), (-1.9, 2, "Kaksoisvoltti ylätangolle")):
        page.evaluate(BETWEEN, [1, a1, 0, 0.3, 0.8, turns])
        assert page.evaluate(FLY, 2) == "bar"
        assert page.evaluate("[bar, elements.map(e => e.name)]") == [0, [name]], turns


def finish_with(page, level, names):
    page.evaluate(f"""() => {{ newRoutine(); level = {level};
      for (const n of {names!r}) addElement(n, 0.1);
      touch = {{ fall: false, stuck: true, saltos: 0, halves: 0 }}; finish(); }}""")
    return page.evaluate("result.passed")


def test_each_bar_task_asks_for_its_own_move(site, context):
    page = open_game(site, context)
    for name in ("Siirto alatangolle", "Pak-voltti", "Kaksoisvoltti alatangolle"):
        assert finish_with(page, 11, [name])
    assert not finish_with(page, 11, ["Shaposhnikova"])
    assert finish_with(page, 12, ["Shaposhnikova"])
    for name in ("Voltti ylätangolle", "Kaksoisvoltti ylätangolle", "Pak-voltti"):
        assert not finish_with(page, 12, [name])
    assert finish_with(page, 13, ["Pak-voltti"])
    for name in ("Siirto alatangolle", "Kaksoisvoltti alatangolle", "Shaposhnikova"):
        assert not finish_with(page, 13, [name])


def test_v1_progress_carries_on_into_the_new_bar_tasks(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:voimistelu:taso', '11'); localStorage.setItem('ai-pelit:voimistelu:paras', '11.2')")
    page.reload()
    assert page.evaluate("[level, best, taskText(level)]") == [11, 11.2, "Siirry alatangolle"]
    meta = json.loads((ROOT / "games/voimistelu/game.json").read_text())
    assert [v["n"] for v in meta["versions"]][:2] == [1, 2]
