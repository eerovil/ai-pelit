"""Seittisankari v3 (#529, #560): a masked hero who climbs skyscrapers and swings between them on a web,
in a city of about 1.7 km across. v1 is the free city and playing with friends (Eero's choice).

The movement is tested on heroes stepped in the page (world.js is plain functions), the screen and
the saves by playing the game itself. The game loads lib/three, so these tests are `alone` and run
on the AgentDeck host (scripts/host-tests.sh)."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/seittisankari/v4/"
KEY = "ai-pelit:seittisankari:"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""


def open_game(site, context, width=360, height=740):
    if not (site.games / "seittisankari").exists():
        shutil.copytree(ROOT / "games" / "seittisankari", site.games / "seittisankari")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof mode !== 'undefined' && mode === 'menu'")
    return page


def go(page):
    page.click("#free")
    page.wait_for_function("mode === 'play' && world && world.hero")


def test_the_menu_has_the_city_and_friends_and_draws_in_3d(site, context):
    page = open_game(site, context)
    assert page.locator("#free").inner_text() == "▶ Kaupunkiin"
    assert page.locator("#friends").is_visible()
    page.wait_for_function("window.L3D && L3D.ready && !L3D.failed", timeout=20000)
    assert page.errors == []


def test_the_city_is_big_with_the_old_downtown_and_its_tower_in_the_middle(site, context):
    page = open_game(site, context)
    n, edge, tower, xs = page.evaluate("""[CITY.length, EDGE, T_BOX.h,
        [Math.min(...CITY.map(b => b.x0)), Math.max(...CITY.map(b => b.x1))]]""")
    assert n > 1500 and edge > 800
    assert tower == 220 and page.evaluate("T_BOX === CITY.reduce((a, b) => b.h > a.h ? b : a)")
    assert xs[0] < -780 and xs[1] > 780
    # Every building stays inside its own lot, so looking up only the lots near a point finds it.
    assert page.evaluate("""CITY.every(b => lotOf((b.x0 + b.x1) / 2) === b.i && lotOf((b.z0 + b.z1) / 2) === b.j &&
        Math.max(Math.abs(b.x0 - lotX(b.i)), Math.abs(b.x1 - lotX(b.i)), Math.abs(b.z0 - lotX(b.j)), Math.abs(b.z1 - lotX(b.j))) <= 17)""")
    # The lot lookup gives the same roof as going through every building.
    assert page.evaluate("""(() => { const r = rng(3);
      for (let k = 0; k < 3000; k++) {
        const x = (r() - 0.5) * 2 * EDGE, z = (r() - 0.5) * 2 * EDGE, rad = r() * 2;
        let s = 0; for (const b of CITY) if (x > b.x0 - rad && x < b.x1 + rad && z > b.z0 - rad && z < b.z1 + rad && b.h > s) s = b.h;
        if (s !== supportAt(x, z, rad)) return [x, z];
      } return true; })()""") is True


def test_a_hero_runs_into_a_wall_grabs_it_and_climbs_onto_the_roof(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const b = BX(1, 0), h = newHero((b.x0 + b.x1) / 2, 0, b.z0 - 4, 0);   // facing +z, the wall ahead
      const seen = new Set(); let t = 0;
      while (t < 60 && !(h.st === 'ground' && h.y > 1)) { stepHero(h, { ix: 0, iy: -1, jump: false, web: false, yaw: 0 }, STEP); seen.add(h.st); t += STEP; }
      return { st: h.st, y: h.y, top: b.h, seen: [...seen], t, on: supportAt(h.x, h.z, 0) === b.h };
    })()""")
    assert "wall" in r["seen"]
    assert r["st"] == "ground" and r["y"] == r["top"] and r["on"]
    assert r["t"] < r["top"] / 6 + 3          # climbs at about 6 m/s


def test_the_web_sticks_high_in_the_sky_the_way_the_camera_looks(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 40, LX(2) + 20, 0); h.st = 'air';
      return [0, 1.5, 3].map(yaw => { const a = aimAnchor(h, Math.sin(yaw), Math.cos(yaw));
        return [a.y - h.y, Math.atan2(a.x - h.x, a.z - h.z) - yaw]; });
    })()""")
    for up, off in r:
        assert up > 150 and abs(off) < 1e-6
    # Far above every roof there is nothing to hang from.
    assert page.evaluate("aimAnchor(Object.assign(newHero(LX(2) + 20, 600, LX(2) + 20, 0), { st: 'air' }), 0, 1)") is None


def test_a_swing_keeps_the_falls_speed_and_makes_none_out_of_nothing(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 120, LX(2) + 20, 0); h.st = 'air'; h.vz = 8;
      const E = () => 0.5 * (h.vx * h.vx + h.vy * h.vy + h.vz * h.vz) + G * h.y;
      const inp = web => ({ ix: 0, iy: 0, jump: false, web, yaw: 0 });
      for (let i = 0; i < 120; i++) stepHero(h, inp(false), STEP);          // a second of falling
      const v0 = Math.hypot(h.vx, h.vy, h.vz), e0 = E();
      stepHero(h, inp(true), STEP);
      const swung = h.st === 'swing';
      let vMin = 99, eMax = -1e9;
      for (let i = 0; i < 240 && h.st === 'swing'; i++) {
        stepHero(h, inp(true), STEP);
        if (i < 30) vMin = Math.min(vMin, Math.hypot(h.vx, h.vy, h.vz));
        eMax = Math.max(eMax, E());
      }
      return { swung, v0, vMin, e0, eMax };
    })()""")
    assert r["swung"]
    assert r["vMin"] > r["v0"] * 0.6          # the web gives: no sudden stop at the catch
    assert r["eMax"] <= r["e0"] + 1           # no speed out of nothing


