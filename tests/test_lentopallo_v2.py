"""Lentopallo v2: 1 vs 1 and 2 vs 2 against the computer, and 2-4 phones in one room.

Each phone is its own Chromium context; the room relay is `Relay` from test_rooms_lib.
"""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/lentopallo/v2/"


def alone(site, context, mode="1v1"):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#m1" if mode == "1v1" else "#m2")
    page.click("#go")
    return page


PLAYING = """() => {
  tossed = true; ball.held = false; ball.served = true; state = 'play';
  for (const p of players) if (p !== mine) { p.x = p.side * 0.5; p.kind = 'shown'; }
}"""


def test_v1_saves_carry_over(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + "games/lentopallo/v1/")
    page.evaluate("localStorage.setItem('ai-pelit:lentopallo:taso', '3'); localStorage.setItem('ai-pelit:lentopallo:voitot', '2')")
    page.goto(site.url + URL)
    assert "Taso 3" in page.inner_text("#foe")
    assert "Voitot 2" in page.inner_text("#stats")


def test_one_against_one_keeps_v1s_rules(site, context):
    page = alone(site, context)
    assert page.evaluate("players.length") == 2
    assert page.evaluate("[matchWinner(11, 9), matchWinner(11, 10), matchWinner(12, 10)]") == [0, -1, 0]
    page.evaluate(PLAYING)
    page.evaluate("last = mine; touchSide = 1; Object.assign(ball, { x: 4.8, y: 0.6, vx: 0.5, vy: -2 })")
    page.wait_for_function("state === 'point'", timeout=2000)
    assert page.evaluate("[score.join('-'), msg.s, team(server)]") == ["0-1", "Ulos!", 1]


def test_the_serve_goes_over_the_net(site, context):
    page = alone(site, context, "2v2")
    assert page.evaluate("state === 'serve' && server === mine && ball.held")
    page.evaluate("press(mine)")
    page.wait_for_function("crossings >= 1", timeout=4000)


def test_two_against_two_with_a_computer_teammate(site, context):
    page = alone(site, context, "2v2")
    assert page.evaluate("players.map(p => [p.side, p.kind])") == [[-1, "me"], [1, "cpu"], [-1, "cpu"], [1, "cpu"]]
    assert page.evaluate("localStorage.getItem('ai-pelit:lentopallo:muoto')") == '"2v2"'
    # A team that wins the serve back serves with its other player.
    page.evaluate("state = 'play'; pointTo(1, 'x')")
    assert page.evaluate("players.indexOf(server)") == 1
    page.evaluate("state = 'play'; pointTo(0, 'x')")
    assert page.evaluate("players.indexOf(server)") == 2
    page.evaluate("state = 'play'; pointTo(0, 'x')")
    assert page.evaluate("players.indexOf(server)") == 2
    page.evaluate("state = 'play'; pointTo(1, 'x')")
    assert page.evaluate("players.indexOf(server)") == 3
    # Three touches on one side, then the fourth is a fault, whoever makes it.
    page.evaluate(PLAYING)
    page.evaluate("touchSide = -1; touches = 3; last = players[2]; hit(mine)")
    assert page.evaluate("msg.s") == "Neljä kosketusta!"


def test_the_computer_teammate_sets_the_ball_for_you(site, context):
    page = alone(site, context, "2v2")
    page.evaluate(PLAYING)
    # The second touch comes down near where the player stands. cpuThink() plans a set for a
    # teammate's second touch, but only on a frame of its own, and before PLAYING it had left
    # 'over' from the serve on some runs: so the plan is set here, as cpuThink() would.
    land = page.evaluate("""() => {
      const t = players[2]; t.kind = 'cpu'; t.intent = 'set'; mine.x = -3; t.x = -1.2;
      touchSide = -1; touches = 1; last = mine;
      Object.assign(ball, { x: -1.2, y: 2.4, vx: 0, vy: -0.5 });
      hit(t);
      return predict(0.2).x;
    }""")
    assert -3.7 < land < -2.0


