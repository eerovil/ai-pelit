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
# The phone's stick, in the arena's directions: at half speed (62 units/s) along the arena's middle (x 170,
# clear of the pillars) towards `dir` (-1 up, 1 down) while `window.__run` is on, until 120 units short of
# the far end, where the other fighter stands.
RUN = """(dir) => { window.__run = false;
  window.playerInput = () => ({ mx: 0, my: window.__run && (dir < 0 ? me.y > 130 : me.y < 310) ? dir * 0.5 : 0,
    sword: false, bow: false, dash: false, lead: 1 }); }"""
# Records, each time the screen is drawn, where fighter `i` is drawn along the arena, and when a host's
# message arrived (so a stall of the test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__ys = []; window.__got = [];
  AiPelitRooms.on('message', m => { if (m.t === 's') window.__got.push(performance.now() / 1000); });
  const d = window.draw;
  window.draw = () => { if (window.__ys.length < 300) window.__ys.push([performance.now() / 1000, fighters[i].y]); d(); }; }"""


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
    ys, got = page.evaluate("[window.__ys, window.__got]")
    sp = [(t2, abs(b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(ys, ys[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 10]
    assert len(moving) > 50, len(moving)
    # Leave out the start and the stop: the drawing speeds up and slows down there over a moment.
    t0, t1 = sp[moving[0]][0] + 0.15, sp[moving[-1]][0] - 0.3
    middle = [(t, v) for t, v in sp if t0 <= t <= t1]
    assert len(middle) > 30, len(middle)

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 20, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def run_and_watch(host, run, watch, others):
    """`run` moves its fighter along the arena while `watch` draws it; the host's messages are jittered."""
    me = index(run)
    run.evaluate(RUN, 1 if run.evaluate("me.y < AH / 2") else -1)
    host.evaluate(JITTER)
    watch.wait_for_function(f"fighters[{me}].tr.size() > 3", timeout=5000)
    watch.evaluate(SAMPLE, me)
    # Between frames the watching phone keeps the newest spot the host sent (ahead of the drawn one, as the
    # fighter runs on): `window.__rule` pairs it with the newest spot heard and the last one drawn.
    watch.evaluate("""(i) => { const f = fighters[i]; let said = null; window.__rule = [];
      AiPelitRooms.on('message', m => { if (m.t === 's') said = m.f[i][1]; });
      setInterval(() => { if (said !== null && window.__ys.length)
        window.__rule.push([f.y, said, window.__ys[window.__ys.length - 1][1]]); }, 37); }""", me)
    run.evaluate("window.__run = true")
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
    """The friend's stick moves their fighter in the host's fight; a third phone draws it as smoothly."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    run_and_watch(host, aino, ville, others=[aino, ville])


def test_a_jump_is_drawn_at_once_not_glided(site, browser):
    """A fighter that the host's spots move further than a dodge between two messages (a phone back after a
    while away, heard again) is drawn there at once on the next frame, not slid across the arena."""
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
