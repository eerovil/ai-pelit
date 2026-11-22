"""Korkeushyppy v17 (#480): a friend's run-up glides on the other phones, drawn from lib/sulava-1 (through
lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to each spot as it comes
and carrying it on at its speed (v16); the take-off is heard when the glide has reached it, so the jumper leaves
the curve where the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "korkeushyppy/v17"
URL = "games/korkeushyppy/v17/"

# The phone on turn runs at 6 m/s (under the curve's cap) from the start, with no taps, and takes off 2 m
# before the bar, as the jump button does.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'run'; th.t = 0; }
      if (th.phase === 'run') { th.v = 6; th.idle = 0; if (th.x >= -2) { window.__run = false; jumpPress(); } }
    }
    return st(dt);
  }; }"""

# On the phone watching: where the take-off puts the jumper.
UP = """() => { const t0 = window.takeOff; window.takeOff = (d, v) => { window.__up = -d; return t0(d, v); }; }"""


def test_a_friends_run_up_glides_and_takes_off_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "x"])
    watcher.evaluate(UP)
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'air'", timeout=15000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(xs, got, ("run", "ready"), 6)
    # The last drawn run-up frame is next to the take-off spot: no hop forward to it.
    last = [x for _, x, ph in xs if ph in ("run", "ready")][-1]
    up = watcher.evaluate("window.__up")
    assert -0.05 < up - last < 0.3, (up, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
