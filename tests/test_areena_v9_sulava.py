"""Areena v9 (#480): on a friend's phone the other fighters glide across the arena, drawn from lib/sulava-1
between the spots the host sends, instead of chasing each newest spot (v8). The host runs the whole fight from
every phone's stick, so it draws everyone where its own fight has them, and nothing about it changes; a guest's
own fighter still chases its newest spot, with no extra delay. Between frames every fighter stands at the newest
spot heard; only the drawing lags."""

import json
import math
import shutil
from statistics import mean, pstdev

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/areena/v9/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# On the host: while `window.__run` is on, fighter `i` moves along the arena's middle (x 170, clear of the
# pillars) at 62 units/s by the wall clock towards `dir` (-1 up, 1 down), until 120 units short of the far
# end, where the other fighter stands. By the clock and not by the host's frames, so a busy test machine
# that drops the host's frames does not make the move itself uneven: what is measured is the guest's drawing.
# The spot is set before the host's own step, which sends it, so each spot goes with the stamp of its own
# moment (set after it, a message would carry the frame before's spot with this frame's stamp: on a busy
# machine, where the host's frames come 10-100 ms apart, the spots then read 15-190 units/s, not 62).
RUN = """([i, dir]) => { window.__run = false; let t0 = null, y0 = 0; const s = window.step;
  window.step = dt => { const f = fighters[i];
    if (!window.__run) t0 = null;
    else {
      const now = AiPelitSulava.now(); if (t0 === null) { t0 = now; y0 = f.y; }
      const y = y0 + dir * 62 * (now - t0); f.y = dir < 0 ? Math.max(130, y) : Math.min(310, y);
    }
    s(dt); }; }"""
# Records, each frame, where fighter `i` is drawn along the arena and the moment its track was asked
# (asDrawn(), right before the drawing), and whether the moment drawn was within the track's 0.05 s guess past
# the newest spot the phone had heard by then. Past that, a stall of the test machine or its relay (no spot
# heard for a while) holds the drawing on the newest spot, by design, and is not a jerk; within it, a fighter
# standing still is one (as when a spot heard but held back was not put on the track in time).
SAMPLE = """(i) => { window.__ys = []; let heard = -Infinity; const tr = fighters[i].tr;
  AiPelitRooms.on('message', m => { if (m.t === 's' && m.ck > heard) heard = m.ck; });
  const a = window.asDrawn;
  window.asDrawn = () => { const t = performance.now() / 1000, kept = a();
    if (window.__ys.length < 300) window.__ys.push([t, fighters[i].y, tr.time <= heard + 0.05]); return kept; }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the fight on."""
    shutil.copytree(ROOT / "games" / "areena", site.games / "areena")
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
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function(f"state === 'fight' && fighters.length === {len(pages)}", timeout=10000)
    host.relay = relay
    return pages


def index(page):
    return page.evaluate("fighters.indexOf(me)")


def glides(page):
    """The speed over each two drawn frames while the fighter ran: about the same all the way."""
    ys = page.evaluate("window.__ys")
    # Only frames that came in time on the watching page itself (both gaps under 40 ms, a 60 Hz frame is 17):
    # a frame late on a busy test machine and the quick one after it measure the machine, not the drawing.
    sp = [(t2, abs(b - a) / (t2 - t0), fa and fb) for (t0, a, fa), (t1, _, _), (t2, b, fb) in zip(ys, ys[1:], ys[2:])
          if t2 > t0 and t1 - t0 < 0.04 and t2 - t1 < 0.04]
    moving = [i for i, (_, v, _) in enumerate(sp) if v > 10]
    assert len(moving) > 50, len(moving)
    # Leave out the start and the stop: the drawing speeds up and slows down there over a moment.
    t0, t1 = sp[moving[0]][0] + 0.15, sp[moving[-1]][0] - 0.3
    middle = [(t, v, fed) for t, v, fed in sp if t0 <= t <= t1]
    assert len(middle) > 30, len(middle)
    # Only frames drawn within the guess past the newest spot heard: the drawing's own glide, not a gap in the
    # messages.
    kept = [v for _, v, fed in middle if fed]
    # Every frame pair whole in a failure's message (a string, which pytest does not shorten): [moment, speed,
    # within the guess].
    shown = json.dumps([[round(t, 3), round(v, 1), fed] for t, v, fed in middle])
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 20, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, f"sd {sd}, mean {m}, frames {shown}"
    assert max(kept) < 2 * m, f"max {max(kept)}, mean {m}, frames {shown}"


