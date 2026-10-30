"""Jalkapallo: 3 vs 3 football from above, against the computer or 2-6 phones in one room.

Each phone is its own Chromium context; the room relay is `Relay` from test_rooms_lib.
"""

import json

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/jalkapallo/v1/"

# Steps the match by hand, 1/60 s at a time, while cond() holds, at most max seconds.
RUN = "() => { window.run = (cond, max = 5) => { for (let t = 0; t < max && cond(); t += 1 / 60) update(1 / 60); }; }"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    return page


# Play on, with nobody moving unless a test moves them: the computer's players are steered by a
# phone that is never there.
STILL = """() => {
  state = 'play'; owner = null;
  ctrls[0].fixed = 0; ctrls[0].p = players[0];
  for (const p of players.slice(1)) { ctrls.push({ id: 'x' + players.indexOf(p), t: p.t, fixed: players.indexOf(p), p, input: newInput() }); }
  for (const p of players) { p.vx = p.vy = 0; p.x = (players.indexOf(p) - 2.5) * 4; p.y = p.t ? 10 : -10; }
}"""


def test_the_menu_starts_a_three_against_three_match(site, context):
    page = start(site, context)
    assert page.evaluate("[players.length, players.filter(p => p.keeper).length, ctrls.length, clock]") == [6, 2, 1, 180]
    assert page.evaluate("state") == "kickoff"
    # Whoever kicks off has the ball on the centre spot, everyone else in their own half.
    assert page.evaluate("owner.slot === 0 && owner.t === kickoffTeam")
    assert page.evaluate("players.every(p => p === owner || p.y * fwd(p.t) < 0)")
    assert page.errors == []


