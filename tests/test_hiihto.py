"""Hiihto in a phone-sized Chromium, driven through the game's own touch handlers and step()."""

from conftest import ROOT

# Plays one race as a careful skier: the given wax (the right one by default), V on the steep
# climbs, tuck down the hills, a kick every 0.4 s, and overtaking a granny on the oncoming track
# when it is clear (or the skating lane when it is not).
BOT = """(opts) => {
  opts = opts || {};
  const tap = (px, py) => { down(7, px, py); up(7); };
  const swipe = d => { down(8, W / 2, H / 2); move(8, W / 2 + 60 * d, H / 2); up(8); };
  draw();
  if (mode === 'wax') { const r = ui.wax[opts.wax ?? bestWax(course.weather.T)]; tap(r.x + 5, r.y + 5); }
  for (let i = 0; i < 400 && mode === 'count'; i++) step(1 / 60);
  let next = 0, holding = false, lastSteer = -9;
  const near = (kind, lane, a, b) => npcs.some(o => o.kind === kind && o.lane === lane && o.z - P.z > a && o.z - P.z < b);
  for (let i = 0; i < 60 * 900 && mode === 'race'; i++) {
    const g = gradeAt(P.z + 2);
    const wantV = opts.noV ? false : g > 0.075;
    if (wantV !== P.vMode) { const b = vButton(); tap(b.x, b.y); }
    if (clock - lastSteer > 0.4 && P.fallT <= 0) {
      const look = 6 + P.v * 1.6;
      if (P.lane === 1 && near('mummo', 1, -0.5, look)) {
        if (!near('vasta', 0, -3, 12 + look * 2.2)) { swipe(-1); lastSteer = clock; }
        else if (!npcs.some(o => o.kind === 'luistelija' && o.z - P.z > -22 && o.z - P.z < 3)) { swipe(1); lastSteer = clock; }
      } else if (P.lane === 0 && (near('vasta', 0, -1, 10 + P.v * 1.5) || !near('mummo', 1, -3, 3))) {
        if (!near('mummo', 1, -2.5, 3)) { swipe(1); lastSteer = clock; }
      } else if (P.lane === 2 && !near('mummo', 1, -2.5, 3)) { swipe(-1); lastSteer = clock; }
    }
    const blocked = P.lane === 1 && near('mummo', 1, 0, 3 + P.v);
    const wantHold = g < -0.02 && !blocked && P.v > 3;
    if (wantHold && !holding) { down(9, W / 2, H / 2); holding = true; }
    if (!wantHold && holding) { up(9); holding = false; }
    if (!holding && !blocked && clock >= next) { tap(W / 2, H / 2 + 40); next = clock + 0.4; }
    step(1 / 60);
  }
  if (holding) up(9);
  return { mode, t: P.t, par: course.par, falls, passes, stars: result && result.stars };
}"""

# Starts a race at level `n` with the right wax and nobody else on the trail.
EMPTY = """(n) => { level = n; newRace(); chooseWax(bestWax(course.weather.T)); mode = 'race';
  npcs = []; nextVasta = nextSkate = 1e9; }"""
# The middle of the first stretch steeper than `g` (or downhill steeper than -g when g < 0).
FIND = """(g) => { for (let z = 0; z < course.len; z += 1) if (g > 0 ? gradeAt(z) > g : gradeAt(z) < g) return z + 6; return -1; }"""
RUN = "s => { for (let i = 0; i < s * 60; i++) step(1 / 60); }"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site.url}games/hiihto/v1/")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    page.errors = errors
    return page


def test_the_wax_must_suit_the_weather(site, context):
    page = open_game(site, context)
    # Blue at -6: full grip, glides freely. Green (a harder wax) slips; violet (softer) drags.
    fits = page.evaluate("[0, 1, 2, 3].map(i => waxFit(WAXES[i], -6))")
    assert fits[1] == {"grip": 1, "drag": 0}
    assert fits[0]["grip"] < 0.6 and fits[0]["drag"] == 0
    assert fits[2]["grip"] == 1 and fits[2]["drag"] > 0.04
    assert page.evaluate("TEMPS.map(bestWax)") == [1, 0, 2, 3, 1, 1, 0, 3, 1, 0]
    assert page.evaluate("weatherFor(4).desc").startswith("Suojakeli")


def test_a_steep_hill_needs_the_v_step(site, context):
    page = open_game(site, context)
    page.evaluate(EMPTY, 1)
    z = page.evaluate(FIND, 0.1)
    assert z > 0
    page.evaluate("z => { P.z = z; P.v = 1; P.t = 5; P.lastKick = 0; }", z)
    stride = page.evaluate("kick(P)")
    assert page.evaluate("P.slipT") > 0
    page.evaluate("P.vMode = true; P.t = 10; P.slipT = 0")
    vee = page.evaluate("kick(P)")
    assert vee > 2 * stride and page.evaluate("P.slipT") == 0
    # Kicking without V, the skier stalls on the hill; with V it gets to the top.
    top = page.evaluate("z => { while (gradeAt(z) > 0.03) z += 1; return z; }", z)
    climb = """([z, v]) => { P.z = z - 10; P.v = 2; P.vMode = v; let next = 0;
      for (let i = 0; i < 60 * 40; i++) { if (P.t >= next) { kick(P); next = P.t + 0.4; } physics(P, 1 / 60); }
      return P.z; }"""
    assert page.evaluate(climb, [z, False]) < top
    assert page.evaluate("P.v") < 0.3
    assert page.evaluate(climb, [z, True]) > top