def run_and_watch(host, run, watch, others):
    """`run`'s fighter moves along the arena in the host's fight while `watch` draws it; the host's messages
    are jittered."""
    me = index(run)
    host.evaluate(RUN, [me, 1 if run.evaluate("me.y < AH / 2") else -1])
    host.evaluate(JITTER)
    watch.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    watch.evaluate(SAMPLE, me)
    # Between frames the watching phone keeps the newest spot the host sent (ahead of the drawn one, as the
    # fighter runs on): `window.__rule` pairs it with the newest spot heard and the last one drawn.
    watch.evaluate("""(i) => { const f = fighters[i]; let said = null; window.__rule = [];
      AiPelitRooms.on('message', m => { if (m.t === 's') said = m.f[i][1]; });
      setInterval(() => { if (said !== null && window.__ys.length)
        window.__rule.push([f.y, said, window.__ys[window.__ys.length - 1][1]]); }, 37); }""", me)
    host.evaluate("window.__run = true")
    watch.wait_for_function("window.__ys.length >= 200", timeout=30000)
    glides(watch)
    rule = watch.evaluate("window.__rule")
    assert len(rule) > 30, rule
    assert all(abs(kept - said) < 0.01 for kept, said, _ in rule), rule
    ahead = [abs(kept - drawn) for kept, _, drawn in rule]
    assert sum(a > 0.5 for a in ahead) > 0.5 * len(ahead) and mean(ahead) > 1, ahead
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


def test_the_host_running_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    run_and_watch(host, host, guest, others=[guest])
    # The guest's own fighter is never drawn back: it has no track, and follows the host's newest spot.
    assert guest.evaluate("me.tr.size()") == 0


def test_a_friend_running_glides_on_a_third_phone(site, browser):
    """A friend's fighter moving in the host's fight: a third phone draws it as smoothly."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    run_and_watch(host, aino, ville, others=[aino, ville])


def test_a_jump_is_drawn_at_once_not_glided(site, browser):
    """The host moves a fighter 230 units in one frame, faster than anything in a round moves one (a jump is
    over 40 units plus 840 units/s for the time between the stamps): from the first frame after the state
    that says so, the guest draws it where it landed, not sliding across the arena towards it."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    guest.evaluate("""(i) => { window.__jump = []; const f = fighters[i]; let want = null; const d = window.draw;
      AiPelitRooms.on('message', m => { if (m.t === 's' && want === null && m.f[i][1] < 200) want = m.f[i][1]; });
      window.draw = () => { d(); if (want !== null && window.__jump.length < 5) window.__jump.push([want, f.y]); }; }""", me)
    host.evaluate("me.y = 150")
    guest.wait_for_function("window.__jump.length >= 5", timeout=5000)
    jump = guest.evaluate("window.__jump")
    # Every frame from the first after the jump draws it where it landed.
    assert all(abs(drawn - want) < 0.5 for want, drawn in jump), jump
    assert not host.errors + guest.errors


# On the host: a fighter's dodge by hand, up the arena's middle (420 units/s for 0.2 s, as act() moves one).
DODGE = """(i) => { const f = fighters[i]; f.dx = 0; f.dy = -1; f.dash = 0.2; f.dashCd = 1.1; }"""
# On the host: while `window.__drop` is on, its messages are not sent.
DROP = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); window.__drop = false;
  AiPelitRooms.send = (m, to) => { if (!window.__drop) send(m, to); }; }"""
