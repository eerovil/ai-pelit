"""Lentopallo in a phone-sized Chromium."""

from conftest import ROOT

URL = "games/lentopallo/v1/"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    return page


def test_eleven_points_wins_but_only_two_ahead(site, context):
    page = start(site, context)
    assert page.evaluate("[matchWinner(11, 9), matchWinner(11, 10), matchWinner(12, 10), matchWinner(9, 11), matchWinner(5, 3)]") == [0, -1, 0, 1, -1]


def test_the_players_serve_goes_over_the_net(site, context):
    page = start(site, context)
    assert page.evaluate("state === 'serve' && server === me && ball.held")
    page.evaluate("press(me)")
    page.wait_for_function("crossings >= 1", timeout=4000)
    assert page.evaluate("score.join('-')") == "0-0"


def test_a_ball_out_after_your_touch_is_the_opponents_point(site, context):
    page = start(site, context)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      last = me; touchSide = 1; touches = 0; cpu.x = 0.5;
      Object.assign(ball, { x: 4.8, y: 0.6, vx: 0.5, vy: -2 });
    }""")
    page.wait_for_function("state === 'point'", timeout=2000)
    assert page.evaluate("[score.join('-'), msg.s, server === cpu]") == ["0-1", "Ulos!", True]


def test_a_ball_down_on_the_opponents_side_is_your_point(site, context):
    page = start(site, context)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      last = me; touchSide = 1; touches = 0; cpu.x = 0.5;
      Object.assign(ball, { x: 3.5, y: 0.5, vx: 0, vy: -2 });
    }""")
    page.wait_for_function("state === 'point'", timeout=2000)
    assert page.evaluate("[score.join('-'), msg.s, server === me]") == ["1-0", "Pallo maassa!", True]


def test_a_fourth_touch_is_a_fault(site, context):
    page = start(site, context)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      touchSide = -1; touches = 3; last = me;
      hit(me);
    }""")
    assert page.evaluate("[score.join('-'), msg.s]") == ["0-1", "Neljä kosketusta!"]


def test_a_won_match_raises_the_level_on_the_phone(site, context):
    page = start(site, context)
    page.evaluate("score = [11, 4]; endMatch(true)")
    assert page.evaluate("localStorage.getItem('ai-pelit:lentopallo:taso')") == "2"
    assert "Voitit 11–4" in page.inner_text("#result")
    page.reload()
    assert "Taso 2" in page.inner_text("#foe")
# CI timing probe for #123, not to be merged
