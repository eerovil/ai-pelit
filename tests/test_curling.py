"""Curling: slide stones into the house from above, against the computer or 2-4 phones in a room.

The world steps by hand (`run()`), so a whole match plays in a moment; each phone in a room is its
own Chromium context, and the room relay is `Relay` from test_rooms_lib.
"""

import json

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/curling/v1/"

# Steps the game by hand, 1/120 s at a time, while cond() holds, at most max seconds of game time.
RUN = "() => { window.run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += DT) update(DT); }; }"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context, hammer=1):
    page = open_game(site, context)
    page.click("#go")
    # The phone throws first: the computer has the last stone.
    page.evaluate(f"hammer = {hammer}; startEnd()")
    return page


# Throws one stone on an empty sheet with the game's own physics and says where it stopped.
SLIDE = """([w, ax, spin, sweep]) => {
  const l = [];
  launch(l, 0, { x: ax, w, spin });
  for (let i = 0; i < 40 / DT && moving(l); i++) physics(l, DT, sweep);
  settle(l);
  return { x: l[0].x, y: l[0].y, out: l[0].out };
}"""


def test_the_menu_starts_a_match_with_the_phone_aiming(site, context):
    page = start(site, context)
    assert page.evaluate("[phase, end, throwN, turnTeam(), thrower(), score.join('-')]") == ["aim", 1, 0, 0, "me", "0-0"]
    assert page.locator("#menu").is_hidden()
    assert page.errors == []


def test_a_draw_weight_stops_in_the_house_and_the_turn_bends_it(site, context):
    page = open_game(site, context)
    straight = page.evaluate(SLIDE, [0.56, 0, 0, 0])
    assert abs(straight["x"]) < 0.01 and page.evaluate(f"weightName(0.56)") == "Pesään"
    assert abs(straight["y"] - page.evaluate("TEE")) < 1.0
    right = page.evaluate(SLIDE, [0.56, 0, 1, 0])
    left = page.evaluate(SLIDE, [0.56, 0, -1, 0])
    # About a metre of bend either way, the way the turn button says.
    assert 0.7 < right["x"] < 1.4 and -1.4 < left["x"] < -0.7
    # Aimed the other way by as much, it comes back to the middle.
    back = page.evaluate(SLIDE, [0.56, -right["x"] * 0.9, 1, 0])
    assert abs(back["x"]) < 0.35


def test_sweeping_takes_the_stone_further_and_straighter(site, context):
    page = open_game(site, context)
    plain = page.evaluate(SLIDE, [0.5, 0, 1, 0])
    swept = page.evaluate(SLIDE, [0.5, 0, 1, 1])
    assert swept["y"] > plain["y"] + 2
    assert swept["x"] / swept["y"] < plain["x"] / plain["y"]


def test_too_light_is_taken_off_and_too_hard_goes_out_the_back(site, context):
    page = open_game(site, context)
    assert page.evaluate(SLIDE, [0.1, 0, 1, 0])["out"] is True
    assert page.evaluate("weightName(0.1)") == "Liian kevyt"
    assert page.evaluate(SLIDE, [0.74, 0, 1, 0])["out"] is True
    assert page.evaluate(SLIDE, [0.35, 0, 1, 0])["out"] is False  # a guard


