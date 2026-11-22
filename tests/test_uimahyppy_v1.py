"""Uimahyppy v1 (#516): springboard diving. Taps in time with the board bounce the diver higher, a
held finger takes off and tucks into somersaults, sliding it sideways twists, lifting it opens before
the water; five judges score the entry and the meet (kisa.js) sums every dive's points."""

import math

from conftest import turn
from test_hiljaiset_aanet import cheer_is_quiet, opens_and_plays_with_the_quiet_library, real  # noqa: F401

URL = "games/uimahyppy/v1"


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, URL)


def test_the_cheer_chime_is_quiet():
    cheer_is_quiet(URL)


def open_game(real, context):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{real.url}{URL}/")
    page.wait_for_function("typeof judge === 'function' && typeof K !== 'undefined'")
    return page, errors


def my_turn(page):
    """Starts a meet alone and runs it on to this phone's first dive, the diver ready on the board."""
    page.click("#go")
    page.wait_for_function("th !== null")
    for _ in range(60):
        if page.evaluate("th && th.mine"):
            break
        page.evaluate("if (th && !th.mine && th.phase !== 'water') th.t = 99")
        page.wait_for_timeout(250)
    page.evaluate("th.t = 99")
    page.wait_for_function("th.phase === 'ready'")


def bounce(page, taps, size):
    """Starts the bounce with one tap, then taps once in the middle of each press of the board."""
    w, h = size
    page.mouse.move(w / 2, h / 2)
    page.mouse.down()
    page.wait_for_timeout(40)
    page.mouse.up()
    heights = []
    for _ in range(taps):
        page.wait_for_function("th.b && !th.b.air && th.b.tc > 0.1", polling=5)
        page.mouse.down()
        page.wait_for_timeout(40)
        page.mouse.up()
        page.wait_for_function("th.b.air", polling=5)
        heights.append(page.evaluate("th.b.h"))
    return heights


def dive(page, size, somersaults=1.5):
    """Bounces high, takes off on a held finger and opens near the given somersaults."""
    bounce(page, 6, size)
    page.wait_for_function("th.b && !th.b.air && th.b.tc > 0.1", polling=5)
    page.mouse.down()
    page.wait_for_function("th.phase === 'dive'", polling=5)
    page.wait_for_function(f"th.d.a > {somersaults * 2} * Math.PI - 1.2 || th.d.y < 1.5", polling=5)
    page.mouse.up()
    page.wait_for_function("th.phase === 'water'", timeout=5000)
    return page.evaluate("th.res")


def test_the_judges_like_a_straight_open_entry_from_high(real, context):
    page, errors = open_game(real, context)
    r = page.evaluate("""() => {
      const fixed = () => 0.25;   // gauss() of 0: every judge gives the same
      return {
        clean: judge(3 * Math.PI, 0, 0, HMAX, fixed),
        off: judge(3 * Math.PI + 30 * DEG, 0, 0, HMAX, fixed),
        tucked: judge(3 * Math.PI, 0, 1, HMAX, fixed),
        low: judge(3 * Math.PI, 0, 0, 0.3, fixed),
        flat: judge(2.5 * Math.PI, 0, 0, HMAX, fixed),
        back: judge(3.5 * Math.PI, 0, 0, HMAX, fixed),
        twist: judge(3 * Math.PI, 2 * Math.PI, 0, HMAX, fixed),
        feet: judge(0, 0, 0, HMAX, fixed),
        hard: judge(5 * Math.PI, 0, 0, HMAX, fixed),
      };
    }""")
    c = r["clean"]
    assert c["halves"] == 3 and c["dd"] == 2.0 and c["name"] == "1½ voltin hyppy" and not c["why"]
    assert c["judges"] == [10, 10, 10, 10, 10] and c["pts"] == 60
    assert r["off"]["pts"] < c["pts"] and r["tucked"]["pts"] < r["off"]["pts"]
    assert r["low"]["pts"] < c["pts"]
    # Flat on the water: on the belly face down, on the back face up, and hardly any points.
    assert r["flat"]["why"] == "Mahalasku!" and r["flat"]["pts"] < 15
    assert r["back"]["why"] == "Selkälasku!"
    # Twists and more somersaults make it harder, so a clean one scores more.
    assert r["twist"]["tw"] == 2 and r["twist"]["dd"] == 2.4 and r["twist"]["name"] == "1½ voltin hyppy, 1 kierre"
    assert r["twist"]["pts"] > c["pts"]
    assert r["feet"]["name"] == "Suora hyppy" and r["feet"]["dd"] == 1.0
    assert r["hard"]["dd"] == 2.6 and r["hard"]["name"] == "2½ voltin hyppy"
    # The highest and lowest judge are left out.
    mid = page.evaluate("""() => { let i = 0; const seq = [0.9, 0.1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
      const g = judge(3 * Math.PI, 0, 0, HMAX, () => seq[i++ % seq.length]); return g; }""")
    js = sorted(mid["judges"])
    assert abs(mid["pts"] - round(sum(js[1:4]) * mid["dd"], 2)) < 1e-9
    assert errors == []


