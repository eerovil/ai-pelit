"""Lentopallo v3: harder. A player who stands still and only knocks the ball back loses (#36)."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/lentopallo/v3/"


def alone(site, context, mode="1v1"):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#m1" if mode == "1v1" else "#m2")
    page.click("#go")
    return page


# A player who never moves from x and sends every ball straight back over, sped up: points won and lost.
STILL = """([X, mode, n]) => {
  level = 1; newMatch(mode);
  let won = 0, lost = 0, prev = [0, 0];
  for (let i = 0; i < 60 * 60 * 30 && won + lost < n; i++) {
    if (state === 'serve' && server === mine) press(mine);
    if (state === 'serve' || state === 'play') { mine.x = X; input.right = true; }
    update(1 / 60);
    if (state === 'done' || state === 'menu') { newMatch(mode); prev = [0, 0]; }
    if (score[0] > prev[0]) won++;
    if (score[1] > prev[1]) lost++;
    prev = score.slice();
  }
  return [won, lost];
}"""


def test_standing_still_loses_on_level_one(site, context):
    page = alone(site, context)
    for mode in ("1v1", "2v2"):
        won, lost = page.evaluate(STILL, [-2.0, mode, 30])
        assert won + lost == 30
        assert won <= 8, (mode, won, lost)


def test_the_computer_sends_the_ball_where_nobody_stands(site, context):
    page = alone(site, context)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      const foe = players[1]; foe.aim = 1; foe.x = 2.0; mine.x = -2.0;
      touchSide = 1; touches = 2; last = foe;
      Object.assign(ball, { x: 2.0, y: 2.0, vx: 0, vy: -1 });
      hit(foe);
    }""")
    # The ball comes down well away from the player, and inside the court.
    land = page.evaluate("predict(0.2).x")
    assert abs(land - -2.0) > 1.0 and -4.0 < land < 0


def test_a_ball_dropping_at_the_net_is_still_played(site, context):
    page = alone(site, context, "2v2")
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      const [, a, , b] = players; a.x = 1.5; b.x = 3.1; b.brain.wait = 0; b.brain.decided = false;
      touchSide = 1; touches = 1; last = a;
      Object.assign(ball, { x: 0.4, y: 3.0, vx: 0, vy: 0 });
    }""")
    page.evaluate("for (let i = 0; i < 30; i++) cpuThink(players[3], 1 / 60), stepPlayer(players[3], 1 / 60)")
    # The partner runs to the net for it instead of back to its own spot.
    assert page.evaluate("players[3].x") < 2.7


def test_v2s_saves_carry_over(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + "games/lentopallo/v2/")
    page.evaluate("""localStorage.setItem('ai-pelit:lentopallo:taso', '4');
      localStorage.setItem('ai-pelit:lentopallo:muoto', '"2v2"');
      localStorage.setItem('ai-pelit:lentopallo:kaverit', '{"voitot":2,"haviot":1}')""")
    page.goto(site.url + URL)
    assert "Taso 4" in page.inner_text("#foe")
    assert "Kavereita vastaan 2–1" in page.inner_text("#stats")
    assert page.evaluate("mode") == "2v2"


def test_two_phones_still_play_in_a_room(site, browser):
    site.build(ROOT / "games")
    relay, pages = Relay(), []
    for name in ("Eero", "Aino"):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host, guest = pages
    host.click("#m1")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    guest.wait_for_function("mine && players.length === 2 && mine.side === 1")
    host.evaluate("score = [11, 3]; state = 'point'; pauseT = 0")
    guest.wait_for_function("state === 'done' && document.querySelector('#aipr-result').innerText.length > 0")
    assert guest.locator("#aipr-result").inner_text() == "Häviö 3–11"
    assert host.errors == guest.errors == []


def test_a_new_match_after_a_win_is_against_a_stronger_opponent(site, context):
    page = alone(site, context)
    before = page.evaluate("[players[1].speed, players[1].err, players[1].aim]")
    page.evaluate("score = [11, 5]; state = 'point'; pauseT = 0; update(1 / 60)")
    assert page.evaluate("state") == "done"
    assert "Voitit 11–5" in page.inner_text("#result")
    page.click("#go")
    after = page.evaluate("[players[1].speed, players[1].err, players[1].aim, level, score.join('-'), state]")
    assert after[3:] == [2, "0-0", "serve"]
    assert after[0] > before[0] and after[1] < before[1] and after[2] > before[2]
    # The still player still loses against the new opponent.
    won, lost = page.evaluate(STILL.replace("level = 1;", "level = 2;"), [-2.0, "1v1", 20])
    assert won <= 6


def test_plays_on_a_390_px_phone(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.click("#m2")
    page.click("#go")
    page.evaluate("press(mine)")
    page.wait_for_function("crossings >= 1", timeout=4000)
    # The whole court and the buttons fit: both end lines and the jump button are on the screen.
    assert page.evaluate("sx(-COURT) > 0 && sx(COURT) < W && buttons[2].x + buttons[2].r <= W")
    assert errors == []
    ctx.close()
