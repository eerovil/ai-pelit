"""Seiväshyppy v18 (#480): a friend's run-up glides on the other phones, drawn from lib/sulava-1 (through
lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to each spot as it comes
and carrying it on at its speed (v17); the plant is heard when the glide has reached it, so the pole goes down
where the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "seivashyppy/v18"
URL = "games/seivashyppy/v18/"

# The phone on turn runs at 9 m/s from the start, with no taps, and plants the pole 0.2 m before the take-off spot.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'run'; th.t = 0; }
      if (th.phase === 'run') { th.v = 9; th.idle = 0; if (th.x >= TAKEOFF - 0.2) { window.__run = false; hold(1); } }
    }
    return st(dt);
  }; }"""


def test_a_friends_run_up_glides_and_plants_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "x"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'pole'", timeout=15000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(xs, got, ("run", "ready"), 9)
    # The last drawn run-up frame is next to the plant: no hop forward onto the box.
    last = [x for _, x, ph in xs if ph in ("run", "ready")][-1]
    px = watcher.evaluate("th.px")
    assert -0.05 < px - last < 0.4, (px, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
