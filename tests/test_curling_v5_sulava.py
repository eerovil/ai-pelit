"""Curling v5 (#480): what another phone moves glides on this phone's screen, drawn from lib/sulava-1 between the
spots heard, instead of jumping to each one as it comes. A guest draws the host's sliding stones a moment back (v4
carried each on at its speed and chased the host's newest spot); every phone draws a friend's aim (the broom the
thrower drags) the same way (v4 drew each spot as it came, 10 and 8 times a second). The rules keep the newest spot."""

import json
import pytest
import shutil
from statistics import mean, median, pstdev

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/curling/v5/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# Records, each time the game works out where to draw (the function `hook`, called once a frame), the moment it was
# called and what `what` gives then ([x, y] as drawn; `r` is what the hook returned), and when a message arrived
# (so a stall of the test machine, with no message for a while, can be told from a jerk). The moment is taken as
# the hook starts, not after the drawing, whose time on a busy test machine varies.
SAMPLE = """([hook, what]) => { window.__xs = []; window.__got = []; const f = new Function('r', 'return ' + what);
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window[hook];
  window[hook] = (...a) => { const t = performance.now() / 1000, r = d(...a), v = f(r);
    if (v && window.__xs.length < 400) window.__xs.push([t, ...v]); return r; }; }"""
STONE = ["stonesDrawn", "phase === 'slide' && stones[0] ? [stones[0].x, stones[0].y, stones[0].tr.time] : null"]
# On the host: each time its frames stalled for longer than one step of the world may take (50 ms, `loop()`), when
# on its clock. The world then ran slower than the clock, so the spots it sent were themselves uneven in time; on a
# busy test machine that is no fault of the drawing.
STALLS = """() => { window.__stall = []; let last = null; const u = window.update;
  window.update = dt => { const t = performance.now() / 1000; if (last !== null && t - last > 0.05) window.__stall.push([last, t]);
    last = t; u(dt); }; }"""
AIM = ["aimDrawn", "phase === 'aim' && aimShown ? [r.x, 0] : null"]
# The thrower's finger drags the broom across at 0.6 m a second, moved each frame just before the game sends it (as
# a pointermove would come before the frame; a separate animation frame might run after the send on a busy machine).
DRAG = """() => { drag.id = 99; const t0 = performance.now(), u = window.guestUpdate;
  window.guestUpdate = dt => { if (drag.id === 99) { aim.x = -1.5 + 0.6 * (performance.now() - t0) / 1000; aim.w = 0.5;
    aimShown = true; } u(dt); }; }"""


def phones(site, browser, names=("Eero", "Aino")):
    """Phones in a room; teams go by the order they joined (Eero and the third phone yellow, Aino red), and the
    hammer is the yellows', so Aino throws first."""
    shutil.copytree(ROOT / "games" / "curling", site.games / "curling", dirs_exist_ok=True)
    site.build()
    relay, pages = Relay(), []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                                  service_workers="block")
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.click("#multi")
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    for g in guests:
        g.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
        g.click("#aipr-joinBtn")
        g.wait_for_function("AiPelitRooms.inRoom")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(pages)}")
    host.evaluate("window.__rnd = Math.random; Math.random = () => 0.1")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("net.setup && phase === 'aim'")
    host.evaluate("Math.random = window.__rnd")
    aino = pages[1].evaluate("AiPelitRooms.me")
    assert host.evaluate("thrower()") == aino
    for p in guests:
        p.wait_for_function(f"net.th === {json.dumps(aino)}")
    host.relay = relay
    return pages


def glides(page, steady=False, stalls=()):
    """The speed over each two drawn frames while it moved: never far from the speed around it (a stone slows down
    as it slides), and for the dragged broom about the same throughout. With `stalls` (the host's, on its clock),
    frames drawing a moment near one (the sample's third value) are left out."""
    xs, got = page.evaluate("[window.__xs, window.__got]")

    def stalled(q):
        return len(q) > 3 and any(a - 0.1 <= q[3] <= b + 0.1 for a, b in stalls)
    sp = [(q2[0], -1 if stalled(q0) or stalled(q2) else ((q2[1] - q0[1]) ** 2 + (q2[2] - q0[2]) ** 2) ** 0.5 / (q2[0] - q0[0]))
          for q0, q2 in zip(xs, xs[2:]) if q2[0] > q0[0]]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.05 or v < 0]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    middle = [(t, v) for t, v in middle if v >= 0]
    vs = [v for _, v in middle]
    shown = [round(v, 2) for v in vs]
    # Each speed against the usual speed around it (16 frames, about a quarter of a second).
    near = [(v, v / max(0.01, median(vs[max(0, i - 8):i + 9]))) for i, v in enumerate(vs) if heard(middle[i][0])]
    assert len(near) > 60 and len(near) > 0.8 * len(middle), (len(near), len(middle))
    # Measured on this host (#480): v5 0.07-0.19, v4's carry-on and chase 0.26-0.55.
    ratio = [r for _, r in near]
    assert pstdev(ratio) < 0.2, (pstdev(ratio), shown)
    if steady:
        assert 0.45 < mean(v for v, _ in near) < 0.75, shown