def test_a_new_web_keeps_the_momentum_of_the_last_swing(site, context):
    # Eero, #560: each new web keeps the speed from the swing before; it never resets.
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 130, LX(2) + 20, 0); h.st = 'air'; h.vz = 30; h.vy = 6;
      const inp = web => ({ ix: 0, iy: 0, jump: false, web, yaw: 0 });
      const v0 = Math.hypot(h.vx, h.vy, h.vz);
      stepHero(h, inp(true), STEP);
      const swung = h.st === 'swing';
      let vMin = 99;
      for (let i = 0; i < 24; i++) { stepHero(h, inp(true), STEP); vMin = Math.min(vMin, Math.hypot(h.vx, h.vy, h.vz)); }
      return { swung, v0, vMin };
    })()""")
    assert r["swung"]
    assert r["vMin"] > r["v0"] * 0.95, r      # the catch turns the speed, it does not brake it


def test_the_stick_web_and_jump_take_touches_and_a_second_thumb_beside_seitti_jumps(site, context):
    page = open_game(site, context)
    go(page)
    b = page.evaluate("buttons()")
    page.evaluate(TOUCH, ["pointerdown", 1, 90, 560])
    page.evaluate(TOUCH, ["pointermove", 1, 90, 500])
    assert page.evaluate("stickInput()[1]") < -0.9
    wx, wy = b["web"]["x"], b["web"]["y"]
    page.evaluate(TOUCH, ["pointerdown", 2, wx, wy])
    assert page.evaluate("webPtr") == 2
    # Right beside the held Seitti. Read jumpQ in the same task as the touch: the next frame
    # takes the jump and clears it, which a busy host reached between two evaluate calls.
    got = page.evaluate(f"(a) => {{ ({TOUCH})(a); return [jumpQ, webPtr]; }}", ["pointerdown", 3, wx - b["web"]["r"] - 8, wy])
    assert got == [True, 2]
    for i in (1, 2, 3):
        page.evaluate(TOUCH, ["pointerup", i, 0, 0])
    assert page.evaluate("[stick, webPtr]") == [None, None]
    assert page.errors == []


def test_the_hero_is_where_it_was_after_a_reload_and_the_hints_show_once(site, context):
    page = open_game(site, context)
    go(page)
    page.wait_for_function("hintT > 0 && hintT < 16")
    page.evaluate("() => { const h = world.hero; h.x = 300; h.z = -250; h.y = 0; h.st = 'ground'; hintT = 15.9; }")
    page.wait_for_function(f"localStorage.getItem('{KEY}ohje') === '1'")
    page.click("#quit")
    saved = page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}kierros2')).h")
    assert abs(saved["x"] - 300) < 3 and abs(saved["z"] + 250) < 3
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert abs(page.evaluate("world.hero.x") - 300) < 3 and abs(page.evaluate("world.hero.z") + 250) < 3
    assert page.evaluate("hintT") == 99
    assert page.errors == []


@pytest.mark.parametrize("size", [{"width": 360, "height": 740}, {"width": 740, "height": 360},
                                  {"width": 360, "height": 640}, {"width": 390, "height": 844}])
def test_the_menu_and_buttons_fit_upright_and_sideways(site, context, size):
    page = open_game(site, context, size["width"], size["height"])
    for sel in ("#free", "#friends"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= size["height"], (sel, box)
    go(page)
    b = page.evaluate("buttons()")
    for k in ("web", "jump", "pull"):
        x, y, r = b[k]["x"], b[k]["y"], b[k]["r"]
        assert r <= x <= size["width"] - r and r <= y <= size["height"] - r, (k, b[k])
    for k1, k2 in (("web", "jump"), ("web", "pull"), ("jump", "pull")):    # Veto (#560) overlaps neither
        p, q = b[k1], b[k2]
        assert ((p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2) ** 0.5 > p["r"] + q["r"] + 8, (k1, k2)
    assert page.errors == []


def test_turning_the_phone_keeps_the_hero(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { world.hero.x = 123; world.hero.z = 45; window.w0 = world; }")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND && W === 740")
    assert page.evaluate("mode === 'play' && world === w0")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!LAND && W === 360")
    assert page.evaluate("mode === 'play' && world === w0")
    assert page.errors == []


def angdiff(a, b):
    import math
    return (a - b + math.pi) % (2 * math.pi) - math.pi


ON_GOAL = """() => { const b = CITY[world.goal], h = world.hero;
  Object.assign(h, { x: (b.x0 + b.x1) / 2, y: b.h, z: (b.z0 + b.z1) / 2, vx: 0, vy: 0, vz: 0, st: 'ground', anchor: null }); }"""


def test_the_city_marks_a_roof_to_go_to_with_a_flag_and_tells_how_far(site, context):
    page = open_game(site, context)
    go(page)
    page.wait_for_function("CITY[world.goal]")
    r = page.evaluate("""(() => { const b = CITY[world.goal], h = world.hero, t = roofTop(b);
      return { d: Math.hypot(t.x - h.x, t.z - h.z), hgt: b.h, tower: !!b.tower, flag: world.flag && world.flag.x === t.x && world.flag.y === b.h }; })()""")
    assert 120 <= r["d"] <= 300 and 20 <= r["hgt"] <= 150 and not r["tower"] and r["flag"]
    # What the player reads: the goal and its distance, upright and sideways.
    page.evaluate("window.__said = []; const st = shadowText; shadowText = function (t) { __said.push(String(t)); return st.apply(this, arguments); }")
    for size in ({"width": 360, "height": 740}, {"width": 740, "height": 360}):
        turn(page, size)
        page.evaluate("__said.length = 0")
        page.wait_for_function("__said.some(t => /^Mene merkitylle katolle! \\d+ m$/.test(t))")
    # The arrow points at the roof as the camera looks: turn the camera, the arrow turns back.
    page.evaluate("window.__arrow = []; const da = drawArrow; drawArrow = function (x, y, a) { __arrow.push(a); return da.apply(this, arguments); }")
    for yaw in (0.0, 1.5):
        got = page.evaluate(f"""new Promise(ok => {{ cam.yaw = {yaw}; cam.manualT = 99; __arrow.length = 0;
          requestAnimationFrame(() => requestAnimationFrame(() => {{ const t = roofTop(CITY[world.goal]), h = world.hero;
            ok([__arrow[__arrow.length - 1], angDiff(cam.yaw, Math.atan2(t.x - h.x, t.z - h.z))]); }})); }})""")
        assert got[0] is not None and abs(angdiff(got[0], got[1])) < 0.05
    assert page.errors == []


# Finish the mission now: stand on its roof, or catch every crook.
FINISH = """() => { if (isCrook(world.kind)) world.crooks.forEach(catchCrook); else (""" + ON_GOAL + """)(); }"""


def test_the_missions_come_in_order_roof_robbers_car_tower_helicopter(site, context):
    # v4 (#561), the approved spec: a roof, robbers on a roof, a getaway car, the tower, a helicopter.
    page = open_game(site, context)
    go(page)
    page.wait_for_function("world.kind")
    seen = [page.evaluate("world.kind")]
    for n in range(1, 11):
        if seen[-1] == "auto":  # by the downtown, so the tower is near enough for its turn
            page.evaluate("const b = BX(1, 1); Object.assign(world.hero, { x: (b.x0 + b.x1) / 2, y: b.h, z: (b.z0 + b.z1) / 2, st: 'ground', vx: 0, vy: 0, vz: 0 })")
        page.evaluate(FINISH)
        page.wait_for_function(f"world.done === {n}")
        r = page.evaluate("""[world.kind, world.gt < 1, world.got && world.got.kind, !!CITY[world.goal] && !!CITY[world.goal].tower,
          world.crooks.length, !!world.flag]""")
        seen.append(r[0])
        assert r[1]                                                    # each new mission's clock starts at 0
        assert r[2] == seen[-2]                                        # "Perillä!", "Rosvot kiinni!", ...
        assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}tehtavat'))") == n
        if r[0] == "torni":
            assert r[3]
        if r[0] in ("katto", "torni", "rosvot"):
            assert r[5]                                                # the flag and its light mark the roof
        assert r[4] == {"rosvot": 3, "auto": 1, "heli": 1}.get(r[0], 0)
    assert seen == ["katto", "rosvot", "auto", "torni", "heli"] * 2 + ["katto"]
    # Over the roof after a swing, the close-by hint points down, not up.
    page.evaluate("const b = CITY[world.goal], t = roofTop(b); Object.assign(world.hero, { x: t.x, z: t.z, y: b.h + 30, st: 'air', vx: 0, vy: 0, vz: 0 })")
    page.evaluate("window.__said = []; const st = shadowText; shadowText = function (t) { __said.push(String(t)); return st.apply(this, arguments); }")
    page.wait_for_function("__said.some(t => /↓ \\d+ m$/.test(t))")
    assert page.errors == []


def test_the_marked_roof_and_the_count_survive_a_reload_and_v1s_save_still_opens(site, context):
    page = open_game(site, context)
    # v1 saved only the hero's spot: v2 opens it and marks a roof.
    page.evaluate(f"localStorage.setItem('{KEY}kierros', JSON.stringify({{ h: {{ x: 300, y: 0, z: -250, yaw: 0, st: 'air' }} }}))")
    go(page)
    page.wait_for_function("CITY[world.goal]")
    assert abs(page.evaluate("world.hero.x") - 300) < 3
    page.evaluate(ON_GOAL)
    page.wait_for_function("world.done === 1")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}tehtavat'))") == 1
    # v4: the second mission is robbers; on to the sixth, a roof again, to keep its roof.
    page.evaluate("world.done = 5; save('tehtavat', 5); startMission(world)")
    g = page.evaluate("world.goal")
    page.evaluate("world.gt = 42")
    page.click("#quit")
    # A cached v1 opened in between writes its own {h} under `kierros`: v2's round stays.
    page.evaluate(f"localStorage.setItem('{KEY}kierros', JSON.stringify({{ h: {{ x: -400, y: 0, z: 400, yaw: 0, st: 'air' }} }}))")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("[world.goal, world.done, world.kind]") == [g, 5, "katto"]
    assert 42 <= page.evaluate("world.gt") < 45     # the roof's clock goes on, not from 0
    assert page.evaluate("world.hero.x") > -300     # v2's own spot, not v1's
    assert page.errors == []


# ---- v3 (#560): Veto, a web shot where the player aims that pulls the hero there ----
# A hero on the street in front of BX(1, 0)'s south wall, facing it (+z).
FRONT = "const b = BX(1, 0), h = newHero((b.x0 + b.x1) / 2, 0, b.z0 - 6, 0);"
NONE = "({ ix: 0, iy: 0, jump: false, web: false, yaw: 0 })"
# Shoot `hit` this step, then step until the hero holds a wall or stands (or 5 s pass).
PULL = """const shoot = (h, hit) => { stepHero(h, Object.assign(""" + NONE + """, { pull: hit }), STEP);
  const seen = new Set([h.st]); let t = STEP;
  while (t < 5 && h.st !== 'wall' && h.st !== 'ground') { stepHero(h, """ + NONE + """, STEP); seen.add(h.st); t += STEP; }
  return { st: h.st, x: h.x, y: h.y, z: h.z, t, seen: [...seen] }; };"""


def test_a_web_shot_at_a_wall_pulls_the_hero_there_and_it_holds_on(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => {" + FRONT + PULL + """
      const hit = aimPull(h, 0, -0.6);                       // looking up at the wall ahead
      return { hit, end: shoot(h, hit), z0: b.z0 };
    })()""")
    hit, end = r["hit"], r["end"]
    assert hit["kind"] == "wall" and hit["nz"] == -1 and hit["y"] > 3
    assert "pull" in end["seen"] and end["st"] == "wall"
    assert abs(end["y"] - (hit["y"] - 1.4)) < 0.5 and abs(end["z"] - (r["z0"] - 0.4)) < 0.1
    assert end["t"] < 1.5                                      # 30 m/s


def test_the_web_shot_works_in_the_air_falling_and_while_swinging(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => {" + PULL + """
      const b = BX(1, 0), out = {};
      // Falling past the wall's middle.
      let h = newHero((b.x0 + b.x1) / 2, b.h * 0.7, b.z0 - 6, 0); h.st = 'air'; h.vy = -15;
      out.fall = shoot(h, aimPull(h, 0, -0.3));
      // Swinging: on the web, then shoot.
      h = newHero((b.x0 + b.x1) / 2, b.h * 0.7, b.z0 - 6, 0); h.st = 'air';
      stepHero(h, { ix: 0, iy: 0, jump: false, web: true, yaw: 0 }, STEP);
      out.swung = h.st;
      out.swing = shoot(h, aimPull(h, 0, -0.3));
      return out;
    })()""")
    assert r["swung"] == "swing"
    for k in ("fall", "swing"):
        assert r[k]["st"] == "wall" and "pull" in r[k]["seen"], (k, r[k])


def test_a_web_shot_at_a_roof_lands_the_hero_on_it(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => {" + PULL + """
      const b = BX(1, 0), h = newHero((b.x0 + b.x1) / 2, b.h + 20, b.z0 - 10, 0); h.st = 'air';
      const hit = aimPull(h, 0, 0.9);                        // looking down onto the roof
      return { hit, end: shoot(h, hit), on: supportAt(h.x, h.z, 0) === b.h, top: b.h };
    })()""")
    assert r["hit"]["kind"] == "roof"
    assert r["end"]["st"] == "ground" and r["end"]["y"] == r["top"] and r["on"]


def test_a_web_shot_down_from_a_roof_reaches_a_lower_wall(site, context):
    # Helper check on #562: the pull used to land back on the roof it started from.
    page = open_game(site, context)
    r = page.evaluate("(() => {" + PULL + """
      for (let i = -3; i <= 3; i++) for (let j = -3; j <= 3; j++) {
        const b = BX(i, j), c = BX(i, j + 1);
        if (!b || !c || c.h > b.h - 12 || c.z0 - b.z1 > 40) continue;
        const x = (Math.max(b.x0, c.x0) + Math.min(b.x1, c.x1)) / 2;
        if (!(x > b.x0 + 1 && x < b.x1 - 1 && x > c.x0 + 1 && x < c.x1 - 1)) continue;
        const h = newHero(x, b.h, b.z1 - 1, 0);
        for (let p = 0.1; p < 1.4; p += 0.05) {
          const hit = aimPull(h, 0, p);
          if (!hit || hit.kind !== 'wall' || CITY[hit.box] !== c) continue;
          return { found: true, hit, end: shoot(h, hit), roof: b.h, z0: c.z0 };
        }
      }
      return { found: false };
    })()""")
    assert r["found"]
    end = r["end"]
    assert end["st"] == "wall" and end["y"] < r["roof"] - 5, r
    assert abs(end["z"] - r["z0"]) < 1, r


def test_seitti_held_through_a_web_pull_needs_a_new_press_to_swing(site, context):
    # Helper check on #562: a Seitti press during the pull used to start a swing on arrival.
    page = open_game(site, context)
    r = page.evaluate("(() => {" + FRONT + """
      const hit = aimPull(h, 0, -0.6), held = { ix: 0, iy: 0, jump: false, web: true, yaw: 0 };
      stepHero(h, Object.assign(""" + NONE + """, { pull: hit }), STEP);
      for (let i = 0; i < 600 && h.st === 'pull'; i++) stepHero(h, held, STEP);
      const arrived = h.st;
      for (let i = 0; i < 30; i++) stepHero(h, held, STEP);
      return [arrived, h.st];
    })()""")
    assert r == ["wall", "wall"]


def test_a_wall_grab_ends_the_landing_slide(site, context):
    # Helper check on #562: a slide left over from a landing froze the stick after a climb.
    page = open_game(site, context)
    r = page.evaluate("(() => {" + FRONT + """
      h.slideT = 0.5; grabWall(h, b, 0, -1); return h.slideT;
    })()""")
    assert r == 0


def test_a_web_shot_at_the_sky_the_street_or_too_far_misses(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const b = BX(1, 0), h = newHero((b.x0 + b.x1) / 2, 0, b.z0 - 6, Math.PI);
      return {
        sky: aimPull(Object.assign(newHero(0, 400, 0, 0), { st: 'air' }), 0, -0.5),
        street: aimPull(Object.assign(newHero((b.x0 + b.x1) / 2, 30, b.z0 - 6, Math.PI), { st: 'air' }), Math.PI, 1.4),   // steeply down at the street
      };
    })()""")
    assert r["sky"] is None and r["street"] is None
    # Without a hit nothing changes: the hero is not pulled.
    st = page.evaluate("(() => {" + FRONT + """ h.vx = 3;
      stepHero(h, Object.assign(""" + NONE + """, { pull: null }), STEP); return [h.st, h.vx > 2]; })()""")
    assert st == ["ground", True]