def test_a_clean_two_and_a_half_needs_the_highest_bounce(real, context):
    # The flight from a low bounce is too short to turn 2½ somersaults and open: the bounce matters.
    page, _ = open_game(real, context)
    r = page.evaluate("""() => {
      const fly = (h, hold) => {
        const a = { phase: 'dive', t: 0, d: { x: FOOT_X, y: BOARD_Y + HIP, vx: VX, vy: Math.sqrt(2 * G * h), a: 0.1, w: 0, k: 0, h }, drops: [], mine: false };
        const saved = enter; let res = null;
        enter = (_, r) => { res = r; a.phase = 'water'; };
        for (let t = 0; a.phase === 'dive' && t < 5; t += 1 / 60) { ptr = t < hold ? 1 : null; stepDive(a, 1 / 60); }
        enter = saved; ptr = null;
        return res;
      };
      const best = h => { let b = null; for (let hold = 0; hold < 1.6; hold += 0.01) { const r = fly(h, hold); if (r && r.halves === 5 && r.err < 20 && (!b || r.pts > b.pts)) b = r; } return b; };
      return { high: best(HMAX), low: best(0.3) };
    }""")
    assert r["high"] is not None and r["high"]["pts"] > 55
    assert r["low"] is None


def test_the_computer_never_dives_past_75_points(real, context):
    page, _ = open_game(real, context)
    marks = page.evaluate("Array.from({ length: 20000 }, () => cpuMark({ skill: 62 }))")
    assert max(marks) <= 75
    assert max(marks) > 74
    assert min(marks) >= 3
    low = page.evaluate("Array.from({ length: 5000 }, () => cpuMark({ skill: 30 }))")
    assert 27 < sum(low) / len(low) < 31


def test_the_meet_sums_every_dive(real, context):
    page, errors = open_game(real, context)
    r = page.evaluate("""() => {
      const F = K.F, c = { throwers: [
        { id: 'a', marks: [40, 41.5, 30] }, { id: 'b', marks: [60, 20, 20] }, { id: 'c', marks: [] }, { id: 'd', marks: [50, 0, 0] }] };
      return { order: F.standings(c).map(t => t.id), best: c.throwers.map(F.bestOf), missed: F.missed, rounds: F.ROUNDS, cut: F.CUT };
    }""")
    assert r["order"] == ["a", "b", "d", "c"]
    assert r["best"] == [111.5, 100, -2, 50]
    assert r["missed"] == 0 and r["rounds"] == 5 and r["cut"] == 3
    # The board's right column says the points are summed.
    texts = page.evaluate("""() => {
      K.solo(); const seen = [];
      const g = document.createElement('canvas').getContext('2d'), ft = g.fillText;
      g.fillText = function (s, ...r) { seen.push(s); return ft.call(this, s, ...r); };
      K.drawBoard(g, false, { w: 360, top: 100, bottom: 700 });
      return seen;
    }""")
    assert "YHT." in texts and "PARAS" not in texts
    assert errors == []