def test_a_sliding_stone_glides_on_a_guest(site, browser):
    """The host runs the stones and sends them 20 times a second, unevenly late: a guest draws the slide smoothly."""
    host, aino = phones(site, browser)
    host.evaluate(JITTER)
    host.evaluate(STALLS)
    aino.evaluate(SAMPLE, STONE)
    host.evaluate("doThrow({ x: 0.4, w: 0.75, spin: 1 })")
    aino.wait_for_function("window.__xs.length >= 300", timeout=30000)
    glides(aino, stalls=host.evaluate("window.__stall"))
    # The rules keep the newest spot: between frames the guest's stone is where the host said last.
    at = aino.evaluate("""() => new Promise(ok => AiPelitRooms.on('message', m => {
      if (m.t === 's' && m.ph === 'slide') ok([m.st[0][1], m.st[0][2], stones[0].x, stones[0].y, stones[0].tr.time, m.ck]); }))""")
    assert abs(at[0] - at[2]) < 1e-6 and abs(at[1] - at[3]) < 1e-6, at
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


def test_a_friends_aim_glides_on_the_host(site, browser):
    """Aino drags the broom, sending it 10 times a second: the host's screen draws it gliding, while its rules (and
    the rows it sends on) keep the newest spot she sent."""
    host, aino = phones(site, browser)
    aino.evaluate(JITTER)
    host.evaluate("""() => { window.__rule = []; AiPelitRooms.on('message', m => {
      if (m.t === 'aim') window.__rule.push([m.x, aim.x, m.ck - aimTr.time]); }); }""")
    host.evaluate(SAMPLE, AIM)
    aino.evaluate(DRAG)
    host.wait_for_function("window.__xs.length >= 200", timeout=20000)
    aino.evaluate("drag.id = null")
    glides(host, steady=True)
    rule = host.evaluate("window.__rule")
    assert len(rule) > 15, rule
    assert all(abs(said - known) < 0.01 for said, known, _ in rule), rule  # the rules: the newest spot
    assert all(back > 0.03 for _, _, back in rule[5:]), rule  # drawn at least 30 ms back on her clock
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


def test_a_friends_aim_glides_on_a_third_phone_too(site, browser):
    """The host sends Aino's aim on with her own clock, unevenly late, so Ville's phone draws it as smoothly."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    host.evaluate(JITTER)
    aino.evaluate(JITTER)
    ville.evaluate(SAMPLE, AIM)
    aino.evaluate(DRAG)
    ville.wait_for_function("window.__xs.length >= 200", timeout=20000)
    aino.evaluate("drag.id = null")
    assert ville.evaluate("aimSrc") == "f"
    glides(ville, steady=True)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# On a guest: each time the host's rows change whose clock the aim carries (the computer took over the thrower),
# the aim that row brought, and where the next frame drew it.
SWITCH = """() => { window.__sw = []; let src = aimSrc, want = null; const d = window.draw;
  AiPelitRooms.on('message', m => { if (m.t === 's' && m.ph === 'aim' && aimSrc !== src) { src = aimSrc; want = [src, m.a[0]]; } });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, aimDrawn().x]); want = null; } }; }"""


def test_the_computer_taking_over_the_aim_is_drawn_where_the_host_says(site, browser):
    """Aino's phone drops while she aims: the host's computer aims for her, so the rows carry the host's clock and no
    longer hers. Ville's phone starts the track again there, drawing the row's aim from the next frame, not a guess
    from the other clock."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    aino.evaluate(DRAG)
    ville.wait_for_function("aimSrc === 'f' && aimTr.size() > 3", timeout=5000)
    ville.evaluate(SWITCH)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function("thrower() === 'cpu'")
    ville.wait_for_function("window.__sw.length >= 1", timeout=5000)
    sw = ville.evaluate("window.__sw")
    assert sw[0][0] == "h", sw
    assert all(abs(a - x) < 0.01 for _, a, x in sw), sw
    aino.evaluate("drag.id = null")
    errors = [e for p in (host, ville) for e in p.errors]
    assert not errors, errors


