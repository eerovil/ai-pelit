"""Yöajo v13 (#440): roadworks with a light, fog, a broken-down car, an ambulance, a wide load, a
snowplough and black ice, and a crash screen tall enough for its hint.
Yöajo v12 (#440): the police, and the police check from leg 3.
Yöajo v11 (#377): drive forward after coffee and let traffic pass the parked car.
Yöajo v8 (#306): the lights button on the left, a livelier gas pedal, a rest area with a lane
of its own and signs, side roads with cars pulling out, no overtaking through a junction, and
the unsafe-overtake rule within 130 m (v4–v7: 180 m)."""

from conftest import ROOT, turn

URL = "games/yoajo/v13/"

# A careful driver: keeps to the lane, overtakes only when nobody is coming and never starts an
# overtake with a solid centre line within 250 m (once out, it goes on), dips the high beams for
# oncoming cars and cars ahead, slows for moose and the speed limits (at most 90 on snow), gets
# out of the way of an oncoming overtaker, leaves a car waiting at a side road alone, and stops
# for coffee when sleepy, waiting behind a slow car before it turns into the rest area. v12: it
# leaves parked police cars alone and stops beside the officer at a police check. v13: it waits for
# green at roadworks and drives their open lane, rounds a broken-down car with room when nobody is
# coming, moves right for an ambulance and for a wide load (under 50), drives 60 on black ice, and
# keeps to low beams in fog.
BOT = """(legs) => { maxLeg = 8; const out = [];
  for (const n of legs) { newLeg(n); HOLD = true;
    for (let i = 0; i < 60 * 400 && mode === 'drive'; i++) {
      let want = LANE;
      const slow = things.filter(t => t.v >= 0 && !(t.kind === 'liittyja' && t.plan === 'wait') && t.lat > -1 && t.s > P.s - 3 && t.s - P.s < 50 && t.kind !== 'takaa' && t.kind !== 'hirvi' && t.kind !== 'poro'
        && !t.parked && t.kind !== 'konstaapeli' && t.kind !== 'partio')
        .sort((a, b) => a.s - b.s)[0];
      const onc = things.some(t => t.v < 0 && t.s + t.len / 2 > P.s - 5 && t.s - P.s < 330 && vehicle(t));
      const head = things.find(t => t.v < 0 && t.lat > 0.5 && t.s > P.s && t.s - P.s < 260);
      if (slow && !onc && !road.works.some(w => w.stop - P.s < 300 && P.s < w.far) && !road.broken.some(b => b.s - P.s < 250 && b.s > P.s - 10) && slow.kind !== 'kavelija' && (P.lat < 0.5 || ![0, 50, 100, 150, 200, 250].some(k => noPass(P.s + k)))) want = -LANE;
      if (slow && slow.kind === 'kavelija' && !onc) want = slow.lat > 0 ? 0 : LANE;
      const beside = things.find(t => t.v >= 0 && vehicle(t) && !t.parked && t.kind !== 'takaa' && t.lat > 0 && t.lat < EDGE && t.s - P.s > -7 && t.s - P.s < 7);
      if (beside && P.lat < 0.5) want = -LANE;
      if (head) want = 4.0;
      const deer = things.find(t => (t.kind === 'hirvi' || t.kind === 'poro') && t.s > P.s && t.s - P.s < 120 && Math.abs(t.lat) < 6);
      const bay = road.bays.find(b => P.s > b.s0 - 5 && P.s < b.s1 - 10);
      const rest = bay && P.tired > 0.15;
      if (rest && !(slow && slow.lat > 0 && slow.s - P.s < 25)) want = 7;
      // Traffic now passes while parked: yield before merging back into its lane.
      const merging = P.lat > EDGE && inBay(P.s, P.lat) && things.some(t => vehicle(t) && t.v > 0 && t.lat > 0 && t.lat < EDGE
        && t.s - P.s > -30 && t.s - P.s < 25);
      if (merging) want = 7;
      // v13: roadworks: stop for red (or a green about to end), then the open (left) lane.
      const w = road.works.find(w => P.s > w.stop - 200 && P.s < w.far + 10), wd = w ? w.stop - 3 - P.s : 0;
      const wait = w && wd > -2 && (!worksGreen(w) || WORK_GREEN - (T + w.off) % WORK_CYCLE < 2.5);
      if (w && P.s > w.stop - 8 && P.s < w.s1 + 4) want = -LANE;
      const inq = w && P.s < w.s1 && things.find(t => t.v >= 0 && vehicle(t) && !t.parked && t.s > P.s && t.s - P.s < 14 + t.len / 2);
      // A broken-down car: round it close to the centre line, or wait behind it while a car comes.
      const bk = road.broken.find(b => b.s - P.s < 150 && b.s - P.s > -6), bkOnc = bk && P.s < bk.s - 12 && things.some(t => t.v < 0 && vehicle(t) && t.s > P.s - 5 && t.s - P.s < 260);
      if (bk && !bkOnc && bk.s - P.s < 90) want = 0.3;
      const bkStop = bk && P.lat > 0.6 ? bk.s - 14 - P.s : 1e9;
      // An ambulance behind, a wide load ahead: to the right edge.
      const amb = things.find(t => t.kind === 'ambulanssi' && t.plan !== 'back' && t.s < P.s && P.s - t.s < 150);
      const load = things.find(t => t.kind === 'erikois' && t.s - P.s < 400 && t.s - P.s > -12);
      if (amb || load) want = 3.0;
      const icy = road.ice.some(x => P.s > x.s0 - ICE_SIGN && P.s < x.s1);
      const ck = road.checks.find(c => c.live && c.state !== 'done' && c.s - P.s > -3 && c.s - P.s < 250), stopIn = ck ? ck.s - 3 - P.s : 0;
      const err = P.lat - want + (P.vl - curveAt(P.s) * P.v * P.v * 0.55) * 0.35;
      input.left = err > 0.15; input.right = err < -0.15;
      const lim = Math.min(limitAt(P.s + 40), limitAt(P.s), (leg.weather === 'lumi' || leg.weather === 'pyry') ? 90 : 200, icy ? 60 : 200, load ? 38 : 200, bk ? 38 : 200);
      input.brake = P.v * 3.6 > lim + 3 || (deer && P.v > 4) || (rest && P.v > 2) || (head && P.v > 12)
        || (slow && want > 0 && slow.kind !== 'kavelija' && P.v > slow.v - 0.5 && slow.s - P.s < 35)
        || (ck && (stopIn < 2 || P.v > Math.sqrt(2 * 3 * stopIn)))
        || (wait && (wd < 2 || P.v > Math.sqrt(2 * 3 * wd))) || (inq && P.v > inq.v - 0.3)
        || bkStop < 2 || P.v > Math.sqrt(2 * 3 * Math.max(0, bkStop));
      P.high = !fogAt(P.s) && !fogAt(P.s + 60) && !things.some(t => t.v < 0 && vehicle(t) && t.s > P.s && t.s - P.s < 320) && !things.some(t => t.v > 0 && vehicle(t) && t.s > P.s && t.s - P.s < 70);
      input.gas = input.brake || (rest && P.s > bay.s0 && P.lat > EDGE + 0.5) || merging ? 0 : 1; step(1 / 60);
    }
    out.push({ n, mode, why: crashWhy, checks: road.checks.map(c => c.state), T, par: parTime(), points, tally: Object.assign({}, tally), stars: result && result.stars });
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
    # v12: never stopped by the police, and through every police check by stopping to blow.
    assert all(r["tally"]["poliisi"] == 0 and r["tally"]["sakot"] == 0 for r in legs), legs
    assert all(r["checks"] == (["done"] if r["n"] >= 3 else []) and r["tally"]["puhallus"] == len(r["checks"]) for r in legs), legs
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


def test_gas_drives_forward_after_coffee_and_the_exit_returns_to_the_road(site, context):
    page = open_game(site, context)
    for n in range(3, 9):
        r = page.evaluate("""(n) => { HOLD = true; maxLeg = 8; newLeg(n);
          things = []; events = []; road.cams = []; const b = road.bays[0];
          P.s = b.s0 + 10; P.lat = 9; P.v = 0; P.tired = 0.5;
          for (let i = 0; i < 120; i++) step(1 / 60);
          const start = P.s; input.gas = 0.5;
          for (let i = 0; i < 240 && mode === 'drive'; i++) step(1 / 60);
          const moved = P.s - start, kmh = P.v * KMH;
          input.gas = 1;
          for (let i = 0; i < 60 * 30 && mode === 'drive' && P.s < b.s1 + BAY_IN + 10; i++) step(1 / 60);
          return { mode, why: crashWhy, moved, kmh, coffee: tally.tauko,
            past: P.s > b.s1 + BAY_IN, lat: P.lat }; }""", n)
        assert r["coffee"] == 1 and r["moved"] > 5 and r["kmh"] > 10, (n, r)
        assert r["mode"] == "drive" and r["past"] and r["lat"] < 3.5, (n, r)
    assert page.errors == []


def test_traffic_passes_a_parked_car_but_still_waits_behind_a_car_on_the_road(site, context):
    page = open_game(site, context)
    for kind in ("traktori", "auto", "rekka"):
        for lat in (1.75, 4.1, 9):
            r = page.evaluate("""([kind, lat]) => { HOLD = true; maxLeg = 8; newLeg(3);
              things = []; events = []; road.cams = []; const b = road.bays[0];
              P.s = b.s0 + 30; P.lat = lat; P.v = 0; P.tired = 0;
              const start = P.s;
              const t = add(kind, { s: P.s - 60, lat: 2.4, v: 8 });
              for (let i = 0; i < 60 * 20 && mode === 'drive'; i++) step(1 / 60);
              return { mode, passed: t.s > P.s, speed: t.v, gap: P.s - t.s, moved: P.s - start }; }
            """, [kind, lat])
            assert r["mode"] == "drive" and r["moved"] == 0, (kind, lat, r)
            if lat == 9:
                assert r["passed"] and r["speed"] > 0, (kind, r)
            else:
                assert not r["passed"] and r["speed"] == 0 and r["gap"] > 20, (kind, lat, r)
                if lat == 4.1:
                    r = page.evaluate("""() => { P.lat = 9; const t = things[0];
                      for (let i = 0; i < 60 * 20 && mode === 'drive'; i++) step(1 / 60);
                      return {mode, passed: t.s > P.s, speed: t.v}; }""")
                    assert r["mode"] == "drive" and r["passed"] and r["speed"] > 0, (kind, r)
    assert page.errors == []


def test_coasting_in_the_rest_area_still_stops_for_coffee(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(3);
      things = []; events = []; road.cams = []; const b = road.bays[0];
      P.s = b.s0 + 20; P.lat = 9; P.v = 12 / KMH; P.tired = 0.5;
      for (let i = 0; i < 60 * 4 && mode === 'drive'; i++) step(1 / 60);
      return { mode, speed: P.v, coffee: tally.tauko, tired: P.tired }; }""")
    assert r == {"mode": "drive", "speed": 0, "coffee": 1, "tired": 0}, r
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


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/yoajo/v13")


