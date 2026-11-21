"""Last Signal v17 (#480): a friend's person walking across SISU glides on the other phones' screens, drawn from
lib/sulava-1 between the spots the friend's phone sends, instead of jerking to each one as it comes; so does SISU
when a friend drives it, and it stops where they let go."""

from statistics import mean, pstdev

from test_last_signal_v17 import _close_pages, room  # noqa: F401

# Records, on every frame, the time and where this phone draws `what` (a JS expression), and when a message
# from another phone arrived, so a stall of the test machine (no message for a while) can be told from a jerk.
SAMPLE = """(what) => { window.__xs = []; window.__got = []; const read = new Function('return ' + what);
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const f = () => { window.__xs.push([performance.now() / 1000, read()]);
    if (window.__xs.length < 400) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""
# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""


def other_x(walker):
    return "net.others[%r].x" % walker.evaluate("AiPelitRooms.me")


def glides(page, settle=0, ends=None):
    """The speed over each two frames of what SAMPLE drew, while it moved: always forward and about the same.
    Left out: the first and last metre of a walk from ends[0] to ends[1] (it starts and stops there, where even
    the library guesses wrong for a moment), `settle` (a share of the move at its start, while the mover still
    sped up), and where the phone heard nothing for 0.3 s (the test machine stalled: the player rightly stops)."""
    xs, got = page.evaluate("[window.__xs, window.__got]")
    lo, hi = (ends[0] + 1, ends[1] - 1) if ends else (-1e9, 1e9)
    sp = [(t2, (c - a) / (t2 - t0)) for (t0, a), (t2, c) in zip(xs, xs[2:]) if t2 > t0 and lo < a and c < hi]
    moving = [i for i, (_, v) in enumerate(sp) if abs(v) > 0.01]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 5 + int(settle * (moving[-1] - moving[0])):moving[-1] - 5]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 0, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def start_walk(walker, *watchers):
    walker.wait_for_function("G.mode === 'home'")
    walker.evaluate("Object.assign(crew, { x: -10, y: LOW, to: null, moving: false, climbing: false }); enterRoom(true)")
    for w in watchers:
        w.wait_for_function(f"Math.abs({other_x(walker)} + 10) < 0.05", timeout=5000)


def test_a_friend_walking_inside_sisu_glides_on_the_host_s_screen(site, browser):
    host, guest = room(site, browser, names=("Eero", "Aino"))
    for p in (host, guest):
        p.evaluate("closeCard()")
    start_walk(guest, host)
    guest.evaluate(JITTER)
    host.evaluate(SAMPLE, other_x(guest))
    guest.evaluate("walkTo(10, 1.2)")
    host.wait_for_function("window.__xs.length >= 400", timeout=20000)
    glides(host, ends=(-10, 10))
    assert not host.errors and not guest.errors, host.errors + guest.errors


def test_a_friend_walking_glides_on_a_third_phone_too(site, browser):
    """The host forwards the walker's spots with the walker's own clock, so a third phone draws them as smoothly."""
    host, aino, ville = room(site, browser, names=("Eero", "Aino", "Ville"))
    for p in (host, aino, ville):
        p.evaluate("closeCard()")
    ville.wait_for_function("G.mode === 'home'")
    start_walk(aino, ville)
    aino.evaluate(JITTER)
    host.evaluate(JITTER)
    ville.evaluate(SAMPLE, other_x(aino))
    aino.evaluate("walkTo(10, 1.2)")
    ville.wait_for_function("window.__xs.length >= 400", timeout=20000)
    glides(ville, ends=(-10, 10))
    assert not host.errors and not aino.errors and not ville.errors


def test_sisu_driven_by_a_friend_glides_and_stops_where_they_let_go(site, browser):
    host, guest = room(site, browser, names=("Eero", "Aino"))
    for p in (host, guest):
        p.evaluate("closeCard()")
    host.evaluate("openHome(); closeCard()")
    guest.wait_for_function("G.mode === 'home'")
    guest.evaluate("""(() => { const r = ROOMS.find(r => r.id === 'ohjaamo');
      Object.assign(crew, { x: (r.x0 + r.x1) / 2, y: UP, to: null, moving: false, climbing: false }); enterRoom(true); toHelm(); })()""")
    guest.wait_for_function("G.mode === 'sub'", timeout=5000)
    host.wait_for_function(f"net.helm === {guest.evaluate('AiPelitRooms.me')!r}")
    guest.evaluate(JITTER)
    host.evaluate(SAMPLE, "sub.x")
    guest.evaluate("G.hold = false; input.x = 1; input.y = 0")
    host.wait_for_function("window.__xs.length >= 400", timeout=20000)
    glides(host, settle=0.5)  # SISU speeds up for over a second
    # Let go and leave the helm: on the host SISU stops at the driver's last spot, without driving on past it.
    host.evaluate("window.__after = []; const f = () => { window.__after.push(sub.x); if (window.__after.length < 120) requestAnimationFrame(f); }; requestAnimationFrame(f)")
    guest.evaluate("input.x = 0; openHome(); closeCard()")
    host.wait_for_function("window.__after.length >= 120 && net.helm === null", timeout=10000)
    after = host.evaluate("window.__after")
    guest.wait_for_function("Math.abs(sub.x - %r) < 0.05" % after[-1], timeout=5000)
    assert max(after) <= after[-1] + 0.05, (max(after), after[-1])
    assert after[-1] == after[-30]
    assert not host.errors and not guest.errors, host.errors + guest.errors
