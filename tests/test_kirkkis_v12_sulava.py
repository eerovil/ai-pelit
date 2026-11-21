"""Kirkkis v12 (#480): a friend running across the yard glides on the other phones' screens, drawn from lib/sulava-1
between the spots their phone sends, instead of jumping to each one as it comes (on the host, v11) or chasing it
(on a guest). The host's rules still use the newest spot; only the drawing lags."""

import json
import shutil
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kirkkis/v12/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# Records, each time the screen is drawn, where person `i` is drawn, and when a message arrived (so a stall of the
# test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { if (window.__xs.length < 300) window.__xs.push([performance.now() / 1000, people[i].x, people[i].y]); d(); }; }"""


def phones(site, browser, seeker, names=("Eero", "Aino"), mode="kirkkis"):
    """Phones in a room, computer players up to five; `seeker` (0 the host, 1 the first guest) counts first."""
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
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
    # The host picks the first seeker among the phones at random: make it the one asked for.
    host.evaluate(f"roomMode = {mode!r}")
    host.evaluate(f"window.__rnd = Math.random; Math.random = () => {(seeker + 0.5) / len(names)}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("people.length === 5 && phase === 'count'")
    host.evaluate("Math.random = window.__rnd")
    assert host.evaluate("people.indexOf(seeker)") == seeker
    host.relay = relay
    return pages


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
    assert min(kept) > 0.3, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


# A guest runs, seen on the host (whose rules keep the newest spot and whose screen draws it smoothly),
# and the host runs, seen on a guest (which in v11 chased the newest spot).
@pytest.mark.parametrize("walker", ["guest", "host"])
def test_a_friend_running_glides_on_the_other_phone(site, browser, walker):
    host, guest = phones(site, browser, seeker=0 if walker == "guest" else 1)
    run_and_watch(host, *((guest, host) if walker == "guest" else (host, guest)), others=[guest])


def test_a_friend_running_glides_on_a_third_phone_too(site, browser):
    """The host forwards a friend's spots with the friend's own clock, so a third phone draws them as smoothly."""
    host, aino, ville = phones(site, browser, seeker=0, names=("Eero", "Aino", "Ville"))
    host.evaluate(JITTER)
    run_and_watch(host, aino, ville, others=[aino, ville])


def run_and_watch(host, run, watch, others):
    me = run.evaluate("people.indexOf(player)")
    run.evaluate(JITTER)
    # Out in the open, running straight along the yard at three quarters of full speed (no sprint).
    run.evaluate("Object.assign(player, { x: 1, y: 11 })")
    watch.wait_for_function(f"Math.abs(people[{me}].x - 1) < 0.05 && Math.abs(people[{me}].y - 11) < 0.05", timeout=5000)
    watch.evaluate(SAMPLE, me)
    if run is not host:
        # On each friend's spot the host's rules know it at once (not where its screen draws them), and the
        # screen draws it a moment back.
        host.evaluate("""(me) => { window.__rule = []; AiPelitRooms.on('message', (m, from) => {
          if (m.t === 'kme' && from === people[me].id && phase === 'count') window.__rule.push([m.x, people[me].x, m.s - people[me].tr.time]); }); }""", me)
    run.evaluate("joy = { id: -1, ox: 100, oy: 100, x: 140, y: 100 }")
    watch.wait_for_function("window.__xs.length >= 200", timeout=20000)
    run.evaluate("letGo()")
    assert run.evaluate("player.x") > 8  # it really ran, not into a wall
    glides(watch)
    if run is not host:
        rule = host.evaluate("window.__rule")
        assert len(rule) > 15, rule
        assert all(abs(said - known) < 0.01 for said, known, _ in rule), rule  # the rules: the newest spot
        assert all(back > 0.03 for _, _, back in rule[5:]), rule  # drawn at least 30 ms back on the friend's clock
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


# Where person `i` is drawn, each time the screen is drawn; and how many frames were drawn when the first message
# that told of a recount or a tag arrived (`__ev`, after the game has read it).
DRAWN = """(i) => { window.__at = []; window.__ev = null; const d = window.draw;
  window.draw = () => { window.__at.push([people[i].x, people[i].y]); d(); };
  AiPelitRooms.on('message', m => { if (window.__ev === null && m.t === 'ks' && (m.ev || []).some(e => e[0] === 'all' || e[0] === 'tag'))
    window.__ev = window.__at.length; }); }"""


def drawn_since(page, n):
    return page.evaluate(f"window.__at.slice({n})")


def drawn_from_event(page, x, y):
    """From the first frame after the message that told of it, a guest draws the person at (x, y)."""
    page.wait_for_function("window.__ev !== null", timeout=2000)
    page.wait_for_timeout(500)
    at = page.evaluate("window.__at.slice(window.__ev)")
    assert len(at) > 10
    assert all(abs(a - x) < 0.05 and abs(b - y) < 0.05 for a, b in at), (x, y, at[:5], at[-5:])


def test_a_friend_seeking_goes_back_to_the_base_at_once_on_every_phone(site, browser):
    """"Kaikki pelastettu!" puts the seeker back at the base. When the seeker is a friend, the host moves them there
    itself and forwards that spot with the friend's last stamp, which the tracks had already heard: v12's first
    commit drew them where they were until their phone sent again."""
    host, aino, ville = phones(site, browser, seeker=1, names=("Eero", "Aino", "Ville"))
    me = 1
    aino.evaluate("Object.assign(player, { x: 3, y: 30 })")
    for p in (host, ville):
        p.wait_for_function(f"Math.abs(people[{me}].x - 3) < 0.05 && Math.abs(people[{me}].y - 30) < 0.05", timeout=5000)
        p.evaluate(DRAWN, me)
    # Aino's phone falls silent, so only the round itself can tell where she is.
    aino.evaluate("AiPelitRooms.send = () => {}")
    n, bx, by = host.evaluate(f"phase = 'seek'; allSaved(player); [window.__at.length, people[{me}].x, people[{me}].y]")
    assert abs(bx - 3) + abs(by - 30) > 5  # the base is far from where she stood
    # The host from its next frame, Ville from the first frame after the message that told him.
    host.wait_for_timeout(500)
    at = drawn_since(host, n)
    assert len(at) > 10 and all(abs(x - bx) < 0.05 and abs(y - by) < 0.05 for x, y in at), (bx, by, at[:5])
    drawn_from_event(ville, bx, by)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_running_friend_tagged_stops_where_they_were_tagged(site, browser):
    """Hippa: a tagged friend waits frozen. The host takes no spot from them meanwhile, so the tracks hear nothing
    and would guess them on at their last speed: v12's first commit drew them sliding on from where they were
    tagged, on the host and on the other phones."""
    host, aino, ville = phones(site, browser, seeker=0, names=("Eero", "Aino", "Ville"), mode="hippa")
    me = 1
    for p in (aino, ville):
        p.wait_for_function("mode === 'hippa'")
    aino.evaluate("Object.assign(player, { x: 1, y: 11 })")
    for p in (host, ville):
        p.wait_for_function(f"Math.abs(people[{me}].x - 1) < 0.05", timeout=5000)
        p.evaluate(DRAWN, me)
    aino.evaluate(JITTER)
    aino.evaluate("joy = { id: -1, ox: 100, oy: 100, x: 140, y: 100 }")
    host.wait_for_function(f"people[{me}].x > 5", timeout=5000)
    # The host, who is it, tags her where she runs: its own player jumps next to her (the rules use her newest spot).
    host.evaluate(f"(() => {{ const h = people[{me}]; Object.assign(player, {{ x: h.x - 0.3, y: h.y }}); timer = Math.max(timer, 20); phase = 'seek'; seeker.st = 'seek'; rulesTag(); }})()")
    assert host.evaluate(f"seeker === people[{me}] && people[{me}].freeze > 0")
    n, tx, ty = host.evaluate(f"[window.__at.length, people[{me}].x, people[{me}].y]")
    # Every frame from the tag on (on Ville from the message that told him) draws her where she was tagged.
    host.wait_for_timeout(500)
    at = drawn_since(host, n)
    assert len(at) > 10 and all(abs(x - tx) < 0.05 and abs(y - ty) < 0.05 for x, y in at), (tx, ty, at[:5], at[-5:])
    drawn_from_event(ville, tx, ty)
    aino.evaluate("letGo()")
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# On a guest: each time the host's rows for person `i` change whose clock they carry (the computer took over a friend,
# or gave them back), the spot that row brought, and where the next frame drew them.
SWITCH = """(i) => { window.__sw = []; let src = people[i].src, want = null; const d = window.draw;
  AiPelitRooms.on('message', m => { if (m.t === 'ks' && people[i].src !== src) { src = people[i].src;
    const q = m.p[i]; want = [src, q[0], q[1]]; } });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, people[i].x, people[i].y]); want = null; } }; }"""


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-run: the host's computer runs their player, so the rows carry the host's clock and
    no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at each
    change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, seeker=0, names=("Eero", "Aino", "Ville"))
    me = 1
    aino.evaluate("Object.assign(player, { x: 1, y: 11 })")
    ville.wait_for_function(f"Math.abs(people[{me}].x - 1) < 0.05 && people[{me}].src === 'f'", timeout=5000)
    ville.evaluate(SWITCH, me)
    aino.evaluate("joy = { id: -1, ox: 100, oy: 100, x: 140, y: 100 }")
    host.wait_for_function(f"people[{me}].x > 3", timeout=5000)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"people[{me}].ctrl === 'bot'")
    ville.wait_for_function("window.__sw.length >= 1", timeout=5000)
    aino.evaluate("letGo()")
    host.relay.back(aino)
    host.wait_for_function(f"people[{me}].ctrl === 'remote' && Number.isFinite(people[{me}].ts)", timeout=20000)
    ville.wait_for_function("window.__sw.length >= 2", timeout=5000)
    sw = ville.evaluate("window.__sw")
    assert [s[0] for s in sw[:2]] == ["h", "f"], sw
    assert all(abs(x - a) < 0.01 and abs(y - b) < 0.01 for _, a, b, x, y in sw), sw
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors
