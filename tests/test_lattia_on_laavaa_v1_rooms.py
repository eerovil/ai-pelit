"""Lattia on laavaa v1 with friends (#488): the host runs the round, each phone moves its own kid.

What the design review asked the code to answer (on the issue): who drives a kid after a reload
or a take-over (the hand-over count `own`), that a pause stops the round clock, that a fall a
guest tells late still counts with its own time, and that every phone ends on the same result."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/lattia-on-laavaa/v1/"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
KID = "world.kids.find(k => k.id === {})"
# On the host: the computer's kids are out and think no more, so only the phones' kids are left.
CPU_OUT = "() => { brains = brains.map(() => null); world.kids.filter(k => k.kind === 'cpu').forEach(k => fall(world, k)); }"
# The widest piece of the room and the piece farthest from it, each as [x, z, top].
WIDE = """(() => { const a = world.pieces.slice().sort((p, q) => q.w - p.w)[0];
  const b = world.pieces.slice().sort((p, q) => Math.hypot(q.x - a.x, q.z - a.z) - Math.hypot(p.x - a.x, p.z - a.z))[0];
  return [a, b].map(p => [p.x, p.z, topOf(p, world.rt)]); })()"""


@pytest.fixture
def kids(site, browser):
    shutil.copytree(ROOT / "games" / "lattia-on-laavaa", site.games / "lattia-on-laavaa")
    site.build()
    relay = Relay()
    contexts = []

    def phone(name, width=360, height=740):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on("pageerror", lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.wait_for_function("typeof mode !== 'undefined'")
        return p

    phone.relay = relay
    yield phone
    for c in contexts:
        c.close()


def room(phone, n=2):
    host = phone("Testi1")
    host.click("#friends")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    pages = [host]
    for i in range(1, n):
        p = phone("Testi" + str(i + 1))
        p.click("#friends")
        p.fill("#aipr-codeIn", code)
        p.click("#aipr-joinBtn")
        p.wait_for_function("AiPelitRooms.inRoom")
        pages.append(p)
    host.wait_for_function(f"AiPelitRooms.members.filter(p => p.on).length === {n}")
    return pages


def start(pages):
    pages[0].click("#aipr-start")
    for p in pages:
        p.wait_for_function("mode === 'netplay' && me && world && world.ph === 'play'", timeout=12000)


def gid_of(page):
    return json.dumps(page.evaluate("AiPelitRooms.me"))


def place(page, x, z, y, face=0):
    """Puts this phone's own kid at a spot, standing still."""
    page.evaluate(f"() => Object.assign(me, {{ x: {x}, z: {z}, y: {y}, vx: 0, vy: 0, vz: 0, face: {face}, ground: true }})")


def test_three_phones_play_the_hosts_room_and_end_on_one_result(kids):
    host, g1, g2 = room(kids, 3)
    # The host picks the room on the room screen; a guest sees who does.
    host.wait_for_function("document.querySelectorAll('#lol-room button').length === 3")
    assert "valitsee huoneen" in g1.locator("#lol-room").inner_text()
    host.click("#lol-room button[data-r='2']")
    assert "on" in host.locator("#lol-room button[data-r='2']").get_attribute("class")
    start([host, g1, g2])
    for p in (host, g1, g2):
        assert p.evaluate("world.level") == 2
        assert p.evaluate("world.kids.length") == 6   # three phones and three of the computer's
        assert p.evaluate("world.kids.filter(k => k.kind === 'cpu').length") == 3
    gid = gid_of(g1)
    # The guest's finger moves its kid on the host's screen.
    host.evaluate(CPU_OUT)
    x0 = host.evaluate(f"{KID.format(gid)}.x")
    g1.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    g1.evaluate(TOUCH, ["pointermove", 7, 150, 560])
    host.wait_for_function(f"{KID.format(gid)}.x > {x0} + 0.3", timeout=5000)
    g1.evaluate(TOUCH, ["pointerup", 7, 150, 560])
    # The host's kid wins: every other kid falls on the host. One result everywhere, nothing saved.
    for p in (host, g1, g2):
        p.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    host.evaluate("() => world.kids.filter(k => k !== me).forEach(k => fall(world, k))")
    for p in (host, g1, g2):
        p.wait_for_function("mode === 'end'", timeout=10000)
        assert p.locator("#again").inner_text() == "Takaisin huoneeseen"
        assert p.locator("#toMenu").is_hidden()
        assert p.evaluate("sent") == []
        assert p.evaluate("['auki', 'voitot', 'paras-2'].map(k => localStorage.getItem('ai-pelit:lattia-on-laavaa:' + k))") == [None] * 3
    assert host.locator("#endTitle").inner_text() == "Voitit!"
    assert g1.locator("#endTitle").inner_text() == "Testi1 voitti"
    rows = [p.evaluate("result.rows.map(r => r.id + ':' + r.t)") for p in (host, g1, g2)]
    assert rows[0] == rows[1] == rows[2]
    assert len(rows[0]) == 6
    # Back in the room, the next round starts clean.
    first = host.evaluate("net.round")
    for p in (g1, g2, host):
        p.click("#again")
    host.wait_for_function("document.getElementById('aipr-start') && !document.getElementById('aipr-start').disabled")
    host.click("#aipr-start")
    for p in (host, g1, g2):
        p.wait_for_function(f"net && net.round !== {json.dumps(first)} && world && me && !me.out && world.kids.every(k => !k.out)", timeout=12000)
    assert host.errors == g1.errors == g2.errors == []


