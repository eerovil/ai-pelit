"""Yöajo v18 (#440): left turns cross the opposing lane inside the junction.
Yöajo v17 (#440): stars from driving points; time is only a high-score bonus.
Yöajo v16 (#440): the endless night, stage after stage, each harder, with its own list.
Yöajo v15 (#440): three Lapland legs on to Utsjoki with reindeer herds, a tank to fill at a
service station, and the whole trip's totals ("Koko matka").
Yöajo v13 (#440): roadworks with a light, fog, a broken-down car, an ambulance, a wide load, a
snowplough and black ice, and a crash screen tall enough for its hint.
Yöajo v12 (#440): the police, and the police check from leg 3.
Yöajo v11 (#377): drive forward after coffee and let traffic pass the parked car.
Yöajo v8 (#306): the lights button on the left, a livelier gas pedal, a rest area with a lane
of its own and signs, side roads with cars pulling out, no overtaking through a junction, and
the unsafe-overtake rule within 130 m (v4–v7: 180 m)."""

from conftest import ROOT, turn

URL = "games/yoajo/v19/"

# A careful driver: keeps to the lane, overtakes only when nobody is coming and never starts an
# overtake with a solid centre line within 250 m (once out, it goes on), dips the high beams for
# oncoming cars and cars ahead, slows for moose and the speed limits (at most 90 on snow), gets
# out of the way of an oncoming overtaker, leaves a car waiting at a side road alone, and stops
# for coffee when sleepy, waiting behind a slow car before it turns into the rest area. v12: it
# leaves parked police cars alone and stops beside the officer at a police check. v13: it waits for
# green at roadworks and drives their open lane, rounds a broken-down car with room when nobody is
# coming, moves right for an ambulance and for a wide load (under 50), drives 60 on black ice, and
# keeps to low beams in fog.
BOT = """(legs) => { maxLeg = 11; const out = [];
  for (const n of legs) { newLeg(n); HOLD = true;
    for (let i = 0; i < 60 * 600 && mode === 'drive'; i++) {
      let want = LANE;
      const slow = things.filter(t => t.v >= 0 && !(t.kind === 'liittyja' && t.plan === 'wait') && t.lat > -1 && t.s > P.s - 3 && t.s - P.s < 50 && t.kind !== 'takaa' && t.kind !== 'hirvi' && t.kind !== 'poro'
        && !t.parked && t.kind !== 'konstaapeli' && t.kind !== 'partio')
        // A faster car can hide a much slower tractor farther ahead. Follow the vehicle whose
        // braking point is nearest, rather than just the nearest centre position.
        .sort((a, b) => (a.s - a.len/2 - Math.max(0,P.v-a.v)**2/8) - (b.s - b.len/2 - Math.max(0,P.v-b.v)**2/8))[0];
      const onc = things.some(t => t.v < 0 && t.s + t.len / 2 > P.s - 5 && t.s - P.s < 330 && vehicle(t));
      const head = things.find(t => t.v < 0 && t.lat > 0.5 && t.s > P.s && t.s - P.s < 260);
      if (slow && !onc && !road.works.some(w => w.stop - P.s < 300 && P.s < w.far) && !road.broken.some(b => b.s - P.s < 250 && b.s > P.s - 10) && slow.kind !== 'kavelija' && (P.lat < 0.5 || ![0, 50, 100, 150, 200, 250].some(k => noPass(P.s + k)))) want = -LANE;
      if (slow && slow.kind === 'kavelija' && !onc) want = slow.lat > 0 ? 0 : LANE;
      const beside = things.find(t => t.v >= 0 && vehicle(t) && !t.parked && t.kind !== 'takaa' && t.lat > 0 && t.lat < EDGE && t.s - P.s > -3 - t.len / 2 && t.s - P.s < 3 + t.len / 2);
      if (beside && P.lat < 0.5) want = -LANE;
      if (head) want = 4.0;
      const deer = things.find(t => (t.kind === 'hirvi' || t.kind === 'poro') && t.s > P.s && t.s - P.s < 120 && Math.abs(t.lat) < 6);
      const bay = road.bays.find(b => P.s > b.s0 - 5 && P.s < b.s1 - 10);
      // v15: on a Lapland leg it fills the tank there too.
      const rest = bay && (P.tired > 0.15 || (bay.station && P.fuel < 0.98));
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
      const amb = things.find(t => t.kind === 'ambulanssi' && t.plan !== 'back' && t.s - P.s < 20 && P.s - t.s < 150);
      const load = things.find(t => t.kind === 'erikois' && t.s - P.s < 400 && t.s - P.s > -12);
      // (Not while out overtaking: back behind the one passed first.)
      if ((amb || load) && !(P.lat < 0.5 && (beside || slow && slow.s - P.s < 30 + slow.len / 2))) want = 3.0;
      const icy = road.ice.some(x => P.s > x.s0 - ICE_SIGN && P.s < x.s1);
      const ck = road.checks.find(c => c.live && c.state !== 'done' && c.s - P.s > -3 && c.s - P.s < 250), stopIn = ck ? ck.s - 3 - P.s : 0;
      // v14: no overtaking near a turn, slow for it and steer into it; at a left turn wait for a car
      // coming from the road ahead; stop for a train at the level crossing.
      const J = turnAhead(), jd = J ? J.a0 - P.s : 1e9;
      // Do not cut into a vehicle still alongside just to prepare for a turn.
      if (jd < 300 && jd > -60 && !head && !amb && !load && !bk && !(P.lat < 0.5 && (beside || slow))) want = Math.max(want, LANE);
      const cross = J && J.kind === 'risteys' && J.dir < 0 && jd > 1 && things.some(t => t.arm === J && t.kind === 'risteava'
        && t.s - J.a0 > J.C - 2 && (t.s - J.a0 - J.C) / Math.max(1, -t.v) < GAP_TIME + 1.5), crossStop = cross ? jd - 3 : 1e9;
      const rx = road.rail.find(x => x.on && x.t < RAIL_UP0 + 0.5 && x.s - P.s > 0 && x.s - P.s < 250), railStop = rx ? rx.s - 10 - P.s : 1e9;
      const err = P.lat - want + (P.vl - curveAt(P.s) * P.v * P.v * 0.55) * 0.35;
      input.left = err > 0.15; input.right = err < -0.15;
      if (J && jd < 1 && P.s < J.a0 + TURN_EASE && !P.into && !cross) { input.left = J.dir < 0; input.right = J.dir > 0; }
      const bad = road.bad.some(b => P.s > b.s0 - 30 && P.s < b.s1);
      const lim = Math.min(limitAt(P.s + 40), limitAt(P.s), (leg.weather === 'lumi' || leg.weather === 'pyry') ? 90 : 200, icy ? 60 : 200, load ? 38 : 200, bk ? 38 : 200, bad ? 50 : 200,
        jd < 400 ? turnCruise(P.s) * KMH - 4 : 200);
      input.brake = P.v * 3.6 > lim + 3 || (deer && P.v > 4) || (rest && P.v > 2) || (head && P.v > 12)
        || (slow && want > 0 && slow.kind !== 'kavelija' && P.v > slow.v - 0.5 && slow.s - P.s < Math.max(35, 10 + (P.v - slow.v) ** 2 / 4))
        || (ck && (stopIn < 2 || P.v > Math.sqrt(2 * 3 * stopIn)))
        || (wait && (wd < 2 || P.v > Math.sqrt(2 * 3 * wd))) || (inq && P.v > inq.v - 0.3)
        || bkStop < 2 || P.v > Math.sqrt(2 * 3 * Math.max(0, bkStop))
        || crossStop < 2 || P.v > Math.sqrt(2 * 3 * Math.max(0, crossStop)) || railStop < 2 || P.v > Math.sqrt(2 * 3 * Math.max(0, railStop));
      P.high = !fogAt(P.s) && !fogAt(P.s + 60) && !things.some(t => t.v < 0 && vehicle(t) && t.s > P.s && t.s - P.s < 320) && !things.some(t => t.v > 0 && vehicle(t) && t.s > P.s && t.s - P.s < 70);
      input.gas = input.brake || (rest && P.s > bay.s0 && P.lat > EDGE + 0.5) || merging ? 0 : 1; step(1 / 60);
    }
    out.push({ n, mode, why: crashWhy, at: Math.round(P.s), checks: road.checks.map(c => c.state), T, par: parTime(), points, drivingPoints: result && result.drivingPoints, tally: Object.assign({}, tally), stars: result && result.stars });
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
    assert all(r["stars"] == 3 for r in legs), [(r["n"], r["drivingPoints"], r["stars"]) for r in legs]
    assert all(r["tally"]["hurjastelu"] == 0 for r in legs), legs
    # The careful driver stops for coffee on every leg with a rest area.
    assert all(r["tally"]["tauko"] == 1 for r in legs if r["n"] >= 3), legs
    # v12: never stopped by the police, and through every police check by stopping to blow.
    assert all(r["tally"]["poliisi"] == 0 and r["tally"]["sakot"] == 0 for r in legs), legs
    assert all(r["checks"] == (["done"] if r["n"] >= 3 else []) and r["tally"]["puhallus"] == len(r["checks"]) for r in legs), legs
    assert page.errors == []


def test_stars_follow_driving_points_without_a_time_or_clean_driving_gate(site, context):
    page = open_game(site, context)
    cases = page.evaluate("""() => { HOLD = true; maxLeg = 11; const cases = [];
      for (let n = 1; n <= LEGS.length; n++) {
        const [two, three] = starTargets(n);
        for (const [p, seconds, dirty] of [[-50, 10, false], [two - 1, 10, false], [two, 10, false],
          [three - 1, 10, false], [three, 10, false], [three, 10, true], [three - 1, -10, false], [three, -10, false]]) {
          newLeg(n); T = parTime() + seconds; points = p;
          if (dirty) Object.assign(tally, { sakot:1, haikaisyt:1, lahelta:1, hurjastelu:1, tukit:1 });
          finish(); cases.push({ n, p, seconds, dirty, two, three, points, mode, result: {...result}, saved:load('tahdet')[n] });
        }
      } return cases; }""")
    for r in cases:
        expected_points = r["p"] + (100 if r["seconds"] < 0 else 0)
        expected_stars = 3 if r["p"] >= r["three"] else 2 if r["p"] >= r["two"] else 1
        assert r["mode"] == "done" and r["points"] == expected_points, r
        assert r["result"]["bonus"] == (100 if r["seconds"] < 0 else 0), r
        assert r["result"]["drivingPoints"] == r["p"], r
        assert r["result"]["stars"] == expected_stars and r["saved"] >= expected_stars, r
    assert page.errors == []


def test_existing_stars_scores_and_progress_are_kept(site, context):
    page = open_game(site, context)
    before = page.evaluate("""() => {
      const bests = {1:starTargets(1)[1], 2:starTargets(2)[0], 3:0};
      save('tahdet', {1:1, 2:1, 3:3}); save('pisteet', bests); save('taso', 4); save('ajettu', 3);
      save('loputon', {p:123, km:6, k:2}); return bests;
    }""")
    page.reload()
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    r = page.evaluate("({stars, bests, maxLeg, driven, saved:load('tahdet'), endless:load('loputon')})")
    assert r["stars"] == r["saved"] == {"1":1, "2":1, "3":3}, r
    assert r["bests"] == before and r["maxLeg"] == 4 and r["driven"] == 3, r
    assert r["endless"] == {"p":123, "km":6, "k":2}, r
    assert page.errors == []


def test_potholes_leave_posted_limits_and_their_signs_unchanged(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; const out = [], original = roadLeg;
      // Isolate the base road limits from independently placed roadworks' temporary limits.
      roadLeg = () => {};
      try {
        for (let n = 3; n <= 11; n++) {
          const L = LEGS[n - 1], count = L.bad;
          try {
            L.bad = 0; newLeg(n);
            const before = JSON.stringify(road.limits), signs = JSON.stringify(road.signs.filter(s => s.kind === 'raja'));
            L.bad = count; newLeg(n);
            out.push({ n, bad:road.bad.length, same:before === JSON.stringify(road.limits),
              sameSigns:signs === JSON.stringify(road.signs.filter(s => s.kind === 'raja')),
              warnings:road.signs.filter(s => s.kind === 'kuoppa').length });
          } finally { L.bad = count; }
        }
      } finally { roadLeg = original; } return out; }""")
    assert all(x["bad"] > 0 and x["warnings"] == x["bad"] and x["same"] and x["sameSigns"] for x in r), r
    assert page.errors == []


