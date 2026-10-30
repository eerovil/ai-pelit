"""Trampoliini v4: 🌀 makes half twists and, held down, keeps twisting until let go."""

import sys
from pathlib import Path

from conftest import ROOT

sys.path.insert(0, str(Path(__file__).parent))
from test_trampoliini import TRICK  # noqa: E402

URL = "games/trampoliini/v4/"
HOLD = "() => { window.__step = step; step = () => {}; }"
# v1's landing bot asks for each twist with one 🌀 tap; from v4 a tap is half a twist.
TRICK_V4 = TRICK.replace("for (let k = 1; k < tw; k++) twistTap();", "for (let k = 1; k < 2 * tw; k++) twistTap();")
# Straight jump at full height; 🌀 held from `start` s after take-off for `hold` s (pressed on
# the mat when start is None). Returns the landing and how far it had twisted at the let-go.
JUMP = """([start, hold]) => { const s = window.__step, face = J.face;
  stand(0); J.face = face; J.vin = T.vMax; lastLand = null;   // keep facing, as between bounces
  while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
  if (start === null) twistDown(); else J.pumpT = CONTACT / 2;
  while (phase === 'mat') s(1 / 60);
  let t = 0;
  if (start !== null) { while (t < start) { s(1 / 60); t += 1 / 60; } twistDown(); t = 0; }
  while (t < hold && phase === 'air') { s(1 / 60); t += 1 / 60; }
  twistUp();
  const atRelease = J.twist;
  while (phase === 'air') s(1 / 60);
  return [lastLand, atRelease]; }"""


