"""Puhelinkoppi v4: a streak of tricks, the spin picked by the throwing motion."""

from conftest import ROOT

FLY = """(seconds) => { for (let t = 0; t < seconds && (state === 'air' || state === 'drop' || state === 'settle'); t += 1 / 60) step(1 / 60); return state; }"""

# Throws the spin the motion picked, with a flick fast enough for upward speed v0.
THROW = """([kind, v0]) => {
  const k = project(pos)[2] / focal();
  throwFromSwipe({ kind, speedUp: v0 * Math.cos(PITCH) / k, speedSide: 0 });
  for (let t = 0; t < 4 && state !== 'result'; t += 1 / 60) step(1 / 60);
  return result;
}"""

NEXT = "resultT = -1e9; onDown({ preventDefault() {} })"  # a tap on the result screen


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v4/")
    page.evaluate("noise = 0")
    return page


def test_tricks_caught_screen_up_make_a_streak_and_a_wrong_one_ends_it(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:puhelinkoppi:taso', '5')")  # v2's level stays untouched
    assert page.evaluate("[streak, record, trick]") == [0, 0, {"kind": "suora", "n": 0}]
    r = page.evaluate(THROW, ["suora", 3])
    assert (r["kind"], r["streak"], r["record"]) == ("win", 1, True)
    page.evaluate(NEXT)
    assert page.evaluate("trick") == {"kind": "kierre", "n": 1}
    r = page.evaluate(THROW, ["kierre", 2.5])
    assert (r["kind"], r["turns"], r["streak"]) == ("win", 1, 2)
    page.evaluate(NEXT)
    assert page.evaluate("trick") == {"kind": "voltti", "n": 1}
    # A kierre when a voltti was asked: caught screen up, but the streak ends.
    r = page.evaluate(THROW, ["kierre", 2.5])
    assert (r["kind"], r["streak"]) == ("trick", 0)
    page.reload()
    assert page.evaluate("[streak, record, catches]") == [0, 2, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:puhelinkoppi:taso')") == "5"


def test_every_trick_can_be_thrown_within_the_hand_s_reach(site, context):
    page = open_game(site, context)
    for kind, n in [("suora", 0), ("kierre", 1), ("kierre", 2), ("voltti", 1), ("voltti", 2)]:
        wins = []
        for i in range(46):
            v0 = 2 + i * 0.1
            page.evaluate(f"newRound(); trick = {{ kind: '{kind}', n: {n} }}")
            if page.evaluate(THROW, [kind, v0])["kind"] == "win":
                wins.append(round(v0, 1))
        assert wins, f"{kind} {n} cannot be thrown"


def test_the_streak_survives_closing_the_game_and_a_record_goes_to_the_streak_list(site, context):
    page = open_game(site, context)
    page.evaluate(THROW, ["suora", 3])
    page.reload()
    assert page.evaluate("[streak, record]") == [1, 1]
    queue = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert queue["puhelinkoppi|putki"]["score"] == 1 and queue["puhelinkoppi|putki"]["version"] == 4


def flick(page, dx, hook):
    """A real throwing motion on the phone: up (and dx sideways), with an optional hook down at the end."""
    px, py = page.evaluate("phoneOnScreen().slice(0, 2)")
    page.mouse.move(px, py)
    page.mouse.down()
    for i in range(1, 6):
        page.mouse.move(px + dx * i, py - 40 * i)
    if hook:
        page.mouse.move(px + dx * 5, py - 200 + 35)
    page.mouse.up()
    return page.evaluate("[state, spinThrown]")


def test_the_throwing_motion_picks_the_spin(site, context):
    page = open_game(site, context)
    assert page.locator("#spins").count() == 0  # no buttons any more
    for dx, hook, kind in [(0, False, "suora"), (40, False, "kierre"), (-40, False, "kierre"), (0, True, "voltti"), (30, True, "voltti")]:
        page.evaluate("newRound()")
        assert flick(page, dx, hook) == ["air", kind], (dx, hook)
        assert page.evaluate("vel[1]") >= 2


def test_the_motion_is_read_from_its_shape(site, context):
    page = open_game(site, context)
    read = lambda pts: page.evaluate("pts => { const t = classifyThrow(pts); return [t.kind, t.dir]; }", pts)
    up = [[100, 500 - 30 * i, 10 * i] for i in range(8)]
    assert read(up) == ["suora", 1]
    assert read([[100 - 25 * i, 500 - 30 * i, 10 * i] for i in range(8)]) == ["kierre", -1]
    # A hook back down within 220 ms of the highest point is a voltti; a slow drift down is not.
    assert read(up + [[100, 325, 120]]) == ["voltti", 1]
    assert read(up + [[100, 325, 400]]) == ["suora", 1]
    # A small wobble at the end is no hook.
    assert read(up + [[100, 300, 90]]) == ["suora", 1]
    # A stroke that starts slanted and ends straight up is still a slanted one: its whole rise counts.
    slant_then_straight = [[100 + 46 * i, 500 - 44 * i, 30 * i] for i in range(6)] + [[330, 280 - 30 * i, 150 + 20 * i] for i in range(1, 4)]
    assert read(slant_then_straight) == ["kierre", 1]
    # Moving the hand 200 px sideways at the same height, then a straight flick: a straight throw.
    assert read([[100 + 40 * i, 500, 30 * i] for i in range(6)] + [[300, 500 - 40 * i, 150 + 15 * i] for i in range(1, 6)]) == ["suora", 1]
    # Dragging the hand around before the flick does not count towards its shape.
    assert read([[100 - 20 * i, 500 + 10 * i, 20 * i] for i in range(6)] + [[0, 550 - 40 * i, 120 + 10 * i] for i in range(1, 7)]) == ["suora", 1]


def test_a_hook_seen_only_where_the_finger_lifts_is_a_voltti(site, context):
    page = open_game(site, context)
    px, py = page.evaluate("phoneOnScreen().slice(0, 2)")
    page.dispatch_event("#c", "pointerdown", {"clientX": px, "clientY": py, "pointerId": 1, "isPrimary": True})
    for i in range(1, 6):
        page.evaluate(f"dispatchEvent(new PointerEvent('pointermove', {{ clientX: {px}, clientY: {py - 40 * i}, pointerId: 1 }}))")
    # The hook down shows only in the lift.
    page.evaluate(f"dispatchEvent(new PointerEvent('pointerup', {{ clientX: {px}, clientY: {py - 200 + 35}, pointerId: 1 }}))")
    assert page.evaluate("[state, spinThrown]") == ["air", "voltti"]


def test_a_catch_screen_down_or_a_drop_ends_the_streak_but_keeps_the_record(site, context):
    page = open_game(site, context)
    for ending, throw in [("down", "launch({ v0: 3, wx: 5 })"), ("drop", "launch({ v0: 3, vx: 0.5 })")]:
        page.evaluate("localStorage.setItem('ai-pelit:puhelinkoppi:putki-nyt', '3');"
                      "localStorage.setItem('ai-pelit:puhelinkoppi:putki', '5')")
        page.reload()
        page.evaluate("noise = 0")
        assert page.evaluate("[streak, record]") == [3, 5]
        page.evaluate(throw)
        page.evaluate(FLY, 4)
        assert page.evaluate("[result.kind, streak, record]") == [ending, 0, 5]
        assert page.evaluate("localStorage.getItem('ai-pelit:puhelinkoppi:putki-nyt')") == "0"
        page.reload()
        assert page.evaluate("[streak, record]") == [0, 5]


def test_it_plays_on_a_390_px_phone(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v4/")
    page.evaluate("noise = 0")
    x, y = page.evaluate("phoneOnScreen().slice(0, 2)")
    assert 0 < x < 390 and 0 < y < 844  # the phone and the hand are on screen
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    assert flick(page, 40, False) == ["air", "kierre"]
    ctx.close()
