"""Kaahari v4: recorded sounds from the shared library public/lib/aanet-2/ (#216)."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaahari/v5/"
SOUNDS = ['kartti', 'valinta', 'onnistui', 'voitto', 'tappio', 'kitka', 'hyppy', 'nousu', 'naksu',
          'suhahdus', 'rajahdys', 'metalli', 'osuma']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def finish(page):
    page.evaluate("""() => {
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150 });
    }""")


def test_a_race_sounds_from_the_countdown_to_the_finish(site, context):
    page = open_game(site, context)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.click("#go")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    assert played(page) == ["valinta", "valinta", "valinta"]
    # The kart's engine is the recorded loop, faster as the kart speeds up.
    page.wait_for_function("me.v > 100 && kart && kart.playing()", timeout=3000)
    assert page.evaluate("kart.rate > 1")
    page.evaluate("heard.splice(0)")
    page.evaluate("""() => {
        for (const it of ['turbo', 'tnt', 'pommi']) { me.item = it; useItem(); }
        me.shield = 0; hit(me);
    }""")
    assert played(page)[:4] == ["nousu", "naksu", "suhahdus", "kitka"]
    # A bomb going off near the kart.
    assert page.evaluate("heard.splice(0); boom({ x: me.x + 50, y: me.y }); heard.splice(0)") == [["rajahdys", True]]
    page.evaluate("me.spin = 0; heard.splice(0)")
    finish(page)
    page.wait_for_function("race.phase === 'over'", timeout=6000)
    got = played(page)
    # #337: the tune alone, no applause after it.
    assert "voitto" in got and "aplodit" not in got, got
    assert page.evaluate("kart") is None
    assert page.errors == []


def test_a_slide_hops_then_each_spark_colour_and_the_turbo_sound(site, context):
    page = open_game(site, context)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.click("#go")
    page.evaluate("race.cdT = 3")
    page.wait_for_function("race.phase === 'run' && me.v > 100", timeout=6000)
    page.evaluate("heard.splice(0); input.drift = true; input.right = true")
    page.wait_for_function("me.drift === 1", timeout=1000)
    page.evaluate("input.right = false")
    page.wait_for_function("me.dTime > 1.5", timeout=3000)
    page.evaluate("input.drift = false")
    page.wait_for_timeout(50)
    got = played(page)
    assert "hyppy" in got and got.count("valinta") >= 2 and "nousu" in got, got
    assert page.errors == []


def test_without_the_sound_files_it_still_races_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        page.wait_for_function("race.phase === 'run'", timeout=6000)
        assert page.evaluate("!kart.playing() && eng !== null")
        finish(page)
        page.wait_for_function("race.phase === 'over'", timeout=6000)
        assert played(page) == []
        assert page.inner_text("#result") == "🏆 Voitit kisan!"
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 4], ['voitot', 3], ['kisat', 7], ['rata', 2]]) localStorage.setItem('ai-pelit:kaahari:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Taso 4 · Voitot 3 / 7 kisaa"
    assert page.evaluate("trackNo") == 2
    assert page.errors == []


def test_a_lost_race_plays_the_losing_tune_and_a_second_race_has_its_engine_again(site, context):
    page = open_game(site, context)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.click("#go")
    page.evaluate("race.cdT = 3")
    page.wait_for_function("race.phase === 'run' && kart && kart.playing()", timeout=6000)
    # Another kart in first: this one ends second.
    page.evaluate("const o = race.karts[1]; o.fin = 1; race.finishers.push(o); heard.splice(0)")
    finish(page)
    page.wait_for_function("race.phase === 'over'", timeout=6000)
    got = played(page)
    assert "tappio" in got and "voitto" not in got and "aplodit" not in got, got
    assert page.evaluate("kart") is None
    page.click("#go")
    page.wait_for_function("race.phase === 'run' && kart && kart.playing()", timeout=6000)
    assert page.errors == []


def room_of_two(site, browser):
    """Eero's phone makes a room, Aino's joins it, and the race is on."""
    relay = Relay()
    pages = []
    for name in ["Eero", "Aino"]:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host, guest = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    assert guest.inner_text("#aipr-extra") == "Huoneen tekijä valitsee radan."
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=8000)
    return host, guest


def test_in_a_room_the_line_blips_then_each_phone_hears_its_own_place(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    for p in (host, guest):
        p.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
        p.evaluate(SPY)
    finish(guest)
    guest.wait_for_function("me.fin !== null", timeout=3000)
    assert "onnistui" in played(guest)
    host.wait_for_function("race.karts[1].fin !== null", timeout=3000)
    finish(host)
    for p in (host, guest):
        p.wait_for_function("(!race || race.phase === 'over') && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert "voitto" in played(guest)
    got = played(host)
    assert "tappio" in got and "voitto" not in got, got
    assert host.errors == [] and guest.errors == []


def test_without_the_sound_library_script_it_still_races_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    try:
        ctx.route("**/aanet.js", lambda route: route.abort())
        site.build(ROOT / "games")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        assert page.evaluate("typeof AiPelitAanet") == "undefined"
        page.click("#go")
        page.wait_for_function("race.phase === 'run'", timeout=6000)
        assert page.evaluate("eng !== null && !kart.playing()")
        finish(page)
        page.wait_for_function("race.phase === 'over'", timeout=6000)
        assert page.inner_text("#result") == "🏆 Voitit kisan!"
        assert page.errors == []
    finally:
        ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/kaahari/v5")
