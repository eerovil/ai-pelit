"""Mäkihyppy v14 (#480): a friend's jumper glides down the in-run and through the air on the other phones, drawn from
lib/sulava-1 (through lib/yleisurheilu-12's K.glide()) between the spots their phone sends (12 a second), instead of
easing after each spot as it comes (v13); the landing is heard when the glide has reached it, so the slide down the
outrun starts where the glide ends."""

import math

import pytest

from yleisurheilu_glide import pair, steady

URL = "games/makihyppy/v14/"

# On the phone watching: each frame the friend's jumper is drawn (inside drawFrame(), where the glide has been
# swapped in), its time, x, y, phase and the snow's height under it, and when each message arrived.
PATH = """() => { const d = window.drawFrame; window.__ys = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  window.drawFrame = function () {
    if (th && !th.mine) window.__ys.push([performance.now() / 1000, th.x, th.y, th.phase, hillY(th.x)]);
    return d.apply(this, arguments); }; }"""
# On the jumping phone: from its landing (fin) on, every message reaches the room `late` s later, in order, as on a
# network that stalls just then; the stamps stay the moments they were sent, so the landing comes after the track's
# delay, while the glide is guessing on along the flight.
LATE = """(late) => { const send = AiPelitRooms.send.bind(AiPelitRooms); let on = false;
  AiPelitRooms.send = (m, to) => { if (m && m.t === 'fin') on = true;
    if (on) setTimeout(() => send(m, to), late * 1000); else send(m, to); }; }"""


@pytest.mark.parametrize("late", [0, 0.35])
def test_a_friends_jump_glides_and_lands_where_the_glide_ends(site, browser, late):
    athlete, watcher = pair(site, browser, "makihyppy/v14")
    watcher.evaluate(PATH)
    if late:
        athlete.evaluate(LATE, late)
    athlete.wait_for_function("th && th.mine && th.phase === 'ready'", timeout=20000)
    athlete.evaluate("go()")
    watcher.wait_for_function("th && !th.mine && th.phase === 'land'", timeout=20000)
    watcher.wait_for_timeout(300)
    path, got = watcher.evaluate("[window.__ys, window.__got]")
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors

    run = [(t, x, y) for t, x, y, ph, _ in path if ph in ("inrun", "fly")]
    assert len(run) > 150, len(run)
    # Down the hill the jumper only ever goes on: never drawn back towards the top.
    back = [(round(t1, 2), round(b - a, 3)) for (_, a, _), (t1, b, _) in zip(run, run[1:]) if b < a - 1e-3]
    assert not back, back
    # Even from frame to frame: the speed (x and y) over two frames changes little from one pair to the next, where
    # spots came steadily (the jumper speeds up on the in-run and slows a little in the air, but never in jerks).
    sp = [(t2, math.hypot(x2 - x0, y2 - y0) / (t2 - t0)) for (t0, x0, y0), (t2, x2, y2) in zip(run, run[2:])
          if 0 < t2 - t0 < 0.1]
    jerks = [(round(t, 2), round(v0, 1), round(v1, 1)) for (_, v0), (t, v1) in zip(sp, sp[1:])
             if steady(got, t) and v0 > 5 and abs(v1 - v0) > 0.3 * v0]
    assert len(jerks) < 0.05 * len(sp), (jerks, len(sp))
    # In the air never drawn under the snow, even while the landing is still on its way.
    under = [(round(t, 2), round(y - h, 2)) for t, x, y, ph, h in path if ph == "fly" and y < h - 1e-6]
    assert not under, under
    # The last frame drawn in the air is next to where the jump touched down: no hop onto the landing spot.
    land_x = watcher.evaluate("th.x")  # slid on down the outrun since
    last = [p for p in path if p[3] == "fly"][-1]
    first_land = next(p for p in path if p[3] == "land")
    assert abs(first_land[1] - last[1]) < 3, (first_land, last)
    if not late:
        assert first_land[1] >= last[1] - 1e-3, (first_land, last)
    assert abs(first_land[2] - first_land[4]) < 1e-6, first_land  # landed: on the snow
    assert land_x >= first_land[1], (land_x, first_land)
    # Down the outrun too, and through a landing heard late: never a hop, at most an easing back of a few frames.
    drawn = [(t, x) for t, x, _, ph, _ in path if ph != "wait"]
    hops = [(round(t1, 2), round(b - a, 2)) for (_, a), (t1, b) in zip(drawn, drawn[1:]) if abs(b - a) > 1.2]
    assert not hops, hops
