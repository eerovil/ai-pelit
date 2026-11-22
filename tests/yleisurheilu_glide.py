"""Helpers for the field events' glide tests (#480, lib/yleisurheilu-12 with lib/sulava-1): two phones in a meet,
the athlete on turn driven at an even speed over a jittery network, and what the phone watching draws."""

from statistics import mean, pstdev

from test_yleisurheilu_vuorot import room

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""

# On the phone watching: each frame the friend's athlete is drawn, `key` of the game's turn object `obj` as drawn
# (inside drawFrame(), where the glide has been swapped in), its phase, and when each message arrived.
SAMPLE = """([obj, key]) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.drawFrame;
  window.drawFrame = function () { const a = window.eval(obj);
    if (a && !a.mine && window.__xs.length < 600) window.__xs.push([performance.now() / 1000, a[key], a.phase]);
    return d.apply(this, arguments); }; }"""


def pair(site, browser, path):
    """Two phones in a meet of `path`, on the first friend's turn: (the athlete's page, the watching page)."""
    _, pages, _ = room(site, browser, path, ["Testi A", "Testi B"])
    host = pages[0]
    host.wait_for_function("K.current() && K.current().p !== null", timeout=20000)
    pid = host.evaluate("K.current().p")
    athlete = next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)
    watcher = next(p for p in pages if p is not athlete)
    athlete.evaluate(JITTER)
    return athlete, watcher


def steady(got, t):
    """Spots came in steadily just before `t`: a loaded test machine sometimes holds the messages back longer than
    the track's longest delay (0.25 s), and nothing glides through such a hole."""
    before = [g for g in got if g <= t]
    return len(before) > 1 and t - before[-1] < 0.15 and before[-1] - before[-2] < 0.2


def even(xs, got, phases, want, lo=None):
    """The drawn speed over each two frames in `phases` is about `want` units a second, and never backwards."""
    run = [(t, x) for t, x, ph in xs if ph in phases]
    sp = [(t2, (b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(run, run[2:]) if t2 > t0 and t2 - t0 < 0.1]
    moving = [t for t, v in sp if abs(v) > 0.2 * abs(want)]
    assert len(moving) > 40, (len(moving), len(sp))
    middle = [(t, v) for t, v in sp if moving[0] + 0.5 <= t <= moving[-1] - 0.2]
    kept = [v for t, v in middle if steady(got, t)]
    shown = [round(v, 1) for v in kept]
    assert len(kept) > 20 and len(kept) > 0.5 * len(middle), (len(kept), len(middle))
    sign = 1 if want > 0 else -1
    assert min(sign * v for v in kept) > (lo if lo is not None else 0.25 * abs(want)), shown
    m, sd = mean(kept), pstdev(kept)
    assert 0.75 * abs(want) < sign * m < 1.25 * abs(want), shown
    assert sd < 0.25 * abs(m), (sd, m, shown)
    return kept
