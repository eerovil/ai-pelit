"""Voimistelu v7: new task levels 21–32, a full pirouette and a bonus for connected flights (#133)."""

import pytest

from conftest import ROOT

FLY = """(seconds) => { for (let t = 0; t < seconds && mode === 'air'; t += 1 / 240) step(1 / 240); return mode; }"""

# From just before the handstand on one side of the high bar, over it, to the same place on the other side:
# a Tkatchev, kept as a flight already under way (the connection is carried on `flight.prev`).
OVER = """(T) => { const a = Math.PI - 0.6, r = R_EXT, prev = flight && flight.prev;
  launchAir({ x: r * Math.sin(a), y: -r * Math.cos(a), vx: -2 * r * Math.sin(a) / T, vy: G * T / 2, phi: a, w: 1.2 / T });
  flight.prev = prev; }"""

# Swings on the bar until the body has passed the bottom of the swing `n` times since the catch.
SWING = """(n) => { for (let t = 0; t < 10 && link.bottoms < n; t += 1 / 240) step(1 / 240); return [mode, link.bottoms]; }"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/voimistelu/v7/")
    return page


def finish_with(page, level, elements, saltos=0, halves=0, stuck=True):
    """Ends a routine on the given level after the given (name, value) elements and a landing."""
    page.evaluate("""([lv, els, saltos, halves, stuck]) => { newRoutine(); level = lv;
      for (const [n, v] of els) addElement(n, v);
      touch = { fall: false, stuck, saltos, halves }; finish(); }""", [level, elements, saltos, halves, stuck])
    return page.evaluate("result.passed")


def caught_tkatchev(page):
    page.evaluate("newRoutine()")
    page.evaluate(OVER, 0.7)
    assert page.evaluate(FLY, 2) == "bar"


def test_a_flight_let_go_within_one_swing_of_a_catch_connects(site, context):
    page = open_game(site, context)
    caught_tkatchev(page)
    assert page.evaluate(SWING, 1) == ["bar", 1]
    page.evaluate("release()")
    assert page.evaluate("flight.prev") == "Tkatchev"
    page.evaluate(OVER, 0.7)
    assert page.evaluate(FLY, 2) == "bar"
    assert page.evaluate("elements.map(e => e.name)") == ["Tkatchev", "Tkatchev", "Yhdistelmä: Tkatchev + Tkatchev"]
    # Scored once per different element: 0,3 for the Tkatchev and 0,1 for the connection.
    page.evaluate("touch = { fall: false, stuck: true, saltos: 0, halves: 0 }; finish()")
    assert page.evaluate("result.d") == pytest.approx(0.4)


def test_two_passes_of_the_bottom_or_a_landing_make_no_connection(site, context):
    page = open_game(site, context)
    caught_tkatchev(page)
    assert page.evaluate(SWING, 2) == ["bar", 2]
    page.evaluate("release()")
    assert page.evaluate("flight.prev") is None
    page.evaluate(OVER, 0.7)
    assert page.evaluate(FLY, 2) == "bar"
    assert not any(n.startswith("Yhdistelmä") for n in page.evaluate("elements.map(e => e.name)"))
    # Let go straight after a catch but land: a dismount is never connected.
    caught_tkatchev(page)
    page.evaluate("release(); launchAir({ x: -2, y: -1, s: 1 }); flight.prev = 'Tkatchev'")
    assert page.evaluate(FLY, 3) == "land"
    assert not any(n.startswith("Yhdistelmä") for n in page.evaluate("elements.map(e => e.name)"))


def test_two_half_turns_the_same_way_in_one_handstand_are_a_kokopiruetti(site, context):
    page = open_game(site, context)
    # The second swipe may come while the first half turn still turns.
    names = page.evaluate("""() => { newRoutine(); th = Math.PI - 0.2; Lb = 0.3; syncBar();
      twist(1); step(1 / 60); twist(1); return elements.map(e => e.name); }""")
    assert names == ["Kokopiruetti"]
    assert page.evaluate("tauT") == pytest.approx(2 * page.evaluate("Math.PI"))
    # The other way back is two pirouettes.
    names = page.evaluate("""() => { newRoutine(); th = Math.PI - 0.2; Lb = 0.3; syncBar();
      twist(1); tau = tauT; twist(-1); return elements.map(e => e.name); }""")
    assert names == ["Piruetti", "Piruetti"]
    # Half turns in two different handstands are two pirouettes.
    names = page.evaluate("""() => { newRoutine(); th = Math.PI - 0.2; Lb = 0.3; syncBar(); twist(1); tau = tauT;
      th = 1; syncBar(); step(1 / 240); th = Math.PI - 0.2; syncBar(); twist(1);
      return elements.map(e => e.name); }""")
    assert names == ["Piruetti", "Piruetti"]


def test_levels_14_to_20_keep_their_scores_and_21_to_32_are_the_new_tasks(site, context):
    page = open_game(site, context)
    texts = page.evaluate("[13, 14, 20, 21, 32, 33, 34, 60].map(taskText)")
    assert texts[0].startswith("Pak-voltti")
    assert texts[1] == "Saa vähintään 10,8 pistettä"
    assert texts[2] == "Saa vähintään 12,6 pistettä"
    assert texts[3] == "Jättikierto taakse ja eteen samassa sarjassa"
    assert texts[4] == "Kolmoisvoltti alas pysäytykseen"
    assert texts[5] == "Saa vähintään 12,9 pistettä"
    assert texts[6] == "Saa vähintään 13,1 pistettä"
    assert texts[7] == "Saa vähintään 15,5 pistettä"


def test_each_new_task_asks_for_its_own_thing(site, context):
    page = open_game(site, context)
    g = [("Jättikierto taakse", 0.1), ("Jättikierto eteen", 0.1)]
    assert finish_with(page, 21, g) and not finish_with(page, 21, g[:1] * 2)
    assert finish_with(page, 22, [("Tkatchev", 0.3), ("Jäger", 0.4)])
    assert not finish_with(page, 22, [("Tkatchev", 0.3), ("Tkatchev", 0.3)])
    assert finish_with(page, 23, [("Kokopiruetti", 0.4)]) and not finish_with(page, 23, [("Piruetti", 0.2)] * 2)
    one = [("Yhdistelmä: Tkatchev + Jäger", 0.1)]
    assert finish_with(page, 24, one) and not finish_with(page, 24, [("Tkatchev", 0.3), ("Jäger", 0.4)])
    assert finish_with(page, 25, [], saltos=2, halves=2) and not finish_with(page, 25, [], saltos=2, halves=1)
    assert finish_with(page, 26, [("Pak-voltti", 0.4), ("Shaposhnikova", 0.4)])
    assert not finish_with(page, 26, [("Pak-voltti", 0.4)])
    assert finish_with(page, 27, [("Kolman", 0.6)]) and not finish_with(page, 27, [("Kovacs", 0.5)])
    assert finish_with(page, 28, [], saltos=2) and not finish_with(page, 28, [], saltos=2, stuck=False)
    assert finish_with(page, 29, [("Tkatchev", 0.3), ("Jäger", 0.4), ("Pak-voltti", 0.4)])
    assert not finish_with(page, 29, [("Tkatchev", 0.3), ("Jäger", 0.4)])
    assert finish_with(page, 30, one + [("Yhdistelmä: Jäger + Tkatchev", 0.1)]) and not finish_with(page, 30, one * 2)
    assert finish_with(page, 31, [("Kolman", 0.6), ("Kovacs", 0.5), ("Kaksoisvoltti ylätangolle", 0.7), ("Pak-voltti", 0.4), ("Gienger", 0.4)])
    assert not finish_with(page, 31, [("Kolman", 0.6), ("Kovacs", 0.5)])
    assert finish_with(page, 32, [], saltos=3) and not finish_with(page, 32, [], saltos=2)
    # A fall passes nothing.
    page.evaluate("""() => { newRoutine(); level = 23; addElement('Kokopiruetti', 0.4);
      touch = { fall: true, stuck: false, saltos: 0, halves: 0 }; finish(); }""")
    assert page.evaluate("[result.passed, level]") == [False, 23]


def test_level_20_saved_by_v6_goes_on_to_the_first_new_task(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:voimistelu:taso', '20'); localStorage.setItem('ai-pelit:voimistelu:paras', '12.7')")
    page.reload()
    assert page.evaluate("[level, best, taskText(level)]") == [20, 12.7, "Saa vähintään 12,6 pistettä"]
    page.evaluate("""() => { newRoutine(); for (const [n, v] of [['Kovacs', 0.5], ['Kolman', 0.6], ['Kaksoisvoltti ylätangolle', 0.7], ['Pak-voltti', 0.4], ['Tkatchev', 0.3], ['Gienger', 0.4]]) addElement(n, v);
      touch = { fall: false, stuck: true, saltos: 2, halves: 0 }; finish(); }""")
    assert page.evaluate("[result.passed, level, taskText(level)]") == [True, 21, "Jättikierto taakse ja eteen samassa sarjassa"]
    assert page.evaluate("localStorage.getItem('ai-pelit:voimistelu:taso')") == "21"


def test_a_long_connection_name_fits_the_score_board(site, browser):
    for size in ({"width": 360, "height": 740}, {"width": 740, "height": 360}):
        ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
        page = ctx.new_page()
        site.build(ROOT / "games")
        page.goto(f"{site.url}games/voimistelu/v7/")
        page.wait_for_function("S > 0")
        widths = page.evaluate("""() => { newRoutine();
          addElement('Yhdistelmä: Kaksoisvoltti alatangolle + Kaksoisvoltti ylätangolle', 0.1, 'Yhdistelmä');
          touch = { fall: false, stuck: true, saltos: 0, halves: 0 }; finish(); resultT = 2; draw();
          const pw = wide() ? Math.min(W - SAFE_L - SAFE_R - 150, 600) / 2 - 74 : Math.min(W - 24, 360) - 76;
          const t = fitText(elements[0].name, 14, pw); x.font = '600 14px system-ui,sans-serif';
          return [x.measureText(t).width, pw, t.endsWith('…')]; }""")
        assert widths[0] <= widths[1] and widths[2]
        ctx.close()
