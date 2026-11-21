"""Pulkkamäki v3 (#480): a friend's sled glides down the hill on the other phones' screens, drawn from lib/sulava-1
between the spots their phone sends, instead of being carried on the way it was going between messages (v2's
coast()). The rules (the finish, the end) keep the newest spot heard; only the drawing lags."""

import json
import shutil
import time
from statistics import mean, median, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/pulkkamaki/v3/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own sled goes straight down the hill at 8 m/s of real time while `window.__run` is on (the game's
# frame step is capped, so a test machine slow to draw would slide slower), and stands still while it is off: no
# trees, jumps or falls to get in the way. Every other sled slides as the game slides it.
STRAIGHT = """() => { const adv = window.__adv = window.advance; window.__run = false; let at = null;
  window.advance = (h, sl, dt) => { if (sl !== me) return adv(h, sl, dt);
    const t = performance.now() / 1000, d = at === null ? 0 : t - at; at = t;
    sl.v = window.__run ? 8 : 0; sl.s += sl.v * d; sl.yaw = 0; sl.air = false; sl.y = groundAt(h, sl.s, sl.x); }; }"""
# Records, each time the hill is drawn, where sled `id` is drawn down the hill, and when a message brought a new spot
# of it (so a stall of the test machine, the sending phone drawing no frame for a while, can be told from a jerk:
# three phones drawing 3D on one machine stall now and then, and the host's own rows keep coming meanwhile).
SAMPLE = """(id) => { window.__zs = []; window.__got = []; let was = null;
  AiPelitRooms.on('message', () => { const s = recOf(id).sl.s; if (s !== was) window.__got.push(performance.now() / 1000); was = s; });
  const d = window.render3d;
  window.render3d = (...a) => { if (window.__zs.length < 300) window.__zs.push([performance.now() / 1000, recOf(id).sl.s]);
    return d(...a); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, the run going, each own sled standing still until `window.__run`."""
    shutil.copytree(ROOT / "games" / "pulkkamaki", site.games / "pulkkamaki")
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
        page.wait_for_function("V3 || no3d", timeout=20000)
        page.evaluate(STRAIGHT)
        page.click("#friends")
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
        p.wait_for_function("mode === 'run' && me", timeout=15000)
    host.relay = relay
    return pages


def me_of(page):
    return page.evaluate("AiPelitRooms.me")


def glides(page):
    """The speed over each two drawn frames while the friend slid: always forward and about the same."""
    zs, got = page.evaluate("[window.__zs, window.__got]")
    sp = [(t2, abs(b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(zs, zs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.01]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        # New spots kept coming over the last 0.6 s, none more than 0.3 s apart: a frame just after the sender
        # stalled draws away the guess it made meanwhile, which is the library's ease and not a jerk.
        near = [g for g in got if t - 0.6 <= g <= t]
        before = [g for g in got if g < t - 0.6]
        seq = before[-1:] + near
        return bool(near) and t - near[-1] <= 0.3 and all(b - a <= 0.3 for a, b in zip(seq, seq[1:])) and bool(before)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    # A loaded test machine stalls the sending phone now and then; enough frames are left between the stalls.
    assert len(kept) > 40 and len(kept) > 0.4 * len(middle), (len(kept), len(middle))
    assert min(kept) > 2, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def slide_and_watch(host, run, watch, others):
    me = me_of(run)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host and watch is not host:
        host.evaluate(SAMPLE, me)  # the host's drawn spots, for its check below
    if run is not host:
        # Between frames the host keeps the friend's newest spot (ahead of where it last drew them, as they slide
        # on), and each of their spots is drawn a moment back on their clock.
        host.evaluate("""(id) => { const r = recOf(id); window.__rule = []; window.__back = [];
          AiPelitRooms.on('message', (m, from) => { if (m.t === 'p' && from === id)
            window.__back.push([performance.now() / 1000, m.st, r.tr.time, r.tr.delay]); });
          setInterval(() => { if (window.__zs.length) window.__rule.push([r.sl.s, window.__zs[window.__zs.length - 1][1]]); }, 37); }""",
                      me)
    s0 = run.evaluate("me.s")
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__zs.length >= 200", timeout=40000)
    run.evaluate("window.__run = false")
    assert run.evaluate("me.s") > s0 + 10  # it really slid
    glides(watch)
    if run is not host:
        rule, back = host.evaluate("[window.__rule, window.__back]")
        ahead = [kept - drawn for kept, drawn in rule if drawn > s0 + 2 and kept < s0 + 20]
        assert len(ahead) > 20, rule
        assert sum(a > 0.2 for a in ahead) > 0.7 * len(ahead), ahead  # the newest spot, not the drawn one
        # Each spot that came on time is drawn at least 40 ms back on its sender's clock. On time: its lag
        # (arrival - stamp) within 20 ms of the smallest in the 2 s before, which is how the track learns the
        # offset. A spot held up longer (a stalled phone under load) lands after its moment was already drawn
        # on a guess, which the library then eases away; its stamp minus `tr.time` is about the delay minus
        # how late it was (measured within 25 ms over 420 spots), so it may well be below 0 and says nothing
        # about the delay (#480: checking every spot failed 1 run of 5 under load 80-97).
        on_time, lags = [], []
        for i, (a, st, t, _) in enumerate(back):
            lags.append((a, a - st))
            if i >= 5 and a - st - min(lag for at, lag in lags if at >= a - 2) < 0.02:
                on_time.append(st - t)
        # The sender's 0-90 ms jitter leaves about a fifth of the spots on time (7 of 33 in one run): a few to check.
        assert len(back) > 15 and len(on_time) > 3 and min(on_time) > 0.04, (on_time, back)
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


def test_a_friend_sliding_glides_on_the_host(site, browser):
    host, guest = phones(site, browser)
    slide_and_watch(host, guest, host, others=[guest])


def test_the_host_sliding_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    slide_and_watch(host, host, guest, others=[guest])


def test_a_friend_sliding_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on as they came, with the friend's own clock, so a third phone draws them
    as smoothly (v2 sent where its own coasting had carried them)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(JITTER)
    slide_and_watch(host, aino, ville, others=[aino, ville])


def test_a_friends_flip_turns_smoothly_between_messages(site, browser):
    """The turns of a trick are on the track too: a friend's front flip is drawn turning a little every frame, not
    in one step per message (v2 turned it on between messages itself; without that, it would only step)."""
    host, guest = phones(site, browser)
    me = me_of(guest)
    host.evaluate("""(id) => { window.__fl = []; window.__heard = new Set(); const r = recOf(id), d = window.render3d;
      AiPelitRooms.on('message', (m, from) => { if (m.t === 'p' && from === id) window.__heard.add(+r.sl.flip.toFixed(4)); });
      window.render3d = (...a) => { if (r.sl.trick || r.sl.flip) window.__fl.push(+r.sl.flip.toFixed(4)); return d(...a); }; }""", me)
    # High above the snow, the friend does a front flip (0.72 s) on the game's own physics.
    guest.evaluate("""() => { window.advance = window.__adv;
      me.air = true; me.y = groundAt(hill, me.s, me.x) + 8; me.vy = 0; me.v = 8; startTrick(me, 'front'); }""")
    guest.wait_for_function("me.jump.length === 1 || !me.air", timeout=5000)
    host.wait_for_timeout(600)
    fl, heard = host.evaluate("[window.__fl, [...window.__heard]]")
    turning = [f for f in fl if 0.2 < f < 6.1]
    between = [f for f in turning if f not in heard]
    # Measured against the frames the host drew while it turned, not a fixed count, which follows the frame rate
    # (#480: 34 turning frames at 59 fps, 13 at 21 fps on a CPU-throttled host; a loaded run showed 12 angles and failed a
    # fixed "more than 12").
    assert len(turning) > 4, fl  # enough frames to judge
    assert len(set(turning)) > 0.8 * len(turning), fl  # a new angle nearly every frame, not one per message
    assert len(between) > 0.6 * len(turning), (fl, heard)  # and mostly angles no message brought
    # Turning one way only, never back (an angle blended the short way round).
    assert all(b >= a - 0.05 for a, b in zip(turning, turning[1:])), turning
    assert not host.errors + guest.errors


# On a phone: each time a message changes whose clock sled `id`'s spot carries (the computer took over a friend, or
# gave them back), the spot it brought and where the next frame drew them.
SWITCH = """(id) => { window.__sw = []; const r = recOf(id); let src = r.src, want = null; const d = window.render3d;
  AiPelitRooms.on('message', m => { if (m.t !== 's' || r.src === src) return; src = r.src;
    want = [src, m.sk.find(k => k.id === id).a[0]]; });
  window.render3d = (...a) => { const o = d(...a); if (want) { window.__sw.push([...want, r.sl.s]); want = null; } return o; }; }"""


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-run: the host's computer slides for them, so the rows carry the host's clock and
    no longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at each
    change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = me_of(aino)
    aino.evaluate("window.__run = true")
    ville.wait_for_function(f"recOf({json.dumps(me)}).src === 'f' && recOf({json.dumps(me)}).sl.s > 6", timeout=5000)
    # The drawn spot is read inside render3d, where the frame has swapped it in.
    ville.evaluate(SWITCH, me)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"recOf({json.dumps(me)}).drive")
    ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
    host.relay.back(aino)
    host.wait_for_function(f"!recOf({json.dumps(me)}).drive && recOf({json.dumps(me)}).ts !== null", timeout=20000)
    ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
    sw = ville.evaluate("window.__sw")
    assert [s[0] for s in sw][:2] == ["h", "f"], sw
    assert all(abs(drawn - said) < 0.01 for _, said, drawn in sw), sw
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


# On a phone: each frame, sled `id` as drawn (inside render3d, where the frame has swapped the drawn spot in), its
# roll, and whether the room is paused.
DRAWN = """(id) => { window.__dr = []; const r = recOf(id), d = window.render3d;
  window.render3d = (...a) => { window.__dr.push([performance.now() / 1000, r.sl.s, r.sl.roll, AiPelitRooms.paused,
    r.tr.time === null ? null : runClock() - r.tr.time]);
    return d(...a); }; }"""


# The room's pause on one phone by hand, from `on` to `off` (ms on the machine's clock, which every page shares), to
# set which phone hears it first; a pause on a busy test machine cannot wait for a message to reach a page.
PAUSE = """([on, off]) => Object.defineProperty(AiPelitRooms, 'paused',
  { get: () => Date.now() >= on && Date.now() < off, configurable: true })"""


@pytest.mark.parametrize("first", ["away", "host", "guest"])
def test_a_pause_holds_the_others_where_they_are_and_they_go_on_from_there(site, browser, first):
    """A phone in the run goes away: every phone waits, and a guest draws the host's sled where it is, not gliding
    on past its newest spot (to slide back once the run goes on). Sleds stand still in a pause, so they are drawn so.
    "away": a third phone really drops. The phones hear a pause a moment apart, so "host" and "guest" pause them by
    hand a quarter of a second apart, each first: a guest that pauses first still hears the host's last spots, sent
    before the host stopped, and they go on its track only once its pause ends, not ahead of the drawn moment."""
    names = ("Testi A", "Testi B", "Testi C") if first == "away" else ("Testi A", "Testi B")
    host, aino, *rest = phones(site, browser, names=names)
    hid = me_of(host)
    # The host's own sled goes straight down at 8 m/s, by the run's clock, which stands still in the pause (as the
    # game's own sleds do: no frame steps them then); on the game's physics a tree could stop it short, and the
    # drawing would then ease away its guess of the sled going on.
    host.evaluate("""() => { const adv = window.__adv; let at = null;
      window.advance = (h, sl, dt) => { if (sl !== me) return adv(h, sl, dt);
        const t = runClock(), d = at === null ? 0 : t - at; at = t;
        sl.v = 8; sl.s += sl.v * d; sl.yaw = 0; sl.air = false; sl.y = groundAt(h, sl.s, sl.x); }; }""")
    aino.wait_for_function(f"recOf({json.dumps(hid)}).sl.s > {aino.evaluate(f'recOf({json.dumps(hid)}).sl.s')} + 6",
                           timeout=10000)
    aino.evaluate(DRAWN, hid)
    aino.wait_for_timeout(500)
    if first == "away":
        host.relay.drop(rest[0])
        aino.wait_for_function("AiPelitRooms.paused", timeout=10000)
        aino.wait_for_timeout(1200)
        host.relay.back(rest[0])
        aino.wait_for_function("!AiPelitRooms.paused", timeout=20000)
    else:
        at = time.time() * 1000 + 300
        for p, d in ((host, 0), (aino, 250)) if first == "host" else ((aino, 0), (host, 250)):
            p.evaluate(PAUSE, [at + d, at + d + 1450])  # both 1.45 s, a quarter of a second apart
        aino.wait_for_timeout(300 + 1700)
    aino.wait_for_timeout(2500)
    dr = aino.evaluate("window.__dr")
    paused = [(t, s) for t, s, _, p, *_ in dr if p]
    assert len(paused) > 4 and paused[-1][0] - paused[0][0] > 0.8, dr  # by time: a loaded machine draws few frames
    # From 0.15 s into the pause (the phones hear of it a moment apart), the sled stands where it was drawn.
    held = [s for t, s in paused if t > paused[0][0] + 0.15]
    assert max(held) - min(held) < 0.05, [round(s, 2) for _, s in paused]
    assert dr[-1][1] > held[-1] + 2, dr[-1]  # and it slid on after the pause
    # Never drawn sliding back up the hill, before, in or after the pause.
    drawn = [round(s, 2) for _, s, *_ in dr]
    assert all(b >= a - 0.05 for a, b in zip(drawn, drawn[1:])), drawn
    errors = [e for p in (host, aino, *rest) for e in p.errors]
    assert not errors, errors
    # After it the host's sled is drawn as far back in its own time as before: a spot heard in the pause with its
    # stamp ahead of the held clock tells the track the spots come sooner than they do, and for the next 2 s it
    # draws the sled up to 0.25 s further on, past its newest spot on a guess. Read from the track (this phone's
    # clock less the drawn moment), which a stall of the sending phone does not move: with the spots held, it moved
    # -0.01 to 0.06 s; heard at once, 0.13; held but heard when the pause ended, 0.12 to 0.16. Only when the two
    # phones' pauses are as long ("host", "guest"): one that stood longer really is further behind the other's clock.
    if first == "away":
        return
    went, gone = min(t for t, _, _, p, _ in dr if p), max(t for t, _, _, p, _ in dr if p)
    # The two clocks are two pages' (each its own performance.now()), so the value is their offset plus the lag:
    # only how it changes counts. By time, not frames: a busy machine can draw no frame for half a second, so the
    # last few frames before the pause, and those from 1 to 2.5 s after it, however few.
    before = [b for t, _, _, p, b in dr if not p and went - 2 < t < went and b is not None][-10:]
    after = [b for t, _, _, p, b in dr if not p and gone + 1 < t < gone + 2.5 and b is not None]
    assert before and after, ([(round(t - went, 2), p) for t, _, _, p, _ in dr])
    assert median(after) > median(before) - 0.08, (round(median(before), 3), [round(b, 3) for b in after])


def test_a_friends_fall_rolls_one_way_and_ends_upright_at_once(site, browser):
    """A fall rolls the sled 1.5 turns, and at its end the sled is upright again at once, as on the friend's own
    phone: drawn on the host, the roll only grows, and then is 0, never rolling back between."""
    host, guest = phones(site, browser)
    gid = me_of(guest)
    host.evaluate(DRAWN, gid)
    guest.evaluate("window.advance = window.__adv; me.v = 6; fall(me, 'Kivi!')")
    host.wait_for_function(f"recOf({json.dumps(gid)}).sl.fallT > 0", timeout=5000)
    host.wait_for_function(f"!(recOf({json.dumps(gid)}).sl.fallT > 0)", timeout=5000)
    host.wait_for_timeout(600)
    rolls = [round(r, 3) for _, _, r, *_ in host.evaluate("window.__dr")]
    assert max(rolls) > 5, rolls  # it really rolled (most of the way to 3π; at a low frame rate no frame is drawn at the top)
    assert rolls[-1] == 0, rolls
    assert all(b >= a - 0.01 or b == 0 for a, b in zip(rolls, rolls[1:])), rolls
    assert not host.errors + guest.errors


def test_a_friend_over_the_finish_line_is_drawn_slowing_down(site, browser):
    """Past the line a finished sled brakes to a stop on its own phone; that phone keeps sending it until it stands,
    so the others draw it slowing down there and not stopping dead at the line."""
    host, guest = phones(site, browser)
    gid = json.dumps(me_of(guest))
    host.evaluate(f"""() => {{ window.__fin = []; const r = recOf({gid});
      AiPelitRooms.on('message', (m, from) => {{ if (m.t === 'p' && from === {gid} && r.sl.fin) window.__fin.push(r.sl.s); }}); }}""")
    guest.evaluate("""() => { window.advance = window.__adv;
      me.s = hill.len - 3; me.x = centreX(hill, me.s); me.y = groundAt(hill, me.s, me.x); me.v = 6; me.yaw = 0; }""")
    host.wait_for_function(f"recOf({gid}).sl.fin", timeout=5000)
    guest.wait_for_function("me.fin && !(me.v > 0)", timeout=10000)
    host.wait_for_timeout(500)
    fin = host.evaluate("window.__fin")
    assert len(set(fin)) > 10, fin  # a spot each tenth of a second while it slowed down
    assert all(b >= a for a, b in zip(fin, fin[1:])), fin
    assert fin[-1] > fin[0] + 3, fin
    # Where it came to rest reaches the host, though the host had the finish long before, and is drawn there.
    rest = guest.evaluate("[me.s, me.v || 0]")
    seen = host.evaluate(f"[recOf({gid}).sl.s, recOf({gid}).sl.v || 0]")
    assert abs(seen[0] - rest[0]) < 0.02 and seen[1] == rest[1] == 0, (seen, rest)
    host.wait_for_function(f"Math.abs(recOf({gid}).tr.at(runClock()).s - {rest[0]}) < 0.05", timeout=3000)
    assert not host.errors + guest.errors


def test_a_fast_friend_glides_over_a_long_gap_and_is_not_drawn_at_once(site, browser):
    """A sled at the top speed (about 20 m/s) goes 20 m in a second's stall of its phone: still a glide on the
    track, not a jump drawn at once. Only a move past 25 m is."""
    host, _ = phones(site, browser)
    sizes = host.evaluate("""() => { const tr = newTrack(), at = (t, s) => ({ s, x: 0, y: 0, yaw: 0, flip: 0, spin: 0, roll: 0, tilt: 0 });
      tr.push(0, at(0, 100), 0); tr.push(1, at(1, 120), 1); const a = tr.size();
      tr.push(2, at(2, 150), 2); return [a, tr.size()]; }""")
    assert sizes == [2, 1], sizes