def test_the_reach_is_60_metres(site, context):
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      // Straight along the camera's level line from far away: hit only within PULL_MAX.
      const b = BX(1, 0), x = (b.x0 + b.x1) / 2, out = [];
      for (const d of [20, 55, 65, 90]) {
        const h = newHero(x + 0.9, 0, b.z0 - d, 0);           // + AIM_SIDE: the ray starts over the right shoulder
        const r = aimRay(h, 0, 0), hit = aimPull(h, 0, 0);
        out.push([d, hit ? Math.hypot(hit.x - r.ox, hit.y - r.oy, hit.z - r.oz) : null, hit && hit.box === b.id]);
      }
      return { out, max: PULL_MAX };
    })()""")
    assert r["max"] == 60
    for d, dist, own in r["out"]:
        if dist is not None:
            assert dist <= 60
        if d <= 55:
            assert dist is not None
        if d >= 65:
            assert not own, (d, dist)


def test_hyppy_during_a_pull_lets_go_and_keeps_the_speed(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => {" + FRONT + """
      const hit = aimPull(h, 0, -0.6);
      stepHero(h, Object.assign(""" + NONE + """, { pull: hit }), STEP);
      for (let i = 0; i < 6; i++) stepHero(h, """ + NONE + """, STEP);
      const v0 = Math.hypot(h.vx, h.vy, h.vz), st0 = h.st;
      stepHero(h, Object.assign(""" + NONE + """, { jump: true }), STEP);
      return [st0, h.st, v0, Math.hypot(h.vx, h.vy, h.vz)];
    })()""")
    assert r[0] == "pull" and r[1] == "air"
    assert r[2] > 25 and r[3] > 25


def test_hyppy_while_hanging_on_the_web_jumps_off_upward(site, context):
    # Eero, #560: "voi hypätä kun roikkuu seitissä".
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 120, LX(2) + 20, 0); h.st = 'air'; h.vy = -12;
      stepHero(h, { ix: 0, iy: 0, jump: false, web: true, yaw: 0 }, STEP);
      const st0 = h.st, vy0 = h.vy;
      stepHero(h, { ix: 0, iy: 0, jump: true, web: true, yaw: 0 }, STEP);
      const st1 = h.st, vy1 = h.vy;
      // Seitti still held: no new swing until it is let go and pressed again.
      for (let i = 0; i < 10; i++) stepHero(h, { ix: 0, iy: 0, jump: false, web: true, yaw: 0 }, STEP);
      return { st0, st1, vy0, vy1, st2: h.st, jump: JUMP };
    })()""")
    assert r["st0"] == "swing" and r["st1"] == "air" and r["st2"] == "air"
    assert r["vy1"] >= r["jump"] - 0.5 and r["vy1"] > r["vy0"]


