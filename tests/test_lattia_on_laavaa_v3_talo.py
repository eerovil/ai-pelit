"""Lattia on laavaa v3 (#526): Koko talo, one round up the stairs to the upstairs room, the roof,
and the things drifting on the lava sea. The rules on worlds built in the page, then the room
played. Loads lib/three, so `alone` (scripts/host-tests.sh)."""
import pytest

from test_lattia_on_laavaa_v3 import KEY, go, open_game

# One kid alone in Koko talo at rt, standing at (x, y, z); steps it `secs` seconds with the stick
# at (ix, iz) and the jump button `jump`, and returns the highest and the last place it was.
WALK = """([rt, x, y, z, ix, iz, jump, secs]) => {
  const w = newWorld(HOUSE_LV, [{ id: 'a', name: 'a', kind: 'me', col: 0 }], 5);
  const k = w.kids[0];
  w.ph = 'play'; w.rt = rt; Object.assign(k, { x, y, z, vx: 0, vy: 0, vz: 0, ground: false });
  let top = -9, near = 9;
  for (let t = 0; t < secs; t += STEP) {
    k.ix = ix; k.iz = iz; k.jump = jump;
    stepWorld(w, STEP, w.kids); top = Math.max(top, k.y); if (k.y > -0.05) near = Math.min(near, k.z);
  }
  return { top, near, x: k.x, y: k.y, z: k.z, ground: k.ground };
}"""
# A whole Koko talo round of six computer kids: when each fell and the highest each got.
SIM = """(seed) => {
  const players = [0, 1, 2, 3, 4, 5].map(i => ({ id: 'c' + i, name: 'c' + i, kind: 'cpu', col: i }));
  const w = newWorld(HOUSE_LV, players, seed);
  const br = w.kids.map((k, i) => cpuBrain(ROOMS[HOUSE_LV - 1].cpu, seed * 7 + i));
  const top = w.kids.map(() => 0);
  while (!w.over && w.rt < 400) {
    if (w.ph === 'play') {
      const sol = solids(w, w.rt);
      w.kids.forEach((k, i) => {
        if (k.out || !cpuThink(w, k, br[i], STEP, sol) || !startShove(k)) return;
        const o = shoveTarget(w, k, k.face);
        if (o) { o.pushedAt = w.rt; applyPush(o, pushOf(k, o)); }
      });
    }
    stepWorld(w, STEP, w.kids);
    w.kids.forEach((k, i) => { if (!k.out) top[i] = Math.max(top[i], k.y); });
    if (w.ph === 'play') for (const k of w.kids) if (inLava(w, k)) fall(w, k);
    decide(w);
  }
  return { over: w.over, rt: w.rt, outs: w.kids.map(k => k.outRt).sort((a, b) => a - b), top };
}"""


