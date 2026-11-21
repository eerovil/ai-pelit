"""Pesis v1 (#504): Finnish baseball from above, alone or as two teams of phones in a room.

The match engine is games/pesis/v1/engine.js (globals); index.html draws it and runs the room.
Each phone in a room test is its own Chromium context; the relay is `Relay` from test_rooms_lib.
"""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/pesis/v1/"

# Steps the match by hand, 1/60 s at a time, while cond() holds, at most max seconds.
RUN = "() => { window.run = (cond, max = 5) => { for (let t = 0; t < max && cond(); t += 1 / 60) update(1 / 60); }; }"

# The first pitch of the match, in the air.
TO_PITCH = "run(() => state !== 'pitch', 3)"


def open_game(site, context, viewport=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if viewport:
        page.set_viewport_size(viewport)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context, viewport=None):
    page = open_game(site, context, viewport)
    page.click("#go")
    page.wait_for_function("state === 'ready' && players.length === 18")
    return page


def test_a_tap_at_the_best_moment_hits_and_the_batter_runs(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    assert page.evaluate("[state, batter, bt]") == ["pitch", 0, 0]
    assert page.evaluate("batTap(pitch.n, bestT(pitch.ap))") == "hit"
    assert page.evaluate("[state, batter, runners.length, runners[0].i, runners[0].bat]") == ["play", -1, 1, 0, True]
    # The same pitch cannot be hit twice.
    assert page.evaluate("pitch.done && batTap(pitch.n, bestT(pitch.ap))") is None
    assert page.errors == []


def test_three_pitches_with_no_hit_are_a_palo(site, context):
    page = start(site, context)
    for n in range(3):
        page.evaluate(TO_PITCH)
        # Far too early: a miss (huti).
        assert page.evaluate("batTap(pitch.n, 0.05)") == "huti"
        page.evaluate("run(() => state === 'pitch', 3)")
        if n < 2:
            assert page.evaluate("[state, tries]") == ["dead", n + 1]
        page.evaluate("run(() => state === 'dead', 3)")
    assert page.evaluate("[outs, players[0].out, batter]") == [1, True, 1]


def test_a_first_landing_short_of_the_front_line_is_foul_and_spends_a_try(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    page.evaluate("Object.assign(ball, { x: 0, y: 2, z: 0.01, vx: 0, vy: 0, vz: -1, fly: true })")
    page.evaluate("update(1 / 60)")
    assert page.evaluate("[state, tries, batter, runners.length, outs]") == ["dead", 1, 0, 0, 0]
    assert page.evaluate("events.some(e => e.k === 'laiton')")


def test_a_catch_in_the_air_takes_the_batter_off_with_no_palo(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    page.evaluate("const f = players[15]; Object.assign(ball, { x: f.x, y: f.y, z: 1.5, vx: 0, vy: 0, vz: 0, fly: true })")
    page.evaluate("update(1 / 60)")
    assert page.evaluate("[state, outs, players[0].out, runners.length]") == ["dead", 0, True, 0]
    assert page.evaluate("events.some(e => e.k === 'koppi')")


def test_the_ball_on_the_base_before_the_runner_is_a_palo(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    page.evaluate("const v = players[10]; v.x = BASES[1].x; v.y = BASES[1].y; v.think = 5; ball.held = 10; ball.fly = false; runners[0].d = 2")
    page.evaluate("update(1 / 60)")
    assert page.evaluate("[outs, players[0].out, runners.length]") == [1, True, 0]
    assert page.evaluate("events.some(e => e.k === 'palo')")


def test_the_lukkari_on_the_plate_stops_the_play(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    # One runner past halfway to the 2nd base, one just off the 2nd, the batter short of the 1st.
    page.evaluate("""runners.push({ i: 1, at: 1, run: true, d: segLen(1) * 0.7, bat: false, wait: 0 },
                                  { i: 2, at: 2, run: true, d: 1, bat: false, wait: 0 });
                     runners[0].d = 1; const l = lukkari(); l.x = 0.4; l.y = 0.4; ball.held = idx(l); ball.fly = false""")
    page.evaluate("checkBases()")
    assert page.evaluate("state") == "dead"
    assert page.evaluate("runners.map(r => [r.i, r.at, r.run])") == [[1, 2, False], [2, 2, False]]
    assert page.evaluate("[outs, players[0].out]") == [1, True]


def test_home_from_the_third_base_is_a_run_and_the_batters_own_round_a_kunnari(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    page.evaluate("ball.held = idx(players[17]); runners.push({ i: 1, at: 3, run: true, d: segLen(3) - 0.05, bat: false, wait: 0 })")
    page.evaluate("Object.assign(runners[0], { at: 3, d: segLen(3) - 0.05 }); players[0].v = players[1].v = 6; players[17].think = 5")
    page.evaluate("update(1 / 60)")
    assert page.evaluate("score") == [2, 0]
    assert page.evaluate("events.filter(e => e.k === 'juoksu').map(e => e.s).sort()") == ["Juoksu!", "Kunnari!"]
    assert page.evaluate("[players[0].home, players[1].home, runners.length]") == [True, True, 0]


def test_three_palos_change_sides_and_the_second_inning_ends_the_match(site, context):
    page = start(site, context)
    page.evaluate("outs = 3; state = 'dead'; stT = 99; update(1 / 60)")
    assert page.evaluate("state") == "change"
    page.evaluate("run(() => state === 'change', 4)")
    assert page.evaluate("[state, inn, bt, outs, batter]") == ["ready", 1, 1, 0, 9]
    page.evaluate("score = [3, 1]; state = 'change'; stT = 99; update(1 / 60); update(1 / 60)")
    page.wait_for_function("!document.getElementById('menu').classList.contains('hidden')")
    assert page.locator("#result").inner_text() == "Voitit 3–1! 🏆"
    st = json.loads(page.evaluate("localStorage.getItem('ai-pelit:pesis:stats')"))
    assert [st["voitot"], st["taso"]] == [1, 2]
    assert page.locator("#foe").inner_text() == "Taso 2: vastassa Pesäketut"
    assert page.errors == []


def test_the_computer_plays_a_whole_match_on_its_own(site, context):
    page = start(site, context)
    # Nobody at the phone: the computer bats and fields for it too.
    page.evaluate("ctrls[0].away = true; run(() => state !== 'done', 600)")
    assert page.evaluate("state") == "done"
    assert page.evaluate("inn") == 1
    assert page.locator("#result").inner_text() != ""
    assert page.errors == []


def test_the_lyo_button_hits_a_falling_ball(site, context):
    page = start(site, context)
    page.wait_for_function("state === 'pitch'", timeout=4000)
    page.evaluate("pitch.t = bestT(pitch.ap) - 0.03")
    # The button fills the control strip at the bottom.
    page.mouse.click(180, 680)
    page.wait_for_function("state === 'play' && runners.length === 1", timeout=1000)
    assert page.errors == []


def test_alternating_feet_runs_faster_than_one_foot(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap))")
    page.evaluate("ball.held = idx(players[17])")  # far away, so the play goes on
    # Through the buttons' own handler, as a tap makes it.
    page.evaluate("players[0].v = 0; for (let i = 0; i < 10; i++) act('foot', i % 2 ? 2 : 1)")
    alt = page.evaluate("players[0].v")
    page.evaluate("players[0].v = 0; for (let i = 0; i < 10; i++) act('foot', 1)")
    same = page.evaluate("players[0].v")
    assert alt > 5 and same < 2


def test_a_runner_on_a_base_waits_for_its_own_press(site, context):
    page = start(site, context)
    page.evaluate(TO_PITCH)
    page.evaluate("batTap(pitch.n, bestT(pitch.ap)); ball.held = idx(players[17]); runners[0].d = segLen(0) - 0.01")
    page.evaluate("players[0].v = 5; update(1 / 60)")
    assert page.evaluate("[runners[0].at, runners[0].run]") == [1, False]
    page.evaluate("run(() => true, 1)")
    assert page.evaluate("[runners[0].at, runners[0].run]") == [1, False]
    page.evaluate("footPress(0, 1)")
    assert page.evaluate("runners[0].run")


def test_a_match_alone_carries_on_after_a_reload(site, context):
    page = start(site, context)
    page.evaluate("score = [2, 0]; outs = 1; tries = 0; batter = 3; queue = [4, 5, 6, 7, 8]; ready(); update(1 / 60)")
    page.reload()
    page.evaluate(RUN)
    assert page.locator("#resume").is_visible()
    assert page.locator("#resume").inner_text() == "Jatka ottelua 2–0 (1/2)"
    page.click("#resume")
    assert page.evaluate("[score, outs, batter, queue.length, state]") == [[2, 0], 1, 3, 5, "ready"]


@pytest.mark.parametrize("size", [(360, 740), (740, 360), (360, 640)])
def test_the_menu_and_the_buttons_fit_the_screen(site, context, size):
    page = open_game(site, context, {"width": size[0], "height": size[1]})
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight + 1")
    box = page.locator("#go").bounding_box()
    assert box["y"] + box["height"] <= size[1]
    page.click("#go")
    page.evaluate(TO_PITCH)
    for md in ["bat", "run", "throw"]:
        for b in page.evaluate(f"layout('{md}').map(b => b.rect ? b.rect : [b.x - b.r, b.y - b.r, b.r * 2, b.r * 2])"):
            assert b[0] >= 0 and b[1] >= 0 and b[0] + b[2] <= size[0] + 0.5 and b[1] + b[3] <= size[1] + 0.5, (md, b)
    assert page.errors == []


# ---------- Rooms ----------

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
            p.wait_for_function("players.length === 18 && net.on")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


# The guest's team bats: the host starts its inning over, the guest's first batter up.
GUEST_BATS = "startInning(1)"


def guest_pitch(host, guest):
    """Waits for a pitch to the guest's batter, heard on the guest; returns its number."""
    host.wait_for_function("state === 'pitch' && P(batter).t === 1", timeout=4000)
    n = host.evaluate("pitch.n")
    guest.wait_for_function(f"lp && lp.n === {n}", timeout=3000)
    return n


def test_the_phones_split_into_two_teams_and_the_computer_fills_the_rest(room):
    host, [a, b] = room("Eero", "Aino", "Iida")
    ids = [p.evaluate("AiPelitRooms.me") for p in (host, a, b)]
    # Alternately into the teams: the host and Iida blue, Aino red.
    assert host.evaluate("ctrls.map(k => [k.id, k.t, k.slots, k.fix])") == [
        [ids[0], 0, [0, 2, 4, 6, 8], 6], [ids[2], 0, [1, 3, 5, 7], 4], [ids[1], 1, [0, 1, 2, 3, 4, 5, 6, 7, 8], 6]]
    assert [p.evaluate("myTeam") for p in (host, a, b)] == [0, 1, 0]
    # The lukkari is always the computer's.
    host.wait_for_function("state === 'pitch' || state === 'ready'")
    assert host.evaluate("!lukkari().ctl")
    assert host.errors == a.errors == b.errors == []


def test_a_guest_bats_with_its_own_tap_and_an_old_pitch_number_is_dropped(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate(GUEST_BATS)
    n = guest_pitch(host, guest)
    assert guest.evaluate("mode()") == "bat"
    # A tap meant for an earlier pitch changes nothing.
    guest.evaluate(f"R.send({{ t: 'b', round: net.round, n: {n - 1}, ph: 0.5 }})")
    host.wait_for_timeout(200)
    assert host.evaluate("[state, pitch.tapped]") == ["pitch", False]
    # The guest taps at the toss's best moment, timed on its own clock.
    guest.evaluate("act('bat', 0, { timeStamp: (lp.t0 + bestT(lp.ap)) * 1000 })")
    host.wait_for_function("state === 'play' && runners.length === 1 && runners[0].i === 9", timeout=2000)
    # Its runner is its own to steer: its feet reach the host.
    guest.wait_for_function("mode() === 'run'", timeout=2000)
    steps = host.evaluate("players[9].steps")
    guest.evaluate("act('foot', 1); act('foot', 2)")
    host.wait_for_function(f"players[9].steps >= {steps} + 2 || state !== 'play'", timeout=2000)
    assert host.errors == guest.errors == []


def test_a_pause_during_a_toss_throws_it_again_with_no_try_spent(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate(GUEST_BATS)
    n = guest_pitch(host, guest)
    tries = host.evaluate("tries")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.wait_for_function("state === 'ready' && pitch === null")
    host.wait_for_timeout(600)
    assert host.evaluate("[state, tries]") == ["ready", tries]
    room.relay.back(guest)
    host.wait_for_function(f"!AiPelitRooms.paused && state === 'pitch' && pitch.n > {n}", timeout=8000)
    assert host.evaluate("tries") == tries
    # The new toss reaches the guest with its new number, and its tap counts.
    m = guest_pitch(host, guest)
    assert m > n
    guest.evaluate("act('bat', 0, { timeStamp: (lp.t0 + bestT(lp.ap)) * 1000 })")
    host.wait_for_function("state === 'play' && runners.length === 1", timeout=2000)
    assert host.errors == guest.errors == []


def test_a_guest_that_reloads_mid_match_gets_the_match_back(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("score = [2, 1]")
    guest.reload()
    guest.wait_for_function("players.length === 18 && myTeam === 1 && score[0] === 2", timeout=8000)
    assert host.errors == guest.errors == []


def test_the_end_reaches_both_phones_once_and_each_saves_its_own_result(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("score = [1, 3]; inn = 1; state = 'change'; stT = 99")
    for p, res, saved in [(host, "Häviö 1–3", {"voitot": 0, "haviot": 1, "tasapelit": 0}),
                          (guest, "Voitto 3–1! 🏆", {"voitot": 1, "haviot": 0, "tasapelit": 0})]:
        p.wait_for_function("state === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
        assert json.loads(p.evaluate("localStorage.getItem('ai-pelit:pesis:stats')"))["kaverit"] == saved
    assert host.errors == guest.errors == []
