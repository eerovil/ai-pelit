"""Jalkapallo v5 (#480): on a guest, the other players glide across the pitch, drawn from lib/sulava-1 between
the spots the host sends, instead of chasing each newest spot (v4). The host runs the whole match (the rules, the
ball, every player), so its own screen draws its own simulation as before; a guest keeps the newest spot in
p.tx, p.ty and draws p.x, p.y a moment back. The player a guest steers itself still chases the newest spot."""

import json
from statistics import mean, pstdev

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/jalkapallo/v5/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# On the host: the computer's players stand still, except player `window.__cpuRun` while `window.__run` is on,
# which runs along the pitch at 5 m/s until x = 10. Everyone is put out of the way of the runner's lane (y = -5)
# and the ball lies still in a far corner, so nobody plays it.
QUIET = """() => { window.__run = false; window.__cpuRun = -1;
  window.cpuThink = p => { const go = window.__run && players.indexOf(p) === window.__cpuRun && p.x < 10;
    p.vx = go ? 5 : 0; p.vy = 0; };
  state = 'play'; owner = null; Object.assign(ball, { x: 13, y: 20, z: 0, vx: 0, vy: 0, vz: 0 });
  players.forEach((p, i) => { p.x = -12 + i * 4.5; p.y = 12; p.vx = p.vy = 0; });
  for (const k of ctrls) { k.switchT = 999; if (k.fixed < 0) k.p = players[k.t * 3]; } }"""
# Records, each frame, where player `i` is drawn across the pitch, and when a message arrived (so a stall of the
# test machine, with no message for a while, can be told from a jerk). The time is taken as the frame's update()
# starts, where guestUpdate() asks the track for the spot: taken later, in draw(), a frame whose work in between
# ran long on a busy machine read as a jerk (#498). Times are the machine's clock (timeOrigin + now), the same on
# every page.
SAMPLE = """(i) => { window.__xs = []; window.__got = []; const now = () => (performance.timeOrigin + performance.now()) / 1000;
  AiPelitRooms.on('message', () => window.__got.push(now()));
  const u = window.update;
  window.update = dt => { const t = now(); u(dt); if (window.__xs.length < 300) window.__xs.push([t, players[i].x]); }; }"""
# On the host: when a frame came late. The host runs at most 50 ms of the match per frame, so a busy test machine
# slows the match itself there, and every phone rightly draws it slower: such moments are left out.
STALLS = """() => { window.__stall = []; let last = 0; const d = window.draw;
  window.draw = () => { const t = (performance.timeOrigin + performance.now()) / 1000;
    if (last && t - last > 0.08) window.__stall.push(t); last = t; d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the match on. Room order puts the 1st and 3rd phone in team 0 (with two phones there,
    each steers its own player: 0 and 1), the 2nd in team 1."""
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
        # Joined one at a time, so the room order is the order of `names`.
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {pages.index(g) + 1}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("players.length === 6 && (state === 'kickoff' || state === 'play')", timeout=10000)
    host.relay = relay
    return pages