# ---- v12 (#440): the police ----

# Leg n with only a police car on the road; the car is driven at kmh (until the police stop it)
# for secs, then left alone (no gas) for `after` seconds.
COP = """([n, cop, kmh, secs, after]) => { HOLD = true; maxLeg = 8; newLeg(n); things = []; events = []; road.cams = []; road.checks = [];
  const seen = []; let stopped = false;
  const c = eval('(' + cop + ')');
  for (let i = 0; i < 60 * (secs + after) && mode === 'drive'; i++) {
    if (i < 60 * secs && !pstop && !stopped) { P.v = kmh / KMH; P.lat = LANE; P.vl = 0; } else { input.gas = 0; input.steer = 0; }
    if (pstop) stopped = true;
    step(1 / 60);
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text);
  }
  return { mode, why: crashWhy, points, stopped, lat: P.lat, v: P.v * KMH, tally: Object.assign({}, tally), seen }; }"""

# A police car driving just ahead of the player at the player's own speed, so it keeps watching.
AHEAD = "cruiseFrom(add('auto', { s: P.s + 20, police: true, watch: true, habit: %d }))"


def test_police_cars_and_checks_are_on_the_legs_as_planned(site, context):
    page = open_game(site, context)
    for n in range(1, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu';
          const cops = events.filter(e => e.kind === 'poliisi'), c = road.checks[0];
          return { cops: cops.map(e => e.how), checks: road.checks.length,
            zone: c ? [limitAt(c.s - 150), limitAt(c.s), bayWidth(c.s + 6)] : null,
            onBad: c ? road.bad.some(b => c.s > b.s0 + 100 && c.s < b.s1 - 60) : false,
            signs: c ? road.signs.filter(s => s.kind === 'poliisi' && s.s < c.s && c.s - s.s < 300).length : 0,
            near: c ? road.bays.some(b => Math.abs(b.s0 - c.s) < 300) || road.cams.some(k => Math.abs(k.s - c.s) < 200)
              || road.junctions.some(J => Math.abs(J.s - c.s) < 100) : false }; }""", n)
        assert len(r["cops"]) == [0, 1, 1, 2, 2, 2, 3, 3][n - 1], (n, r)
        assert r["checks"] == (1 if n >= 3 else 0), (n, r)
        if r["checks"]:
            # On a pothole stretch, under its 50 limit, with a shoulder widened for the police car.
            assert r["onBad"] and r["zone"][0] == 50 and r["zone"][1] == 50, (n, r)
            assert r["zone"][2] > 6 and r["signs"] == 1 and not r["near"], (n, r)
    assert page.errors == []


def test_12_over_in_police_sight_is_a_stop_and_a_fine_and_the_drive_goes_on(site, context):
    page = open_game(site, context)
    r = page.evaluate(COP, [2, AHEAD % 12, 112, 3, 9])
    assert r["mode"] == "drive" and r["stopped"], r
    assert r["tally"]["sakot"] == 1 and r["tally"]["poliisi"] == 1 and r["points"] == -150, r
    assert "Siniset vilkut: pysähdy tien sivuun" in r["seen"] and "Poliisi: ylinopeus 12 km/h, sakko -150" in r["seen"], r
    # Pulled over onto the shoulder, and free to drive on.
    assert r["lat"] > 3.5 and page.evaluate("pstop") is None, r
    assert page.errors == []


def test_8_over_in_police_sight_is_nothing(site, context):
    page = open_game(site, context)
    r = page.evaluate(COP, [2, AHEAD % 8, 108, 6, 0])
    assert r["mode"] == "drive" and not r["stopped"] and r["tally"]["sakot"] == 0 and r["points"] == 0, r
    assert page.errors == []


def test_20_over_in_police_sight_ends_the_leg(site, context):
    page = open_game(site, context)
    r = page.evaluate(COP, [2, AHEAD % 22, 122, 3, 0])
    assert r["mode"] == "crash" and r["why"] == "Poliisi pysäytti: 122 km/h, rajoitus 100.", r
    # Out of sight it is only the old minus points.
    r = page.evaluate(COP, [2, "null", 122, 3, 0])
    assert r["mode"] == "drive" and r["tally"]["hurjastelu"] == 1 and r["points"] == -25, r
    assert page.errors == []


def test_a_police_car_does_not_see_over_a_crest(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; road.cams = []; road.checks = [];
      const s0 = 300; P.s = s0; P.lat = LANE;
      add('auto', { s: s0 + 150, lat: 13, v: 0, police: true, watch: true, parked: true, passed: true, yaw: Math.PI / 2 });
      const run = () => { for (let i = 0; i < 60; i++) { P.s = s0; P.v = (limitAt(s0) + 25) / KMH; police(1 / 60); } return mode; };
      const Y = road.Y.slice();
      for (let j = Math.floor((s0 + 60) / SEG); j < (s0 + 90) / SEG; j++) road.Y[j] += 6;
      const hidden = [policeSees(things[0]), run()];
      road.Y.set(Y);
      const open = [policeSees(things[0]), run(), crashWhy];
      return { hidden, open }; }""")
    assert r["hidden"] == [False, "drive"], r
    assert r["open"][0] is True and r["open"][1] == "crash" and r["open"][2].startswith("Poliisi pysäytti: "), r
    assert page.errors == []