def test_potholes_still_advise_slowing_down_and_damage_fast_driving(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; newLeg(3);
      let h = road.holes[0]; P.s = h.s; P.lat = LANE; h.lat = LANE - 0.75; P.v = 50 / KMH; holes();
      const safe = { points, damage:P.damage, hits:tally.kuopat, messages:msgs.map(m => m.text) };
      newLeg(3);
      for (const h of road.holes.slice(0, 4)) { P.s = h.s; P.lat = LANE; h.lat = LANE - 0.75; P.v = 80 / KMH; holes(); }
      return { safe, mode, why:crashWhy, damage:P.damage, hits:tally.kuopat }; }""")
    assert r["safe"]["points"] == 0 and r["safe"]["damage"] == 0 and r["safe"]["hits"] == 0, r
    assert "Kuoppia: hidasta alle 50 km/h" in r["safe"]["messages"], r
    assert r["mode"] == "crash" and r["why"] == "Rengas puhkesi kuoppaan." and r["damage"] == 4 and r["hits"] == 4, r
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
        # Hands off the wheel: on a bend (leg 5 from v14) the car drifts a little onto the shoulder.
        assert r["mode"] == "drive" and r["past"] and r["lat"] < 4.0, (n, r)
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
    opens_and_plays_with_the_quiet_library(real, context, "games/yoajo/v19")


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
            # Potholes no longer set a 50 limit; the officer still has a widened shoulder.
            assert r["onBad"] and all(v > 50 for v in r["zone"][:2]), (n, r)
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
  road.turns = [];   // v14: no turn to take on the way (the road still bends there)
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

PLANNED = {1: set(), 2: {"tietyo", "rikki", "sumu"}, 3: {"ambulanssi", "rikki", "sumu"},
           4: {"ambulanssi", "rata", "sumu"}, 5: {"aura", "jaa", "ambulanssi"}, 6: {"aura", "jaa", "rikki"},
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
          if (road.rail.length) got.push('rata');
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
    r = page.evaluate(DRIVE, [2, WORKS + " greenIn(15);", 20, left])
    assert r["mode"] == "drive" and r["tally"]["punaiset"] == 1 and r["tally"]["hurjastelu"] == 1, r
    assert "Punaisia päin -50" in r["seen"] and "Tietyö: yksi kaista, odota vihreää" in r["seen"], r
    # Stopped at the line until green, then through.
    wait = "if (P.s < w.stop - 4 && !worksGreen(w)) P.v = Math.min(40 / KMH, Math.max(0, w.stop - 4 - P.s)); else P.v = 40 / KMH;" \
           " P.lat = P.s > w.stop - 20 && P.s < w.s1 + 5 ? -LANE : LANE;"
    r = page.evaluate(DRIVE, [2, WORKS + " greenIn(15);", 40, wait])
    assert r["mode"] == "drive" and r["tally"]["tietyo"] == 1 and r["tally"]["punaiset"] == 0 and r["points"] >= 20, r
    assert "Odotit vihreää +20" in r["seen"], r
    # On green, but in the shut lane: into the roadworks.
    r = page.evaluate(DRIVE, [2, WORKS + " greenIn(-1);", 20, "P.v = 40 / KMH; P.lat = LANE;"])
    assert r["mode"] == "crash" and r["why"] == "Ajoit tietyömaalle.", r
    assert page.errors == []


def test_oncoming_cars_queue_at_the_far_line_and_come_through_on_their_turn(site, context):
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [2, WORKS + """ greenIn(5); P.s = w.stop - 400;
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
    # The wide load's reason, and the police screen whose second hint line ran under
    # "Yritä uudelleen" in v12 upright (found on the v12 live check, #440).
    page = open_game(site, context)
    cases = (("Vaaratilanne: ohitit erikoiskuljetuksen liian kovaa.", ["Erikoiskuljetusta", "alle 50"]),
             ("Poliisi pysäytti: vaarallinen ohitus.", ["Poliisin nähden", "ja vain turvallisia"]))
    for size in ((360, 640), (360, 740), (740, 360)):
        page.set_viewport_size({"width": size[0], "height": size[1]})
        for why, starts in cases:
            r = page.evaluate("""([why, starts]) => { HOLD = true; maxLeg = 8; newLeg(4); resize();
              mode = 'crash'; crashWhy = why;
              const ys = [], real = text;
              text = (s, x, y, ...rest) => { ys.push([s, y]); return real(s, x, y, ...rest); };
              btns = []; draw(); text = real;
              const b = btns.find(b => b.id === 'uudelleen');
              return { hint: ys.filter(([s]) => starts.some(t => String(s).startsWith(t))).map(([, y]) => y), top: b.y, H }; }""",
                [why, starts])
            assert len(r["hint"]) == 2 and max(r["hint"]) + 8 < r["top"], (size, why, r)
    assert page.errors == []


