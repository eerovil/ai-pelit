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


def test_a_small_trampoline_slides_less_but_a_lean_still_counts(site, context):
    page = open_game(site, context, level=3)
    assert page.evaluate("T.name") == "Minitrampoliini"
    vx, _ = page.evaluate(LAND, [0.3, 5, 0])
    assert -0.5 < vx < -0.2
    # Over a whole bounce at full height that lean keeps you on the mini trampoline.
    drift = page.evaluate("() => -0.36 * airtime(T.vMax)")
    assert abs(drift) < page.evaluate("T.half + 0.15")


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
