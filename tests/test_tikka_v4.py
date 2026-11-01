"""Tikanheitto v4: recorded sounds from the shared library public/lib/aanet-2/ (#230)."""

import test_tikka_v3 as v3

URL = "games/tikka/v4/"
NAMES = "['suhahdus', 'puu', 'virhe', 'yleiso', 'voitto']"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


def open_game(site, context, saved=None):
    old = v3.URL
    v3.URL = URL
    try:
        page = v3.open_game(site, context, saved)
    finally:
        v3.URL = old
    page.evaluate(SPY)
    return page


def sound_on(page):
    page.wait_for_function(f"{NAMES}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('puu', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def throw(page, mx, my):
    page.evaluate(f"throwAt({mx}, {my}); run(() => flying !== null, 2)")


def test_a_throw_whooshes_and_hits_wood_and_a_full_turn_gets_the_crowd(site, context):
    page = open_game(site, context)
    page.click("#go")
    sound_on(page)
    throw(page, 0, 0)
    assert played(page) == ["suhahdus", "puu"]
    throw(page, 0, 0)
    throw(page, 0, 0)   # 30, the most there is: the crowd shouts
    assert played(page) == ["suhahdus", "puu", "suhahdus", "puu", "yleiso"]
    # Off the board: the same wood, only quieter.
    page.evaluate("run(() => pause > 0, 3)")
    throw(page, 0, 300)
    assert page.evaluate("heard.filter(h => h[1]).map(h => h[0])") == ["suhahdus", "puu"]
    assert page.evaluate("players[0].score") == 30
    assert page.errors == []


def test_501_bust_buzzes_and_the_win_plays_its_tune(site, context):
    page = open_game(site, context, {"vastus": "kova"})
    page.click("#go501")
    sound_on(page)
    page.evaluate("players[0].score = turnStart = 70")
    throw(page, 0, -135)   # 20, 50 left
    throw(page, 0, -103)   # T20 would go under nought
    assert played(page) == ["suhahdus", "puu", "suhahdus", "puu", "virhe"]
    # Exactly nought wins: the tune.
    page = open_game(site, context)
    page.click("#go501")
    sound_on(page)
    page.evaluate("players[0].score = turnStart = 32")
    throw(page, *page.evaluate("[spotOf(16, 2).x, spotOf(16, 2).y]"))   # D16
    assert played(page)[-1] == "voitto"
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        for _ in range(3):
            throw(page, 0, 0)
        assert page.evaluate("players[0].score") == 30
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context, {"mokki": 231, "ennatys": 412, "voitot": 3, "vapaa": "darts"})
    assert page.inner_text("#stats") == "Ennätykset: Mökkitikka 231 p · Pistekisa 412 p · Voittoja tietokoneesta 3"
    page.click("#frees button[data-b=darts]")
    assert page.evaluate("freeBoard") == "darts"
    assert page.errors == []
