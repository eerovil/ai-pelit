"""Kaahari v7 (#480): a friend's kart glides on the other phones' screens, drawn from lib/sulava-1 between the spots
their phone sends, instead of jumping to each one as it comes and carrying it on at its last speed until the next
(v6). A bump with a friend's kart is worked out where it is drawn (#480's D11); the places and the finish use the
newest spot."""

import json
import math
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaahari/v7/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own kart drives round the track at 150 px/s in lane `window.__lane` (px from the middle; its grid
# lane until set) while `window.__run` is on, and stands still when it is off: no slides, walls or pads. On the
# host, the computer's karts stand far away, out of everyone's way.
STRAIGHT = """() => { const dr = window.drive; window.__run = false; window.__s = me.s; window.__lane = me.lat;
  if (AiPelitRooms.isHost) race.karts.forEach((k, n) => { if (k.bot) Object.assign(k, { x: -5000 - 100 * n, y: -5000, v: 0 }); });
  window.drive = (k, dt, steer, d) => {
    if (k.bot) return;
    if (k !== me) return dr(k, dt, steer, d);
    const v = window.__run ? 150 : 0;
    window.__s += v * dt; k.prog += v * dt; k.v = v;
    // Between two of the track's samples (6 px apart), so the kart moves evenly and not in 6 px steps.
    const n = Math.floor(window.__s / T.step), f = window.__s / T.step - n;
    const p = at(T, n * T.step, window.__lane), q = at(T, (n + 1) * T.step, window.__lane);
    Object.assign(k, { x: p.x + (q.x - p.x) * f, y: p.y + (q.y - p.y) * f, a: p.a, idx: p.i, s: ((window.__s % T.L) + T.L) % T.L, lat: window.__lane, z: 0, vz: 0 });
  }; }"""
# Records, each time the screen is drawn, where kart `i` is drawn and which moment of the sending phone's clock
# that is (`tr.time`), when a message arrived, and the sending phone's stamp on each of its spots: so a stall of the
# test machine, on either phone, can be told from a jerk. `__bh`: [when, how far the drawn moment is behind the
# newest spot on the track, s].
SAMPLE = """(i) => { window.__xs = []; window.__got = []; window.__st = []; window.__bh = []; let top = null;
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const tr = race.karts[i].tr, push = tr.push, snap = tr.snap;
  tr.push = (st, ...r) => { window.__st.push(st); if (st !== null && !(st < top)) top = st; return push(st, ...r); };
  tr.snap = (st, ...r) => { window.__st.push(st); top = st; return snap(st, ...r); };
  const d = window.draw;
  window.draw = () => { const k = race.karts[i];
    if (window.__xs.length < (window.__cap || 300) && !window.__stop) { window.__xs.push([performance.now() / 1000, k.x, k.y, k.tr.time]);
      if (top !== null && k.tr.time !== null) window.__bh.push([performance.now() / 1000, top - k.tr.time]); } d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the race running."""
    site.build(ROOT / "games")
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
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=10000)
        p.evaluate(STRAIGHT)
    host.relay = relay
    return pages


def index(page):
    return page.evaluate("race.karts.indexOf(me)")


