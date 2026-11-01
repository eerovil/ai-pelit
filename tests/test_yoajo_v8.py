"""Yöajo v8 (#306): the lights button on the left, a livelier gas pedal, a rest area with a lane
of its own and signs, side roads with cars pulling out, no overtaking through a junction, and
the unsafe-overtake rule within 130 m (v4–v7: 180 m)."""

from conftest import ROOT
from test_yoajo_v7 import BOT as BOT_V7, RUN

URL = "games/yoajo/v8/"

# v7's careful driver, which now also leaves a car waiting at a side road alone and never
# starts an overtake with a solid centre line within 250 m (once out, it goes on).
BOT = BOT_V7.replace(
    "const slow = things.find(t => t.v >= 0 &&",
    "const slow = things.find(t => t.v >= 0 && !(t.kind === 'liittyja' && t.plan === 'wait') &&", 1).replace(
    "if (slow && !onc && slow.kind !== 'kavelija') want = -LANE;",
    "if (slow && !onc && slow.kind !== 'kavelija' && (P.lat < 0.5 || ![0, 50, 100, 150, 200, 250].some(k => noPass(P.s + k)))) want = -LANE;", 1)
assert BOT.count("liittyja") == 1 and BOT.count("noPass") == 1


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"]) for r in legs]
    assert all(r["tally"]["hurjastelu"] == 0 for r in legs), legs
    # The careful driver stops for coffee on every leg with a rest area.
    assert all(r["tally"]["tauko"] == 1 for r in legs if r["n"] >= 3), legs
    assert page.errors == []


def test_the_lights_button_is_in_the_lower_left_corner(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; newLeg(1); btns = []; draw();
      const b = btns.find(b => b.id === 'lights'); return { b, W, H }; }""")
    b = r["b"]
    assert b["x"] < 30 and b["y"] + b["h"] > r["H"] - 30, r
    # Two thumbs keep it between them, as before.
    r = page.evaluate("""() => { setControls('kaksi'); btns = []; draw();
      const b = btns.find(b => b.id === 'lights'); setControls('yksi'); return { mid: b.x + b.w / 2, W }; }""")
    assert abs(r["mid"] - r["W"] / 2) < 1, r
    assert page.errors == []


def test_full_gas_reaches_100_in_about_7_s_and_a_light_press_still_cruises_under_100(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(1); things = []; events = []; road.cams = [];
      P.v = 0; let t100 = 0; input.gas = 1;
      for (let i = 0; i < 60 * 12 && mode === 'drive'; i++) { P.lat = LANE; P.vl = 0; step(1 / 60); if (!t100 && P.v * KMH >= 100) t100 = (i + 1) / 60; }
      newLeg(1); things = []; events = []; road.cams = []; P.v = 0; input.gas = 0.35;
      for (let i = 0; i < 60 * 60 && mode === 'drive'; i++) { P.lat = LANE; P.vl = 0; step(1 / 60); }
      return { t100, cruise: P.v * KMH, mode }; }""")
    assert 5 < r["t100"] < 8.5, r
    assert 85 < r["cruise"] < 98, r
    assert page.errors == []


def test_the_rest_area_has_a_lane_signs_and_a_kerb(site, context):
    page = open_game(site, context)
    for n in range(3, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu'; const b = road.bays[0];
          const signs = road.signs.filter(s => s.kind === 'levahdys' || s.kind === 'pnuoli').map(s => [Math.round(b.s0 - s.s), s.kind, s.text || '']);
          return { signs, w: [bayWidth(b.s0 - BAY_IN - 1), bayWidth(b.s0 - BAY_IN / 2), bayWidth(b.s0 + 10), bayWidth(b.s1 + BAY_IN / 2), bayWidth(b.s1 + BAY_IN + 1)] }; }""", n)
        kinds = sorted(k for _, k, _ in r["signs"])
        assert kinds == ["levahdys", "levahdys", "pnuoli"], (n, r)
        assert [100, "levahdys", "100 m"] in r["signs"] and [500, "levahdys", "500 m"] in r["signs"], (n, r)
        assert r["w"] == [0, 4, 8, 4, 0], (n, r)
    # Driving out of the parking place along the narrowing lane leads back onto the road, no ditch.
    r = page.evaluate("""() => { HOLD = true; newLeg(3); things = []; events = []; road.cams = []; const b = road.bays[0];
      P.s = b.s1 - 10; P.lat = 11; P.v = 10;
      for (let i = 0; i < 60 * 8 && mode === 'drive'; i++) { P.v = 10; step(1 / 60); }
      return { mode, lat: P.lat, past: P.s > b.s1 + BAY_IN }; }""")
    assert r["mode"] == "drive" and r["past"] and r["lat"] < 5.6, r
    assert page.errors == []


def test_every_leg_has_junctions_with_a_sign_and_a_solid_centre_line(site, context):
    page = open_game(site, context)
    for n in range(1, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu';
          return { n: road.junctions.length, want: leg.junctions,
            ok: road.junctions.every(J => J.s % 4 === 0 && noPass(J.s - 100) && noPass(J.s + 20) && !noPass(J.s + 40)
              && road.signs.some(s => s.kind === 'risteys' && J.s - s.s > 120 && J.s - s.s < 160)
              && road.signs.some(s => s.kind === 'ohituskielto' && s.s === J.s - NOPASS_BEFORE)),
            cars: events.filter(e => e.kind === 'liittyja').length }; }""", n)
        assert r["n"] == r["want"] and r["ok"] and r["cars"] >= 1, (n, r)
    assert page.errors == []


