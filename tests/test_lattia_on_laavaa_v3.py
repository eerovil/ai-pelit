"""Lattia on laavaa v3 (#526; v2 #505, v1 #488): kids jumping from furniture to furniture over a lava floor, alone
against the computer's kids.

The rules are tested on fresh worlds built in the page (world.js and ai.js are plain functions),
the screen and the saves by playing the game itself. The game loads lib/three, so these tests are
`alone` and run on the AgentDeck host (scripts/host-tests.sh)."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/lattia-on-laavaa/v3/"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
KEY = "ai-pelit:lattia-on-laavaa:"
# A whole round of six computer kids in room `lv`: when each fell, and whether every piece sank.
SIM = """([lv, seed]) => {
  const players = [0, 1, 2, 3, 4, 5].map(i => ({ id: 'c' + i, name: 'c' + i, kind: 'cpu', col: i }));
  const w = newWorld(lv, players, seed);
  const br = w.kids.map((k, i) => cpuBrain(ROOMS[lv - 1].cpu, seed * 7 + i));
  while (!w.over && w.rt < 240) {
    if (w.ph === 'play') {
      const sol = solids(w, w.rt);
      w.kids.forEach((k, i) => {
        if (k.out || !cpuThink(w, k, br[i], STEP, sol) || !startShove(k)) return;
        const o = shoveTarget(w, k, k.face);
        if (o) { o.pushedAt = w.rt; applyPush(o, pushOf(k, o)); }
      });
    }
    stepWorld(w, STEP, w.kids);
    if (w.ph === 'play') for (const k of w.kids) if (inLava(w, k)) fall(w, k);
    decide(w);
  }
  return { over: w.over, rt: w.rt, outs: w.kids.filter(k => k.out).map(k => k.outRt).sort((a, b) => a - b),
           jumps: w.kids.reduce((n, k) => n + (k.jumps || 0), 0) };
}"""


def open_game(site, context, width=360, height=740):
    if not (site.games / "lattia-on-laavaa").exists():
        shutil.copytree(ROOT / "games" / "lattia-on-laavaa", site.games / "lattia-on-laavaa")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof mode !== 'undefined' && mode === 'menu'")
    return page


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'play' && world && world.ph === 'play'", timeout=8000)


def test_the_menu_opens_the_first_room_only_and_draws_in_3d(site, context):
    page = open_game(site, context)
    rooms = page.locator("#rooms button")
    assert rooms.count() == 4
    assert [rooms.nth(i).is_disabled() for i in range(4)] == [False, True, True, True]
    assert "🔒" in rooms.nth(2).inner_text()
    assert "Koko talo" in rooms.nth(3).inner_text()
    assert page.locator("#friends").is_visible()
    page.wait_for_function("window.L3D && L3D.build && !L3D.failed")
    assert page.errors == []


def test_pieces_sink_one_by_one_in_the_seeds_order_and_the_lava_rises(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const p = [{ id: 'a', name: 'a', kind: 'cpu' }];
      const a = newWorld(1, p, 5), b = newWorld(1, p, 5), c = newWorld(1, p, 6);
      const when = w => w.pieces.map(q => q.wobAt);
      const sorted = when(a).slice().sort((x, y) => x - y);
      const gaps = sorted.slice(1).map((t, i) => t - sorted[i]);
      // The floats are the same for the same seed and time, on every phone.
      const fa = JSON.stringify(floatsAt(a, 70)), fb = JSON.stringify(floatsAt(b, 70));
      return { same: JSON.stringify(when(a)) === JSON.stringify(when(b)), other: JSON.stringify(when(a)) !== JSON.stringify(when(c)),
               gaps: Math.min(...gaps), floats: fa === fb && floatsAt(a, 70).length > 0, none: floatsAt(a, a.floatAt - 0.1).length,
               lava: [lavaAt(0), lavaAt(19), lavaAt(50) > lavaAt(30), lavaAt(500)],
               sinks: a.pieces.every(q => topOf(q, q.sinkAt - 0.01) === q.h0 && topOf(q, q.sinkAt + 1) < q.h0 && Math.abs(q.sinkAt - q.wobAt - WOBBLE) < 1e-9) };
    }""")
    assert r["same"] and r["other"]
    assert r["gaps"] >= 2.2 - 1e-9
    assert r["floats"] and r["none"] == 0
    assert r["lava"][0] == r["lava"][1] == pytest.approx(0.02) and r["lava"][2] and r["lava"][3] == pytest.approx(0.45)
    assert r["sinks"]