def open_game(site, context, width=360, height=740, level=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.goto(site.url + URL)
    page.evaluate(f"localStorage.setItem('ai-pelit:trampoliini:taso', '{level}')")
    page.reload()
    page.click("#go")
    page.evaluate(HOLD)
    return page


def test_a_quick_tap_is_a_half_twist_and_you_land_facing_the_other_way(site, context):
    page = open_game(site, context)
    land, _ = page.evaluate(JUMP, [None, 0])
    assert land == {"trick": [0, 0.5], "clean": True}
    assert page.evaluate("[J.face, pops.some(p => p.text.startsWith('Puolikierrehyppy'))]") == [-1, True]
    # Another half twist turns you back round.
    page.evaluate(JUMP, [None, 0])
    assert page.evaluate("J.face") == 1


def test_holding_keeps_twisting_and_letting_go_stops_at_the_next_half(site, context):
    page = open_game(site, context)
    land, at_release = page.evaluate(JUMP, [None, 0.8])
    assert 1 < at_release < 1.5
    assert land == {"trick": [0, 1.5], "clean": True}
    assert page.evaluate("pops.some(p => p.text.startsWith('1½-kierrehyppy'))")
    land, _ = page.evaluate(JUMP, [None, 0.5])
    assert land["trick"] == [0, 1] and land["clean"]


def test_pressed_in_the_air_it_twists_from_there(site, context):
    page = open_game(site, context)
    land, at_release = page.evaluate(JUMP, [0.2, 0.2])
    assert 0.2 < at_release < 0.5
    assert land == {"trick": [0, 0.5], "clean": True}


def test_a_twist_still_under_way_at_the_landing_is_a_wobble_not_a_fall(site, context):
    page = open_game(site, context)
    land = page.evaluate("""() => { const s = window.__step;
      stand(0); J.vin = T.vMax; lastLand = null;
      while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
      twistDown();
      while (phase === 'mat') s(1 / 60);
      while (phase === 'air') s(1 / 60);      // never let go before the landing
      return [lastLand, hearts, phase]; }""")
    assert land[0]["clean"] is False and land[1:] == [3, "mat"]
    # Leaning too far is still a fall.
    fell = page.evaluate("""() => { const s = window.__step;
      stand(0); J.vin = 6; while (phase === 'mat') s(1 / 60);
      while (!(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
      J.a = 1.4; s(1 / 60); return [lastLand, hearts]; }""")
    assert fell == [{"crash": "kaatui"}, 2]


def test_facing_back_a_back_flip_still_drifts_and_slides_your_own_way_back(site, context):
    page = open_game(site, context, level=4)
    r = page.evaluate("""() => { const s = window.__step, out = [];
      for (const face of [1, -1]) {
        stand(0); J.face = face; J.vin = T.vMax;
        while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
        press(1); while (phase === 'mat') s(1 / 60);
        const drift = J.vx; release();
        while (!(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
        pops = []; J.vx = 0; J.x = 0; J.a = 2 * Math.PI + 0.4; J.rot = J.a; s(1 / 60);
        out.push([Math.sign(drift), Math.sign(J.vx), pops.map(p => p.text).filter(t => t.includes('Liukuu'))]);
      }
      return out; }""")
    assert r[0] == [-1, -1, ["← Liukuu taaksepäin"]]
    assert r[1] == [1, 1, ["Liukuu taaksepäin →"]]


def test_flip_and_twist_held_together_then_let_go_in_either_order(site, context):
    page = open_game(site, context, level=4)
    for twist_first in (True, False):
        land = page.evaluate("""(twistFirst) => { const s = window.__step;
          stand(0); J.vin = T.vMax; lastLand = null;
          while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
          press(1); twistDown();                          // both buttons down on the mat
          while (phase === 'mat') s(1 / 60);
          const letFlipGo = () => { while (phase === 'air' && Math.abs(J.rot) < 2 * Math.PI - 1.4) s(1 / 60); release(); };
          const letTwistGo = () => { while (phase === 'air' && J.twist < 0.8) s(1 / 60); twistUp(); };
          if (twistFirst) { letTwistGo(); letFlipGo(); } else { letFlipGo(); letTwistGo(); }
          while (phase === 'air') s(1 / 60);
          return lastLand; }""", twist_first)
        assert land == {"trick": [1, 1], "clean": True}, (twist_first, land)


def test_the_real_button_twists_while_pressed(site, context):
    page = open_game(site, context)
    page.evaluate("() => { const s = window.__step; stand(0); J.vin = T.vMax; while (phase === 'mat') s(1 / 60); for (let i = 0; i < 6; i++) s(1 / 60); }")
    btn = page.locator("#pad button[data-act=kierre]")
    btn.dispatch_event("pointerdown", {"pointerId": 3})
    page.evaluate("() => { for (let i = 0; i < 50; i++) window.__step(1 / 60); }")
    assert page.evaluate("[twistHeld, J.twist > 1, J.twists]") == [True, True, 1.5]
    btn.dispatch_event("pointerup", {"pointerId": 3})
    assert page.evaluate("twistHeld") is False


def test_every_trick_of_the_first_ten_levels_still_lands(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    for lv in range(1, 11):
        page.evaluate(f"level = {lv}; setup()")
        for n, tw in page.evaluate("L.tasks"):
            ok = any(
                (r := page.evaluate(TRICK_V4, [n, tw, 0.2 + i * 0.1])) and r.get("trick") == [n, tw] and r.get("clean")
                for i in range(25)
            )
            assert ok, (lv, n, tw)


def test_half_twist_names(site, context):
    page = open_game(site, context)
    names = page.evaluate("[[0, 0.5], [1, 0.5], [-1, 1.5], [0, 2.5], [0, 1], [2, 2]].map(trickName)")
    assert names == ["Puolikierrehyppy", "Puolikierrevoltti taakse", "1½-kierrevoltti eteen",
                     "2½-kierrehyppy", "Kierrehyppy", "Tuplakierretuplavoltti taakse"]


def test_the_menu_fits_small_phones(site, context):
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


def test_twist_pressed_in_the_last_moment_before_a_clean_landing_is_for_the_next_jump(site, context):
    page = open_game(site, context, level=1)
    r = page.evaluate("""() => { const s = window.__step;
      stand(0); J.vin = T.vMax; lastLand = null;
      while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
      press(1); while (phase === 'mat') s(1 / 60);
      while (phase === 'air' && Math.abs(J.rot) < 2 * Math.PI - 1.2) s(1 / 60);
      release();
      while (phase === 'air' && timeToMat() > 0.08) s(1 / 60);
      twistDown();                                   // within 0.12 s of the mat
      const queued = [J.queuedTwist, J.twists];
      while (phase === 'air') s(1 / 60);
      const landed = lastLand;
      twistUp(); while (phase === 'mat') s(1 / 60);
      return [queued, landed, J.twists]; }""")
    assert r[0] == [True, 0]
    assert r[1] == {"trick": [1, 0], "clean": True}   # the back flip keeps its full points
    assert r[2] == 0.5                                 # and the next jump twists


def test_twist_held_through_a_landing_keeps_twisting_on_the_next_jump(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const s = window.__step;
      stand(0); J.vin = T.vMax; lastLand = null;
      while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
      twistDown();                                   // one press, never let go
      while (phase === 'mat') s(1 / 60);
      while (phase === 'air') s(1 / 60);
      const first = lastLand;
      while (phase === 'mat') s(1 / 60);
      for (let i = 0; i < 30; i++) s(1 / 60);
      const second = [J.twist > 0.5, J.twists > J.twist];
      twistUp(); while (phase === 'air') s(1 / 60);
      return [first, second, lastLand]; }""")
    assert r[0]["clean"] is False and r[0]["trick"][1] >= 1
    assert r[1] == [True, True]
    assert r[2]["clean"] and r[2]["trick"][1] >= 1
