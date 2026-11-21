"""Areena v9 (#480): on a friend's phone the other fighters glide across the arena, drawn from lib/sulava-1
between the spots the host sends, instead of chasing each newest spot (v8). The host runs the whole fight from
every phone's stick, so it draws everyone where its own fight has them, and nothing about it changes; a guest's
own fighter still chases its newest spot, with no extra delay. Between frames every fighter stands at the newest
spot heard; only the drawing lags."""

import json
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
# (asDrawn(), right before the drawing), and whether the phone had by then heard a spot from the host newer
# than the moment drawn (so a stall of the test machine or its relay, with no spot heard for a while, can be
# told from a jerk: the drawing then waits on the newest spot, by design).
SAMPLE = """(i) => { window.__ys = []; let heard = -Infinity; const tr = fighters[i].tr;
  AiPelitRooms.on('message', m => { if (m.t === 's' && m.ck > heard) heard = m.ck; });
  const a = window.asDrawn;
  window.asDrawn = () => { const t = performance.now() / 1000, kept = a();
    if (window.__ys.length < 300) window.__ys.push([t, fighters[i].y, tr.time <= heard]); return kept; }; }"""


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
    # Only frames drawn with a spot heard ahead of them: the drawing's own glide, not a gap in the messages.
    kept = [v for _, v, fed in middle if fed]
    shown = [round(v) for _, v, _ in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 20, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


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
    """The host moves a fighter 230 units in one frame, further than the track's jump (120 units, more than a
    whole dodge's 84): from the first frame after the state that says so, the guest draws it where it landed,
    not sliding across the arena towards it."""
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


def test_on_a_laggy_link_the_drawn_moment_stays_within_the_tracks_spots(site, browser):
    """A track keeps 8 spots. The host sends 30 states a second, and 8 of them span under a quarter second,
    less than the longest the drawing may wait (0.25 s): on a laggy link the drawn moment would fall before
    the oldest spot, and the fighter would stand on it. A spot goes on the track only 0.06 s or more after the
    one before it (or when the drawing comes near the newest one), so on a link 0-250 ms late the drawn moment
    stays within the spots kept; the messages and how often they go are as before."""
    host, guest = phones(site, browser)
    me = index(host)
    host.evaluate(JITTER.replace("rnd() * 90", "rnd() * 250"))
    guest.evaluate("""(i) => { window.__in = []; window.__sent = []; window.__at = [];
      const tr = fighters[i].tr, p = tr.push;
      AiPelitRooms.on('message', m => { if (m.t === 's') window.__sent.push(m.ck); });
      tr.push = (t, v, a) => { const n = window.__in; if (!n.length || t > n[n.length - 1]) n.push(t); return p(t, v, a); };
      const d = window.asDrawn;
      window.asDrawn = () => { const k = d(), n = window.__in;
        if (n.length >= 10) window.__at.push([tr.time, n[n.length - 8], tr.delay]); return k; }; }""", me)
    guest.wait_for_function("window.__at.length >= 240", timeout=20000)
    at, sent = guest.evaluate("[window.__at, window.__sent]")
    gaps = [b - a for a, b in zip(sent, sent[1:])]
    # The host still sends one state each frame once 1/30 s has passed (two or three 60 Hz frames).
    assert mean(gaps) < 0.055, gaps
    # The link is laggy enough that the drawing waits long.
    assert max(d for _, _, d in at[-60:]) > 0.2, [round(d, 3) for _, _, d in at]
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
    assert past < 25, (past, stop, ys)
    assert not host.errors + guest.errors


def test_a_paused_room_holds_the_drawn_fighters_and_goes_on_from_there(site, browser):
    """While the room waits for a phone that is away, a guest draws the other fighters where they were when
    it paused, not going on at their last speed past the newest spot; when the room goes on, they move on
    from there a little each frame, with no jump over the pause (1.5 s here)."""
    host, guest = phones(site, browser)
    me = index(host)
    host.evaluate(PAUSE)
    guest.evaluate(PAUSE)
    host.evaluate(RUN, [me, 1 if guest.evaluate(f"fighters[{me}].y < AH / 2") else -1])
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
    assert abs(after[0][2] - stop) > 2, (after[0][2], stop)
    assert abs(after[-1][2] - stop) < 0.5, (after[-1][2], stop)
    steps = [abs(b[2] - a[2]) for a, b in zip(after, after[1:])]
    assert max(steps) < 3, [round(s, 2) for s in steps]
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
