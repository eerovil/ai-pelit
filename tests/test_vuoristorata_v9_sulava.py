"""Vuoristorata v7-v8 (#480): a friend's train glides along the track on the other phones' screens, drawn from
lib/sulava-1 between the spots their phone sends, instead of being carried on at its last speed between messages
(v6). The places and the end use the newest spot heard; only the drawing lags."""

import math
import time
from statistics import mean, pstdev

import pytest

from test_vuoristorata_v8 import room_of

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own train goes on at 12 m/s while `window.__run` is on, and stands still while it is off.
STRAIGHT = """() => { window.__run = false;
  window.rideStep = (t, car, h) => { car.v = window.__run ? 12 : 0; car.s += car.v * h; car.t += h; return null; }; }"""
# Records, each time the screen draws car `i`, where along the track it is drawn, and when a message arrived (so a
# stall of the test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__ss = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.drawnS;
  window.drawnS = k => { const s = d(k); if (k === net.cars[i] && window.__ss.length < 300) window.__ss.push([performance.now() / 1000, s]); return s; }; }"""


def phones(site, browser, names=("Eero", "Aino")):
    """Phones in a room, the race running, every train standing still at 40 m."""
    relay, host, guests, ctxs = room_of(site, browser, list(names))
    host.click("#aipr-start")
    pages = [host, *guests]
    for p in pages:
        p.wait_for_function("net && net.cfg && game.mode === 'ride'", timeout=15000)
        p.evaluate(STRAIGHT)
        p.evaluate("game.car.s = 40; game.car.check = 40")
    host.relay = relay
    host.ctxs = ctxs
    return pages


def index(page):
    return page.evaluate("net.cars.findIndex(k => k.kind === 'me')")


def glides(page):
    """The speed over each two drawn frames while the friend rode: always forward and about the same."""
    ss, got = page.evaluate("[window.__ss, window.__got]")
    sp = [(t2, (b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(ss, ss[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.5]
    assert len(moving) > 60, len(moving)
    t0, t1 = sp[moving[0]][0] + 0.3, sp[moving[-1]][0] - 0.3  # the start and the stop take a moment to glide
    middle = [(t, v) for t, v in sp if t0 <= t <= t1]
    assert len(middle) > 40, len(middle)

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 3, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def ride_and_watch(host, run, watch, others):
    me = index(run)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host and watch is not host:
        host.evaluate(SAMPLE, me)  # the host's drawn spots, for its check below
    if run is not host:
        # Between frames the host keeps the friend's newest spot (ahead of where it last drew them, as they ride on).
        host.evaluate("""(me) => { const k = net.cars[me]; window.__rule = [];
          setInterval(() => { if (window.__ss.length) window.__rule.push([k.s, window.__ss[window.__ss.length - 1][1]]); }, 37); }""", me)
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__ss.length >= 200", timeout=30000)
    run.evaluate("window.__run = false")
    assert run.evaluate("game.car.s") > 60  # it really rode
    glides(watch)
    if run is not host:
        rule = host.evaluate("window.__rule")
        ahead = [kept - drawn for kept, drawn in rule if 42 < drawn and kept < 70]
        assert len(ahead) > 30, rule
        # The newest spot, not the drawn one (a late message can leave the drawing running on a moment past it).
        assert sum(a > 0 for a in ahead) > 0.75 * len(ahead) and mean(ahead) > 0.3, ahead
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


def close(host):
    for c in host.ctxs:
        c.close()


def test_a_friend_riding_glides_on_the_host(site, browser):
    host, guest = phones(site, browser)
    try:
        ride_and_watch(host, guest, host, others=[guest])
    finally:
        close(host)


def test_the_host_riding_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    try:
        ride_and_watch(host, host, guest, others=[guest])
    finally:
        close(host)


def test_a_friend_riding_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on as they came, with the friend's own clock, so a third phone draws them
    as smoothly (v6 sent where its own guess had carried them)."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    try:
        host.evaluate(JITTER)
        ride_and_watch(host, aino, ville, others=[aino, ville])
    finally:
        close(host)


# On a phone: each time a message changes whose clock car `i`'s spot carries (the computer took over a friend, or
# gave them back), the spot it brought and where the next frame drew them.
SWITCH = """(i) => { window.__sw = []; const k = net.cars[i]; let src = k.src, want = null; const d = window.drawnS;
  AiPelitRooms.on('message', m => { if (m.t !== 's' || k.src === src) return; src = k.src; want = [src, m.c[i][0]]; });
  window.drawnS = o => { const s = d(o); if (o === k && want) { window.__sw.push([...want, s]); want = null; } return s; }; }"""


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-race: the host's computer rides for them, so their row carries the host's clock and
    no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at each
    change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    try:
        me = index(aino)
        aino.evaluate("window.__run = true")
        ville.wait_for_function(f"net.cars[{me}].src === 'f' && net.cars[{me}].s > 44", timeout=5000)
        ville.evaluate(SWITCH, me)
        host.relay.drop(aino)
        host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
        host.click("#aipr-goOn")
        host.wait_for_function(f"net.cars[{me}].kind === 'cpu'")
        ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
        host.relay.back(aino)
        host.wait_for_function(f"net.cars[{me}].kind === 'net' && !net.cars[{me}].handback && net.cars[{me}].ts !== null",
                               timeout=20000)
        ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
        sw = ville.evaluate("window.__sw")
        assert [s[0] for s in sw][:2] == ["h", "f"], sw
        assert all(abs(drawn - said) < 0.01 for _, said, drawn in sw), sw
        errors = [e for p in (host, aino, ville) for e in p.errors]
        assert not errors, errors
    finally:
        close(host)


def test_a_train_put_back_after_a_derail_is_drawn_there_at_once(site, browser):
    """A friend's train flies off and is put back before the place it flew off: the other phone draws it there from
    the first spot after, instead of gliding it backwards down the track."""
    host, guest = phones(site, browser)
    try:
        me = index(guest)
        guest.evaluate("window.__run = true")
        host.wait_for_function(f"net.cars[{me}].s > 70", timeout=10000)
        guest.evaluate("window.__run = false")
        host.evaluate("""(i) => { window.__back = null; const k = net.cars[i]; const d = window.drawnS; let was = false;
          window.drawnS = o => { const s = d(o); if (o === k) { if (was && !k.crash && window.__back === null) window.__back = [k.s, s];
            was = was || !!k.crash; } return s; }; }""", me)
        # Put back 8 m: closer than the track's jump (30 m), so only the derail tells it to start again there.
        off = guest.evaluate("game.car.check = game.car.s - 8; crash('air'); game.car.check")
        host.wait_for_function("window.__back !== null", timeout=10000)
        said, drawn = host.evaluate("window.__back")
        assert abs(said - off) < 0.5 and abs(drawn - said) < 0.01, (off, said, drawn)
        assert not host.errors + guest.errors
    finally:
        close(host)


def test_a_long_frame_on_the_sending_phone_stamps_each_spot_with_its_own_moment(site, browser):
    """A slow phone's long frame is ridden in 50 ms steps, and a spot may be sent in any of them. Each one carries the
    moment of its own step, not the frame's: one stamp for several spots made the other phones draw the train behind
    its stamp, then rush it on (seen on a loaded test machine as a jerk forward and an ease back)."""
    host, guest = phones(site, browser)
    try:
        guest.evaluate("""() => { window.__sent = []; const send = AiPelitRooms.send.bind(AiPelitRooms);
          AiPelitRooms.send = (m, to) => { if (m.t === 'p') window.__sent.push([m.st, m.c[0]]); return send(m, to); }; }""")
        guest.evaluate("window.__run = true")
        guest.wait_for_function("window.__sent.length >= 3", timeout=5000)
        # Judge only spots sent while the train runs: a pair across the start or the stop moved for part of its gap.
        guest.evaluate("window.__sent.length = 0")
        # Hold the page busy for 0.4 s, as a slow phone does; its next frame rides those 0.4 s in steps.
        guest.evaluate("""() => new Promise(ok => requestAnimationFrame(() => {
          const until = performance.now() + 400; while (performance.now() < until) {} ok(); }))""")
        guest.wait_for_function("window.__sent.length >= 9", timeout=5000)
        sent = guest.evaluate("window.__sent.slice()")
        guest.evaluate("window.__run = false")
        sp = [(s2 - s1) / (t2 - t1) for (t1, s1), (t2, s2) in zip(sent, sent[1:]) if s2 > s1]
        assert all(t2 > t1 for (t1, _), (t2, _) in zip(sent, sent[1:])), sent
        assert sp and all(9 < v < 15 for v in sp), (sp, sent)
    finally:
        close(host)


def test_a_friend_past_the_line_brakes_to_a_stop_on_every_screen(site, browser):
    """Past the finish line the friend's train still moves while it brakes, and their phone still sends where it is.
    The host kept their finish time and place but dropped those spots too, so the host and a third phone drew the
    train stopped at its last spot before the line (or guessed on past it)."""
    host, aino, ville = phones(site, browser, names=("Eero", "Aino", "Ville"))
    try:
        i = index(aino)
        aino.evaluate("game.car.fin = game.car.t = 5; game.mode = 'done'; meK().fin = 5; window.__run = true")
        host.wait_for_function(f"net.cars[{i}].fin !== null", timeout=10000)
        at_fin = host.evaluate(f"net.cars[{i}].s")
        aino.wait_for_timeout(1000)
        aino.evaluate("window.__run = false")
        end = aino.evaluate("game.car.s")
        assert end > at_fin + 5  # it really rode on past the line
        for p in (host, ville):
            p.wait_for_function(f"Math.abs(drawnS(net.cars[{i}]) - {end}) < 0.5", timeout=5000)
        # The finish heard first stands.
        assert host.evaluate(f"net.cars[{i}].fin") == 5
        errors = [e for p in (host, aino, ville) for e in p.errors]
        assert not errors, errors
    finally:
        close(host)


# The room's pause on one phone by hand, from `on` to `off` (ms on the machine's clock, which every page shares), to
# set which phone hears it first; a pause on a busy test machine cannot wait for a message to reach a page.
PAUSE = """([on, off]) => Object.defineProperty(AiPelitRooms, 'paused',
  { get: () => Date.now() >= on && Date.now() < off, configurable: true })"""
# Each frame, where car `i` is drawn and whether this phone is paused.
DRAWN = """(i) => { window.__dr = []; const d = window.drawnS;
  window.drawnS = k => { const s = d(k); if (k === net.cars[i])
    window.__dr.push([performance.now() / 1000, s, AiPelitRooms.paused]); return s; }; }"""


@pytest.mark.parametrize("first", ["host", "guest"])
def test_a_pause_holds_a_friend_s_train_where_it_is_drawn_and_it_rides_on_from_there(site, browser, first):
    """A phone in the race goes away: the race stands still on every phone (step()), so the friend's train is drawn
    standing where it was, not guessed on along the track (to be pulled back once the race goes on). The phones hear
    a pause a moment apart, so each order is paused by hand a quarter of a second apart: a phone that pauses first
    still hears the other's last spots, and they go on its track only once its own pause ends."""
    host, guest = phones(site, browser)
    try:
        i = index(guest)
        guest.evaluate("window.__run = true")
        host.wait_for_function(f"net.cars[{i}].s > 46", timeout=10000)
        host.evaluate(DRAWN, i)
        host.wait_for_timeout(500)
        at = time.time() * 1000 + 300
        for p, d in ((host, 0), (guest, 250)) if first == "host" else ((guest, 0), (host, 250)):
            p.evaluate(PAUSE, [at + d, at + d + 1450])  # both 1.45 s, a quarter of a second apart
        host.wait_for_timeout(300 + 1700 + 1500)
        guest.evaluate("window.__run = false")
        dr = host.evaluate("window.__dr")
        paused = [(t, s) for t, s, p in dr if p]
        assert len(paused) > 4 and paused[-1][0] - paused[0][0] > 0.8, dr  # by time: a loaded machine draws few frames
        # From 0.3 s into this phone's pause (the other's spots sent before its own pause have been drawn by then),
        # the train stands where it was drawn.
        held = [s for t, s in paused if t > paused[0][0] + 0.3]
        assert held and max(held) - min(held) < 0.05, [round(s, 2) for _, s in paused]
        assert dr[-1][1] > held[-1] + 5, dr[-1]  # and it rode on after the pause
        # Never drawn going back along the track, before, in or after the pause.
        drawn = [round(s, 2) for _, s, _ in dr]
        assert all(b >= a - 0.05 for a, b in zip(drawn, drawn[1:])), drawn
        assert not host.errors + guest.errors
    finally:
        close(host)