def test_a_takeout_knocks_a_stone_out_of_the_house(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      const l = [stone(1, 0, TEE)];
      launch(l, 0, { x: 0, w: 1, spin: 0 });
      let hits = 0;
      for (let i = 0; i < 40 / DT && moving(l); i++) hits += physics(l, DT, 0);
      settle(l);
      return { hits, red: l[0].out, ours: !l[1].out };
    }""")
    assert res == {"hits": 1, "red": True, "ours": True}


def test_the_nearest_stones_score_until_the_other_teams_nearest(site, context):
    page = open_game(site, context)
    pts = page.evaluate("""() => {
      const p = endPoints([stone(0, 0, TEE + 0.1), stone(0, 0.5, TEE), stone(1, 0, TEE - 0.9), stone(0, 1.5, TEE), stone(1, 0, 10)]);
      return [p.t, p.n];
    }""")
    assert pts == [0, 2]
    # A stone only touching the house still counts; one outside it does not.
    assert page.evaluate("[endPoints([stone(1, HOUSE + RS - 0.01, TEE)]).n, endPoints([stone(1, HOUSE + RS + 0.02, TEE)]).t]") == [1, -1]


def test_pulling_the_stone_back_throws_it_and_a_short_pull_does_not(site, context):
    page = start(site, context)
    px, py = page.evaluate("[pad.x, pad.y]")
    # A short pull lets go of nothing.
    page.mouse.move(px, py); page.mouse.down(); page.mouse.move(px, py + 8, steps=3); page.mouse.up()
    assert page.evaluate("phase") == "aim"
    # Down and to the left: aims right of the middle, about house weight.
    page.mouse.move(px, py); page.mouse.down(); page.mouse.move(px - 30, py + 0.58 * page.evaluate("pad.pull"), steps=8)
    assert page.evaluate("weightName(aim.w)") == "Pesään"
    assert page.evaluate("aim.x") > 0.3
    page.mouse.up()
    assert page.evaluate("phase") == "slide"
    page.evaluate("run(() => phase === 'slide')")
    assert page.evaluate("[phase, throwN, turnTeam(), thrower()]") == ["aim", 1, 1, "cpu"]
    assert page.evaluate("stones.filter(s => !s.out).length") == 1
    assert page.errors == []


def test_the_turn_buttons_choose_the_bend_and_it_stays_for_the_next_throw(site, context):
    page = start(site, context)
    b = page.evaluate("spinBtns.find(b => b.s === -1)")
    page.mouse.click(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
    assert page.evaluate("aim.spin") == -1
    page.evaluate("doThrow({ x: 0, w: 0.5, spin: aim.spin }); run(() => phase === 'slide'); run(() => thrower() === 'cpu')")
    assert page.evaluate("[thrower(), aim.spin]") == ["me", -1]


def test_rubbing_the_screen_sweeps_only_while_our_stone_slides(site, context):
    page = start(site, context)
    page.evaluate("doThrow({ x: 0, w: 0.5, spin: 1 })")
    page.evaluate("run(() => true, 0.2)")
    page.mouse.move(100, 300); page.mouse.down()
    for i in range(12):
        page.mouse.move(100 + (60 if i % 2 == 0 else 0), 300, steps=2)
        page.evaluate("update(1 / 30)")
    assert page.evaluate("sweepOf(0)") > 0.3
    page.mouse.up()
    page.evaluate("run(() => true, 1)")
    assert page.evaluate("sweepOf(0)") < 0.05


def test_the_computer_draws_into_an_empty_house(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      const plan = cpuPlan([], 1, 7);
      const l = simulate([], 1, plan);
      return endPoints(l);
    }""")
    assert res["t"] == 1 and res["n"] == 1