def test_events_never_share_a_stretch_and_a_restart_mid_event_starts_it_fresh(site, context):
    page = open_game(site, context)
    # Two at once: the placed events keep apart on every leg, so only fog can join another.
    for n in range(1, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu';
          const t = road.taken.slice().sort((a, b) => a[0] - b[0]);
          return { overlap: t.some((x, i) => i > 0 && x[0] < t[i - 1][1]), n: t.length }; }""", n)
        assert not r["overlap"], (n, r)
    # Fog and the ambulance together: the ambulance still gets by and scores in the fog.
    r = page.evaluate(DRIVE, [2, "const z = road.fog[0]; P.s = z.s - 120; P.lat = LANE; roadRelease({ kind: 'ambulanssi' });"
                      + " out = { fog: [] };", 25,
                      "P.v = 60 / KMH; out.fog.push(fogAt(P.s)); P.lat = things.some(t => t.kind === 'ambulanssi' && t.plan === 'behind') ? 3.0 : P.lat;"])
    assert r["mode"] == "drive" and r["tally"]["ambulanssi"] == 1 and max(r["out"]["fog"]) == 1, r
    # Another order: already on the edge when it arrives, it goes straight by.
    r = page.evaluate(DRIVE, [3, AMB, 25, "P.v = 60 / KMH; P.lat = 3.0;"])
    assert r["tally"]["ambulanssi"] == 1 and r["tally"]["tukit"] == 0, r
    # A restart (the pause menu's "Aloita alusta") while the ambulance is blocked: it starts fresh.
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(3); things = []; events = []; road.cams = []; road.checks = [];
      P.s = road.broken[0].s - 300; P.lat = LANE; roadRelease({ kind: 'ambulanssi' });
      for (let i = 0; i < 60 * 20; i++) { P.vl = 0; P.v = 60 / KMH; P.lat = LANE; step(1 / 60); }
      const before = { tukit: tally.tukit, amb: things.some(t => t.kind === 'ambulanssi'), broken: road.broken.map(b => b.s), judged: road.broken.some(b => b.judged) };
      mode = 'pause'; act({ id: 'uudelleen' });
      return { before, amb: things.some(t => t.kind === 'ambulanssi'), tukit: tally.tukit || 0, points, mode,
        broken: road.broken.map(b => [b.s, b.judged]), s: P.s }; }""")
    assert r["before"]["tukit"] == 1 and r["before"]["amb"] and r["before"]["judged"], r
    assert not r["amb"] and r["tukit"] == 0 and r["points"] == 0, r
    assert [b[0] for b in r["broken"]] == r["before"]["broken"] and not any(b[1] for b in r["broken"]), r
    assert page.errors == []


