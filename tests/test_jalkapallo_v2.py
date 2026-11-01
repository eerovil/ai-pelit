"""Jalkapallo v2: recorded sounds from the shared library public/lib/aanet-2/ (#215)."""

import pytest

import test_jalkapallo as v1
from test_jalkapallo import STILL, room  # noqa: F401  (room is a fixture)

URL = "games/jalkapallo/v2/"
SOUNDS = ['pilli', 'pilli2', 'potku', 'verkko', 'yleiso', 'suhahdus', 'puu', 'osuma', 'ohhoo', 'metalli']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


@pytest.fixture(autouse=True)
def v2_url():
    old = v1.URL
    v1.URL = URL
    yield
    v1.URL = old


def start(site, context, ready=True):
    page = v1.start(site, context)
    page.evaluate(SPY)
    if ready:
        page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
        page.evaluate("heard.splice(0)")
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_goal_sounds_the_whistle_the_net_and_the_crowd_then_the_kickoff_whistle(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[5].x = 12; players[0].x = 1; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[0].input.x = 0.1; ctrls[0].input.y = 1; press(ctrls[0], 'shootDown'); shootUp(ctrls[0], 0.4)")
    assert played(page) == ["potku"]
    page.evaluate("run(() => state === 'play', 3)")
    assert page.evaluate("state") == "goal"
    assert played(page) == ["pilli", "verkko", "yleiso"]
    page.evaluate("run(() => state === 'goal', 4)")
    assert played(page) == ["pilli"]
    assert page.errors == []


def test_the_final_whistle_blows_twice(site, context):
    page = start(site, context)
    page.evaluate("state = 'play'; clock = 0.01; update(1 / 60)")
    assert played(page) == ["pilli2"]


def test_a_tackle_whooshes(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[3].x = 0; players[3].y = 0; take(players[3]); players[0].x = 0; players[0].y = -2.2")
    page.evaluate("press(ctrls[0], 'pass')")
    assert played(page) == ["suhahdus"]


def test_a_keeper_save_is_a_hit_and_an_ooh(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("const k = players[5]; k.x = 0; k.y = 21.5; k.save = 1; Object.assign(ball, { x: 0, y: 21, z: 0.3, vx: 0, vy: 20, vz: 0, shot: true, from: players[0], fromT: 0 })")
    page.evaluate("pickUp()")
    assert played(page) == ["osuma", "ohhoo"]


def test_the_ball_knocks_on_the_side_boards_and_rings_off_a_post(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("Object.assign(ball, { x: WID / 2 - 0.3, y: 0, z: 0, vx: 10, vy: 0, vz: 0, from: null, fromT: 0 }); stepBall(1 / 60, true)")
    assert played(page) == ["puu"]
    page.evaluate("Object.assign(ball, { x: GOAL / 2, y: LEN / 2 - 0.3, z: 0, vx: 0, vy: 10, vz: 0, from: null, fromT: 0 }); stepBall(1 / 60, true)")
    assert played(page) == ["metalli"]
    assert page.evaluate("ball.vy < 0 && score.join('-') === '0-0'")


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = start(site, ctx, ready=False)
        page.evaluate("state = 'play'; clock = 0.01")
        page.evaluate("run(() => state !== 'done', 4)")
        assert page.inner_text("#result") != ""
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v1_saves_are_read_as_they_are(site, context):
    page = start(site, context, ready=False)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 3], ['voitot', 2], ['haviot', 1], ['tasapelit', 4]]) localStorage.setItem('ai-pelit:jalkapallo:' + k, JSON.stringify(v));
    }""")
    page.goto(page.url)
    assert "Taso 3" in page.inner_text("#foe")
    assert page.evaluate("[level, wins, losses, draws]") == [3, 2, 1, 4]
    assert page.errors == []


# v1's play, unchanged in v2.
test_a_shot_at_an_empty_goal_scores_and_the_other_team_kicks_off = v1.test_a_shot_at_an_empty_goal_scores_and_the_other_team_kicks_off
test_the_keeper_holds_a_soft_shot = v1.test_the_keeper_holds_a_soft_shot
test_a_tackle_takes_the_ball = v1.test_a_tackle_takes_the_ball
test_the_final_whistle_ends_the_match_and_saves_it = v1.test_the_final_whistle_ends_the_match_and_saves_it
test_the_computer_plays_a_whole_match_on_its_own = v1.test_the_computer_plays_a_whole_match_on_its_own
test_two_phones_play_against_each_other_with_computer_teammates = v1.test_two_phones_play_against_each_other_with_computer_teammates
test_a_guest_that_reloads_mid_match_gets_its_player_back = v1.test_a_guest_that_reloads_mid_match_gets_its_player_back
