"""Aitajuoksu v7: recorded sounds from the shared library public/lib/aanet-2/ (#205, #211)."""

import json

import test_aitajuoksu_v5 as v5

URL = "games/aitajuoksu/v7/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

NAMES = ["pilli", "lahto", "askel", "askel2", "ponnistus", "suhahdus", "rima", "onnistui", "aplodit"]


def open_game(site, browser, **kw):
    old = v5.URL
    v5.URL = URL
    try:
        page = v5.open_game(site, browser, **kw)
    finally:
        v5.URL = old
    page.evaluate(SPY)
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def ready(page):
    """Starts a race and waits until the sounds can play (the menu's tap unlocked them)."""
    page.click("#go")
    page.wait_for_function(f"{json.dumps(NAMES)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('askel', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def test_a_race_sounds_from_the_gun_to_the_finish(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("race.cdT = race.gunAt - 0.001")
    page.wait_for_function("race.phase === 'run'", timeout=3000)
    assert played(page) == ["lahto"]
    page.evaluate("step(me, 1); step(me, 2)")
    assert played(page) == ["askel", "askel2"]
    page.evaluate("jump(me)")
    assert played(page) == ["ponnistus", "suhahdus"]
    # Into a hurdle without a jump: it falls with a clatter.
    page.evaluate("Object.assign(me, { x: HURDLES[1] - 0.3, v: 8, y: 0, vy: 0, stum: 0 })")
    page.wait_for_function("me.hits === 1", timeout=3000)
    assert "rima" in played(page)
    # The first finish is a record: the chime, then the crowd.
    page.evaluate("Object.assign(me, { x: TRACK - 0.2, v: 9 })")
    page.wait_for_function("me.fin !== null", timeout=3000)
    assert [n for n in played(page) if n in ("onnistui", "aplodit")] == ["onnistui", "aplodit"]
    assert page.errors == []


def test_a_slower_time_than_the_record_gets_no_applause(site, browser):
    page = open_game(site, browser)
    page.evaluate("localStorage.setItem('ai-pelit:aitajuoksu:ennatys', '0')")
    ready(page)
    page.evaluate("race.cdT = race.gunAt; Object.assign(me, { x: TRACK - 0.2, v: 9, down: 1023 })")
    page.wait_for_function("me.fin !== null", timeout=3000)
    got = played(page)
    assert "onnistui" in got and "aplodit" not in got, got
    assert page.errors == []


def test_a_false_start_blows_the_whistle(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("race.gunAt = 99; race.cdT = SET_AT + 0.1; press(1)")
    assert page.evaluate("race.phase") == "false"
    assert played(page) == ["pilli"]
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    v5.build(site)
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.evaluate(SPY)
        page.click("#go")
        page.evaluate("race.cdT = race.gunAt")
        page.wait_for_function("race.phase === 'run'", timeout=3000)
        page.evaluate("step(me, 1); jump(me)")
        page.evaluate("Object.assign(me, { x: TRACK - 0.2, v: 9, y: 0, vy: 0, down: 1023 })")
        page.wait_for_function("me.fin !== null", timeout=3000)
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v6_saves_are_read_as_they_are(site, browser):
    page = open_game(site, browser)
    page.evaluate("""() => {
      for (const [k, v] of [['juoksut', 5], ['voitot', 3], ['ennatys', 14.2]]) localStorage.setItem('ai-pelit:aitajuoksu:' + k, JSON.stringify(v));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Juoksut 5 · Voitot 3 · Ennätys 14,20 s"
    assert page.errors == []