def test_a_guests_shove_pushes_the_host_and_through_the_host_another_guest(kids):
    host, g1, g2 = room(kids, 3)
    start([host, g1, g2])
    host.evaluate(CPU_OUT)
    (x, z, top), (x2, z2, top2) = host.evaluate(WIDE)
    gid1, gid2 = gid_of(g1), gid_of(g2)
    # The first guest with the host's kid just in front of it, on the same piece.
    # The host and the far guest first, so the first guest's phone sees them there before it
    # stands beside the host (it would bump into where it last saw them).
    place(host, x + 0.4, z, top)
    place(g2, x2, z2, top2)   # on another piece for now
    hid = gid_of(host)
    g1.wait_for_function(f"Math.abs({KID.format(hid)}.x - {x + 0.4}) < 0.3 && Math.abs({KID.format(gid2)}.x - {x2}) < 0.3", timeout=5000)
    place(g1, x - 0.4, z, top)
    host.wait_for_function(f"Math.abs({KID.format(gid1)}.x - {x - 0.4}) < 0.3", timeout=5000)
    g1.evaluate("() => { me.face = 0; shoveBtn(); }")
    host.wait_for_function("me.pushedAt > 0", timeout=5000)
    host.wait_for_function(f"{KID.format(gid1)}.shoves === 1", timeout=5000)
    # The second guest in front of the first: the host tells the second phone to fly.
    g2.evaluate("() => { window.pushes = 0; const ap = applyPush; applyPush = (k, i) => { if (k === me) pushes++; ap(k, i); }; }")
    g1.wait_for_function("me.cd <= 0", timeout=5000)
    place(g1, x - 0.4, z, top)
    place(g2, x + 0.4, z, top)
    host.wait_for_function(f"Math.abs({KID.format(gid1)}.x - {x - 0.4}) < 0.3 && Math.abs({KID.format(gid2)}.x - {x + 0.4}) < 0.3", timeout=5000)
    g1.evaluate("() => { me.face = 0; shoveBtn(); }")
    g2.wait_for_function("pushes === 1", timeout=5000)
    assert host.errors == g1.errors == g2.errors == []


def test_a_guest_reloaded_mid_round_takes_its_kid_back_and_drives_it(kids):
    host, guest = room(kids)
    start([host, guest])
    host.evaluate("() => { brains = brains.map(() => null); }")
    gid = gid_of(guest)
    own = host.evaluate(f"{KID.format(gid)}.own")
    guest.reload()
    guest.wait_for_function("mode === 'netplay' && me && net.h >= 0", timeout=15000)
    assert host.evaluate(f"{KID.format(gid)}.own") == own + 1
    assert guest.evaluate("net.h") == own + 1
    assert abs(guest.evaluate("me.x") - host.evaluate(f"{KID.format(gid)}.x")) < 0.5
    # A spot sent with the count from before the reload moves nothing.
    host.evaluate(f"(() => {{ const k = {KID.format(gid)}; hostSpot({{ t: 'p', round: net.round, h: {own}, x: 6, y: 3, z: 4, o: -1 }}, {gid}); }})()")
    assert host.evaluate(f"{KID.format(gid)}.x") != 6
    # Its finger drives the kid again.
    x0 = host.evaluate(f"{KID.format(gid)}.x")
    guest.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 150, 560])
    host.wait_for_function(f"{KID.format(gid)}.x > {x0} + 0.3", timeout=5000)
    assert host.errors == guest.errors == []


