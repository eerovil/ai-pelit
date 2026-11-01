"""Yöajo v8 (#306): the lights button on the left, a livelier gas pedal, a rest area with a lane
of its own and signs, side roads with cars pulling out, no overtaking through a junction, and
the unsafe-overtake rule within 130 m (v4–v7: 180 m)."""

from conftest import ROOT, turn

URL = "games/yoajo/v9/"

# A careful driver: keeps to the lane, overtakes only when nobody is coming and never starts an
# overtake with a solid centre line within 250 m (once out, it goes on), dips the high beams for
# oncoming cars and cars ahead, slows for moose and the speed limits (at most 90 on snow), gets
# out of the way of an oncoming overtaker, leaves a car waiting at a side road alone, and stops
# for coffee when sleepy, waiting behind a slow car before it turns into the rest area.
BOT = """(legs) => { maxLeg = 8; const out = [];
  for (const n of legs) { newLeg(n); HOLD = true;
    for (let i = 0; i < 60 * 400 && mode === 'drive'; i++) {
      let want = LANE;
      const slow = things.find(t => t.v >= 0 && !(t.kind === 'liittyja' && t.plan === 'wait') && t.lat > -1 && t.s > P.s - 3 && t.s - P.s < 50 && t.kind !== 'takaa' && t.kind !== 'hirvi' && t.kind !== 'poro');
      const onc = things.some(t => t.v < 0 && t.s > P.s - 5 && t.s - P.s < 330 && vehicle(t));
      const head = things.find(t => t.v < 0 && t.lat > 0.5 && t.s > P.s && t.s - P.s < 260);
      if (slow && !onc && slow.kind !== 'kavelija' && (P.lat < 0.5 || ![0, 50, 100, 150, 200, 250].some(k => noPass(P.s + k)))) want = -LANE;
      if (slow && slow.kind === 'kavelija' && !onc) want = slow.lat > 0 ? 0 : LANE;
      const beside = things.find(t => t.v >= 0 && vehicle(t) && t.kind !== 'takaa' && t.lat > 0 && t.s - P.s > -7 && t.s - P.s < 7);
      if (beside && P.lat < 0.5) want = -LANE;
      if (head) want = 4.0;
      const deer = things.find(t => (t.kind === 'hirvi' || t.kind === 'poro') && t.s > P.s && t.s - P.s < 120 && Math.abs(t.lat) < 6);
      const bay = road.bays.find(b => P.s > b.s0 - 5 && P.s < b.s1 - 10);
      const rest = bay && P.tired > 0.15;
      if (rest && !(slow && slow.lat > 0 && slow.s - P.s < 25)) want = 7;
      const err = P.lat - want + (P.vl - curveAt(P.s) * P.v * P.v * 0.55) * 0.35;
      input.left = err > 0.15; input.right = err < -0.15;
      const lim = Math.min(limitAt(P.s + 40), limitAt(P.s), (leg.weather === 'lumi' || leg.weather === 'pyry') ? 90 : 200);
      input.brake = P.v * 3.6 > lim + 3 || (deer && P.v > 4) || (rest && P.v > 2) || (head && P.v > 12)
        || (slow && want === LANE && slow.kind !== 'kavelija' && P.v > slow.v - 0.5 && slow.s - P.s < 35);
      P.high = !things.some(t => t.v < 0 && vehicle(t) && t.s > P.s && t.s - P.s < 320) && !things.some(t => t.v > 0 && vehicle(t) && t.s > P.s && t.s - P.s < 70);
      input.gas = input.brake ? 0 : 1; step(1 / 60);
    }
    out.push({ n, mode, why: crashWhy, T, par: parTime(), points, tally: Object.assign({}, tally), stars: result && result.stars });
  }
  return out; }"""

# Leg n with nobody else on the road, the clock held, the car kept in its lane at kmh.
RUN = """([n, setup, kmh, secs]) => { HOLD = true; maxLeg = 8; newLeg(n); things = []; events = []; road.cams = [];
  const seen = []; eval(setup);
  for (let i = 0; i < 60 * secs && mode === 'drive'; i++) { P.v = kmh / KMH; P.lat = LANE; P.vl = 0; step(1 / 60);
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
  return { mode, why: crashWhy, points, damage: P.damage, tally: Object.assign({}, tally), seen }; }"""


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