def test_the_computer_takes_out_a_stone_on_the_button(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      const l0 = [stone(0, 0, TEE)];
      const plan = cpuPlan(l0, 1, 1);
      return endPoints(simulate(l0, 1, plan)).t;
    }""")
    assert res == 1


def test_a_whole_match_ends_saves_and_raises_the_level_on_a_win(site, context):
    page = start(site, context)
    # The phone draws to the button every time, the computer throws far too light.
    page.evaluate("""() => {
      cpuPlan = () => ({ x: 0, w: 0.05, spin: 1 });
      skillOf = () => ({ ex: 0, ew: 0 });
      for (let k = 0; k < 2000 && phase !== 'done'; k++) {
        if (phase === 'aim' && thrower() === 'me') doThrow({ x: 0, w: 0.55 + (throwN % 4) * 0.01, spin: 0 });
        else if (phase === 'endshow') nextEnd();
        else run(() => phase === 'slide' || (phase === 'aim' && thrower() === 'cpu'), 30);
      }
    }""")
    assert page.evaluate("[phase, ends.length]") == ["done", 3]
    assert page.evaluate("score[0] > 0 && score[1] === 0")
    assert page.evaluate("localStorage.getItem('ai-pelit:curling:taso')") == "2"
    assert page.evaluate("localStorage.getItem('ai-pelit:curling:voitot')") == "1"
    assert page.evaluate("localStorage.getItem('ai-pelit:curling:ottelu')") == "null"
    assert page.locator("#result").inner_text().startswith("Voitit")
    assert page.locator("#foe").inner_text() == "Taso 2: vastassa Kurkiseura"
    assert page.errors == []


def test_a_level_match_plays_an_extra_end(site, context):
    page = start(site, context)
    page.evaluate("end = 3; score = [2, 2]; stones = []; throwN = 8; scoreEnd()")
    assert page.evaluate("[endMsg.t, over()]") == [-1, False]
    page.evaluate("nextEnd()")
    assert page.evaluate("[phase, end]") == ["aim", 4]


def test_a_reload_mid_match_can_carry_the_match_on(site, context):
    page = start(site, context)
    page.evaluate("doThrow({ x: 0, w: 0.56, spin: 1 }); run(() => phase === 'slide')")
    page.evaluate("score = [1, 0]; end = 2; keepMatch()")
    page.reload()
    page.evaluate(RUN)
    assert page.locator("#resume").is_visible()
    assert "1–0" in page.locator("#resume").inner_text()
    page.click("#resume")
    assert page.evaluate("[phase, end, score.join('-'), throwN, stones.length]") == ["aim", 2, "1-0", 1, 1]


def test_the_end_shows_its_points_and_a_tap_goes_on(site, context):
    page = start(site, context)
    page.evaluate("stones = [stone(0, 0, TEE), stone(0, 0.4, TEE), stone(1, 0, TEE + 1)]; throwN = 8; scoreEnd()")
    assert page.evaluate("[phase, endMsg.t, endMsg.n, score.join('-'), hammer]") == ["endshow", 0, 2, "2-0", 1]
    page.evaluate("phaseT = 2")
    page.mouse.click(180, 400)
    assert page.evaluate("[phase, end, throwN, stones.length]") == ["aim", 2, 0, 0]


# ---------- Playing with friends ----------

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
        page.evaluate(RUN)
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
            p.wait_for_function("phase === 'aim'")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def test_two_phones_take_turns_and_the_thrower_sweeps(room):
    host, [guest] = room("Eero", "Aino")
    assert host.evaluate("net.setup.teams.map(t => t.map(p => p.name))") == [["Eero"], ["Aino"]]
    assert host.evaluate("myTeam") == 0 and guest.evaluate("myTeam") == 1
    # Make the guest's team throw first.
    host.evaluate("hammer = 0; startEnd()")
    guest.wait_for_function("myTurn()")
    assert host.evaluate("myTurn()") is False
    # The guest drags: the host sees its aim; it lets go: the stone slides on the host.
    px, py = guest.evaluate("[pad.x, pad.y]")
    guest.mouse.move(px, py); guest.mouse.down(); guest.mouse.move(px - 20, py + 0.5 * guest.evaluate("pad.pull"), steps=6)
    host.wait_for_function("aimShown && aim.x > 0.1", timeout=3000)
    guest.mouse.up()
    host.wait_for_function("phase === 'slide'", timeout=3000)
    guest.wait_for_function("phase === 'slide' && stones.length === 1", timeout=3000)
    # The guest rubs its screen: the host's stone is swept.
    guest.mouse.move(100, 300); guest.mouse.down()
    swept = False
    for i in range(30):
        guest.mouse.move(100 + (70 if i % 2 == 0 else 0), 300, steps=2)
        guest.wait_for_timeout(30)
        if host.evaluate("sweepOf(1)") > 0.2:
            swept = True
            break
    guest.mouse.up()
    assert swept
    # Then it is the host's turn.
    host.wait_for_function("phase === 'aim' && myTurn()", timeout=20000)
    guest.wait_for_function("phase === 'aim' && !myTurn() && throwerName() === 'Eero'", timeout=3000)
    # The match ends on the host; both phones hear it once and go back to the room.
    host.evaluate("score = [1, 3]; end = 3; hostEnd()")
    for p, res, saved in [(host, "Häviö 1–3", '{"voitot":0,"haviot":1,"tasapelit":0}'), (guest, "Voitto 3–1! 🏆", '{"voitot":1,"haviot":0,"tasapelit":0}')]:
        p.wait_for_function("phase === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
        assert p.evaluate("localStorage.getItem('ai-pelit:curling:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_three_phones_two_share_a_team_and_take_its_turns(room):
    host, guests = room("Eero", "Aino", "Iida")
    assert host.evaluate("net.setup.teams.map(t => t.map(p => p.name))") == [["Eero", "Iida"], ["Aino"]]
    host.evaluate("hammer = 1; startEnd()")
    ids = host.evaluate("[0, 2, 4, 6].map(n => { throwN = n; return thrower(); })")
    eero, iida = host.evaluate("AiPelitRooms.me"), guests[1].evaluate("AiPelitRooms.me")
    assert ids == [eero, iida, eero, iida]


def test_a_throw_out_of_turn_or_sent_twice_is_ignored(room):
    host, [guest] = room("Eero", "Aino")
    # The host's turn: a throw from the guest does nothing.
    host.evaluate("hammer = 1; startEnd()")
    host.wait_for_function("myTurn()")
    guest.wait_for_function("phase === 'aim' && !myTurn()")
    guest.evaluate("AiPelitRooms.send({ t: 'throw', round: net.round, n: throwN, x: 0, w: 0.5, spin: 1 })")
    host.wait_for_timeout(400)
    assert host.evaluate("[phase, stones.length]") == ["aim", 0]
    # The guest's turn: its throw sent twice (a double tap, a resend) throws one stone.
    host.evaluate("doThrow({ x: 0, w: 0.5, spin: 1 }); run(() => phase === 'slide')")
    guest.wait_for_function("myTurn()", timeout=5000)
    guest.evaluate("const m = { t: 'throw', round: net.round, n: throwN, x: 0.2, w: 0.5, spin: -1 }; AiPelitRooms.send(m); AiPelitRooms.send(m)")
    host.wait_for_function("phase === 'slide'", timeout=3000)
    host.evaluate("run(() => phase === 'slide')")
    assert host.evaluate("[throwN, stones.filter(s => s.t === 1).length]") == [2, 1]
    assert host.errors == guest.errors == []


def test_a_phone_let_go_is_thrown_for_by_the_computer(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    host.evaluate("hammer = 0; startEnd()")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("thrower() === 'cpu'")
    host.wait_for_function("phase === 'slide'", timeout=8000)
    assert host.errors == third.errors == []


def test_a_guest_that_reloads_mid_match_gets_it_back(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("doThrow({ x: 0, w: 0.5, spin: 1 }); run(() => phase === 'slide')")
    guest.reload()
    guest.evaluate(RUN)
    guest.wait_for_function("phase === 'aim' && stones.filter(s => !s.out).length === 1", timeout=8000)
    assert guest.errors == []


# ---------- Screens ----------

@pytest.mark.parametrize("size", [(740, 360), (640, 360), (360, 640), (390, 844)])
def test_the_menu_and_the_pad_fit_the_screen(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    for sel in ["#go", "#multi", "h1"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] >= 0 and b["x"] + b["width"] <= size[0], sel
    page.click("#go")
    page.evaluate("hammer = 1; startEnd()")
    # The pad and the turn buttons are on the screen, and apart from each other.
    inside = page.evaluate("""() => spinBtns.every(b => b.x >= 0 && b.y >= 0 && b.x + b.w <= W && b.y + b.h <= H)
      && pad.x > 0 && pad.y < H && spinBtns.every(b => Math.hypot(pad.x - (b.x + b.w / 2), pad.y - (b.y + b.h / 2)) > 60)""")
    assert inside is True
    # The whole house is in view while aiming.
    page.evaluate("camY = END + 0.4 - viewLen() / 2")
    top = page.evaluate("[P(0, TEE + HOUSE), P(0, TEE - HOUSE), P(HOUSE, TEE), P(-HOUSE, TEE)]")
    assert all(0 <= px <= size[0] and 0 <= py <= size[1] for px, py in top)
    ctx.close()


def test_turning_the_phone_mid_round_keeps_the_round(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.evaluate("hammer = 1; startEnd(); doThrow({ x: 0, w: 0.56, spin: 1 }); run(() => phase === 'slide')")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide === true")
    assert page.evaluate("[phase, throwN, stones.length]") == ["aim", 1, 1]
    # Sideways the sheet runs to the right: the house is right of the pad.
    assert page.evaluate("P(0, TEE)[0] > pad.x + 100")
    ctx.close()
