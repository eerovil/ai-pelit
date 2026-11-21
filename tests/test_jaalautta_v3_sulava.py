"""Jäälautta v3 (#480): on a guest, the other seals glide, drawn from lib/sulava-1 between the host's states a
moment back, instead of sliding on at their last speed until the next state and jumping to it (v2). The seals
keep the newest spot heard between frames; only the picture uses the drawn one. A new erä and a move longer than
any seal slides between two states are drawn at once, not glided."""
import json
import math
import shutil
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/jaalautta/v3/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# On the host: nobody bumps, thinks, picks up or breaks the ice, and the host's own seal goes round a circle of
# radius 4 at 4 units/s while `window.__run` is on, and stands where it is when off. It goes by the real clock, not
# by the world's steps: a loaded test machine's slow frames lose world time (a frame counts at most 0.1 s), which
# would show as a change of speed on the stamps the host sends.
STEADY = """() => { const mv = window.moveSeal; window.__run = false; window.__a = 0;
  window.collide = () => {}; window.cpuThink = () => {}; window.powers = () => {}; window.shrink = () => {};
  window.moveSeal = (w, sl, h) => {
    if (sl !== me) return mv(w, sl, h);
    if (!window.__run) { sl.vx = sl.vy = 0; window.__t0 = null; return; }
    const t = performance.now() / 1000;
    if (window.__t0 == null) window.__t0 = t - window.__a;
    window.__a = t - window.__t0;
    Object.assign(sl, { x: 4 * Math.cos(window.__a), y: 4 * Math.sin(window.__a), vx: -4 * Math.sin(window.__a),
      vy: 4 * Math.cos(window.__a), face: window.__a + Math.PI / 2 });
  }; }"""
# On a guest: each time the screen is drawn, where seal `i` is drawn and the newest spot heard for it; and when
# each state arrived, with the host's stamp (so a stall of the test machine, on either phone, can be told from a
# jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = []; window.__new = null; window.__back = [];
  AiPelitRooms.on('message', m => { if (m.t !== 's') return; window.__got.push([performance.now() / 1000, m.st]);
    if (net && m.seq === net.lastSeq) window.__new = [m.sk[i][6], m.sk[i][7]];  // a state the game took (a late one it drops)
    const tr = world.seals[i].tr; if (tr && tr.time !== null) window.__back.push(m.st - tr.time); });
  const d = window.draw;
  window.draw = dt => { const t = performance.now() / 1000, sl = world && world.seals[i];
    if (sl && !window.__stop) window.__xs.push([t, sl.x, sl.y]); d(dt); }; }"""


@pytest.fixture
def pair(site, browser):
    """A host and a guest on the first floe, the erä on, the host's seal steady (STEADY)."""
    shutil.copytree(ROOT / "games" / "jaalautta", site.games / "jaalautta")
    site.build()
    relay, contexts, pages = Relay(), [], []
    for name in ("Testi A", "Testi B"):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                                  service_workers="block")
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on("pageerror", lambda e, p=p: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.wait_for_function("typeof mode !== 'undefined'")
        p.click("#friends")
        pages.append(p)
    host, guest = pages
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("AiPelitRooms.inRoom")
    host.wait_for_function("AiPelitRooms.members.filter(p => p.on).length === 2")
    host.click("#aipr-start")
    host.wait_for_function("mode === 'netplay' && me && world")
    host.evaluate(STEADY)
    for p in pages:
        p.wait_for_function("mode === 'netplay' && me && world && world.ph === 'play'", timeout=12000)
    i = guest.evaluate(f"world.seals.findIndex(s => s.id === {json.dumps(host.evaluate('AiPelitRooms.me'))})")
    yield host, guest, i
    errors = [e for p in pages for e in p.errors]
    assert not errors, errors
    for c in contexts:
        c.close()


def drive_and_watch(host, guest, i, seconds=4):
    """The host's seal goes round for `seconds` over a jittery network while the guest samples it."""
    host.evaluate(JITTER)
    guest.evaluate(SAMPLE, i)
    host.evaluate("window.__run = true")
    guest.wait_for_timeout(seconds * 1000)
    guest.evaluate("window.__stop = true")
    host.evaluate("window.__run = false")
    assert host.evaluate("window.__a") > 0.7 * seconds  # it really went round (by the real clock)


def test_a_friend_s_seal_glides_on_the_guest(pair):
    """The speed over each two drawn frames, while the friend slid round at 4 units/s, is about the same: no
    frame stands still waiting for the next state, and none jumps to catch up with it."""
    host, guest, i = pair
    drive_and_watch(host, guest, i)
    xs, got = guest.evaluate("[window.__xs, window.__got]")
    sp = [(t2, math.hypot(c - a, d - b) / (t2 - t0)) for (t0, a, b), (t2, c, d) in zip(xs, xs[2:]) if t2 > t0]
    moving = [t for t, v in sp if v > 1]
    assert len(moving) > 40, len(moving)
    # Past the first half second (the glide picks up from standing) and before the last frames.
    middle = [(t, v) for t, v in sp if moving[0] + 0.5 <= t <= moving[-1] - 0.3]

    def heard(t):
        """States came in steadily over the half second before: the last at most 0.15 s back, and each under
        0.2 s after the one before, both as they arrived and on the host's clock. A loaded test machine sometimes
        holds the host's frames or the messages back longer than the track's longest delay (0.25 s), and nothing
        can glide through such a hole; a jerk with the states coming in steadily is the game's."""
        before = [g for g in got if t - 0.5 <= g[0] <= t]
        return (len(before) > 3 and t - before[-1][0] < 0.15
                and all(b[0] - a[0] < 0.2 and b[1] - a[1] < 0.2 for a, b in zip(before, before[1:])))
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 1) for _, v in middle]
    assert len(kept) > 25 and len(kept) > 0.5 * len(middle), (len(kept), len(middle))
    m, sd = mean(kept), pstdev(kept)
    assert 3 < m < 5, (m, shown)
    assert min(kept) > 0.4 * m, shown
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def test_between_frames_the_guest_keeps_the_newest_spot_and_draws_one_a_moment_back(pair):
    """The guest's own rules and HUD read where the host last said the seal is; only the picture is a moment
    back, on the host's clock."""
    host, guest, i = pair
    guest.evaluate("""(i) => { window.__rule = []; setInterval(() => { const sl = world && world.seals[i];
      if (sl && window.__new && !window.__stop) window.__rule.push([sl.x === window.__new[0] && sl.y === window.__new[1] || [sl.x, sl.y, ...window.__new],
        window.__xs.length ? Math.hypot(sl.x - window.__xs[window.__xs.length - 1][1], sl.y - window.__xs[window.__xs.length - 1][2]) : 0]); }, 37); }""", i)
    drive_and_watch(host, guest, i, seconds=3)
    rule, back = guest.evaluate("[window.__rule, window.__back]")
    assert len(rule) > 20, rule
    assert all(r[0] is True for r in rule), [(n, r) for n, r in enumerate(rule) if r[0] is not True]  # between frames the seal is at the newest spot heard
    behind = [d for _, d in rule[5:]]
    assert mean(behind) > 0.1 and sum(d > 0.02 for d in behind) > 0.7 * len(behind), behind  # not the drawn one
    assert len(back) > 15 and all(b > 0.03 for b in back[5:]), back  # drawn at least 30 ms back


