"""Pingis v1 (#502): table tennis in 3D, the bat under the finger, alone against the computer."""
import json
import shutil

from conftest import ROOT, turn

URL = "games/pingis/v1/"
KEY = "ai-pelit:pingis:"
TOUCH = """([t, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: 9, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# Whole games played in the page, fast, without drawing: my bat (side 0) played by `style`
# ('lazy' stands in the middle, 'sloppy' goes where the ball will be give or take 10 cm).
SIM = """([lvl, style, games]) => {
  cancelAnimationFrame(raf); raf = 1;
  const r = rng(1234), out = { won: 0, lost: 0, pts: [0, 0], hits: 0 };
  for (let gN = 0; gN < games; gN++) {
    level = lvl; soloGame(null); brains[1] = cpuBrain(lvl, 99 + gN); game.wait = 0;
    for (let k = 0; k < 60 * 60 * 30 && !game.over; k++) {
      const dt = 1 / 60, b = bats[0], f = game.flight;
      let tx = 0;
      if (style !== 'lazy' && f && f.by === 1 && !f.over) { const q = predict(f, 0, 0.35); if (q) tx = q.x + gauss(r) * 0.1; }
      b.x = b.tx = tx; b.z = b.tz = HL + 0.35; b.vx = 0; b.vz = 0;
      if (game.ph === 'serve' && game.sv === 0 && game.wait <= 0) tryServe(0, r() * 2 - 1);
      const n = f ? f.n : -1;
      advance(dt * SLOW);
      if (game.flight && game.flight.n > n && game.flight.by === 0) out.hits++;
    }
    out.pts[0] += game.sc[0]; out.pts[1] += game.sc[1];
    if (game.winner === 0) out.won++; else out.lost++;
  }
  raf = 0; wake();
  return out;
}"""
# The events of one serve or shot flown out, until it is dead or past either end.
FLY = """(a) => { const b = ballFrom(a), ev = [];
  for (let k = 0; k < 2400 && !b.dead && Math.abs(b.z) < HL + 0.6; k++) { const e = ballStep(b); if (e) ev.push(e); }
  return ev; }"""


def open_game(site, context, width=360, height=740, saves=None):
    if not (site.games / "pingis").exists():
        shutil.copytree(ROOT / "games" / "pingis", site.games / "pingis")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    if saves:
        page.add_init_script("(() => { const s = " + json.dumps(saves) + "; for (const k in s) localStorage.setItem('" + KEY + "' + k, s[k]); })()")
    page.goto(site.url + URL)
    page.wait_for_function("V3 || no3d", timeout=20000)
    return page


def saved(page, k):
    v = page.evaluate(f"localStorage.getItem('{KEY}{k}')")
    return None if v is None else json.loads(v)


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'play' && game && game.ph === 'serve'", timeout=8000)


def test_the_menu_picks_a_level_and_keeps_it(site, context):
    page = open_game(site, context)
    assert page.evaluate("!!V3")
    levels = page.locator("#levels button")
    assert levels.count() == 3
    assert [levels.nth(i).inner_text().split("\n")[0] for i in range(3)] == ["Helppo", "Keskitaso", "Vaikea"]
    levels.nth(2).click()
    assert saved(page, "taso") == 2
    assert "on" in page.locator("#levels button").nth(2).get_attribute("class")
    assert page.locator("#friends").is_visible()
    go(page)
    assert page.evaluate("names") == ["Sinä", "Kone"]
    assert page.evaluate("brains[1].L.name") == "Vaikea"
    assert page.errors == []


def test_the_rules_score_and_serve_like_table_tennis(site, context):
    page = open_game(site, context)
    # Two serves each, then one each from 10–10.
    assert page.evaluate("[0, 1, 2, 3, 4].map(t => serverAt([t, 0], 0))") == [0, 0, 1, 1, 0]
    assert page.evaluate("[serverAt([10, 10], 0), serverAt([11, 10], 0), serverAt([11, 11], 0)]") == [0, 1, 0]
    assert page.evaluate("serverAt([0, 0], 1)") == 1
    # Eleven wins, but only two clear.
    assert page.evaluate("[winnerOf([11, 9]), winnerOf([11, 10]), winnerOf([12, 10]), winnerOf([3, 11])]") == [0, -1, 0, 1]
    # A serve by side 0 must bounce on its own half first, then on the other.
    assert page.evaluate("(() => { const f = newFlight(0, 0, true, [0,0.3,1.5,0,0,-3,0]); return judge(f, 'bounce1'); })()") == {"w": 1}
    assert page.evaluate("""(() => { const f = newFlight(0, 0, true, [0,0.3,1.5,0,0,-3,0]);
      return [judge(f, 'bounce0'), judge(f, 'bounce1'), judge(f, 'bounce1')]; })()""") == [None, None, {"w": 0}]
    # A shot that misses the other half is the receiver's point; one that bounced there and
    # flew past them is the hitter's.
    assert page.evaluate("(() => { const f = newFlight(1, 0, false, [0,0.3,1.5,0,0,-3,0]); return judge(f, 'floor'); })()") == {"w": 1}
    assert page.evaluate("(() => { const f = newFlight(1, 0, false, [0,0.3,1.5,0,0,-3,0]); judge(f, 'bounce1'); return judge(f, 'floor'); })()") == {"w": 0}
    # Back on the hitter's own half (off the net) is the receiver's point.
    assert page.evaluate("(() => { const f = newFlight(1, 0, false, [0,0.3,1.5,0,0,-3,0]); return judge(f, 'bounce0'); })()") == {"w": 1}


def test_every_serve_clears_the_net_and_lands_on_both_halves(site, context):
    page = open_game(site, context)
    bad = page.evaluate("""() => { const r = rng(7), bad = [];
      for (const side of [0, 1]) for (const x of [-1.1, -0.5, 0, 0.6, 1.1]) for (const d of [-0.25, 0.2, 0.6, 1.0])
        for (const aim of [-1, 0, 1]) {
          const a = serveLaunch({ x, z: sgn(side) * (HL + d) }, side, aim, r), ev = [], b = ballFrom(a);
          for (let k = 0; k < 2400 && !b.dead && Math.abs(b.z) < HL + 1.4; k++) { const e = ballStep(b); if (e) ev.push(e); }
          const own = side === 0 ? 'bounce0' : 'bounce1', far = side === 0 ? 'bounce1' : 'bounce0';
          if (ev[0] !== own || ev[1] !== far || ev.includes('net')) bad.push([side, x, d, aim, ev.join(' ')]);
        }
      return bad; }""")
    assert bad == []


def test_shots_from_the_middle_land_and_launches_are_rounded(site, context):
    page = open_game(site, context)
    # A clean block, drive and smash of an ordinary ball land on the other half, past the net.
    for kind in ("block", "drive", "smash"):
        a = page.evaluate(f"""(() => shotLaunch({{ x: 0, y: 0.25, z: HL + 0.3, vx: 0, vy: 0, vz: 2 }}, 0, '{kind}', 0, 0, () => 0.5))()""")
        assert all(round(v, 4) == v for v in a)
        assert page.evaluate(FLY, a)[:1] == ["bounce1"], kind


def test_a_bat_over_the_table_in_front_of_the_bounce_still_meets_the_ball(site, context):
    # Eero on the preview: too hard to hit. A bat held over the table 12 cm in front of the bounce
    # (the ball bounces 48 cm from the end line), where the ball has not
    # bounced yet, meets it right after the bounce; 30 cm to the side still meets it; a bat
    # far to the side, or a ball long past, does not.
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const out = {};
      for (const [name, dx, dz] of [['front', 0, -0.6], ['side', 0.3, 0.3], ['far', 0.6, 0.3]]) {
        const f = newFlight(1, 1, false, [0, 0.3, -1.2, 0, 0, 3.2, 0]);
        const q = predict(f, 0, 0.3), bat = { x: q.x + dx, z: HL + dz };
        let met = false;
        for (let k = 0; k < 2400 && !f.ball.dead && !met; k++) { judge(f, ballStep(f.ball)); met = hittable(f) && meets(f, bat); }
        out[name] = met;
      }
      return out; }""")
    assert got == {"front": True, "side": True, "far": False}


    # The computer keeps its old bat: 26 cm sideways, and only at its line, so the easier hit
    # helps only the player (review of #509).
    cpu = page.evaluate("""() => {
      const out = {};
      for (const [name, dx, dz] of [['front', 0, -0.6], ['line', 0.2, 0.3], ['side', 0.3, 0.3]]) {
        const f = newFlight(1, 0, false, [0, 0.3, 1.2, 0, 0, -3.2, 0]);
        const q = predict(f, 1, 0.3), bat = { x: q.x + dx, z: -HL - dz };
        let met = false;
        for (let k = 0; k < 2400 && !f.ball.dead && !met; k++) { const pz = f.ball.z; judge(f, ballStep(f.ball)); met = hittable(f) && meets(f, bat, true, pz); }
        out[name] = met;
      }
      return out; }""")
    assert cpu == {"front": False, "line": True, "side": False}
    # And its hit off the bat's middle is judged against its own narrower bat.
    go(page)
    off = page.evaluate("""() => {
      let seen = -1; const real = shotLaunch;
      shotLaunch = (...a) => { seen = a[4]; return real(...a); };
      game.ph = 'play'; brains[1].kind = 'block'; brains[1].aim = 0;
      bats[1].x = 0; bats[1].z = -HL - 0.3;
      const f = newFlight(1, 0, false, [0.13, 0.25, -HL - 0.3, 0, 0, -3, 0]); f.bR = 1;
      hitBy(1, f); shotLaunch = real; return seen; }""")
    assert abs(off - 0.13 / 0.26) < 1e-6

