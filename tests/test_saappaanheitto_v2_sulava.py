"""Saappaanheitto v2 (#480): a friend's swing glides on the other phones, the boot's arm angle drawn from
lib/sulava-1 (through lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to
each spot as it comes (v1); the release is heard when the glide has reached it, so the boot leaves the hand where
the glide ends."""

import math

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "saappaanheitto/v2"
URL = "games/saappaanheitto/v2/"

# The phone on turn swings the boot over the top (clockwise, dir -1) at an even 12 rad/s from the moment the boot
# hangs, with no thumb, and lets go after 2.5 s (about five laps, short of the tiring arm).
W = 12
DRIVE = """() => { const st = window.step; window.__run = true; let spun = 0;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'spin'; th.t = 0; th.turn = 0; th.v = 20; th.dir = -1; th.lap = 0; spun = 0; }
      else if (th.phase === 'spin') {
        th.idle = 0; spun += dt;
        let a = th.a - 12 * dt; if (a <= -Math.PI) a += 2 * Math.PI;
        th.a = a; th.turn += 12 * dt;
        if (spun >= 2.5) { window.__run = false; letGo(); }
      }
    }
    return st(dt);
  }; }"""


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


def test_a_friends_swing_glides_and_lets_go_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "a"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=20000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(unwrapped(xs), got, ("spin",), -W)
    # The last drawn swing frame is next to the release angle: no hop round onto it.
    last = [a for _, a, ph in xs if ph == "spin"][-1]
    rel = watcher.evaluate("th.a")
    assert -0.6 < wrap(rel - last) < 0.06, (rel, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
