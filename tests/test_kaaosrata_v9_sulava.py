"""Kaaosrata v9 (#480): a friend's runner glides on the other phones' screens, drawn from lib/sulava-1 between the
spots their phone sends, instead of jumping to each one as it comes (v8 drew each spot at once and carried it on at
its last speed until the next). The race's rules (bumps, the finish) still use the newest spot; only the drawing lags."""

import json
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaaosrata/v9/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own runner goes straight up the course at 4 m/s, past every obstacle (so it never falls or is knocked),
# while `window.__run` is on; the others move by the game's own rules.
STRAIGHT = """() => { const mv = window.move; window.__run = false;
  window.move = (r, dt, t) => { if (r !== me || !window.__run || r.fall > 0) return mv(r, dt, t);
    r.vx = 0; r.vy = 4; r.z = 0; r.vz = 0; r.y += 4 * dt; }; }"""
# Records, each time the screen is drawn, where runner `i` is drawn, and when a message arrived (so a stall of the
# test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { const r = race.runners[i];
    if (window.__xs.length < 300) window.__xs.push([performance.now() / 1000, r.x, r.y]); d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the race running; the computer's runners stand aside, out of everyone's way."""
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
    host.evaluate("race.runners.forEach(r => { if (r.bot) { r.kind = 'parked'; Object.assign(r, { x: -4.5, y: -3, vx: 0, vy: 0 }); } })")
    host.relay = relay
    return pages


def index(page):
    return page.evaluate("race.runners.indexOf(me)")


def glides(page):
    """The speed over each two drawn frames while the friend ran: always forward and about the same."""
    xs, got = page.evaluate("[window.__xs, window.__got]")
    sp = [(t2, ((c - a) ** 2 + (d - b) ** 2) ** 0.5 / (t2 - t0))
          for (t0, a, b), (t2, c, d) in zip(xs, xs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.01]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 1, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def run_and_watch(host, run, watch, others):
    me = index(run)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host:
        # On each friend's spot the host's rules know it at once (not where its screen draws them), and the
        # screen draws it a moment back on the friend's clock.
        host.evaluate("""(me) => { window.__rule = []; AiPelitRooms.on('message', (m, from) => { const r = race.runners[me];
          if (m.t === 'p' && from === r.id) window.__rule.push([m.r[1], r.y, m.s - r.tr.time]); }); }""", me)
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__xs.length >= 200", timeout=20000)
    run.evaluate("window.__run = false")
    assert run.evaluate("me.y") > 8  # it really ran
    glides(watch)
    if run is not host:
        rule = host.evaluate("window.__rule")
        assert len(rule) > 15, rule
        assert all(abs(said - known) < 0.01 for said, known, _ in rule), rule  # the rules: the newest spot
        assert all(back > 0.03 for _, _, back in rule[5:]), rule  # drawn at least 30 ms back
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


# A guest runs, seen on the host (whose rules keep the newest spot and whose screen draws it smoothly),
# and the host runs, seen on a guest.
@pytest.mark.parametrize("walker", ["guest", "host"])
def test_a_friend_running_glides_on_the_other_phone(site, browser, walker):
    host, guest = phones(site, browser)
    run_and_watch(host, *((guest, host) if walker == "guest" else (host, guest)), others=[guest])


def test_a_friend_running_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on as they came, with the friend's own clock, so a third phone draws them
    as smoothly (v8 sent its own guess of where they had got to)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(JITTER)
    run_and_watch(host, aino, ville, others=[aino, ville])


# On a phone: each time a message brings runner `i` back on their feet after a fall, or changes whose clock their
# spot carries (the computer took over a friend, or gave them back), the spot it brought and where the next frame
# drew them.
SWITCH = """(i) => { window.__sw = []; const r = race.runners[i]; let src = r.src, fell = false, want = null; const d = window.draw;
  AiPelitRooms.on('message', (m, from) => { const a = m.t === 's' ? m.r[i] : m.t === 'p' && from === r.id ? m.r : null;
    if (!a) return;
    if (a[7] > 0) fell = true;
    else if (fell) { fell = false; want = ['up', a[0], a[1]]; }
    if (r.src !== src) { src = r.src; want = [src, a[0], a[1]]; } });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, r.x, r.y]); want = null; } }; }"""


def placed(page, n):
    page.wait_for_function(f"window.__sw.length >= {n}", timeout=8000)
    sw = page.evaluate("window.__sw")
    assert all(abs(x - a) < 0.01 and abs(y - b) < 0.01 for _, a, b, x, y in sw), sw
    return [s[0] for s in sw]


@pytest.mark.parametrize("watcher", ["host", "third"])
def test_a_friend_back_on_their_feet_after_a_fall_is_drawn_at_the_checkpoint_at_once(site, browser, watcher):
    """A fall ends at the checkpoint: the next spot is there, which the track must not glide to from the pit. Here
    the pit is only 1.8 m from it, too near for the track to tell a jump by itself: only the fall says it was one."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    watch = host if watcher == "host" else ville
    me = index(aino)
    # She stands 1.8 m up from the start line, in the middle, where she comes back too (a fixed random spot).
    aino.evaluate("Math.random = () => 0.5; Object.assign(me, { x: 0, y: 1.8, vx: 0, vy: 0, vz: 0 })")
    watch.wait_for_function(f"Math.abs(race.runners[{me}].x) < 0.05 && Math.abs(race.runners[{me}].y - 1.8) < 0.05", timeout=3000)
    watch.wait_for_timeout(400)
    watch.evaluate(SWITCH, me)
    aino.evaluate("Object.assign(me, { fall: 0.001, vx: 0, vy: 0, vz: 0 })")
    aino.wait_for_function("me.fall === 0 && me.y === 0", timeout=3000)
    assert placed(watch, 1)[0] == "up"
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-race: the host's computer runs their runner, so the rows carry the host's clock
    and no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at
    each change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = index(aino)
    aino.evaluate("window.__run = true")
    ville.wait_for_function(f"race.runners[{me}].src === 'f' && race.runners[{me}].y > 2", timeout=5000)
    ville.evaluate(SWITCH, me)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"race.runners[{me}].kind === 'cpu'")
    ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
    aino.evaluate("window.__run = false")
    host.relay.back(aino)
    host.wait_for_function(f"race.runners[{me}].kind === 'net' && race.runners[{me}].hd", timeout=20000)
    ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
    kinds = [k for k in placed(ville, 2) if k != "up"]
    assert kinds[:2] == ["h", "f"], kinds
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors
