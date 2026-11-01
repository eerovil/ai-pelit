"""Hiihto v10 (#213): v9 with recorded sounds from the shared library public/lib/aanet-2/ (#205)."""

from conftest import ROOT
from test_hiihto import BOT

URL = "games/hiihto/v10/"
SOUNDS = ["valinta", "naksu", "lumi", "askel", "puu", "tomahdys", "voitto", "tappio", "aplodit", "tuuli"]

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


def test_a_race_over_the_road_sounds_from_the_wax_to_the_applause(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("style = 'luistelu'; heard.splice(0)")
    page.evaluate("setStyle('perinteinen')")
    assert played(page) == ["naksu"]
    assert page.evaluate(RACE) == "done"
    got = played(page)
    # The wax, the start, kicks in the snow; at the road the bindings click open, steps on the
    # asphalt, knocks of snow out of the bindings and a click as they close; the tune and the crowd.
    assert got[:3] == ["valinta", "valinta", "lumi"], got[:5]
    road = [n for n in got if n != "lumi"][2:]
    assert road[:2] == ["naksu", "askel"] and road[-5:] == ["puu", "puu", "naksu", "voitto", "aplodit"], road
    assert page.errors == []


def test_a_fall_thuds_and_a_slow_race_ends_on_the_losing_tune(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("chooseWax(bestWax(course.weather.T)); mode = 'race'; heard.splice(0); crash({ kind: 'vasta' })")
    assert played(page) == ["tomahdys"]
    page.evaluate("P.t = course.par + 10; finish()")
    assert played(page) == ["tappio", "aplodit"]
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