# On the guest, with the host sending nothing and the room's pause by hand (`window.__pz`): the host's train fed by
# hand, riding at V m/s by the tracks' clock, a spot each 1/30 s (stamps on a clock 100 s from the guest's). After
# 0.6 s the link stalls for 1 s (the spots go on being made and wait), then the guest pauses and the waiting ones
# land; 0.5 s on the pause ends and the spots come on as before for 0.5 s. Records each frame [moment, s drawn,
# paused, s at the moment drawn].
STALL = """([i, V]) => new Promise(done => {
  window.__pz = false;
  Object.defineProperty(AiPelitRooms, 'paused', { get: () => window.__pz, configurable: true });
  const k = net.cars[i], s0 = k.s, t0 = netClock(), off = 100, q = [];
  k.tr.reset();   // a clock of its own from here
  const hear = (c, s) => { k.s = s; heardSpot(k, c + off, k.src || 'h', false); };
  window.__st = []; const d = window.drawnS;
  window.drawnS = c => { const s = d(c); if (c === k) window.__st.push([performance.now() / 1000, s, window.__pz,
    k.tr.time === null ? null : s0 + V * (k.tr.time - off - t0)]); return s; };
  let phase = 'on';
  const tick = setInterval(() => { const c = netClock(), s = s0 + V * (c - t0);
    if (phase === 'on') hear(c, s); else if (phase === 'stall') q.push([c, s]); }, 1000 / 30);
  setTimeout(() => { phase = 'stall'; }, 600);
  setTimeout(() => { phase = 'pause'; window.__pz = true; for (const [c, s] of q.splice(0)) hear(c, s); }, 1600);
  setTimeout(() => { window.__pz = false; phase = 'on'; }, 2100);
  setTimeout(() => { clearInterval(tick); done(); }, 2600); })"""