def test_an_unsafe_overtake_in_police_sight_ends_the_leg_and_out_of_sight_costs_50(site, context):
    page = open_game(site, context)
    setup = """() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; road.cams = []; road.checks = []; road.nopass = [];
      P.s = 300; P.lat = -LANE; P.v = 25;
      add('vastaan', { s: 410, lat: -LANE, v: -25 });
      %s
      step(1 / 60); return { mode, why: crashWhy, points, h: tally.hurjastelu }; }"""
    r = page.evaluate(setup % "add('auto', { s: 360, lat: 13, v: 0, police: true, watch: true, parked: true, passed: true });")
    assert r["mode"] == "crash" and r["why"] == "Poliisi pysäytti: vaarallinen ohitus.", r
    r = page.evaluate(setup % "")
    assert r["mode"] == "drive" and r["points"] == -50 and r["h"] == 1, r
    assert page.errors == []


def test_dazzling_a_police_car_is_a_stop_and_a_fine(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; road.cams = []; road.checks = [];
      P.s = 300; P.lat = LANE; P.v = 20; P.high = true;
      add('vastaan', { s: 400, lat: -LANE, v: -20, police: true, watch: true });
      for (let i = 0; i < 60 && !pstop; i++) { P.high = true; step(1 / 60); }
      return { why: pstop && pstop.why, mode, h: tally.haikaisyt }; }""")
    assert r["why"] == "häikäisit poliisiautoa" and r["mode"] == "drive" and r["h"] == 1, r
    assert page.errors == []


def test_two_police_cars_fine_once_and_a_restart_mid_stop_starts_clean(site, context):
    # Two police cars see the same 14 km/h over at once: one stop, one fine. Then a restart while
    # the car is pulled over leaves no stop, no blue lights and no patrol on the new leg.
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; road.cams = []; road.checks = [];
      cruiseFrom(add('auto', { s: P.s + 20, police: true, watch: true, habit: 14 }));
      cruiseFrom(add('auto', { s: P.s + 60, police: true, watch: true, habit: 14 }));
      let stopping = false;
      for (let i = 0; i < 60 * 12 && mode === 'drive'; i++) {
        if (!pstop && !stopping) { P.v = 114 / KMH; P.lat = LANE; P.vl = 0; } else { stopping = true; input.gas = 0; }
        step(1 / 60);
      }
      const first = { sakot: tally.sakot, points, mode };
      cruiseFrom(add('auto', { s: P.s + 20, police: true, watch: true, habit: 14 }));
      for (let i = 0; i < 60 * 3 && !pstop; i++) { P.v = 114 / KMH; P.lat = LANE; P.vl = 0; step(1 / 60); }
      const mid = !!pstop;
      newLeg(2);
      for (let i = 0; i < 30; i++) step(1 / 60);
      return { first, mid, pstop: !!pstop, blue: blueLights(), patrol: things.some(t => t.kind === 'partio'),
        sakot: tally.sakot, points, mode, brake: input.brake }; }""")
    assert r["first"]["sakot"] == 1 and r["first"]["points"] == -150 and r["first"]["mode"] == "drive", r
    assert r["mid"] and not r["pstop"] and not r["blue"] and not r["patrol"], r
    assert r["sakot"] == 0 and r["points"] == 0 and r["mode"] == "drive", r
    assert page.errors == []


