"""Jalkapallo v5 (#480): on a guest, the other players glide across the pitch, drawn from lib/sulava-1 between
the spots the host sends, instead of chasing each newest spot (v4). The host runs the whole match (the rules, the
ball, every player), so its own screen draws its own simulation as before; a guest keeps the newest spot in
p.tx, p.ty and draws p.x, p.y a moment back. The player a guest steers itself still chases the newest spot."""

import json
import math
from statistics import mean, pstdev

import pytest

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
# every page. Called again, it starts a new record of player `i`.
SAMPLE = """(i) => { window.__xs = []; window.__got = []; window.__si = i; if (window.__sampling) return; window.__sampling = true;
  const now = () => (performance.timeOrigin + performance.now()) / 1000;
  let ck = null; AiPelitRooms.on('message', m => { window.__got.push(now()); if (m.t === 's') ck = m.ck; });
  const u = window.update;
  window.update = dt => { const t = now(); u(dt); if (window.__xs.length < 300) { const p = players[window.__si]; window.__xs.push([t, p.x, p.tr.time, ck]); } }; }"""
# On the host: when a frame came late. The host runs at most 50 ms of the match per frame, so a busy test machine
# slows the match itself there, and every phone rightly draws it slower: such moments are left out.
STALLS = """() => { window.__stall = []; if (window.__stalls) return; window.__stalls = true; let last = 0; const d = window.draw;
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
    sp = [(t2, (b - a) / (t2 - t0)) for (t0, a, *_), (t1, *_), (t2, b, *_) in zip(xs, xs[1:], xs[2:])
          if t2 > t0 and t1 - t0 < 0.04 and t2 - t1 < 0.04]
    # For a failure's message: per frame, the speed per drawn moment and whether it was drawn past the newest
    # spot heard (a guess).
    why = {t2: (round((b - a) / (d2 - d0), 2) if d0 is not None and d2 is not None and d2 > d0 else None,
                d2 is not None and c2 is not None and d2 > c2)
           for (t0, a, d0, _), (t2, b, d2, c2) in zip(xs, xs[2:])}
    # Judged by time, not by a count of frames: a busy test machine draws fewer of them, and fewer in time (#498:
    # 40 moving frames at load 105-115, where 50 were asked for). The run is 20 m at 5-6.3 m/s, over 3 s.
    moving = [i for i, (_, v) in enumerate(sp) if abs(v) > 0.5]
    assert moving and sp[moving[-1]][0] - sp[moving[0]][0] > 2.0, (len(moving), len(sp))
    # Leave out the start and the stop: the drawing speeds up and slows down there over a moment.
    t0, t1 = sp[moving[0]][0] + 0.15, sp[moving[-1]][0] - 0.3
    middle = [(t, v) for t, v in sp if t0 <= t <= t1]
    assert len(middle) >= 10, len(middle)

    # And only frames drawn between two spots heard, and not just after: when the spots come late (a busy test
    # machine), the track draws on a guess past the newest and then draws the difference away (lib/sulava-1's
    # `extra`), which is uneven by design. Measured at load 45-60: guessed frames down to 0.13x, 2.2x around
    # them. Without the smoothing nothing is drawn from the track and every frame is judged.
    guessed = [t for t, (_, g) in why.items() if g]

    def heard(t):
        return (any(t - 0.3 <= g <= t for g in got) and not any(s <= t <= s + 0.35 for s in stalls)
                and not any(g <= t <= g + 0.15 for g in guessed))
    kept = [v for t, v in middle if heard(t)]
    odd_why = [(round(v, 2), why.get(t)) for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) >= max(10, len(middle) // 4), (len(kept), len(middle), len(stalls))
    assert min(kept) > 0, shown  # never backwards
    m, sd = mean(kept), pstdev(kept)
    # The spread: under 0.33 of the mean. Without the smoothing it was 0.41-0.45 (sd 2.0-2.9 against 5-6.4);
    # with it 0.05 on a quiet machine, but up to 0.28 with three pages on a machine at load 65-72, where the
    # frames' own timing (not the drawing) spreads it.
    assert sd < 0.33 * m, (sd, m, shown, [w for w in odd_why if not 0.5 * m < w[0] < 1.8 * m])
    # Hardly a frame at twice the speed or under half of it. One in fifty may be: under a 10x CPU throttle the
    # watching page now and then ran a frame's work late (a pause between the frame's start and its track
    # lookup), so one frame read up to 1.75x (2x in a loaded verification run) while the drawn moment went on
    # evenly, at most 1.25x (#498).
    odd = [v for v in kept if not 0.5 * m < v < 1.8 * m]
    assert len(odd) <= max(1, len(kept) // 50), (odd, m, [w for w in odd_why if not 0.5 * m < w[0] < 1.8 * m], shown)


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


def test_a_dash_after_a_long_gap_in_the_messages_glides_on_a_guest(site, browser):
    """A player dashes at 10 m/s (the top speed) and no word comes from the host for 0.4 s, so the two spots on each
    side of the gap are 4.5 m apart. That is a gap in the messages, not the host putting them somewhere new: the
    guest goes on drawing them gliding, not in one step to the newest spot."""
    host, guest = phones(site, browser)
    host.evaluate(QUIET)
    host.evaluate("players[4].x = -13; players[4].y = -5")
    guest.wait_for_function("Math.abs(players[4].x + 13) < 0.05 && players[4].tr.size() > 3", timeout=5000)
    host.evaluate(STALLS)
    host.evaluate("""() => { const u = window.update;
      window.update = dt => { u(dt); if (window.__dash && players[4].x < 13) players[4].x += 10 * Math.min(dt, 0.05); };
      const send = AiPelitRooms.send.bind(AiPelitRooms);
      AiPelitRooms.send = (m, to) => { if (m.t === 's' && window.__gap) return; send(m, to); }; }""")
    guest.evaluate("""() => { window.__d = []; const now = () => (performance.timeOrigin + performance.now()) / 1000;
      const u = window.update; window.update = dt => { const t = now(); u(dt); window.__d.push([t, players[4].x]); }; }""")
    host.evaluate("window.__dash = true")
    host.wait_for_function("players[4].x > -4", timeout=5000)
    gap = host.evaluate("""() => { window.__gap = true; const t = (performance.timeOrigin + performance.now()) / 1000;
      setTimeout(() => { window.__gap = false; }, 400); return t; }""")
    host.wait_for_function("players[4].x >= 13", timeout=10000)
    guest.wait_for_timeout(500)
    d, stalls = guest.evaluate("window.__d"), host.evaluate("window.__stall")
    # Every frame from just before the gap to well after it: a step of a frame (17 ms at 10 m/s is 0.17 m), never
    # back and never a jump. Measured (#480): at most 0.33 m; with the track's own 4 m jump it was a 2.17 m step.
    near = [(round(t1 - gap, 3), round(b - a, 2)) for (t0, a), (t1, b) in zip(d, d[1:])
            if gap - 0.2 <= t1 <= gap + 1.0 and t1 - t0 < 0.04 and not any(s <= t1 <= s + 0.35 for s in stalls)]
    assert len(near) > 20, near
    assert all(-0.05 < step < 0.6 for _, step in near), near
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
    host.evaluate(STALLS)
    # Per frame: the ball from the drawn player, from the newest spot, the player's lag behind it, the machine's
    # time, the moment drawn and the newest stamp heard.
    guest.evaluate("""() => { window.__f = []; let ck = null; AiPelitRooms.on('message', m => { if (m.t === 's') ck = m.ck; });
      const d = window.draw; window.draw = () => { const p = players[2];
      if (owner === p && p.tx > -7 && p.tx < 7) window.__f.push([ball.x - p.x, ball.tx - p.tx, p.tx - p.x,
        (performance.timeOrigin + performance.now()) / 1000, p.tr.time, ck]); d(); }; }""")
    host.evaluate("window.__cpuRun = 2; window.__run = true")
    host.wait_for_function("players[2].x >= 9", timeout=10000)
    f, stalls = guest.evaluate("window.__f"), host.evaluate("window.__stall")
    assert len(f) > 30, f
    # The ball held where the host has it, in every frame.
    assert all(abs(drawn - said) < 0.1 for drawn, said, *_ in f), [(round(a, 2), round(b, 2)) for a, b, *_ in f]
    # The player is drawn back by about the drawing's delay at 5 m/s. Judged only where the host ran the match in
    # time and the moment drawn is not past the newest spot: at load 75-95 the mean lag over every frame was -0.43 m
    # and 0.06 m (#498), likely as the host stood still in its late frames while the guest drew on a guess past it.
    lags = [lag for _, _, lag, t, d, c in f if d is not None and c is not None and d <= c
            and not any(st <= t <= st + 0.35 for st in stalls)]
    assert len(lags) >= max(5, len(f) // 4), (len(lags), len(f), len(stalls))
    assert mean(lags) > 0.1, (lags, f)
    assert not host.errors + guest.errors + ville.errors


@pytest.mark.parametrize("what", ["shot", "pass"])
def test_a_guests_own_kick_leaves_its_feet_at_once_on_that_guest(site, browser, what):
    """A guest's own player runs up the pitch with the ball and shoots or passes it on. On that guest's phone the
    ball leaves from where it was drawn, at the player's feet, as soon as the host's word of the kick comes, and
    flies where the host has it, not the drawing's delay behind (the phone's own actions are not delayed)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    host.evaluate("""() => { const p = players[1]; p.x = -3; p.y = -15; p.fx = 0; p.fy = 1;
      players[0].x = 3; players[0].y = 2; ball.x = -3; ball.y = -14.2; take(p); }""")
    ville.wait_for_function("owner === players[1] && players[1].ctl === AiPelitRooms.me && players[1].tr.size() > 3",
                            timeout=5000)
    host.evaluate(JITTER)
    host.evaluate(STALLS)
    # Per frame, on both: the machine's time (the same on every page), the ball, the kicker's kicks.
    rec_js = """window.__k = []; const now = () => (performance.timeOrigin + performance.now()) / 1000;
      const u = window.update; window.update = dt => { const t = now(); u(dt);
        if (window.__k.length < 400) window.__k.push([t, ball.x, ball.y, players[1].kicks]); };"""
    host.evaluate("() => { " + rec_js + " }")
    ville.evaluate("() => { " + rec_js + """
      setInterval(() => { input.jx = 0; input.jy = window.__go ? view : 0; }, 5); window.__go = true; }""")
    ville.wait_for_function("players[1].ty > -8", timeout=5000)
    k0 = ville.evaluate("players[1].kicks")
    if what == "shot":
        ville.evaluate("act('shootDown'); act('shootUp', 0.6)")
    else:
        ville.evaluate("act('pass')")
    ville.wait_for_function(f"players[1].kicks > {k0}", timeout=5000)
    ville.wait_for_timeout(600)
    rec, stalls, on_host = ville.evaluate("window.__k"), host.evaluate("window.__stall"), host.evaluate("window.__k")
    i = next(i for i, f in enumerate(rec) if f[3] > k0)
    t_h, y0 = rec[i][0], rec[i - 1][2]
    # The ball goes up the pitch from the frame the kick is heard: never back down it (a held ball sits 0.8 m in
    # front of the player's feet), and 0.1 s on it is over 1 m on its way (a pass goes at 7-17 m/s, the shot at
    # 22).
    after = [f for f in rec[i - 1:] if f[0] <= t_h + 0.4]
    back = [(round(b[0] - t_h, 3), round(b[2] - a[2], 2)) for a, b in zip(after, after[1:]) if b[2] - a[2] < -0.05]
    assert not back, (back, [(round(f[0] - t_h, 3), round(f[2], 2)) for f in after])
    late = next(f for f in rec if f[0] >= t_h + 0.1)
    assert late[2] - y0 > 1.0, (round(late[0] - t_h, 3), late[2] - y0, [(round(f[0] - t_h, 3), round(f[2], 2)) for f in after])
    # And from 0.15 s (the step from the feet faded out) to 0.3 s it is drawn about where the host has it at the
    # same moment, the message's way behind, not the track's delay more.

    def host_y(t):
        for a, b in zip(on_host, on_host[1:]):
            if a[0] <= t <= b[0]:
                return a[2] + (b[2] - a[2]) * (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else a[2]
    lead = [(round(f[0] - t_h, 3), round(host_y(f[0]) - f[2], 2)) for f in rec
            if t_h + 0.15 <= f[0] <= t_h + 0.3 and host_y(f[0]) is not None
            and not any(s <= f[0] <= s + 0.35 for s in stalls)]
    # Measured (#480): 0.06-0.39 m behind the host; drawn from the track, the shot was 2.8 m and the pass 1.1 m
    # behind all along.
    assert lead and all(abs(d) < 0.8 for _, d in lead), lead
    assert not host.errors + aino.errors + ville.errors


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
            if (window.__on && window.__seen.length < 30) window.__seen.push(players.map(p => [p.x, p.y]).concat([[ball.x, ball.y]]));
            d(); }; }""")
    host.evaluate("""() => { window.__spots = null; const ko = window.kickoff;
      window.kickoff = t => { ko(t); window.__spots = players.map(p => [p.x, p.y]); };
      msg = { s: 'MAALI!', t: 0 }; state = 'goal'; pauseT = 0.3; }""")
    for g in (aino, ville):
        g.wait_for_function("window.__seen.length >= 30", timeout=5000)
    spots = host.evaluate("window.__spots")
    for g in (aino, ville):
        seen, mine = g.evaluate("window.__seen"), g.evaluate("players.indexOf(myPlayer())")
        for frame in seen:
            *frame, (bx, by) = frame
            off = [(i, x, y, spots[i]) for i, (x, y) in enumerate(frame)
                   if i != mine and (abs(x - spots[i][0]) > 0.05 or abs(y - spots[i][1]) > 0.05)]
            assert not off, (off, seen)
            # The ball too: from the corner it lay in (13, 20) straight to the centre spot, at the kicker's feet,
            # not sliding across the pitch.
            assert math.hypot(bx, by) < 1.5, (bx, by, seen)
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
    # Ville steers again: he runs his player along the lane once more, and the third phone draws it gliding.
    host.evaluate("window.__run = false; players[1].x = -10; players[1].y = -5")
    aino.wait_for_function("Math.abs(players[1].x + 10) < 0.05 && players[1].ctl !== ''", timeout=5000)
    ville.evaluate("setInterval(() => { input.jx = players[1].tx < 10 && window.__go ? 1 : 0; input.jy = 0; }, 5)")
    aino.evaluate(SAMPLE, 1)
    host.evaluate(STALLS)
    ville.evaluate("window.__go = true")
    host.wait_for_function("players[1].x >= 9", timeout=10000)
    aino.wait_for_function("window.__xs.length >= 200", timeout=30000)
    glides(aino, host)
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# On a guest, each frame: [the frame's time (as in SAMPLE), the moment the first of `ids` is drawn at (its track's,
# on the host's clock), ball x, ball y, the newest holder's index, x, y of the two players in `ids`, the host's
# clock on the newest spot heard, and the moment the ball is drawn at (the first player's on v5 before #498's
# review, which had no ball track)].
BALL = """(ids) => { window.__b = []; const now = () => (performance.timeOrigin + performance.now()) / 1000;
  let ck = null; AiPelitRooms.on('message', m => { if (m.t === 's') ck = m.ck; });
  const u = window.update;
  window.update = dt => { const t = now(); u(dt); if (window.__b.length < 400) window.__b.push([t, players[ids[0]].tr.time,
    ball.x, ball.y, players.indexOf(owner)].concat(...ids.map(i => [players[i].x, players[i].y]), [ck, (ball.tr || players[ids[0]].tr).time])); }; }"""


def test_a_tackle_moves_the_ball_to_the_tackler_without_a_step(site, browser):
    """A computer player of team 0 runs with the ball at 5 m/s; one of team 1, standing by its lane, takes it
    (the host's take(), as a tackle or a steal does). On the host the ball rolls to the taker's feet in a few
    frames; on a guest it must not jump there in one, neither on a third phone (Ville: both drawn from tracks) nor
    on the phone the taker's team is steered from (Aino: the taker becomes her player, drawn ahead of the tracks)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    host.evaluate("""() => { const p = players[2], q = players[4];
      p.x = -8; p.y = -5; p.fx = 1; p.fy = 0; ball.x = -7.2; ball.y = -5; take(p);
      q.x = 1.6; q.y = -6.4; q.fx = 0; q.fy = 1; }""")
    for g in (aino, ville):
        g.wait_for_function("owner === players[2] && Math.abs(players[2].x + 8) < 0.05 && players[2].tr.size() > 3"
                            " && Math.hypot(ball.x + 7.18, ball.y + 5) < 0.1", timeout=5000)
    host.evaluate(JITTER)
    host.evaluate("""() => { const u = window.update; window.update = dt => { u(dt);
      if (!window.__stole && owner === players[2] && players[2].x > 0) { window.__stole = true; take(players[4]); } }; }""")
    for g in (aino, ville):
        g.evaluate(BALL, [2, 4])
    host.evaluate("window.__cpuRun = 2; window.__run = true")
    for g in (aino, ville):
        g.wait_for_function("owner === players[4]", timeout=10000)
        g.wait_for_function("window.__b.length >= 400", timeout=20000)
    for g, name in ((aino, "Aino"), (ville, "Ville")):
        rec = g.evaluate("window.__b")
        took = next(i for i, r in enumerate(rec) if r[4] == 4)
        # The ball's speed over each frame around the take, per moment drawn (the ball track's; a busy test
        # machine's uneven frames do not show in it, see glides()).
        sp = [(i - took, math.hypot(b[2] - a[2], b[3] - a[3]) / (b[10] - a[10]))
              for i, (a, b) in enumerate(zip(rec, rec[1:]), 1)
              if took - 30 <= i <= took + 60 and a[10] is not None and b[10] is not None and b[10] - a[10] > 0.008]
        assert len(sp) > 40, (name, len(sp))
        # Dribbled at 5 m/s, then a metre or so over to the taker as the host rolls it there. Measured at load
        # 50-65: at most 18 m/s; v5 before the review jumped it there in one frame, 47-67 m/s.
        fast = [(i, round(v, 1)) for i, v in sp if v > 30]
        assert not fast, (name, fast, [round(v, 1) for _, v in sp])
        # And it ends at the taker's feet as drawn.
        bx, by, qx, qy = rec[-1][2], rec[-1][3], rec[-1][7], rec[-1][8]
        assert math.hypot(bx - qx, by - qy) < 1.0, (name, rec[-1])
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_a_pass_is_drawn_at_the_moment_the_players_are(site, browser):
    """A computer player passes along the lane at 10 m/s to Ville's player, standing 8 m on. Aino's phone draws
    the players a moment back, and the ball must be drawn at that same moment, where the host had it then: so it
    leaves the passer's feet as drawn and comes to the taker's. v5 before the review drew a loose ball at its
    newest spot, guessed on, so a kicked ball ran ahead of the kick."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(QUIET)
    host.evaluate("""() => { const p = players[2], q = players[1];
      p.x = -6; p.y = -5; p.fx = 1; p.fy = 0; ball.x = -5.2; ball.y = -5; take(p);
      q.x = 2; q.y = -5; q.fx = -1; q.fy = 0; }""")
    aino.wait_for_function("owner === players[2] && Math.abs(players[1].x - 2) < 0.05 && players[2].tr.size() > 3"
                           " && Math.hypot(ball.x + 5.18, ball.y + 5) < 0.1", timeout=5000)
    host.evaluate(JITTER)
    # On the host, each frame: [the clock its spots are stamped with (ck, netClock()), ball x, ball y].
    host.evaluate("""() => { window.__hb = []; const u = window.update;
      window.update = dt => { u(dt); window.__hb.push([netClock(), ball.x, ball.y]); }; }""")
    aino.evaluate(BALL, [2, 1])
    aino.wait_for_function("window.__b.length >= 30", timeout=5000)
    host.evaluate("release(players[2], 10, 0, 0, false)")
    aino.wait_for_function("owner === players[1]", timeout=10000)
    aino.wait_for_function("window.__b.length >= 150", timeout=10000)
    rec, hb = aino.evaluate("window.__b"), host.evaluate("window.__hb")

    def host_ball(t):
        for (t0, x0, y0), (t1, x1, y1) in zip(hb, hb[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        return None
    # While the ball is on its way (the host had it loose and past the passer's feet at the moment drawn), in
    # frames drawn between two spots heard: on a busy test machine the spots now and then come late, and the
    # drawing goes past the newest on a guess (sulava's `extra`), for the players as for the ball.
    # From 0.1 s after the kick: the host's ball stood, then went at 10 m/s, between two of its spots (0.05 s apart, or
    # more on a busy host), and a straight line between them sets the drawn ball off early by up to that much
    # (measured: 0.13 m, 0.41 m at load 40).
    kick = next(t for t, x, _ in hb if x > -5.17)

    def judged(r):
        return (r[1] is not None and r[9] is not None and kick + 0.1 <= r[1] <= r[9]
                and (h := host_ball(r[1])) and h[0] < 1 and h)
    off = []
    for r in rec:
        if hbx := judged(r):
            off.append(math.hypot(r[2] - hbx[0], r[3] - hbx[1]))
    # Enough of the flight judged, by time: the moments judged span at least half of the time the host had the ball
    # on its way (#498: 12 frames at load 105-115, where 20 were asked for; a busy machine draws fewer).
    way = [t for t, x, _ in hb if t >= kick + 0.1 and x < 1]
    seen = [r[1] for r in rec if judged(r)]
    assert len(off) >= 5 and way and max(seen) - min(seen) >= 0.5 * (way[-1] - way[0]), (
        len(off), seen and (min(seen), max(seen)), way and (way[0], way[-1]))
    # Measured with the ball on its own track: at most 0.13 m off. Drawn at its newest spot (v5 before the
    # review) it ran 0.6-1.2 m ahead.
    assert max(off) < 0.4, [round(d, 2) for d in off]
    bx, by, qx, qy = rec[-1][2], rec[-1][3], rec[-1][7], rec[-1][8]
    assert math.hypot(bx - qx, by - qy) < 1.0, rec[-1]
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# Fakes the room's pause (a phone away), which rooms.js sets: `window.__pz` on a phone is its AiPelitRooms.paused.
PAUSE = """() => { window.__pz = false;
  Object.defineProperty(AiPelitRooms, 'paused', { get: () => window.__pz, configurable: true }); }"""
# On a guest, each frame until `window.__pzStop`: [the frame's time (as in SAMPLE), player i's drawn x, the ball's,
# the moment player i is drawn at and the newest stamp on the tracks].
PZREC = """(i) => { window.__pr = []; const now = () => (performance.timeOrigin + performance.now()) / 1000;
  const u = window.update;
  window.update = dt => { const t = now(); u(dt); if (!window.__pzStop) window.__pr.push([t, players[i].x, ball.x, players[i].tr.time, (net.fed || []).slice(-1)[0]]); }; }"""


@pytest.mark.parametrize("first", ["host", "guest"])
def test_a_paused_match_goes_on_from_where_the_guest_drew_it(site, browser, first):
    """A computer player dribbles along the lane at 5 m/s and the room pauses for 0.7 s (a phone away). The host's
    match stands and sends nothing; the guest stands too, and when the match goes on, the player and the ball go
    on from where the guest drew them, at their speed: no step forward or back. The phones hear the pause 0.6 s
    apart and its end 0.1 s apart, in either order. Before the fix the tracks ran on the real clock: a guest that
    stopped first jumped over the host's last moments at the end, and one that stopped last had drawn on past the
    newest spot on a guess and slid back."""
    # Three phones, so player 2 is the computer's (with one phone on a team, it steers whoever has the ball).
    host, guest, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    for p in (host, guest, ville):
        p.evaluate(PAUSE)
    host.evaluate(QUIET)
    host.evaluate("""() => { const p = players[2]; p.x = -10; p.y = -5; p.fx = 1; p.fy = 0;
      ball.x = -9.2; ball.y = -5; take(p); }""")
    guest.wait_for_function("owner === players[2] && Math.abs(players[2].x + 10) < 0.05 && players[2].tr.size() > 3"
                            " && Math.abs(ball.x + 9.18) < 0.1", timeout=5000)
    host.evaluate(JITTER)
    host.evaluate(STALLS)
    guest.evaluate(PZREC, 2)
    host.evaluate("window.__cpuRun = 2; window.__run = true")
    guest.wait_for_timeout(1000)
    clock = "(performance.timeOrigin + performance.now()) / 1000"
    stop_host = lambda: [p.evaluate("window.__pz = true") for p in (host, ville)]
    stop_guest = lambda: guest.evaluate(f"window.__pzAt = {clock}; window.__pz = true")
    go_host = lambda: [p.evaluate("window.__pz = false") for p in (host, ville)]
    go_guest = lambda: guest.evaluate(f"window.__goAt = {clock}; window.__pz = false")
    order = [(stop_host, stop_guest), (go_host, go_guest)] if first == "host" else [(stop_guest, stop_host), (go_guest, go_host)]
    # The other phone hears the pause 0.6 s later and the end of it 0.1 s later: each phone has its own connection,
    # so the two pauses are not as long. 0.6 s is 12 of the host's spots, more than a track keeps (8).
    for (a, b), later in zip(order, (600, 100)):
        a()
        guest.wait_for_timeout(later)
        b()
        guest.wait_for_timeout(300)
    # Then 1.8 s more, so most of the 2 s in which a track still has lags from before the pause is judged too.
    guest.wait_for_timeout(1800)
    guest.evaluate("window.__pzStop = true")
    pr, pz_at, go_at = guest.evaluate("[window.__pr, window.__pzAt, window.__goAt]")
    stalls = host.evaluate("window.__stall")
    t_from = go_at - 1.5  # half a second before the first phone paused
    rec = [f for f in pr if f[0] >= t_from]
    assert rec and rec[-1][0] > go_at + 1.7, (t_from, go_at, rec[-1:])
    held = [f for f in rec if pz_at + 0.02 <= f[0] <= go_at]
    assert held and max(abs(f[1] - held[0][1]) for f in held) < 0.01, held[:3]  # it stood all through the pause
    # Each frame's step, against its time, from before the pause to the end, in both orders: about 5-6 m/s (1.2x while the drawing
    # catches up), never back. A long frame on a busy machine steps further, at the same speed: judged per second,
    # with 0.2 m to spare. Left out, as in glides(): a moment after a frame came late on the host, whose match then
    # stood, so the guest rightly drew a stop and a start (at load 75 the player stood 0.5 s mid-run after the pause,
    # likely such a stall: not proven). The guest's clock stops at the first frame or message after the pause
    # comes, so the first frame after it draws that time too: up to the frame gap around the pause's start (measured:
    # 0.05 s, 0.27 m, in a 17 ms frame).
    gap = next(b[0] - a[0] for a, b in zip(rec, rec[1:]) if b[0] >= pz_at)
    first_on = next(f[0] for f in rec if f[0] > go_at)
    bad = []
    for (t0, x0, b0, *_), (t1, x1, b1, *_) in zip(rec, rec[1:]):
        if any(st <= t1 <= st + 0.35 for st in stalls):
            continue
        took = t1 - t0 + (gap if t1 == first_on else 0)
        for what, d in (("player", x1 - x0), ("ball", b1 - b0)):
            if d < -0.1 or d > 0.2 + 7 * took:
                bad.append((what, round(t1 - go_at, 3), round(d, 2), round(t1 - t0, 3)))
    assert not bad, (bad, [(round(t - go_at, 3), round(x, 2), round(b, 2)) for t, x, b, *_ in rec])
    after = [f for f in rec if f[0] > go_at + 0.6]
    assert after[-1][1] > held[-1][1] + 1, (held[-1], after[-1])  # and it went on
    # And from 0.75 s after the resume the drawing is a moment behind the newest spot, between two spots heard, as
    # before the pause, not on a guess past it (lib/sulava-1 draws up to 0.25 s on), which steps from spot to spot.
    # Host first, the guest's clock ran on while the host's stood, and its tracks then drew past the newest spot for
    # up to 2 s (measured before the fix: 110 frames, the first 20 of them 0.28-0.43 s past it). With the fix the
    # guest's clock goes slower until the host's spots catch up: past them by 0.25 s at 0.3 s, 0.05 s at 0.52 s.
    # Past it by more than two spots' gap (0.1 s) counts: the bug drew 0.28-0.43 s past it, while under a full
    # suite's load the slowed clock was still 0.02-0.05 s past it at 0.86-0.93 s (job af1befa4a4cc), a frame's
    # worth of the library's own short guess.
    ahead = [(round(t - go_at, 2), round(d - c, 3)) for t, _, _, d, c in rec
             if t > go_at + 0.75 and d is not None and c is not None and d > c + 0.1
             and not any(st <= t <= st + 0.35 for st in stalls)]
    assert len(ahead) <= 3, ahead
    errors = [e for p in (host, guest, ville) for e in p.errors]
    assert not errors, errors


# On the host: while `window.__hold`, its snapshots wait (a stalled link); `window.__release()` sends them all.
HOLD = """() => { window.__hold = false; const q = []; const send = AiPelitRooms.send.bind(AiPelitRooms);
  AiPelitRooms.send = (m, to) => { if (m.t === 's' && window.__hold) { q.push([m, to]); return; } send(m, to); };
  window.__release = () => { for (const [m, to] of q.splice(0)) send(m, to); }; }"""


@pytest.mark.parametrize("ms", [False, True], ids=["chromium-clock", "whole-ms-clock"])
def test_spots_landing_in_a_guests_pause_after_a_stall_do_not_hop_the_drawing(site, browser, ms):
    """A computer player runs at 5 m/s when the link stalls for 0.5 s: the guest draws them on past the newest
    spot on a guess (lib/sulava-1 goes on 0.25 s, then stands), short of where they are. Then the room pauses on
    both phones and the stalled spots land. The guest's clock stands in a pause, and the track eases a correction
    only when its clock has moved on since the frame before: the drawing must still stand all through the pause,
    and after it ease onto the spots, not cover the gap in one frame. Also on a clock that counts whole
    milliseconds (Safari's and Firefox's). It holds because update() draws no track while paused, so the paused
    moment netClock() returns again after the pause is a frame later than the last drawn one (Areena v9 hopped
    where its drawing read the paused moment twice)."""
    host, guest = phones(site, browser)
    if ms:
        guest.evaluate("""() => { const n = performance.now.bind(performance);
          AiPelitSulava.now = () => Math.floor(n()) / 1000; }""")
    for pg in (host, guest):
        pg.evaluate(PAUSE)
    host.evaluate(QUIET)
    host.evaluate("players[4].x = -12; players[4].y = -5")
    guest.wait_for_function("Math.abs(players[4].x + 12) < 0.05 && players[4].tr.size() > 3", timeout=5000)
    host.evaluate(HOLD)
    host.evaluate(STALLS)
    guest.evaluate(PZREC, 4)
    host.evaluate("window.__cpuRun = 4; window.__run = true")
    guest.wait_for_timeout(800)
    host.evaluate("window.__hold = true")
    guest.wait_for_timeout(500)
    clock = "(performance.timeOrigin + performance.now()) / 1000"
    guest.evaluate(f"window.__pzAt = {clock}; window.__pz = true")
    host.evaluate("window.__pz = true; window.__release()")
    guest.wait_for_timeout(500)
    host.evaluate("window.__hold = false; window.__pz = false")
    guest.evaluate(f"window.__goAt = {clock}; window.__pz = false")
    guest.wait_for_timeout(1000)
    guest.evaluate("window.__pzStop = true")
    pr, pz_at, go_at = guest.evaluate("[window.__pr, window.__pzAt, window.__goAt]")
    stalls = host.evaluate("window.__stall")
    # The stall outran the guess: when the pause came, the drawn moment was over 0.25 s past the newest spot.
    at_pz = [f for f in pr if f[0] < pz_at][-1]
    assert at_pz[3] - at_pz[4] > 0.3, at_pz
    held = [f for f in pr if pz_at <= f[0] <= go_at]
    assert len(held) > 3, len(held)
    assert max(f[1] for f in held) - min(f[1] for f in held) < 0.01, [(round(f[0] - pz_at, 3), round(f[1], 2)) for f in held]
    # After it, each frame steps at the player's speed (5 m/s, 7 with the catching up), plus the eased gap (0.1 s).
    gap = 5 * (at_pz[3] - at_pz[4] - 0.25)
    after = [f for f in pr if f[0] > go_at - 0.05]
    hops = [(round(t1 - go_at, 3), round(x1 - x0, 2)) for (t0, x0, *_), (t1, x1, *_) in zip(after, after[1:])
            if not any(st <= t1 <= st + 0.35 for st in stalls)
            and (x1 - x0 < -0.1 or x1 - x0 > 0.1 + 7 * (t1 - t0) + gap * (1 - math.exp(-(t1 - t0) / 0.1)))]
    assert not hops, (hops, round(gap, 2), [(round(f[0] - go_at, 3), round(f[1], 2)) for f in pr if f[0] > pz_at - 0.2][:40])
    assert pr[-1][1] > held[-1][1] + 2  # and it ran on
    assert not host.errors + guest.errors