def test_a_phone_not_on_turn_let_go_and_back_leaves_the_aim_alone(site, browser):
    """Ville's phone drops while Aino aims, the host lets him go and he comes back: the host's aim stays on Aino's
    track and her clock, since neither change was hers (the first version of v5 reset it for any phone)."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    aino.evaluate(DRAG)
    host.wait_for_function("Number.isFinite(net.aimTs) && aimTr.size() > 3", timeout=5000)
    host.relay.drop(ville)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"net.away.includes({json.dumps(ville.evaluate('AiPelitRooms.me'))})")
    assert host.evaluate("[Number.isFinite(net.aimTs), aimTr.size() > 3, aimSrc]") == [True, True, "f"]
    host.relay.back(ville)
    host.wait_for_function("net.away.length === 0", timeout=20000)
    assert host.evaluate("[Number.isFinite(net.aimTs), aimTr.size() > 3, aimSrc, thrower()]") == [True, True, "f", aino.evaluate("AiPelitRooms.me")]
    aino.evaluate("drag.id = null")
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_resting_stones_keep_their_tracks_into_the_next_throw(site, browser):
    """A new throw starts the aim again, not the stones: a guest's stone lying still keeps the spots it heard (the
    first version of v5 started every stone's track again, which could jump one still gliding to rest)."""
    host, aino = phones(site, browser)
    host.evaluate("doThrow({ x: 0.2, w: 0.6, spin: 1 })")
    aino.wait_for_function("phase === 'slide' && stones[0] && stones[0].tr.size() >= 8", timeout=5000)
    # Stop the stone where it is, so the throw ends at once.
    host.evaluate("stones.forEach(s => { s.vx = 0; s.vy = 0; s.m = false; })")
    sizes = aino.evaluate("""() => new Promise(ok => { let before = stones[0].tr.size(), n = throwN;
      AiPelitRooms.on('message', m => { if (m.t === 's' && throwN !== n) ok([before, stones[0].tr.size()]); before = stones[0].tr.size(); }); })""")
    assert sizes[0] >= 8 and sizes[1] >= 8, sizes
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


def test_lifting_the_finger_sends_the_aim_where_it_left(site, browser):
    """The thrower's phone sends its aim 10 times a second while it drags, and once more as the finger lifts, so the
    host (and through it every phone) ends on the true spot."""
    host, aino = phones(site, browser)
    aino.evaluate("drag.id = 99; drag.ox = drag.cx = 180; drag.oy = drag.cy = 600")
    host.wait_for_function("Number.isFinite(net.aimTs)", timeout=5000)
    # The finger moves, and lifts before the next of the 10 a second goes (a pull under 18 px throws nothing).
    aino.evaluate("net.sendT = 100; aim.x = 0.77; aim.w = 0.4; up({ pointerId: 99 })")
    host.wait_for_function("Math.abs(aim.x - 0.77) < 0.01 && Math.abs(aim.w - 0.4) < 0.01", timeout=3000)
    assert host.evaluate("phase") == "aim"
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


# Fakes the room's pause (a phone away), which rooms.js sets: `window.__pz` on a phone is its AiPelitRooms.paused.
PAUSE = """() => { window.__pz = false;
  Object.defineProperty(AiPelitRooms, 'paused', { get: () => window.__pz, configurable: true }); }"""
# A clock that counts whole milliseconds, as Safari's and Firefox's do.
WHOLE_MS = """() => { const n = performance.now.bind(performance); AiPelitSulava.now = () => Math.floor(n()) / 1000; }"""
# The thrower's finger drags the broom across at 0.6 m a second of the match's own time (the steps it runs), so it
# stands while the match is paused, and the aim she sends after the pause goes on from where it stood.
DRAG_STEPS = """() => { drag.id = 99; aim.x = -1.5; const u = window.guestUpdate;
  window.guestUpdate = dt => { if (drag.id === 99) { aim.x += 0.6 * dt; aim.w = 0.5; aimShown = true; } u(dt); }; }"""


def pause_both(first, then, watcher):
    """The room pauses and goes on, each heard by the two phones a quarter of a second apart, `first` first both
    times (as when its link is the quicker). The watcher marks when its own pause starts and ends."""
    def stop(p):
        p.evaluate("window.__pzAt = performance.now() / 1000; window.__pz = true")

    def go(p):
        p.evaluate("window.__goAt = performance.now() / 1000; window.__pz = false")
    for n, step in enumerate((stop, go)):
        step(first)
        watcher.wait_for_timeout(250)
        step(then)
        watcher.wait_for_timeout(1200)
    return watcher.evaluate("[window.__xs, window.__pzAt, window.__goAt]")