def test_sideways_and_on_a_390_phone_the_lights_and_the_stick_stay_apart(site, context):
    page = open_game(site, context)
    page.evaluate("HOLD = true; newLeg(1)")
    for size in ({"width": 740, "height": 360}, {"width": 390, "height": 844}, {"width": 360, "height": 640}):
        turn(page, size)
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { resize(); btns = []; draw(); const b = btns.find(b => b.id === 'lights'), h = stickHome();
          return { b, h, R: STICK, W, H }; }""")
        b, h, R = r["b"], r["h"], r["R"]
        assert h["x"] - R > b["x"] + b["w"], (size, r)
        assert b["x"] >= 0 and b["y"] + b["h"] <= r["H"], (size, r)
    assert page.errors == []


def test_a_retry_brings_back_the_same_junctions_a_fresh_waiting_car_and_no_haze(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(5);
      const before = JSON.stringify(road.junctions), cars = events.filter(e => e.kind === 'liittyja').length;
      const J = road.junctions[0]; P.s = J.s - 60; P.v = 0; events = events.filter(e => e.kind === 'liittyja' && e.j === J);
      for (let i = 0; i < 30; i++) step(1 / 60);
      const t = things.find(t => t.kind === 'liittyja'); if (t) t.plan = 'turn';
      cloudIn = 0.25; step(1 / 60); crash('Kolari toisen auton kanssa.'); act({ id: 'uudelleen' });
      return { same: JSON.stringify(road.junctions) === before, cars: events.filter(e => e.kind === 'liittyja').length, want: cars,
        things: things.length, whiteout, cloudIn, mode }; }""")
    assert r["same"] and r["cars"] == r["want"] and r["things"] == 0, r
    assert r["whiteout"] == 0 and r["cloudIn"] == 0 and r["mode"] == "drive", r
    assert page.errors == []


def test_the_no_overtaking_line_shows_in_a_blizzard_too(site, context):
    page = open_game(site, context)
    page.wait_for_function("V3 && V3.scene || no3d", timeout=15000)
    r = page.evaluate("""() => { const out = []; maxLeg = 8;
      for (const n of [5, 7, 8]) { newLeg(n); mode = 'menu'; buildWorld();
        let m = null; V3.world.traverse(o => { if (o.userData.markings) m = o; });
        // Yellow vertices inside the junctions' no-overtaking stretches.
        let yellow = 0; const c = m ? m.geometry.attributes.color.array : [];
        for (let i = 0; i < c.length; i += 3) if (c[i] > 0.7 && c[i + 2] < 0.2) yellow++;
        out.push({ n, weather: leg.weather, junctions: road.junctions.length, yellow }); }
      return out; }""")
    assert all(x["junctions"] > 0 and x["yellow"] > 0 for x in r), r
    assert r[1]["weather"] == "pyry" and r[2]["weather"] == "pyry", r
    assert page.errors == []


def test_a_car_waiting_or_turning_at_a_right_side_road_does_not_slow_the_main_road(site, context):
    page = open_game(site, context)
    for plan in ("wait", "turn"):
        r = page.evaluate("""(plan) => { HOLD = true; maxLeg = 8; newLeg(1); things = []; events = []; road.cams = []; road.nopass = [];
          P.s = 50; P.lat = -LANE;   // the player out of the way
          const J = { s: Math.round((P.s + 400) / 4) * 4, side: 1 };
          const j = release({ kind: 'liittyja', j: J, side: 1, dir: 'same', careless: false, r: 0.3 });
          const car = add('auto', { s: J.s - 60, lat: LANE, v: 25, habit: 0 }); car.base = car.v;
          if (plan === 'turn') { j.plan = 'turn'; j.turn = 0.05; }
          let dropped = 0;
          for (let i = 0; i < 60 * 1.2; i++) { P.v = 0; P.lat = -LANE; const v0 = car.v; move(car, 1 / 60); if (plan === 'wait') { j.s = J.s; j.v = 0; } else if (j.lat > EDGE) move(j, 1 / 60);
            if (j.lat > EDGE) dropped = Math.max(dropped, v0 - car.v); }
          return { dropped, v: car.v, joinerLat: j.lat }; }""", plan)
        assert r["dropped"] == 0 and r["v"] > 25, (plan, r)
    # And once the main-road car has gone by, the waiting car pulls out: nobody waits for the other.
    r = page.evaluate("""() => { HOLD = true; newLeg(1); things = []; events = []; road.cams = []; road.nopass = [];
      const J = { s: Math.round((P.s + 300) / 4) * 4, side: 1 };
      const j = release({ kind: 'liittyja', j: J, side: 1, dir: 'same', careless: false, r: 0.3 });
      const car = add('auto', { s: J.s - 50, lat: LANE, v: 22, habit: 0 }); car.base = car.v;
      for (let i = 0; i < 60 * 8 && mode === 'drive'; i++) { P.v = 25; P.lat = LANE; P.vl = 0; step(1 / 60); }
      return { carPast: car.s > J.s + 20, carV: car.v, joined: j.kind === 'auto' || j.plan === 'turn' }; }""")
    assert r["carPast"] and r["carV"] > 15 and r["joined"], r
    assert page.errors == []


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/yoajo/v9")
