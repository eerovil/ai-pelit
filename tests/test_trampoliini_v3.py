"""Trampoliini v3: the landing decides the sideways movement."""

import sys
from pathlib import Path

from conftest import ROOT

sys.path.insert(0, str(Path(__file__).parent))
from test_trampoliini import TRICK  # noqa: E402

URL = "games/trampoliini/v3/"
HOLD = "() => { window.__step = step; step = () => {}; }"
# Lands with the given tilt (radians, > 0 leaning back) from a bounce of speed vin; returns vx.
LAND = """([tilt, vin, x0]) => { const s = window.__step;
  stand(x0); J.vin = vin; while (phase === 'mat') s(1 / 60);
  J.vx = 0; while (!(J.vy < 0 && J.y < COMH + 0.05)) s(1 / 60);
  J.a = tilt; J.rot = tilt; s(1 / 60); return [J.vx, phase]; }"""


def open_game(site, context, level=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate(f"localStorage.setItem('ai-pelit:trampoliini:taso', '{level}')")
    page.reload()
    page.click("#go")
    page.evaluate(HOLD)
    return page


def test_landing_leaning_back_slides_back_forward_slides_forward_straight_stays(site, context):
    page = open_game(site, context)
    back, phase = page.evaluate(LAND, [0.4, 6, 0])
    fwd, _ = page.evaluate(LAND, [-0.4, 6, 0])
    straight, _ = page.evaluate(LAND, [0, 6, 0])
    assert phase == "mat" and back < -1 and fwd > 1 and straight == 0
    assert abs(back + fwd) < 1e-9


def test_the_mat_still_pulls_a_little_towards_the_middle(site, context):
    page = open_game(site, context)
    vx, _ = page.evaluate(LAND, [0, 6, 1.5])
    assert -0.6 < vx < 0


def test_the_steepest_clean_lean_at_full_height_takes_several_landings_to_reach_the_edge(site, context):
    page = open_game(site, context)
    for tramp in ("pieni", "mini", "kilpa", "jatti"):
        # Bounce at full height, pushing at the bottom each time, and land every time leaning back
        # 0.49 rad (still clean), through the real air() and land(). Where is each landing?
        r = page.evaluate("""(name) => { const s = window.__step;
          T = TRAMPS[name]; hearts = 9; stand(0); J.vin = T.vMax;
          const xs = [];
          for (let k = 0; k < 6; k++) {
            while (phase === 'mat') { if (J.pumpT === null && J.matT >= CONTACT / 2) J.pumpT = CONTACT / 2; s(1 / 60); }
            while (phase === 'air' && !J.off && !(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
            if (J.off || phase !== 'air') break;
            J.a = 0.49; J.rot = 0.49; s(1 / 60);
            if (phase !== 'mat' || !lastLand.clean) break;
            xs.push(J.x);
          }
          return { name, xs, half: T.half, top: J.vin >= T.vMax - 0.01 }; }""", tramp)
        assert len(r["xs"]) >= 3, r                       # on the mat for at least three landings
        assert abs(r["xs"][1]) > 0.15 * r["half"], r     # but the lean does move you


def test_every_trick_of_the_first_ten_levels_still_lands(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    for lv in range(1, 11):
        page.evaluate(f"level = {lv}; setup()")
        for n, tw in page.evaluate("L.tasks"):
            ok = any(
                (r := page.evaluate(TRICK, [n, tw, 0.2 + i * 0.1])) and r.get("trick") == [n, tw] and r.get("clean")
                for i in range(25)
            )
            assert ok, f"level {lv}: {n} turns, {tw} twists"


def test_v3_plays_on_with_the_saved_level_and_record(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:trampoliini:taso', '4'); localStorage.setItem('ai-pelit:trampoliini:ennatys', '300')")
    page.reload()
    assert page.inner_text("#level") == "Taso 4: Kilpatrampoliini"
    assert page.inner_text("#stats").startswith("Ennätys 300 p")


def test_two_leaning_landings_in_a_row_add_up_and_one_the_other_way_brings_you_back(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const s = window.__step, land = tilt => {
        while (phase === 'mat') s(1 / 60);
        while (!(J.vy < 0 && J.y < COMH + 0.05)) s(1 / 60);
        J.a = tilt; J.rot = tilt; s(1 / 60); return J.vx; };
      stand(0); J.vin = 6;
      const one = land(0.4), two = land(0.4), back = land(-0.4);
      return [one, two, back, J.x, phase]; }""")
    one, two, back, x, phase = r
    assert two < one < 0 and back > two and phase == "mat"
    assert x < 0     # walked backwards


def test_a_wobbly_landing_slides_by_its_lean_not_by_where_you_stand(site, context):
    page = open_game(site, context)
    vx, phase = page.evaluate(LAND, [-0.8, 6, -1])   # wobble, leaning forward, standing back of the middle
    assert phase == "mat" and vx > 1.5


def test_the_slide_labels_fit_a_390_and_a_360_px_phone(site, context):
    site.build(ROOT / "games")
    for width in (360, 390):
        page = context.new_page()
        page.set_viewport_size({"width": width, "height": 740})
        page.goto(site.url + URL)
        widths = page.evaluate("""() => { x.font = '800 16px system-ui,sans-serif';
          return ['← Liukuu taaksepäin', 'Liukuu eteenpäin →'].map(t => x.measureText(t).width); }""")
        assert max(widths) < width - 24
        page.close()


def test_every_trampoline_says_when_a_lean_slides_you_and_which_way(site, context):
    page = open_game(site, context)
    for tramp in ("piha", "pieni", "mini", "kilpa", "jatti"):
        said = page.evaluate("""(name) => { const s = window.__step, out = [];
          for (const tilt of [0.4, -0.4, 0.1]) {
            T = TRAMPS[name]; stand(0); J.vin = 6; while (phase === 'mat') s(1 / 60);
            while (!(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
            pops = []; J.a = tilt; J.rot = tilt; s(1 / 60);
            out.push([pops.map(p => p.text).filter(t => t.includes('Liukuu')), Math.sign(J.vx)]);
          }
          return out; }""", tramp)
        assert said[0] == [["← Liukuu taaksepäin"], -1], (tramp, said)
        assert said[1] == [["Liukuu eteenpäin →"], 1], (tramp, said)
        assert said[2][0] == [], (tramp, said)   # a slight lean slides a little, unannounced


def test_back_flips_started_from_the_mat_and_landed_leaning_take_several_landings_to_go_off(site, context):
    page = open_game(site, context)
    for tramp in ("pieni", "mini", "kilpa", "jatti"):
        # As a player would: push at the bottom, press ↺ Taakse on the mat (it starts the flip
        # with its drift), let go late in the turn, and land every time 0.49 rad past upright.
        r = page.evaluate("""(name) => { const s = window.__step;
          T = TRAMPS[name]; hearts = 9; stand(0); J.vin = T.vMax;
          const xs = [];
          for (let k = 0; k < 6; k++) {
            while (phase === 'mat' && J.matT < CONTACT / 2) s(1 / 60);
            if (phase !== 'mat') break;
            press(1);                                   // the real button path: pump and flip
            while (phase === 'mat') s(1 / 60);
            while (phase === 'air' && Math.abs(J.rot) < 2 * Math.PI - 1.2) s(1 / 60);
            release();
            while (phase === 'air' && !J.off && !(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
            if (J.off || phase !== 'air') break;
            J.a = 2 * Math.PI + 0.49; J.rot = J.a; s(1 / 60);
            if (phase !== 'mat' || !lastLand.clean) break;
            xs.push(J.x);
          }
          return { name, xs, off: J.off, half: T.half }; }""", tramp)
        assert len(r["xs"]) >= 3, r
        assert abs(r["xs"][0]) > 0.1 * r["half"], r


def test_off_the_middle_the_slide_label_only_says_the_way_you_really_go(site, context):
    page = open_game(site, context, level=4)
    assert page.evaluate("T.name") == "Kilpatrampoliini"
    seen = page.evaluate("""() => { const s = window.__step, out = [];
      for (const x0 of [-2.25, -1, 0, 1, 2.25]) for (const tilt of [0.26, -0.26, 0.45, -0.45]) {
        stand(x0); J.vin = 6; while (phase === 'mat') s(1 / 60);
        J.vx = 0; J.x = x0;
        while (!(J.vy < 0 && J.y + J.vy / 60 <= COMH)) s(1 / 60);
        J.x = x0; pops = []; J.a = tilt; J.rot = tilt; s(1 / 60);
        const said = pops.map(p => p.text).filter(t => t.includes('Liukuu'));
        out.push([x0, tilt, said, J.vx]);
      }
      return out; }""")
    for x0, tilt, said, vx in seen:
        if said == ["← Liukuu taaksepäin"]:
            assert vx < 0, (x0, tilt, vx)
        elif said == ["Liukuu eteenpäin →"]:
            assert vx > 0, (x0, tilt, vx)
        else:
            assert said == [], (x0, tilt, said)
    # In the middle the lean always shows.
    assert all(said for x0, tilt, said, vx in seen if x0 == 0)
    # At the back edge leaning back, the mat's pull wins: no "taaksepäin".
    assert ["← Liukuu taaksepäin"] not in [said for x0, tilt, said, vx in seen if x0 == -2.25 and tilt == 0.26]
