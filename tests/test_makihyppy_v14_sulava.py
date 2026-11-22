"""Mäkihyppy v14 (#480): a friend's jumper glides down the in-run and through the air on the other phones, drawn from
lib/sulava-1 (through lib/yleisurheilu-12's K.glide()) between the spots their phone sends (12 a second), instead of
easing after each spot as it comes (v13); the landing is heard when the glide has reached it, so the slide down the
outrun starts where the glide ends."""

from yleisurheilu_glide import SAMPLE, pair, steady

URL = "games/makihyppy/v14/"


def test_a_friends_jump_glides_and_lands_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, "makihyppy/v14")
    watcher.evaluate(SAMPLE, ["th", "x"])
    ys = """() => { const d = window.drawFrame; window.__ys = [];
      window.drawFrame = function () { if (th && !th.mine) window.__ys.push([th.x, th.y, th.phase]);
        return d.apply(this, arguments); }; }"""
    watcher.evaluate(ys)
    athlete.wait_for_function("th && th.mine && th.phase === 'ready'", timeout=20000)
    athlete.evaluate("go()")
    watcher.wait_for_function("th && !th.mine && th.phase === 'land'", timeout=20000)
    watcher.wait_for_timeout(300)
    xs, got, path = watcher.evaluate("[window.__xs, window.__got, window.__ys]")
    land_x = watcher.evaluate("xAtDist(th.res.d)")
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors

    run = [(t, x, ph) for t, x, ph in xs if ph in ("inrun", "fly")]
    assert len(run) > 60, len(run)
    # Down the hill the jumper only ever goes on: never drawn back towards the top.
    back = [(round(t1, 2), round(b - a, 3)) for (_, a, _), (t1, b, _) in zip(run, run[1:]) if b < a - 1e-3]
    assert not back, back
    # Even from frame to frame: the speed over two frames changes little from one pair to the next, where spots
    # came steadily (the jumper speeds up on the in-run and slows a little in the air, but never in jerks).
    sp = [(t2, (c - a) / (t2 - t0)) for (t0, a, _), (t2, c, _) in zip(run, run[2:]) if 0 < t2 - t0 < 0.1]
    jerks = [(round(t, 2), round(v0, 1), round(v1, 1)) for (_, v0), (t, v1) in zip(sp, sp[1:])
             if steady(got, t) and v0 > 5 and abs(v1 - v0) > 0.3 * v0]
    assert len(jerks) < 0.05 * len(sp), (jerks, len(sp))
    # The last frame drawn in the air is next to where the jump lands: no hop onto the landing spot.
    last = [p for p in path if p[2] == "fly"][-1]
    assert abs(last[0] - land_x) < 3, (last, land_x)
    first_land = next(p for p in path if p[2] == "land")
    assert abs(first_land[0] - last[0]) < 3, (first_land, last)
