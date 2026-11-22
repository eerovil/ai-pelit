"""Pituushyppy v20 (#480): a friend's run-up glides on the other phones, drawn from lib/sulava-1 (through
lib/yleisurheilu-12's K.glide()) between the spots their phone sends, instead of jumping to each spot as it comes
and carrying it on at its speed (v19); the take-off is heard when the glide has reached it, so the jumper leaves
the board where the glide ends."""

from yleisurheilu_glide import SAMPLE, even, pair

PATH = "pituushyppy/v20"
URL = "games/pituushyppy/v20/"

# The phone on turn runs at 9 m/s from the start, with no taps, and takes off 1.5 m before the board.
DRIVE = """() => { const st = window.step; window.__run = true;
  window.step = dt => {
    if (th && th.mine && window.__run) {
      if (th.phase === 'ready') { th.phase = 'run'; th.t = 0; }
      if (th.phase === 'run') { th.v = 9; th.idle = 0; if (th.x >= -1.5) { window.__run = false; th.ang = 20; leap(); } }
    }
    return st(dt);
  }; }"""


def test_a_friends_run_up_glides_and_takes_off_where_the_glide_ends(site, browser):
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "x"])
    athlete.evaluate(DRIVE)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=15000)
    watcher.wait_for_timeout(200)
    xs, got = watcher.evaluate("[window.__xs, window.__got]")
    even(xs, got, ("run", "ready"), 9)
    # The last drawn run-up frame is next to the take-off spot: no hop forward onto the board.
    last = [x for _, x, ph in xs if ph in ("run", "ready", "aim")][-1]
    rel = watcher.evaluate("th.relX")
    assert -0.05 < rel - last < 0.4, (rel, last)
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors


def test_a_stalled_frame_on_the_athletes_phone_never_draws_them_back(site, browser):
    """A busy phone misses frames: the game moves its athlete at most 0.05 s a frame, so after a stalled frame it has
    gone less far than the wall clock says. lib/yleisurheilu-12 stamps the spots on a clock that moves the same way
    and catches up slowly (stampTick): stamped on the wall clock, the watching phone guessed the athlete on at full
    speed through the stall and then drew it back (9 m/s, then -5.9)."""
    athlete, watcher = pair(site, browser, PATH)
    watcher.evaluate(SAMPLE, ["th", "x"])
    athlete.evaluate(DRIVE)
    athlete.wait_for_function("th && th.mine && th.phase === 'run'", timeout=15000)
    athlete.wait_for_timeout(600)
    for _ in range(3):
        athlete.evaluate("() => { const e = performance.now() + 200; while (performance.now() < e); }")
        athlete.wait_for_timeout(300)
    watcher.wait_for_function("th && th.phase === 'fly'", timeout=15000)
    xs = watcher.evaluate("window.__xs")
    run = [(t, x) for t, x, ph in xs if ph in ("run", "ready")]
    back = [(round(t1, 2), round(b - a, 3)) for (_, a), (t1, b) in zip(run, run[1:]) if b < a - 1e-3]
    assert not back, back
    assert run[-1][1] - run[0][1] > 20, (run[0][1], run[-1][1])
    assert not athlete.errors and not watcher.errors, athlete.errors + watcher.errors