def test_the_phone_steers_the_field_player_nearest_the_ball_never_the_keeper(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("ctrls[0].fixed = -1; ctrls = ctrls.slice(0, 1)")
    page.evaluate("Object.assign(ball, { x: 0, y: -21, vx: 0, vy: 0, z: 0 }); players[2].x = 0; players[2].y = -22; players[0].x = 10; players[0].y = 15; players[1].x = 3; players[1].y = -15")
    page.evaluate("for (const p of players.slice(3)) { p.x = 14; p.y = 20; }")
    page.evaluate("autoSwitch(ctrls[0], 1)")
    assert page.evaluate("players.indexOf(ctrls[0].p)") == 1
    # A pass to a teammate gives the phone the player who got it.
    page.evaluate("take(players[0])")
    assert page.evaluate("players.indexOf(ctrls[0].p)") == 0


def test_a_pass_goes_to_the_teammate_it_points_at(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[0].x = 0; players[0].y = 0; players[1].x = 8; players[1].y = 6; players[2].x = -8; players[2].y = 2; take(players[0])")
    page.evaluate("ctrls[0].input.x = 1; ctrls[0].input.y = 0.6; press(ctrls[0], 'pass')")
    page.evaluate("run(() => owner === null, 3)")
    assert page.evaluate("players.indexOf(owner)") == 1


def test_a_shot_at_an_empty_goal_scores_and_the_other_team_kicks_off(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[5].x = 12; players[0].x = 1; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[0].input.x = 0.1; ctrls[0].input.y = 1; press(ctrls[0], 'shootDown'); shootUp(ctrls[0], 0.4)")
    page.evaluate("run(() => state === 'play', 3)")
    assert page.evaluate("[state, score.join('-'), msg.by]") == ["goal", "1-0", "me"]
    page.evaluate("run(() => state === 'goal', 4)")
    assert page.evaluate("[state, owner.t]") == ["kickoff", 1]


def test_a_shot_roughly_at_the_goal_is_pulled_inside_the_posts(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[0].x = 6; players[0].y = 10; take(players[0])")
    # Facing up the pitch from 6 m right of the goal's middle: the shot still heads between the posts.
    cross = page.evaluate("shoot(players[0], 0, 1, 0.5); const t = (LEN / 2 - ball.y) / ball.vy; ball.x + ball.vx * t")
    assert abs(cross) < 3


def test_the_keeper_holds_a_soft_shot(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("const k = players[5]; k.x = 0; k.y = 21.5; players[0].x = 0; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[5].input.x = 0; shoot(players[0], 0, 1, 0)")
    page.evaluate("run(() => owner === null && state === 'play', 2)")
    assert page.evaluate("[players.indexOf(owner), score.join('-')]") == [5, "0-0"]


def test_a_tackle_takes_the_ball(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[3].x = 0; players[3].y = 0; players[3].fy = -1; take(players[3]); players[0].x = 0; players[0].y = -2.2; players[0].fx = 0; players[0].fy = 1")
    page.evaluate("stepBall(1 / 60, true); press(ctrls[0], 'pass')")
    assert page.evaluate("players[0].lunge > 0")
    page.evaluate("ctrls[0].input.y = 1; run(() => owner !== players[0], 0.4)")
    assert page.evaluate("players.indexOf(owner)") == 0
    assert page.evaluate("players[3].stun > 0")


def test_the_final_whistle_ends_the_match_and_saves_it(site, context):
    page = start(site, context)
    page.evaluate("state = 'play'; score = [2, 1]; clock = 0.01")
    page.evaluate("run(() => state !== 'done', 4)")
    assert page.inner_text("#result") == "Voitit 2–1! 🏆"
    assert page.evaluate("[load('taso', 0), load('voitot', 0)]") == [2, 1]
    assert "Taso 2" in page.inner_text("#foe")
    page.click("#go")
    page.evaluate("state = 'play'; score = [1, 1]; clock = 0.01")
    page.evaluate("run(() => state !== 'done', 4)")
    assert page.inner_text("#result") == "Tasapeli 1–1"
    assert "Tasapelit 1" in page.inner_text("#stats")


def test_the_computer_plays_a_whole_match_on_its_own(site, context):
    page = start(site, context)
    kicks = page.evaluate("ctrls = []; level = 4; run(() => state !== 'done', 200); players.reduce((n, p) => n + p.kicks, 0)")
    assert page.evaluate("state") == "done"
    assert kicks > 20
    assert page.errors == []


@pytest.fixture
def room(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        return page

    def play(*names):
        host = phone(names[0])
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
        code = host.evaluate("AiPelitRooms.code")
        guests = []
        for n in names[1:]:
            g = phone(n)
            g.click("#multi")
            g.fill("#aipr-codeIn", code)
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
            guests.append(g)
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
        host.click("#aipr-start")
        for p in [host, *guests]:
            p.wait_for_function("players.length === 6 && (state === 'kickoff' || state === 'play')")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def test_two_phones_play_against_each_other_with_computer_teammates(room):
    host, [guest] = room("Eero", "Aino")
    assert host.evaluate("players.map(p => [p.t, p.name, p.id ? 'phone' : 'cpu'])") == [
        [0, "Eero", "phone"], [0, "Aino", "cpu"], [0, "Onni", "cpu"],
        [1, "Aino", "phone"], [1, "Sammal", "cpu"], [1, "Kettu", "cpu"]]
    assert host.evaluate("ctrls.map(k => [k.t, k.fixed])") == [[0, -1], [1, -1]]
    # Each phone sees its own team attacking up the screen: the guest's pitch is turned round.
    assert host.evaluate("view") == 1 and guest.evaluate("[view, myTeam]") == [-1, 1]
    # The guest's joystick up the screen runs its player towards the host's goal (down the world).
    host.evaluate("state = 'play'; owner = null; ball.x = 0; ball.y = 0; for (const p of players) { p.x = (p.slot - 1) * 5; p.y = p.t ? 6 : -6; } ctrls[1].switchT = 99")
    guest.wait_for_function("myPlayer() !== null")
    start = host.evaluate("ctrls[1].p.y")
    guest.evaluate("input.jx = 0; input.jy = view")  # what setStick() makes of a thumb pushed up
    host.wait_for_function(f"ctrls[1].p.y < {start} - 1.5", timeout=3000)
    guest.evaluate("input.jy = 0")
    # The guest's player shows on the guest's own phone with its yellow ring.
    guest.wait_for_function("myPlayer() && myPlayer().t === 1")
    # The guest's pass button reaches the host: with the ball, its player passes.
    host.evaluate("const p = ctrls[1].p; ball.x = p.x; ball.y = p.y; take(p); ctrls[1].switchT = 5")
    guest.wait_for_function("owner && owner === myPlayer()")
    kicks = host.evaluate("ctrls[1].p.kicks")
    guest.evaluate("act('pass')")
    host.wait_for_function(f"players.filter(p => p.t === 1).reduce((n, p) => n + p.kicks, 0) > {kicks}", timeout=3000)
    # The match ends on the host; both phones hear it once and go back to the room.
    host.evaluate("score = [1, 3]; state = 'full'; pauseT = 0")
    for p, res, saved in [(host, "Häviö 1–3", '{"voitot":0,"haviot":1,"tasapelit":0}'), (guest, "Voitto 3–1! 🏆", '{"voitot":1,"haviot":0,"tasapelit":0}')]:
        p.wait_for_function("state === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
        assert p.evaluate("localStorage.getItem('ai-pelit:jalkapallo:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_four_phones_each_keep_their_own_player_and_the_computer_keeps_goal(room):
    host, guests = room("Eero", "Aino", "Iida", "Onni")
    assert host.evaluate("players.map(p => [p.t, p.slot, p.id ? 'phone' : 'cpu'])") == [
        [0, 0, "phone"], [0, 1, "phone"], [0, 2, "cpu"], [1, 0, "phone"], [1, 1, "phone"], [1, 2, "cpu"]]
    assert host.evaluate("ctrls.map(k => [k.t, k.fixed])") == [[0, 0], [0, 1], [1, 3], [1, 4]]
    assert [g.evaluate("myTeam") for g in guests] == [1, 0, 1]
    # Fixed players do not switch, however near the ball another one is.
    host.evaluate("state = 'play'; owner = null; Object.assign(ball, { x: 0, y: 0, vx: 0, vy: 0 }); players[0].x = 12; players[1].x = 0.2; players[1].y = -0.1")
    host.evaluate("autoSwitch(ctrls[0], 1)")
    assert host.evaluate("ctrls[0].p === players[0]")
    assert host.errors == [] and all(g.errors == [] for g in guests)


def test_six_phones_play_every_spot(room):
    host, guests = room("A", "B", "C", "D", "E", "F")
    assert host.evaluate("players.every(p => p.id)") is True
    assert host.evaluate("ctrls.map(k => k.fixed)") == [0, 1, 2, 3, 4, 5]
    assert host.errors == [] and all(g.errors == [] for g in guests)


def test_a_phone_let_go_is_played_by_the_computer(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("ctrls.find(k => k.t === 1).away === true")
    host.wait_for_timeout(300)
    assert host.evaluate("players.filter(p => p.t === 1).every(p => !p.ctl)")
    assert host.errors == third.errors == []


# ---------- Sideways (#95) ----------

LANDSCAPE = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def phone(site, browser):
    site.build(ROOT / "games")
    contexts = []

    def open_at(width, height):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.evaluate("localStorage.setItem('ai-pelit:jalkapallo:kaverit', '{\"voitot\":2,\"haviot\":1,\"tasapelit\":1}')")
        page.reload()
        page.evaluate(RUN)
        return page

    yield open_at
    for ctx in contexts:
        ctx.close()


def inside(box, width, height):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height


@pytest.mark.parametrize("size", LANDSCAPE)
def test_the_menu_fits_sideways(phone, size):
    w, h = size
    page = phone(w, h)
    page.evaluate("showMenu('Voitit 3–2! 🏆', 'win')")
    for sel in ("#menu h1", "#result", "#foe", "#go", "#multi", "#stats", "#menu .help.short", "#ai-pelit-back"):
        box = page.locator(sel).bounding_box()
        assert box and inside(box, w, h), (sel, box)
    assert not page.locator("#menu .help.long").is_visible()
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    page.click("#multi")
    page.wait_for_selector("#aipr-create", state="visible")
    assert page.errors == []


def test_portrait_shows_the_long_help(phone):
    page = phone(360, 740)
    assert page.locator("#menu .help.long").is_visible()
    assert not page.locator("#menu .help.short").is_visible()


def test_sideways_the_pitch_runs_across_and_survives_turning_the_phone(phone):
    page = phone(740, 360)
    page.click("#go")
    assert page.evaluate("wide")
    # The goal this phone attacks is to the right, and the controls sit in the lower corners.
    assert page.evaluate("P(0, LEN / 2)[0] > P(0, -LEN / 2)[0]")
    assert page.evaluate("""buttons.every(b => b.x - b.r >= 0 && b.x + b.r <= W && b.y + b.r <= H && b.x > W * 2 / 3)
      && stickHome.x < W / 3 && stickHome.y > H / 2""")
    # A thumb pushed right on the joystick runs towards that goal.
    page.evaluate(STILL)
    page.evaluate("stick.id = 1; stick.dx = 40; stick.dy = 0; setStick()")
    assert page.evaluate("[Math.round(input.jx * 10), Math.round(input.jy * 10)]") == [0, 9]
    y0 = page.evaluate("players[0].y")
    page.evaluate("run(() => true, 0.5)")
    assert page.evaluate("players[0].y") > y0 + 2
    page.evaluate("stick.id = null; stick.dx = 0; setStick(); score = [2, 1]")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("W === 360 && !wide")
    assert page.evaluate("[score.join('-'), state, players.length]") == ["2-1", "play", 6]
    assert page.evaluate("P(0, LEN / 2)[1] < P(0, -LEN / 2)[1]")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("W === 740 && wide")
    assert page.evaluate("[score.join('-'), state]") == ["2-1", "play"]
    assert page.errors == []


def test_controls_fit_a_390_px_phone(phone):
    page = phone(390, 844)
    page.click("#go")
    assert page.evaluate("""!wide && buttons.every(b => b.x - b.r >= 0 && b.x + b.r <= W && b.y - b.r >= ctrlTop && b.y + b.r <= H)
      && stickHome.x + STICK_R < buttons[0].x - buttons[0].r && stickHome.y + STICK_R <= H""")
    # The two buttons do not overlap each other.
    assert page.evaluate("Math.hypot(buttons[0].x - buttons[1].x, buttons[0].y - buttons[1].y) > buttons[0].r + buttons[1].r")
    assert page.errors == []


def test_two_tackles_at_once_give_the_ball_to_one(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("""() => { players[3].x = 0; players[3].y = 0; players[3].fx = 0; players[3].fy = -1; take(players[3]);
      for (let i = 0; i < 20; i++) stepBall(1 / 60, true);
      for (const i of [0, 1]) { const p = players[i]; p.x = i ? 0.9 : -0.9; p.y = -1.6; p.fx = i ? -0.5 : 0.5; p.fy = 0.86; }
      press(ctrls[0], 'pass'); press(ctrls[1], 'shootDown'); }""")
    page.evaluate("run(() => owner === players[3], 0.4)")
    assert page.evaluate("players.indexOf(owner)") in (0, 1)
    assert page.errors == []


def test_buttons_without_the_ball_at_the_kickoff_do_nothing(site, context):
    page = start(site, context)
    page.evaluate("kickoff(1)")
    page.evaluate("press(ctrls[0], 'pass'); press(ctrls[0], 'shootDown'); shootUp(ctrls[0], 1)")
    assert page.evaluate("[state, owner.t, ctrls[0].p.lunge]") == ["kickoff", 1, 0]
    assert page.errors == []


def test_a_guest_that_reloads_mid_match_gets_its_player_back(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("state = 'play'; score = [1, 0]")
    guest.reload()
    guest.wait_for_function("players.length === 6 && myTeam === 1 && score[0] === 1", timeout=8000)
    guest.wait_for_function("myPlayer() && myPlayer().t === 1", timeout=4000)
    # Its joystick moves its player on the host again.
    host.evaluate("ctrls[1].switchT = 99")
    start = host.evaluate("ctrls[1].p.y")
    guest.evaluate("input.jx = 0; input.jy = -1")
    host.wait_for_function(f"ctrls[1].p.y < {start} - 1", timeout=3000)
    assert host.errors == guest.errors == []
