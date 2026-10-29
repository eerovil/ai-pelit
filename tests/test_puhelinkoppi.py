"""Puhelinkoppi in a phone-sized Chromium: the phone tumbles as a real one does, and a catch screen-up passes."""

from conftest import ROOT

# Flies the phone synchronously through the game's own step(), so nothing hangs on frame timing.
FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""

# World angular momentum and rotational energy of the phone in flight.
INVARIANTS = """() => {
  const Iw = [w[0] * I[0], w[1] * I[1], w[2] * I[2]];
  return { L: rot(q, Iw), E: Iw[0] * w[0] + Iw[1] * w[1] + Iw[2] * w[2] };
}"""


REST_Y = 0.008 * 0.825  # the phone's centre above the palm: REST * cos(TILT)


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v1/")
    page.evaluate("noise = 0")
    return page


def test_free_flight_keeps_angular_momentum_and_energy(site, context):
    page = open_game(site, context)
    page.evaluate("launch({ v0: 6, wx: 14, wy: 3 }); w[2] = 2")
    before = page.evaluate(INVARIANTS)
    page.evaluate("for (let i = 0; i < 60; i++) step(1 / 60)")
    after = page.evaluate(INVARIANTS)
    assert abs(after["E"] - before["E"]) < 1e-6 * before["E"] + 1e-9
    for a, b in zip(after["L"], before["L"]):
        assert abs(a - b) < 1e-4 * max(abs(x) for x in before["L"]) + 1e-9


def test_an_end_over_end_flip_turns_into_a_twist_but_a_long_axis_spin_stays_steady(site, context):
    """The tennis racket effect: the middle axis is unstable, the long axis is not."""
    page = open_game(site, context)
    flip = page.evaluate("launch({ v0: 6, wx: 15 }); w[1] = 0.01; w[2] = 0.01; let m = 0;"
                         "for (let i = 0; i < 60; i++) { step(1 / 60); m = Math.max(m, Math.abs(w[2])); } m")
    assert flip > 5
    page.evaluate("newRound()")
    roll = page.evaluate("launch({ v0: 6, wy: 15 }); w[0] = 0.01; w[2] = 0.01; let m = 0;"
                         "for (let i = 0; i < 60; i++) { step(1 / 60); m = Math.max(m, Math.abs(w[0]), Math.abs(w[2])); } m")
    assert roll < 0.1


def test_a_catch_screen_up_passes_the_level_and_is_kept_after_a_reload(site, context):
    page = open_game(site, context)
    assert page.evaluate("level") == 1
    # Half a turn lands it screen down: no pass.
    page.evaluate("launch({ v0: 3, wx: 5 })")
    assert page.evaluate(FLY, 3) == "result"
    assert page.evaluate("result.kind") == "down"
    # A straight throw lands screen up.
    page.evaluate("newRound(); launch({ v0: 3 })")
    assert page.evaluate(FLY, 3) == "result"
    assert page.evaluate("result") == {"kind": "win", "turns": 0, "level": 1}
    page.reload()
    assert page.evaluate("[level, best, catches]") == [2, 2, 1]
    # Level 2 wants a full turn: a straight throw is not enough, and a missed hand drops it.
    page.evaluate("noise = 0; launch({ v0: 3 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "turns"
    page.evaluate("newRound(); launch({ v0: 3, vx: 0.5 })")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
    assert page.evaluate("level") == 2


def test_the_hand_carries_the_phone_and_a_flick_up_throws_it(site, context):
    page = open_game(site, context)
    px, py = page.evaluate("phoneOnScreen().slice(0, 2)")
    # A slow drag only moves the hand, with the phone in it.
    page.mouse.move(px, py)
    page.mouse.down()
    for i in range(1, 6):
        page.mouse.move(px + 10 * i, py + 10 * i)
        page.wait_for_timeout(120)
    page.mouse.up()
    assert page.evaluate("state") == "ready"
    hand = page.evaluate("[handX, handY]")
    assert hand[0] > 0.02 and hand[1] < -0.02
    assert page.evaluate("Math.abs(pos[0] - handX) + Math.abs(dot(sub(pos, hand()), N) - REST)") < 1e-9
    # A quick flick up throws it from where the hand is.
    px, py = page.evaluate("phoneOnScreen().slice(0, 2)")
    page.mouse.move(px, py)
    page.mouse.down()
    for i in range(1, 6):
        page.mouse.move(px, py - 40 * i)
    page.mouse.up()
    assert page.evaluate("state") == "air"
    assert page.evaluate("vel[1]") >= 2
    page.evaluate("vel[1] = 6")  # keep it in the air while the hand moves
    # During the flight a drag moves the hand sideways and up.
    page.mouse.move(180, 600)
    page.mouse.down()
    page.mouse.move(260, 520)
    page.mouse.up()
    assert page.evaluate("handX") > hand[0] + 0.05
    assert page.evaluate("handY") > hand[1] + 0.05


def test_a_raised_hand_catches_the_phone_higher_up(site, context):
    page = open_game(site, context)
    page.evaluate("launch({ v0: 3 }); handY = 0.3")
    assert page.evaluate(FLY, 3) == "result"
    assert page.evaluate("result.kind") == "win"
    assert abs(page.evaluate("pos[1]") - 0.3 - REST_Y) < 0.01
    # A hand raised past a phone that is already below it does not catch it.
    page.evaluate("newRound(); launch({ v0: 3 })")
    page.evaluate("for (let i = 0; i < 120 && !(vel[1] < 0 && pos[1] < 0.1); i++) step(1 / 60); handY = 0.4")
    page.evaluate(FLY, 3)
    assert page.evaluate("result.kind") == "drop"