def test_holding_a_finger_down_a_hill_is_the_tuck(site, context):
    page = open_game(site, context)
    page.evaluate(EMPTY, 1)
    z = page.evaluate(FIND, -0.07)
    start = "z => { P.z = z - 12; P.v = 4; P.t = 0; }"
    page.evaluate(start, z)
    page.evaluate(RUN, 3)
    standing = page.evaluate("P.v")
    page.evaluate(start, z)
    page.evaluate("down(9, W / 2, H / 2)")
    page.evaluate(RUN, 3)
    assert page.evaluate("P.hold") is True
    tucked = page.evaluate("P.v")
    page.evaluate("up(9)")
    assert tucked > standing + 0.5
    # A V downhill brakes.
    page.evaluate(start, z)
    page.evaluate("P.vMode = true")
    page.evaluate(RUN, 3)
    assert page.evaluate("P.v") < standing - 1


def test_overtaking_a_granny_on_the_other_track(site, context):
    page = open_game(site, context)
    page.evaluate(EMPTY, 1)
    page.evaluate("P.z = 20; P.v = 5; addGranny(28); npcs[0].base = 0")
    swipe = "d => { down(8, W / 2, H / 2); move(8, W / 2 + 60 * d, H / 2); up(8); }"
    page.evaluate(swipe, -1)
    assert page.evaluate("P.lane") == 0
    page.evaluate(RUN, 3)
    assert page.evaluate("[passes, bubbles.length]") == [1, 1]
    page.evaluate(swipe, 1)
    page.evaluate(RUN, 1)
    assert page.evaluate("[passes, falls, P.lane]") == [1, 0, 1]


def test_running_into_anyone_is_a_fall(site, context):
    page = open_game(site, context)
    for setup in ["addGranny(24); npcs[0].base = 0",
                  "P.lane = 0; P.x = LX[0]; addVasta(30)",
                  "P.lane = 2; P.x = LX[2]; P.v = 0; addSkater(8)"]:
        page.evaluate(EMPTY, 1)
        page.evaluate("P.z = 20; P.v = 5")
        page.evaluate(setup)
        page.evaluate(RUN, 2)
        assert page.evaluate("falls") == 1, setup
        # Back on the skis after a moment, and no second fall from the same skier.
        page.evaluate(RUN, 3)
        assert page.evaluate("[falls, P.fallT]") == [1, 0], setup


def test_a_skater_shouts_before_passing(site, context):
    page = open_game(site, context)
    page.evaluate(EMPTY, 1)
    page.evaluate("P.z = 40; P.v = 0; P.lane = 2; P.x = LX[2]; addSkater(26)")
    page.evaluate(RUN, 0.5)
    assert page.evaluate("bubbles.map(b => b.text)") == ["Latua!"]
    assert page.evaluate("hint()[0]") == "Takaa tulee luistelija!"


def test_a_race_with_the_right_wax_passes_and_saves(site, context):
    page = open_game(site, context)
    r = page.evaluate(BOT)
    assert r["mode"] == "done", r
    assert r["t"] < r["par"] and r["stars"] >= 1, r
    assert r["passes"] >= 3, r
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:taso')") == "2"
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:hiihto:tahdet'))['1']") == r["stars"]
    # A tap on the result goes on to level 2, and a reload opens it too.
    page.evaluate("step(1); down(1, W / 2, H / 2); up(1)")
    assert page.evaluate("[mode, level]") == ["wax", 2]
    page.reload()
    page.wait_for_function("typeof course === 'object'")
    assert page.evaluate("[level, maxLevel]") == [2, 2]
    assert page.errors == []


def test_klister_on_a_frosty_day_is_too_slow(site, context):
    page = open_game(site, context)
    r = page.evaluate(BOT, {"wax": 3})
    assert r["mode"] == "done" and r["stars"] == 0, r
    assert page.evaluate("result.note").startswith("Voide oli liian pehmeä")
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:taso')") is None


def test_it_fits_a_small_phone(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx)
    boxes = page.evaluate("ui.wax.map(r => [r.x, r.y, r.x + r.w, r.y + r.h])")
    for x0, y0, x1, y1 in boxes:
        assert 0 <= x0 and x1 <= 360 and 40 <= y0 and y1 <= 640
    page.evaluate("chooseWax(1)")
    b = page.evaluate("vButton()")
    assert b["y"] + b["r"] <= 640 and b["x"] - b["r"] >= 0
    ctx.close()
# CI timing probe for #123, not to be merged
