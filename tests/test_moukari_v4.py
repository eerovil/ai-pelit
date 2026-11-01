"""Moukarinheitto v4: recorded sounds from the shared library public/lib/aanet-2/ (#223)."""

import test_moukari_v2 as v2
import test_moukari_v3 as v3

URL = "games/moukari/v4/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

NAMES = ['valinta', 'onnistui', 'suhahdus', 'virhe', 'ohhoo', 'tomahdys', 'metalli', 'aplodit', 'mitali']


def open_game(site, context):
    old = v3.URL
    v3.URL = URL
    try:
        page = v3.open_game(site, context)
    finally:
        v3.URL = old
    page.evaluate(SPY)
    return page


def ready(page):
    page.click("#go")
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_throw_sounds_from_the_turn_to_the_landing(site, context):
    page = open_game(site, context)
    ready(page)
    page.evaluate("th.t = 99; step(0.001)")
    assert played(page) == ["valinta"]
    # The first tap starts the swings with a whoosh; a good tap in rhythm blips or confirms.
    page.evaluate("press(1)")
    assert played(page) == ["suhahdus"]
    page.evaluate("tapAt(1, 0)")
    assert played(page) == ["onnistui"]
    page.evaluate("tapAt(2, 0.05)")
    assert played(page) == ["valinta"]
    # Each turn whooshes at its low point; letting go whooshes too.
    page.evaluate("tapAt(3, 0); heard.splice(0); letGo(0)")
    got = played(page)
    assert got.count("suhahdus") >= 1 and got[-1] == "suhahdus", got
    # The first throw of the meet leads it: the thud, then the crowd claps.
    page.evaluate("quick()")
    assert played(page) == ["tomahdys", "aplodit"]
    assert page.errors == []


def test_out_of_rhythm_buzzes_and_out_of_the_circle_the_crowd_goes_ooh(site, context):
    page = open_game(site, context)
    ready(page)
    page.evaluate("th.t = 99; step(0.001); press(1); tapAt(1, 0); run(() => th.a < 1.5 * TAU); heard.splice(0); press(1)")
    assert played(page) == ["virhe"]
    page.evaluate("for (let n = 2; n <= 4; n++) tapAt(n, 0)")
    assert page.evaluate("th.v >= RED")
    page.evaluate("run(() => th.a < 4.5 * TAU); heard.splice(0); press(1)")
    assert page.evaluate("th.why") == "Rytmi petti: ulos ympyrästä"
    assert played(page) == ["ohhoo"]
    assert page.errors == []


def test_into_the_cage_it_clangs_and_drops(site, context):
    page = open_game(site, context)
    ready(page)
    page.evaluate("spin(4, 0, 40); heard.splice(0); run(() => th.phase === 'fly', 6)")
    assert page.evaluate("th.why") == "Osui häkkiin"
    assert played(page) == ["metalli", "tomahdys", "ohhoo"]
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
      for (const [k, v] of [['kisat', 4], ['voitot', 2], ['ennatys', 71.5]]) localStorage.setItem('ai-pelit:moukari:' + k, JSON.stringify(v));
    }""")
    page.goto(page.url)
    stats = page.inner_text("#stats")
    assert "4" in stats and "2" in stats and "71,5" in stats, stats
    assert page.errors == []


def test_a_whole_meet_alone_still_ends_on_the_podium(site, context):
    page = open_game(site, context)
    v3.win_meet(page)
    page.evaluate("for (let i = 0; i < 10 * 60; i++) step(1 / 60)")
    v3.tap(page)
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    assert page.errors == []


def test_with_friends_a_meet_still_plays_through(site, browser):
    old = v2.URL
    v2.URL = URL
    try:
        relay, pages = v2.room(site, browser, ["Eero", "Aino"])
    finally:
        v2.URL = old
    host = pages[0]
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = v2.thrower_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("spin(4, 0.01, 0); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null", timeout=10000)
        assert p.errors == []
        p.context.close()


def test_a_meet_left_in_v3_goes_on_in_v4_with_sound(site, context):
    page = open_game(site, context)
    page.goto(page.url.replace("/v4/", "/v3/"))
    page.evaluate(v2.HELPERS)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001); th.phase = 'land'; th.mark = 55.5; th.t = 99; th.sent = false; step(0.001)")
    first = page.evaluate("K.mine().marks[0]")
    page.goto(page.url.replace("/v3/", "/v4/"))
    page.evaluate(v2.HELPERS)
    page.evaluate(SPY)
    assert page.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    page.click("#cont")
    assert page.evaluate("[K.comp.round, K.mine().marks[0], th.mine]") == [2, first, True]
    page.wait_for_function("AiPelitAanet.ready('valinta')", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0); th.t = 99; step(0.001)")
    assert played(page) == ["valinta"]
    assert page.errors == []