@pytest.fixture
def room(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name, query=""):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL + query)
        return page

    def play(*names, mode="1v1"):
        host = phone(names[0])
        host.click("#m1" if mode == "1v1" else "#m2")
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
            p.wait_for_function("mine && players.length && (state === 'serve' || state === 'play')")
        return host, guests

    play.relay = relay
    play.phone = phone
    yield play
    for ctx in contexts:
        ctx.close()


def test_two_phones_play_one_against_one(room):
    host, [guest] = room("Eero", "Aino")
    assert host.evaluate("players.map(p => [p.name, p.side, p.kind])") == [["Sinä", -1, "me"], ["Aino", 1, "remote"]]
    assert guest.evaluate("players.map(p => [p.name, p.side, p.kind])") == [["Eero", -1, "shown"], ["Sinä", 1, "me"]]
    # Each phone sees its own side on the left: the guest's court is drawn mirrored.
    assert host.evaluate("view") == 1 and guest.evaluate("view") == -1
    assert guest.evaluate("sx(mine.x) < sx(0)")
    # The guest's ▶ runs toward the net, which for its side is toward smaller x; the host sees it.
    start = guest.evaluate("mine.x")
    guest.evaluate("state = 'play'; input.right = true")
    guest.wait_for_timeout(300)
    guest.evaluate("input.right = false")
    assert guest.evaluate("mine.x") < start
    host.wait_for_function(f"players[1].x < {start} - 0.3")
    # The host's serve reaches the guest's phone.
    host.evaluate("press(mine)")
    guest.wait_for_function("crossings >= 0 && ball.x > 0 && !ball.held", timeout=4000)
    # The match ends on the host; both phones hear it once and go back to the room.
    host.evaluate("score = [11, 4]; state = 'point'; pauseT = 0")
    for p, res, saved in [(host, "Voitto 11–4! 🏆", '{"voitot":1,"haviot":0}'), (guest, "Häviö 4–11", '{"voitot":0,"haviot":1}')]:
        p.wait_for_function("state === 'done'")
        p.wait_for_function("document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
        assert p.evaluate("localStorage.getItem('ai-pelit:lentopallo:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_three_phones_play_two_against_two_with_the_computer(room):
    host, [a, b] = room("Eero", "Aino", "Iida")
    teams = host.evaluate("players.map(p => [p.side, p.slot, p.kind])")
    assert teams == [[-1, 0, "me"], [1, 0, "remote"], [-1, 1, "remote"], [1, 1, "cpu"]]
    assert b.evaluate("[mine.side, view]") == [-1, 1]
    assert a.evaluate("[mine.side, view]") == [1, -1]
    # Iida (the host's teammate) serves when the host's team wins the serve back.
    host.evaluate("state = 'play'; pointTo(1, 'x'); state = 'play'; pointTo(0, 'x')")
    b.wait_for_function("server === mine")
    b.wait_for_function("state === 'serve'")
    b.evaluate("press(mine)")
    host.wait_for_function("tossed && server === players[2]")
    assert host.errors == a.errors == b.errors == []


def test_two_phones_play_two_against_two_when_the_host_picks_it(room):
    host, [guest] = room("Eero", "Aino", mode="2v2")
    assert host.evaluate("players.map(p => [p.side, p.slot, p.kind])") == [[-1, 0, "me"], [1, 0, "remote"], [-1, 1, "cpu"], [1, 1, "cpu"]]
    assert guest.evaluate("players.length") == 4
    assert host.errors == guest.errors == []


def test_four_phones_play_two_against_two(room):
    host, guests = room("Eero", "Aino", "Iida", "Onni")
    assert host.evaluate("players.map(p => [p.side, p.slot, p.kind])") == [[-1, 0, "me"], [1, 0, "remote"], [-1, 1, "remote"], [1, 1, "remote"]]
    assert [g.evaluate("[mine.side, mine.slot, view]") for g in guests] == [[1, 0, -1], [-1, 1, 1], [1, 1, -1]]
    # Each guest's own player moves on the host's phone.
    for i, g in enumerate(guests, start=1):
        before = host.evaluate(f"players[{i}].x")
        g.evaluate("mine.x = mine.side * 3.3")
        host.wait_for_function(f"Math.abs(players[{i}].x - players[{i}].side * 3.3) < 0.1 && players[{i}].x !== {before}")
    host.evaluate("score = [9, 11]; state = 'point'; pauseT = 0")
    for p, res in [(host, "Häviö 9–11"), (guests[0], "Voitto 11–9! 🏆"), (guests[1], "Häviö 9–11"), (guests[2], "Voitto 11–9! 🏆")]:
        p.wait_for_function("state === 'done' && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
    assert host.errors == [] and all(g.errors == [] for g in guests)


def test_a_phone_away_at_the_end_gets_its_result_once_after_a_reload(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("players[1].kind === 'cpu'")
    host.evaluate("score = [4, 11]; state = 'point'; pauseT = 0")
    third.wait_for_function("state === 'done'")
    # Aino's page reloads as her phone comes back: a fresh page that knows no match.
    room.relay.back(guest)
    guest.reload()
    guest.wait_for_function("document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0", timeout=8000)
    assert guest.locator("#aipr-result").inner_text() == "Voitto 11–4! 🏆"
    assert guest.evaluate("localStorage.getItem('ai-pelit:lentopallo:kaverit')") == '{"voitot":1,"haviot":0}'
    # Back in the room after another reload, the match is not counted again.
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.connected", timeout=8000)
    guest.wait_for_timeout(500)
    assert guest.evaluate("localStorage.getItem('ai-pelit:lentopallo:kaverit')") == '{"voitot":1,"haviot":0}'
    assert host.errors == guest.errors == third.errors == []


def test_teammates_on_the_same_spot_touch_the_ball_once(site, context):
    page = alone(site, context, "2v2")
    page.evaluate(PLAYING)
    page.evaluate("""() => {
      const t = players[2]; t.kind = 'shown'; mine.x = -2; t.x = -2;
      touchSide = -1; touches = 0; last = players[1];
      Object.assign(ball, { x: -2, y: 2.3, vx: 0, vy: -1, cd: 0 });
      for (let i = 0; i < 12; i++) stepBall(1 / 240, true);
    }""")
    assert page.evaluate("[touches, players[0].hits + players[2].hits]") == [1, 1]


def test_only_the_host_says_which_game_the_room_plays(room):
    host = room.phone("Eero")
    host.click("#m2")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    # Aino last played 1 vs 1 alone; Iida joins by the QR link.
    aino = room.phone("Aino")
    aino.click("#m1")
    aino.click("#multi")
    aino.fill("#aipr-codeIn", code)
    aino.click("#aipr-joinBtn")
    iida = room.phone("Iida", f"?huone={code}")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 3")
    for g in (aino, iida):
        g.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 3")
        info = g.locator("#aipr-info").inner_text()
        assert "Huoneen tekijä valitsee, pelataanko 1 vs 1 vai 2 vs 2." in info
        assert "Kaksi pelaa" not in info and "Pelataan" not in info
    assert "Pelataan 2 vs 2." in host.locator("#aipr-info").inner_text()
    assert host.errors == aino.errors == iida.errors == []


def test_a_defender_at_the_net_can_play_a_spike_at_once(site, context):
    page = alone(site, context)
    page.evaluate(PLAYING)
    page.evaluate("""() => {
      const foe = players[1]; foe.kind = 'shown'; foe.x = 0.6; foe.cd = 0;
      touchSide = -1; touches = 2; last = mine; mine.x = -0.3; mine.y = 1.0;
      Object.assign(ball, { x: -0.25, y: 3.2, vx: 0, vy: 0, cd: 0 });
      mine.intent = 'set'; hit(mine);
      // A fast ball straight at the defender, just over the net, well within 0.2 s of the spike.
      Object.assign(ball, { x: 0.3, y: 2.0, vx: 6, vy: -4 });
      for (let i = 0; i < 8; i++) stepBall(1 / 240, true);
    }""")
    assert page.evaluate("[players[1].hits, last === players[1]]") == [1, True]