def test_events_from_the_legs_own_queue_get_their_random_number_and_the_waiting_car_comes_through(site, context):
    # Review of #442: newLeg() handed out e.r before roadLeg() added its events, so the car
    # waiting at the roadworks got a NaN habit and vanished on its first step.
    page = open_game(site, context)
    r = page.evaluate(DRIVE, [2, """var real = (newLeg(2), events.filter(e => e.kind === 'tietyo' || e.kind === 'rikki'));
      var w = road.works[0]; events = real; P.s = real.find(e => e.kind === "tietyo").s; P.lat = LANE;
      out = { r: real.map(e => e.r), finite: true, seen: false, through: false, inWorks: 0, colour: null };""", 60, """P.v = 0;
      const c = things.find(t => t.kind === 'vastaan' && !t.escort);
      if (c) { out.seen = true; if (![c.s, c.v, c.lat].every(Number.isFinite)) out.finite = false;
        if (c.s < w.stop - 10) out.through = true;
        if (c.s > w.s0 && c.s < w.s1 && !worksOpen(w) && !c.inWorks) out.inWorks++; }
      const b = things.find(t => t.broken); if (b) out.colour = b.colour;"""])
    assert all(isinstance(x, float) and 0 <= x < 1 for x in r["out"]["r"]), r
    assert r["out"]["seen"] and r["out"]["finite"] and r["out"]["through"] and r["out"]["inWorks"] == 0, r["out"]
    r2 = page.evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(5);
      const e = events.find(e => e.kind === 'aura'); release(e);
      return { r: e.r, beacon: things.find(t => t.kind === 'aura').beacon }; }""")
    assert 0 <= r2["r"] < 1 and 0 <= r2["beacon"] < 7, r2
    assert page.errors == []


# v14 (#440): the route turns. A driver alone on the leg: keeps its lane, takes each turn at
# `kmh` (0: the speed the turn is meant for), steers into it once at its start unless `straight`,
# and stops `stop` (an expression: metres to the stop line, or null) when asked. Sleep is off.
TURN = """([n, setup, kmh, straight, until, stop]) => { HOLD = true; maxLeg = 11; newLeg(n); things = []; events = [];
  road.cams = []; road.checks = []; const seen = [], sig = {}; let out = {}; eval(setup);
  for (let i = 0; i < 60 * 240 && mode === 'drive' && !eval(until); i++) {
    P.tired = 0; const J = turnAhead(), jd = J ? J.a0 - P.s : 1e9;
    const err = P.lat - LANE + (P.vl - curveAt(P.s) * P.v * P.v * 0.55) * 0.35;
    input.left = err > 0.15; input.right = err < -0.15;
    if (straight) { input.left = input.right = false; P.lat = LANE; P.vl = 0; }
    else if (J && jd < 1 && P.s < J.a0 + TURN_EASE && !P.into) { input.left = J.dir < 0; input.right = J.dir > 0; }
    const bad = road.bad.some(b => P.s > b.s0 - 30 && P.s < b.s1);
    const lim = kmh || Math.min(limitAt(P.s), turnCruise(P.s) * KMH - 4, bad ? 50 : 200), d = eval(stop);
    input.brake = P.v * KMH > lim + 2 || (d !== null && (d < 1 || P.v > Math.sqrt(2 * 3 * Math.max(0, d)))) ? 1 : 0;
    input.gas = input.brake ? 0 : 1;
    step(1 / 60);
    if (J && jd > 0 && P.signal) sig[J.a0] = P.signal;
    for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text);
  }
  return { mode, why: crashWhy, points, tally: Object.assign({}, tally), seen, out, s: P.s, wrong: !!P.wrong,
    turns: road.turns.map(J => ({ a0: J.a0, a1: J.a1, dir: J.dir, kind: J.kind, done: J.done, signal: sig[J.a0] || 0 })) }; }"""
PAST_TURNS = "P.s > road.turns[road.turns.length - 1].a1 + 150"


def test_the_legs_turn_ramps_first_then_crossroads_with_signs_before(site, context):
    page = open_game(site, context)
    for n in range(1, 9):
        r = page.evaluate("""(n) => { maxLeg = 8; newLeg(n); mode = 'menu';
          return { turns: road.turns.map(J => [J.a0, J.dir, J.kind]), rail: road.rail.length,
            signs: road.signs.filter(s => s.kind === 'suunta').map(s => [Math.round(s.s), s.dir]),
            limits: road.turns.map(J => limitAt(J.a0)) }; }""", n)
        assert 1 <= len(r["turns"]) <= 3, (n, r)
        assert all(k == ("ramppi" if n <= 2 else "risteys") for _, _, k in r["turns"]), (n, r)
        assert all(d == 1 for _, d, k in r["turns"] if k == "ramppi"), (n, r)
        # Two blue signs before each, on its side: 600 m and 150 m (one may step past a police check).
        for a0, d, _ in r["turns"]:
            near = [s for s in r["signs"] if s[1] == d and 0 < a0 - s[0] <= 600]
            assert len(near) == 2 and any(a0 - s[0] == 150 for s in near), (n, a0, r)
        assert r["rail"] == (1 if n == 4 else 0), (n, r)
    lefts = page.evaluate("""() => { maxLeg = 8; let k = 0; for (let n = 3; n <= 8; n++) { newLeg(n); k += road.turns.filter(J => J.dir < 0).length; } return k; }""")
    assert lefts >= 3
    assert page.errors == []


def test_right_and_left_turns_at_the_right_speed_finish_the_leg_with_the_blinker_on_by_itself(site, context):
    page = open_game(site, context)
    for n in (1, 3, 5):
        r = page.evaluate(TURN, [n, "", 0, False, PAST_TURNS, "null"])
        assert r["mode"] == "drive" and not r["wrong"], (n, r)
        assert all(J["done"] for J in r["turns"]), (n, r)
        # The blinker came on before each turn, to its side, with no button.
        assert all(J["signal"] == J["dir"] for J in r["turns"]), (n, r)
        assert any(t.startswith("Käänny ") for t in r["seen"]), (n, r)
    assert {J["dir"] for n in (3, 5) for J in page.evaluate(TURN, [n, "", 0, False, PAST_TURNS, "null"])["turns"]} == {1, -1}
    # To the end of a leg with a crossroads: done, not crashed.
    r = page.evaluate(TURN, [3, "", 0, False, "false", "null"])
    assert r["mode"] == "done", r
    assert page.errors == []


def test_a_missed_turn_ends_the_leg_on_the_wrong_road(site, context):
    page = open_game(site, context)
    r = page.evaluate(TURN, [3, "P.s = road.turns[0].a0 - 300;", 40, True, "false", "null"])
    assert r["mode"] == "crash" and r["why"] == "Väärä tie: ajoit ohi käännöksen.", r
    assert "Väärä tie!" in r["seen"] and r["wrong"], r
    J = r["turns"][0]
    assert J["a0"] + 240 < r["s"] < J["a0"] + 270, r
    assert page.errors == []


def test_a_crossroads_at_70_ends_in_the_ditch_and_a_ramp_takes_60(site, context):
    page = open_game(site, context)
    r = page.evaluate(TURN, [3, "P.s = road.turns[0].a0 - 300; P.v = 70 / KMH;", 70, False, PAST_TURNS, "null"])
    assert r["mode"] == "crash" and r["why"] == "Ajoit ojaan: liian lujaa risteykseen.", r
    r = page.evaluate(TURN, [1, "P.s = road.turns[0].a0 - 300;", 60, False, PAST_TURNS, "null"])
    assert r["mode"] == "drive" and r["turns"][0]["done"], r
    assert page.errors == []


# A left turn on leg 5, with the car from the road ahead set off so that it is `gap` s from the
# crossing when the player rounds into the turn; `wait`: stop before the turn until it has gone by.
LEFT = """var LJ = road.turns.find(J => J.dir < 0); P.s = LJ.a0 - 140; LJ.spawned = true; out = { went: false };"""
LEFT_EACH = """(() => { const J = LJ;
  if (!out.went && J.a0 - P.s < 12) { out.went = true; const t = (J.a0 + TURN_EASE - P.s) / Math.max(P.v, 1);
    add('risteava', { s: J.a0 + J.C + ARM_V * (%s + t), lat: -LANE, v: -ARM_V, arm: J, colour: 1, high: false, passed: true }); }
  const c = things.find(t => t.kind === 'risteava');
  return %s && c && c.s - J.a0 > J.C - 2 ? J.a0 - 3 - P.s : null; })()"""
PAST_LEFT = "P.s > LJ.a1 + 60"


def test_a_left_turn_across_a_close_oncoming_car_is_50_off_and_waiting_is_20(site, context):
    page = open_game(site, context)
    r = page.evaluate(TURN, [5, LEFT, 0, False, PAST_LEFT, LEFT_EACH % (2, "false")])
    assert r["mode"] == "drive" and all(J["done"] for J in r["turns"] if J["dir"] < 0), r
    assert "Käännyit vastaantulijan eteen -50" in r["seen"] and r["tally"]["hurjastelu"] == 1, r
    # The same with the police watching ends the leg.
    r = page.evaluate(TURN, [5, LEFT + "add('auto', { s: LJ.a0 + 20, lat: 13, v: 0, police: true, watch: true, parked: true, passed: true, yaw: Math.PI / 2 });",
                             0, False, PAST_LEFT, LEFT_EACH % (2, "false")])
    assert "Käännyit vastaantulijan eteen -50" in r["seen"], r
    assert r["mode"] == "crash" and r["why"] == "Poliisi pysäytti: vaarallinen käännös.", r
    # Waiting for it: +20, and no harm.
    r = page.evaluate(TURN, [5, LEFT, 0, False, PAST_LEFT, LEFT_EACH % (2, "true")])
    assert r["mode"] == "drive" and "Annoit tietä +20" in r["seen"] and r["tally"]["kaannos"] == 1, r
    assert r["tally"]["hurjastelu"] == 0, r
    # One far enough away is no harm either.
    r = page.evaluate(TURN, [5, LEFT, 0, False, PAST_LEFT, LEFT_EACH % (9, "false")])
    assert r["mode"] == "drive" and r["tally"]["hurjastelu"] == 0 and r["points"] >= 0, r
    assert page.errors == []


RAIL = """var x = road.rail[0]; P.s = x.s - 400; out = { queued: null };
  var car = cruiseFrom(add('auto', { s: x.s - 300, lat: LANE, colour: 2, habit: 0, passed: true }));"""
RAIL_STOP = """(() => { if (x.on && x.t > 8 && out.queued === null) out.queued = Math.round(x.s - car.s);
  const rail = x.on && x.t < RAIL_UP0 + 0.5 ? x.s - 12 - P.s : 1e9, gap = car.s > P.s ? car.s - car.len / 2 - 8 - P.s : 1e9;
  return Math.min(rail, gap) < 1e9 ? Math.min(rail, gap) : null; })()"""


def test_the_level_crossing_waiting_is_20_through_the_barriers_ends_the_leg_and_traffic_queues(site, context):
    page = open_game(site, context)
    # v15: leg 4 and Lapland's first leg (#440's spec: the level crossing on leg 4 and in Lapland).
    rails = page.evaluate("() => { maxLeg = 11; const out = []; for (let n = 1; n <= 11; n++) { newLeg(n); out.push(road.rail.length); } return out; }")
    assert rails == [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0], rails
    for n in (4, 9):
        r = page.evaluate(TURN, [n, RAIL, 60, False, "P.s > x.s + 40", RAIL_STOP])
        assert r["mode"] == "drive" and r["tally"]["juna"] == 1, (n, r)
        assert "Juna tulee: puomit laskeutuvat" in r["seen"] and "Juna meni ohi +20" in r["seen"], (n, r)
        # The car ahead stopped before the crossing while the train went by.
        assert r["out"]["queued"] is not None and 3 < r["out"]["queued"] < 20, (n, r)
        r = page.evaluate(TURN, [n, "var x = road.rail[0]; P.s = x.s - 400;", 60, False, "P.s > x.s + 40", "null"])
        assert r["mode"] == "crash" and r["why"] == "Ajoit puomien läpi tasoristeyksessä.", (n, r)
    assert page.errors == []


def test_a_restart_in_a_bend_or_on_the_wrong_road_starts_the_leg_with_its_turns_fresh(site, context):
    # "Aloita alusta" in the pause menu and "Yritä uudelleen" both call newLeg(level) (ui.js).
    page = open_game(site, context)
    state = """() => ({ level, mode, wrong: P.wrong, into: P.into, signal: P.signal, s: P.s,
      done: road.turns.map(J => !!J.done), told: road.turns.map(J => J.told || 0),
      crossers: things.filter(t => t.arm).length })"""
    # Mid-bend at leg 5's first (left) turn, then restart.
    r = page.evaluate(TURN, [5, "", 0, False, "P.into && P.s > road.turns[0].a0 + 2", "null"])
    assert r["mode"] == "drive", r
    page.evaluate("() => newLeg(level)")
    a = page.evaluate(state)
    assert a["level"] == 5 and a["mode"] == "drive" and a["wrong"] is None and not a["into"], a
    assert a["signal"] == 0 and not any(a["done"]) and not any(a["told"]) and a["crossers"] == 0, a
    # On the wrong road past it, then restart.
    r = page.evaluate(TURN, [5, "", 40, True, "P.wrong && P.s > P.wrong.s0 + 100", "null"])
    assert r["mode"] == "drive" and r["wrong"], r
    page.evaluate("() => newLeg(level)")
    a = page.evaluate(state)
    assert a["wrong"] is None and not a["into"] and a["signal"] == 0 and not any(a["done"]), a
    assert a["s"] < 50, a
    # The restarted leg drives through all its turns.
    r = page.evaluate(TURN, [5, "", 0, False, PAST_TURNS, "null"])
    assert r["mode"] == "drive" and not r["wrong"] and all(J["done"] for J in r["turns"]), r
    assert page.errors == []


def test_the_crossing_car_once_through_the_junction_is_an_oncoming_car_on_the_players_road(site, context):
    r = open_game(site, context).evaluate("""() => { HOLD = true; maxLeg = 8; newLeg(5); things = []; events = [];
      road.cams = []; road.checks = [];
      const J = road.turns.find(J => J.dir < 0 && J.kind === 'risteys');
      P.s = J.a0 - 60; P.v = 0; P.lat = LANE; P.vl = 0;
      const t = add('risteava', { s: J.a0 + 40, lat: -LANE, v: -ARM_V, arm: J, colour: 1, high: false, passed: true });
      let through = null;
      for (let i = 0; i < 60 * 20 && mode === 'drive'; i++) {
        P.tired = 0; input.left = input.right = false; input.gas = 0; input.brake = 1; P.lat = LANE; P.vl = 0;
        step(1 / 60);
        if (t.kind === 'vastaan' && !through) { through = { arm: t.arm, s: t.s - J.a0, lat: t.lat }; break; }
      }
      const drawnOn = through && things.includes(t) ? 'road' : null;
      // Now the player swerves into its lane: that is a crash, not a pass through it.
      for (let i = 0; i < 60 * 10 && mode === 'drive'; i++) { P.tired = 0; input.brake = 1; P.lat = -LANE; P.vl = 0; step(1 / 60); }
      return { through, drawnOn, mode, why: crashWhy, gap: Math.round(t.s - P.s) }; }""")
    assert r["through"] and r["through"]["arm"] is None and r["through"]["s"] < -1, r
    assert r["drawnOn"] == "road", r
    assert r["mode"] == "crash" and r["why"] != "Väärä tie: ajoit ohi käännöksen.", r


# ---- v15 (#440): Lapland ----

def test_the_lapland_legs_can_be_driven_with_a_stop_for_fuel(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, [9, 10, 11])
    assert all(r["mode"] == "done" for r in legs), [(r["n"], r["why"], r["at"]) for r in legs]
    assert all(r["stars"] == 3 for r in legs), [(r["n"], r["drivingPoints"], r["stars"]) for r in legs]
    for r in legs:
        t = r["tally"]
        assert t["tankkaus"] == 1 and t["tauko"] == 1 and t["hurjastelu"] == 0 and t["poliisi"] == 0, (r["n"], t)
        # Moose and reindeer got past are counted for the trip's totals.
        assert t["elaimet"] >= 3, (r["n"], t)
    assert page.errors == []


FUEL = """([n, kmh]) => { HOLD = true; maxLeg = 11; newLeg(n); things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.turns = [];
  const st = road.bays.find(b => b.station), start = P.fuel;
  for (let i = 0; i < 60 * 600 && mode === 'drive' && P.s < st.s0; i++) {
    if (!P.dry) P.v = (kmh || limitAt(P.s)) / KMH; P.lat = LANE; P.vl = 0; step(1 / 60); }
  return { mode, why: crashWhy, start, fuel: P.fuel, at: Math.round(P.s), s0: st.s0, low: msgs.map(m => m.text) }; }"""


def test_the_tank_reaches_the_station_at_the_limits_but_not_at_full_speed(site, context):
    page = open_game(site, context)
    for n in (9, 10, 11):
        r = page.evaluate(FUEL, [n, 0])
        assert r["mode"] == "drive" and 0.1 < r["fuel"] < 0.35 and r["start"] < 1, (n, r)
        r = page.evaluate(FUEL, [n, 130])
        assert r["mode"] == "crash" and r["why"] == "Polttoaine loppui." and r["at"] < r["s0"], (n, r)
    # The warning names how far the station is.
    r = page.evaluate("""() => { HOLD = true; newLeg(9); things = []; events = []; road.cams = []; road.checks = [];
      const st = road.bays.find(b => b.station); P.s = st.s0 - 900; P.fuel = FUEL_LOW + 0.0001; P.v = 80 / KMH; P.lat = LANE;
      for (let i = 0; i < 60; i++) { P.v = 80 / KMH; step(1 / 60); } return msgs.map(m => m.text); }""")
    assert any(t.startswith("Tankki vähissä: huoltoasema 0,9 km") for t in r), r
    assert page.errors == []


def test_the_pump_fills_the_tank_and_only_lapland_has_one(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const out = []; maxLeg = 11;
      for (let n = 1; n <= 11; n++) { newLeg(n); out.push([n, P.fuel, road.bays.filter(b => b.station).length,
        road.signs.filter(s => s.kind === 'huolto').map(s => s.text), road.signs.filter(s => s.kind === 'levahdys').length]); }
      return out; }""")
    for n, fuel, stations, huolto, rest in r:
        if n <= 8:
            assert fuel is None and stations == 0 and huolto == [], r
        else:
            assert 0 < fuel < 1 and stations == 1 and huolto == ["500 m", "100 m"] and rest == 0, r
    r = page.evaluate("""() => { HOLD = true; newLeg(10); things = []; events = []; road.cams = []; road.checks = [];
      const b = road.bays.find(b => b.station); P.s = b.s0 + 30; P.lat = 9; P.v = 0; P.fuel = 0.3; P.tired = 0;
      const seen = [];
      for (let i = 0; i < 60 * 9; i++) { step(1 / 60); if (i === 60) seen.push(P.filling); }
      btns = []; draw(); return { fuel: P.fuel, filling: seen[0], n: tally.tankkaus, msgs: msgs.map(m => m.text), mode }; }""")
    assert r["fuel"] == 1 and r["filling"] and r["n"] == 1 and "Tankki täynnä" in r["msgs"] and r["mode"] == "drive", r
    assert page.errors == []


