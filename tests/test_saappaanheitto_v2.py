"""Saappaanheitto v1 (#503): the boot is swung round in an upright circle by drawing circles with a
thumb, and flies off along the circle when the thumb lifts; an athletics meet (kisa.js)."""

import math

from conftest import turn
from test_hiljaiset_aanet import cheer_is_quiet, opens_and_plays_with_the_quiet_library, real  # noqa: F401

URL = "games/saappaanheitto/v2"


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, URL)


def test_the_cheer_chime_is_quiet():
    cheer_is_quiet(URL)


def open_game(real, context):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{real.url}{URL}/")
    page.wait_for_function("typeof flight === 'function' && typeof K !== 'undefined'")
    return page, errors


def my_turn(page):
    """Starts a meet alone and runs it on to this phone's first throw, the boot hanging ready."""
    page.click("#go")
    page.wait_for_function("th !== null")
    for _ in range(60):
        if page.evaluate("th && th.mine"):
            break
        page.evaluate("if (th && !th.mine && th.phase !== 'land') th.t = 99")
        page.wait_for_timeout(250)
    page.evaluate("th.t = 99")
    page.wait_for_function("th.phase === 'ready'")


def test_the_flight_rewards_speed_and_the_right_moment(real, context):
    page, errors = open_game(real, context)
    r = page.evaluate("""() => {
      // Over the top (clockwise, dir -1, Eero's choice on #503): the angle falls as the boot goes
      // round, so an early release is at a larger angle and a late one at a smaller.
      const best = (BEST + 90) * DEG;               // high behind the shoulder
      return {
        top: flight(best, VMAX, -1),
        slow: flight(best, 12, -1),
        early: flight(best + 100 * DEG, VMAX, -1),  // still rising behind: flies up and back
        late: flight(best - 110 * DEG, VMAX, -1),   // coming down in front: low, into the ground
        under: flight((BEST - 90) * DEG, VMAX, 1),  // the underarm swing, mirrored
      };
    }""")
    assert 55 < r["top"]["mark"] < 62, r["top"]
    assert abs(r["top"]["ang"] - 43) < 0.5
    assert 0 < r["slow"]["mark"] < 20, r["slow"]
    assert r["early"]["mark"] == -1 and r["early"]["why"]
    assert r["late"]["mark"] < 0.3 * r["top"]["mark"], r["late"]
    # The underarm swing reaches about as far, from the same best angle.
    assert abs(r["under"]["mark"] - r["top"]["mark"]) < 2
    # The arm halves an error: 30 degrees off the tangent costs a little, not the throw.
    off = page.evaluate("flight((BEST + 90 + 30) * DEG, VMAX, -1)")
    assert 0.8 * r["top"]["mark"] < off["mark"] < r["top"]["mark"]
    assert errors == []


def test_the_computer_never_throws_past_58_m(real, context):
    page, _ = open_game(real, context)
    marks = page.evaluate("Array.from({ length: 20000 }, () => cpuMark({ skill: 54 }))")
    good = [m for m in marks if m >= 0]
    assert max(good) <= 58
    assert max(good) > 57
    assert 0.09 < marks.count(-1) / len(marks) < 0.15
    low = [m for m in page.evaluate("Array.from({ length: 5000 }, () => cpuMark({ skill: 32 }))") if m >= 0]
    assert 31 < sum(low) / len(low) < 33


def circles(page, laps, lap_ms, stop_deg=None):
    """Draws circles clockwise (over the top) on the spin pad with the mouse, from the bottom, and lifts at stop_deg."""
    cx, cy, r = page.evaluate("[ring.cx, ring.cy, ring.r]")
    per = 24
    a = -math.pi / 2
    page.mouse.move(cx + r * math.cos(a), cy - r * math.sin(a))
    page.mouse.down()
    for _ in range(int(laps * per)):
        a -= 2 * math.pi / per
        page.mouse.move(cx + r * math.cos(a), cy - r * math.sin(a))
        page.wait_for_timeout(lap_ms / per)
    if stop_deg is not None:
        target = stop_deg * math.pi / 180
        while abs(((target - a + math.pi) % (2 * math.pi)) - math.pi) > 0.15:
            a -= 2 * math.pi / per
            page.mouse.move(cx + r * math.cos(a), cy - r * math.sin(a))
            page.wait_for_timeout(lap_ms / per)
    page.mouse.up()