def test_holding_veto_aims_with_the_same_finger_and_lifting_it_shoots(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => { const b = BX(1, 0), h = world.hero;
      Object.assign(h, { x: (b.x0 + b.x1) / 2, y: 0, z: b.z0 - 6, vx: 0, vy: 0, vz: 0, st: 'ground', anchor: null, yaw: 0 });
      cam.yaw = 0; cam.pitch = 0.3; }""")
    b = page.evaluate("buttons()")
    x, y = b["pull"]["x"], b["pull"]["y"]
    page.evaluate(TOUCH, ["pointerdown", 4, x, y])
    assert page.evaluate("pullPtr && pullPtr.id") == 4
    # Slide up 150 px: the camera tilts to look up, past the plain drag's limit.
    for k in range(1, 16):
        page.evaluate(TOUCH, ["pointermove", 4, x, y - 10 * k])
    pitch = page.evaluate("cam.pitch")
    assert pitch < -0.35 and pitch >= -1.0
    page.wait_for_timeout(300)
    assert page.evaluate("cam.pitch") == pitch                 # the camera stays where the finger put it
    assert page.evaluate("!!aimPull(world.hero, cam.yaw, cam.pitch)")
    page.evaluate(TOUCH, ["pointerup", 4, x, y - 150])
    page.wait_for_function("world.hero.st === 'pull' || world.hero.st === 'wall'")
    page.wait_for_function("world.hero.st === 'wall'", timeout=5000)
    assert page.evaluate("[pullPtr, pullQ]") == [None, None]
    assert page.errors == []


def test_sliding_the_held_seitti_turns_the_camera_and_keeps_the_web(site, context):
    # Eero on #561: with Seitti held, moving the finger turns the camera, a bit like Veto.
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { cam.yaw = 0; cam.pitch = 0.3; }")
    b = page.evaluate("buttons()")
    x, y = b["web"]["x"], b["web"]["y"]
    page.evaluate(TOUCH, ["pointerdown", 6, x, y])
    assert page.evaluate("webPtr") == 6
    for k in range(1, 11):                                  # 100 px left and 50 px up
        page.evaluate(TOUCH, ["pointermove", 6, x - 10 * k, y - 5 * k])
    yaw, pitch = page.evaluate("[cam.yaw, cam.pitch]")
    assert abs(yaw - 0.8) < 0.01 and abs(pitch - 0.0) < 0.01
    assert page.evaluate("webPtr") == 6                     # the web is still held
    page.evaluate(TOUCH, ["pointerup", 6, x - 100, y - 50])
    assert page.evaluate("[webPtr, webAt]") == [None, None]
    assert page.errors == []


def test_a_thumb_beside_veto_on_the_left_half_is_the_stick(site, context):
    # #562 review: at 360 px Veto's 22 px margin reached into the stick's half and took the thumb.
    page = open_game(site, context)
    go(page)
    b = page.evaluate("buttons()")
    w = page.evaluate("W")
    p = b["pull"]
    x, y = p["x"] - p["r"] - 10, p["y"]                  # just outside Veto, in its old margin
    assert x < w / 2
    page.evaluate(TOUCH, ["pointerdown", 7, x, y])
    assert page.evaluate("[pullPtr, !!stick && stick.id]") == [None, 7]
    page.evaluate(TOUCH, ["pointerup", 7, x, y])
    # Veto itself still answers on its left part, and its margin on the right half too.
    page.evaluate(TOUCH, ["pointerdown", 8, p["x"] - p["r"] + 4, y])
    assert page.evaluate("pullPtr && pullPtr.id") == 8
    page.evaluate(TOUCH, ["pointerup", 8, 0, 0])
    assert p["x"] > w / 2                                  # just above Veto, in the right half
    page.evaluate(TOUCH, ["pointerdown", 9, p["x"], y - p["r"] - 10])
    assert page.evaluate("pullPtr && pullPtr.id") == 9
    assert page.errors == []


def test_a_web_shot_low_on_a_wall_grabs_the_wall(site, context):
    # #562 review: a hit under 1.4 m used to end standing on the street.
    page = open_game(site, context)
    r = page.evaluate("(() => {" + FRONT + PULL + """
      h.x += 0; const hit = { x: h.x, y: 0.8, z: b.z0, kind: 'wall', box: b.id, nx: 0, nz: -1 };
      return shoot(h, hit);
    })()""")
    assert r["st"] == "wall" and r["y"] > 0, r


def test_a_missed_shot_does_nothing_and_the_hero_keeps_running(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => { const h = world.hero; Object.assign(h, { x: 0, y: 400, z: 0, vx: 0, vy: 0, vz: 0, st: 'air', anchor: null });
      cam.yaw = 0; cam.pitch = -0.3; }""")
    b = page.evaluate("buttons()")
    got = page.evaluate(f"""(p) => {{ const T = {TOUCH}; T(['pointerdown', 4, p.x, p.y]); T(['pointerup', 4, p.x, p.y]);
      return [pullQ, !!missFx, world.hero.st]; }}""", b["pull"])
    assert got == [None, True, "air"]
    assert page.errors == []


