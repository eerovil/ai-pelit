"""Voimistelu v9: score levels end at 12,0, a catch adds no speed, D shows all through the routine (#199)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/voimistelu/v9/"


@pytest.fixture
def voim_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "voimistelu", games / "voimistelu")
    site.build(games)
    return site


def open_game(site, context, taso=None):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if taso is not None:
        page.add_init_script(f"localStorage.setItem('ai-pelit:voimistelu:taso', '{taso}')")
    page.goto(site.url + URL)
    page.wait_for_function("typeof newRoutine === 'function'")
    return page, errors


def finish_on(page, lv, total):
    """Ends a stuck routine on level `lv` with D making the total `total`."""
    page.evaluate("""([lv, d]) => { newRoutine(); level = lv; addElement('Testi', d);
      touch = { fall: false, stuck: true, saltos: 0, halves: 0 }; finish(); }""", [lv, total - 10])
    return page.evaluate("[result.passed, level]")


def test_score_levels_end_at_12_and_go_on_to_the_new_tasks(voim_site, context):
    page, errors = open_game(voim_site, context)
    targets = page.evaluate("[14, 15, 16, 17, 18].map(target)")
    assert targets == pytest.approx([10.8, 11.1, 11.4, 11.7, 12.0])
    assert finish_on(page, 17, 11.7) == [True, 18]
    assert finish_on(page, 18, 11.9) == [False, 18]
    assert finish_on(page, 18, 12.0) == [True, 21]
    assert page.evaluate("localStorage.getItem('ai-pelit:voimistelu:taso')") == "21"
    assert page.evaluate("taskText(21)") == "Jättikierto taakse ja eteen samassa sarjassa"
    assert errors == []


@pytest.mark.parametrize("saved,now", [(18, 18), (19, 21), (20, 21), (21, 21), (25, 25)])
def test_a_phone_saved_on_level_19_or_20_goes_on_from_21(voim_site, context, saved, now):
    page, errors = open_game(voim_site, context, saved)
    assert page.evaluate("level") == now
    assert page.evaluate("localStorage.getItem('ai-pelit:voimistelu:taso')") == str(now)
    assert errors == []


# Flights that end on the high bar, from all round it: random but the same each run. Each catch is checked
# once the joint has handed the body to the rigid swing: the swing has no more energy than the flight had
# at the catch, or (when the arms straightening lifted the body) no more speed.
CATCHES = """(N) => {
  let seed = 12345; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const flightE = () => [0.5 * (vel[0] ** 2 + vel[1] ** 2) + 0.5 * L * L / icAir(s), G * pos[1]];
  let at = null; const grab0 = grab; grab = to => { at = flightE(); grab0(to); };
  const out = [];
  for (let k = 0; k < N; k++) {
    newRoutine(); hold = false; at = null;
    const a = rnd() * TAU, d = 0.5 + rnd() * 1.2, phi = rnd() * TAU, w = (rnd() * 2 - 1) * 8;
    const vx = (rnd() * 2 - 1) * 5, vy = (rnd() * 2 - 1) * 5;
    launchAir({ x: d * Math.sin(a), y: -d * Math.cos(a), vx, vy, phi, w, from: 1 });
    flight.t = 1; // ready to catch either bar at once
    for (let t = 0; t < 0.6 && mode === 'air'; t += 1 / 240) step(1 / 240);
    if (mode !== 'bar' || bar !== 0) continue;
    for (let t = 0; t < 4 && jt; t += 1 / 240) step(1 / 240);
    if (mode !== 'bar') continue;
    const r = rBar(s), ke = 0.5 * (icBar(s) + r * r) * barOmega() ** 2, pe = G * (BARS[bar][1] - r * Math.cos(th));
    out.push({ k, a: +a.toFixed(2), ke0: at[0], e0: at[0] + at[1], ke, e: ke + pe, w: barOmega() });
  }
  grab = grab0;
  return out;
}"""


def test_a_catch_from_any_angle_adds_no_speed(voim_site, context):
    page, errors = open_game(voim_site, context)
    caught = page.evaluate(CATCHES, 3000)
    assert len(caught) > 1000
    # From every side of the bar.
    assert len({int(c["a"] / 0.5) for c in caught}) == 13
    bad = [c for c in caught if c["e"] > c["e0"] + 0.1 and c["ke"] > c["ke0"] + 0.1]
    assert bad == []
    # v8 spun up to 160 rad/s; a flight of at most 8 rad/s and 7 m/s is caught to a few turns a second.
    assert max(abs(c["w"]) for c in caught) < 9
    assert errors == []


def test_a_shoulder_caught_right_at_the_bar_does_not_spin(voim_site, context):
    # One of v8's: the shoulder 0.1 m from the bar when the hands took it, then giant swings at 160 rad/s.
    page, errors = open_game(voim_site, context)
    w = page.evaluate("""() => { newRoutine(); hold = false;
      launchAir({ x: -0.218, y: -0.471, vx: 1.599, vy: 1.910, phi: 5.874, w: -0.172, from: 1 }); flight.t = 1;
      for (let t = 0; t < 0.6 && mode === 'air'; t += 1 / 240) step(1 / 240);
      if (mode !== 'bar') return null;
      for (let t = 0; t < 2; t += 1 / 240) step(1 / 240);
      return [mode, barOmega(), elements.filter(e => e.name.startsWith('Jättikierto')).length]; }""")
    assert w is not None and w[0] == "bar"
    assert abs(w[1]) < 6
    assert w[2] == 0
    assert errors == []


def test_d_shows_all_through_the_routine(voim_site, context):
    page, errors = open_game(voim_site, context)
    page.evaluate("""() => { window.drawn = []; const f = x.fillText.bind(x);
      x.fillText = (t, ...a) => { drawn.push(t); return f(t, ...a); }; }""")
    page.evaluate("newRoutine(); drawn = []; draw()")
    assert "D 0,0" in page.evaluate("drawn")
    # Each different element once, as the score board counts it.
    page.evaluate("addElement('Tkatchev', 0.3); addElement('Tkatchev', 0.3); addElement('Jättikierto taakse', 0.1); drawn = []; draw()")
    assert "D 0,4" in page.evaluate("drawn")
    assert page.evaluate("difficulty()") == pytest.approx(0.4)
    assert errors == []