def test_a_police_car_dazzled_over_a_crest_does_not_stop_the_car(site, context):
    # Oncoming at the dazzle distance, and ahead within 50 m, but behind a crest: the usual
    # dazzle minus stays, the police do not stop or fine the car.
    page = open_game(site, context)
    js = """([ahead]) => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; road.cams = []; road.checks = [];
      P.s = 300; P.lat = LANE; P.v = 20; P.high = true;
      const Y = road.Y.slice(), bump = ahead ? [312, 324] : [330, 360];
      for (let j = Math.floor(bump[0] / SEG); j < bump[1] / SEG; j++) road.Y[j] += 6;
      const t = ahead ? add('auto', { s: 335, lat: LANE, v: 20, police: true, watch: true })
                      : add('vastaan', { s: 400, lat: -LANE, v: -20, police: true, watch: true });
      for (let i = 0; i < 60 * 4 && !pstop && mode === 'drive'; i++) {
        P.high = true; P.lat = LANE; P.vl = 0; P.v = 20; if (ahead) { P.s = 300; t.s = 335; t.v = 20; } step(1 / 60);
      }
      const out = { seen: policeSees(t), pstop: !!pstop, mode, h: tally.haikaisyt, sakot: tally.sakot, points };
      road.Y.set(Y); return out; }"""
    for ahead in (False, True):
        r = page.evaluate(js, [ahead])
        assert not r["seen"] and not r["pstop"] and r["mode"] == "drive", (ahead, r)
        assert r["h"] == 1 and r["sakot"] == 0 and r["points"] < 0 and r["points"] > -150, (ahead, r)
    assert page.errors == []