@pytest.mark.parametrize("ms", [False, True], ids=["chromium-clock", "whole-ms-clock"])
def test_spots_landing_in_a_pause_after_a_stall_are_eased_in_after_it(site, browser, ms):
    """v8: a stall, then the guest pauses and the stalled spots land in the pause. The train drawn holds still all
    through the pause, and once it is over the drawing eases to the spots, not the whole way in one frame. Also on
    a clock that counts whole milliseconds (Safari's, Firefox's), where the first frame after the pause read the
    paused moment again in v7: the track eases a correction only when its clock has moved on since the last frame,
    so the train hopped there."""
    host, guest = phones(site, browser)
    try:
        i = index(host)
        if ms:
            guest.evaluate("""() => { const n = performance.now.bind(performance);
              AiPelitSulava.now = () => Math.floor(n()) / 1000; }""")
        host.evaluate("() => { AiPelitRooms.send = () => {}; }")  # the host's own spots no longer reach the guest
        guest.wait_for_timeout(300)
        V = 20
        guest.evaluate(STALL, [i, V])
        st = guest.evaluate("window.__st")
        first = next(n for n, e in enumerate(st) if e[2])
        held = [st[first - 1][1]] + [s for _, s, p, *_ in st[first:] if p]
        assert len(held) > 3, len(held)
        assert max(held) - min(held) < 0.01, [round(s, 2) for s in held]
        last = max(n for n, e in enumerate(st) if e[2])
        after = [(t, s) for t, s, p, *_ in st[last + 1:]]
        # By the pause the drawing had stood a while (the stall outran its 0.25 s guess) well short of the spot for its
        # moment; after it, it eases there by the time gone (the track's easing, 0.1 s), and the drawn moment goes on
        # at most 1.2 times the clock: never the whole way in one frame, however long the frame.
        gap = st[first][3] - held[-1]
        assert gap > 5, gap
        t1 = st[last][0]
        over = [(round(t - t1, 3), round(s - held[-1], 2)) for t, s in after[:6]
                if s - held[-1] > gap * (1 - math.exp(-(t - t1) / 0.1)) + 1.2 * V * (t - t1) + 0.3]
        assert not over, (over, round(gap, 2))
        (ta, sa), (tb, sb) = after[-2], after[-1]
        assert abs(sb - sa) / (tb - ta) < 1.5 * V, after[-5:]  # and by the end it runs on at the spots' speed
        assert not host.errors + guest.errors
    finally:
        close(host)