def test_taps_in_time_bounce_higher_and_a_hold_dives(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    heights = bounce(page, 5, (360, 740))
    assert heights[-1] > heights[0] + 0.8, heights
    assert all(b >= a for a, b in zip(heights, heights[1:])), heights
    res = None
    page.wait_for_function("th.b && !th.b.air && th.b.tc > 0.1", polling=5)
    page.mouse.down()
    page.wait_for_function("th.phase === 'dive'", polling=5)
    assert page.evaluate("th.d.h") > 1.2
    page.wait_for_timeout(250)
    assert page.evaluate("th.d.k") > 0.9   # tucked while the finger stays down
    page.wait_for_function("th.d.a > 3 * Math.PI - 1.2 || th.d.y < 1.5", polling=5)
    page.mouse.up()
    page.wait_for_timeout(200)
    assert page.evaluate("th.phase === 'water' || th.d.k < 0.1")
    page.wait_for_function("th.phase === 'water'", timeout=5000)
    res = page.evaluate("th.res")
    assert res["halves"] >= 2 and res["pts"] > 20, res
    # Its points go to the meet once the splash has settled.
    page.wait_for_function("K.mine().marks.length === 1", timeout=8000)
    assert page.evaluate("K.mine().marks[0]") == res["pts"]
    assert errors == []


def test_taps_off_the_beat_or_none_bounce_lower(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    bounce(page, 4, (360, 740))
    high = page.evaluate("th.b.h")
    # No tap on the next press: the hop halves.
    page.wait_for_function("th.b && !th.b.air", polling=5)
    page.wait_for_function("th.b.air", polling=5)
    assert page.evaluate("th.b.h") < high * 0.6
    assert page.evaluate("th.phase") == "bounce"
    assert errors == []


def test_sliding_the_held_finger_twists(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    bounce(page, 5, (360, 740))
    page.wait_for_function("th.b && !th.b.air && th.b.tc > 0.1", polling=5)
    page.mouse.down()
    page.wait_for_function("th.phase === 'dive'", polling=5)
    page.mouse.move(180 + 90, 370, steps=4)
    page.wait_for_timeout(300)
    w = page.evaluate("th.d.w")
    assert w > 1
    page.mouse.up()
    page.wait_for_function("th.phase === 'water'", timeout=5000)
    r = page.evaluate("[th.d.w, th.res.tw]")
    # Let go, the twist finished on a half turn.
    assert abs(r[0] - r[1] * math.pi) < 0.05 and r[1] >= 1
    assert errors == []


def test_on_its_side_it_fits_and_dives(real, context):
    page, errors = open_game(real, context)
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    my_turn(page)
    # The whole dive fits between the score bar and the bottom: the top of the highest hop, the water.
    assert page.evaluate("sy(BOARD_Y + HIP + HMAX + 0.8) > hudTop + 36 && OY < sceneB - 10")
    res = dive(page, (740, 360))
    assert res["pts"] > 0
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
      ptr = 7;
      const ev = new PointerEvent('pointerup', { pointerId: 7, clientX: 100, clientY: 100 });
      lastT = ev.timeStamp - 8;
      window.dispatchEvent(ev);
      log.push(ptr);
      return log;
    }""")
    assert abs(log[0] - 0.008) < 1e-6
    assert log[1:] == [None]


def test_a_watching_phone_draws_the_same_dive(real, context):
    # In a room the diver's phone sends `p` while bouncing and diving and `end` with the judges' points;
    # a phone watching draws the dive and shows the same points.
    page, errors = open_game(real, context)
    my_turn(page)
    r = page.evaluate("""() => {
      th.mine = false; th.track = AiPelitSulava.track({ keys: ['x', 'y', 'a', 'w', 'k', 'd'] });
      watchFrom({ t: 'p', id: th.id, s: 1, a: [0.3, 4.5, 1.2, 0, 1, 0, 'dive'] });
      watchFrom({ t: 'p', id: 'someone-else', s: 1, a: [0, 0, 0, 0, 0, 0, 'bounce'] });   // another phone's: ignored
      const seen = { phase: th.phase, pose: pose(th) };
      const res = judge(3 * Math.PI, 0, 0, HMAX, () => 0.25);
      watchFrom({ t: 'end', id: th.id, r: res, a: [1.5, 0.15, 3 * Math.PI, 0, 0] });
      watchFrom({ t: 'p', id: th.id, s: 2, a: [0, 4, 0, 0, 0, 0, 'dive'] });   // late: does not pull it back
      return { seen, phase: th.phase, pts: th.res.pts, want: res.pts };
    }""")
    assert r["seen"]["phase"] == "dive"
    assert abs(r["seen"]["pose"]["a"] - 1.2) < 1e-6 and abs(r["seen"]["pose"]["y"] - 4.5) < 1e-6
    assert r["phase"] == "water" and r["pts"] == r["want"]
    assert errors == []


def test_a_second_finger_does_not_take_the_dive(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    r = page.evaluate("""() => {
      press({ pointerId: 7, clientX: 100, clientY: 300 });
      press({ pointerId: 8, clientX: 200, clientY: 300 });
      const kept = ptr;
      release({ pointerId: 8, timeStamp: performance.now() });
      return { kept, ptr, phase: th.phase };
    }""")
    assert r == {"kept": 7, "ptr": 7, "phase": "bounce"}
    assert errors == []


def test_a_reload_mid_meet_offers_to_go_on(real, context):
    page, errors = open_game(real, context)
    my_turn(page)
    dive(page, (360, 740))
    page.wait_for_function("K.mine().marks.length === 1", timeout=10000)
    mark = page.evaluate("K.mine().marks[0]")
    page.reload()
    page.wait_for_function("typeof K !== 'undefined'")
    page.wait_for_selector("#cont:not(.hidden)")
    page.click("#cont")
    page.wait_for_function("K.comp !== null && th !== null")
    assert page.evaluate("K.mine().marks[0]") == mark
    assert errors == []


def test_the_open_menu_does_not_redraw_every_frame(real, context):
    # A still game must not draw every frame (docs/making-games.md).
    page, errors = open_game(real, context)
    page.wait_for_timeout(300)
    n = page.evaluate("draws")
    page.wait_for_timeout(600)
    assert page.evaluate("draws") == n
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert 0 < page.evaluate("draws") - n < 4
    page.click("#go")
    n = page.evaluate("draws")
    page.wait_for_timeout(500)
    assert page.evaluate("draws") - n > 10
    assert errors == []