# The police check on leg n: everything else off the road, the car driven at 50 to it. stop:
# whether the driver stops beside the officer.
CHECK = """([n, stop, lat]) => { lat = lat === undefined ? LANE : lat; HOLD = true; maxLeg = 8; newLeg(n); things = []; road.cams = [];
  events = events.filter(e => e.kind === 'puhallus'); const c = road.checks[0]; P.s = c.s - 700;
  const seen = [];
  for (let i = 0; i < 60 * 90 && mode === 'drive' && P.s < c.s + 120; i++) {
    const d = c.s - 3 - P.s; P.lat = lat; P.vl = 0;
    input.gas = c.state === 'done' || !stop ? 0.6 : 0.4;
    input.brake = stop && c.state !== 'done' && (d < 1 || P.v > Math.sqrt(2 * 3 * Math.max(0, d))) ? 1 : 0;
    if (input.brake) input.gas = 0;
    P.v = Math.min(P.v, 50 / KMH);
    step(1 / 60);
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text);
  }
  return { at: Math.round(P.s - c.s), v: Math.round(P.v * KMH), mode, why: crashWhy, state: c.state, points, seen, puhallus: tally.puhallus, officer: things.some(t => t.kind === 'konstaapeli'),
    blue: things.some(t => t.police && t.blue && t.parked) }; }"""


