"""Keihäänheitto v19 (#480): a friend's run-up glides on the other phones, drawn from lib/sulava-1 (through
lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to each spot as it comes
and carrying it on at its speed (v18); the release is heard when the glide has reached it, so the javelin leaves
the hand where the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "keihas/v19"
URL = "games/keihas/v19/"

# The phone on turn runs at 9 m/s from the start, with no taps, and throws at 36 degrees 8 m before the line.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'run'; th.t = 0; }
      if (th.phase === 'run') { th.v = 9; th.idle = 0;
        if (th.x >= -8) { window.__run = false; th.phase = 'aim'; th.aimT = 1; th.ang = 36; letFly(); } }
    }
    return st(dt);
  }; }"""


def test_a_friends_run_up_glides_and_releases_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "x"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=15000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(xs, got, ("run", "ready"), 9)
    # The last drawn run-up frame is next to the release spot: no hop forward to it.
    last = [x for _, x, ph in xs if ph in ("run", "ready", "aim")][-1]
    rel = watcher.evaluate("th.relX")
    assert -0.05 < rel - last < 0.4, (rel, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