# The room's pause by hand: `AiPelitRooms.paused` reads `window.__pz` (as while a phone is away).
PAUSE = """() => { window.__pz = false;
  Object.defineProperty(AiPelitRooms, 'paused', { get: () => window.__pz, configurable: true }); }"""
# Every drawn frame of fighter `i` on the watching phone: [moment, x, y].
DRAWN = """(i) => { window.__drawn = []; const a = window.asDrawn;
  window.asDrawn = () => { const kept = a();
    window.__drawn.push([performance.now() / 1000, fighters[i].x, fighters[i].y]); return kept; }; }"""


# On the guest, with the host's own messages dropped: the host's states fed to the game by hand, stamped
# every 1/30 s as a host at its full rate stamps them (on from the last real one, with the real link's lag),
# and let through in bursts, all waiting ones in order every 250 ms (as a mobile link that batches its
# packets does). Records, each frame for 3 s, [moment drawn, stamp of the oldest of the 8 spots on the track,
# delay].
LAGGY = """(i) => new Promise(done => {
  const base = JSON.parse(JSON.stringify(window.__last)), tr = fighters[i].tr, on = [], q = [], p = tr.push;
  tr.push = (t, v, a) => { if (!on.length || t > on[on.length - 1]) on.push(t); return p(t, v, a); };
  window.__at = []; const d = window.asDrawn;
  window.asDrawn = () => { const k = d();
    if (on.length >= 10) window.__at.push([tr.time, on[on.length - 8], tr.delay]); return k; };
  const send = setInterval(() => { const m = JSON.parse(JSON.stringify(base));
    m.ck = base.ck + fightClock() - window.__lastAt; q.push(m); }, 1000 / 30);
  const burst = setInterval(() => { for (const m of q.splice(0)) onMessage(m); }, 250);
  setTimeout(() => { clearInterval(send); clearInterval(burst); done(); }, 3000); })"""


