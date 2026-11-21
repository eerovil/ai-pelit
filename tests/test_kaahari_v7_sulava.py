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
    const p = at(T, window.__s, window.__lane);
    Object.assign(k, { x: p.x, y: p.y, a: p.a, idx: p.i, s: ((window.__s % T.L) + T.L) % T.L, lat: window.__lane, z: 0, vz: 0 });
  }; }"""
# Records, each time the screen is drawn, where kart `i` is drawn, and when a message arrived (so a stall of the
# test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { const k = race.karts[i];
    if (window.__xs.length < 300) window.__xs.push([performance.now() / 1000, k.x, k.y]); d(); }; }"""


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
    xs, got = page.evaluate("[window.__xs, window.__got]")
    sp = [(t2, math.hypot(c - a, d - b) / (t2 - t0)) for (t0, a, b), (t2, c, d) in zip(xs, xs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 1]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
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
            if (l) window.__rule.push((k.x - l[1]) * Math.cos(k.a) + (k.y - l[2]) * Math.sin(k.a)); }, 37); }""", me)
    s0 = run.evaluate("window.__s")
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__xs.length >= 200", timeout=20000)
    run.evaluate("window.__run = false")
    assert run.evaluate("window.__s") > s0 + 200  # it really drove
    glides(watch)
    if run is not host:
        rule, back = host.evaluate("[window.__rule, window.__back]")
        assert len(rule) > 30, rule
        moving = rule[5:-10]
        assert sum(a > 3 for a in moving) > 0.9 * len(moving), rule  # the newest spot, not the drawn one
        assert len(back) > 15 and all(b > 0.03 for b in back[5:]), back  # drawn at least 30 ms back
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
    assert math.hypot(nx - bx, ny - by) > 3, (nx, ny, bx, by)  # and the newest spot was elsewhere
    errors = [e for p in (host, aino) for e in p.errors]
    assert not errors, errors
