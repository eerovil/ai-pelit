"""Yöajo v19 (#451 "Risteykseen ajaminen menee todella herkästi ojaan"): a crossroads turn pushes the
car wide smoothly with speed, the junction's drawn paving counts as road, and the turn pill and the
crash screen name the turn's own safe speed (30 km/h left, 50 right, less in bad weather)."""

from test_yoajo_v19 import open_game

# A human-like driver alone on leg n, held at `kmh` (0: the turn's own safe speed) from 140 m before
# turn number k. It keeps its lane but does not know the bend's push: in the bend it waits `react` s
# before it steers in, then steers by how far it is from its lane. Returns how it went.
DRIVE_TURN = """([n, k, kmh, react, weather]) => { HOLD = true; maxLeg = 11; newLeg(n); if (weather) leg.weather = weather;
  things = []; events = []; road.cams = []; road.checks = []; road.holes = []; road.bad = [];
  const J = road.turns[k]; J.spawned = true; P.s = J.a0 - 140; P.lat = LANE; P.vl = 0; P.tired = 0;
  const v = (kmh || turnSafe(J)) / KMH; let tIn = null, wide = 0;
  for (let i = 0; i < 60 * 60 && mode === 'drive' && P.s < J.a1 + 60; i++) {
    P.v = v; P.tired = 0;
    const inBend = P.s >= J.a0 && P.s <= J.a1;
    if (inBend && tIn === null) tIn = T;
    let s = clamp(-(P.lat - LANE) * 1.5 - P.vl * 0.3, -1, 1);
    if (P.s > J.a0 - 6 && P.s < J.a0 + TURN_EASE) s = J.dir;          // into the turn, as the bot does
    if (tIn !== null && T - tIn < react && P.s < J.a1) s = J.dir * 0.3;   // late to steer properly
    input.steer = s; input.gas = 0; input.brake = 0;
    step(1 / 60);
    if (inBend) wide = Math.max(wide, (P.lat - LANE) * -J.dir);
  }
  return { mode, why: crashWhy, done: J.done, wrong: !!P.wrong, dir: J.dir, safe: turnSafe(J), wide, weather: leg.weather }; }"""

TURNS = """() => { HOLD = true; maxLeg = 11; const out = [];
  for (let n = 3; n <= 8; n++) { newLeg(n); road.turns.forEach((J, k) => out.push([n, k, J.dir, leg.weather])); }
  mode = 'menu'; return out; }"""


def test_every_crossroads_turn_is_made_at_its_safe_speed_by_a_driver_half_a_second_late(site, context):
    page = open_game(site, context)
    turns = page.evaluate(TURNS)
    assert {d for _, _, d, _ in turns} == {1, -1}, turns
    for n, k, d, w in turns:
        r = page.evaluate(DRIVE_TURN, [n, k, 0, 0.4, None])
        assert r["mode"] == "drive" and r["done"] and not r["wrong"], (n, k, r)
        assert r["safe"] == {(-1, "kuiva"): 30, (-1, "sade"): 30, (-1, "lumi"): 25, (-1, "pyry"): 25,
                             (1, "kuiva"): 50, (1, "sade"): 50, (1, "lumi"): 45, (1, "pyry"): 40}[(d, w)], (n, k, r)
    assert page.errors == []


def test_a_dry_left_turn_forgives_a_little_too_fast_but_not_much_too_fast(site, context):
    page = open_game(site, context)
    left = next((n, k) for n, k, d, _ in page.evaluate(TURNS) if d < 0)
    # 35 km/h, above the advised 30: made, wide on the paving at most.
    r = page.evaluate(DRIVE_TURN, [*left, 35, 0.4, "kuiva"])
    assert r["mode"] == "drive" and r["done"], r
    # 50 km/h: in the ditch, and the message names the left turn.
    r = page.evaluate(DRIVE_TURN, [*left, 50, 0.4, "kuiva"])
    assert r["mode"] == "crash" and r["why"] == "Ajoit ojaan: liian lujaa vasempaan käännökseen.", r
    # The crash screen's tip names its speed (v14–v18: "alle 40" for every crossroads).
    seen = page.evaluate("""() => { const out = []; const f = text; text = (t, ...a) => { out.push(t); return f(t, ...a); };
      draw(); text = f; return out; }""")
    assert "Hidasta vasempaan käännökseen" in seen and "alle 30 km/h." in seen, seen
    assert page.errors == []


def test_the_junction_paving_is_road_but_off_it_is_the_ditch(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; newLeg(5); things = []; events = [];
      const J = road.turns.find(j => j.dir < 0); J.spawned = true; J.done = true; P.into = true;
      const at = (s, lat) => { mode = 'drive'; crashWhy = ''; P.s = s; P.lat = lat; P.vl = 0; P.v = 20 / KMH;
        input.steer = 0; input.gas = 0; input.brake = 0; const v0 = P.v; step(1 / 60);
        return { mode, why: crashWhy, slowed: v0 - P.v }; };
      const mid = (J.a0 + J.a1) / 2;
      return { paving: onJunction(mid, 7), on: at(mid, 7), lane: at(mid, LANE), past: at(J.a1 + 60, 7) }; }""")
    assert r["paving"] and r["on"]["mode"] == "drive", r
    # Not slowed as on gravel: no more than in its own lane.
    assert abs(r["on"]["slowed"] - r["lane"]["slowed"]) < 1e-6, r
    assert r["past"]["mode"] == "crash" and r["past"]["why"].startswith("Ajoit ojaan"), r
    assert page.errors == []


def test_the_turn_pill_shows_the_safe_speed_on_the_way_in(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; const out = {};
      for (const w of ['kuiva', 'pyry']) { newLeg(5); leg.weather = w; things = []; events = [];
        const J = road.turns.find(j => j.dir < 0); P.s = J.a0 - 450;
        const seen = [], f = fitText; fitText = (t, ...a) => { seen.push(t); return f(t, ...a); };
        draw(); fitText = f; out[w] = seen.filter(t => t.startsWith('Käänny')); }
      return out; }""")
    assert r["kuiva"] == ["Käänny vasemmalle 450 m · alle 30"], r
    assert r["pyry"] == ["Käänny vasemmalle 450 m · alle 25"], r
    assert page.errors == []


def test_running_wide_off_the_paving_after_the_bend_still_names_the_turn(site, context):
    # Seen while taking screenshots: the paving let the car run wide past the bend's end, and the
    # ditch there said only "Ajoit ojaan." with no speed tip.
    page = open_game(site, context)
    r = page.evaluate("""() => { HOLD = true; maxLeg = 11; newLeg(5); leg.weather = 'kuiva'; things = []; events = [];
      const J = road.turns.find(j => j.dir < 0); J.spawned = true; J.done = true; P.into = true;
      P.s = J.a1 + 20; P.lat = 9; P.vl = 3; P.v = 45 / KMH; input.steer = 0; input.gas = 0; input.brake = 0;
      for (let i = 0; i < 600 && mode === 'drive'; i++) step(1 / 60);
      return { mode, why: crashWhy, s: P.s - J.a1, turn: crashTurn }; }""")
    assert r["mode"] == "crash" and r["why"] == "Ajoit ojaan: liian lujaa vasempaan käännökseen.", r
    assert r["turn"] == {"way": "vasen", "safe": 30}, r
    assert page.errors == []
