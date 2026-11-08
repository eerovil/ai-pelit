"""Kaaosrata v3: recorded sounds from the shared library public/lib/aanet-2/ (#217)."""

import json

from conftest import ROOT

URL = "games/kaaosrata/v7/"
NAMES = ['valinta', 'hyppy', 'potku', 'putoaminen', 'osuma', 'tomahdys', 'voitto', 'suhahdus']

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


def heard(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def running(page):
    """A race with sound on and every file in, the computer's players standing out of the way."""
    page.click("#go")
    page.wait_for_function(f"{json.dumps(NAMES)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("soloRace(); heard.splice(0)")
    page.wait_for_function("race && race.phase === 'run'", timeout=6000)
    page.evaluate("race.runners.forEach(r => { if (r !== me) Object.assign(r, { kind: 'net', x: -4, y: -3, vx: 0, vy: 0 }); })")


def put(page, **kw):
    page.evaluate(f"heard.splice(0); input.x = 0; input.y = 0; Object.assign(me, {{ z: 0, vx: 0, vy: 0, vz: 0, stun: 0, cd: 0, fall: 0 }}, {json.dumps(kw)})")


def test_the_countdown_blips_and_a_jump_lands_with_a_thud(site, context):
    page = open_game(site, context)
    running(page)
    assert heard(page).count("valinta") >= 3
    put(page, x=0, y=2)
    page.evaluate("press()")
    page.wait_for_function("me.z > 0.5", timeout=1000)
    page.wait_for_function("me.z === 0", timeout=2000)
    got = heard(page)
    assert got[:2] == ["hyppy", "tomahdys"], got
    assert page.errors == []


def test_bars_pits_players_checkpoints_and_the_finish_each_sound(site, context):
    page = open_game(site, context)
    running(page)
    # A spinning bar: a kick.
    put(page, x=3, y=18)
    page.wait_for_function("me.knocks > 0", timeout=6000)
    assert "potku" in heard(page)
    # Between two stepping stones: the falling whistle, and no crowd's ooh (#337).
    put(page, x=-1.7, y=40, cp=1)
    page.wait_for_function("me.fall > 0", timeout=2000)
    assert heard(page)[:1] == ["putoaminen"] and "ohhoo" not in heard(page)
    page.wait_for_function("me.fall === 0", timeout=3000)
    # Another player running into this one.
    put(page, x=0, y=5)
    page.evaluate("const o = race.runners[1]; Object.assign(o, { kind: 'cpu', x: 0.3, y: 5, z: 0, vx: -4, vy: 0, fall: 0 }); o.ai.skill = 0")
    page.wait_for_function("heard.some(h => h[0] === 'osuma')", timeout=2000)
    page.evaluate("Object.assign(race.runners[1], { kind: 'net', x: -4, y: -3, vx: 0, vy: 0 })")
    # Over a checkpoint line, then over the finish.
    put(page, x=0, y=33, cp=0, vy=5)
    page.evaluate("input.y = 1")
    page.wait_for_function("me.cp === 1", timeout=2000)
    assert "valinta" in heard(page)
    put(page, x=0, y=139.5, vy=5, cp=4)
    page.evaluate("input.y = 1")
    page.wait_for_function("me.fin !== null", timeout=2000)
    assert "voitto" in heard(page)
    assert page.errors == []


def test_a_swinging_ball_whooshes_past_only_near_the_player(site, context):
    page = open_game(site, context)
    running(page)
    # The first ball (y 116) crosses the middle of the bridge at race time 0. The race is held
    # still, so only these calls swing it.
    page.evaluate("race.phase = 'wait'")
    put(page, x=0, y=60, cp=1)
    page.evaluate("swing = [true, swing[1], swing[2]]; whoosh(0)")
    assert heard(page) == []
    put(page, x=0, y=114, cp=4)
    page.evaluate("swing = [true, swing[1], swing[2]]; whoosh(0)")
    assert heard(page) == ["suhahdus"]
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        page.wait_for_function("race && race.phase === 'run'", timeout=6000)
        put(page, x=0, y=139.5, vy=5, cp=4)
        page.evaluate("input.y = 1; press()")
        page.wait_for_function("!race", timeout=12000)
        assert heard(page) == []
        assert page.inner_text("#result").startswith("Voitit!")
        assert page.errors == []
    finally:
        ctx.close()


def test_v2_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 3], ['voitot', 2], ['kisat', 5], ['ennatys', 61.2]]) localStorage.setItem('ai-pelit:kaaosrata:' + k, String(v));
    }""")
    page.reload()
    assert "Taso 3" in page.inner_text("#foe")
    assert "Ennätys" in page.inner_text("#stats")
    assert page.errors == []


def test_only_this_phones_runner_sounds_and_a_new_race_starts_quiet(site, context):
    page = open_game(site, context)
    running(page)
    put(page, x=0, y=2)
    # A computer runner jumping and then falling into a gap, at the same time as nothing else.
    page.evaluate("const o = race.runners[1]; Object.assign(o, { kind: 'cpu', x: -1.7, y: 40, z: 0, vx: 0, vy: 0, fall: 0, cp: 1 }); o.ai.skill = 0; jump(o)")
    page.wait_for_function("race.runners[1].fall > 0", timeout=2000)
    assert heard(page) == []
    # A new race forgets where the balls were: no whoosh before the player is anywhere near.
    page.evaluate("soloRace(); heard.splice(0)")
    assert page.evaluate("swing.length") == 0
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    assert "suhahdus" not in heard(page)
    assert page.errors == []


def test_without_the_sound_library_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/aanet.js", lambda route: route.abort())
        site.build(ROOT / "games")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.click("#go")
        page.wait_for_function("race && race.phase === 'run'", timeout=6000)
        page.evaluate("Object.assign(me, { x: 0, y: 139.5, z: 0, vx: 0, vy: 5, cp: 4 }); input.y = 1; press()")
        page.wait_for_function("!race", timeout=12000)
        assert page.inner_text("#result").startswith("Voitit!")
        assert page.errors == []
    finally:
        ctx.close()


def test_a_jump_down_into_a_gap_falls_without_a_landing_thud(site, context):
    page = open_game(site, context)
    running(page)
    # Up in the air above the gap between two stepping stones, coming down.
    put(page, x=-1.7, y=40, z=1, vz=-1, cp=1)
    page.wait_for_function("me.fall > 0", timeout=2000)
    page.wait_for_timeout(600)
    got = heard(page)
    assert got[:1] == ["putoaminen"] and "ohhoo" not in got, got
    assert "tomahdys" not in got
    assert page.errors == []


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/kaaosrata/v7")
