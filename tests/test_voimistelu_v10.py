"""Voimistelu v10: the bar let go of is caught again only after a moment off it (#199)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/voimistelu/v10/"

# Let go from the handstand on the high bar with a little hop up: the body falls back onto the bar.
HOP = """(vy) => { newRoutine(); hold = false;
  launchAir({ x: 0, y: 1.0, vx: 0, vy, phi: Math.PI, w: 0, from: 0 });
  let caughtAt = null;
  for (let t = 0; t < 1.5 && mode === 'air'; t += 1 / 240) { step(1 / 240); if (mode === 'bar') caughtAt = flight.t; }
  return [mode, caughtAt]; }"""

# From just before the handstand on one side of the high bar, over it, to the other side: a Tkatchev.
OVER = """(T) => { newRoutine(); const a = Math.PI - 0.6, r = R_EXT;
  launchAir({ x: r * Math.sin(a), y: -r * Math.cos(a), vx: -2 * r * Math.sin(a) / T, vy: G * T / 2, phi: a, w: 1.2 / T });
  for (let t = 0; t < 2 && mode === 'air'; t += 1 / 240) step(1 / 240);
  return [mode, flight.t, elements.map(e => e.name)]; }"""


@pytest.fixture
def voim_site(site, tmp_path):
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "voimistelu", games / "voimistelu")
    site.build(games)
    return site


def open_game(site, context, url=URL):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + url)
    page.wait_for_function("typeof newRoutine === 'function'")
    return page, errors


@pytest.mark.parametrize("vy", [0.5, 1.0, 1.5])
def test_a_small_hop_off_the_bar_is_not_caught_at_once(voim_site, context, vy):
    # v9 caught these straight back, a quarter of a second after letting go.
    page, errors = open_game(voim_site, context, "games/voimistelu/v9/")
    mode, at = page.evaluate(HOP, vy)
    assert mode == "bar" and at < 0.5
    page, errors = open_game(voim_site, context)
    mode, at = page.evaluate(HOP, vy)
    assert at is None or at >= 0.5
    assert errors == []


def test_a_release_move_is_still_caught(voim_site, context):
    page, errors = open_game(voim_site, context)
    mode, t, names = page.evaluate(OVER, 0.7)
    assert mode == "bar" and t >= 0.5
    assert names == ["Tkatchev"]
    assert errors == []


def test_the_other_bar_is_still_caught_at_once(voim_site, context):
    # Let go of the low bar right under the high one: its hands take the high bar well before 0.5 s.
    page, errors = open_game(voim_site, context)
    mode, bar, at = page.evaluate("""() => { newRoutine(); hold = false;
      launchAir({ x: 0, y: -1.3, vx: 0, vy: 3, phi: 0, w: 0, from: 1 });
      for (let t = 0; t < 1 && mode === 'air'; t += 1 / 240) step(1 / 240);
      return [mode, bar, flight.t]; }""")
    assert (mode, bar) == ("bar", 0) and at < 0.5
    assert errors == []