def glides(page):
    """The speed over each two drawn frames while the friend drove: always forward and about the same."""
    xs, got, st = page.evaluate("[window.__xs, window.__got, window.__st]")
    st = sorted(s for s in st if s is not None)
    sp = [(t2, math.hypot(c - a, d - b) / (t2 - t0), w0, w2)
          for (t0, a, b, w0), (t2, c, d, w2) in zip(xs, xs[2:]) if t2 > t0]
    moving = [t for t, v, _, _ in sp if v > 20]
    assert len(moving) > 60, len(moving)
    # Past the first half second (the glide picks up from standing) and before the last frames.
    middle = [(t, v, w0, w2) for t, v, w0, w2 in sp if moving[0] + 0.5 <= t <= moving[-1] - 0.2]
    assert len(middle) > 40, len(middle)

    def heard(t):
        """Spots came in steadily just before: the last one at most 0.15 s back, and less than 0.2 s after the one
        before it. A loaded test machine sometimes holds the messages back for longer than the track's longest
        delay (0.25 s), and nothing can glide through such a hole; a jerk with the spots coming in is the game's."""
        before = [g for g in got if g <= t]
        return len(before) > 1 and t - before[-1] < 0.15 and before[-1] - before[-2] < 0.2

    def sent(w):
        """The sending phone sent the spots on both sides of the drawn moment `w` (its own clock) less than 0.2 s
        apart. Its page stalls on a loaded machine too (verification job 709b18f4e4b8: no frame and no spot for
        0.84 s, and its kart, whose step per frame is capped, went 17 px in that time); the watcher then draws
        the kart as slowly as it went by the sender's clock, which is right."""
        if w is None:
            return False
        lo = [s for s in st if s <= w]
        hi = [s for s in st if s > w]
        return bool(lo) and bool(hi) and hi[0] - lo[-1] < 0.2

    kept = [v for t, v, w0, w2 in middle if heard(t) and sent(w0) and sent(w2)]
    shown = [round(v) for _, v, _, _ in middle]
    assert len(kept) > 30 and len(kept) > 0.5 * len(middle), (len(kept), len(middle))
    assert min(kept) > 30, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def run_and_watch(host, run, watch, others):
    me = index(run)
    run.evaluate("window.__lane = 0")  # the middle of the road, clear of the karts standing on the grid
    run.wait_for_timeout(500)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host and watch is not host:
        host.evaluate(SAMPLE, me)  # the host's drawn spots, for its check below
    if run is not host:
        # Between frames the host keeps the friend's newest spot (ahead of where it last drew them, as they drive
        # on), and each of their spots is drawn a moment back on their clock.
        host.evaluate("""(me) => { const k = race.karts[me]; window.__rule = []; window.__back = [];
          AiPelitRooms.on('message', (m, from) => { if (m.t === 'p' && from === k.id) window.__back.push(m.st - k.tr.time); });
          setInterval(() => { const l = window.__xs[window.__xs.length - 1];
            if (l && !window.__stop) window.__rule.push([(k.x - l[1]) * Math.cos(k.a) + (k.y - l[2]) * Math.sin(k.a),
              k.x === k.hd[0] && k.y === k.hd[1]]); }, 37); }""", me)
    s0 = run.evaluate("window.__s")
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__xs.length >= 200", timeout=20000)
    for p in {host, watch}:
        p.evaluate("window.__stop = true")  # only frames while the friend still drove
    run.evaluate("window.__run = false")
    assert run.evaluate("window.__s") > s0 + 200  # it really drove
    glides(watch)
    if run is not host:
        rule, back = host.evaluate("[window.__rule, window.__back]")
        assert len(rule) > 30, rule
        assert all(newest for _, newest in rule), rule  # between frames the kart is at the newest spot heard
        ahead = [a for a, _ in rule[5:]]
        assert mean(ahead) > 5 and sum(a > 0 for a in ahead) > 0.8 * len(ahead), ahead  # not the drawn one
        assert len(back) > 15 and all(b > 0.03 for b in back[5:]), (len(back), [round(b, 3) for b in back[5:] if b <= 0.03])  # drawn at least 30 ms back
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


# A guest drives, seen on the host (which keeps the newest spot between frames and draws it smoothly),
# and the host drives, seen on a guest.
@pytest.mark.parametrize("driver", ["guest", "host"])
def test_a_friend_driving_glides_on_the_other_phone(site, browser, driver):
    host, guest = phones(site, browser)
    run_and_watch(host, *((guest, host) if driver == "guest" else (host, guest)), others=[guest])


def test_a_friend_driving_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on as they came, with the friend's own clock, so a third phone draws them
    as smoothly (v6 sent its own guess of where they had got to)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(JITTER)
    run_and_watch(host, aino, ville, others=[aino, ville])


# On a phone: each time a message changes whose clock kart `i`'s spot carries (the computer took over a friend, or
# gave them back), or moves it more than 120 px, the spot it brought and where the next frame drew it (draw() runs
# with the drawn spot swapped in).
SWITCH = """(i) => { window.__sw = []; const k = race.karts[i]; let src = k.src, was = null, want = null; const d = window.draw;
  AiPelitRooms.on('message', (m, from) => { const a = m.t === 's' ? m.k[i] : m.t === 'p' && from === k.id ? m.k : null;
    if (!a) return;
    if (k.src !== src) { src = k.src; want = [src, a[0], a[1]]; }
    else if (was && Math.hypot(a[0] - was[0], a[1] - was[1]) > 120) want = ['jump', a[0], a[1]];
    was = a; });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, k.x, k.y]); want = null; } }; }"""
def placed(page, n):
    page.wait_for_function(f"window.__sw.length >= {n}", timeout=8000)
    sw = page.evaluate("window.__sw")
    return sw


