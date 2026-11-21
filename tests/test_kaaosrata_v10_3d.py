"""Kaaosrata v10 (#493): the race drawn in 3D behind the runner, and courses with heights (ramps, steps to jump
onto, drops to lower floors, stepping stones at rising heights). A phone without WebGL plays on the 2D drawing."""
import io

from PIL import Image

from conftest import ROOT

URL = 'games/kaaosrata/v10/'


def open_game(site, context):
    site.build(ROOT / 'games')
    page = context.new_page()
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    return page


# A solo race on a course, the computer's runners parked out of the way, the clock running.
SOLO = '''(id) => { useCourse(id); soloRace(); race.phase = 'run'; race.clock = 1;
  race.runners.forEach(r => { if (r !== me) Object.assign(r, { kind: 'net', x: -4.5, y: -3, vx: 0, vy: 0 }); }); }'''
# Put this phone's runner standing at (x, y), then run `n` frames with the stick pushed up (and a jump on frame `jump`).
RUN = '''([x, y, n, jump]) => { input.x = 0; input.y = 0;
  Object.assign(me, { x, y, z: baseAt(x, y), gx: x, gy: y, vx: 0, vy: 0, vz: 0, stun: 0, cd: 0, fall: 0, coyote: 0.1 });
  const zs = [];
  for (let i = 0; i < n; i++) { input.y = 1; if (i === jump) press(); tick(1 / 60); zs.push([me.y, me.z]); }
  return { y: me.y, z: me.z, fall: me.fall, falls: me.falls || 0, zs }; }'''


def test_every_course_has_ramps_steps_drops_and_rising_stones(site, context):
    """Eero picked heights on all four courses, of four kinds. Every course has ramps, steps and drops; the three
    with stepping stones (Hihnatehdas has none, as in v8) set them at rising heights."""
    page = open_game(site, context)
    kinds = page.evaluate('''() => RADAT.map(c => { useCourse(c.id);
      const all = FLOORS.concat(BELTS, TILES), top0 = f => f.h || 0, top1 = f => f.h1 ?? (f.h || 0);
      let up = 0, down = 0;
      // Where one surface ends and the next (up the course, overlapping across) begins within a jump.
      for (const a of all) for (const b of all) if (b.y0 >= a.y1 && b.y0 - a.y1 < 3 && b.x0 < a.x1 && a.x0 < b.x1) {
        const d = top0(b) - top1(a);
        if (d > STEP) up++; if (d < -STEP) down++;
      }
      const stones = FLOORS.filter(f => f.stone).map(top0);
      return { id: c.id, ramps: all.filter(f => f.h1 !== undefined).length, up, down,
               stones: new Set(stones).size, board: c.board }; })''')
    for k in kinds:
        assert k['ramps'] >= 1 and k['up'] >= 1 and k['down'] >= 1, k
        assert k['stones'] >= (0 if k['id'] == 'hihna' else 2), k
        assert k['board'] == k['id'] + '10', k
    page.evaluate("useCourse('main')")
    assert page.errors == []


def test_moving_ground_sits_at_the_height_of_its_neighbours(site, context):
    """The design's data rules, on every course: a belt is as high as any floor under it, and the sliding
    platform and each spinning disc are within a walkable step (STEP) of the surfaces just before and after them,
    so moving ground never hides a wall or a drop."""
    page = open_game(site, context)
    bad = page.evaluate('''() => { const bad = [];
      for (const c of RADAT) { useCourse(c.id);
        for (const b of BELTS) for (const f of FLOORS)
          for (const [px, py] of [[b.x0 + 0.01, b.y0 + 0.01], [b.x1 - 0.01, b.y1 - 0.01], [(b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2]])
            if (inRect(f, px, py) && Math.abs(topOf(f, py) - topOf(b, py)) > 1e-9) bad.push([c.id, 'belt', b.y0, f.y0]);
        const movers = DISCS.map(d => ({ y0: d.y - d.r, y1: d.y + d.r, h: d.h || 0, x0: d.x - d.r, x1: d.x + d.r }));
        if (MOV) movers.push({ y0: MOV.y0, y1: MOV.y1, h: MOV.h || 0, x0: -MOV.a - MOV.hw, x1: MOV.a + MOV.hw });
        const all = FLOORS.map(f => ({ y0: f.y0, y1: f.y1, x0: f.x0, x1: f.x1, a: topOf(f, f.y0), b: topOf(f, f.y1) }))
          .concat(movers.map(m => ({ ...m, a: m.h, b: m.h })));
        for (const m of movers) {
          const next = all.filter(o => o.x0 < m.x1 && m.x0 < o.x1 && (o.y1 <= m.y0 + 0.01 && o.y1 > m.y0 - 3.5 || o.y0 >= m.y1 - 0.01 && o.y0 < m.y1 + 3.5) && o.y0 !== m.y0);
          if (!next.length) bad.push([c.id, 'alone', m.y0]);
          for (const o of next) if (Math.abs((o.y1 <= m.y0 + 0.01 ? o.b : o.a) - m.h) > STEP + 1e-9) bad.push([c.id, 'mover', m.y0, o.y0]);
        }
      }
      useCourse('main'); return bad; }''')
    assert bad == []
    assert page.errors == []


