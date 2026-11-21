"""Pulkkamäki v3 (#480): a friend's sled glides down the hill on the other phones' screens, drawn from lib/sulava-1
between the spots their phone sends, instead of being carried on the way it was going between messages (v2's
coast()). The rules (the finish, the end) keep the newest spot heard; only the drawing lags."""

import json
import shutil
from statistics import mean, pstdev

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
          AiPelitRooms.on('message', (m, from) => { if (m.t === 'p' && from === id) window.__back.push(m.st - r.tr.time); });
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
        assert len(back) > 15 and all(b > 0.03 for b in back[5:]), back  # drawn at least 30 ms back
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
    assert len(set(turning)) > 12, fl
    assert len(between) > 0.6 * len(turning), (fl, heard)
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
