"""Hiihto v10 (#213): v9 with recorded sounds from the shared library public/lib/aanet-2/ (#205)."""

from conftest import ROOT

URL = "games/hiihto/v12/"
SOUNDS = ["valinta", "naksu", "lumi", "askel", "puu", "tomahdys", "voitto", "tappio", "tuuli"]

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

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Classic at level 3, which crosses the road, with nobody else on the trail. Every move is a tap on
# the screen, as a player makes it; the bindings hold snow, so the skis go on after two knocks.
RACE = """() => {
  const tap = () => { down(7, W / 2, H / 2 + 40); up(7); };
  setStyle('perinteinen'); level = 3; newRace(); draw();
  const r = ui.wax[bestWax(course.weather.T)]; down(7, r.x + 5, r.y + 5); up(7);
  for (let i = 0; i < 400 && mode === 'count'; i++) step(1 / 60);
  npcs = []; nextVasta = nextSkate = 1e9;
  let next = 0;
  for (let i = 0; i < 60 * 900 && mode === 'race'; i++) {
    const g = gradeAt(P.z + 2);
    if (P.road === 'skison') P.clog = 2;
    if (onRoad(P)) { if (P.t >= next) { tap(); next = P.t + 0.5; } }
    // Before the road it glides in slowly: faster than a walk onto it is a fall.
    else { P.vMode = g > 0.075; const slow = P.z > course.road.z0 - 30 && P.v > 3;
      if (P.t >= next && !slow) { tap(); next = P.t + 0.4; } }
    step(1 / 60);
  }
  return mode;
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    page.evaluate(SPY)
    return page


def sound_on(page):
    # Sound starts with the first tap; a tap on the sky above the menu presses nothing.
    page.mouse.click(180, 60)
    assert page.evaluate("mode") == "wax"
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_race_over_the_road_sounds_from_the_wax_to_the_tune(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("style = 'luistelu'; heard.splice(0)")
    page.evaluate("setStyle('perinteinen')")
    assert played(page) == ["naksu"]
    assert page.evaluate(RACE) == "done"
    got = played(page)
    # The wax, the start, kicks in the snow; at the road the bindings click open, steps on the
    # asphalt, knocks of snow out of the bindings and a click as they close; the tune (#337: no crowd).
    assert got[:3] == ["valinta", "valinta", "lumi"], got[:5]
    road = [n for n in got if n != "lumi"][2:]
    assert road[:2] == ["naksu", "askel"] and road[-4:] == ["puu", "puu", "naksu", "voitto"], road
    assert page.errors == []


def test_a_fall_thuds_and_a_slow_race_ends_on_the_losing_tune(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("chooseWax(bestWax(course.weather.T)); mode = 'race'; heard.splice(0); crash({ kind: 'vasta' })")
    assert played(page) == ["tomahdys"]
    page.evaluate("P.t = course.par + 10; finish()")
    assert played(page) == ["tappio"]
    assert page.errors == []


def test_the_glide_is_a_quiet_wind_that_grows_with_the_speed(site, context):
    page = open_game(site, context)
    sound_on(page)
    assert page.evaluate("glideSound(), glide.vol") == 0
    page.evaluate("chooseWax(bestWax(course.weather.T)); mode = 'race'; npcs = []; P.z = 30")
    slow, fast = page.evaluate("[(P.v = 2, glideSound(), glide.vol), (P.v = 9, glideSound(), [glide.vol, glide.rate])]")
    assert 0 < slow < fast[0] <= 0.3 and fast[1] > 1
    page.wait_for_function("!!glide.src", timeout=5000)
    # Down on the snow, or the race over, the wind goes quiet.
    assert page.evaluate("P.fallT = 1; glideSound(), glide.vol") == 0
    assert page.evaluate("P.fallT = 0; finish(); glideSound(), glide.vol") == 0
    assert page.errors == []


def test_without_the_sound_files_it_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.mouse.click(180, 60)
        page.evaluate("setStyle('perinteinen'); level = 1; newRace()")
        r = page.evaluate(BOT)
        assert r["mode"] == "done" and r["stars"] >= 1, r
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v9_saves_carry_on(site, context):
    context.add_init_script("""if (!sessionStorage.seeded) { sessionStorage.seeded = 1;
      localStorage.setItem('ai-pelit:hiihto:taso', '3'); localStorage.setItem('ai-pelit:hiihto:tyyli', '"luistelu"');
      localStorage.setItem('ai-pelit:hiihto:ajat', '{"1":200}'); localStorage.setItem('ai-pelit:hiihto:luistelu-ajat', '{"2":150}'); }""")
    page = open_game(site, context)
    assert page.evaluate("[maxLevel, level, style, bests[1], sBests[2]]") == [3, 3, "luistelu", 200, 150]
    assert page.errors == []


def test_skating_pushes_crunch_a_slip_on_the_road_thuds_and_a_restart_silences_the_glide(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("setStyle('luistelu'); level = 3; newRace(); chooseWax(bestWax(course.weather.T)); mode = 'race'; npcs = []; heard.splice(0)")
    page.evaluate("down(7, 40, H / 2 + 40); up(7); down(7, W - 40, H / 2 + 40); up(7)")
    assert played(page) == ["lumi", "lumi"]
    # On the road's ice two quick steps: the second comes before the beat and slips.
    page.evaluate("P.road = 'walk'; P.z = course.road.z0; P.lastKick = P.t - 1; heard.splice(0); roadFx(roadTap(P)); roadFx(roadTap(P))")
    assert played(page) == ["askel", "tomahdys"]
    page.evaluate("P.road = null; P.fallT = 0; P.z = 30; P.v = 8; glideSound()")
    assert page.evaluate("glide.vol") > 0
    assert page.evaluate("newRace(); glideSound(), glide.vol") == 0
    assert page.errors == []


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/hiihto/v12")