def test_the_police_check_is_passed_by_stopping_and_ends_the_leg_when_driven_through(site, context):
    page = open_game(site, context)
    r = page.evaluate(CHECK, [3, True])
    assert r["mode"] == "drive" and r["state"] == "done" and r["puhallus"] == 1, r
    assert r["officer"] and r["blue"], r
    assert "Puhalluskoe: pysähdy poliisin kohdalle" in r["seen"] and "0,00 ‰ – hyvää matkaa! +20" in r["seen"], r
    # Stopped beside the officer but in the oncoming lane: no blow, no +20.
    r = page.evaluate(CHECK, [3, True, -3.5])
    assert r["mode"] == "drive" and r["state"] == "wait" and r["puhallus"] == 0 and r["points"] <= 0, r
    assert not any("hyvää matkaa" in m for m in r["seen"]), r
    r = page.evaluate(CHECK, [3, False])
    assert r["mode"] == "crash" and r["why"] == "Poliisi pysäytti: ajoit puhalluskokeen ohi.", r
    assert page.errors == []


def test_the_blue_lights_flash_on_both_edges_in_turn(site, context):
    # Both screen edges turn blue while the police stop the car, the left and the right in turn.
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = [];
      const real = performance.now.bind(performance), out = [];
      pstop = { t: 0, why: 'testi', cop: null, car: null };
      for (const ms of [30, 270]) {     // sin(t*13) > 0, then < 0: the left lit, then the right
        performance.now = () => ms; draw();
        const px = (sx) => Array.from(x.getImageData(Math.round(sx * DPR), Math.round(H * 0.5 * DPR), 1, 1).data);
        out.push({ left: px(2), right: px(W - 3), mid: px(W / 2) });
      }
      performance.now = real; pstop = null;
      return out; }""")
    for phase, lit in ((r[0], "left"), (r[1], "right")):
        dark = "right" if lit == "left" else "left"
        assert phase[lit][2] > 0 and phase[lit][3] > 100, (lit, r)
        assert 0 < phase[dark][3] < phase[lit][3], (lit, r)
    assert page.errors == []


# v13: leg n with no other traffic; setup runs once, each before every step (it holds the car's
# speed and line), and `out` is returned.
DRIVE = """([n, setup, secs, each]) => { HOLD = true; maxLeg = 8; newLeg(n); things = []; events = []; road.cams = []; road.checks = [];
  const seen = []; let out = null; eval(setup);
  for (let i = 0; i < 60 * secs && mode === 'drive'; i++) { P.vl = 0; eval(each); step(1 / 60);
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
  return { mode, why: crashWhy, points, tally: Object.assign({}, tally), seen, out, lat: P.lat, s: P.s }; }"""

PLANNED = {1: {"tietyo"}, 2: {"tietyo", "rikki", "sumu"}, 3: {"ambulanssi", "rikki", "sumu"},
           4: {"ambulanssi", "erikois", "sumu"}, 5: {"aura", "jaa", "ambulanssi"}, 6: {"aura", "jaa", "rikki"},
           7: {"aura", "jaa", "erikois"}, 8: {"aura", "jaa", "ambulanssi"}}


def test_road_events_are_on_the_legs_as_planned(site, context):
    page = open_game(site, context)
    for n in range(1, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu';
          const kinds = new Set(events.map(e => e.kind));
          const got = [];
          if (road.works.length) got.push('tietyo');
          if (road.broken.length && kinds.has('rikki')) got.push('rikki');
          if (road.fog.length) got.push('sumu');
          if (road.ice.length) got.push('jaa');
          for (const k of ['ambulanssi', 'erikois', 'aura']) if (kinds.has(k)) got.push(k);
          const w = road.works[0];
          return { planned: ROAD_EVENTS[n - 1], got, works: road.works.length,
            zone: w ? [limitAt(w.stop - 60), limitAt(w.s0 + 20)] : null,
            near: w ? road.bays.some(b => b.s1 > w.stop - 300 && b.s0 < w.far + 100) || road.checks.some(c => Math.abs(c.s - w.s0) < 400) : false,
            signs: road.signs.filter(s => s.kind === 'liukas' && s.ice).length, ice: road.ice.length }; }""", n)
        assert set(r["planned"]) == PLANNED[n] and len(r["planned"]) <= 3, (n, r)
        # Fog lies only where the leg has a dip deep enough: every other kind is always there.
        assert set(r["got"]) - {"sumu"} == PLANNED[n] - {"sumu"}, (n, r)
        assert r["works"] <= 1 and r["signs"] == r["ice"], (n, r)
        if r["works"]:
            assert r["zone"] == [50, 50] and not r["near"], (n, r)
    assert page.errors == []