def at_once(sw):
    """Each change drawn on the next frame at the spot the message brought, not glided to from before."""
    assert all(abs(x - a) < 0.5 and abs(y - b) < 0.5 for _, a, b, x, y in sw), sw


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-race: the host's computer drives their kart, so the rows carry the host's clock
    and no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at
    each change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = index(aino)
    aino.evaluate("window.__lane = 0; window.__run = true")
    ville.wait_for_function(f"race.karts[{me}].src === 'f'", timeout=5000)
    ville.evaluate(SWITCH, me)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"race.karts[{me}].kind === 'cpu'")
    ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
    aino.evaluate("window.__run = false")
    host.relay.back(aino)
    host.wait_for_function(f"race.karts[{me}].kind === 'net' && race.karts[{me}].hd", timeout=20000)
    ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
    sw = [s for s in placed(ville, 2) if s[0] != "jump"]
    assert [s[0] for s in sw][:2] == ["h", "f"], sw
    at_once(sw[:2])
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


@pytest.mark.parametrize("watcher", ["host", "third"])
def test_a_kart_moved_far_at_once_is_drawn_there_at_once(site, browser, watcher):
    """A move of more than 120 px between two spots (no kart drives that far in a message's gap) is a jump: the
    track draws the kart at its new spot on the next frame, not sliding across the track to it."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    watch = host if watcher == "host" else ville
    me = index(aino)
    aino.evaluate("window.__lane = 0")
    watch.wait_for_timeout(600)
    watch.evaluate(SWITCH, me)
    watch.wait_for_timeout(400)  # a few spots heard before the jump
    aino.evaluate("window.__s += 300; me.prog += 300")
    sw = placed(watch, 1)
    assert sw[0][0] == "jump", sw
    at_once(sw[:1])
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_bump_with_a_friend_happens_where_the_phone_draws_them(site, browser):
    """A friend drives past this phone's kart. The bump that pushes it is worked out from where this phone draws the
    friend (#480's D11), not from their newest spot, which is a moment further on: a bump where the player sees one."""
    host, aino = phones(site, browser)
    me = index(aino)
    aino.evaluate(JITTER)
    # The host's kart stands in the middle of the road 160 px up from Aino; she drives past it 10 px to its side.
    aino.evaluate("window.__lane = 10")
    host.evaluate(f"window.__s = race.karts[{me}].s + 160; window.__lane = 0")
    host.wait_for_timeout(600)
    # Each frame: where the friend is drawn, and where the bumps saw them on a frame that pushed this phone's kart.
    host.evaluate("""(i) => { window.__fr = 0; window.__drawn = {}; window.__hit = null; const d = window.draw, b = window.collide;
      window.draw = () => { const k = race.karts[i]; window.__drawn[window.__fr] = [k.x, k.y]; d(); window.__fr++; };
      window.collide = () => { const k = race.karts[i], at = [me.x, me.y, k.x, k.y]; b();
        if (window.__hit === null && (me.x !== at[0] || me.y !== at[1])) window.__hit = [window.__fr, at[2], at[3], k.hd[0], k.hd[1], at[0], at[1]]; }; }""", me)
    aino.evaluate("window.__run = true")
    host.wait_for_function("window.__hit !== null && window.__drawn[window.__hit[0]]", timeout=8000)
    aino.evaluate("window.__run = false")
    fr, bx, by, nx, ny, mx, my = host.evaluate("window.__hit")
    dx, dy = host.evaluate(f"window.__drawn[{fr}]")
    # The draw swaps the drawn spot in after the tick, a moment later on the clock: within a pixel.
    assert abs(bx - dx) < 1 and abs(by - dy) < 1, (bx, by, dx, dy)  # the bump saw what that frame drew
    assert math.hypot(dx - mx, dy - my) < 15  # drawn touching
    assert math.hypot(nx - bx, ny - by) > 0.5, (nx, ny, bx, by)  # and the newest spot was elsewhere
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors


# Fakes the room's pause (a phone away), which rooms.js sets: `window.__pz` on a phone is its AiPelitRooms.paused.
PAUSE = """() => { window.__pz = false;
  Object.defineProperty(AiPelitRooms, 'paused', { get: () => window.__pz, configurable: true }); }"""


def paused_race(site, browser, first, after):
    """The host drives; the room pauses and goes on, each heard by the two phones a quarter of a second apart, the
    driver (the host) or the watcher (the guest) first; the guest records `after` s past it."""
    host, guest = phones(site, browser)
    i = index(host)
    for p in (host, guest):
        p.evaluate(PAUSE)
    host.evaluate("window.__lane = 0")
    host.wait_for_timeout(500)
    host.evaluate(JITTER)
    guest.evaluate("window.__cap = 100000")
    guest.evaluate(SAMPLE, i)
    host.evaluate("window.__run = true")
    guest.wait_for_timeout(1200)
    stop_host = lambda: host.evaluate("window.__pz = true")
    stop_guest = lambda: guest.evaluate("window.__pzAt = performance.now() / 1000; window.__pz = true")
    go_host = lambda: host.evaluate("window.__pz = false")
    go_guest = lambda: guest.evaluate("window.__goAt = performance.now() / 1000; window.__pz = false")
    order = [(stop_host, stop_guest), (go_host, go_guest)] if first == "driver" else [(stop_guest, stop_host), (go_guest, go_host)]
    for n, (a, b) in enumerate(order):
        a()
        guest.wait_for_timeout(250)  # the other phone hears it a quarter of a second later
        b()
        guest.wait_for_timeout(1200 if n == 0 else int(after * 1000))
    guest.evaluate("window.__stop = true")
    host.evaluate("window.__run = false")
    errors = [e for p in (host, guest) for e in p.errors]
    assert not errors, errors
    return guest


@pytest.mark.parametrize("first", ["driver", "watcher"])
def test_a_paused_race_holds_the_friend_s_kart_where_it_is_drawn(site, browser, first):
    """While the room is paused the race stands and nothing is sent; the watching phone's tracks wait too, so the
    friend's kart driving on is not guessed on beyond its last spot and pulled back when the race goes on: it
    stands where it was drawn, and drives on from there. The two phones hear the pause a moment apart, in either
    order: a watcher that hears it first still gets the driver's last spots, sent before the driver stopped, and
    they go on its track only once the race goes on, not ahead of the drawn moment."""
    guest = paused_race(site, browser, first, 1.2)
    xs, pz_at, go_at = guest.evaluate("[window.__xs, window.__pzAt, window.__goAt]")
    held = [(t, x, y) for t, x, y, _ in xs if pz_at + 0.02 <= t <= go_at]
    # By time, not frames: a loaded test machine draws few (13 in a 1.25 s pause, in job fddb753a588e).
    assert len(held) >= 5 and held[-1][0] - held[0][0] >= 1, [round(t - pz_at, 3) for t, _, _ in held]
    held = [(x, y) for _, x, y in held]
    spread = max(math.hypot(x - held[0][0], y - held[0][1]) for x, y in held)
    assert spread < 0.01, spread  # it stood still all through the pause
    after = [f for f in xs if f[0] > pz_at - 0.3]
    # And went on with no jump, back or forward: 150 px/s is 2.5 px a frame, more over a frame the test machine
    # was late with, but never much faster than the kart goes.
    steps = [(math.hypot(c - a, d - b), t2 - t1) for (t1, a, b, _), (t2, c, d, _) in zip(after, after[1:])]
    jumps = [(round(m, 1), round(dt, 3)) for m, dt in steps if m > 8 and m > 300 * dt]
    assert not jumps, jumps
    moved = [f for f in xs if f[0] > go_at + 0.6]
    assert moved and math.hypot(moved[-1][1] - held[-1][0], moved[-1][2] - held[-1][1]) > 30, moved[-1:]


@pytest.mark.parametrize("first", ["driver", "watcher"])
def test_after_a_pause_the_friend_s_kart_is_drawn_as_far_behind_its_newest_spot_as_before(site, browser, first):
    """The watcher holds the driver's spots it hears while paused and puts them on the track when its own pause
    ends: the driver's last spots, sent before it heard the pause, when the watcher pauses first, and its first
    ones after the pause, when the driver goes on first. Its paused clock reads the same at both ends of the pause, so taken as heard
    then, the spots would seem to have come early: the track would lower its delay and for a second or two draw
    the kart ahead of the newest spot it knows (on a guess). Each held spot goes on as heard at its stamp plus the
    lag of the last spot heard before the pause, so the kart is drawn about as far behind as before."""
    guest = paused_race(site, browser, first, 2.2)
    bh, pz_at, go_at = guest.evaluate("[window.__bh, window.__pzAt, window.__goAt]")
    before = [b for t, b in bh if pz_at - 1.2 <= t <= pz_at - 0.3]
    after = [b for t, b in bh if go_at + 1 <= t <= go_at + 2]
    assert len(before) >= 5 and len(after) >= 5, (len(before), len(after))
    shown = (round(mean(before), 3), round(min(after), 3), round(mean(after), 3))
    assert mean(after) > mean(before) - 0.08, shown


def test_spots_held_in_a_pause_with_no_frame_drawn_go_on_the_track_when_it_ends(site, browser):
    """A phone whose page draws no frame (hidden) still hears the room. Spots it hears while paused wait, and the
    first spot heard after the pause puts them on the track, though no frame read the clock in between."""
    host, guest = phones(site, browser)
    i = index(host)
    guest.evaluate(PAUSE)
    host.evaluate("window.__lane = 0; window.__run = true")
    guest.wait_for_timeout(500)
    guest.evaluate("window.__frame = window.frame; window.frame = () => {}")  # no more frames
    guest.wait_for_timeout(200)
    guest.evaluate("window.__pz = true")
    guest.wait_for_function(f"race.karts[{i}].held && race.karts[{i}].held.length >= 3", timeout=5000)
    guest.evaluate("window.__pz = false")
    guest.wait_for_function(f"race.karts[{i}].held === null", timeout=2000)  # put on the track by the next spot
    guest.evaluate("window.frame = window.__frame; requestAnimationFrame(window.frame)")
    host.evaluate("window.__run = false")
    errors = [e for p in (host, guest) for e in p.errors]
    assert not errors, errors


# On the host: while `window.__stall` is on, its messages wait (a link that stalls), and `__flush()` sends the
# waiting ones at once. Records each frame where its own kart is, by the clock it stamps its spots with.
STALL = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms), q = [];
  window.__stall = false; window.__own = [];
  AiPelitRooms.send = (m, to) => { if (window.__stall) q.push([m, to]); else send(m, to); };
  window.__flush = () => { window.__stall = false; for (const [m, to] of q.splice(0)) send(m, to); };
  const d = window.draw;
  window.draw = () => { window.__own.push([netClock(), me.x, me.y]); d(); }; }"""


@pytest.mark.parametrize("ms", [False, True], ids=["chromium-clock", "whole-ms-clock"])
def test_after_a_stall_then_a_pause_the_friend_s_kart_eases_to_its_spots(site, browser, ms):
    """The host's spots stall for 0.7 s, so the guest draws the host's kart on a guess past its newest spot and then
    stops (0.25 s at most): by the guess it falls behind where the kart really was. Then the guest pauses, and the
    stalled spots land in the pause and are held. When the pause ends they go on the track, and the drawing eases
    to them by the time gone (the track's 0.1 s easing), never the whole gap in one frame. Also on a clock that
    counts whole milliseconds (Safari's and Firefox's): the first read after a pause gives the paused moment
    again, and a track read at the same moment as the frame before does not ease a correction in."""
    host, guest = phones(site, browser)
    i = index(host)
    if ms:
        guest.evaluate("""() => { const n = performance.now.bind(performance);
          AiPelitSulava.now = () => Math.floor(n()) / 1000; }""")
    guest.evaluate(PAUSE)
    host.evaluate("window.__lane = 0")
    host.evaluate(STALL)
    guest.evaluate("window.__cap = 100000")
    guest.evaluate(SAMPLE, i)
    host.evaluate("window.__run = true")
    guest.wait_for_timeout(1200)
    host.evaluate("window.__stall = true")
    guest.wait_for_timeout(700)
    guest.evaluate("window.__pzAt = performance.now() / 1000; window.__pz = true")
    host.evaluate("window.__flush()")
    guest.wait_for_timeout(500)
    guest.evaluate("window.__goAt = performance.now() / 1000; window.__pz = false")
    guest.wait_for_timeout(700)
    guest.evaluate("window.__stop = true")
    host.evaluate("window.__run = false")
    xs, pz_at, go_at = guest.evaluate("[window.__xs, window.__pzAt, window.__goAt]")
    own = host.evaluate("window.__own")
    paused = [f for f in xs if pz_at + 0.02 <= f[0] <= go_at]
    assert len(paused) >= 3, len(paused)
    t1, hx, hy, moment = paused[-1]
    # Where the host's kart really was at the moment the paused frames drew: the gap the guess left.
    real = min(own, key=lambda o: abs(o[0] - moment))
    gap = math.hypot(real[1] - hx, real[2] - hy)
    assert gap > 20, (gap, moment, real)
    after = [(t, x, y) for t, x, y, _ in xs if t > go_at][:8]
    assert len(after) >= 4, len(after)
    over = [(round(t - t1, 3), round(math.hypot(x - hx, y - hy), 1)) for t, x, y in after
            if math.hypot(x - hx, y - hy) > gap * (1 - math.exp(-(t - t1) / 0.1)) + 1.2 * 150 * (t - t1) + 2]
    assert not over, (over, round(gap, 1))
    errors = [e for p in (host, guest) for e in p.errors]
    assert not errors, errors