def test_the_lapland_legs_open_in_turn_and_an_old_save_opens_the_first(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 8; driven = 7; newLeg(8); P.s = leg.len + 1; finish();
      return { maxLeg, taso: load('taso'), ajettu: load('ajettu'), buttons: btns.map(b => b.id) }; }""")
    assert r["maxLeg"] == 9 and r["taso"] == 9 and r["ajettu"] == 8, r
    # A phone that drove to Rovaniemi in v14 (taso stopped at 8) gets Lapland's first leg.
    page.evaluate("""() => { localStorage.setItem('ai-pelit:yoajo:taso', '8'); localStorage.setItem('ai-pelit:yoajo:ajettu', '8'); }""")
    page.reload(); page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    assert page.evaluate("[maxLeg, level, load('taso')]") == [9, 9, 9]
    # One that had not, keeps its legs.
    page.evaluate("""() => { localStorage.setItem('ai-pelit:yoajo:taso', '8'); localStorage.setItem('ai-pelit:yoajo:ajettu', '7'); }""")
    page.reload(); page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    assert page.evaluate("[maxLeg, level]") == [8, 8]
    # The last leg's end offers the whole trip; "Takaisin" comes back to it.
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; newLeg(11); P.s = leg.len + 1; finish(); btns = []; draw();
      const ids = btns.map(b => b.id); act({ id: 'matka' }); const m1 = mode; btns = []; draw();
      const back = btns.map(b => b.id); act({ id: 'takaisin' }); return { ids, m1, back, m2: mode }; }""")
    assert r["ids"] == ["matka", "uudelleen", "valikko"] and r["m1"] == "matka" and r["back"] == ["takaisin"] and r["m2"] == "done", r
    assert page.errors == []