# On the guest: when a state moves seal `i` by more than 0.5 units from the one before it (a new erä, or a move
# of the test's own), the spot it brought and where the next frame drew the seal.
WATCH_JUMP = """(i) => { window.__sw = []; let was = null, want = null; const d = window.draw;
  AiPelitRooms.on('message', m => { if (m.t !== 's') return; const a = m.sk[i]; window.__heard = (window.__heard || 0) + 1;
    if (was && Math.hypot(a[6] - was[0], a[7] - was[1]) > 0.5) want = [m.era, a[6], a[7]];
    was = [a[6], a[7]]; });
  window.draw = dt => { d(dt); if (want) { const sl = world.seals[i]; window.__sw.push([...want, sl.x, sl.y]); want = null; } }; }"""


@pytest.mark.parametrize("how", ["new era", "far move"])
def test_a_seal_put_somewhere_new_is_drawn_there_at_once(pair, how):
    """A new erä puts every seal back in its ring; a move of over 8 units between two states (no seal slides
    that far in a state's gap) is a jump. Either way the guest draws the seal at its new spot on the next frame,
    not sliding across the ice to it."""
    host, guest, i = pair
    # The host's seal stands at (2, 0), under 8 units from its ring spot (0, -5.5), so only the new erä can say
    # it is a jump; for the far move it stands at (-4, 0) and goes to (4.5, 0).
    start = "[2, 0]" if how == "new era" else "[-4, 0]"
    host.evaluate(f"() => {{ [me.x, me.y] = {start}; me.vx = me.vy = 0; }}")
    guest.wait_for_timeout(700)  # a few states heard there, the track settled
    guest.evaluate(WATCH_JUMP, i)
    guest.wait_for_function("window.__heard > 2", timeout=5000)  # the watch has a spot to compare with
    if how == "new era":
        host.evaluate("world.seals.filter(s => s !== me).forEach(s => fall(world, s))")
        guest.wait_for_function("window.__sw.length >= 1", timeout=12000)
    else:
        host.evaluate("() => { me.x = 4.5; me.y = 0; }")
        guest.wait_for_function("window.__sw.length >= 1", timeout=5000)
    sw = guest.evaluate("window.__sw")
    era, ax, ay, x, y = sw[0]
    if how == "new era":
        assert era == 2, sw
        assert abs(ax) < 0.01 and abs(ay + 5.5) < 0.01, sw  # its ring spot
    assert abs(x - ax) < 0.01 and abs(y - ay) < 0.01, sw
