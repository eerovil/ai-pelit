"""Lentopallo v8 (#480): a friend's player glides along the sand on the other phones' screens, drawn from
lib/sulava-1 between the spots their phone sends, instead of chasing each newest spot (v7). The rules, the hits
and the score use the newest spot heard; only the drawing lags."""

import json
from statistics import mean, pstdev

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/lentopallo/v8/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own player runs away from the net at 2.5 m/s while `window.__run` is on, and stops 0.4 m before
# the back line; the computer's players stand still, so nobody serves or plays the ball meanwhile.
RUN = """() => { window.__run = false;
  window.steer = () => { mine.vx = window.__run && Math.abs(mine.x) < 4.7 ? mine.side * 2.5 : 0; };
  window.cpuThink = p => { p.vx = 0; }; }"""
# Records, each time the screen is drawn, where player `i` is drawn along the sand, and when a message arrived
# (so a stall of the test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { if (window.__xs.length < 300) window.__xs.push([performance.now() / 1000, players[i].x]); d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the match on, nobody serving."""
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
        p.wait_for_function("mine && players.length && state === 'serve'", timeout=10000)
        p.evaluate(RUN)
    host.relay = relay
    return pages


def index(page):
    return page.evaluate("players.indexOf(mine)")


def glides(page):
    """The speed over each two drawn frames while the friend ran: always the same way and about the same."""
    xs, got = page.evaluate("[window.__xs, window.__got]")
    sp = [(t2, abs(b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(xs, xs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.3]
    assert len(moving) > 50, len(moving)
    # Leave out the start and the stop: the drawing speeds up and slows down there over a moment.
    t0, t1 = sp[moving[0]][0] + 0.15, sp[moving[-1]][0] - 0.3
    middle = [(t, v) for t, v in sp if t0 <= t <= t1]
    assert len(middle) > 30, len(middle)

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 0.8, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def run_and_watch(host, run, watch, others):
    me = index(run)
    # Free to run: whoever serves is not the runner, and the runner starts near the net.
    host.evaluate("(i) => { if (server === players[i]) { server = players.find(p => p !== players[i]); newRally(); } }", me)
    run.wait_for_function("state === 'serve' && mine.x !== 0")
    run.evaluate("mine.x = mine.side * 0.5")
    watch.wait_for_function(f"Math.abs(players[{me}].x) < 0.6 && players[{me}].tr.size() > 3", timeout=5000)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host and watch is not host:
        host.evaluate(SAMPLE, me)  # the host's drawn spots, for its check below
    if run is not host:
        # Between frames the host keeps the friend's newest spot (ahead of where it last drew them, as they run
        # on): its rules play the ball against it.
        host.evaluate("""(me) => { const p = players[me]; window.__rule = [];
          setInterval(() => { if (window.__xs.length) window.__rule.push([p.x, window.__xs[window.__xs.length - 1][1]]); }, 37); }""", me)
    run.evaluate("window.__run = true")
    run.wait_for_function("Math.abs(mine.x) >= 4.7", timeout=10000)
    watch.wait_for_function("window.__xs.length >= 200", timeout=30000)
    glides(watch)
    if run is not host:
        rule = host.evaluate("window.__rule")
        ahead = [abs(kept) - abs(drawn) for kept, drawn in rule if 1.5 < abs(drawn) and abs(kept) < 4.2]
        assert len(ahead) > 15, rule
        # The newest spot, not the drawn one: ahead mostly, by about the drawing's delay at 2.5 m/s (less
        # while a late message has the drawing run on at the last speed).
        assert sum(a > 0 for a in ahead) > 0.75 * len(ahead) and mean(ahead) > 0.05, ahead
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


def test_a_friend_running_glides_on_the_host(site, browser):
    host, guest = phones(site, browser)
    run_and_watch(host, guest, host, others=[guest])


def test_the_host_running_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    run_and_watch(host, host, guest, others=[guest])


def test_a_friend_running_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on with the friend's own clock, so a third phone draws them as smoothly."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(JITTER)
    run_and_watch(host, aino, ville, others=[aino, ville])


def test_a_new_rally_puts_a_friend_on_their_spot_at_once(site, browser):
    """At a new rally the host puts everyone on their serving spot. A spot the friend's phone sent before it heard of
    the rally must not pull them back there and slide them in again: from the rally's first frame the host draws
    them on their spot."""
    host, guest = phones(site, browser)
    me = index(guest)
    # Every spot 120 ms on the way, so the ones sent just before the guest hears of the rally reach the host after it.
    guest.evaluate("""() => { const send = AiPelitRooms.send.bind(AiPelitRooms);
      AiPelitRooms.send = (m, to) => setTimeout(() => send(m, to), 120); }""")
    # Off the serving spot (2.2 m), running until the point ends: their spots sent just before they hear of it are
    # still on the way.
    guest.evaluate("setInterval(() => { if (state === 'point') window.__run = false; }, 4); window.__run = true")
    host.wait_for_function(f"Math.abs(players[{me}].x) > 3.6 && players[{me}].tr.size() > 3", timeout=5000)
    host.evaluate("""(i) => { window.__xs = []; const d = window.draw;
      window.draw = () => { if (state === 'serve' && window.__xs.length < 40) window.__xs.push(players[i].x); d(); };
      server = mine; state = 'point'; pauseT = 0.4; msg = null; }""", me)
    host.wait_for_function("window.__xs.length >= 40", timeout=5000)
    xs = host.evaluate("window.__xs")
    assert all(abs(abs(v) - 2.2) < 0.05 for v in xs), [round(v, 2) for v in xs if abs(abs(v) - 2.2) >= 0.05]
    assert not host.errors + guest.errors


def test_a_new_rally_puts_everyone_on_their_spot_at_once_on_a_third_phone(site, browser):
    """A guest that only watches starts every track again at the new rally, so the host, the friend and the
    computer's player are drawn on their serving spots from its first frame, and nobody slides there."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = index(aino)
    aino.evaluate("""() => { const send = AiPelitRooms.send.bind(AiPelitRooms);
      AiPelitRooms.send = (m, to) => setTimeout(() => send(m, to), 120); }""")
    aino.evaluate("setInterval(() => { if (state === 'point') window.__run = false; }, 4); window.__run = true")
    ville.wait_for_function(f"Math.abs(players[{me}].x) > 3.6", timeout=5000)
    ville.evaluate("""() => { window.__seen = []; let was = state; const d = window.draw;
      window.draw = () => { if (state === 'serve' && was !== 'serve') window.__on = true; was = state;
        if (window.__on && window.__seen.length < 30) window.__seen.push(players.map(p => p.x)); d(); }; }""")
    host.evaluate("""() => { window.__spots = null; const nr = window.newRally;
      window.newRally = () => { nr(); window.__spots = players.map(p => p.x); };
      server = mine; state = 'point'; pauseT = 0.4; msg = null; }""")
    ville.wait_for_function("window.__seen.length >= 30", timeout=5000)
    spots, seen = host.evaluate("window.__spots"), ville.evaluate("window.__seen")
    mine = index(ville)
    for frame in seen:
        off = [(i, round(x, 2), spots[i]) for i, x in enumerate(frame) if i != mine and abs(x - spots[i]) > 0.05]
        assert not off, (off, seen)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# On a phone: each time a message changes whose clock player `i`'s spot carries (the computer took over a friend,
# or gave them back), the spot it brought and where the next frame drew them.
SWITCH = """(i) => { window.__sw = []; const p = players[i]; let src = p.src, want = null; const d = window.draw;
  AiPelitRooms.on('message', m => { if (m.t !== 's' || p.src === src) return; src = p.src; want = [src, m.p[i][0]]; });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, p.x]); want = null; } }; }"""


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-match: the host's computer plays for them, so their row carries the host's clock
    and no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again
    at each change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = index(aino)
    aino.evaluate("window.__run = true")
    ville.wait_for_function(f"players[{me}].src === 'f' && Math.abs(players[{me}].x) > 3", timeout=5000)
    ville.evaluate(SWITCH, me)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"players[{me}].kind === 'cpu'")
    ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
    host.relay.back(aino)
    host.wait_for_function(f"players[{me}].kind === 'remote' && players[{me}].ts !== null", timeout=20000)
    ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
    sw = ville.evaluate("window.__sw")
    assert [s[0] for s in sw][:2] == ["h", "f"], sw
    assert all(abs(drawn - said) < 0.01 for _, said, drawn in sw), sw
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_the_host_takes_a_friends_spots_from_the_matchs_first_moment(site, browser):
    """A guest that hears the match start marks its first spot (j), so the host does not wait out the half second
    it drops spots for after a new rally: the friend moves on the host from the match's first moment."""
    site.build(ROOT / "games")
    relay, pages = Relay(), []
    for name in ("Testi A", "Testi B"):
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
    host, guest = pages
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    # The guest runs from the moment it hears the match; the host notes each friend's spot it takes, and when.
    guest.evaluate(RUN.replace("window.__run = false", "window.__run = true"))
    host.evaluate("""() => { window.__took = [];
      AiPelitRooms.on('message', (m, from) => { if (m.t !== 'p') return; const p = players.find(q => q.id === from);
        if (p) setTimeout(() => window.__took.push([state, stateT, p.x === m.x]), 0); }); }""")
    host.click("#aipr-start")
    host.wait_for_function("window.__took.length >= 12", timeout=10000)
    took = host.evaluate("window.__took")
    early = [t for t in took if t[0] == "serve" and t[1] < 0.5]
    assert early, took
    assert all(t[2] for t in early), took
    assert not host.errors + guest.errors
