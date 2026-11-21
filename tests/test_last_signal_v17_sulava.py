"""Last Signal v17 (#480): a friend's person walking across SISU glides on the host's screen, drawn from
lib/sulava-1 between the spots the friend's phone sends, instead of jerking to each one as it comes."""

from statistics import mean, pstdev

from test_last_signal_v17 import _close_pages, room  # noqa: F401

# Records, on every frame, where this phone draws the other phone's person.
SAMPLE = """() => { window.__xs = []; const o = Object.values(net.others)[0];
  const f = () => { window.__xs.push(o.x); if (window.__xs.length < 400) requestAnimationFrame(f); }; requestAnimationFrame(f); }"""
# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""


def test_a_friend_walking_inside_sisu_glides_on_the_host_s_screen(site, browser):
    host, guest = room(site, browser, names=("Eero", "Aino"))
    for p in (host, guest):
        p.evaluate("closeCard()")
    guest.wait_for_function("G.mode === 'home'")
    guest.evaluate("Object.assign(crew, { x: -10, y: LOW, to: null, moving: false, climbing: false }); enterRoom(true)")
    host.wait_for_function("Math.abs(Object.values(net.others)[0].x + 10) < 0.05", timeout=5000)
    guest.evaluate(JITTER)
    host.evaluate(SAMPLE)
    guest.evaluate("walkTo(10, 1.2)")
    host.wait_for_function("window.__xs.length >= 400", timeout=20000)
    xs = host.evaluate("window.__xs")
    st = [b - a for a, b in zip(xs, xs[1:])]
    walking = [s for s in st if abs(s) > 1e-4]
    # The walk shows on the host (4.2 m/s, about 0.07 m a frame), every frame of it a step forward of
    # about the same size: no frames standing still in the middle, no jumps of a whole message's walk.
    first = next(i for i, s in enumerate(st) if abs(s) > 1e-4)
    last = max(i for i, s in enumerate(st) if abs(s) > 1e-4)
    middle = st[first + 5:last - 5]
    assert len(walking) > 60, len(walking)
    assert all(s > 0 for s in middle), [round(s, 3) for s in middle]
    m, sd = mean(middle), pstdev(middle)
    assert sd < 0.25 * m, (sd, m)
    assert max(middle) < 2 * m, (max(middle), m)
    assert not host.errors and not guest.errors, host.errors + guest.errors