def test_on_a_laggy_link_the_drawn_moment_stays_within_the_tracks_spots(site, browser):
    """A track keeps 8 spots. A host sends up to 30 states a second, and 8 of them span under a quarter
    second, less than the longest the drawing may wait (0.25 s): on a laggy link the drawn moment would fall
    before the oldest spot, and the fighter would stand on it. A spot goes on the track only 0.06 s or more
    after the one before it (or when the drawing comes near the newest one), so with states 1/30 s apart
    arriving in bursts every 250 ms, the drawn moment stays within the spots kept. The messages are as
    before."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.evaluate("""() => { AiPelitRooms.on('message', m => { if (m.t === 's') { window.__last = m; window.__lastAt = fightClock(); } }); }""")
    guest.wait_for_function(f"window.__last && fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate(DROP)
    host.evaluate("window.__drop = true")
    guest.evaluate(LAGGY, me)
    at = guest.evaluate("window.__at")
    # Enough frames to judge, also on a machine so busy it draws 15 a second.
    assert len(at) > 20, len(at)
    # The link is laggy enough that the drawing waits about as long as it may.
    assert max(d for _, _, d in at) > 0.2, [round(d, 3) for _, _, d in at]
    before = [round(oldest - t, 3) for t, oldest, _ in at if t < oldest]
    assert not before, before
    assert not host.errors + guest.errors


def test_a_dodge_on_a_stalled_link_is_drawn_only_a_little_past_its_end(site, browser):
    """The host's fighter dodges, and the host's messages stop as the dodge ends: the guest goes on at the
    last speed it saw (420 units/s) for only 0.05 s, so it draws the fighter at most about 21 units past where
    it stopped (with the library's 0.25 s, up to about 100)."""
    host, guest = phones(site, browser)
    me = index(host)
    host.evaluate(DROP)
    guest.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    guest.evaluate(DRAWN, me)
    host.evaluate(DODGE, me)
    host.wait_for_function(f"fighters[{me}].dash <= 0", polling="raf", timeout=5000)
    host.evaluate("window.__drop = true")
    stop = host.evaluate(f"fighters[{me}].y")
    guest.wait_for_timeout(600)
    ys = [y for _, _, y in guest.evaluate("window.__drawn")]
    # It dodged: drawn going up the arena by most of the dodge's 84 units.
    assert ys[0] - min(ys) > 50, ys
    past = stop - min(ys)
    # Every frame whole in a failure's message (a string, which pytest does not shorten): [moment, x, y].
    assert past < 25, f"past {past}, stop {stop}, frames " + json.dumps(guest.evaluate("window.__drawn"))
    assert not host.errors + guest.errors


def test_a_paused_room_holds_the_drawn_fighters_and_goes_on_from_there(site, browser):
    """The host pauses first. While the room waits for a phone that is away, a guest draws the other fighters
    where they were when it paused, not going on at their last speed past the newest spot; when the room goes
    on, they move on from there at about its speed, with no jump over the pause (1.5 s here)."""
    host, guest = phones(site, browser)
    me = index(host)
    host.evaluate(PAUSE)
    guest.evaluate(PAUSE)
    host.evaluate(RUN, [me, 1 if guest.evaluate(f"fighters[{me}].y < AH / 2") else -1])
    # A phone network's lag: the guest draws a longer moment back (0.11 s seen, 7 units at its speed), so
    # the moment between the host's pause and the guest's (longer on a busy machine) leaves the drawn
    # fighter short of where it stopped (4.2 units seen; 1.6 at the least without the lag).
    host.evaluate(JITTER)
    guest.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    guest.evaluate(DRAWN, me)
    host.evaluate("window.__run = true")
    guest.wait_for_timeout(500)
    # It stops running and the room pauses at once, while the guest still draws it gliding a moment back.
    host.evaluate("window.__run = false; window.__pz = true")
    guest.evaluate("window.__pz = true; window.__held = window.__drawn.length")
    guest.wait_for_timeout(1500)
    held = guest.evaluate("window.__drawn.slice(window.__held)")
    assert len(held) > 30, len(held)
    assert max(y for _, _, y in held) - min(y for _, _, y in held) < 0.01, [round(y, 2) for _, _, y in held]
    host.evaluate("window.__pz = false")
    guest.evaluate("window.__pz = false; window.__go = window.__drawn.length")
    guest.wait_for_timeout(800)
    after = guest.evaluate("window.__drawn.slice(window.__go - 1)")
    stop = host.evaluate(f"fighters[{me}].y")
    # Held short of where it stopped, then on to there.
    assert abs(after[0][2] - stop) > 1, (after[0][2], stop)
    assert abs(after[-1][2] - stop) < 0.5, (after[-1][2], stop)
    # On at about its running speed (62 units/s), by the time between frames: no jump over the pause.
    speeds = [abs(b[2] - a[2]) / (b[0] - a[0]) for a, b in zip(after, after[1:]) if b[0] > a[0]]
    assert max(speeds) < 1.5 * 62, [round(v) for v in speeds]
    assert not host.errors + guest.errors


def test_a_hits_number_starts_where_the_fighter_is_drawn(site, browser):
    """A guest's hit number for a running fighter starts at its drawn spot (a moment back), not at the newest
    spot the host sent."""
    host, guest = phones(site, browser)
    me = index(host)
    host.evaluate(RUN, [me, 1 if guest.evaluate(f"fighters[{me}].y < AH / 2") else -1])
    guest.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate("window.__run = true")
    guest.wait_for_timeout(600)
    # Heard after the game's own handler, which has made the number by then.
    guest.evaluate("""(i) => { window.__hit = null; const f = fighters[i];
      AiPelitRooms.on('message', m => { if (m.t === 's' && window.__hit === null && m.f[i][2] < f.max)
        window.__hit = { newest: m.f[i][1], seen: f.seenY, text: texts.length ? texts[texts.length - 1].y : null }; }); }""", me)
    host.evaluate(f"fighters[{me}].hp -= 7")
    guest.wait_for_function("window.__hit !== null", timeout=5000)
    hit = guest.evaluate("window.__hit")
    assert abs(hit["text"] - hit["seen"]) < 0.01, hit
    assert abs(hit["newest"] - hit["seen"]) > 0.5, hit
    assert not host.errors + guest.errors


# On the guest, with the host's own messages dropped: states fed to the game by hand, fighter `i` moving
# down at V units/s by the fight clock. Every 0.065 s for 0.8 s (each goes on the track), then one more
# only 0.035 s after the last (held back: under 0.06 s), then none. Records each frame [moment drawn, y].
FEED = """([i, V]) => new Promise(done => {
  // Stamps go on from the host's clock, as the host's own would (the track keeps them past its newest).
  const base = JSON.parse(JSON.stringify(window.__last)), off = base.ck - window.__lastAt;
  const t0 = fightClock(), y0 = 120, f = fighters[i];
  const feed = at => { const m = JSON.parse(JSON.stringify(base)), ck = at === undefined ? fightClock() : at;
    m.ck = ck + off; m.f[i][1] = y0 + V * (ck - t0); onMessage(m); return ck; };
  window.__feed = []; const d = window.asDrawn;
  window.asDrawn = () => { const k = d(); window.__feed.push([f.tr.time, f.y]); return k; };
  const tick = () => {
    if (fightClock() - t0 < 0.8) { feed(); setTimeout(tick, 65); return; }
    const last = feed();
    // Stamped 0.035 s after the last, however late the machine's timer brings it.
    setTimeout(() => { window.__held = feed(last + 0.035) - t0; window.__lastOn = last - t0;
      setTimeout(() => done([y0, t0]), 500); }, 35);
  };
  tick(); })"""


def test_a_spot_held_back_goes_on_the_track_before_the_drawing_needs_it(site, browser):
    """A spot heard under 0.06 s after the newest one on the track waits; once the drawn moment nears the
    newest spot on the track, it goes on. Without that, the drawing would stop 0.05 s past the track's newest
    spot (its guess) while a newer spot had been heard: here, with the messages then stopping, it goes on to
    0.05 s past the spot held back."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.evaluate("""() => { AiPelitRooms.on('message', m => { if (m.t === 's') { window.__last = m; window.__lastAt = fightClock(); } }); }""")
    guest.wait_for_function(f"window.__last && fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate(DROP)
    host.evaluate("window.__drop = true")
    guest.wait_for_timeout(300)
    V = 200
    y0, _ = guest.evaluate(FEED, [me, V])
    held, last_on = guest.evaluate("[window.__held, window.__lastOn]")
    assert 0.03 <= held - last_on < 0.06, (held, last_on)
    ys = [y for _, y in guest.evaluate("window.__feed")]
    # Drawn on to 0.05 s past the spot held back (10 units), not stopping 7 units short of it.
    want = y0 + V * (held + 0.05)
    assert abs(ys[-1] - want) < 2, (ys[-1], want, y0 + V * (last_on + 0.05))
    assert not host.errors + guest.errors


# On the guest, with the host's own messages dropped and the room's pause by hand: the host's states fed by
# hand, fighter `i` moving down at V units/s by the fight clock, every 1/30 s (stamps on from the host's
# clock). After 0.6 s the link stalls for 0.5 s (the states go on being made and wait), then the guest pauses
# and the waiting ones land; 0.5 s on the pause ends and the states come on as before for 0.5 s. Records each
# frame [moment, y drawn, paused, y at the moment drawn].
STALL = """([i, V]) => new Promise(done => {
  const base = JSON.parse(JSON.stringify(window.__last)), off = base.ck - window.__lastAt;
  const t0 = fightClock(), y0 = 120, f = fighters[i], q = [];
  const make = () => { const m = JSON.parse(JSON.stringify(base)), ck = fightClock();
    m.ck = ck + off; m.f[i][1] = y0 + V * (ck - t0); return m; };
  window.__st = []; const d = window.asDrawn;
  window.asDrawn = () => { const k = d(); window.__st.push([performance.now() / 1000, f.y, window.__pz,
    f.tr.time === null ? null : y0 + V * (f.tr.time - off - t0)]); return k; };
  let phase = 'on';
  const tick = setInterval(() => { if (phase === 'on') onMessage(make()); else if (phase === 'stall') q.push(make()); }, 1000 / 30);
  setTimeout(() => { phase = 'stall'; }, 600);
  setTimeout(() => { phase = 'pause'; window.__pz = true; for (const m of q.splice(0)) onMessage(m); }, 1100);
  setTimeout(() => { window.__pz = false; phase = 'on'; }, 1600);
  setTimeout(() => { clearInterval(tick); done(); }, 2100); })"""


def test_states_landing_after_a_guest_paused_wait_for_the_pause_to_end(site, browser):
    """The guest pauses before the host's last states reach it (the room tells each phone on its own): they
    land during the pause, after a stall. The drawn fighter holds still all through the pause, and once it is
    over the states go on the track and the drawing eases to them, not in one frame."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.evaluate(PAUSE)
    guest.evaluate("""() => { AiPelitRooms.on('message', m => { if (m.t === 's') { window.__last = m; window.__lastAt = fightClock(); } }); }""")
    guest.wait_for_function(f"window.__last && fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate(DROP)
    host.evaluate("window.__drop = true")
    guest.wait_for_timeout(300)
    guest.evaluate(STALL, [me, 200])
    st = guest.evaluate("window.__st")
    first = next(k for k, e in enumerate(st) if e[2])
    # From the last frame before the pause: the states land as it starts.
    held = [st[first - 1][1]] + [y for _, y, p, *_ in st[first:] if p]
    # Enough frames to judge, also on a machine so busy it draws 8 a second.
    assert len(held) > 3, len(held)
    assert max(held) - min(held) < 0.01, [round(y, 2) for y in held]
    last = max(k for k, e in enumerate(st) if e[2])
    after = [(t, y) for t, y, p, *_ in st[last + 1:]]
    # By the pause the drawing had stood a while (the stall outran its 0.05 s guess) well short of the spot
    # for its moment; after it, it eases there by the time gone (the track's easing, 0.1 s), and the drawn
    # moment goes on at most 1.2 times the clock: never the whole way in one frame, however long the frame.
    gap = st[first][3] - held[-1]
    assert gap > 20, gap
    t1 = st[last][0]
    over = [(round(t - t1, 3), round(y - held[-1], 1)) for t, y in after[:6]
            if y - held[-1] > gap * (1 - math.exp(-(t - t1) / 0.1)) + 1.2 * 200 * (t - t1) + 2]
    assert not over, (over, gap)
    # And by the end it runs on at the states' speed (200 units/s), caught up.
    (ta, ya), (tb, yb) = after[-2], after[-1]
    assert abs(yb - ya) / (tb - ta) < 1.5 * 200, after[-5:]
    assert not host.errors + guest.errors


# The host's states at V units/s, made each 1/30 s by the guest's own clock (the host's stamps, as above) and
# heard L s later. At 2 s the guest pauses and the states on the way land; at 2.5 s the pause ends and they
# come on as before, to 5 s. Records each frame [moment, how far the drawn moment is behind the newest state
# heard, paused].
BEHIND = """([i, V, L]) => new Promise(done => {
  const base = JSON.parse(JSON.stringify(window.__last)), off = base.ck - window.__lastAt;
  const t0 = fightClock(), y0 = 120, f = fighters[i], fly = [];
  let newest = -Infinity, on = true;
  const make = st => { const m = JSON.parse(JSON.stringify(base)); m.ck = st + off; m.f[i][1] = y0 + V * (st - t0); return m; };
  const hear = m => { newest = Math.max(newest, m.ck); onMessage(m); };
  window.__bh = []; const d = window.asDrawn;
  window.asDrawn = () => { const k = d(); window.__bh.push([fightClock() - t0, newest - f.tr.time, window.__pz]); return k; };
  const tick = setInterval(() => {
    if (!on) return;
    fly.push(fightClock());
    while (fly.length && fly[0] <= fightClock() - L) hear(make(fly.shift()));
  }, 1000 / 30);
  setTimeout(() => { on = false; window.__pz = true; for (const st of fly.splice(0)) hear(make(st)); }, 2000);
  setTimeout(() => { window.__pz = false; on = true; }, 2500);
  setTimeout(() => { clearInterval(tick); done(); }, 5000); })"""


def test_after_a_pause_heard_first_the_fighter_is_drawn_behind_its_newest_state(site, browser):
    """The states that landed during the guest's pause go on the track as heard their usual lag after their
    stamps: with the clock read inside the pause they would look early, and the track would draw the fighter
    ahead of its newest state, guessed, for a second or two (without it: up to 0.12 s ahead, 0.07 s ahead on
    average 1 to 2 s on, against 0.04 s behind before the pause)."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.evaluate(PAUSE)
    guest.evaluate("""() => { AiPelitRooms.on('message', m => { if (m.t === 's') { window.__last = m; window.__lastAt = fightClock(); } }); }""")
    guest.wait_for_function(f"window.__last && fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate(DROP)
    host.evaluate("window.__drop = true")
    guest.wait_for_timeout(300)
    guest.evaluate(BEHIND, [me, 100, 0.3])
    bh = guest.evaluate("window.__bh")
    tp = next(t for t, _, p in bh if p)
    tr = max(t for t, _, p in bh if p)
    before = [b for t, b, p in bh if tp - 1 <= t < tp and not p]
    soon = [(round(t - tr, 2), round(b, 3)) for t, b, p in bh if tr + 0.4 <= t < tr + 2 and not p]
    later = [b for t, b, p in bh if tr + 1 <= t < tr + 2 and not p]
    assert len(before) > 5 and len(later) > 5, (len(before), len(later))
    # Once the held states are drawn through (0.4 s on), never drawn ahead of the newest state...
    assert min(b for _, b in soon) > -0.03, soon
    # ...and 1 to 2 s on as far behind it as before the pause, give or take.
    mb, ml = sum(before) / len(before), sum(later) / len(later)
    assert ml > mb - 0.05, (round(mb, 3), round(ml, 3), soon)
    assert not host.errors + guest.errors


# On the guest, with the host's own messages dropped: the host's states fed by hand each 1/30 s (stamped on
# from the host's clock, as above), fighter `i` running down at 125 units/s. From 0.8 s none arrive for 0.4 s
# (lost: the host's phone stalled), and in them it dodges (84 units more, from 0.9 s to 1.1 s); then they come
# on as before, to 2 s. Records each frame [moment, y drawn, whether the state after the stall was heard].
STALLED_DODGE = """(i) => new Promise(done => {
  const base = JSON.parse(JSON.stringify(window.__last)), off = base.ck - window.__lastAt;
  const t0 = fightClock(), y0 = 60, f = fighters[i];
  const y = t => y0 + 125 * t + 84 * Math.min(1, Math.max(0, (t - 0.9) / 0.2));
  let back = false;
  window.__sd = []; const d = window.asDrawn;
  window.asDrawn = () => { const k = d(); window.__sd.push([fightClock() - t0, f.y, back]); return k; };
  const tick = setInterval(() => {
    const t = fightClock() - t0;
    if (t >= 0.8 && t < 1.2) return;
    const m = JSON.parse(JSON.stringify(base)); m.ck = t0 + t + off; m.f[i][1] = y(t);
    onMessage(m); if (t >= 1.2) back = true;
  }, 1000 / 30);
  setTimeout(() => { clearInterval(tick); done(); }, 2000); })"""


def test_a_dodge_over_a_stalled_link_glides(site, browser):
    """A dodge and a run while no state came for 0.4 s (84 + 125 x 0.4 = 134 units between two states, more
    than a fixed 120-unit jump would allow) glides on a guest: a jump is judged by the time between the
    stamps, and nothing in a round moves a fighter that fast. Snapped, it would be drawn over 100 units on in
    one frame."""
    host, guest = phones(site, browser)
    me = index(host)
    guest.evaluate("""() => { AiPelitRooms.on('message', m => { if (m.t === 's') { window.__last = m; window.__lastAt = fightClock(); } }); }""")
    guest.wait_for_function(f"window.__last && fighters[{me}].tr.size() > 3", timeout=5000)
    host.evaluate(DROP)
    host.evaluate("window.__drop = true")
    guest.wait_for_timeout(300)
    guest.evaluate(STALLED_DODGE, me)
    sd = guest.evaluate("window.__sd")
    k = next(k for k, e in enumerate(sd) if e[2])
    # From the frame before the state after the stall was heard to 0.3 s on.
    steps = [(round(t1, 3), round(b - a, 1)) for (_, a, _), (t1, b, _) in zip(sd[k - 1:], sd[k:])
             if t1 < sd[k][0] + 0.3]
    assert len(steps) > 2, steps
    # Each step at most what a 0.1 s ease and the drawn moment's catch-up allow in a frame, never the whole way.
    assert max(abs(s) for _, s in steps) < 60, "steps " + json.dumps(steps) + " frames " + json.dumps(sd)
    assert not host.errors + guest.errors


def test_a_guest_reloading_mid_fight_draws_the_others_at_the_host_s_spot_then_glides(site, browser):
    """A guest that reloads mid-fight comes back into the round (rooms.js): the first state it hears is put on
    the track as it is (net.fresh), so from its first frame it draws the host's fighter where the host has it,
    not gliding there from the start spot, and from then on it glides."""
    host, guest = phones(site, browser)
    me = index(host)
    # The host's fighter goes up and down the arena's middle (y 140 to 300) at 64 units/s, by the clock.
    host.evaluate("""(i) => { const s = window.step; window.step = dt => { const f = fighters[i];
      const p = (64 * AiPelitSulava.now()) % 320; f.x = 170; f.y = 140 + (p < 160 ? p : 320 - p); s(dt); }; }""", me)
    guest.wait_for_timeout(500)
    guest.context.add_init_script("""addEventListener('load', () => {
      window.__rl = []; let said = null, first = null;
      AiPelitRooms.on('message', m => { if (m.t === 's' && typeof fighters !== 'undefined' && foe) {
        said = m.f[fighters.indexOf(foe)][1]; if (first === null) first = said; } });
      const d = window.asDrawn;
      window.asDrawn = () => { const k = d();
        if (state === 'fight' && foe && first !== null) window.__rl.push([performance.now() / 1000, foe.y, first, said]);
        return k; }; })""")
    guest.reload()
    guest.wait_for_function("state === 'fight' && window.__rl && window.__rl.length >= 60", timeout=15000)
    rl = guest.evaluate("window.__rl")
    # The first frame drawn is at the first state heard.
    assert abs(rl[0][1] - rl[0][2]) < 1, rl[:5]
    # Then it glides: on at up to the fighter's speed (64 units/s) over each two frames that came in time,
    # never a jump.
    sp = [(round(t2 - rl[0][0], 3), round(abs(b - a) / (t2 - t0), 1))
          for (t0, a, *_), (t1, *_), (t2, b, *_) in zip(rl, rl[1:], rl[2:]) if t1 - t0 < 0.04 and t2 - t1 < 0.04]
    assert len(sp) > 20, len(sp)
    assert max(v for _, v in sp) < 1.5 * 64, "speeds " + json.dumps(sp)
    # And it moves, not standing on the first spot.
    assert max(y for _, y, *_ in rl) - min(y for _, y, *_ in rl) > 10, rl
    assert not host.errors + guest.errors
