"""Aitajuoksu v13 (#480): a friend's runner glides on the other phones' screens, drawn from lib/sulava-1 between the
spots their phone sends (12 a second), instead of jumping to each one as it comes and carrying it on at its last
speed until the next (v12), and its jump over a hurdle rises and falls every frame instead of in steps. The race
itself (places, the host's end of the race) keeps the newest spot."""

import json
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/aitajuoksu/v13/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own runner runs at 8 m/s while `window.__run` is on, hopping 0.8 m high over 4 m of every 8, with no
# taps and no hurdles hit; the computer's and the friends' runners move as the game moves them.
DRIVE = """() => { const mv = window.move; window.__run = false;
  window.move = (r, dt, clock) => {
    if (r !== me) return mv(r, dt, clock);
    const v = window.__run ? 8 : 0;
    r.v = v; r.x += v * dt; r.ph += v * dt * 1.5;
    const k = (r.x % 8) / 4;
    r.y = window.__hop && k < 1 ? 0.8 * Math.sin(Math.PI * k) : 0; r.vy = 0;
  }; }"""
# Records, each time the screen is drawn, where runner `i` is drawn (x, y), and when each message arrived.
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.drawFrame;
  window.drawFrame = () => { const r = race.runners[i];
    if (window.__xs.length < 400 && !window.__stop) window.__xs.push([performance.now() / 1000, r.x, r.y]); d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room (two unless more names are given), the race running."""
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
    for n, guest in enumerate(guests, 2):
        guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
        guest.click("#aipr-joinBtn")
        guest.wait_for_function("AiPelitRooms.inRoom")
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {n}")
    for p in pages:
        p.evaluate(DRIVE)
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=10000)
    return pages


def watch(run, other, hop=False):
    """`run` runs for 2.5 s while `other` records where it draws `run`'s runner."""
    i = run.evaluate("race.runners.indexOf(me)")
    run.evaluate(JITTER)
    if hop:
        run.evaluate("window.__hop = true")
    other.evaluate(SAMPLE, i)
    run.evaluate("window.__run = true")
    run.wait_for_timeout(2500)
    other.evaluate("window.__stop = true")
    run.evaluate("window.__run = false")
    return other.evaluate("[window.__xs, window.__got]")


def steady(got, t):
    """Spots came in steadily just before `t`: a loaded test machine sometimes holds the messages back longer than
    the track's longest delay (0.25 s), and nothing glides through such a hole."""
    before = [g for g in got if g <= t]
    return len(before) > 1 and t - before[-1] < 0.15 and before[-1] - before[-2] < 0.2


def speeds(xs, got):
    sp = [(t2, (c - a) / (t2 - t0)) for (t0, a, _), (t2, c, _) in zip(xs, xs[2:]) if t2 > t0]
    moving = [t for t, v in sp if v > 1]
    assert len(moving) > 60, len(moving)
    middle = [(t, v) for t, v in sp if moving[0] + 0.5 <= t <= moving[-1] - 0.2]
    kept = [v for t, v in middle if steady(got, t)]
    assert len(kept) > 30 and len(kept) > 0.5 * len(middle), (len(kept), len(middle))
    return kept


def glides(xs, got, lo=2, spread=0.25):
    kept = speeds(xs, got)
    shown = [round(v, 1) for v in kept]
    # Never backwards (v12: each spot that came later than the one before pulled the runner back), and about 8 m/s.
    assert min(kept) > lo, shown
    m, sd = mean(kept), pstdev(kept)
    assert 6 < m < 10, shown
    assert sd < spread * m, (sd, m, shown)


@pytest.mark.parametrize("who", ["guest", "host"])
def test_a_friends_runner_glides_at_its_own_speed(site, browser, who):
    host, guest = phones(site, browser)
    run, other = (guest, host) if who == "guest" else (host, guest)
    glides(*watch(run, other))
    assert not host.errors and not guest.errors, host.errors + guest.errors


def test_a_friends_runner_glides_on_a_third_phone_too(site, browser):
    """A friend's spots reach a third phone through the host, as they came: not where the host has carried the
    runner on since, which would no longer match the friend's stamp sent with it."""
    pages = phones(site, browser, ("Testi A", "Testi B", "Testi C"))
    host, run, other = pages
    host.evaluate(JITTER)
    # Two jittery hops may now and then leave a frame slow, but the speed stays even: sent on from where the host
    # had carried the runner, it spread 2-3 m/s about its 8 (0.6-0.9 sent as it came).
    glides(*watch(run, other), lo=1, spread=0.15)
    assert not any(p.errors for p in pages), [p.errors for p in pages]


def test_a_friends_jump_rises_and_falls_every_frame(site, browser):
    host, guest = phones(site, browser)
    xs, got = watch(guest, host, hop=True)
    up = [(t, y0, y1) for (t, _, y0), (_, _, y1) in zip(xs, xs[1:]) if y0 > 0.15 and y1 > 0.15 and steady(got, t)]
    assert len(up) > 20, len(up)
    # v12 drew the height only as each spot came, 12 a second, so it stood still on most frames of a jump.
    still = sum(1 for _, y0, y1 in up if abs(y1 - y0) < 1e-6)
    assert still < 0.3 * len(up), (still, len(up))
    assert max(y for _, _, y in xs) > 0.6
    assert not host.errors and not guest.errors, host.errors + guest.errors


def test_the_race_keeps_the_newest_spot(site, browser):
    """Between frames the host keeps a friend's runner where its phone last said, ahead of where it is drawn."""
    host, guest = phones(site, browser)
    i = guest.evaluate("race.runners.indexOf(me)")
    guest.evaluate("window.__run = true")
    guest.wait_for_timeout(1500)
    drawn, kept = host.evaluate("""(i) => { const r = race.runners[i], x = r.x;
      const o = r.tr.at(); return [o.x, x]; }""", i)
    guest.evaluate("window.__run = false")
    assert kept > drawn, (kept, drawn)
    assert kept - drawn < 8 * 0.4, (kept, drawn)


def test_the_place_shown_is_the_races(site, browser):
    """The place on the screen goes by the newest spots, not by where the friends are drawn a moment back."""
    host, guest = phones(site, browser)
    i = guest.evaluate("race.runners.indexOf(me)")
    # The friend stands just ahead of the host's runner, but is drawn well behind it.
    place = host.evaluate("""(i) => { const r = race.runners[i]; me.x = r.x - 1;
      r.tr = { at: () => ({ x: me.x - 5, y: 0 }), size: () => 1, push() {}, reset() {} };
      draw(); return [livePlace, place(me), race.runners.length]; }""", i)
    assert place[0] == place[1] and place[0] >= 2, place
    assert not host.errors and not guest.errors, host.errors + guest.errors


def test_a_stalled_frame_on_the_friends_phone_never_draws_them_back(site, browser):
    """A busy phone (here the host) misses frames: its runner moves at most 0.05 s a frame, so after a stalled frame
    it has gone less far than the wall clock says. Its spots are stamped on a clock (gameT) that moves the same way
    and catches up with the wall clock slowly: stamped on the wall clock, the other phone guessed the runner on at
    full speed through the stall and then drew it back (-3.4 m/s)."""
    host, guest = phones(site, browser)
    i = host.evaluate("race.runners.indexOf(me)")
    guest.evaluate(SAMPLE, i)
    host.evaluate("window.__run = true")
    host.wait_for_timeout(1200)
    for _ in range(3):
        host.evaluate("() => { const e = performance.now() + 200; while (performance.now() < e); }")
        host.wait_for_timeout(300)
    host.wait_for_timeout(600)
    guest.evaluate("window.__stop = true")
    xs = guest.evaluate("window.__xs")
    back = [(round(t1, 2), round(b - a, 3)) for (_, a, _), (t1, b, _) in zip(xs, xs[1:]) if b < a - 1e-3]
    assert not back, back
    assert xs[-1][1] - xs[0][1] > 15, (xs[0][1], xs[-1][1])
    assert not host.errors and not guest.errors, host.errors + guest.errors
