"""Pituushyppy v7: recorded sounds from the shared library public/lib/aanet-1/ (#205)."""

import json

import test_pituushyppy_v5 as v5
import test_pituushyppy_v6 as v6

URL = "games/pituushyppy/v7/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


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


def test_a_jump_sounds_from_the_run_up_to_the_sand(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("['askel', 'askel2', 'ponnistus', 'hiekka', 'aplodit'].every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("th.t = 99; step(0.001); heard.splice(0)")
    page.evaluate("press(1); press(2)")
    assert played(page) == ["askel", "askel2"]
    # The first jump of the meet leads it: the sand, then the crowd claps.
    page.evaluate("go(9, 20, -0.05); quick()")
    got = played(page)
    assert got[0] == "ponnistus" and "hiekka" in got and got[-1] == "aplodit", got
    assert page.errors == []


def test_over_the_line_the_crowd_goes_ooh(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("AiPelitAanet.ready('ohhoo')", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.v = 9; th.x = 1; heard.splice(0); step(1 / 60)")
    assert played(page) == ["ohhoo"]
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


def test_v6_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['kisat', 5], ['voitot', 3], ['ennatys', 7.12]]) localStorage.setItem('ai-pelit:pituushyppy:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Kisat 5 · Voitot 3 · Ennätys 7,12 m"
    assert page.errors == []


def test_the_podium_still_stays_until_a_tap(site, context):
    old = v6.URL
    v6.URL = URL
    try:
        v6.test_alone_the_podium_stays_until_a_tap_after_the_ceremony(site, context)
    finally:
        v6.URL = old