def stands_then_goes_on(xs, pz_at, go_at, fast):
    """Drawn frames ([t, x, y, ...]) stand still through the watcher's pause, go on after it with no jump (never
    much faster than `fast`, m/s, more over a frame the test machine was late with), and do move on."""
    held = [(t, x, y) for t, x, y, *_ in xs if pz_at + 0.02 <= t <= go_at]
    assert len(held) >= 5 and held[-1][0] - held[0][0] >= 0.8, [round(t - pz_at, 3) for t, _, _ in held]
    spread = max(((x - held[0][1]) ** 2 + (y - held[0][2]) ** 2) ** 0.5 for _, x, y in held)
    assert spread < 0.005, spread
    after = [f for f in xs if f[0] > pz_at - 0.3]
    steps = [(((c - a) ** 2 + (d - b) ** 2) ** 0.5, t2 - t1, t2) for (t1, a, b, *_), (t2, c, d, *_) in zip(after, after[1:])]
    jumps = [(round(m, 3), round(dt, 3), round(t - go_at, 3)) for m, dt, t in steps if m > 0.02 and m > 1.5 * fast * dt]
    assert not jumps, jumps
    moved = [f for f in xs if f[0] > go_at + 0.6]
    assert moved and ((moved[-1][1] - held[-1][1]) ** 2 + (moved[-1][2] - held[-1][2]) ** 2) ** 0.5 > 0.1, moved[-1:]


BOTH = [pytest.param(ms, first, id=f"{first}-first-{'whole-ms' if ms else 'chromium'}-clock")
        for ms in (False, True) for first in ("watcher", "mover")]


@pytest.mark.parametrize("ms,first", BOTH)
def test_a_paused_room_holds_a_sliding_stone_where_a_guest_draws_it(site, browser, ms, first):
    """The host's stone slides; a phone is away, so the room pauses and the slide stands, and goes on. The guest's
    drawing stands with it: its track's clock stands while paused, so the stone is not guessed on past the host's
    last spot (0.25 s at most) and pulled back when the slide goes on. When the guest hears the pause first, the
    host's last spots come in its pause; when the host goes on first, its first spots after do: either way they
    wait, and go on the track as the guest goes on, with no jump. Also on a clock of whole milliseconds."""
    host, aino = phones(site, browser)
    for p in (host, aino):
        p.evaluate(PAUSE)
    if ms:
        for p in (host, aino):
            p.evaluate(WHOLE_MS)
    host.evaluate(JITTER)
    aino.evaluate(SAMPLE, STONE)
    host.evaluate("doThrow({ x: 0.4, w: 0.75, spin: 1 })")
    aino.wait_for_function("window.__xs.length >= 40", timeout=10000)
    xs = aino.evaluate("window.__xs")
    fast = max(((c - a) ** 2 + (d - b) ** 2) ** 0.5 / (t2 - t1) for (t1, a, b, _), (t2, c, d, _) in zip(xs[10:], xs[11:]) if t2 > t1)
    xs, pz_at, go_at = pause_both(*((aino, host) if first == "watcher" else (host, aino)), aino)
    assert host.evaluate("phase") == "slide"
    stands_then_goes_on(xs, pz_at, go_at, max(fast, 1))
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


@pytest.mark.parametrize("ms,first", BOTH)
def test_a_paused_room_holds_a_friends_aim_where_the_host_draws_it(site, browser, ms, first):
    """Aino drags the broom; the room pauses and goes on. The host's drawing of her aim stands through its pause
    and goes on from there. When the host hears the pause first, her last aims come in its pause; when she goes on
    first, her first ones after do: they wait, and go on the track as the host goes on."""
    host, aino = phones(site, browser)
    for p in (host, aino):
        p.evaluate(PAUSE)
    if ms:
        for p in (host, aino):
            p.evaluate(WHOLE_MS)
    aino.evaluate(JITTER)
    host.evaluate(SAMPLE, AIM)
    aino.evaluate(DRAG_STEPS)
    host.wait_for_function("window.__xs.length >= 40 && aimTr.size() > 5", timeout=10000)
    xs, pz_at, go_at = pause_both(*((host, aino) if first == "watcher" else (aino, host)), host)
    aino.evaluate("drag.id = null")
    stands_then_goes_on(xs, pz_at, go_at, 0.6)
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors
