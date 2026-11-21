"""Jäälautta v1 with friends (#478): the host runs the floe, the guests send their fingers."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/jaalautta/v1/"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# On the host: every seal but the host's own falls in, erä after erä, until the match is over.
HOST_WINS = """() => { for (let k = 0; k < 3 && !world.over; k++) {
  world.ph = 'play'; world.seals.filter(s => s !== me).forEach(s => fall(world, s)); step(world, ERA_PAUSE + 0.2); } }"""
SEAL = "world.seals.find(s => s.id === {})"


@pytest.fixture
def seals(site, browser):
    shutil.copytree(ROOT / "games" / "jaalautta", site.games / "jaalautta")
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


def test_three_phones_play_one_floe_and_the_next_match_starts_clean(seals):
    host, g1, g2 = room(seals, 3)
    # The host picks the floe on the room screen; a guest sees who does.
    assert host.locator("#jaa-room button").count() == 5
    assert "valitsee lautan" in g1.locator("#jaa-room").inner_text()
    start([host, g1, g2])
    for p in (host, g1, g2):
        assert p.evaluate("world.seals.length") == 4   # three phones and one of the computer's
        assert p.evaluate("world.seals.filter(s => s.kind === 'cpu').length") == 1
    gid = json.dumps(g1.evaluate("AiPelitRooms.me"))
    # The guest's finger moves its seal on the host's floe.
    x0 = host.evaluate(f"{SEAL.format(gid)}.x")
    g1.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    g1.evaluate(TOUCH, ["pointermove", 7, 160, 560])
    host.wait_for_function(f"{SEAL.format(gid)}.x > {x0} + 0.5", timeout=5000)
    g1.evaluate(TOUCH, ["pointerup", 7, 160, 560])
    # A lunge pressed on the guest is counted once on the host.
    b = g1.evaluate("button()")
    g1.evaluate(TOUCH, ["pointerdown", 8, b["x"], b["y"]])
    host.wait_for_function(f"{SEAL.format(gid)}.lunges === 1", timeout=5000)
    host.wait_for_timeout(400)
    assert host.evaluate(f"{SEAL.format(gid)}.lunges") == 1
    # A knock-out on the host is seen on every phone.
    host.evaluate("fall(world, world.seals.find(s => s.kind === 'cpu'))")
    for p in (g1, g2):
        p.wait_for_function("world.seals.find(s => s.kind === 'cpu').out > 0", timeout=5000)
    # The last knock-out of an erä: every guest sees all of them in the water through the pause.
    host.evaluate("() => { world.seals.filter(s => s !== me).forEach(s => fall(world, s)); step(world, 0.02); }")
    for p in (g1, g2):
        p.wait_for_function("world.ph === 'erä'", timeout=5000)
        assert p.evaluate(f"world.seals.filter(s => s.id !== {json.dumps(host.evaluate('me.id'))}).every(s => s.out > 0)")
    # A lunge between erät: the guest's button does nothing, and a late one reaching the host is
    # counted but never lunges when the next erä starts.
    l0 = g1.evaluate("net.myL")
    g1.evaluate(TOUCH, ["pointerdown", 9, b["x"], b["y"]])
    assert g1.evaluate("net.myL") == l0
    host.evaluate(f"(() => {{ const s = {SEAL.format(gid)}; hostInput({{ t: 'i', round: net.round, w: s.own, x: 0, y: 0, l: s.lunges + 1 }}, {gid}); }})()")
    assert host.evaluate(f"(() => {{ const s = {SEAL.format(gid)}; return [s.want === s.lunges, s.lunges]; }})()") == [True, 2]
    g1.wait_for_function("net.myL === 2", timeout=5000)
    # The host's seal wins the match: one result everywhere, nothing saved anywhere.
    for p in (host, g1, g2):
        p.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    host.evaluate(HOST_WINS)
    for p in (host, g1, g2):
        p.wait_for_function("mode === 'end'", timeout=10000)
        assert p.locator("#again").inner_text() == "Takaisin huoneeseen"
        assert p.locator("#toMenu").is_hidden()
        assert p.evaluate("sent") == []
        assert p.evaluate("['voitot', 'auki', 'kesken1'].map(k => localStorage.getItem('ai-pelit:jaalautta:' + k))") == [None, None, None]
    assert host.locator("#endTitle").inner_text() == "Voitit ottelun!"
    assert g1.locator("#endTitle").inner_text() == "Testi1 voitti ottelun"
    rows = [p.evaluate("result.rows.map(r => r.id + r.stars)") for p in (host, g1, g2)]
    assert rows[0] == rows[1] == rows[2]
    first = host.evaluate("net.round")
    for p in (g1, g2, host):
        p.click("#again")
    host.wait_for_function("document.getElementById('aipr-start') && !document.getElementById('aipr-start').disabled")
    host.click("#aipr-start")
    for p in (host, g1, g2):
        p.wait_for_function(f"net && net.round !== {json.dumps(first)} && world && me && me.stars === 0 && me.lunges === 0", timeout=12000)
    # A state of the old round is dropped, however high its count; so is an older one of this round.
    g1.wait_for_function("net.lastSeq > 0")
    seq = g1.evaluate("net.lastSeq")
    host.evaluate("(round) => { const m = hostState(); m.round = round; m.seq = 1e9; m.sk.forEach(a => { a[22] = 2; }); AiPelitRooms.send(m); }", first)
    host.evaluate("() => { const m = hostState(); m.seq = 1; m.sk.forEach(a => { a[22] = 2; }); AiPelitRooms.send(m); }")
    g1.wait_for_timeout(500)
    assert g1.evaluate("world.seals.map(s => s.stars)") == [0, 0, 0, 0]
    assert g1.evaluate("net.lastSeq") >= seq
    assert host.errors == g1.errors == g2.errors == []


def test_a_guest_reloaded_mid_match_takes_its_seal_back(seals):
    host, guest = room(seals)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.evaluate(f"(() => {{ const s = {SEAL.format(gid)}; s.x = 2; s.y = 2; s.stars = 1; }})()")
    own = host.evaluate(f"{SEAL.format(gid)}.own")
    guest.reload()
    guest.wait_for_function("mode === 'netplay' && me && net.myOwn >= 0", timeout=15000)
    assert host.evaluate(f"{SEAL.format(gid)}.own") == own + 1
    assert guest.evaluate("[net.myOwn, me.stars]") == [own + 1, 1]
    assert abs(guest.evaluate("me.x") - 2) < 2.5
    # Its finger drives the seal again.
    x0 = host.evaluate(f"{SEAL.format(gid)}.x")
    guest.evaluate(TOUCH, ["pointerdown", 7, 100, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 160, 560])
    host.wait_for_function(f"{SEAL.format(gid)}.x > {x0} + 0.5", timeout=5000)
    assert host.errors == guest.errors == []


def test_the_computer_takes_an_away_phone_and_gives_it_back(seals):
    host, guest = room(seals)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    i = host.evaluate(f"net.recs.findIndex(r => r.id === {gid})")
    seals.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"net.recs[{i}].drive && !AiPelitRooms.paused")
    own = host.evaluate(f"world.seals[{i}].own")
    # An input from before the switch (the old take-over count) moves nothing.
    host.evaluate(f"hostInput({{ t: 'i', round: net.round, w: {own} - 1, x: 1, y: 0, l: 5 }}, {gid})")
    assert host.evaluate(f"world.seals[{i}].lunges") < 5
    seals.relay.back(guest)
    host.wait_for_function(f"!net.recs[{i}].drive", timeout=15000)
    guest.wait_for_function(f"net.myOwn >= {own + 1} && mode === 'netplay'", timeout=10000)
    # Back on the floe it counts its lunges on from the host's.
    lunges = host.evaluate(f"world.seals[{i}].lunges")
    assert guest.evaluate("net.myL") >= lunges
    host.evaluate(HOST_WINS)
    guest.wait_for_function("mode === 'end'", timeout=10000)
    assert guest.evaluate("result.helped")
    assert "Tietokone" in guest.locator("#endNote").inner_text()
    assert host.errors == guest.errors == []