def test_a_careless_car_pulls_out_ahead_with_room_to_brake_and_drives_on(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(1); things = []; events = []; road.cams = [];
      const J = { s: Math.round((P.s + 300) / 4) * 4, side: 1 };
      road.junctions = [J];
      const t = release({ kind: 'liittyja', j: J, side: 1, dir: 'same', careless: true, r: 0.3 });
      let gap = null, seen = [];
      for (let i = 0; i < 60 * 12 && mode === 'drive'; i++) { P.v = 90 / KMH; P.lat = LANE; P.vl = 0;
        if (t.plan === 'turn' && gap === null) gap = t.s - P.s;
        if (t.kind === 'auto' && t.s - P.s < 30) input.brake = 1; else input.brake = 0;
        if (t.kind === 'auto' && t.s - P.s < 25) P.v = Math.min(P.v, t.v);
        step(1 / 60); for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
      return { gap, kind: t.kind, lat: t.lat, v: t.v * KMH, mode, why: crashWhy, seen }; }""")
    assert r["gap"] is not None and 60 <= r["gap"] < 100, r
    assert r["kind"] == "auto" and abs(r["lat"] - 1.75) < 0.01 and r["v"] > 20, r
    assert "Auto risteyksestä!" in r["seen"], r
    # A careful one waits until the player is far: it pulls out at seven seconds at least.
    r = page.evaluate("""() => { newLeg(1); things = []; events = []; road.cams = [];
      const J = { s: Math.round((P.s + 400) / 4) * 4, side: -1 };
      const t = release({ kind: 'liittyja', j: J, side: -1, dir: 'same', careless: false, r: 0.3 });
      let gap = null;
      for (let i = 0; i < 60 * 12 && mode === 'drive'; i++) { P.v = 90 / KMH; P.lat = LANE; P.vl = 0;
        if (t.plan === 'turn' && gap === null) gap = t.s - P.s; step(1 / 60); }
      return { gap }; }""")
    assert r["gap"] is not None and r["gap"] >= 120, r
    assert page.errors == []


def test_crossing_the_solid_line_costs_30_once_and_counts_as_reckless(site, context):
    page = open_game(site, context)
    setup = "road.nopass = [{ s0: P.s + 5, s1: P.s + 200 }];"
    r = page.evaluate(RUN.replace("P.lat = LANE;", "P.lat = -LANE;"), [1, setup, 80, 3])
    assert r["tally"]["hurjastelu"] == 1 and r["points"] == -30, r
    assert "Ohitit sulkuviivan yli -30" in r["seen"], r
    # Outside the zone the oncoming lane is free to use.
    r = page.evaluate(RUN.replace("P.lat = LANE;", "P.lat = -LANE;"), [1, "road.nopass = [];", 80, 3])
    assert r["tally"]["hurjastelu"] == 0, r
    assert page.errors == []


def test_an_oncoming_car_150_m_away_is_not_unsafe_but_100_m_is(site, context):
    page = open_game(site, context)
    out = []
    for gap in (150, 100):
        r = page.evaluate("""(gap) => { HOLD = true; maxLeg = 8; newLeg(1); things = []; events = []; road.cams = []; road.nopass = [];
          P.lat = -LANE; P.v = 80 / KMH; add('vastaan', { s: P.s + gap, lat: 4.5, v: -20 }); step(1 / 60);
          return tally.hurjastelu; }""", gap)
        out.append(r)
    assert out == [0, 1], out
    assert page.errors == []


def test_every_leg_builds_its_world_in_3d(site, context):
    page = open_game(site, context)
    page.wait_for_function("V3 && V3.scene || no3d", timeout=15000)
    r = page.evaluate("""() => { const out = []; maxLeg = 8;
      for (let n = 1; n <= 8; n++) { newLeg(n); mode = 'menu'; buildWorld(); draw3d(); out.push(V3.signs.length); }
      return out; }""")
    assert all(n > 5 for n in r), r
    assert page.errors == []


def test_an_oncoming_truck_in_snow_brings_a_haze_not_a_white_flash(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(5); things = []; events = []; road.cams = []; road.nopass = [];
      add('vastaan', { s: P.s + 40, lat: -LANE, v: -20, truck: true, len: 17, wid: 2.55, habit: 0 });
      const seen = [];
      for (let i = 0; i < 60 * 4 && mode === 'drive'; i++) { P.v = 60 / KMH; P.lat = LANE; P.vl = 0; step(1 / 60); seen.push(whiteout); }
      const first = seen.findIndex(w => w > 0);
      return { first, max: Math.max(...seen), jump: Math.max(...seen.slice(1).map((w, i) => w - seen[i])), end: seen[seen.length - 1] }; }""")
    assert r["first"] >= 0 and r["max"] <= 0.5 and r["jump"] < 0.05 and r["end"] == 0, r
    assert page.errors == []
