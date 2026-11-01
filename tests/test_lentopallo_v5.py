"""Lentopallo v5: recorded sounds from the shared library public/lib/aanet-2/ (#222)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/lentopallo/v5/"
SOUNDS = ["pilli", "naksu", "lyonti", "verkko", "suhahdus", "hiekka", "aplodit", "voitto", "tappio"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


@pytest.fixture
def game(site, context):
    shutil.copytree(ROOT / "games" / "lentopallo", site.games / "lentopallo")
    site.build()

    def start(ctx=context):
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.evaluate(SPY)
        page.click("#go")
        return page

    return start


def ready(page):
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('naksu', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_rally_sounds_from_the_serve_to_the_applause(game):
    page = game()
    ready(page)
    page.evaluate("server = mine; ball.held = true; tossed = false; state = 'serve'; press(mine)")
    assert played(page) == ["naksu"]
    # A dig, then a spike: the same slap, the spike harder.
    page.evaluate("""() => {
      ball.served = true; touchSide = 0; touches = 0; mine.y = 0; mine.intent = 'set';
      Object.assign(ball, { x: mine.x, y: 1.2 }); hit(mine);
    }""")
    assert played(page) == ["lyonti"]
    page.evaluate("""() => {
      mine.cd = 0; mine.y = 0; mine.vy = 0; jump(mine);
      mine.y = 0.6; Object.assign(ball, { x: mine.x, y: mine.y + 2.5 }); hit(mine);
    }""")
    assert played(page) == ["suhahdus", "lyonti"]
    # Into the net, then down in the sand: the whistle, then the crowd claps.
    page.evaluate("""() => {
      Object.assign(ball, { x: -0.3, y: 1.5, vx: 6, vy: 0, held: false }); stepBall(0.1, true);
    }""")
    assert played(page) == ["verkko"]
    page.evaluate("""() => {
      state = 'play'; last = mine; touchSide = 1; touches = 0;
      Object.assign(ball, { x: 3, y: 0.2, vx: 0, vy: -3 }); stepBall(0.1, true);
    }""")
    assert played(page) == ["hiekka", "pilli", "aplodit"]
    assert page.evaluate("state") == "point"
    page.evaluate("score = [11, 4]; endMatch(true)")
    assert played(page) == ["voitto"]
    page.evaluate("score = [4, 11]; endMatch(false)")
    assert played(page) == ["tappio"]
    assert page.errors == []


def test_a_fault_with_the_ball_up_has_no_sand(game):
    page = game()
    ready(page)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      touchSide = -1; touches = 3; last = mine; ball.y = 2; hit(mine);
    }""")
    assert played(page) == ["pilli", "aplodit"]
    assert page.evaluate("msg.s") == "Neljä kosketusta!"


def test_without_the_sound_files_it_still_plays_with_its_beeps(game, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = game(ctx)
        page.evaluate("""() => {
          server = mine; ball.held = true; tossed = false; state = 'serve'; press(mine);
          for (let i = 0; i < 60 * 20; i++) update(1 / 60);
          score = [11, 4]; endMatch(true);
        }""")
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v4_saves_are_read_as_they_are(game):
    page = game()
    page.evaluate("""() => {
      localStorage.setItem('ai-pelit:lentopallo:taso', '3');
      localStorage.setItem('ai-pelit:lentopallo:voitot', '2');
      localStorage.setItem('ai-pelit:lentopallo:haviot', '5');
    }""")
    page.reload()
    assert "Taso 3" in page.inner_text("#foe")
    assert page.inner_text("#stats").startswith("Voitot 2 · Häviöt 5")
    assert page.errors == []
