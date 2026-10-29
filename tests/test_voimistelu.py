"""Voimistelu in a phone-sized Chromium: a pumped swing, release moves caught again, and a judged dismount."""

from conftest import ROOT

# Runs the game's own step() until the body is back on the bar, has landed, or the time is up.
FLY = """(seconds) => { for (let t = 0; t < seconds && mode === 'air'; t += 1 / 240) step(1 / 240); return mode; }"""
# Plays out the landing until the score board shows.
SETTLE = """() => { for (let t = 0; t < 3 && mode !== 'result'; t += 1 / 60) step(1 / 60); return mode; }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/voimistelu/v1/")
    return page


def test_pumping_the_swing_reaches_a_giant_swing_and_hanging_still_dies_down(site, context):
    page = open_game(site, context)
    # Pulled in through the bottom, straight at the ends of the swing.
    t = page.evaluate("""() => { newRoutine(); let t = 0;
      for (; t < 30 && !elements.length; t += 1 / 60) { hold = Math.abs(wrap(th)) < 1; step(1 / 60); } return t; }""")
    assert t < 20
    assert page.evaluate("elements[0].name").startswith("Jättikierto")
    left = page.evaluate("""() => { newRoutine(); const a0 = th; let a = 0;
      for (let t = 0; t < 30; t += 1 / 60) { hold = false; step(1 / 60); if (t > 25) a = Math.max(a, Math.abs(wrap(th))); } return [a0, a]; }""")
    assert left[1] < left[0] * 0.9


def test_a_tuck_spins_faster_and_keeps_the_angular_momentum(site, context):
    page = open_game(site, context)
    page.evaluate("launchAir({ x: 0, y: 1, vy: 3, w: 4 })")
    w0 = page.evaluate("phiDot()")
    page.evaluate("hold = true; for (let i = 0; i < 30; i++) step(1 / 60)")
    w1 = page.evaluate("phiDot()")
    assert abs(w0 - 4) < 1e-9
    assert abs(w1 / w0 - page.evaluate("IC_EXT / IC_TUCK")) < 1e-6


# From just before the handstand on one side of the bar, over it, to the same place on the other side.
OVER = """([T, turns]) => { const a = Math.PI - 0.6, r = R_EXT;
  launchAir({ x: r * Math.sin(a), y: -r * Math.cos(a), vx: -2 * r * Math.sin(a) / T, vy: G * T / 2,
              phi: a, w: (1.2 + turns * TAU) / T }); }"""


def test_flying_over_the_bar_and_catching_it_is_a_tkatchev(site, context):
    page = open_game(site, context)
    page.evaluate(OVER, [0.7, 0])
    assert page.evaluate(FLY, 2) == "bar"
    assert page.evaluate("elements.map(e => e.name)") == ["Tkatchev"]


def test_a_double_salto_over_the_bar_is_caught_again_as_a_kovacs(site, context):
    page = open_game(site, context)
    page.evaluate(OVER, [1.2, 2])
    assert page.evaluate(FLY, 3) == "bar"
    assert page.evaluate("elements.map(e => e.name)") == ["Kovacs"]
    # Caught, it swings on the way it was spinning.
    assert page.evaluate("Lb") > 3


def test_a_tucked_double_salto_can_be_stuck_and_passes_the_level(site, context):
    page = open_game(site, context)
    page.evaluate("level = 7")  # Kaksoisvoltti alas
    # Tucked for the first 0.7 s, then open: find the spin that lands upright.
    best = page.evaluate("""() => { let best = null;
      for (let w = 3; w < 9; w += 0.02) {
        newRoutine(); elements = []; launchAir({ x: 0.8, y: 0.3, vx: 0.8, vy: 4.5, w }); hold = true;
        for (let t = 0; t < 3 && mode === 'air'; t += 1 / 240) { if (t > 0.7) hold = false; step(1 / 240); }
        if (mode === 'land' && touch.saltos === 2 && touch.onFeet && (!best || Math.abs(touch.aEff) < Math.abs(best.aEff)))
          best = { w, aEff: touch.aEff };
      } return best; }""")
    assert best and abs(best["aEff"]) < 0.3
    page.evaluate(f"""newRoutine(); launchAir({{ x: 0.8, y: 0.3, vx: 0.8, vy: 4.5, w: {best['w']} }}); hold = true;
      for (let t = 0; t < 3 && mode === 'air'; t += 1 / 240) {{ if (t > 0.7) hold = false; step(1 / 240); }}""")
    assert page.evaluate("[touch.stuck, touch.fall]") == [True, False]
    assert page.evaluate(SETTLE) == "result"
    r = page.evaluate("result")
    assert r["passed"] and r["names"] == ["Kaksoisvoltti alas"]
    assert abs(r["d"] - 0.3) < 1e-9 and abs(r["e"] - 10) < 1e-9
    page.reload()
    assert page.evaluate("[level, best, routines]") == [8, 10.3, 1]


def test_landing_on_the_back_is_a_fall_and_the_level_stays(site, context):
    page = open_game(site, context)
    page.evaluate("launchAir({ x: 0, y: -1, phi: Math.PI / 2 })")
    assert page.evaluate(FLY, 2) == "land"
    assert page.evaluate("touch.fall") is True
    page.evaluate(SETTLE)
    assert page.evaluate("[result.passed, result.e, level]") == [False, 9, 1]


def test_a_flick_up_lets_go_and_a_flick_sideways_in_the_handstand_is_a_pirouette(site, context):
    page = open_game(site, context)
    # Slowly over the top, as in a giant swing.
    page.evaluate("th = Math.PI - 0.2; Lb = 0.5; s = 0; syncBar()")
    page.mouse.move(150, 500)
    page.mouse.down()
    page.mouse.move(250, 505)
    page.mouse.up()
    assert page.evaluate("elements.map(e => e.name)") == ["Piruetti"]
    assert page.evaluate("tauT") == page.evaluate("Math.PI")
    # A slow drag does nothing but pull in while the finger is down.
    page.mouse.move(180, 500)
    page.mouse.down()
    assert page.evaluate("hold") is True
    page.wait_for_timeout(450)
    page.mouse.move(180, 300)
    page.mouse.up()
    assert page.evaluate("[mode, hold]") == ["bar", False]
    # A quick flick up lets go.
    page.mouse.move(180, 500)
    page.mouse.down()
    page.mouse.move(180, 420)
    page.mouse.up()
    assert page.evaluate("mode") in ("air", "land")


def finish_with(page, level, names):
    """Ends a routine with a stuck landing after the given elements, on the given level."""
    page.evaluate(f"""() => {{ newRoutine(); level = {level};
      for (const n of {names!r}) addElement(n, 0.1);
      touch = {{ fall: false, stuck: true, saltos: 0, halves: 0 }}; finish(); }}""")
    return page.evaluate("result.passed")


def test_a_release_task_asks_for_that_release_move_and_no_other(site, context):
    page = open_game(site, context)
    assert finish_with(page, 8, ["Jäger"]) and finish_with(page, 8, ["Gienger"])
    assert not finish_with(page, 8, ["Kovacs"]) and not finish_with(page, 8, ["Kolman"])
    assert finish_with(page, 10, ["Kovacs"])
    assert not finish_with(page, 10, ["Kolman"]) and not finish_with(page, 10, ["Kolmoisvoltti tangolle"])


def test_the_score_board_fits_a_small_screen_however_many_elements(site, browser):
    from conftest import ROOT as _root
    site.build(_root / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(f"{site.url}games/voimistelu/v1/")
    page.evaluate("""() => { newRoutine();
      for (let i = 0; i < 26; i++) addElement('Jättikierto taakse', 0.1);
      for (const n of ['Piruetti', 'Tkatchev', 'Jäger', 'Kovacs', 'Kolman', 'Lentoliike', 'Gienger', 'Jättikierto eteen',
                       'Lentoliike kierteellä', 'Kolmoisvoltti tangolle', 'Voltti alas']) addElement(n, 0.2);
      deductions = [['Iso askel', 0.5], ['Kerä auki liian myöhään', 0.3], ['Kierre kesken', 0.3]];
      touch = { fall: false, stuck: false, saltos: 1, halves: 0 }; finish(); resultT = 1; best = 0; result.record = true; }""")
    page.wait_for_timeout(200)
    lay = page.evaluate("resultLayout")
    assert lay["bottom"] <= 640 and lay["tapY"] < lay["bottom"]
    assert lay["recordY"] < lay["tapY"] - 15
    assert page.evaluate("result.names.length") == 37
    ctx.close()