def test_a_spot_saved_mid_pull_opens_as_a_fall_and_the_veto_hint_shows_once(site, context):
    page = open_game(site, context)
    page.evaluate(f"localStorage.setItem('{KEY}ohje', '1')")    # saw v1/v2's hints already
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("hintT") == 99 and page.evaluate("hint3T") < 9
    page.evaluate("""() => { const b = BX(1, 0), h = world.hero;
      Object.assign(h, { x: (b.x0 + b.x1) / 2, y: 0, z: b.z0 - 6, st: 'ground' });
      pullQ = aimPull(h, 0, -0.6); }""")
    page.wait_for_function("world.hero.st === 'pull'")
    page.evaluate("saveRound()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}kierros2')).h.st") == "air"
    page.evaluate("hint3T = 8.95")
    page.wait_for_function(f"localStorage.getItem('{KEY}ohje3') === '1'")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("hint3T") == 99
    assert page.evaluate("world.hero.st") in ("air", "ground", "wall")
    assert page.errors == []


def test_a_jump_goes_three_times_as_high_as_before(site, context):
    # Eero, #560: "yleinen hyppykorkeus ... kolme kertaa korkeampi" (v2: about 2 m).
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const top = start => { let m = 0; for (let i = 0; i < 600; i++) { stepHero(start, { ix: 0, iy: 0, jump: i === 0, web: false, yaw: 0 }, STEP); m = Math.max(m, start.y); if (start.st === 'ground' && i > 2) break; } return m; };
      const b = BX(1, 0), out = {};
      out.street = top(newHero(LX(2) + 20, 0, LX(2) + 20, 0));
      // Off a wall: push off it, up as high.
      const h = newHero((b.x0 + b.x1) / 2, 10, b.z0 - 0.4, 0); Object.assign(h, { st: 'wall', box: b, nx: 0, nz: -1 });
      out.wall = top(h) - 10;
      return out;
    })()""")
    v2 = 10.5 ** 2 / (2 * 28)
    assert 2.8 * v2 < r["street"] < 3.2 * v2, r
    assert r["wall"] > 2.8 * v2, r


def test_veto_on_a_wall_aims_straight_back_and_keeps_the_camera_out_of_the_building(site, context):
    # Eero, #560: pressing Veto while climbing put the camera inside the building.
    page = open_game(site, context)
    go(page)
    page.evaluate("""() => { const b = BX(1, 0), h = world.hero;
      Object.assign(h, { x: (b.x0 + b.x1) / 2, y: 12, z: b.z0 - 0.4, vx: 0, vy: 0, vz: 0, st: 'wall', box: b, nx: 0, nz: -1, anchor: null });
      cam.yaw = 0.3; cam.pitch = 0.5; }""")
    b = page.evaluate("buttons()")
    # Eero, #560: on a wall the aim turns straight back from it (the wall faces -z), level, and
    # the camera swings there instead of jumping: read in the same task as the touch.
    yaw0 = page.evaluate(f"(a) => {{ ({TOUCH})(a); return cam.yaw; }}", ["pointerdown", 4, b["pull"]["x"], b["pull"]["y"]])
    assert abs(angdiff(yaw0, 3.141592653589793)) > 2          # not turned yet
    page.wait_for_function("aimTurn === null", timeout=3000)
    yaw, pitch = page.evaluate("[cam.yaw, cam.pitch]")
    assert abs(angdiff(yaw, 3.141592653589793)) < 1e-6 and pitch == 0
    page.wait_for_timeout(800)
    c = page.evaluate("L3D.camAt()")
    assert page.evaluate("([x, y, z]) => !insideCity(x, y, z, 0.05)", c), c
    hit = page.evaluate("aimPull(world.hero, cam.yaw, cam.pitch)")
    assert hit and hit["box"] != page.evaluate("BX(1, 0).id")      # aims at the building across, not its own
    assert page.errors == []


def test_letting_go_of_the_web_always_jumps(site, context):
    # Eero, #560: "aina kun päästään irti seitistä, niin se hyppää automaattisesti" (with a backflip,
    # drawn in draw3d.js from the swing-to-air change).
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 120, LX(2) + 20, 0); h.st = 'air'; h.vy = -12;
      const inp = web => ({ ix: 0, iy: 0, jump: false, web, yaw: 0 });
      stepHero(h, inp(true), STEP);
      for (let i = 0; i < 30; i++) stepHero(h, inp(true), STEP);
      const st0 = h.st, vy0 = h.vy, jumped0 = h.jumped;
      stepHero(h, inp(false), STEP);
      return { st0, st1: h.st, vy0, vy1: h.vy, jumped: h.jumped && !jumped0, jump: JUMP, g: G, dt: STEP };
    })()""")
    assert r["st0"] == "swing" and r["st1"] == "air" and r["jumped"]
    assert r["vy1"] >= r["jump"] - r["g"] * r["dt"] - 1e-6
    assert r["vy1"] > r["vy0"]