def glides(page, host):
    """The speed over each two drawn frames while the player ran: always the same way and about the same."""
    xs, got = page.evaluate("[window.__xs, window.__got]")
    stalls = host.evaluate("window.__stall")
    # Only frames that came in time on the watching page itself (both gaps under 40 ms, a 60 Hz frame is 17): a
    # frame late on a busy test machine and the quick one after it measure the machine, not the drawing. Measured
    # (#498): around such a spike the drawn moment (tr.time) went on evenly at 6.3 m/s; only the page's frames
    # were uneven.
    sp = [(t2, (b - a) / (t2 - t0)) for (t0, a), (t1, _), (t2, b) in zip(xs, xs[1:], xs[2:])
          if t2 > t0 and t1 - t0 < 0.04 and t2 - t1 < 0.04]
    moving = [i for i, (_, v) in enumerate(sp) if abs(v) > 0.5]
    assert len(moving) > 50, len(moving)
    # Leave out the start and the stop: the drawing speeds up and slows down there over a moment.
    t0, t1 = sp[moving[0]][0] + 0.15, sp[moving[-1]][0] - 0.3
    middle = [(t, v) for t, v in sp if t0 <= t <= t1]
    assert len(middle) > 30, len(middle)

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got) and not any(s <= t <= s + 0.35 for s in stalls)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 30, (len(kept), len(middle), len(stalls))
    assert min(kept) > 0, shown  # never backwards
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.2 * m, (sd, m, shown)
    # Hardly a frame at twice the speed or under half of it. One in fifty may be: under a 10x CPU throttle the
    # watching page now and then ran a frame's work late (a pause between the frame's start and its track
    # lookup), so one frame read up to 1.75x (2x in a loaded verification run) while the drawn moment went on
    # evenly, at most 1.25x (#498). Without the
    # smoothing, the spread above fails by far (sd 2.0-2.9 against a mean of 5-6.4).
    odd = [v for v in kept if not 0.5 * m < v < 1.8 * m]
    assert len(odd) <= max(1, len(kept) // 50), (odd, m, shown)


def watch_run(host, watch, i, start):
    """Player `i` runs along y = -5 from x = -10; `start()` sets them going. `watch` must draw them gliding."""
    host.evaluate(QUIET)
    host.evaluate(f"players[{i}].x = -10; players[{i}].y = -5")
    watch.wait_for_function(f"Math.abs(players[{i}].x + 10) < 0.05 && players[{i}].tr.size() > 3", timeout=5000)
    host.evaluate(JITTER)
    watch.evaluate(SAMPLE, i)
    host.evaluate(STALLS)
    start()
    host.wait_for_function(f"players[{i}].x >= 9", timeout=10000)
    watch.wait_for_function("window.__xs.length >= 200", timeout=30000)
    glides(watch, host)


def test_a_computer_player_running_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    host.evaluate(QUIET)
    watch_run(host, guest, 4, lambda: host.evaluate("window.__cpuRun = 4; window.__run = true"))
    assert not host.errors + guest.errors


def test_the_host_running_glides_on_a_guest(site, browser):
    """The host steers player 0 with its own joystick."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate("setInterval(() => { input.jx = players[0].x < 10 && window.__go ? 1 : 0; input.jy = 0; }, 5)")
    watch_run(host, aino, 0, lambda: host.evaluate("window.__go = true"))
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_friend_running_glides_on_a_third_phone(site, browser):
    """Ville steers player 1 with his joystick through the host; Aino draws them from the host's jittered spots."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    ville.evaluate("setInterval(() => { input.jx = players[1].tx < 10 && window.__go ? 1 : 0; input.jy = 0; }, 5)")
    watch_run(host, aino, 1, lambda: ville.evaluate("window.__go = true"))
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_guest_draws_its_own_player_at_the_newest_spot(site, browser):
    """The player a guest steers is not drawn from the track: it chases the newest spot the host sent, as in v4."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    ville.evaluate("setInterval(() => { input.jx = players[1].tx < 10 && window.__go ? 1 : 0; input.jy = 0; }, 5)")
    host.evaluate(QUIET)
    host.evaluate("players[1].x = -10; players[1].y = -5")
    ville.wait_for_function("Math.abs(players[1].x + 10) < 0.05 && players[1].tr.size() > 3", timeout=5000)
    host.evaluate(JITTER)
    ville.evaluate("""() => { window.__d = []; const d = window.draw; window.draw = () => { const p = players[1];
      if (p.tx > -7 && p.tx < 7) window.__d.push([p.x, p.tr.at().x]); d(); }; }""")
    ville.evaluate("window.__go = true")
    host.wait_for_function("players[1].x >= 9", timeout=10000)
    d = ville.evaluate("window.__d")
    assert len(d) > 30, d
    # Not the track's spot (that would be 0 all along). Measured: on average it is drawn about as far back as
    # the track would draw it, so the chase costs no time, but it is kept as v4 had it.
    off = [abs(drawn - track) for drawn, track in d]
    assert mean(off) > 0.05, [round(a, 2) for a in off]
    assert not host.errors + aino.errors + ville.errors


def test_a_friends_held_ball_is_drawn_at_their_feet(site, browser):
    """The host's ball sits just in front of the player who has it. A guest draws that player a moment back, and
    the ball with them, not at its newest spot ahead of them."""
    host, guest, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    host.evaluate("players[2].x = -10; players[2].y = -5; ball.x = -9.2; ball.y = -5; take(players[2]); players[2].fx = 1; players[2].fy = 0")
    guest.wait_for_function("owner === players[2] && Math.abs(players[2].x + 10) < 0.05", timeout=5000)
    guest.evaluate("""() => { window.__f = []; const d = window.draw; window.draw = () => { const p = players[2];
      if (owner === p && p.tx > -7 && p.tx < 7) window.__f.push([ball.x - p.x, ball.nx - p.tx, p.tx - p.x]); d(); }; }""")
    host.evaluate("window.__cpuRun = 2; window.__run = true")
    host.wait_for_function("players[2].x >= 9", timeout=10000)
    f = guest.evaluate("window.__f")
    assert len(f) > 30, f
    # The player is drawn back by about the drawing's delay at 5 m/s, the ball held where the host has it.
    assert mean(lag for _, _, lag in f) > 0.1, f
    assert all(abs(drawn - said) < 0.1 for drawn, said, _ in f), [(round(a, 2), round(b, 2)) for a, b, _ in f]
    assert not host.errors + guest.errors + ville.errors


def test_a_kickoff_puts_everyone_on_their_spot_at_once_on_the_guests(site, browser):
    """After a goal the host puts everyone on their kickoff spot. Every guest starts each track again there, so
    from the kickoff's first frame everyone else is drawn on their spot, and nobody slides there."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    # Everyone 1.5 m off their kickoff spot, under the track's jump (4 m): a glide there would show.
    host.evaluate("""() => { kickoff(1); for (const p of players) p.x += 1.5; state = 'play'; owner = null;
      Object.assign(ball, { x: 13, y: 20, z: 0, vx: 0, vy: 0, vz: 0 }); window.__off = players.map(p => p.x); }""")
    for g in (aino, ville):
        g.wait_for_function("players.every((p, i) => Math.abs(p.tx - window.__off[i]) < 0.01 && p.tr.size() > 3)"
                            .replace("window.__off", json.dumps(host.evaluate("window.__off"))), timeout=5000)
        g.evaluate("""() => { window.__seen = []; let was = state; const d = window.draw;
          window.draw = () => { if (state === 'kickoff' && was !== 'kickoff') window.__on = true; was = state;
            if (window.__on && window.__seen.length < 30) window.__seen.push(players.map(p => [p.x, p.y])); d(); }; }""")
    host.evaluate("""() => { window.__spots = null; const ko = window.kickoff;
      window.kickoff = t => { ko(t); window.__spots = players.map(p => [p.x, p.y]); };
      msg = { s: 'MAALI!', t: 0 }; state = 'goal'; pauseT = 0.3; }""")
    for g in (aino, ville):
        g.wait_for_function("window.__seen.length >= 30", timeout=5000)
    spots = host.evaluate("window.__spots")
    for g in (aino, ville):
        seen, mine = g.evaluate("window.__seen"), g.evaluate("players.indexOf(myPlayer())")
        for frame in seen:
            off = [(i, x, y, spots[i]) for i, (x, y) in enumerate(frame)
                   if i != mine and (abs(x - spots[i][0]) > 0.05 or abs(y - spots[i][1]) > 0.05)]
            assert not off, (off, seen)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_guest_draws_everyone_on_their_spot_from_the_matchs_first_moment(site, browser):
    """A guest's players are made at the centre spot when the host's setup comes; the first spot heard starts
    each track there, so nobody slides out from the centre (v4 did)."""
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
    guest.evaluate("""() => { window.__seen = []; const d = window.draw;
      window.draw = () => { if (players.length && players[0].tx !== undefined && window.__seen.length < 20)
        window.__seen.push(players.map(p => [p.x, p.y, p.tx, p.ty])); d(); }; }""")
    host.click("#aipr-start")
    guest.wait_for_function("window.__seen.length >= 20", timeout=10000)
    first = guest.evaluate("window.__seen")[0]
    # At the kickoff nobody but the kicker moves; each is drawn where the host said.
    off = [(i, q) for i, q in enumerate(first) if abs(q[0] - q[2]) > 0.05 or abs(q[1] - q[3]) > 0.05]
    assert not off, first
    assert not host.errors + guest.errors


def test_a_friend_taken_over_by_the_computer_and_given_back_keeps_gliding_on_a_third_phone(site, browser):
    """Ville's phone drops mid-match: the host's computer plays his player, and when the phone is back, Ville
    again. The host runs the player all along on one clock, so a third phone's track goes on without a jump:
    the player runs on smoothly under the computer, and is drawn where the host says once they stop."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    host.evaluate("players[1].x = -10; players[1].y = -5")
    aino.wait_for_function("Math.abs(players[1].x + 10) < 0.05 && players[1].ctl !== ''", timeout=5000)
    host.relay.drop(ville)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function("ctrls.find(k => k.fixed === 1).away")
    aino.wait_for_function("players[1].ctl === ''", timeout=5000)
    host.evaluate(JITTER)
    aino.evaluate(SAMPLE, 1)
    host.evaluate(STALLS)
    host.evaluate("window.__cpuRun = 1; window.__run = true")
    host.wait_for_function("players[1].x >= 9", timeout=10000)
    aino.wait_for_function("window.__xs.length >= 200", timeout=30000)
    glides(aino, host)
    host.relay.back(ville)
    host.wait_for_function("!ctrls.find(k => k.fixed === 1).away", timeout=20000)
    aino.wait_for_function("players[1].ctl !== ''", timeout=5000)
    aino.wait_for_function("Math.abs(players[1].x - players[1].tx) < 0.01 && players[1].tx >= 9", timeout=5000)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors
