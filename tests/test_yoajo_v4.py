"""Yöajo v4 (#181): one thumb as a round stick, fairer high beams, penalties for reckless
driving, fewer limit changes, traffic that keeps to the limits."""

import pytest

from conftest import ROOT, turn
from test_yoajo import BOT as BOT_V1

URL = "games/yoajo/v4/"
# v1's careful driver, on full gas unless it brakes.
BOT = BOT_V1.replace("      step(1 / 60);", "      input.gas = input.brake ? 0 : 1; step(1 / 60);", 1)


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def run(page, setup, secs, each=""):
    """Leg 1 (or setup's), clock held, the car kept in its lane by hand unless setup says."""
    return page.evaluate(f"""() => {{ HOLD = true; maxLeg = 8; newLeg(1); things = []; events = []; road.cams = [];
      const seen = []; {setup};
      for (let i = 0; i < 60 * {secs} && mode === 'drive'; i++) {{ {each}; step(1 / 60);
        for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }}
      return {{ mode, points, tally: Object.assign({{}}, tally), seen }}; }}""")


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"]) for r in legs]
    # The careful driver keeps to the limits and overtakes only when nobody comes.
    assert all(r["tally"]["hurjastelu"] == 0 for r in legs), legs
    assert page.errors == []


def thumb(cdp, kind, points):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})


def test_one_thumb_steers_gives_gas_and_brakes(site, context):
    page = open_game(site, context)
    page.evaluate("newLeg(1); HOLD = true")
    assert page.evaluate("controls") == "yksi"
    cdp = page.context.new_cdp_session(page)
    p = {"x": 150, "y": 600, "id": 1}
    thumb(cdp, "touchStart", [p])
    page.wait_for_function("thumbs.size === 1")
    assert page.evaluate("[input.steer, input.gas, input.brake]") == [0, 0.35, 0]
    # Half way right is a gentle turn; up and right at once steers and gives more gas.
    thumb(cdp, "touchMove", [dict(p, x=178)])
    page.wait_for_function("input.steer > 0")
    assert 0.3 < page.evaluate("input.steer") < 0.45
    thumb(cdp, "touchMove", [dict(p, x=180, y=570)])
    page.wait_for_function("input.gas > 0.6")
    assert page.evaluate("input.steer") > 0.4
    # The knob stays inside the circle: a long slide is a full turn, not more.
    thumb(cdp, "touchMove", [dict(p, x=400)])
    page.wait_for_function("input.steer === 1")
    # Down brakes.
    thumb(cdp, "touchMove", [dict(p, y=680)])
    page.wait_for_function("input.brake > 0.5 && input.gas === 0")
    thumb(cdp, "touchEnd", [])
    page.wait_for_function("thumbs.size === 0")
    assert page.evaluate("[input.steer, input.gas, input.brake]") == [0, 0, 0]
    assert page.errors == []


def test_the_menu_switches_to_two_thumbs_and_remembers(site, context):
    page = open_game(site, context)
    b = page.evaluate("(() => { draw(); const b = btns.find(b => b.id === 'ohjaus'); return [b.x + b.w / 2, b.y + b.h / 2]; })()")
    page.touchscreen.tap(*b)
    assert page.evaluate("controls") == "kaksi"
    page.reload()
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    assert page.evaluate("[controls, localStorage.getItem('ai-pelit:yoajo:ohjaus')]") == ["kaksi", '"kaksi"']
    # Two thumbs: the left half steers, the right half is the gas, as in v3.
    page.evaluate("newLeg(1); HOLD = true")
    cdp = page.context.new_cdp_session(page)
    thumb(cdp, "touchStart", [{"x": 80, "y": 560, "id": 1}, {"x": 280, "y": 560, "id": 2}])
    page.wait_for_function("thumbs.size === 2")
    assert sorted(page.evaluate("[...thumbs.values()].map(t => t.kind)")) == ["gas", "steer"]
    thumb(cdp, "touchEnd", [])


def test_the_lights_button_is_not_a_thumb(site, context):
    page = open_game(site, context)
    page.evaluate("newLeg(1); HOLD = true")
    b = page.evaluate("(() => { draw(); const b = btns.find(b => b.id === 'lights'); return [b.x + b.w / 2, b.y + b.h / 2]; })()")
    page.touchscreen.tap(*b)
    assert page.evaluate("[P.high, thumbs.size]") == [True, 0]