def test_a_kid_standing_still_falls_once_its_piece_sinks_into_the_lava(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [{ id: 'a', name: 'a', kind: 'cpu' }], 3), k = w.kids[0];
      const p = w.pieces.find(q => Math.abs(q.x - k.x) < q.w / 2 && Math.abs(q.z - k.z) < q.d / 2);
      let wobbled = null;
      while (!k.out && w.rt < 200) {
        stepWorld(w, STEP, [k]);
        if (w.ph === 'play' && inLava(w, k)) fall(w, k);
        if (wobbled === null && w.rt > p.wobAt) wobbled = !k.out;
      }
      return { out: k.out, at: k.outRt, sinkAt: p.sinkAt, gone: p.sinkAt + (p.h0 + 0.1) / SINK_V, wobbled };
    }""")
    assert r["out"] and r["wobbled"]
    # Never before the piece starts sinking, and soon after it reaches the lava.
    assert r["sinkAt"] < r["at"] < r["gone"] + 0.5


def test_a_shove_pushes_the_kid_in_front_once_and_waits_for_its_cooldown(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [0, 1, 2].map(i => ({ id: 'k' + i, name: 'k' + i, kind: 'cpu' })), 1);
      w.ph = 'play'; w.rt = 5;
      const [a, b, c] = w.kids;
      Object.assign(a, { x: 0, z: 0, y: 0.5, face: 0 }); Object.assign(b, { x: 0.8, z: 0, y: 0.5 }); Object.assign(c, { x: -0.8, z: 0, y: 0.5 });
      const behind = shoveTarget(w, a, Math.PI / 2 * 2) === c, front = shoveTarget(w, a, 0) === b;
      const s1 = startShove(a), s2 = startShove(a);
      const imp = pushOf(a, b); b.pushedAt = w.rt; applyPush(b, imp);
      return { behind, front, s1, s2, cd: a.cd, away: b.vx > 0 && b.vy > 0 && b.stun > 0, again: shoveTarget(w, a, 0) };
    }""")
    assert r["behind"] and r["front"]
    assert r["s1"] is True and r["s2"] is False and r["cd"] == pytest.approx(1.5)
    assert r["away"] and r["again"] is None


# A kid alone on one piece, with nothing else in the room: [world, kid, piece].
ALONE_ON = """(kind) => {
  const w = newWorld(1, [{ id: 'a', name: 'a', kind: 'cpu' }, { id: 'b', name: 'b', kind: 'cpu' }], 1);
  w.ph = 'play'; w.rt = 5;
  const p = w.pieces.find(q => q.kind === kind), k = w.kids[0];
  Object.assign(k, { x: p.x, z: p.z, y: p.h0, ground: true, gpId: 'p' + p.i, vx: 0, vy: 0, vz: 0 });
  w.kids[1].out = true;
  return [w, k, p];
}"""


