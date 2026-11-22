"""Moukari v15 (#480): a friend's spin glides on the other phones, drawn from lib/sulava-1 (through
lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to each spot as it comes
(v14); the release is heard when the glide has reached it, so the hammer leaves where the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "moukari/v15"
URL = "games/moukari/v15/"

# The phone on turn spins at an even 8 rad/s from the start, with no taps (its speed set each step for the wire's
# length at that angle), and lets go a radian before the foul at the end of the last turn. The angle a counts up
# over every lap, so it needs no unwrapping.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'spin'; th.t = 0; th.a = START_A; th.chk = 0; th.tapped = {}; th.idle = 0; }
      if (th.phase === 'spin') {
        if (th.a >= TAU * LAPS - 1) { window.__run = false; release(); }
        else th.v = 8 * radius(th.a) / SLOW;
      }
    }
    return st(dt);
  }; }"""


def test_a_friends_spin_glides_and_lets_go_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "a"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=20000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(xs, got, ("spin",), 8)
    # The last drawn spin frame is next to the release angle: no hop round onto it.
    last = [a for _, a, ph in xs if ph == "spin"][-1]
    rel = watcher.evaluate("th.a")
    assert -0.05 < rel - last < 0.4, (rel, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
