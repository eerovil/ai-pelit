"""Kuula v13 (#480): a friend's glide or spin across the circle glides on the other phones, drawn from lib/sulava-1
(through lib/yleisurheilu-12's K.glide()) on a track of its time t, instead of jumping to each t their phone sends
and running on from it (v12); the put is heard when the glide has reached it, so the putter pushes and puts where
the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "kuula/v13"
URL = "games/kuula/v13/"

# The phone on turn spins (t runs at 1 a second for 1.4 s), pushes at the power position and lets go at 37°.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'move'; th.k = 2; th.t = 0; th.idle = 0; }
      if (th.phase === 'move' && th.t >= TECH[2].T) { th.phase = 'push'; th.off = th.t - TECH[2].T; th.hold = 0; th.ang = AIM0; }
      if (th.phase === 'push' && th.ang >= 37) { window.__run = false; letGo(); }
    }
    return st(dt);
  }; }"""


def test_a_friends_spin_glides_and_puts_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "t"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=20000)
    watcher.wait_for_timeout(200)
    ts, got = watcher.evaluate("[window.__xs, window.__got]")
    even(ts, got, ("move",), 1)
    # The last drawn moment across the circle is where the put starts: no hop of the hips at the push or the put.
    last = [t for _, t, ph in ts if ph in ("move", "push")][-1]
    put = watcher.evaluate("TECH[2].T + th.off")
    assert abs(put - last) < 0.03, (put, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