def test_dazzling_is_judged_at_90_m(site, context):
    page = open_game(site, context)
    # High beams kept on until the oncoming car is 100 m away, then dipped: no penalty.
    keep = "P.lat = LANE; P.vl = 0; P.v = 20; const o = things.find(t => t.kind === 'vastaan'); if (o && o.s - P.s < 100) P.high = false"
    r = run(page, "P.high = true; add('vastaan', { s: P.s + 400, lat: -LANE, habit: 0 }); things[0].v = -25", 10, keep)
    assert r["tally"]["haikaisyt"] == 0, r
    # Kept on past 90 m: dazzled.
    r = run(page, "P.high = true; add('vastaan', { s: P.s + 400, lat: -LANE, habit: 0 }); things[0].v = -25", 10, "P.lat = LANE; P.vl = 0; P.v = 20")
    assert r["tally"]["haikaisyt"] == 1, r
    # A car ahead: 60 m away is fine; within 50 m for 2.5 s dazzles it.
    r = run(page, "P.high = true; add('auto', { s: P.s + 60, v: 20 })", 4, "P.lat = LANE; P.vl = 0; P.v = 20; things[0].v = 20")
    assert r["tally"]["haikaisyt"] == 0, r
    r = run(page, "P.high = true; add('auto', { s: P.s + 40, v: 20 })", 4, "P.lat = LANE; P.vl = 0; P.v = 20; things[0].v = 20")
    assert r["tally"]["haikaisyt"] == 1, r


def test_high_beams_earn_points_but_not_under_street_lights(site, context):
    page = open_game(site, context)
    hold = "P.lat = LANE; P.vl = 0; P.v = 25"
    r = run(page, "P.high = true", 21, hold)
    assert r["tally"]["pitkatP"] == 25 and r["points"] == 25, r
    assert "Pitkillä 0,5 km +25" in r["seen"]
    # In the town at the end the street lights are on: nothing.
    r = run(page, "P.high = true; P.s = leg.len - 290", 5, hold)
    assert r["tally"]["pitkatP"] == 0, r
    # In a village (a 60 stretch, from leg 5) too.
    v = page.evaluate("""() => { HOLD = true; newLeg(6); things = []; events = []; const l = road.limits.find(l => l.v === 60);
      P.s = l.s + 5; P.high = true; tally.pitkatP = 0;
      for (let i = 0; i < 60 * 5; i++) { P.lat = LANE; P.vl = 0; P.v = 16; step(1 / 60); }
      return [limitAt(P.s), tally.pitkatP]; }""")
    assert v == [60, 0]


def test_low_beams_on_an_empty_road_bring_a_reminder(site, context):
    page = open_game(site, context)
    hold = "P.lat = LANE; P.vl = 0; P.v = 25"
    assert "Tie on tyhjä: pitkät päälle!" in run(page, "", 7, hold)["seen"]
    # Not while a car is coming.
    r = run(page, "add('vastaan', { s: P.s + 500, lat: -LANE, habit: 0 })", 7, hold + "; things[0].v = -1")
    assert "Tie on tyhjä: pitkät päälle!" not in r["seen"]


def test_speeding_20_over_costs_points(site, context):
    page = open_game(site, context)
    lim = page.evaluate("newLeg(1); limitAt(10)")
    r = run(page, "", 1.5, f"P.lat = LANE; P.vl = 0; P.v = ({lim} + 19) / KMH")
    assert r["tally"]["hurjastelu"] == 0, r
    # 1 s in, and 5 s later again.
    r = run(page, "", 6.5, f"P.lat = LANE; P.vl = 0; P.v = ({lim} + 25) / KMH")
    assert r["tally"]["hurjastelu"] == 2 and r["points"] == -50, r
    assert f"Hurjastelu: {lim + 25} km/h -25" in r["seen"]


def test_an_unsafe_overtake_costs_and_earns_nothing(site, context):
    page = open_game(site, context)
    out = "P.lat = -LANE; P.vl = 0; P.v = 25"
    r = run(page, "add('traktori', { s: P.s + 12, lat: 2.4, v: 7 })", 1.5, out + "; things[0].v = 7")
    assert r["points"] == 40 and r["tally"]["ohitukset"] == 1, r
    r = run(page, "add('traktori', { s: P.s + 12, lat: 2.4, v: 7 }); add('vastaan', { s: P.s + 170, lat: -LANE, habit: 0 })", 1.5,
            out + "; things[0].v = 7; things[1].v = -25")
    assert r["points"] == -50 and r["tally"]["ohitukset"] == 0 and r["tally"]["hurjastelu"] == 1, r
    assert "Vaarallinen ohitus -50" in r["seen"]
    # The third star needs a leg with no reckless driving.
    stars = page.evaluate("() => { HOLD = true; newLeg(1); things = []; events = []; tally.hurjastelu = 1; P.s = leg.len - 0.1; P.v = 25; T = 50; step(1 / 60); return result.stars; }")
    assert stars == 2