def test_the_trip_adds_up_and_keeps_what_was_driven(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; localStorage.removeItem('ai-pelit:yoajo:tilasto');
      stars = { 1: 3, 2: 2, 9: 1 }; bests = { 1: 800, 2: 650, 9: 400 };
      const tot = tripTotals();
      // A leg crashed 1.5 km in: its km count, not as a leg driven to the end.
      newLeg(9); things = []; events = []; road.cams = []; road.checks = []; P.s = 1500; tally.elaimet = 2; crash('Kolari!');
      const a = load('tilasto');
      // A leg driven to the end.
      newLeg(1); P.s = leg.len + 1; tally.sakot = 1; finish();
      const b = load('tilasto');
      // Leaving a leg from the pause menu before 30 m adds nothing.
      newLeg(2); P.s = 10; act({ id: 'valikko' });
      return { tot, a, b, c: load('tilasto') }; }""")
    assert r["tot"] == {"pts": 1850, "st": 6, "legs": 3, "of": 33}, r
    assert r["a"] == {"km": 1.5, "osuudet": 0, "poliisi": 0, "sakot": 0, "elaimet": 2, "tankkaus": 0}, r
    assert r["b"]["osuudet"] == 1 and r["b"]["sakot"] == 1 and r["b"]["km"] >= 1.5 + 3, r
    assert r["c"] == r["b"], r
    assert page.errors == []


def test_reindeer_herds_cross_one_after_another_and_stand_longer(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const out = []; maxLeg = 11;
      for (let n = 1; n <= 11; n++) { newLeg(n); const h = events.filter(e => e.herd != null);
        out.push({ n, herd: h.length, holds: h.map(e => e.hold), sides: [...new Set(h.map(e => e.side))].length }); }
      return out; }""")
    for x in r:
        herds = {9: 1, 10: 2, 11: 2}.get(x["n"], 0)
        assert 3 * herds <= x["herd"] <= 5 * herds, x
        assert all(h >= 2 for h in x["holds"]), x
    # Each reindeer of a herd waits its own while on the road, longer than a lone one's 1.6 s.
    r = page.evaluate("""() => { HOLD = true; newLeg(10); things = []; road.cams = []; road.checks = []; road.holes = [];
      const e = events.find(e => e.herd === 0); events = events.filter(x => x.herd != null && x.s === e.s);
      P.s = e.s - 20; P.v = 0; P.lat = LANE; let most = 0;
      for (let i = 0; i < 60 * 3 && events.length; i++) { P.v = 30 / KMH; step(1 / 60); }
      P.v = 0; for (let i = 0; i < 60 * 15; i++) { P.v = 0; step(1 / 60); most = Math.max(most, things.filter(t => t.kind === 'poro').length); }
      return { most, n: events.length, mode }; }""")
    assert r["most"] >= 3 and r["mode"] == "drive", r
    assert page.errors == []


MENU = """(sel0) => { HOLD = true; maxLeg = 11; sel = sel0; preview(sel0); btns = []; draw();
  const rows = btns.filter(b => b.id.startsWith('osa-')), ohj = btns.find(b => b.id === 'ohjaus'), mat = btns.find(b => b.id === 'matka');
  return { rows: rows.map(b => [b.id, b.y, b.h]), ids: btns.map(b => b.id), bottom: Math.max(...btns.filter(b => !['ohjaus', 'matka', 'aja', 'loputon'].includes(b.id)).map(b => b.y + b.h)),
    ohj: ohj && [ohj.x, ohj.y, ohj.w], mat: mat && [mat.x, mat.y, mat.w], W, H }; }"""


def test_the_menu_shows_eleven_legs_at_both_sizes(site, context):
    for w, h in ((360, 740), (360, 640), (390, 844), (740, 360)):
        page = open_game(site, context)
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_function(f"W === {w} && H === {h}")
        for sel0 in (1, 11, 6):
            r = page.evaluate(MENU, sel0)
            ids = [x[0] for x in r["rows"]]
            assert f"osa-{sel0}" in ids, (w, h, sel0, r)
            assert all(x[2] >= 30 for x in r["rows"]), (w, h, r)
            assert r["mat"] and r["ohj"][0] + r["ohj"][2] < r["mat"][0] and r["mat"][0] + r["mat"][2] <= r["W"], (w, h, r)
            if h > w:
                assert r["bottom"] < r["ohj"][1], (w, h, r)
            if len(ids) < 11:
                assert "ylos" in r["ids"] and "alas" in r["ids"], (w, h, r)
        # The arrows move the window.
        r = page.evaluate("""() => { sel = 1; preview(1); btns = []; draw(); const a = btns.filter(b => b.id.startsWith('osa-')).map(b => b.id);
          if (!btns.some(b => b.id === 'alas')) return { a, b: a };
          act({ id: 'alas' }); btns = []; draw(); return { a, b: btns.filter(b => b.id.startsWith('osa-')).map(b => b.id) }; }""")
        if len(r["a"]) < 11:
            assert r["b"] != r["a"] and "osa-11" in r["b"] or r["b"][0] == "osa-4", (w, h, r)
        assert page.errors == []
        page.close()


