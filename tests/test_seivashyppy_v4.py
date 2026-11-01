"""Seiväshyppy v4: recorded sounds from the shared library public/lib/aanet-2/ (#227)."""

import test_seivashyppy_v3 as v3

URL = "games/seivashyppy/v4/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

NAMES = ['valinta', 'askel', 'askel2', 'seivas', 'suhahdus', 'rima', 'onnistui', 'aplodit', 'ohhoo', 'tomahdys', 'mitali']


def open_game(site, context):
    old = v3.URL
    v3.URL = URL
    try:
        page = v3.open_game(site, context)
    finally:
        v3.URL = old
    page.evaluate(SPY)
    return page


def sound_on(page):
    page.click("#go")
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_clean_vault_sounds_from_the_run_up_to_the_mat(site, context):
    page = open_game(site, context)
    sound_on(page)
    # The player's turn comes with a blip, then a step on each foot.
    page.evaluate("th.phase = 'wait'; th.t = 99; step(0.001)")
    assert played(page) == ["valinta"]
    page.evaluate("press(1); press(2)")
    assert played(page) == ["askel", "askel2"]
    # The pole in the box, the push off, the mat, and the crowd or a confirmation.
    page.evaluate("go(9.2); quick()")
    got = played(page)
    assert got[:3] == ["seivas", "suhahdus", "tomahdys"], got
    assert got[3] in ("aplodit", "onnistui") and len(got) == 4, got
    assert page.errors == []


def test_a_knocked_bar_clatters_and_the_crowd_goes_ooh(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("ready(); heard.splice(0); go(6.5, -4, 0, 1.0); quick()")
    got = played(page)
    assert got[:2] == ["seivas", "suhahdus"] and "rima" in got and "tomahdys" in got and got[-1] == "ohhoo", got
    assert page.errors == []


def test_a_run_through_goes_ooh_and_a_pass_blips(site, context):
    page = open_game(site, context)
    sound_on(page)
    page.evaluate("ready(); heard.splice(0); th.phase = 'run'; th.x = -2; th.v = 8; step(0.02)")
    assert played(page) == ["ohhoo"]
    page.evaluate("th.t = 99; step(0.001)")
    page.evaluate("run(() => !th || !th.mine || th.phase !== 'ready', 30); ready(); heard.splice(0); pass()")
    assert played(page) == ["valinta"]
    assert page.errors == []


def test_the_medals_ring_and_the_podium_stays_until_a_tap(site, context):
    page = open_game(site, context)
    v3.win_meet(page)
    page.evaluate("heard.splice(0); for (let i = 0; i < 60 * 20; i++) step(1 / 60)")
    got = played(page)
    assert got.count("mitali") == 3 and "aplodit" in got, got
    assert page.evaluate("K.ending !== null")
    v3.tap(page)
    assert page.is_visible("#menu")
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        v3.win_meet(page)
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['kisat', 5], ['voitot', 3], ['ennatys', 5.1]]) localStorage.setItem('ai-pelit:seivashyppy:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Kisat 5 · Voitot 3 · Ennätys 5,10 m"
    assert page.errors == []
