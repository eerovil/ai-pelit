"""Trampoliini v4: 🌀 held down keeps twisting until it is let go."""

import sys
from pathlib import Path

from conftest import ROOT

sys.path.insert(0, str(Path(__file__).parent))
from test_trampoliini import TRICK  # noqa: E402

URL = "games/trampoliini/v4/"
HOLD = "() => { window.__step = step; step = () => {}; }"
# Straight jump at full height on the big garden trampoline; 🌀 held from `start` s after take-off
# for `hold` s (pressed on the mat when start is None). Returns the landing and the twists done.
JUMP = """([start, hold]) => { const s = window.__step;
  stand(0); J.vin = T.vMax; lastLand = null;
  while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
  if (start === null) twistDown();
  else { J.pumpT = CONTACT / 2; }
  while (phase === 'mat') s(1 / 60);
  let t = 0;
  if (start !== null) { while (t < start) { s(1 / 60); t += 1 / 60; } twistDown(); t = 0; }
  while (t < hold) { s(1 / 60); t += 1 / 60; }
  twistUp();
  const atRelease = J.twist;
  while (phase === 'air') s(1 / 60);
  return [lastLand, atRelease]; }"""


def open_game(site, context, width=360, height=740):
    site.build(ROOT / "games")
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.goto(site.url + URL)
    page.click("#go")
    page.evaluate(HOLD)
    return page


def test_holding_the_twist_keeps_twisting_and_letting_go_finishes_the_twist_under_way(site, context):
    page = open_game(site, context)
    land, at_release = page.evaluate(JUMP, [None, 0.8])
    assert 1 < at_release < 2                     # still twisting past the first whole twist
    assert land == {"trick": [0, 2], "clean": True}


def test_a_quick_tap_is_still_one_twist(site, context):
    page = open_game(site, context)
    land, _ = page.evaluate(JUMP, [None, 0])
    assert land == {"trick": [0, 1], "clean": True}


def test_pressed_in_the_air_it_twists_from_there_until_let_go(site, context):
    page = open_game(site, context)
    land, at_release = page.evaluate(JUMP, [0.2, 0.5])
    assert 0.5 < at_release < 1
    assert land == {"trick": [0, 1], "clean": True}
    land, _ = page.evaluate(JUMP, [0.1, 1.0])
    assert land["trick"][1] == 2 and land["clean"]


def test_held_into_the_landing_the_twist_is_unfinished_and_you_fall(site, context):
    page = open_game(site, context)
    land = page.evaluate("""() => { const s = window.__step;
      stand(0); J.vin = T.vMax; lastLand = null;
      while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
      twistDown();
      while (phase === 'mat') s(1 / 60);
      while (phase === 'air') s(1 / 60);      // never let go before the landing
      return lastLand; }""")
    assert land == {"crash": "kierre"}


def test_the_real_button_twists_while_pressed(site, context):
    page = open_game(site, context)
    page.evaluate("() => { const s = window.__step; stand(0); J.vin = T.vMax; while (phase === 'mat') s(1 / 60); for (let i = 0; i < 6; i++) s(1 / 60); }")
    btn = page.locator("#pad button[data-act=kierre]")
    btn.dispatch_event("pointerdown", {"pointerId": 3})
    page.evaluate("() => { for (let i = 0; i < 50; i++) window.__step(1 / 60); }")
    assert page.evaluate("[twistHeld, J.twist > 1, J.twists]") == [True, True, 2]
    btn.dispatch_event("pointerup", {"pointerId": 3})
    assert page.evaluate("twistHeld") is False


def test_a_flip_with_a_held_twist_still_lands(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("level = 4; setup()")
    for n, tw in [(1, 2), (-1, 1), (2, 0)]:
        ok = any(
            (r := page.evaluate(TRICK, [n, tw, 0.2 + i * 0.1])) and r.get("trick") == [n, tw] and r.get("clean")
            for i in range(25)
        )
        assert ok, (n, tw)


def test_the_menu_with_the_longer_help_fits_small_phones(site, context):
    site.build(ROOT / "games")
    for width, height in ((360, 640), (390, 740)):
        page = context.new_page()
        page.set_viewport_size({"width": width, "height": height})
        page.goto(site.url + URL)
        go = page.locator("#go").bounding_box()
        assert go["y"] >= 0 and go["y"] + go["height"] <= height
        page.close()


def test_v4_plays_on_with_the_saved_level_and_record(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:trampoliini:taso', '5'); localStorage.setItem('ai-pelit:trampoliini:ennatys', '400')")
    page.reload()
    assert page.inner_text("#level") == "Taso 5: Jättitrampoliini"
    assert page.inner_text("#stats").startswith("Ennätys 400 p")
