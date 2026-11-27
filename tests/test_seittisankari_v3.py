"""Seittisankari v2 (#529): a masked hero who climbs skyscrapers and swings between them on a web,
in a city of about 1.7 km across. v1 is the free city and playing with friends (Eero's choice).

The movement is tested on heroes stepped in the page (world.js is plain functions), the screen and
the saves by playing the game itself. The game loads lib/three, so these tests are `alone` and run
on the AgentDeck host (scripts/host-tests.sh)."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/seittisankari/v3/"
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
    for k in ("web", "jump"):
        x, y, r = b[k]["x"], b[k]["y"], b[k]["r"]
        assert r <= x <= size["width"] - r and r <= y <= size["height"] - r, (k, b[k])
    assert page.evaluate("Math.hypot(buttons().web.x - buttons().jump.x, buttons().web.y - buttons().jump.y)") > b["web"]["r"] + b["jump"]["r"]
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


def test_standing_on_the_roof_counts_it_and_every_fifth_is_the_tower(site, context):
    page = open_game(site, context)
    go(page)
    page.wait_for_function("CITY[world.goal]")
    seen = []
    for n in range(1, 6):
        if n == 4:  # end the fourth downtown, so the tower is near enough to be the fifth
            page.evaluate("setGoal(world, BX(1, 1).id)")
        g0 = page.evaluate("world.goal")
        page.evaluate(ON_GOAL)
        page.wait_for_function(f"world.done === {n} && world.goal !== {g0}")
        seen.append(page.evaluate("[!!CITY[world.goal].tower, world.gt < 1, !!world.got && world.got.tower]"))
        assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}tehtavat'))") == n
    # After the fourth roof the fifth target is the tower; after it, a roof again.
    assert [s[0] for s in seen] == [False, False, False, True, False]
    assert all(s[1] for s in seen)                                   # each new roof's clock starts at 0
    assert [s[2] for s in seen] == [False, False, False, False, True]  # "Tornin huipulla!"
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
    g = page.evaluate("world.goal")
    page.evaluate("world.gt = 42")
    page.click("#quit")
    # A cached v1 opened in between writes its own {h} under `kierros`: v2's round stays.
    page.evaluate(f"localStorage.setItem('{KEY}kierros', JSON.stringify({{ h: {{ x: -400, y: 0, z: 400, yaw: 0, st: 'air' }} }}))")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    go(page)
    assert page.evaluate("[world.goal, world.done]") == [g, 1]
    assert 42 <= page.evaluate("world.gt") < 45     # the roof's clock goes on, not from 0
    assert page.evaluate("world.hero.x") > -300     # v2's own spot, not v1's
    assert page.errors == []
