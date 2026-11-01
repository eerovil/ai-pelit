"""Pallorata v3 (#225): v2's ball run with recorded sounds from public/lib/aanet-2/ (#205)."""

import json
import shutil

import pytest

from conftest import ROOT

URL = "games/pallorata/v3/"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

NAMES = ["hyppy", "nousu", "valinta", "osuma", "putoaminen", "tomahdys", "rullaus"]


def open_game(site, browser, block_mp3=False):
    shutil.copytree(ROOT / "games" / "pallorata", site.games / "pallorata")
    site.build()
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                              service_workers="block")
    if block_mp3:
        ctx.route("**/*.mp3", lambda route: route.abort())
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    if page.evaluate("window.noWebgl === true"):
        ctx.close()
        pytest.skip("this Chromium has no WebGL")
    page.evaluate(SPY)
    return ctx, page


# On a busy host a frame can be slow, so a target placed once may be passed before the next frame:
# these keep putting it right at the ball until it is hit.
STAR_AT_BALL = """window.holdStar = setInterval(() => { const s = stars.find(s => s.visible);
  if (s) s.position.set(ball.x, ball.y, ball.z); }, 16)"""
BOOST_AT_BALL = """window.holdBoost = setInterval(() => { const i = Math.floor(-ball.z / 2);
  row(i).kind = row(i + 1).kind = 'boost'; }, 16)"""


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def start(page):
    """Starts a round with the ball kept on the track, and waits until the sounds can play."""
    page.click("#aloita")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    page.evaluate("window.keep = setInterval(() => { ball.aimX = row(Math.floor(-ball.z / 2)).cx; }, 16)")
    page.wait_for_function(f"{json.dumps(NAMES)}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


@pytest.fixture
def game(site, browser):
    ctx, page = open_game(site, browser)
    yield page
    ctx.close()


def test_rolling_sounds_with_the_speed_and_stops_in_the_air(game):
    page = game
    page.wait_for_timeout(300)
    assert page.evaluate("roll.vol") == 0  # the menu's ball rolls silently
    start(page)
    page.wait_for_function("roll.playing() && roll.vol > 0.3", timeout=3000)
    slow = page.evaluate("roll.rate")
    page.evaluate("ball.boost = 3")
    page.wait_for_function(f"roll.rate > {slow + 0.2}", timeout=3000)
    page.evaluate("clearInterval(keep); ball.aimX = 50")
    page.wait_for_function("round.phase !== 'run'", timeout=5000)
    page.wait_for_timeout(100)
    assert page.evaluate("roll.vol") == 0
    assert page.errors == []


def test_each_event_plays_its_sound(game):
    page = game
    start(page)
    # A turbo strip under the ball.
    page.evaluate("ball.boost = 0")
    page.evaluate(BOOST_AT_BALL)
    page.wait_for_function("ball.boost > 0", timeout=5000)
    page.evaluate("clearInterval(holdBoost)")
    assert "nousu" in played(page)
    # A star right at the ball.
    page.evaluate(STAR_AT_BALL)
    page.wait_for_function("round.stars > 0", timeout=5000)
    page.evaluate("clearInterval(holdStar)")
    assert "valinta" in played(page)
    # Thrown up off a ramp's end: the jump.
    page.evaluate("ball.ramp = true; ball.air = false")
    page.wait_for_function("ball.air", timeout=2000)
    assert "hyppy" in played(page)
    # Coming down hard onto a solid row: the landing thud.
    page.evaluate("""() => { const r = row(Math.floor(-ball.z / 2)); r.kind = 'flat';
      Object.assign(ball, { air: true, ramp: false, y: 0.5, vy: -7, x: r.cx, aimX: r.cx }); }""")
    page.wait_for_function("!ball.air", timeout=2000)
    assert "tomahdys" in played(page)
    # Off the edge: the falling whistle.
    page.evaluate("clearInterval(keep); ball.aimX = 50")
    page.wait_for_function("round.phase !== 'run'", timeout=5000)
    assert "putoaminen" in played(page)
    assert page.errors == []


def test_a_block_bump_plays_the_hit(game):
    page = game
    start(page)
    # Blocks come after row 120: make the track that far, and put the ball on a block's row (a
    # solid one). Each tick the block moves onto the ball's row just ahead of it (sp 0: it sits at
    # the row's middle, where the ball is kept).
    page.evaluate("""() => {
      row(300);
      window.target = blocks.find(b => b.i > 125);
      target.sp = 0; target.ph = 0;
      const r = row(target.i);
      Object.assign(ball, { z: -target.i * 2 - 0.05, x: r.cx, aimX: r.cx, y: 0.45, vy: 0, air: false, ramp: false });
      window.holdBlock = setInterval(() => { target.i = Math.floor(-ball.z / 2); target.mesh.position.z = ball.z - 0.3; }, 16);
    }""")
    page.wait_for_function("target.hit || round.phase !== 'run'", timeout=5000)
    assert page.evaluate("target.hit")
    assert "osuma" in played(page)
    assert page.errors == []


def test_without_the_sound_files_it_still_plays(site, browser):
    ctx, page = open_game(site, browser, block_mp3=True)
    try:
        page.click("#aloita")
        page.wait_for_function("round.phase === 'run' && -ball.z > 4", timeout=5000)
        page.evaluate("ball.aimX = 50")
        page.wait_for_function("round.phase === 'over'", timeout=5000)
        assert played(page) == []
        assert not page.evaluate("roll.playing()")
        assert page.errors == []
    finally:
        ctx.close()


def test_v2_saves_are_read_as_they_are(game):
    page = game
    page.evaluate("localStorage.setItem('ai-pelit:pallorata:ennatys', '321'); localStorage.setItem('ai-pelit:pallorata:pelit', '7')")
    page.reload()
    page.wait_for_function("window.drawn === true", timeout=15000)
    assert page.inner_text("#paras") == "Ennätys: 321 pistettä"
    page.click("#aloita")
    page.evaluate("ball.aimX = 50")
    page.wait_for_function("round.phase === 'over'", timeout=5000)
    assert page.evaluate("localStorage.getItem('ai-pelit:pallorata:pelit')") == "8"
    assert page.errors == []


def test_a_second_round_rolls_and_sounds_again(game):
    page = game
    start(page)
    page.wait_for_function("roll.vol > 0.3", timeout=3000)
    page.evaluate("clearInterval(keep); ball.aimX = 50")
    page.wait_for_function("round.phase === 'over'", timeout=5000)
    page.wait_for_function("roll.vol === 0", timeout=1000)
    played(page)
    page.click("#uudestaan")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    page.evaluate("window.keep = setInterval(() => { ball.aimX = row(Math.floor(-ball.z / 2)).cx; }, 16)")
    page.wait_for_function("roll.playing() && roll.vol > 0.3", timeout=3000)
    # A star and a turbo in the same frame both sound.
    page.evaluate("ball.boost = 0")
    page.evaluate(STAR_AT_BALL)
    page.evaluate(BOOST_AT_BALL)
    page.wait_for_function("round.stars > 0 && ball.boost > 0", timeout=5000)
    got = played(page)
    assert "valinta" in got and "nousu" in got, got
    assert page.errors == []