def test_a_restart_gives_a_fresh_tank_and_station(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; newLeg(9); things = []; events = []; road.cams = []; road.checks = [];
      const start = P.fuel, b = road.bays.find(b => b.station); P.s = b.s0 + 30; P.lat = 9; P.v = 0; P.fuel = 0.2;
      for (let i = 0; i < 60 * 9; i++) step(1 / 60);
      const filled = [P.fuel, tally.tankkaus]; P.fuel = 0.05; act({ id: 'uudelleen' });
      const b2 = road.bays.find(b => b.station);
      return { start, filled, again: P.fuel, n: tally.tankkaus, dry: P.dry, fresh: !b2.filled, mode }; }""")
    assert r["filled"] == [1, 1] and r["again"] == r["start"] and r["n"] == 0 and not r["dry"] and r["fresh"], r
    assert page.errors == []


DONE = """(n) => { HOLD = true; maxLeg = 11; newLeg(n); P.s = leg.len + 1; finish(); btns = []; draw();
  return { ids: btns.map(b => b.id), bottom: Math.max(...btns.map(b => b.y + b.h)), W, H }; }"""


def test_the_trip_is_offered_after_rovaniemi_and_utsjoki(site, context):
    # #440's spec: "Koko matka" after Rovaniemi (leg 8) and after Utsjoki (leg 11); the next leg stays.
    for w, h in ((360, 640), (390, 844), (740, 360)):
        page = open_game(site, context)
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_function(f"W === {w} && H === {h}")
        for n, ids in ((7, ["seuraava", "uudelleen", "valikko"]), (8, ["seuraava", "matka", "uudelleen", "valikko"]),
                       (11, ["matka", "uudelleen", "valikko"])):
            r = page.evaluate(DONE, n)
            assert r["ids"] == ids and r["bottom"] <= h, (w, h, n, r)
        page.evaluate(DONE, 8)
        r = page.evaluate("() => { act({ id: 'matka' }); const m = mode; act({ id: 'takaisin' }); const m2 = mode; act({ id: 'seuraava' }); return [m, m2, mode, level]; }")
        assert r == ["matka", "done", "drive", 9], r
        assert page.errors == []
        page.close()


def test_lapland_has_long_straights_and_legs_1_to_8_keep_their_road(site, context):
    page = open_game(site, context)
    # The share of each leg's road that runs straight, and its longest straight in metres.
    r = page.evaluate("""() => { const out = {}; for (let n = 1; n <= 11; n++) { const L = LEGS[n - 1], R = makeRoad(L);
        let run = 0, best = 0, flat = 0; for (let i = 0; i < R.K.length; i++) { if (R.K[i] === 0) { run += SEG; flat += SEG; best = Math.max(best, run); } else run = 0; }
        out[n] = [Math.round(flat / (R.K.length * SEG) * 100), Math.round(best)]; } return out; }""")
    lap = [r[str(n)] for n in (9, 10, 11)]
    south = [r[str(n)] for n in range(1, 9)]
    assert all(b >= 500 for _, b in lap), r
    assert min(p for p, _ in lap) > max(p for p, _ in south), r
    assert page.errors == []


def test_a_leg_left_by_the_back_chip_still_counts_on_the_trip_once(site, context):
    page = open_game(site, context)
    # Driving 800 m with a fine and two animals, the page hidden and shown twice (a call, the home
    # screen): each look adds only what is new.
    r = page.evaluate("""() => { HOLD = true; localStorage.removeItem('ai-pelit:yoajo:tilasto'); maxLeg = 9;
      newLeg(9); mode = 'drive'; P.s = 800; tally.sakot = 1; tally.elaimet = 2; tripLog(); tripLog();
      const a = load('tilasto'); P.s = 1300; tally.elaimet = 3; tripLog(); return { a, b: load('tilasto') }; }""")
    assert r["a"] == {"km": 0.8, "osuudet": 0, "poliisi": 0, "sakot": 1, "elaimet": 2, "tankkaus": 0}, r
    assert round(r["b"]["km"], 3) == 1.3 and r["b"]["sakot"] == 1 and r["b"]["elaimet"] == 3, r
    # Then on to 2 km and straight out to the shelf, as "‹ Pelit → Takaisin pelilistaan" does:
    # pagehide logs the rest.
    page.evaluate("() => { P.s = 2000; tally.poliisi = 1; }")
    page.goto(f"{site.url}/")
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    t = page.evaluate("() => tripStats()")
    assert round(t["km"], 3) == 2.0 and t["poliisi"] == 1 and t["sakot"] == 1 and t["elaimet"] == 3 and t["osuudet"] == 0, t
    assert page.errors == []


# ---- v16: the endless night ----

# The careful driver on the endless night: the run from its first stage until it reaches stage
# `stages` + 1 or ends.
ENDLESS_BOT = BOT.replace("""(legs) => { maxLeg = 11; const out = [];
  for (const n of legs) { newLeg(n); HOLD = true;""", """([stages, seed]) => { driven = 1; const out = [];
  { startEndless(seed); HOLD = true; const n = 0;""").replace(
    "i < 60 * 600 && mode === 'drive'", "i < 60 * 3000 && mode === 'drive' && endless.k <= stages").replace(
    "out.push({ n, mode,", "out.push({ k: endless.k, why: crashWhy, km: endlessMetres() / 1000, fuel: P.fuel, tired: P.tired, mode,").replace(
    # Waiting at the roadworks' red in its own lane, not creeping into the open lane before green
    # (a stage may start just before the works, where the legs never put them).
    "if (w && P.s > w.stop - 8 && P.s < w.s1 + 4) want = -LANE;", "if (w && P.s > w.stop - 8 && P.s < w.s1 + 4 && !(wait && wd > -2)) want = -LANE;")
assert ENDLESS_BOT != BOT and "startEndless" in ENDLESS_BOT and "endless.k <= stages" in ENDLESS_BOT


def test_the_endless_night_opens_once_leg_1_is_driven(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { driven = 0; btns = []; draw(); const lo = btns.find(b => b.id === 'loputon');
      act(lo); const a = { locked: lo.locked, mode, endless };
      driven = 1; btns = []; draw(); const lo2 = btns.find(b => b.id === 'loputon');
      const boards = []; AiPelitScores.board = (id, label) => boards.push([id, label]);
      act(lo2); return { a, locked: lo2.locked, mode, k: endless && endless.k, stage: leg.endless, fuel: P.fuel, boards, from: leg.from, to: leg.to }; }""")
    assert r["a"] == {"locked": True, "mode": "menu", "endless": None}, r
    assert r["locked"] is False and r["mode"] == "drive" and r["k"] == 1 and r["stage"] is True and r["fuel"] == 1, r
    assert r["boards"] == [["loputon", "Loputon yö"]] and r["from"] != r["to"], r
    assert page.errors == []


def test_each_stage_is_a_little_harder_and_a_station_comes_every_other_stage(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { endless = { k: 1, seed: 1234, back: 1, m: 0, paid: 0, fade: 0, over: null };
      const out = [];
      for (let k = 1; k <= 14; k++) { endless.k = k; newLeg(); out.push({ k, len: leg.len, oncoming: leg.oncoming, trucks: leg.trucks, moose: leg.moose,
        police: leg.police, turns: leg.turns, weather: leg.weather, stations: road.bays.filter(b => b.station).length,
        realTurns: road.turns.length, cops: things.length >= 0 ? events.filter(e => e.kind === 'partio' || e.kind === 'poliisi').length : 0,
        from: leg.from, to: leg.to }); }
      endless = null; return out; }""")
    a, b = r[0], r[1]
    assert b["oncoming"] > a["oncoming"] and b["trucks"] > a["trucks"] and b["moose"] > a["moose"], (a, b)
    assert a["weather"] == "kuiva" and b["weather"] == "sade", (a, b)
    for key in ("oncoming", "trucks", "moose", "police", "turns", "len"):
        vals = [x[key] for x in r]
        assert vals == sorted(vals) and vals[-1] > vals[0], (key, vals)
    # A station on the even stages only; each stage starts where the last one ended, no place twice.
    assert [x["stations"] for x in r] == [k % 2 == 0 and 1 or 0 for k in range(1, 15)], r
    assert all(r[i]["from"] == r[i - 1]["to"] for i in range(1, len(r))), r
    assert len({x["to"] for x in r}) == len(r), r
    assert all(x["realTurns"] >= 1 for x in r), r
    assert all(2800 <= x["len"] <= 3900 for x in r), r
    assert page.errors == []


def test_the_next_stage_keeps_the_speed_tank_alertness_and_points_behind_a_fade(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; driven = 1; startEndless(977); things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.broken = []; road.works = []; road.rail = [];
      const len1 = leg.len, to1 = leg.to; P.s = leg.len - 0.2; P.v = 25; P.fuel = 0.6; P.tired = 0.3; P.high = true; points = 345; endless.paid = 3;
      step(1 / 60);
      const a = { k: endless.k, s: P.s, v: P.v, fuel: P.fuel, tired: P.tired, high: P.high, points, fade: endless.fade, msgs: msgs.map(m => m.text), from: leg.from, to1, mode,
        km: endlessMetres() };
      btns = []; draw();
      for (let i = 0; i < 80; i++) { P.v = 25; step(1 / 60); }
      return { a, len1, fade: endless.fade, mode, seen: msgs.map(m => m.text) }; }""")
    a = r["a"]
    assert a["k"] == 2 and a["mode"] == "drive" and a["s"] < 10 and a["from"] == a["to1"], r
    assert abs(a["v"] - 25) < 0.5 and abs(a["fuel"] - 0.6) < 0.01 and abs(a["tired"] - 0.3) < 0.01 and a["high"] is True, r
    assert a["points"] == 345 and a["fade"] > 0.9, r
    assert f"Etappi 2 · {r['len1'] // 1000} km" in a["msgs"], r
    assert r["fade"] == 0 and r["mode"] == "drive", r
    assert page.errors == []


def test_a_finger_held_over_the_stage_line_keeps_steering_and_the_gas(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; driven = 1; startEndless(977); things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.broken = []; road.works = []; road.rail = [];
      const box = c.getBoundingClientRect(), ev = (type, id, x, y) => c.dispatchEvent(new PointerEvent(type, { pointerId: id, clientX: box.left + x, clientY: box.top + y, bubbles: true, cancelable: true }));
      // The two thumbs (left steers, right drives), each slid from where it landed.
      setControls('kaksi'); btns = []; draw();   // a drive frame's buttons, not the menu's
      ev('pointerdown', 1, 60, 640); ev('pointermove', 1, 90, 640);
      ev('pointerdown', 2, 300, 660); ev('pointermove', 2, 300, 620);
      const before = { steer: input.steer, gas: input.gas };
      P.s = leg.len - 0.2; P.v = 25; step(1 / 60);
      const after = { k: endless.k, steer: input.steer, gas: input.gas };
      ev('pointerup', 1, 90, 640); ev('pointerup', 2, 300, 620);
      return { before, after, released: { steer: input.steer, gas: input.gas } }; }""")
    b, a = r["before"], r["after"]
    assert b["steer"] > 0 and b["gas"] > 0.35, r
    assert a["k"] == 2 and abs(a["steer"] - b["steer"]) < 1e-9 and abs(a["gas"] - b["gas"]) < 1e-9, r
    assert r["released"] == {"steer": 0, "gas": 0}, r
    assert page.errors == []


def test_the_run_scores_20_a_km_and_its_end_goes_to_the_loputon_list(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; driven = 1; localStorage.removeItem('ai-pelit:yoajo:loputon');
      const sent = []; AiPelitScores.submit = p => sent.push(p);
      startEndless(977); road.turns = []; things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.broken = []; road.works = []; road.rail = [];
      const seen = [];
      for (let i = 0; i < 60 * 200 && P.s < 2100; i++) { P.v = 13; P.lat = LANE; P.vl = 0; step(1 / 60); for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
      const a = { points, msgs: seen };
      crash('Ajoit ojaan.');
      const b = { mode, sent: sent.slice(), best: load('loputon'), over: endless.over };
      btns = []; draw(); const ids = btns.map(x => x.id);
      act({ id: 'uudelleen' }); const c = { mode, k: endless.k, points, s: P.s };
      points = 5; crash('Ajoit ojaan.');
      const d = { sent: sent.slice(), best: load('loputon'), record: endless.over.record };
      act({ id: 'valikko' });
      return { a, b, ids, c, d, after: { mode, endless, level, board: leg.endless } }; }""")
    assert r["a"]["points"] == 40 and "2 km +20" in r["a"]["msgs"], r
    b = r["b"]
    assert b["mode"] == "crash" and b["sent"] == [40] and b["best"]["p"] == 40 and b["best"]["k"] == 1 and 2.0 <= b["best"]["km"] <= 2.2, r
    assert b["over"]["record"] is True, r
    assert r["ids"] == ["uudelleen", "valikko"], r
    assert r["c"] == {"mode": "drive", "k": 1, "points": 0, "s": 6}, r
    # A worse run is sent too, but the best stays.
    assert r["d"]["sent"] == [40, 5] and r["d"]["best"]["p"] == 40 and r["d"]["record"] is False, r
    assert r["after"]["mode"] == "menu" and r["after"]["endless"] is None and r["after"]["board"] is not True, r
    assert page.errors == []


def test_an_empty_tank_and_a_missed_turn_end_the_run(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; driven = 1; startEndless(977); road.turns = []; things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.broken = []; road.works = []; road.rail = [];
      P.s = 500; P.fuel = 0.002; let seen = [];
      for (let i = 0; i < 60 * 60 && mode === 'drive'; i++) { if (!P.dry) P.v = 13; P.lat = LANE; P.vl = 0; step(1 / 60);
        for (const m of msgs) if (!seen.includes(m.text)) seen.push(m.text); }
      return { mode, why: crashWhy, seen, over: !!endless.over }; }""")
    assert r["mode"] == "crash" and r["why"] == "Polttoaine loppui." and r["over"], r
    assert "Tankki vähissä: huoltoasema seuraavalla etapilla" in r["seen"], r
    r = page.evaluate("""() => { HOLD = true; startEndless(977); things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.broken = []; road.works = []; road.rail = []; const J = road.turns[0];
      P.s = J.a0 - 150; for (let i = 0; i < 60 * 40 && mode === 'drive'; i++) { P.v = 14; P.lat = LANE; P.vl = 0; input.left = input.right = false; step(1 / 60); }
      return { mode, why: crashWhy, over: !!endless.over }; }""")
    assert r["mode"] == "crash" and r["why"].startswith("Väärä tie") and r["over"], r
    assert page.errors == []


def test_the_careful_driver_gets_through_four_stages_filling_up_on_the_way(site, context):
    page = open_game(site, context)
    # A fixed run (seed 977): on random runs the bot sometimes misses a tractor behind a walker or
    # cuts in too soon after an overtake, as it would on the legs with other seeds.
    r = page.evaluate(ENDLESS_BOT, [4, 977])[0]
    assert r["mode"] == "drive" and r["k"] == 5, r
    # 12.8 km on a tank that lasts 12 km at 80: it filled up, and had coffee there.
    assert r["km"] > 12.5 and r["fuel"] > 0.5 and r["tired"] < 0.4 and r["tally"]["hurjastelu"] == 0, r
    assert page.errors == []


def test_the_menu_and_the_end_screen_fit_at_every_size(site, context):
    for w, h in ((360, 740), (360, 640), (390, 844), (740, 360)):
        page = open_game(site, context)
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_function(f"W === {w} && H === {h}")
        r = page.evaluate("""() => { driven = 1; btns = []; draw(); const box = id => { const b = btns.find(x => x.id === id); return b && [b.x, b.y, b.w, b.h]; };
          const m = { aja: box('aja'), lo: box('loputon'), ohj: box('ohjaus'), W, H };
          startEndless(); crash('Ajoit ojaan.'); btns = []; draw();
          return { m, end: btns.map(b => [b.id, b.x, b.y, b.w, b.h]) }; }""")
        m = r["m"]
        assert m["aja"][0] + m["aja"][2] < m["lo"][0] and m["lo"][0] + m["lo"][2] <= m["W"] and m["lo"][1] + m["lo"][3] <= m["H"], (w, h, r)
        assert m["lo"][1] > m["ohj"][1] + m["ohj"][3] or m["lo"][0] > m["ohj"][0] + m["ohj"][2], (w, h, r)
        ids = [e[0] for e in r["end"]]
        assert ids == ["uudelleen", "valikko"], (w, h, r)
        assert all(0 <= e[1] and e[1] + e[3] <= w and 0 <= e[2] and e[2] + e[4] <= h for e in r["end"]), (w, h, r)
        assert page.errors == []
        page.close()


def test_left_turn_crosses_the_opposing_lane_only_inside_the_junction(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD=true; maxLeg=11; const out=[];
      for(let n=3;n<=11;n++) {newLeg(n); for(const J of road.turns.filter(j=>j.dir<0)) {
        const early=[],outside=[]; for(let s=J.a0;s<=J.a1;s+=0.2) {
          const q=worldAt(s,LANE), dx=q[0]-J.x,dz=q[2]-J.z;
          const along=dx*J.fx+dz*J.fz, lat=dx*J.rx+dz*J.rz;
          if(lat<0 && lat>-EDGE && along<J.C-EDGE) early.push({along,lat});
          if(Math.abs(lat)>EDGE && Math.abs(along-J.C)>EDGE)outside.push({along,lat});
        } const e=worldAt(J.a1,LANE),endLane=(e[0]-J.x)*J.fx+(e[2]-J.z)*J.fz-J.C;
        out.push({n,early,outside,endLane});
      }} return out; }""")
    assert r and all(not x['early'] and not x['outside'] and 0 < x['endLane'] < 3.5 for x in r), r


def test_oncoming_traffic_keeps_priority_over_a_car_waiting_to_turn_left(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {HOLD=true;maxLeg=11;newLeg(5);const J=road.turns.find(j=>j.dir<0);
      P.s=J.a0+1;P.v=0; const t=add('risteava',{s:J.a0+J.C+15,lat:-LANE,v:-ARM_V,arm:J});
      for(let i=0;i<60;i++)crosser(t,1/60);
      return {s:t.s-J.a0,speed:-t.v,expected:J.C+15-ARM_V}; }""")
    assert abs(r['s']-r['expected']) < 0.01 and abs(r['speed']-50/3.6)<0.01,r


def test_the_car_stays_in_picture_through_a_compact_left_turn(site, context):
    page = open_game(site, context)
    for width,height in ((390,844),(740,360)):
        page.set_viewport_size({"width":width,"height":height})
        page.evaluate("() => {HOLD=true;maxLeg=11;newLeg(5);}")
        page.wait_for_function("!!V3")
        r=page.evaluate("""() => {const J=road.turns.find(j=>j.dir<0),out=[];P.lat=LANE;
          for(let s=J.a0-15;s<J.a1+15;s+=1) {P.s=s;draw3d(performance.now());
            out.push(screenOf(P.s,P.lat,1));}return {out,W,H};}""")
        assert all(q and 0.1*r['W']<q['x']<0.9*r['W'] and 0.1*r['H']<q['y']<0.9*r['H'] for q in r['out']), r


def test_a_thumb_turns_left_from_its_own_lane_through_the_junction(site, context):
    page = open_game(site, context)
    page.set_viewport_size({"width":390,"height":844})
    r=page.evaluate("""() => {HOLD=true;maxLeg=11;newLeg(5);setControls('yksi');
      things=[];events=[];road.cams=[];road.checks=[];road.holes=[];
      const J=road.turns.find(j=>j.dir<0);J.spawned=true;
      P.s=J.a0-6;P.v=14/KMH;P.lat=LANE;P.vl=0;draw();
      const home=stickHome(),box=c.getBoundingClientRect();
      const ev=(type,dx,dy)=>c.dispatchEvent(new PointerEvent(type,{pointerId:71,clientX:box.left+home.x+dx,clientY:box.top+home.y+dy,bubbles:true,cancelable:true}));
      ev('pointerdown',0,0);let minLat=LANE;
      for(let i=0;i<900 && mode==='drive' && P.s<J.a1+5;i++) {
        const strength=2.6+Math.min(P.v,25)*0.15;
        const steer=clamp((curveAt(P.s)*P.v*P.v*0.55-2*(P.lat-LANE)-0.8*P.vl)/strength,-1,1);
        ev('pointermove',Math.sign(steer)*Math.pow(Math.abs(steer),1/1.4)*STICK,8);
        step(1/60);minLat=Math.min(minLat,P.lat);
      }ev('pointerup',0,0);
      return {mode,why:crashWhy,wrong:!!P.wrong,done:J.done,s:P.s,end:J.a1,minLat,lat:P.lat};}""")
    assert r['mode']=='drive' and not r['wrong'] and r['done'] and r['s']>r['end'] and r['minLat']>0,r