def test_the_swing_web_waits_a_second_after_letting_go(site, context):
    # Eero, #560: "sekunnin cooldown", so pressing Seitti again and again cannot climb to the sky.
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const h = newHero(LX(2) + 20, 120, LX(2) + 20, 0); h.st = 'air';
      const inp = web => ({ ix: 0, iy: 0, jump: false, web, yaw: 0 });
      for (let i = 0; i < 30; i++) stepHero(h, inp(true), STEP);
      stepHero(h, inp(false), STEP);                       // let go: a jump
      const out = [];
      let t = 0;
      while (t < 1.3) {                                     // press every 0.1 s
        stepHero(h, inp(true), STEP); out.push([Math.round(t * 1000), h.st]);
        if (h.st === 'swing') break;
        stepHero(h, inp(false), STEP);
        for (let i = 0; i < 10; i++) stepHero(h, inp(false), STEP);
        t += 12 * STEP;
      }
      return out;
    })()""")
    early = [st for ms, st in r if ms < 950]
    assert early and all(st != "swing" for st in early), r
    assert r[-1][1] == "swing" and r[-1][0] < 1150, r


def test_a_fast_landing_keeps_its_speed_a_moment_and_a_jump_takes_it_along(site, context):
    # Eero, #560: landing from the web keeps the speed a short while on the ground, and a jump
    # straight away keeps it in the air.
    page = open_game(site, context)
    r = page.evaluate("""(() => {
      const fall = () => { const h = newHero(LX(2) + 20, 3, LX(2) + 20, 0); h.st = 'air'; h.vz = 25; h.vy = -5;
        let i = 0; while (h.st !== 'ground' && i++ < 200) stepHero(h, { ix: 0, iy: 0, jump: false, web: false, yaw: 0 }, STEP); return h; };
      const idle = { ix: 0, iy: 0, jump: false, web: false, yaw: 0 };
      const sp = h => Math.hypot(h.vx, h.vz);
      let h = fall(); const atLand = sp(h);
      for (let i = 0; i < 36; i++) stepHero(h, idle, STEP);      // 0.3 s on the ground, no stick
      const after03 = sp(h);
      for (let i = 0; i < 84; i++) stepHero(h, idle, STEP);      // 1 s: the slide is over
      const after1 = sp(h);
      h = fall();
      for (let i = 0; i < 24; i++) stepHero(h, idle, STEP);      // 0.2 s, then jump
      stepHero(h, Object.assign({}, idle, { jump: true }), STEP);
      const inAir = []; for (let i = 0; i < 60; i++) { stepHero(h, idle, STEP); inAir.push(h.st === 'air' ? sp(h) : null); }
      return { atLand, after03, after1, inAir };
    })()""")
    assert r["atLand"] > 20
    assert r["after03"] > 18          # still sliding
    assert r["after1"] < 2            # then stops without the stick, as before
    air = [v for v in r["inAir"] if v is not None]
    assert len(air) > 30 and min(air) > 18


# ---- v4 (#561): robbers on a roof, a getaway car and a getaway helicopter, caught with the web ----
# A world at mission `n` (0 = the first), started from the hero's spot by the tower with a fixed seed.
AT = """(n, seed) => { const w = newWorld(); w.done = n; const r = rng(seed || 7); startMission(w, r); return [w, r]; }"""


def test_the_robbers_walk_on_their_roof_and_three_web_hits_catch_them(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => { const [w, r] = (" + AT + """)(1);
      const b = CITY[w.crookBox], h = w.hero, t = roofTop(b);
      const out = { n: w.crooks.length, d: Math.hypot(t.x - h.x, t.z - h.z), hgt: b.h, flag: w.flag.x === t.x && w.flag.y === b.h };
      let off = 0, moved = 0; const x0 = w.crooks.map(k => k.x);
      for (let i = 0; i < 60 / STEP; i++) {
        stepRound(w, STEP, r);
        for (const k of w.crooks) if (k.y !== b.h || k.x < b.x0 || k.x > b.x1 || k.z < b.z0 || k.z > b.z1) off++;
      }
      moved = Math.min(...w.crooks.map((k, i) => Math.abs(k.x - x0[i])));
      catchCrook(w.crooks[0]); catchCrook(w.crooks[1]); stepRound(w, STEP, r);
      out.two = [w.done, w.kind];
      const third = w.crooks[2]; catchCrook(third); stepRound(w, STEP, r);
      Object.assign(out, { off, moved, three: [w.done, w.kind], gone: !!w.gone && w.gone.includes(third) });
      return out; })()""")
    assert r["n"] == 3 and 120 <= r["d"] <= 300 and 20 <= r["hgt"] <= 150 and r["flag"]
    assert r["off"] == 0 and r["moved"] > 0.5      # they walk about, never off the roof
    assert r["two"] == [1, "rosvot"]               # two caught is not yet done
    assert r["three"] == [2, "auto"] and r["gone"]


def test_the_getaway_car_drives_the_streets_and_one_web_hit_stops_it(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => { const [w, r] = (" + AT + """)(2);
      const k = w.crooks[0], h = w.hero;
      const out = { d0: Math.hypot(k.x - h.x, k.z - h.z), inside: 0, outside: 0, path: 0, turns: 0 };
      let px = k.x, pz = k.z, pyaw = k.yaw;
      for (let i = 0; i < 120 / STEP; i++) {
        stepRound(w, STEP, r);
        if (supportAt(k.x, k.z, 1.0) > 0) out.inside++;
        if (Math.abs(k.x) > EDGE || Math.abs(k.z) > EDGE) out.outside++;
        out.path += Math.hypot(k.x - px, k.z - pz); px = k.x; pz = k.z;
        if (k.yaw !== pyaw) { out.turns++; pyaw = k.yaw; }
      }
      catchCrook(k); stepRound(w, STEP, r);
      const done = [w.done, w.kind];
      for (let i = 0; i < 3 / STEP; i++) stepRound(w, STEP, r);
      const x1 = k.x, z1 = k.z;
      for (let i = 0; i < 2 / STEP; i++) stepRound(w, STEP, r);
      Object.assign(out, { done, still: x1 === k.x && z1 === k.z && k.v === 0, street: supportAt(k.x, k.z, 1.0) === 0 });
      return out; })()""")
    assert 150 <= r["d0"] <= 250
    assert r["inside"] == 0 and r["outside"] == 0          # on the streets, never in a building
    assert 19 * 120 < r["path"] < 21 * 120                 # 20 m/s
    assert r["turns"] >= 3
    assert r["done"] == [3, "torni"]                       # one hit is enough
    assert r["still"] and r["street"]                      # skidded to a stop on its street


def test_the_getaway_helicopter_flies_high_and_one_hit_brings_it_down(site, context):
    page = open_game(site, context)
    r = page.evaluate("(() => { const [w, r] = (" + AT + """)(4, 11);
      const k = w.crooks[0], h = w.hero;
      const out = { d0: Math.hypot(k.x - h.x, k.z - h.z), lo: 1e9, hi: -1e9, hit: 0, far: 0, path: 0 };
      let px = k.x, pz = k.z;
      for (let i = 0; i < 120 / STEP; i++) {
        stepRound(w, STEP, r);
        out.lo = Math.min(out.lo, k.y); out.hi = Math.max(out.hi, k.y);
        if (supportAt(k.x, k.z, 4) > k.y - 2) out.hit++;
        if (Math.abs(k.x) > 700 || Math.abs(k.z) > 700) out.far++;
        out.path += Math.hypot(k.x - px, k.z - pz); px = k.x; pz = k.z;
      }
      catchCrook(k); stepRound(w, STEP, r);
      out.done = [w.done, w.kind];
      for (let i = 0; i < 9 / STEP; i++) stepRound(w, STEP, r);
      out.down = k.y - supportAt(k.x, k.z, 3); out.shown = !!w.gone;
      return out; })()""")
    assert 140 <= r["d0"] <= 260
    assert r["lo"] >= 70 and r["hi"] <= 90 and r["hit"] == 0 and r["far"] == 0
    assert r["path"] > 800                                 # it keeps flying (15 m/s, with turns)
    assert r["done"] == [5, "katto"]
    assert r["down"] == 0 and r["shown"]                   # set down on what is under it, still seen


def test_aiming_at_a_robber_turns_the_ring_red_and_letting_go_catches_him(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate(f"localStorage.setItem('{KEY}ohje4', '{{}}')")
    page.evaluate("""() => { const b = BX(1, 0), h = world.hero;
      Object.assign(h, { x: (b.x0 + b.x1) / 2, y: 0, z: b.z0 - 14, vx: 0, vy: 0, vz: 0, st: 'ground', anchor: null, yaw: 0 });
      world.kind = 'rosvot'; world.goal = -1;
      const k = newRobber(b, rng(1)); Object.assign(k, { x: h.x, y: 0, z: b.z0 - 6, wait: 1e9 }); world.crooks = [k];
      window.__k = k; cam.yaw = 0; cam.manualT = 0;
      const r = aimRay(h, 0, 0); cam.pitch = Math.atan2(r.oy - CROOK_MID.rosvo, k.z - r.oz); }""")
    assert page.evaluate("aimCrook(world.hero, cam.yaw, cam.pitch, world.crooks) === __k")
    # 3 m to his side the aim goes past him to the wall behind.
    assert page.evaluate("""(() => { const k = __k, x = k.x; k.x += 3; const a = [aimCrook(world.hero, cam.yaw, cam.pitch, world.crooks), !!aimPull(world.hero, cam.yaw, cam.pitch)]; k.x = x; return a; })()""") == [None, True]
    b = page.evaluate("buttons()")["pull"]
    page.evaluate("() => { window.__ring = []; const sk = CanvasRenderingContext2D.prototype.stroke; CanvasRenderingContext2D.prototype.stroke = function () { __ring.push(this.strokeStyle); return sk.apply(this, arguments); }; }")
    page.evaluate(TOUCH, ["pointerdown", 4, b["x"], b["y"]])
    page.wait_for_function("__ring.includes('#ff4d4d')")
    page.evaluate("window.__said = []; const st = shadowText; shadowText = function (t) { __said.push(String(t)); return st.apply(this, arguments); }")
    page.wait_for_function("__said.some(t => /^Ota rosvot kiinni! 0\\/1 · ↑ 0 m$/.test(t))")
    got = page.evaluate(f"(a) => {{ ({TOUCH})(a); return [__k.caught, pullQ, world.hero.st, !!catchFx]; }}", ["pointerup", 4, b["x"], b["y"]])
    assert got == [True, None, "ground", True]           # caught, and the hero stays where he is
    page.wait_for_function("world.done === 1")
    assert page.errors == []


def test_a_robber_mission_left_open_starts_again_and_each_hint_shows_once(site, context):
    page = open_game(site, context)
    page.evaluate(f"""localStorage.setItem('{KEY}ohje', '1'); localStorage.setItem('{KEY}ohje3', '1');
      localStorage.setItem('{KEY}tehtavat', '2'); localStorage.setItem('{KEY}tehtava4', JSON.stringify({{ k: 'auto', gt: 30 }}))""")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("[world.kind, world.crooks.length, world.crooks[0].type, world.crooks[0].caught]") == ["auto", 1, "auto", False]
    assert page.evaluate("world.gt") >= 30
    page.evaluate("window.__said = []; const st = shadowText; shadowText = function (t) { __said.push(String(t)); return st.apply(this, arguments); }")
    page.wait_for_function("__said.includes('Karkuriauto pakenee kaduilla!')")
    page.wait_for_function("__said.some(t => /^Pysäytä karkuriauto! \\d+ m$/.test(t))")
    page.evaluate("hint4T = 6.95")
    page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}ohje4') || '{{}}').auto === 1")
    page.click("#quit")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}tehtava4')).k") == "auto"
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    page.evaluate("window.__said = []; const st = shadowText; shadowText = function (t) { __said.push(String(t)); return st.apply(this, arguments); }")
    page.wait_for_timeout(300)
    assert not page.evaluate("__said.includes('Karkuriauto pakenee kaduilla!')")
    # A saved kind that is not this mission's turn starts the clock from 0.
    page.click("#quit")
    page.evaluate(f"localStorage.setItem('{KEY}tehtava4', JSON.stringify({{ k: 'heli', gt: 30 }}))")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("world.kind") == "auto" and page.evaluate("world.gt") < 5
    page.wait_for_function("window.L3D && L3D.ready")
    assert page.errors == []