def test_the_lava_climbs_the_house_in_stages_and_the_rooms_keep_theirs(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const h = newWorld(HOUSE_LV, [], 1), o = newWorld(1, [], 1);
      return { h: [10, 39.9, 58, 77, 99, 118, 137, 160].map(t => lavaAt(t, h)), o: [10, 30, 200].map(t => lavaAt(t, o)),
               name: ROOMS[HOUSE_LV - 1].name, lv: HOUSE_LV, statics: [1, 2, 3].map(n => newWorld(n, [], 1).statics.length),
               kept: newWorld(HOUSE_LV, [], 1).pieces.filter(p => p.order >= 3 && p.floor < 2).map(p => [p.floor, p.wobAt]),
               bots: [1, 2, 3].every(n => solids(newWorld(n, [], 4), 5).every(s => s.bot === 0)) }; }""")
    assert r["lv"] == 4 and r["name"] == "Koko talo"
    h = r["h"]
    assert h[0] == pytest.approx(0.02)
    assert h[1] == pytest.approx(0.12, abs=0.01)
    assert 1.2 < h[2] < 1.8          # halfway up the first staircase
    assert 3.0 <= h[3] < 3.1         # the upstairs floor is lava by about 76 s
    assert 3.0 < h[4] < 3.2          # and creeps there until 100 s
    assert 4.2 < h[5] < 4.8
    assert 6.0 <= h[6] < 6.1         # the roof by about 136 s
    assert 6.0 < h[7] < 6.3
    # The three rooms: the same lava as v2, no steps or floors, every solid from the floor up.
    assert r["o"] == pytest.approx([0.02, 0.045, 0.45])
    assert r["statics"] == [0, 0, 0]
    assert r["bots"]
    # The pieces on the way to the stairs wobble and sink too, in a later turn once the lava climbs.
    assert all(w >= (42 if f == 0 else 102) and w < 200 for f, w in r["kept"]), r["kept"]
    assert page.errors == []


def test_a_kid_walks_up_the_stairs_once_the_door_is_open(site, context):
    page = open_game(site, context)
    # On the pouf in front of the first staircase's door, walking up the screen (to the back).
    up = page.evaluate(WALK, [36, -6.35, 0.45, 4.1, 0, -1, False, 5])
    assert up["y"] == pytest.approx(3.0, abs=0.02) and up["z"] < -3.6 and up["ground"], up
    # Before 35 s the door is shut.
    shut = page.evaluate(WALK, [20, -6.35, 0.45, 4.1, 0, -1, False, 3])
    # It walks off the pouf into the lava in front of the door, never through it.
    assert shut["near"] > 3.1 and shut["top"] < 0.5, shut
    # The second staircase, upstairs, opens at 95 s.
    up2 = page.evaluate(WALK, [96, 6.35, 3.45, 4.1, 0, -1, False, 5])
    assert up2["y"] == pytest.approx(6.0, abs=0.02) and up2["z"] < -3.6, up2
    assert page.errors == []


def test_the_floor_above_stops_a_jump_and_never_pushes_a_kid_aside(site, context):
    page = open_game(site, context)
    # Under the upstairs floor (its bottom at 2.8 m): a jump stops at the ceiling.
    j = page.evaluate(WALK, [5, -2.2, 0.5, 1.0, 0, 0, True, 1.2])
    assert j["top"] <= 2.8 - 1.0 + 0.01, j
    assert j["top"] > 1.2, j
    # Running along under it, nothing stops the kid.
    run = page.evaluate(WALK, [5, -2.2, 0.5, 1.0, 1, 0, False, 0.3])
    assert run["x"] > -1.6, run
    assert page.errors == []


def test_things_drift_on_the_lava_sea_the_same_for_the_same_seed(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { const a = newWorld(HOUSE_LV, [], 9), b = newWorld(HOUSE_LV, [], 9);
      const fa = floatsAt(a, 150), fb = floatsAt(b, 150), L = lavaAt(150, a);
      return { same: JSON.stringify(fa) === JSON.stringify(fb), n: fa.length, none: floatsAt(a, 134).length,
               kinds: [...new Set(Array.from({ length: 60 }, (_, k) => floatOf(a, k).kind))].sort(),
               ride: fa.every(f => Math.abs(f.top - (L + 0.18)) < 0.4) }; }""")
    assert r["same"] and r["n"] > 0 and r["none"] == 0
    assert r["kinds"] == ["bigcushion", "boat", "door", "log", "raft"]
    assert r["ride"]
    assert page.errors == []


def test_the_computer_kids_climb_to_the_upstairs_room(site, context):
    page = open_game(site, context)
    for seed in (1, 2, 3):
        r = page.evaluate(SIM, seed)
        assert r["over"], (seed, r["rt"])
        # Some of the six get upstairs, and the round goes on past the first climb.
        assert sum(t > 2.9 for t in r["top"]) >= 1, (seed, r)
        assert r["outs"][-1] > 80, (seed, r)
    assert page.errors == []


def test_a_kitchen_win_opens_koko_talo_and_it_plays(site, context):
    context.add_init_script(f"if (!localStorage.getItem('{KEY}auki')) {{ localStorage.setItem('{KEY}auki', '3'); localStorage.setItem('{KEY}huone', '3'); }}")
    page = open_game(site, context)
    rooms = page.locator("#rooms button")
    assert rooms.nth(3).is_disabled()
    page.evaluate("() => { AiPelitScores.submit = () => {}; }")
    go(page)
    page.evaluate("() => { world.rt = 12.3; world.kids.filter(k => k !== me).forEach(k => fall(world, k)); }")
    page.wait_for_function("soloWon")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}auki'))") == 4
    page.evaluate("() => { world.rt = 20; fall(world, me); }")
    page.wait_for_function("mode === 'end'")
    assert "Koko talo" in page.locator("#endOpen").inner_text()
    page.reload()
    page.wait_for_function("mode === 'menu'")
    rooms = page.locator("#rooms button")
    assert not rooms.nth(3).is_disabled()
    rooms.nth(3).click()
    go(page)
    assert page.evaluate("world.level === 4 && world.house && world.statics.length > 0")
    # The camera follows the kid up: placed upstairs, the floors above are cut away from 5.8 m.
    page.wait_for_function("L3D.cutY === 2.8")
    page.evaluate("() => { world.rt = 60; Object.assign(me, { x: 0, z: 2, y: 3.0, vy: 0, ground: true }); }")
    page.wait_for_function("L3D.cutY > 5.7 && L3D.cutY < 5.9", timeout=5000)
    assert page.errors == []