WORKS = """var w = road.works[0]; P.s = w.stop - 120; P.lat = LANE;
  var greenIn = (x) => { T = (WORK_CYCLE - w.off + WORK_CYCLE * 4 - x) % WORK_CYCLE; };"""


def test_roadworks_red_light_costs_50_waiting_for_green_is_20_and_the_cones_end_the_leg(site, context):
    page = open_game(site, context)
    left = "P.v = 40 / KMH; P.lat = P.s > w.stop - 20 && P.s < w.s1 + 5 ? -LANE : LANE;"
    # Through on red, in the open lane.
    r = page.evaluate(DRIVE, [1, WORKS + " greenIn(15);", 20, left])
    assert r["mode"] == "drive" and r["tally"]["punaiset"] == 1 and r["tally"]["hurjastelu"] == 1, r
    assert "Punaisia päin -50" in r["seen"] and "Tietyö: yksi kaista, odota vihreää" in r["seen"], r
    # Stopped at the line until green, then through.
    wait = "if (P.s < w.stop - 4 && !worksGreen(w)) P.v = Math.min(40 / KMH, Math.max(0, w.stop - 4 - P.s)); else P.v = 40 / KMH;" \
           " P.lat = P.s > w.stop - 20 && P.s < w.s1 + 5 ? -LANE : LANE;"
    r = page.evaluate(DRIVE, [1, WORKS + " greenIn(15);", 40, wait])
    assert r["mode"] == "drive" and r["tally"]["tietyo"] == 1 and r["tally"]["punaiset"] == 0 and r["points"] >= 20, r
    assert "Odotit vihreää +20" in r["seen"], r
    # On green, but in the shut lane: into the roadworks.
    r = page.evaluate(DRIVE, [1, WORKS + " greenIn(-1);", 20, "P.v = 40 / KMH; P.lat = LANE;"])
    assert r["mode"] == "crash" and r["why"] == "Ajoit tietyömaalle.", r
    assert page.errors == []


def test_oncoming_cars_queue_at_the_far_line_and_come_through_on_their_turn(site, context):
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [1, WORKS + """ greenIn(5); P.s = w.stop - 400;
      for (const k of [0, 1, 2]) cruiseFrom(add('vastaan', { s: w.far + 60 + k * 15, lat: -LANE, habit: 0, passed: true }));
      out = { gaps: [], through: 0, inWorks: 0 };""", 30, """P.v = 0;
      const q = things.filter(t => t.kind === 'vastaan').sort((a, b) => a.s - b.s);
      if (q.every(t => t.v > -0.5) && !out.gaps.length) out.gaps = q.slice(1).map((t, i) => +(t.s - q[i].s).toFixed(1));
      for (const t of q) { if (t.s < w.stop - 10 && !t.counted) { t.counted = true; out.through++; }
        if (t.s > w.s0 && t.s < w.s1 && !worksOpen(w) && !t.inWorks) out.inWorks++; }"""])
    # Waiting nose to tail, not on top of each other, then all through on their own green.
    assert len(r["out"]["gaps"]) == 2 and all(5 < g < 9 for g in r["out"]["gaps"]), r
    assert r["out"]["through"] == 3 and r["out"]["inWorks"] == 0, r
    assert page.errors == []


BROKEN = """var b = road.broken[0]; P.s = b.s - 150; things = [];
  add('auto', { s: b.s, lat: BROKEN_LAT, v: 0, broken: true, parked: true, passed: true });"""


def test_a_broken_down_car_close_and_fast_is_minus_40_and_with_room_plus_20(site, context):
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [2, BROKEN, 12, "P.v = 60 / KMH; P.lat = 1.0;"])
    assert r["mode"] == "drive" and r["tally"]["lahelta"] == 1 and "Liian läheltä rikkinäistä autoa -40" in r["seen"], r
    r = page.evaluate(DRIVE, [2, BROKEN, 18, "P.v = 40 / KMH; P.lat = 0.3;"])
    assert r["mode"] == "drive" and r["tally"]["lahelta"] == 0 and "Väljä ohitus +20" in r["seen"], r
    # Straight on in the lane is a crash into it.
    r = page.evaluate(DRIVE, [2, BROKEN, 18, "P.v = 40 / KMH; P.lat = LANE;"])
    assert r["mode"] == "crash", r
    assert page.errors == []