def test_an_away_phone_pauses_the_clock_and_the_computer_takes_it_and_gives_it_back(kids):
    host, guest = room(kids)
    start([host, guest])
    gid = gid_of(guest)
    kids.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused && AiPelitRooms.waiting.length === 1", timeout=10000)
    rt = host.evaluate("world.rt")
    host.wait_for_timeout(600)
    assert host.evaluate("world.rt") == rt   # the round clock waits with the room
    host.click("#aipr-goOn")
    host.wait_for_function(f"net.recs.get({gid}).drive && !AiPelitRooms.paused")
    own = host.evaluate(f"{KID.format(gid)}.own")
    # A spot from before the take-over (the old count) moves nothing, and neither does a fall.
    host.evaluate(f"(() => {{ hostSpot({{ t: 'p', round: net.round, h: {own} - 1, x: 6, y: 3, z: 4, o: 0.5 }}, {gid}); }})()")
    assert host.evaluate(f"[{KID.format(gid)}.x !== 6, {KID.format(gid)}.out]") == [True, False]
    host.wait_for_function(f"world.rt > {rt} + 0.3")
    kids.relay.back(guest)
    host.wait_for_function(f"!net.recs.get({gid}).drive", timeout=15000)
    guest.wait_for_function(f"net.h >= {own + 1} && !net.cpuMine && mode === 'netplay'", timeout=10000)
    # The host ran the kid on until the phone's first spot with the new count, then let it go.
    host.wait_for_function(f"!net.recs.get({gid}).hand && !runsHere({KID.format(gid)})", timeout=5000)
    host.evaluate("() => world.kids.filter(k => k !== me).forEach(k => fall(world, k))")
    guest.wait_for_function("mode === 'end'", timeout=10000)
    assert guest.evaluate("result.helped")
    note = guest.locator("#endNote").inner_text()
    assert "Tietokone" in note and "Kestit" in note   # helped, and still its own time
    assert host.errors == guest.errors == []


def test_a_fall_a_guest_tells_late_counts_with_its_own_time(kids):
    host, guest = room(kids)
    start([host, guest])
    host.evaluate(CPU_OUT)
    gid = gid_of(guest)
    host.wait_for_function("world.rt > 1")
    # The host's kid falls; the guest's word that it fell a moment before comes inside the wait,
    # so nobody is left and the latest fall (the host's) wins, not the guest standing in the
    # host's view.
    host.evaluate(f"""() => {{ fall(world, me); const g = {KID.format(gid)};
      hostSpot({{ t: 'p', round: net.round, h: g.own, s: 0, x: g.x, y: g.y, z: g.z, vx: 0, vy: 0, vz: 0, f: 0, st: 0, da: 0,
                  sh: g.shoves, j: 0, o: world.rt - 0.1 }}, {gid}); }}""")
    for p in (host, guest):
        p.wait_for_function("mode === 'end'", timeout=10000)
    assert host.locator("#endTitle").inner_text() == "Voitit!"
    assert guest.locator("#endTitle").inner_text() == "Testi1 voitti"
    assert guest.evaluate("me.out")
    assert host.errors == guest.errors == []


def test_a_guest_judges_its_own_fall_and_watches_on(kids):
    host, g1, g2 = room(kids, 3)
    start([host, g1, g2])
    host.evaluate("() => { brains = brains.map(() => null); }")
    gid = gid_of(g1)
    g1.evaluate("() => { fall(world, me); window.outAt = me.outRt; }")
    at = g1.evaluate("outAt")
    host.wait_for_function(f"{KID.format(gid)}.out", timeout=5000)
    assert host.evaluate(f"{KID.format(gid)}.outRt") == pytest.approx(at, abs=0.01)
    g2.wait_for_function(f"{KID.format(gid)}.out", timeout=5000)
    # Out, the phone only watches: its stick no longer moves anything, the round goes on.
    assert g1.evaluate("playing()") is False
    g1.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    assert g1.evaluate("stick") is None
    g1.wait_for_timeout(400)
    assert g1.evaluate("mode") == "netplay"
    assert host.evaluate("world.ph") == "play"
    assert host.errors == g1.errors == g2.errors == []


def test_the_host_keeps_a_guests_shove_cooldown_even_across_a_reload(kids):
    # Review finding (#488): a guest sending `sh` again and again must not shove more often than
    # SHOVE_CD; the host keeps the cooldown on its own clock, and a reload does not reset it.
    host, guest = room(kids)
    start([host, guest])
    host.evaluate("() => { brains = brains.map(() => null); }")
    host.wait_for_function("world.ph === 'play'", timeout=15000)
    gid = gid_of(guest)
    host.evaluate("() => { window.tries = 0; const st = shoveTarget; shoveTarget = (...a) => { tries++; return st(...a); }; }")
    sh = f"() => hostShove({{ t: 'sh', round: net.round, h: {KID.format(gid)}.own, f: 0 }}, {gid})"
    for _ in range(4):
        host.evaluate(sh)
    assert host.evaluate("tries") == 1
    t0 = host.evaluate(f"net.recs.get({gid}).shT")
    guest.reload()
    guest.wait_for_function("mode === 'netplay' && me && net.h >= 0", timeout=15000)
    if host.evaluate(f"world.rt - {t0}") < 1.2:
        host.evaluate(sh)
        assert host.evaluate("tries") == 1   # still cooling down after the reload
    host.wait_for_function(f"world.rt > {t0} + 1.5", timeout=10000)
    host.evaluate(sh)
    host.evaluate(sh)
    assert host.evaluate("tries") == 2   # one more once the cooldown is over, and only one
    assert host.errors == guest.errors == []
