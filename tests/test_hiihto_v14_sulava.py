"""Hiihto v13 (#480): a friend's skier glides along the trail on the other phones' screens, drawn from lib/sulava-1
between the spots their phone sends, instead of being carried on at their last speed between messages (v12). The
places and the end use the newest spot heard; only the drawing lags."""

import json
from statistics import mean, pstdev

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/hiihto/v14/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# The phone's own skier goes straight on at 6 m/s while `window.__run` is on, and stands still while it is off;
# no grannies or skaters on the trail to get in the way.
STRAIGHT = """() => { const ph = window.physics; window.__run = false; window.world = () => { npcs = []; };
  window.physics = (p, dt) => { if (p !== P) return ph(p, dt); p.v = window.__run ? 6 : 0; p.z += p.v * dt; }; }"""
# Records, each time the screen is drawn, where skier `i` is drawn along the trail, and when a message arrived (so a
# stall of the test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__zs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { if (window.__zs.length < 300) window.__zs.push([performance.now() / 1000, net.skiers[i].z]); d(); }; }"""


def phones(site, browser, names=("Testi A", "Testi B")):
    """Phones in a room, each waxed, the race running."""
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
        page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
        page.evaluate("AiPelitRooms.open()")
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
        p.wait_for_function("net && net.cfg && mode === 'wax'", timeout=10000)
        p.evaluate("chooseWax(bestWax(course.weather.T))")
    for p in pages:
        p.wait_for_function("mode === 'race'", timeout=15000)
        p.evaluate(STRAIGHT)
    host.relay = relay
    return pages


def index(page):
    return page.evaluate("net.skiers.findIndex(k => k.kind === 'me')")


