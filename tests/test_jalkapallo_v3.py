"""Jalkapallo v2: recorded sounds from the shared library public/lib/aanet-2/ (#215).

Each phone is its own Chromium context; the room relay is `Relay` from test_rooms_lib.
"""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/jalkapallo/v3/"
SOUNDS = ['onnistui', 'pilli', 'pilli2', 'potku', 'verkko', 'suhahdus', 'puu', 'osuma', 'metalli']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Steps the match by hand, 1/60 s at a time, while cond() holds, at most max seconds.
RUN = "() => { window.run = (cond, max = 5) => { for (let t = 0; t < max && cond(); t += 1 / 60) update(1 / 60); }; }"

# Play on, with nobody moving unless a test moves them: the computer's players are steered by a
# phone that is never there.
STILL = """() => {
  state = 'play'; owner = null;
  ctrls[0].fixed = 0; ctrls[0].p = players[0];
  for (const p of players.slice(1)) { ctrls.push({ id: 'x' + players.indexOf(p), t: p.t, fixed: players.indexOf(p), p, input: newInput() }); }
  for (const p of players) { p.vx = p.vy = 0; p.x = (players.indexOf(p) - 2.5) * 4; p.y = p.t ? 10 : -10; }
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    return page


def start(site, context, ready=True):
    page = open_game(site, context)
    page.evaluate(SPY)
    if ready:
        page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
        page.evaluate("heard.splice(0)")
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_goal_sounds_the_whistle_the_net_and_a_blip_then_the_kickoff_whistle(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("players[5].x = 12; players[0].x = 1; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[0].input.x = 0.1; ctrls[0].input.y = 1; press(ctrls[0], 'shootDown'); shootUp(ctrls[0], 0.4)")
    assert played(page) == ["potku"]
    page.evaluate("run(() => state === 'play', 3)")
    assert page.evaluate("state") == "goal"
    assert played(page) == ["pilli", "verkko", "onnistui"]
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


def test_a_keeper_save_is_a_hit_and_no_ooh(site, context):
    page = start(site, context)
    page.evaluate(STILL)
    page.evaluate("const k = players[5]; k.x = 0; k.y = 21.5; k.save = 1; Object.assign(ball, { x: 0, y: 21, z: 0.3, vx: 0, vy: 20, vz: 0, shot: true, from: players[0], fromT: 0 })")
    page.evaluate("pickUp()")
    assert played(page) == ["osuma"]


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
def test_a_shot_at_an_empty_goal_scores_and_the_other_team_kicks_off(site, context):
    page = open_game(site, context)
    page.evaluate(STILL)
    page.evaluate("players[5].x = 12; players[0].x = 1; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[0].input.x = 0.1; ctrls[0].input.y = 1; press(ctrls[0], 'shootDown'); shootUp(ctrls[0], 0.4)")
    page.evaluate("run(() => state === 'play', 3)")
    assert page.evaluate("[state, score.join('-'), msg.by]") == ["goal", "1-0", "me"]
    page.evaluate("run(() => state === 'goal', 4)")
    assert page.evaluate("[state, owner.t]") == ["kickoff", 1]


def test_the_keeper_holds_a_soft_shot(site, context):
    page = open_game(site, context)
    page.evaluate(STILL)
    page.evaluate("const k = players[5]; k.x = 0; k.y = 21.5; players[0].x = 0; players[0].y = 12; players[0].fx = 0; players[0].fy = 1; take(players[0])")
    page.evaluate("ctrls[5].input.x = 0; shoot(players[0], 0, 1, 0)")
    page.evaluate("run(() => owner === null && state === 'play', 2)")
    assert page.evaluate("[players.indexOf(owner), score.join('-')]") == [5, "0-0"]


def test_a_tackle_takes_the_ball(site, context):
    page = open_game(site, context)
    page.evaluate(STILL)
    page.evaluate("players[3].x = 0; players[3].y = 0; players[3].fy = -1; take(players[3]); players[0].x = 0; players[0].y = -2.2; players[0].fx = 0; players[0].fy = 1")
    page.evaluate("stepBall(1 / 60, true); press(ctrls[0], 'pass')")
    assert page.evaluate("players[0].lunge > 0")
    page.evaluate("ctrls[0].input.y = 1; run(() => owner !== players[0], 0.4)")
    assert page.evaluate("players.indexOf(owner)") == 0
    assert page.evaluate("players[3].stun > 0")


def test_the_final_whistle_ends_the_match_and_saves_it(site, context):
    page = open_game(site, context)
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
    page = open_game(site, context)
    kicks = page.evaluate("ctrls = []; level = 4; run(() => state !== 'done', 200); players.reduce((n, p) => n + p.kicks, 0)")
    assert page.evaluate("state") == "done"
    assert kicks > 20
    assert page.errors == []


def test_two_phones_play_against_each_other_with_computer_teammates(room):
    host, [guest] = room("Eero", "Aino")
    # A phone alone on its team owns no player: it steers whichever one is nearest the ball.
    assert host.evaluate("players.map(p => [p.t, p.name, p.id ? 'phone' : 'cpu'])") == [
        [0, "Ville", "cpu"], [0, "Aino", "cpu"], [0, "Onni", "cpu"],
        [1, "Kurki", "cpu"], [1, "Sammal", "cpu"], [1, "Kettu", "cpu"]]
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


def test_a_guest_hears_the_hosts_save_tackle_and_post(room):
    host, [guest] = room("Eero", "Aino")
    guest.evaluate(SPY)
    guest.click("#c", position={"x": 180, "y": 300})  # the tap that turns sound on
    guest.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    guest.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
    host.evaluate("state = 'play'; owner = null; for (const k of ctrls) k.switchT = 99")
    guest.wait_for_function("state === 'play'")
    guest.evaluate("heard.splice(0)")
    # A keeper's save shows as the host's text: the guest hears it once.
    host.evaluate("say(0, 21, 'Torjunta!', '#fff')")
    guest.wait_for_function("heard.some(h => h[0] === 'osuma')", timeout=3000)
    guest.wait_for_timeout(300)
    assert played(guest) == ["osuma"]
    # A lunge starting on the host is a tackle on the guest.
    host.evaluate("players[1].lunge = 0.28")
    guest.wait_for_function("heard.some(h => h[0] === 'suhahdus')", timeout=3000)
    # A loose ball turned back beside the goal mouth: the post (nobody may take it on the way).
    guest.evaluate("heard.splice(0)")
    host.evaluate("for (const p of players) { p.x = (p.slot - 1) * 5; p.y = p.t ? 6 : -6; p.vx = p.vy = 0; p.cd = 5; } owner = null; Object.assign(ball, { x: GOAL / 2, y: LEN / 2 - 4, z: 0, vx: 0, vy: 14, vz: 0, from: null, fromT: 0, shot: false })")
    guest.wait_for_function("heard.some(h => h[0] === 'metalli')", timeout=3000)
    assert host.errors == guest.errors == []


@pytest.mark.parametrize("missing,heard", [("verkko", ["onnistui"]), ("onnistui", ["verkko"])])
def test_a_goal_without_one_of_its_two_sounds_plays_the_other(site, browser, missing, heard):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route(f"**/{missing}.mp3", lambda route: route.abort())
        page = start(site, ctx, ready=False)
        here = [n for n in SOUNDS if n != missing]
        page.wait_for_function(f"{here}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('osuma', { vol: 0 })", timeout=5000)
        page.evaluate("() => { window.beeps = 0; const t = tone; tone = (...a) => { beeps++; t(...a); }; heard.splice(0); }")
        page.evaluate("cheer()")
        assert played(page) == heard
        # Without the blip, one soft tone stands in for it (#337: v1's six-note crowd is gone).
        page.wait_for_timeout(500)
        assert page.evaluate("beeps") == (1 if missing == "onnistui" else 0)
        assert page.errors == []
    finally:
        ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/jalkapallo/v3")