def test_a_shove_at_the_edge_of_a_small_piece_never_carries_the_shover_off(site, context):
    # Eero (#505): in v1 a shove always threw the shover off a small piece (its dash is ~1.65 m).
    page = open_game(site, context)
    r = page.evaluate("""(ALONE_ON) => {
      const res = [];
      for (const face of [0, Math.PI / 2, Math.PI, -Math.PI / 2, Math.PI / 4]) {
        const [w, k, p] = eval(ALONE_ON)('pouf');
        k.face = face;
        // Start near the edge it dashes towards, too.
        k.x = p.x + Math.cos(face) * 0.2; k.z = p.z + Math.sin(face) * 0.2;
        const started = startShove(k);
        for (let i = 0; i < 240; i++) { stepWorld(w, STEP, [k]); if (inLava(w, k)) fall(w, k); }
        res.push({ started, out: k.out, ground: k.ground, on: k.gpId === 'p' + p.i,
                   inside: Math.abs(k.x - p.x) <= p.w / 2 && Math.abs(k.z - p.z) <= p.d / 2 });
      }
      // In the air a shove pushes without the dash, which could only carry the shover off.
      let [w, k, p] = eval(ALONE_ON)('pouf');
      k.face = 0; k.ground = false; k.gpId = null; k.y = p.h0 + 1; k.vy = 0;
      const airStarted = startShove(k), airDash = k.dash;
      for (let i = 0; i < 30; i++) stepWorld(w, STEP, [k]);
      const air = { started: airStarted, dash: airDash, moved: Math.abs(k.x - p.x), shoves: k.shoves };
      // A jump pressed during the dash ends it: the shover lands back on its pouf.
      [w, k, p] = eval(ALONE_ON)('pouf');
      k.face = 0; startShove(k); stepWorld(w, STEP, [k]); k.jump = true;
      let left = false;
      for (let i = 0; i < 240; i++) { stepWorld(w, STEP, [k]); if (k.vy < 0) k.jump = false; if (!k.ground && i > 5) left = true; if (inLava(w, k)) fall(w, k); }
      const jumped = { left, out: k.out, on: k.gpId === 'p' + p.i };
      // Along pieces of the same height (Keittiö's counters, 0.2 m apart) the dash goes on.
      const w3 = newWorld(3, [{ id: 'a', name: 'a', kind: 'cpu' }, { id: 'b', name: 'b', kind: 'cpu' }], 1);
      w3.ph = 'play'; w3.rt = 5; w3.kids[1].out = true;
      const c1 = w3.pieces[0], k3 = w3.kids[0];
      Object.assign(k3, { x: c1.x + 0.6, z: c1.z, y: c1.h0, ground: true, gpId: 'p0', vx: 0, vy: 0, vz: 0, face: 0 });
      startShove(k3);
      for (let i = 0; i < 120; i++) stepWorld(w3, STEP, [k3]);
      return { res, air, jumped, along: { x: k3.x, on: k3.gpId, out: k3.out } };
    }""", ALONE_ON)
    for one in r["res"]:
        assert one == {"started": True, "out": False, "ground": True, "on": True, "inside": True}, r
    assert r["air"] == {"started": True, "dash": 0, "moved": pytest.approx(0, abs=0.05), "shoves": 1}, r
    assert r["jumped"] == {"left": True, "out": False, "on": True}, r
    assert r["along"]["on"] == "p1" and not r["along"]["out"], r