def test_a_ramp_lifts_a_step_stops_a_walk_and_a_jump_climbs_it(site, context):
    page = open_game(site, context)
    page.click('#go')
    page.evaluate(SOLO, 'main')
    # Up the ramp to the bars (10-14, from 0 to 1 m): the runner walks up it, on it all the way.
    ramp = page.evaluate(RUN, [0, 9, 100, -1])
    mid = [z for y, z in ramp['zs'] if 11.5 < y < 12.5]
    assert mid and all(0.3 < z < 0.7 for z in mid), ramp['zs']
    assert ramp['z'] == 1 and ramp['falls'] == 0
    # The bridge ends under a 0.8 m higher step to the finish (y 130): a walk stops at its edge without falling.
    walk = page.evaluate(RUN, [0, 128.6, 90, -1])
    assert 129 < walk['y'] < 130 and walk['fall'] == 0 and walk['falls'] == 0, walk
    # A jump from the same place lands on it.
    jump = page.evaluate(RUN, [0, 128.6, 90, 0])
    assert jump['y'] > 130.5 and jump['z'] == 3.2 and jump['falls'] == 0, jump
    assert page.errors == []


def test_running_off_a_drop_lands_on_the_lower_floor(site, context):
    page = open_game(site, context)
    page.click('#go')
    page.evaluate(SOLO, 'main')
    # Checkpoint 2's floor (2.2 m) ends at y 66 above the walls' floor (1.2 m).
    drop = page.evaluate(RUN, [0, 64.5, 80, -1])
    assert drop['y'] > 67 and drop['z'] == 1.2 and drop['fall'] == 0 and drop['falls'] == 0, drop
    # Into the gap before the stones there is nothing to land on: a fall.
    gap = page.evaluate('''() => { Object.assign(me, { x: -1.7, y: 40, z: 1.4, gx: -1.7, gy: 40, vx: 0, vy: 0, vz: 0, fall: 0 });
      input.y = 0; for (let i = 0; i < 60 && me.fall <= 0; i++) tick(1 / 60); return me.fall; }''')
    assert gap > 0
    assert page.errors == []


def test_the_race_is_drawn_in_3d_behind_the_runner(site, context):
    page = open_game(site, context)
    page.wait_for_function('K3D.ready || K3D.failed', timeout=10000)
    assert page.evaluate('[K3D.ready, K3D.failed]') == [True, False]
    page.click('#go')
    page.wait_for_function("race && race.phase === 'run'", timeout=8000)
    page.evaluate("race.runners.forEach(r => { if (r !== me) Object.assign(r, { kind: 'net', x: -4.5, y: -3, vx: 0, vy: 0 }); })")
    page.evaluate("Object.assign(me, { x: 0, y: 20, z: baseAt(0, 20), gx: 0, gy: 20, vx: 0, vy: 0 })")
    page.wait_for_timeout(1200)
    # The runner shows in the lower middle of the screen, the course ahead of it above.
    spot = page.evaluate('K3D.project(me.x, me.z + 0.6, me.y)')
    w, h = page.viewport_size['width'], page.viewport_size['height']
    assert 0.3 * w < spot['x'] < 0.7 * w and 0.45 * h < spot['y'] < 0.85 * h, spot
    ahead = page.evaluate('K3D.project(0, baseAt(0, me.y + 15), me.y + 15)')
    assert ahead['y'] < spot['y'] - 60, (ahead, spot)
    # The WebGL canvas draws it, with the HUD canvas see-through above it.
    shot = Image.open(io.BytesIO(page.locator('#g').screenshot())).convert('RGB').resize((36, 74))
    assert len(set(shot.getdata())) > 40
    assert page.evaluate("getComputedStyle(document.getElementById('g')).pointerEvents") == 'none'
    assert page.errors == []


def test_without_webgl_it_plays_on_the_2d_drawing(site, browser):
    ctx = browser.new_context(viewport={'width': 360, 'height': 740}, service_workers='block')
    try:
        ctx.route('**/three.module.js', lambda route: route.abort())
        page = open_game(site, ctx)
        page.wait_for_function('K3D.failed', timeout=10000)
        page.click('#go')
        page.wait_for_function("race && race.phase === 'run'", timeout=8000)
        page.evaluate("Object.assign(me, { x: 0, y: 139.5, z: baseAt(0, 139.5), gx: 0, gy: 139.5, vx: 0, vy: 5, cp: 4 }); input.y = 1")
        page.wait_for_function('!race', timeout=12000)
        assert page.inner_text('#result').startswith('Voitit!')
        # The 2D drawing fills its canvas (v9's sky), so the screen is not left blank.
        shot = Image.open(io.BytesIO(page.locator('#c').screenshot())).convert('RGB')
        assert shot.getpixel((180, 700)) != (0, 0, 0)
        assert page.errors == []
    finally:
        ctx.close()