def glides(page):
    """The speed over each two drawn frames while the friend skied: always forward and about the same."""
    zs, got = page.evaluate("[window.__zs, window.__got]")
    sp = [(t2, abs(b - a) / (t2 - t0)) for (t0, a), (t2, b) in zip(zs, zs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.01]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 1.5, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


def ski_and_watch(host, run, watch, others):
    me = index(run)
    run.evaluate(JITTER)
    watch.evaluate(SAMPLE, me)
    if run is not host and watch is not host:
        host.evaluate(SAMPLE, me)  # the host's drawn spots, for its check below
    if run is not host:
        # Between frames the host keeps the friend's newest spot (ahead of where it last drew them, as they ski on),
        # and each of their spots is drawn a moment back on their clock.
        # v14 (#570): the check is the newest spot itself, the one the friend's last message brought. v13 asked
        # for it to be 0.15 m ahead of the drawn one nine times in ten, which a late message (the track then
        # carries the drawing on up to it, or a little past) failed on this host about one run in three, from
        # v13's own merge on.
        host.evaluate("""(me) => { const k = net.skiers[me]; window.__rule = []; window.__back = []; let heard = null;
          AiPelitRooms.on('message', (m, from) => { if (m.t === 'p' && from === k.id) { heard = m.s[0]; window.__back.push(m.st - k.tr.time); } });
          setInterval(() => { if (window.__zs.length && heard !== null) window.__rule.push([k.z, window.__zs[window.__zs.length - 1][1], heard]); }, 37); }""", me)
    z0 = run.evaluate("P.z")
    run.evaluate("window.__run = true")
    watch.wait_for_function("window.__zs.length >= 200", timeout=30000)
    run.evaluate("window.__run = false")
    assert run.evaluate("P.z") > z0 + 8  # it really skied
    glides(watch)
    if run is not host:
        rule, back = host.evaluate("[window.__rule, window.__back]")
        moving = [(kept, drawn, heard) for kept, drawn, heard in rule if drawn > z0 + 2 and kept < z0 + 12]
        assert len(moving) > 30, rule
        assert all(kept == heard for kept, _, heard in moving), moving  # the newest spot, not the drawn one
        assert sum(kept != drawn for kept, drawn, _ in moving) > 0.5 * len(moving), moving  # and the drawing lags
        assert len(back) > 15 and all(b > 0.03 for b in back[5:]), back  # drawn at least 30 ms back
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors


def test_a_friend_skiing_glides_on_the_host(site, browser):
    host, guest = phones(site, browser)
    ski_and_watch(host, guest, host, others=[guest])


def test_the_host_skiing_glides_on_a_guest(site, browser):
    host, guest = phones(site, browser)
    ski_and_watch(host, host, guest, others=[guest])


def test_a_friend_skiing_glides_on_a_third_phone_too(site, browser):
    """The host sends a friend's spots on as they came, with the friend's own clock, so a third phone draws them
    as smoothly (v12 sent where its own guess had carried them)."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    host.evaluate(JITTER)
    ski_and_watch(host, aino, ville, others=[aino, ville])


# On a phone: each time a message changes whose clock skier `i`'s spot carries (the computer took over a friend, or
# gave them back), the spot it brought and where the next frame drew them.
SWITCH = """(i) => { window.__sw = []; const k = net.skiers[i]; let src = k.src, want = null; const d = window.draw;
  AiPelitRooms.on('message', m => { if (m.t !== 's' || k.src === src) return; src = k.src; want = [src, m.sk[i][0]]; });
  window.draw = () => { d(); if (want) { window.__sw.push([...want, k.z]); want = null; } }; }"""


def test_a_friend_taken_over_by_the_computer_and_given_back_is_drawn_where_the_host_says(site, browser):
    """A friend's phone drops mid-race: the host's computer skis for them, so the rows carry the host's clock and no
    longer the friend's; when the phone is back, the friend's again. A third phone starts the track again at each
    change, drawing the row's spot from the next frame, not a guess from the other clock."""
    host, aino, ville = phones(site, browser, names=("Testi A", "Testi B", "Testi C"))
    me = index(aino)
    aino.evaluate("window.__run = true")
    ville.wait_for_function(f"net.skiers[{me}].src === 'f' && net.skiers[{me}].z > 4", timeout=5000)
    ville.evaluate(SWITCH, me)
    host.relay.drop(aino)
    host.wait_for_selector("#aipr-goOn", state="visible", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"net.skiers[{me}].kind === 'cpu'")
    ville.wait_for_function("window.__sw.some(s => s[0] === 'h')", timeout=5000)
    host.relay.back(aino)
    host.wait_for_function(f"net.skiers[{me}].kind === 'net' && net.skiers[{me}].ts !== null", timeout=20000)
    ville.wait_for_function("window.__sw.some(s => s[0] === 'f')", timeout=5000)
    sw = ville.evaluate("window.__sw")
    assert [s[0] for s in sw][:2] == ["h", "f"], sw
    assert all(abs(drawn - said) < 0.01 for _, said, drawn in sw), sw
    errors = [e for p in (host, aino, ville) for e in p.errors]
    assert not errors, errors


def test_the_place_on_screen_goes_by_the_newest_spot_not_the_drawn_one(site, browser):
    """While a frame draws a friend a moment back, "sija" and the waiting list still count them where their phone last
    said, like the end does: a friend who has just passed you is ahead at once."""
    host, guest = phones(site, browser)
    me = index(guest)
    # v14 (#570): the host stands a metre on, so the friend passes them a moment after setting off, while the
    # drawing is still a moment back. v13's host stood at the start line, and a frame with the friend drawn
    # exactly there but heard past it only came when the run started early in the friend's send cycle.
    host.evaluate("P.z = 1")
    host.evaluate("""(i) => { window.__pl = []; const d = window.draw, k = net.skiers[i];
      window.draw = () => { const own = synced(meK()).z; window.__pl.push([k.z, k.zNew ?? k.z, own, livePlace(),
        standings()[0].id === k.id]); d(); }; }""", me)
    guest.evaluate("window.__run = true")
    host.wait_for_function(f"net.skiers[{me}].z > 6", timeout=10000)
    guest.evaluate("window.__run = false")
    pl = host.evaluate("window.__pl")
    split = [p for p in pl if p[0] <= p[2] < p[1]]  # drawn behind the host, but heard ahead of them
    assert split, pl[:40]
    for drawn, heard, own, place, first in pl:
        ahead = heard > own
        assert place == (2 if ahead else 1), (drawn, heard, own, place)
        if ahead:
            assert first, (drawn, heard, own)
    assert not host.errors + guest.errors