def test_a_shove_from_the_edge_still_pushes_the_kid_in_front(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const w = newWorld(1, [0, 1].map(i => ({ id: 'k' + i, name: 'k' + i, kind: 'cpu' })), 1);
      w.ph = 'play'; w.rt = 5;
      const p = w.pieces.find(q => q.kind === 'table'), [a, b] = w.kids;
      Object.assign(a, { x: p.x + p.w / 2 - 0.3, z: p.z, y: p.h0, ground: true, gpId: 'p' + p.i, face: 0 });
      Object.assign(b, { x: p.x + p.w / 2 + 0.5, z: p.z, y: p.h0, ground: false });
      const o = startShove(a) && shoveTarget(w, a, a.face);
      if (o) { o.pushedAt = w.rt; applyPush(o, pushOf(a, o)); }
      for (let i = 0; i < 60; i++) stepWorld(w, STEP, [a, b]);
      return { hit: o === b, flew: b.x - (p.x + p.w / 2 + 0.5), stays: a.ground && Math.abs(a.x - p.x) <= p.w / 2 };
    }""")
    assert r["hit"] and r["flew"] > 0.8 and r["stays"], r


def test_a_jump_that_falls_just_short_of_the_edge_climbs_up(site, context):
    # Eero (#505): a jump that lands a little short of a piece's edge climbs onto it.
    page = open_game(site, context)
    r = page.evaluate("""(ALONE_ON) => {
      const tryJump = (gap, stickOn, drop, vy = -1) => {
        const [w, k, p] = eval(ALONE_ON)('sofa');
        // In the air beside the sofa's right side, its feet `drop` below the top, moving at it.
        Object.assign(k, { x: p.x + p.w / 2 + gap, z: p.z, y: p.h0 - drop, ground: false, gpId: null, vx: stickOn ? -2 : 0, vy, vz: 0, ix: stickOn ? -1 : 0, iz: 0, jump: vy > 0, jumpHeld: vy > 0 });
        let peak = k.y;
        for (let i = 0; i < 60 && !k.out; i++) { stepWorld(w, STEP, [k]); peak = Math.max(peak, k.y); if (inLava(w, k)) fall(w, k); }
        return { up: !k.out && k.ground && k.gpId === 'p' + p.i, climbs: k.climbs, over: peak - p.h0 };
      };
      return { near: tryJump(0.25, true, 0.4), low: tryJump(0.25, true, 0.72), far: tryJump(0.9, true, 0.4), away: tryJump(0.25, false, 0.4), rising: tryJump(0.25, true, 0.4, 6) };
    }""", ALONE_ON)
    assert r["near"]["up"] and r["near"]["climbs"] == 1, r
    assert not r["low"]["up"] and not r["far"]["up"] and not r["away"]["up"], r
    # Still rising fast past a taller piece's side: no grab, the jump goes on.
    assert r["rising"]["climbs"] == 0 and r["rising"]["over"] > 0.2, r["rising"]


def test_a_sinking_piece_tips_over_as_it_goes_under(site, context):
    # Review finding (#488): the furniture tips, not only shakes. The tilt grows over the first
    # 1.5 s of sinking, and the 3D scene draws it.
    page = open_game(site, context)
    go(page)
    p = page.evaluate("""() => { const p = world.pieces[0];
      return [tipOf(p, p.sinkAt), tipOf(p, p.sinkAt + 0.5), tipOf(p, p.sinkAt + 1.5), tipOf(p, p.sinkAt + 4), p.sinkAt]; }""")
    assert p[0] == 0 and 0.1 < abs(p[1]) < abs(p[2]) and abs(p[2]) == pytest.approx(abs(p[3])) and abs(p[3]) > 0.35
    page.evaluate(f"() => {{ world.rt = {p[4]} + 1.2; }}")
    page.wait_for_function("(() => { const t = L3D.tilt(0); return t && Math.max(Math.abs(t[0]), Math.abs(t[1])) > 0.25; })()", timeout=5000)
    assert page.errors == []


@pytest.mark.parametrize("lv", [1, 2, 3])
def test_the_computer_kids_jump_about_and_every_round_ends(site, context, lv):
    page = open_game(site, context)
    for seed in (1, 2, 3):
        r = page.evaluate(SIM, [lv, seed])
        assert r["over"], (lv, seed, r["rt"])
        # Measured in v2 (#505) over rooms 1–3, seeds 1–4: the first fall at 42–71 s, half of the
        # kids out at 58 s or later (v1: 41 s), the last by 94 s, and the kids jump several times a
        # round. The bounds leave room for luck.
        outs = r["outs"]
        assert outs[len(outs) // 2] > 35, (lv, seed, outs)
        assert outs[-1] < 200, (lv, seed, outs)
        assert r["jumps"] >= 4, (lv, seed, r)


def test_the_stick_runs_my_kid_and_the_buttons_jump_and_shove(site, context):
    page = open_game(site, context)
    go(page)
    x0 = page.evaluate("me.x")
    page.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    page.evaluate(TOUCH, ["pointermove", 7, 150, 560])
    page.wait_for_function(f"me.x > {x0} + 0.3", timeout=3000)
    # A second finger on the jump button leaves the stick with the first one.
    b = page.evaluate("buttons()")
    page.evaluate(TOUCH, ["pointerup", 7, 150, 560])
    page.wait_for_function("me.ground")
    page.evaluate(TOUCH, ["pointerdown", 8, b["jump"]["x"], b["jump"]["y"]])
    page.wait_for_function("!me.ground && me.vy > 0", timeout=3000)
    page.evaluate(TOUCH, ["pointerup", 8, b["jump"]["x"], b["jump"]["y"]])
    page.evaluate(TOUCH, ["pointerdown", 9, b["shove"]["x"], b["shove"]["y"]])
    page.wait_for_function("me.shoves === 1 && me.cd > 0", timeout=3000)
    assert page.evaluate("stick") is None
    # A thumb on the right half that misses the buttons starts no stick (the stick is the left's).
    page.evaluate(TOUCH, ["pointerdown", 10, b["jump"]["x"], b["jump"]["y"] - 230])
    assert page.evaluate("stick") is None
    page.evaluate(TOUCH, ["pointerup", 10, b["jump"]["x"], b["jump"]["y"] - 230])
    assert page.errors == []


def test_a_solo_win_opens_the_next_room_and_the_time_is_the_score(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.sent = []; window.boards = []; AiPelitScores.submit = s => { sent.push(s); }; "
                  "AiPelitScores.board = id => { boards.push(id); }; }")
    go(page)
    # Every computer kid falls while mine stands: won, the next room opens at once.
    page.evaluate("() => { world.rt = 12.3; world.kids.filter(k => k !== me).forEach(k => fall(world, k)); }")
    page.wait_for_function("soloWon")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}auki'))") == 2
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}voitot'))") == 1
    # The round goes on until I fall; my time is sent to the room's list.
    page.evaluate("() => { world.rt = 20.47; fall(world, me); }")
    page.wait_for_function("mode === 'end'")
    assert page.evaluate("sent") == [205]
    assert "huone-1" in page.evaluate("boards")
    assert page.locator("#endTitle").inner_text() == "Voitit kierroksen!"
    assert "Lastenhuone" in page.locator("#endOpen").inner_text()
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}paras-1'))") == pytest.approx(20.5)
    assert page.locator("#endList li").count() == 6
    page.reload()
    page.wait_for_function("mode === 'menu'")
    rooms = page.locator("#rooms button")
    assert [rooms.nth(i).is_disabled() for i in range(4)] == [False, False, True, True]
    assert "Paras 0:20,5" in rooms.nth(0).inner_text()
    # A lost round: no room opens and the record stays.
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    go(page)
    page.evaluate("() => { world.rt = 4.2; fall(world, me); }")
    page.wait_for_function("mode === 'end'")
    assert page.locator("#endTitle").inner_text() == "Laavaan!"
    assert page.locator("#endOpen").is_hidden()
    assert page.evaluate("sent") == [42]
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}auki'))") == 2
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}paras-1'))") == pytest.approx(20.5)
    page.click("#again")
    page.wait_for_function("mode === 'play'")
    assert page.errors == []


def test_saves_from_before_are_read_and_kept(site, context):
    context.add_init_script(f"""localStorage.setItem('{KEY}auki', '3'); localStorage.setItem('{KEY}huone', '3');
      localStorage.setItem('{KEY}paras-2', '33.3'); localStorage.setItem('{KEY}voitot', '4');""")
    page = open_game(site, context)
    rooms = page.locator("#rooms button")
    assert [rooms.nth(i).is_disabled() for i in range(4)] == [False, False, False, True]
    assert "on" in rooms.nth(2).get_attribute("class")
    assert "0:33,3" in rooms.nth(1).inner_text()
    go(page)
    assert page.evaluate("world.level") == 3
    assert page.evaluate(f"localStorage.getItem('{KEY}voitot')") == "4"


@pytest.mark.parametrize("size", [{"width": 360, "height": 740}, {"width": 740, "height": 360}, {"width": 360, "height": 640}])
def test_the_menu_end_and_buttons_fit_upright_and_sideways(site, context, size):
    page = open_game(site, context, size["width"], size["height"])
    for sel in ("#go", "#friends", "#rooms button >> nth=3"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= size["height"], (sel, box)
    go(page)
    b = page.evaluate("buttons()")
    for k in ("jump", "shove"):
        x, y, r = b[k]["x"], b[k]["y"], b[k]["r"]
        assert r <= x <= size["width"] - r and r <= y <= size["height"] - r, (k, b[k])
    page.evaluate("() => { world.rt = 3; fall(world, me); }")
    page.wait_for_function("mode === 'end'")
    for sel in ("#endTitle", "#again", "#toMenu"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= size["height"], (sel, box)
    assert page.errors == []


def test_turning_the_phone_keeps_the_round(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { window.seed0 = world.seed; }")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND && W === 740")
    assert page.evaluate("mode === 'play' && world.seed === seed0 && !me.out")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!LAND && W === 360")
    assert page.evaluate("mode === 'play' && world.seed === seed0")
    assert page.errors == []