AMB = """P.s = 400; P.lat = LANE; roadRelease({ kind: 'ambulanssi' });
  out = { amb: things.find(t => t.kind === 'ambulanssi') };"""


def test_letting_the_ambulance_by_is_30_and_blocking_it_is_minus_50(site, context):
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [3, AMB, 25, "P.v = 60 / KMH; P.lat = things.some(t => t.kind === 'ambulanssi' && t.plan !== 'catch' && t.plan !== 'back') ? 3.0 : LANE;"])
    assert r["mode"] == "drive" and r["tally"]["ambulanssi"] == 1 and r["tally"]["tukit"] == 0, r
    assert "Ambulanssi takana: väistä oikealle" in r["seen"] and "Päästit ambulanssin ohi +30" in r["seen"], r
    assert r["out"]["amb"]["plan"] == "back" and r["out"]["amb"]["s"] > r["s"], r
    r = page.evaluate(DRIVE, [3, AMB, 25, "P.v = 60 / KMH; P.lat = LANE;"])
    assert r["mode"] == "drive" and r["tally"]["tukit"] == 1 and r["tally"]["ambulanssi"] == 0, r
    assert "Tukit ambulanssin -50" in r["seen"], r
    assert page.errors == []


LOAD = """P.s = 400; P.lat = LANE; roadRelease({ kind: 'erikois' });"""


def test_a_wide_load_passed_fast_ends_the_leg_and_slow_on_the_edge_is_20(site, context):
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [4, LOAD, 30, "P.v = 45 / KMH; P.lat = 3.0;"])
    assert r["mode"] == "drive" and r["tally"]["erikois"] == 1, r
    assert "Erikoiskuljetus vastaan: oikeaan reunaan ja alle 50" in r["seen"] and "Väistit erikoiskuljetusta +20" in r["seen"], r
    r = page.evaluate(DRIVE, [4, LOAD, 30, "P.v = 70 / KMH; P.lat = 3.0;"])
    assert r["mode"] == "crash" and r["why"] == "Vaaratilanne: ohitit erikoiskuljetuksen liian kovaa.", r
    assert page.errors == []


def test_the_plough_throws_snow_black_ice_halves_grip_and_fog_shortens_high_beams(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(5); things = []; events = []; road.cams = []; road.checks = [];
      P.s = 600; P.lat = LANE; P.v = 40 / KMH; roadRelease({ kind: 'aura' });
      const a = things.find(t => t.kind === 'aura'); a.s = P.s + 20; whiteout = 0; roadTick(1 / 60);
      const near = whiteout; a.s = P.s + 200; whiteout = 0; roadTick(1 / 60);
      const x = road.ice[0];
      return { near, far: whiteout, grip: [gripAt(x.s0 + 5), gripAt(x.s0 - 30)] }; }""")
    assert r["near"] > 0.3 and r["far"] == 0, r
    assert r["grip"] == [0.5, 1], r
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(2); things = []; events = []; mode = 'drive';
      const z = road.fog[0]; P.s = z.s;
      const out = { fog: fogAt(P.s), high: fogReach(true, 200), low: fogReach(false, 80) };
      P.high = true; whiteout = 0; roadTick(1 / 60); out.white = whiteout;
      P.s = z.s + 400; out.clear = [fogAt(P.s), fogReach(true, 200)];
      return out; }""")
    assert r["fog"] == 1 and r["high"] == 30 and r["low"] == 45 and r["white"] > 0.3, r
    assert r["clear"] == [0, 200], r
    assert page.errors == []


def test_a_long_reason_and_its_hint_fit_above_the_crash_screen_buttons(site, context):
    page = open_game(site, context)
    for size in ((360, 640), (360, 740)):
        page.set_viewport_size({"width": size[0], "height": size[1]})
        r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(4); resize();
          mode = 'crash'; crashWhy = 'Vaaratilanne: ohitit erikoiskuljetuksen liian kovaa.';
          const ys = [], real = text;
          text = (s, x, y, ...rest) => { ys.push([s, y]); return real(s, x, y, ...rest); };
          btns = []; draw(); text = real;
          const b = btns.find(b => b.id === 'uudelleen');
          return { hint: ys.filter(([s]) => s.startsWith('Erikoiskuljetusta') || s.startsWith('alle 50')).map(([, y]) => y), top: b.y, H }; }""")
        assert len(r["hint"]) == 2 and max(r["hint"]) + 8 < r["top"], (size, r)
    assert page.errors == []
