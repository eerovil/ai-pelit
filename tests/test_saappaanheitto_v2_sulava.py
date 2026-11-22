"""Saappaanheitto v2 (#480): a friend's swing glides on the other phones, the boot's arm angle drawn from
lib/sulava-1 (through lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to
each spot as it comes (v1); the release is heard when the glide has reached it, so the boot leaves the hand where
the glide ends."""

import math

import pytest

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "saappaanheitto/v2"
URL = "games/saappaanheitto/v2/"

# The phone on turn swings the boot round from the moment it hangs, with no thumb, at `plan`'s speeds ([from s, rad/s],
# negative over the top, clockwise, dir -1), and lets go after `dur` s (short of the arm slipping, 14 laps). Each of
# `jumps` ([at s, rad]) turns the boot at once, as a thumb jumping over a quarter lap does. With `abort`, it first
# lifts the thumb after `abort` s, short of half a lap, as spinEnd() does (the boot hangs again), and swings again
# half a second later. It keeps th.turn and th.moves as spinMove() does (the game takes the way, dir, from the last
# 0.25 s of them), and the running angle it sends (th.w, at the start and
# at the release) is kept for the test.
DRIVE = """([plan, dur, abort, jumps]) => { const st = window.step; window.__run = true; let spun = 0, wait = 0, done = 0;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready' && (wait -= dt) <= 0) {
        th.phase = 'spin'; th.t = 0; th.turn = 0; th.v = 20; th.dir = -1; th.lap = 0; spun = 0; done = 0; window.__w0 = th.w; }
      else if (th.phase === 'spin') {
        th.idle = 0; spun += dt;
        const w = plan.filter(s => s[0] <= spun).pop()[1];
        th.moves.push([clock, w * dt]); th.turn += Math.abs(w) * dt;   // the game takes its way (dir) from these
        setA(wrapR(th.a + w * dt));
        while (done < jumps.length && jumps[done][0] <= spun) setA(wrapR(th.a + jumps[done++][1]));
        if (abort && spun >= abort) {
          abort = 0; wait = 0.5;
          th.phase = 'ready'; th.a = th.w = -Math.PI / 2 - 0.15; th.v = 0; th.turn = 0; th.dir = -1;
          K.send({ t: 'p', a: [r3(th.a), 0, 'ready', th.dir, 0, r3(th.w)] });
        } else if (spun >= dur) { window.__run = false; window.__w1 = th.w; letGo(); }
      }
    }
    return st(dt);
  }; }"""


HANG = -math.pi / 2 - 0.15


def wrap(d):
    return (d + math.pi) % (2 * math.pi) - math.pi


def unwrapped(xs):
    """The drawn angles made continuous over the ±π seam, so a speed reads the same across it."""
    out, prev, acc = [], None, 0.0
    for t, a, ph in xs:
        if prev is not None:
            acc += wrap(a - prev)
        else:
            acc = a
        prev = a
        out.append((t, acc, ph))
    return out


def swing(site, browser, plan, dur, abort=0, jumps=()):
    """A friend's swing as `plan` drives it: (the frames the watching phone drew, when its messages came, the
    athlete's running angle at the swing's start and release, the watcher's page)."""
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "a"])
    athlete.evaluate(DRIVE, [plan, dur, abort, list(jumps)])
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=20000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    w0, w1 = athlete.evaluate("[window.__w0, window.__w1]")
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
    return xs, got, w0, w1, watcher


def ends_at_release(xs, watcher):
    """The last drawn swing frame is next to the release angle: no hop round onto it."""
    last = [a for _, a, ph in xs if ph == "spin"][-1]
    rel = watcher.evaluate("th.a")
    assert -0.6 < wrap(rel - last) < 0.6, (rel, last)


# 40 rad/s is more than half a lap between two spots (12 a second): gliding the sent angle the short way round
# would turn the boot backwards, so the track glides the running angle the phone on turn sends.
# A thumb lifted early (abort) snaps the boot back to hanging: the swing is never glided back to it.
@pytest.mark.parametrize("w, dur, abort", [(12, 2.5, 0), (40, 2.0, 0), (12, 2.5, 0.2)])
def test_a_friends_swing_glides_and_lets_go_where_the_glide_ends(site, browser, w, dur, abort):
    xs, got, _, _, watcher = swing(site, browser, [[0, -w]], dur, abort)
    even(unwrapped(xs), got, ("spin",), -w)
    # Every drawn spin frame, to the last before the boot leaves, turns the boot the swing's way from the frame
    # drawn just before it (even() leaves the last 0.2 s out).
    back = [(round(t, 2), round(wrap(b - a), 2)) for (_, a, p0), (t, b, p1) in zip(xs, xs[1:])
            if p0 == p1 == "spin" and wrap(b - a) > 0.02]
    assert not back, back
    if abort:
        # The early lift snaps the boot back to hanging on the first frame it is heard: no glide back round to it.
        # (The next swing's first spots then glide on while the phase still reads ready.)
        first = next(i for i, (_, _, ph) in enumerate(xs) if ph == "spin")
        hang = next(a for _, a, ph in xs[first:] if ph == "ready")
        assert abs(hang - HANG) < 0.05, round(hang, 2)
    # The last drawn swing frame is next to the release angle: no hop round onto it.
    last =[a for _, a, ph in xs if ph == "spin"][-1]
    rel = watcher.evaluate("th.a")
    assert -0.6 < wrap(rel - last) < 0.06, (rel, last)


# The thumb turns back mid-swing (once, and once again just before the release), and jumps over a quarter lap at
# once: the boot is drawn turning as far as the friend's own running angle went, never a lap off (before, the
# watching phone guessed the way from the thumb's last 0.25 s, and drew a false lap at a turn back).
@pytest.mark.parametrize("plan, dur, jumps", [
    ([[0, -25], [1.0, 25], [1.6, -25]], 2.2, []),
    ([[0, -25], [1.6, 25]], 1.8, []),
    ([[0, -12]], 2.0, [[0.7, 2.0], [1.3, -1.9]]),
])
def test_a_turn_back_or_a_jump_is_drawn_as_far_as_it_went(site, browser, plan, dur, jumps):
    xs, _, w0, w1, watcher = swing(site, browser, plan, dur, jumps=jumps)
    run = unwrapped([f for f in xs if f[2] in ("ready", "spin")])
    went = run[-1][1] - run[0][1]
    assert abs(went - (w1 - w0)) < 0.7, (went, w1 - w0)
    sp = [abs(b - a) / (t1 - t0) for (t0, a, _), (t1, b, _) in zip(run, run[1:]) if t1 > t0]
    assert max(sp) < 50, round(max(sp), 1)
    ends_at_release(xs, watcher)
