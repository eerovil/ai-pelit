"""Pulkkamäki v4 with friends (#475, #480): everyone down the same hill at once, the host keeps the end."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/pulkkamaki/v4/"
# My sled straight to just above the finish line, so the run ends in seconds.
NEAR_END = "(() => { me.s = hill.len - 4; me.x = centreX(hill, me.s); me.y = groundAt(hill, me.s, me.x); me.v = 12; me.yaw = 0; me.air = false; })()"
# The host's computer sledders the same way.
CPU_NEAR_END = "net.sleds.filter(r => r.kind === 'cpu').forEach(r => { const sl = r.sl; sl.s = hill.len - 4; sl.x = centreX(hill, sl.s); sl.y = groundAt(hill, sl.s, sl.x); sl.v = 12; sl.yaw = 0; })"


@pytest.fixture
def sledders(site, browser):
    shutil.copytree(ROOT / "games" / "pulkkamaki", site.games / "pulkkamaki")
    site.build()
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on("pageerror", lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.wait_for_function("V3 || no3d", timeout=20000)
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
        p.wait_for_function("mode === 'run' && me", timeout=10000)


def test_two_phones_go_down_together_and_get_one_result(sledders):
    host, guest = room(sledders)
    # The host picks the hill on the room screen; a guest only sees who does.
    assert host.locator("#pulkka-room button").count() == 5   # every hill, from v4 (#517) five
    assert "valitsee mäen" in guest.locator("#pulkka-room").inner_text()
    start([host, guest])
    for p in (host, guest):
        assert p.evaluate("sleds.length") == 4   # the two of us and two of the computer's
        assert p.evaluate("hill.n") == 1
    # Each phone sees the other's sled come down the hill.
    gid = guest.evaluate("AiPelitRooms.me")
    guest.wait_for_timeout(800)
    seen = host.evaluate(f"recOf({json.dumps(gid)}).sl.s")
    assert seen == pytest.approx(guest.evaluate("me.s"), abs=6)
    assert seen > 1
    # Everyone over the line: the host ends the run, both phones show the same order.
    guest.evaluate(NEAR_END)
    host.evaluate(NEAR_END)
    host.evaluate(CPU_NEAR_END)
    for p in (host, guest):
        p.wait_for_function("mode === 'end'", timeout=15000)
        assert p.locator("#again").inner_text() == "Takaisin huoneeseen"
        assert p.locator("#toMenu").is_hidden()
    rows = [p.evaluate("result.rows.map(r => r.points)") for p in (host, guest)]
    assert rows[0] == rows[1]
    gp = guest.evaluate("me.points")
    assert guest.evaluate("result.pts") == gp
    assert guest.evaluate("+(localStorage.getItem('ai-pelit:pulkkamaki:ennatys-1') || 0)") == gp
    first = json.dumps(host.evaluate("net.round"))
    # Back to the room screen, ready for the next run.
    guest.click("#again")
    guest.wait_for_function("document.getElementById('aipr-room') && !document.getElementById('aipr-room').hidden")
    host.click("#again")
    # A second run: a new round number, fresh sleds, the old round's messages ignored.
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function(f"net && net.round !== {first} && (mode === 'count' || mode === 'run') && me && me.points === 0 && !me.fin", timeout=10000)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    fake = "(round) => { net.sendT = 1e9; const r = recOf(AiPelitRooms.me); const a = pack(r.sl); a[10] = 9999; AiPelitRooms.send({ t: 'p', round, w: r.own, a }); }"
    guest.evaluate(fake, json.loads(first))
    host.wait_for_timeout(400)
    assert host.evaluate(f"recOf({gid}).sl.points") == 0
    guest.evaluate(fake, guest.evaluate("net.round"))
    host.wait_for_function(f"recOf({gid}).sl.points === 9999", timeout=3000)
    assert host.errors == guest.errors == []


def test_a_guest_sees_the_finish_clock_after_the_first_is_down(sledders):
    host, guest = room(sledders)
    start([host, guest])
    host.evaluate(NEAR_END)
    host.wait_for_function("net.firstFin !== null", timeout=10000)
    guest.wait_for_function("lateLeft() !== null && lateLeft() <= 30", timeout=5000)
    assert host.errors == guest.errors == []


def test_a_guest_reloaded_mid_run_carries_on_from_where_it_was(sledders):
    host, guest = room(sledders)
    start([host, guest])
    guest.evaluate("me.s = 120; me.x = centreX(hill, 120); me.y = groundAt(hill, 120, me.x);")
    host.wait_for_function(f"recOf({json.dumps(guest.evaluate('AiPelitRooms.me'))}).sl.s > 110")
    guest.reload()
    guest.wait_for_function("mode === 'run' && me", timeout=15000)
    # The host's record of the sled, not a new start at the top.
    assert guest.evaluate("me.s") > 100
    assert host.errors == guest.errors == []


def test_the_computer_takes_an_away_phone_and_its_result_is_not_saved(sledders):
    host, guest = room(sledders)
    start([host, guest])
    gid = guest.evaluate("AiPelitRooms.me")
    sledders.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"recOf({json.dumps(gid)}).drive && !AiPelitRooms.paused")
    # The host's computer now drives the guest's sled down the hill.
    s0 = host.evaluate(f"recOf({json.dumps(gid)}).sl.s")
    host.wait_for_timeout(800)
    assert host.evaluate(f"recOf({json.dumps(gid)}).sl.s") > s0
    host.evaluate(f"(() => {{ const sl = recOf({json.dumps(gid)}).sl; sl.s = hill.len - 4; sl.x = centreX(hill, sl.s); sl.y = groundAt(hill, sl.s, sl.x); sl.v = 12; sl.yaw = 0; }})()")
    host.evaluate(NEAR_END)
    host.evaluate(CPU_NEAR_END)
    host.wait_for_function("mode === 'end'", timeout=15000)
    assert host.evaluate(f"net.res.find(r => r.id === {json.dumps(gid)}).m") == 1
    # Back again: the phone hears the result, marked as the computer's, and saves nothing.
    sledders.relay.back(guest)
    guest.wait_for_function("mode === 'end'", timeout=15000)
    assert guest.evaluate("result.helped")
    assert "Tietokone" in guest.locator("#endNote").inner_text()
    assert guest.evaluate("localStorage.getItem('ai-pelit:pulkkamaki:ennatys-1')") is None
    assert host.errors == guest.errors == []


def test_a_phone_back_after_the_computer_drove_carries_on_from_the_computers_run(sledders):
    host, guest = room(sledders)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.wait_for_function(f"recOf({gid}).lastA")
    sledders.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"recOf({gid}).drive && !AiPelitRooms.paused")
    host.wait_for_function(f"recOf({gid}).sl.s > 60", timeout=20000)
    sledders.relay.back(guest)
    host.wait_for_function(f"!recOf({gid}).drive", timeout=15000)
    # The host keeps the computer's run, and the phone takes it up from there.
    driven = host.evaluate(f"recOf({gid}).sl.s")
    assert driven > 60
    guest.wait_for_function(f"me.s > {driven - 5}", timeout=10000)
    assert host.errors == guest.errors == []


def test_a_phone_in_the_air_reloaded_keeps_what_the_jump_has_earned(sledders):
    host, guest = room(sledders)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    # A flip done high in the air, not yet landed: its points come on landing.
    guest.evaluate("(() => { me.s = 120; me.x = centreX(hill, 120); me.y = groundAt(hill, 120, me.x) + 60; me.vy = 15; me.air = true; me.jump = [{ type: 'front', pts: 300 }]; })()")
    host.wait_for_function(f"recOf({gid}).sl.jump.length === 1 && recOf({gid}).sl.air")
    guest.reload()
    guest.wait_for_function("mode === 'run' && me", timeout=15000)
    assert guest.evaluate("me.air && me.jump.length === 1 && me.points === 0")
    guest.wait_for_function("!me.air", timeout=15000)
    assert guest.evaluate("me.points") > 0
    assert host.errors == guest.errors == []


def test_a_phone_back_only_after_the_end_saves_on_the_hosts_hill(sledders):
    host, guest = room(sledders)
    host.evaluate("open = 2; roomControls()")
    host.locator("#pulkka-room button").nth(1).click()
    assert host.evaluate("hillN") == 2
    start([host, guest])
    assert guest.evaluate("hill.n") == 2
    gid = guest.evaluate("AiPelitRooms.me")
    guest.evaluate(NEAR_END)
    host.wait_for_function(f"recOf({json.dumps(gid)}).sl.fin", timeout=10000)
    pts = host.evaluate(f"recOf({json.dumps(gid)}).sl.points")
    # Gone before the end, and back on a fresh page only once the host has the result.
    sledders.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.evaluate(NEAR_END)
    host.evaluate(CPU_NEAR_END)
    host.wait_for_function("mode === 'end'", timeout=15000)
    guest.reload()
    guest.wait_for_function("V3 || no3d", timeout=20000)
    sledders.relay.blocked.discard(gid)
    guest.wait_for_function("mode === 'end' && net && net.hill === 2", timeout=20000)
    assert guest.evaluate("+localStorage.getItem('ai-pelit:pulkkamaki:ennatys-2')") == pts
    assert guest.evaluate("localStorage.getItem('ai-pelit:pulkkamaki:ennatys-1')") is None
    assert host.errors == guest.errors == []


def test_three_phones_share_one_result_and_the_next_round_starts_fresh(sledders):
    pages = room(sledders, 3)
    start(pages)
    ids = pages[0].evaluate("net.sleds.map(r => r.id)")
    assert len(ids) == 4   # three phones and one of the computer's
    for p in pages:
        assert p.evaluate("net.sleds.map(r => r.id)") == ids
        p.evaluate(NEAR_END)
    pages[0].evaluate(CPU_NEAR_END)
    for p in pages:
        p.wait_for_function("mode === 'end'", timeout=15000)
    rows = [p.evaluate("result.rows.map(r => [r.id, r.points])") for p in pages]
    assert rows[0] == rows[1] == rows[2]
    first = json.dumps(pages[0].evaluate("net.round"))
    for p in pages:
        p.click("#again")
    pages[0].click("#aipr-start")
    for p in pages:
        p.wait_for_function(f"net && net.round !== {first} && me && !me.fin && me.points === 0", timeout=10000)
        assert p.evaluate("net.sleds.map(r => r.id)") == ids
        assert p.evaluate("net.sleds.every(r => !r.sl.fin && r.sl.points === 0 && r.own === 0)")
    for p in pages:
        assert p.errors == []


# A grab held high in the air, long enough to count, with a flip already done in the same jump.
IN_A_GRAB = "(() => { me.s = 120; me.x = centreX(hill, 120); me.y = groundAt(hill, 120, me.x) + 40; me.vy = 8; me.air = true; me.jump = [{ type: 'front', pts: 300 }]; me.grab = true; me.grabT = 0.6; })()"


def test_a_phone_reloaded_in_the_middle_of_a_grab_keeps_its_points_and_lands(sledders):
    # v2 (#475): the finger holding the grab is gone with the old page, so the grab is let go when
    # the phone comes back, and counts; before, the sled could never let go and fell on landing.
    host, guest = room(sledders)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    guest.evaluate(IN_A_GRAB)
    host.wait_for_function(f"recOf({gid}).sl.grab && recOf({gid}).sl.air")
    guest.reload()
    guest.wait_for_function("mode === 'run' && me", timeout=15000)
    assert guest.evaluate("!me.grab && me.jump.map(j => j.type).join()") == "front,grab"
    guest.wait_for_function("!me.air", timeout=15000)
    assert guest.evaluate("[me.fallT, me.points > 0]") == [0, True]
    assert host.errors == guest.errors == []


def test_the_computer_taking_a_sled_mid_grab_lets_go_and_keeps_its_points(sledders):
    # v2 (#475): the computer never grabs nor lets go, so a grab it took over always fell.
    host, guest = room(sledders)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    guest.evaluate(IN_A_GRAB)
    host.wait_for_function(f"recOf({gid}).sl.grab && recOf({gid}).sl.air")
    sledders.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"recOf({gid}).drive && !AiPelitRooms.paused")
    assert host.evaluate(f"(sl => !sl.grab && sl.jump.map(j => j.type).slice(0, 2).join())(recOf({gid}).sl)") == "front,grab"
    host.wait_for_function(f"!recOf({gid}).sl.air", timeout=15000)
    assert host.evaluate(f"(recOf({gid}).sl.pop || {{}}).text") != "Päästä irti ennen alastuloa!"
    assert host.evaluate(f"recOf({gid}).sl.points") > 0
    assert host.errors == guest.errors == []