def test_limits_change_seldom_and_60_comes_late(site, context):
    page = open_game(site, context)
    legs = page.evaluate("() => { maxLeg = 8; const out = []; for (let n = 1; n <= 8; n++) { newLeg(n); out.push(road.limits.map(l => l.v)); } return out; }")
    for n, lims in enumerate(legs, 1):
        # The start, at most two stretches with another limit (in and out), and 50 into the town.
        assert lims[0] in (80, 100) and lims[-1] == 50 and len(lims) <= 6, (n, lims)
        assert (60 in lims) == (n >= 5 and 60 in lims), (n, lims)
        if n < 5:
            assert 60 not in lims, (n, lims)
    assert any(60 in lims for lims in legs[4:])


def test_traffic_keeps_to_the_limits(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; newLeg(1); things = []; events = [];
      road.limits = [{ s: 0, v: 100 }, { s: P.s + 200, v: 80 }];
      const car = add('auto', { s: P.s + 100, habit: 0 }); cruiseFrom(car);
      const truck = add('rekka', { s: P.s + 60, lat: 1.8, habit: 3 }); cruiseFrom(truck);
      const before = [car.v * KMH, truck.v * KMH];
      for (let i = 0; i < 60 * 20; i++) { P.lat = LANE; P.vl = 0; P.s = truck.s - 120; P.v = truck.v; step(1 / 60); }
      return { before, after: [car.v * KMH, truck.v * KMH] }; }""")
    # At the limit (100), the truck at its own 80 + 3; past the 80 sign both slow to it.
    assert r["before"][0] == pytest.approx(100, abs=0.5) and r["before"][1] == pytest.approx(83, abs=0.5), r
    assert r["after"][0] == pytest.approx(80, abs=0.5) and r["after"][1] == pytest.approx(83, abs=0.5), r


def test_the_reckless_driver_never_hits_the_player_out_overtaking(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; newLeg(1); things = []; events = [];
      const t = add('takaa', { s: P.s - 60, v: 44, high: true, plan: 'pass', lat: -LANE });
      for (let i = 0; i < 60 * 4 && mode === 'drive'; i++) { P.lat = -LANE; P.vl = 0; P.v = 8; step(1 / 60); }
      return { mode, gap: P.s - t.s }; }""")
    assert r["mode"] == "drive" and r["gap"] > 4, r


@pytest.mark.parametrize("size", [{"width": 360, "height": 640}, {"width": 390, "height": 844}, {"width": 740, "height": 360}])
def test_everything_fits_on_the_screen(site, context, size):
    page = open_game(site, context)
    turn(page, size)
    page.wait_for_function(f"W === {size['width']} && H === {size['height']}")
    # The longest end screen: a leg with a coffee stop and every row.
    for setup in ["preview(1)", "newLeg(1)", "newLeg(4); things = []; events = []; tally.hurjastelu = 1; P.s = leg.len; step(1 / 60)", "newLeg(1); crash('Kolari!')"]:
        boxes = page.evaluate(f"() => {{ HOLD = true; maxLeg = 8; {setup}; draw(); return btns.map(b => [b.id, b.x, b.y, b.w, b.h]); }}")
        for id_, bx, by, bw, bh in boxes:
            assert bx >= 0 and by >= 0 and bx + bw <= size["width"] + 0.5 and by + bh <= size["height"] + 0.5, (setup, id_)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1] or a[2] + a[4] <= b[2] or b[2] + b[4] <= a[2], (setup, a, b)
    assert page.errors == []


def test_saves_from_v3_carry_on(site, context):
    context.add_init_script("""if (!sessionStorage.seeded) { sessionStorage.seeded = 1;
      localStorage.setItem('ai-pelit:yoajo:taso', '5'); localStorage.setItem('ai-pelit:yoajo:ajettu', '4');
      localStorage.setItem('ai-pelit:yoajo:pisteet', '{"4":310}'); }""")
    page = open_game(site, context)
    assert page.evaluate("[maxLeg, driven, bests[4], level, controls]") == [5, 4, 310, 5, "yksi"]