def test_a_thumb_drawing_circles_throws_the_boot(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    circles(page, 4, 300, stop_deg=133)
    page.wait_for_function("th.phase === 'land'", timeout=10000)
    th = page.evaluate("({ mark: th.mark, ang: th.ang, v: th.v, dir: th.dir })")
    assert th["dir"] == -1
    assert th["v"] > 5
    assert abs(th["ang"] - 43) < 8, th
    assert th["mark"] > 5, th
    # Its mark goes to the meet once the boot has lain a moment.
    page.wait_for_function("K.mine().marks.length === 1", timeout=8000)
    assert page.evaluate("K.mine().marks[0]") == th["mark"]
    assert errors == []


def test_a_lift_before_half_a_lap_is_no_throw(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    circles(page, 0.25, 300)
    page.wait_for_timeout(200)
    assert page.evaluate("th.phase") == "ready"
    assert page.evaluate("th.boot") is None
    assert errors == []


def test_swinging_on_and_on_tires_the_arm(real, context):
    # Laps past TIRE take speed away, and at SLIP the boot slips from the hand: a foul.
    page, errors = open_game(real, context)
    assert page.evaluate("build(TIRE + 3) < build(TIRE)")
    assert page.evaluate("build(0) === 0.5 && build(BUILD) === 1")
    my_turn(page)
    page.evaluate("""() => {
      const fake = { pointerId: 7, clientX: ring.cx, clientY: ring.cy + ring.r, timeStamp: performance.now() };
      spinStart(fake);
      let a = -Math.PI / 2;
      for (let i = 0; i < 24 * (SLIP + 1); i++) {
        a += Math.PI / 12;
        spinMove(ring.cx + Math.cos(a) * ring.r, ring.cy - Math.sin(a) * ring.r, clock);
      }
    }""")
    page.wait_for_function("th.phase === 'land'", timeout=5000)
    assert page.evaluate("th.mark") == -1
    assert "lipsahti" in page.evaluate("th.why")
    assert errors == []


def test_on_its_side_the_pad_is_under_the_right_thumb(real, context):
    page, errors = open_game(real, context)
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    # The menu fits without scrolling.
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    my_turn(page)
    cx, cy, r = page.evaluate("[ring.cx, ring.cy, ring.r]")
    assert cx > 740 * 0.66
    assert cx + 1.45 * r <= 740 and cx - 1.45 * r >= page.evaluate("W - side")
    assert cy - 1.45 * r >= 0 and cy + 1.45 * r <= 360
    circles(page, 3, 300, stop_deg=133)
    page.wait_for_function("th.phase === 'land'", timeout=10000)
    assert page.evaluate("th.mark") > 0
    # Turning back upright keeps the meet going.
    turn(page, {"width": 360, "height": 740})
    page.wait_for_timeout(300)
    assert page.evaluate("!land && K.comp !== null")
    assert errors == []


def test_letting_go_between_frames_counts_at_its_own_moment(real, context):
    # #404: the lift is judged at its own moment, the game run on to it first. (A made-up event has
    # no target, which other scripts on the page trip over, so page errors are not checked here.)
    page, _ = open_game(real, context)
    my_turn(page)
    log = page.evaluate("""() => {
      requestAnimationFrame = () => 0;
      const log = [], realStep = step;
      step = d => { log.push(d); realStep(d); };
      letGo = () => log.push('judged');
      th.phase = 'spin'; th.turn = 2 * TAU; spinPtr = 7;
      const ev = new PointerEvent('pointerup', { pointerId: 7, clientX: ring.cx + ring.r, clientY: ring.cy });
      lastT = ev.timeStamp - 8;
      window.dispatchEvent(ev);
      return log;
    }""")
    assert abs(log[0] - 0.008) < 1e-6
    assert log[1:] == ["judged"]


def test_a_watching_phone_flies_the_same_boot(real, context):
    # In a room the thrower's phone sends `p` while spinning and `rel` on the lift; a phone watching
    # draws the spin and flies the same boot to the same mark. Driven here by making this phone's
    # turn someone else's, as a watching phone has it.
    page, errors = open_game(real, context)
    my_turn(page)
    r = page.evaluate("""() => {
      th.mine = false; th.phase = 'spin'; th.boot = null;
      watchFrom({ t: 'p', id: th.id, a: [1.2, 20, 'spin', -1, 9] });
      const seen = { a: th.a, v: th.v, dir: th.dir, turn: th.turn };
      watchFrom({ t: 'p', id: 'someone-else', a: [0, 0, 'ready', 1, 0] });   // another phone's: ignored
      const a = (BEST + 90) * DEG;
      watchFrom({ t: 'rel', id: th.id, a: [a, VMAX, -1] });
      // A late `p` after the release does not pull the boot back.
      watchFrom({ t: 'p', id: th.id, a: [0, 0, 'ready', -1, 0] });
      return { seen, phase: th.phase, mark: th.mark, want: flight(a, VMAX, -1).mark };
    }""")
    assert r["seen"] == {"a": 1.2, "v": 20, "dir": -1, "turn": 9}
    assert r["phase"] in ("fly", "land")
    page.wait_for_function("th.phase === 'land'", timeout=10000)
    assert page.evaluate("th.mark") == r["want"]
    assert errors == []


def test_a_second_finger_does_not_take_the_boot(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    r = page.evaluate("""() => {
      spinStart({ pointerId: 7, clientX: ring.cx, clientY: ring.cy + ring.r, timeStamp: performance.now() });
      spinStart({ pointerId: 8, clientX: ring.cx + ring.r, clientY: ring.cy, timeStamp: performance.now() });
      const kept = spinPtr;
      spinEnd({ pointerId: 8, clientX: ring.cx + ring.r, clientY: ring.cy, timeStamp: performance.now() });
      return { kept, ptr: spinPtr, phase: th.phase };
    }""")
    assert r == {"kept": 7, "ptr": 7, "phase": "spin"}
    assert errors == []


def test_a_reload_mid_meet_offers_to_go_on(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    circles(page, 3, 300, stop_deg=133)
    page.wait_for_function("K.mine().marks.length === 1", timeout=10000)
    mark = page.evaluate("K.mine().marks[0]")
    page.reload()
    page.wait_for_function("typeof K !== 'undefined'")
    page.wait_for_selector("#cont:not(.hidden)")
    page.click("#cont")
    page.wait_for_function("K.comp !== null && th !== null")
    assert page.evaluate("K.mine().marks[0]") == mark
    assert errors == []


def test_going_back_the_other_way_keeps_the_laps(real, context):
    # Review of #507: the laps count how far the arm went, either way, so turning back after two
    # laps neither cancels the throw nor resets the arm's tiring.
    page, errors = open_game(real, context)
    my_turn(page)
    r = page.evaluate("""() => {
      spinStart({ pointerId: 7, clientX: ring.cx, clientY: ring.cy + ring.r, timeStamp: performance.now() });
      let a = -Math.PI / 2;
      const go = (n, s) => { for (let i = 0; i < n; i++) { a += s * Math.PI / 12; spinMove(ring.cx + Math.cos(a) * ring.r, ring.cy - Math.sin(a) * ring.r, clock); } };
      go(48, -1);
      const before = laps(th);
      go(24, 1);
      return { before, after: laps(th) };
    }""")
    assert abs(r["before"] - 2) < 0.05
    assert abs(r["after"] - 3) < 0.05
    page.mouse.move(*page.evaluate("[ring.cx + ring.r, ring.cy]"))
    page.evaluate("spinEnd({ pointerId: 7, clientX: ring.cx + ring.r, clientY: ring.cy, timeStamp: performance.now() })")
    assert page.evaluate("th.phase") in ("fly", "land")
    assert errors == []


def test_the_open_menu_does_not_redraw_every_frame(real, context):
    # Review of #507: a still game must not draw every frame (docs/making-games.md).
    page, errors = open_game(real, context)
    page.wait_for_timeout(300)
    n = page.evaluate("draws")
    page.wait_for_timeout(600)
    assert page.evaluate("draws") == n
    # Turning the phone draws it once again, and a meet draws every frame.
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert 0 < page.evaluate("draws") - n < 4
    page.click("#go")
    n = page.evaluate("draws")
    page.wait_for_timeout(500)
    assert page.evaluate("draws") - n > 10
    assert errors == []
