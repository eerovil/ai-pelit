"""Keihäänheitto v6: recorded sounds from the shared library public/lib/aanet-2/ (#218)."""

import test_keihas_v5 as v5

URL = "games/keihas/v6/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

SOUNDS = ['valinta', 'askel', 'askel2', 'naksu', 'suhahdus', 'tomahdys', 'onnistui', 'aplodit', 'ohhoo', 'mitali']


def open_game(site, context):
    old = v5.URL
    v5.URL = URL
    try:
        page = v5.open_game(site, context)
    finally:
        v5.URL = old
    page.evaluate(SPY)
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def ready(page):
    page.click("#go")
    page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def test_a_throw_sounds_from_the_run_up_to_the_grass(site, context):
    page = open_game(site, context)
    ready(page)
    page.evaluate("th.t = 99; step(0.001)")
    assert played(page) == ["valinta"]
    page.evaluate("press(1); press(2)")
    assert played(page) == ["askel", "askel2"]
    page.evaluate("th.x = -6; startAim(1)")
    assert played(page) == ["naksu"]
    page.evaluate("th.aimT = (36 - AIM0) / AIM_RATE; th.ang = 36; th.v = 9; release()")
    assert played(page) == ["suhahdus"]
    # The first throw of the meet leads it: the javelin thuds into the grass, then the crowd claps.
    page.evaluate("quick()")
    assert played(page) == ["tomahdys", "aplodit"]
    # A shorter one, no record and no lead: a chime.
    page.evaluate("go(4, 36, -3); quick()")
    assert played(page)[-2:] == ["tomahdys", "onnistui"]
    assert page.errors == []


def test_over_the_line_the_crowd_goes_ooh(site, context):
    page = open_game(site, context)
    ready(page)
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.v = 9; th.x = 1; heard.splice(0); step(1 / 60)")
    assert played(page) == ["ohhoo"]
    assert page.errors == []


def test_the_medals_ring_and_the_gold_gets_applause(site, context):
    page = open_game(site, context)
    ready(page)
    for _ in range(6):
        page.evaluate("go(9, 36, -3.5); quick()")
    page.evaluate("heard.splice(0); for (let i = 0; i < 60 * 60; i++) step(1 / 60)")
    got = played(page)
    assert got.count("mitali") == 3 and "aplodit" in got, got
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        v5.win_meet(page)
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v5_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['kisat', 5], ['voitot', 3], ['ennatys', 71.25]]) localStorage.setItem('ai-pelit:keihas:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Kisat 5 · Voitot 3 · Ennätys 71,25 m"
    assert page.errors == []


def test_the_podium_still_stays_until_a_tap(site, context):
    old = v5.URL
    v5.URL = URL
    try:
        v5.test_the_medals_are_hung_and_the_podium_stays_until_a_tap(site, context)
    finally:
        v5.URL = old