def test_a_flick_up_serves_and_a_bat_in_the_way_returns_the_ball(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { game.sv = 0; game.wait = 0; brains[1] = null; }")
    # My bat goes under the finger; a quick push up serves.
    p = page.evaluate("project3d(0, 0.12, HL + 0.3)")
    page.evaluate(TOUCH, ["pointerdown", p["x"], p["y"] + 46])
    page.wait_for_timeout(120)
    assert page.evaluate("game.ph") == "serve"
    page.evaluate(TOUCH, ["pointermove", p["x"], p["y"] - 40])
    page.wait_for_timeout(30)
    page.evaluate(TOUCH, ["pointermove", p["x"], p["y"] - 120])
    page.wait_for_function("game.ph === 'play' && game.flight && game.flight.serve", timeout=3000)
    page.evaluate(TOUCH, ["pointerup", p["x"], p["y"] - 120])
    # The computer's ball comes back to me: the finger puts my bat where it will cross, and it
    # goes back over the net.
    page.evaluate("() => { brains[1] = cpuBrain(0, 5); brains[1].L = Object.assign({}, LEVELS[0], { miss: 0 }); }")
    page.wait_for_function("game.flight && game.flight.by === 1 || game.ph !== 'play'", timeout=8000)
    assert page.evaluate("game.ph") == "play", page.evaluate("game.sc")
    page.evaluate(TOUCH, ["pointerdown", 180, 600])
    for _ in range(80):
        q = page.evaluate("(() => { const f = game.flight; const q = f && f.by === 1 ? predict(f, 0, 0.35) : null; return q && project3d(q.x, 0.12, HL + 0.35); })()")
        if q:
            page.evaluate(TOUCH, ["pointermove", q["x"], q["y"] + 46])
        if page.evaluate("game.flight && game.flight.by === 0 && game.flight.n >= 2"):
            break
        page.wait_for_timeout(25)
    assert page.evaluate("game.flight.by === 0 && game.flight.n >= 2")
    assert page.evaluate("bats[0].swing") > 0
    assert page.errors == []


def test_standing_still_loses_and_following_the_ball_wins_on_easy(site, context):
    page = open_game(site, context)
    # Standing still won 1 of 40 games on easy when this was measured (4.4 points a game, at
    # most 14), so four games may hold one lucky win.
    lazy = page.evaluate(SIM, [0, "lazy", 4])
    assert lazy["lost"] >= 3 and lazy["pts"][0] < 32
    # Following the ball (with a 10 cm wobble) won 8 of 8 games on easy when this was measured,
    # so three of four leaves room for chance.
    good = page.evaluate(SIM, [0, "sloppy", 4])
    assert good["won"] >= 3 and good["hits"] > 80
    # The hard computer gives a player like that a real game.
    hard = page.evaluate(SIM, [2, "sloppy", 2])
    assert hard["pts"][1] >= 14
    assert page.errors == []


def test_a_game_is_saved_point_by_point_and_the_end_counts_once(site, context):
    page = open_game(site, context, saves={"taso": "1"})
    go(page)
    page.evaluate("() => { game.ph = 'play'; game.flight = newFlight(0, 1, false, [0,0.3,-1,0,0,3,0]); soloPoint(game.flight, 0); }")
    assert saved(page, "kesken") == {"lvl": 1, "sc": [1, 0], "first": 0}
    page.reload()
    page.wait_for_function("mode === 'play' && game", timeout=20000)
    assert page.evaluate("game.sc") == [1, 0]
    assert page.evaluate("level") == 1
    # Winning the game: the end screen, one more win on this level, the save cleared.
    page.evaluate("() => { game.sc = [10, 3]; game.ph = 'play'; game.flight = newFlight(0, 1, false, [0,0.3,-1,0,0,3,0]); soloPoint(game.flight, 0); game.wait = 0; }")
    page.wait_for_function("mode === 'end'", timeout=5000)
    assert page.locator("#endTitle").inner_text() == "Voitit!"
    assert page.locator("#endScore").inner_text() == "11–3"
    assert saved(page, "voitot") == {"1": [1, 0]}
    assert saved(page, "kesken") is None
    page.click("#toMenu")
    assert "voitot 1/1" in page.locator("#levels button").nth(1).inner_text()
    assert page.errors == []


def test_a_long_deuce_is_resumed_and_a_broken_save_is_dropped(site, context):
    # 40–39 is still on: nobody leads by two. It comes back after a reload as it was.
    page = open_game(site, context, saves={"kesken": json.dumps({"lvl": 2, "sc": [40, 39], "first": 1})})
    page.wait_for_function("mode === 'play' && game", timeout=20000)
    assert page.evaluate("[game.sc, level, game.first, game.over]") == [[40, 39], 2, 1, False]
    assert page.evaluate("serverAt(game.sc, game.first)") == page.evaluate("game.sv")
    page.close()
    # A finished score, a broken one or a level that is not one: the menu, and the save is gone.
    for bad in ({"lvl": 0, "sc": [41, 39]}, {"lvl": 0, "sc": [3, -1]}, {"lvl": 0, "sc": [3, 1.5]}, {"lvl": 0.5, "sc": [3, 1]}, {"lvl": 3, "sc": [3, 1]}):
        page = open_game(site, context, saves={"kesken": json.dumps(bad)})
        page.wait_for_function("mode === 'menu'", timeout=20000)
        assert saved(page, "kesken") is None, bad
        assert page.errors == []
        page.close()


def test_sideways_the_menu_fits_and_turning_keeps_the_game(site, context):
    page = open_game(site, context, width=740, height=360)
    for sel in ("#go", "#friends", "#levels button >> nth=2"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= 360, sel
    go(page)
    page.evaluate("() => { game.sc = [4, 2]; }")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!LAND && H === 740")
    assert page.evaluate("game.sc") == [4, 2] and page.evaluate("mode") == "play"
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND")
    assert page.evaluate("game.sc") == [4, 2]
    assert page.errors == []
