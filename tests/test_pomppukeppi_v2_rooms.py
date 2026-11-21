"""Pomppukeppi v2 with friends (#482): the host runs the board, the guests send their stick."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/pomppukeppi/v2/"
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# On the host: my hare wins erä after erä until the match is over.
HOST_WINS = """() => { for (let k = 0; k < 3 && !world.over; k++) {
  world.ph = 'play'; world.t = ERA_T; me.pts = 20 + k; step(world, 0.01); step(world, ERA_PAUSE + 0.1); } }"""
HARE = "world.hares.find(h => h.id === {})"


@pytest.fixture
def hares(site, browser):
    shutil.copytree(ROOT / "games" / "pomppukeppi", site.games / "pomppukeppi")
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


def still(host):
    """Nothing moves on the host but what a test moves: the computer's hares stand, no boxes."""
    host.evaluate("() => { brains = brains.map(() => null); world.cashT = 99; world.qT = 99; world.cash = null; world.qbox = null; }")


def test_three_phones_paint_one_board_and_the_next_match_starts_clean(hares):
    host, g1, g2 = room(hares, 3)
    # The host picks the board on the room screen; a guest sees who does.
    assert host.locator("#ppk-room button").count() == 3
    assert "valitsee kentän" in g1.locator("#ppk-room").inner_text()
    start([host, g1, g2])
    for p in (host, g1, g2):
        assert p.evaluate("world.hares.length") == 4   # three phones and one of the computer's
        assert p.evaluate("world.hares.filter(h => h.kind === 'cpu').length") == 1
        assert p.evaluate("new Set(world.hares.map(h => h.col)).size") == 4
    still(host)
    gid = json.dumps(g1.evaluate("AiPelitRooms.me"))
    # The guest (bottom-right corner) holds left: its hare hops left on the host, painting.
    x0 = host.evaluate(f"{HARE.format(gid)}.x")
    g1.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    g1.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    host.wait_for_function(f"{HARE.format(gid)}.x <= {x0} - 2", timeout=5000)
    g1.evaluate(TOUCH, ["pointerup", 7, 140, 560])
    i = host.evaluate(f"world.hares.indexOf({HARE.format(gid)})")
    assert host.evaluate(f"tileAt(world, {x0} - 1, world.n - 1)") == i
    # A cash-in on the host is seen on every phone.
    host.evaluate(f"""() => {{ const h = {HARE.format(gid)}; world.cash = {{ x: h.x, y: h.y - 1 }};
      Object.assign(h, {{ fx: h.x, fy: h.y, y: h.y - 1, p: 0.99 }}); step(world, 0.02); }}""")
    for p in (g1, g2):
        p.wait_for_function(f"{HARE.format(gid)}.cashN === 1 && {HARE.format(gid)}.pts >= 3", timeout=5000)
    # The host's hare wins the match: one result everywhere, nothing saved anywhere.
    for p in (host, g1, g2):
        p.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    host.evaluate(HOST_WINS)
    for p in (host, g1, g2):
        p.wait_for_function("mode === 'end'", timeout=10000)
        assert p.locator("#again").inner_text() == "Takaisin huoneeseen"
        assert p.locator("#toMenu").is_hidden()
        assert p.evaluate("sent") == []
        assert p.evaluate("['auki', 'ennatys', 'kesken1'].map(k => localStorage.getItem('ai-pelit:pomppukeppi:' + k))") == [None, None, None]
    assert host.locator("#endTitle").inner_text() == "Voitit ottelun!"
    assert g1.locator("#endTitle").inner_text() == "Testi1 voitti ottelun"
    rows = [p.evaluate("result.rows.map(r => r.id + r.wins)") for p in (host, g1, g2)]
    assert rows[0] == rows[1] == rows[2]
    first = host.evaluate("net.round")
    for p in (g1, g2, host):
        p.click("#again")
    host.wait_for_function("document.getElementById('aipr-start') && !document.getElementById('aipr-start').disabled")
    host.click("#aipr-start")
    for p in (host, g1, g2):
        p.wait_for_function(f"net && net.round !== {json.dumps(first)} && world && me && me.wins === 0", timeout=12000)
    # A state of the old round is dropped, however high its count; so is an older one of this round.
    g1.wait_for_function("net.lastSeq > 0")
    seq = g1.evaluate("net.lastSeq")
    host.evaluate("(round) => { const m = hostState(); m.round = round; m.seq = 1e9; m.hk.forEach(a => { a[12] = 1; }); AiPelitRooms.send(m); }", first)
    host.evaluate("() => { const m = hostState(); m.seq = 1; m.hk.forEach(a => { a[12] = 1; }); AiPelitRooms.send(m); }")
    g1.wait_for_timeout(500)
    assert g1.evaluate("world.hares.map(h => h.wins)") == [0, 0, 0, 0]
    assert g1.evaluate("net.lastSeq") >= seq
    assert host.errors == g1.errors == g2.errors == []


@pytest.mark.parametrize("lag", [100, 200])
def test_a_guest_holding_one_way_on_a_slow_link_is_never_snapped_back(hares, lag):
    # Design review note (#482): the guest's own hops are matched to the host's hop by hop, so
    # holding one direction across many hops, with the host's word arriving late, keeps going.
    host, guest = room(hares)
    start([host, guest])
    still(host)
    guest.wait_for_function("net.myOwn >= 0 && world.ph === 'play'")
    # Both ways late by `lag` ms on the guest's side; then count the snaps and watch x.
    guest.evaluate("""(lag) => {
      const send = AiPelitRooms.send.bind(AiPelitRooms);
      AiPelitRooms.send = (m, to) => setTimeout(() => send(m, to), lag);
      const gs = guestState; guestState = m => setTimeout(() => gs(m), lag);
      const sn = snapMine; window.snaps = 0; snapMine = a => { snaps++; sn(a); };
      window.xs = []; (function rec() { xs.push(harePos(me).x); if (xs.length < 400) requestAnimationFrame(rec); })();
    }""", lag)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    x0 = guest.evaluate("me.x")
    assert x0 == 7
    guest.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    # Six hops left, to the square next to the computer's hare in the bottom-left corner.
    host.wait_for_function(f"{HARE.format(gid)}.x === 1", timeout=6000)
    guest.wait_for_timeout(lag * 2 + 400)
    guest.evaluate(TOUCH, ["pointerup", 7, 140, 560])
    assert guest.evaluate("me.x") == 1
    assert guest.evaluate("snaps") == 0
    xs = guest.evaluate("xs")
    assert all(b <= a + 1e-6 for a, b in zip(xs, xs[1:])), "my hare went back to the right"
    assert host.errors == guest.errors == []


def test_a_hop_the_host_blocked_snaps_the_guest_to_the_host(hares):
    host, guest = room(hares)
    start([host, guest])
    still(host)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    guest.wait_for_function("net.myOwn >= 0 && world.ph === 'play'")
    guest.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    guest.wait_for_function("me.x <= 5", timeout=4000)
    # The host's word: my hare bounced in place at hop n where my phone hopped on.
    guest.evaluate("() => { const sn = snapMine; window.snaps = 0; snapMine = a => { snaps++; sn(a); }; }")
    got = guest.evaluate(f"""() => {{
      const m = {{ t: 's', round: net.round, seq: net.lastSeq + 1000, b: world.board, ph: 'play', cd: 0, era: world.era, tt: world.t,
        pause: 0, win: null, ew: null, cash: null, q: null, tiles: world.tiles.slice(),
        hk: world.hares.map(h => [h.id, h.name, h.col, h.kind === 'cpu' ? 1 : 0, h.own, h.x, h.y, h.fx, h.fy, h.p, h.hopT,
          h.pts, h.wins, h.best, h.fast, h.stun, h.hopN, h.bumpN, h.cashN, h.lastCash, h.got, h.gotK || '', 0]) }};
      const a = m.hk[world.hares.indexOf(me)], e = net.hist[net.hist.length - 1];
      a[4] = net.myOwn; a[5] = a[7] = e.fx; a[6] = a[8] = e.fy; a[16] = e.n; a[9] = 0.4;
      guestState(m);
      return [snaps, me.x === e.fx && me.fx === e.fx, net.hist.length];
    }}""")
    assert got == [1, True, 1]
    guest.evaluate(TOUCH, ["pointerup", 7, 140, 560])
    assert host.errors == guest.errors == []


def test_a_flick_reaches_the_host_for_its_landing(hares):
    host, guest = room(hares)
    start([host, guest])
    still(host)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.wait_for_function(f"net.recs.find(r => r.id === {gid}).inT > 0")
    # A flick up for the landing that ends hop n, then "nothing held" arriving first at the host.
    got = host.evaluate(f"""() => {{
      const h = {HARE.format(gid)}, rec = net.recs.find(r => r.id === {gid});
      hostInput({{ t: 'i', round: net.round, w: h.own, d: -1, f: 3, n: h.hopN, c: h.col }}, {gid});
      hostInput({{ t: 'i', round: net.round, w: h.own, d: -1, f: -1, n: h.hopN, c: h.col }}, {gid});
      // An old take-over's message moves nothing.
      hostInput({{ t: 'i', round: net.round, w: h.own - 1, d: 2, f: -1, n: h.hopN, c: h.col }}, {gid});
      netTick(0.001);
      return [rec.d, h.want];
    }}""")
    assert got == [-1, 3]
    y0 = host.evaluate(f"{HARE.format(gid)}.y")
    host.wait_for_function(f"{HARE.format(gid)}.y === {y0} - 1", timeout=3000)
    # Used once: the next hop is in place.
    host.wait_for_timeout(800)
    assert host.evaluate(f"{HARE.format(gid)}.y") == y0 - 1
    assert host.errors == guest.errors == []


def test_a_guest_reloaded_mid_match_takes_its_hare_back(hares):
    host, guest = room(hares)
    start([host, guest])
    still(host)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.evaluate(f"(() => {{ {HARE.format(gid)}.pts = 4; }})()")
    own = host.evaluate(f"{HARE.format(gid)}.own")
    guest.reload()
    guest.wait_for_function("mode === 'netplay' && me && net.myOwn >= 0", timeout=15000)
    assert host.evaluate(f"{HARE.format(gid)}.own") == own + 1
    assert guest.evaluate("[net.myOwn, me.pts]") == [own + 1, 4]
    # Its finger drives the hare again.
    x0 = host.evaluate(f"{HARE.format(gid)}.x")
    guest.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    host.wait_for_function(f"{HARE.format(gid)}.x < {x0}", timeout=5000)
    assert host.errors == guest.errors == []


def test_a_silent_guest_s_stick_counts_as_let_go(hares):
    host, guest = room(hares)
    start([host, guest])
    still(host)
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    guest.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    host.wait_for_function(f"net.recs.find(r => r.id === {gid}).d === 2", timeout=3000)
    guest.evaluate("() => { AiPelitRooms.send = () => {}; }")   # the guest's messages stop
    host.wait_for_function(f"net.recs.find(r => r.id === {gid}).d === -1", timeout=3000)
    x = host.evaluate(f"{HARE.format(gid)}.x")
    host.wait_for_timeout(800)
    assert host.evaluate(f"{HARE.format(gid)}.x") == x
    assert host.errors == guest.errors == []


def test_the_computer_takes_an_away_phone_and_gives_it_back(hares):
    host, guest = room(hares)
    start([host, guest])
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    i = host.evaluate(f"net.recs.findIndex(r => r.id === {gid})")
    hares.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"net.recs[{i}].drive && !AiPelitRooms.paused")
    own = host.evaluate(f"world.hares[{i}].own")
    # A direction from before the switch (the old take-over count) is ignored.
    host.evaluate(f"hostInput({{ t: 'i', round: net.round, w: {own} - 1, d: 0, f: -1, n: 0 }}, {gid})")
    assert host.evaluate(f"net.recs[{i}].d") != 0
    hares.relay.back(guest)
    host.wait_for_function(f"!net.recs[{i}].drive", timeout=15000)
    guest.wait_for_function(f"net.myOwn >= {own + 1} && mode === 'netplay'", timeout=10000)
    host.evaluate(HOST_WINS)
    guest.wait_for_function("mode === 'end'", timeout=10000)
    assert guest.evaluate("result.helped")
    assert "Tietokone" in guest.locator("#endNote").inner_text()
    assert host.errors == guest.errors == []


def test_the_other_hares_glide_on_a_guest(hares):
    # lib/sulava-1 (#480): the host's hare, seen on the guest, moves in small steps every frame.
    host, guest = room(hares)
    start([host, guest])
    still(host)
    guest.wait_for_function("net.myOwn >= 0 && world.ph === 'play'")
    hid = json.dumps(host.evaluate("AiPelitRooms.me"))
    guest.evaluate(f"""() => {{
      window.gx = []; const h = {HARE.format(hid)};
      (function rec() {{ const p = harePos(h); gx.push([p.x, p.y, p.z]); if (gx.length < 120) requestAnimationFrame(rec); }})();
    }}""")
    host.evaluate(TOUCH, ["pointerdown", 7, 150, 500])
    host.evaluate(TOUCH, ["pointermove", 7, 150, 560])
    guest.wait_for_function("gx.length >= 120", timeout=8000)
    host.evaluate(TOUCH, ["pointerup", 7, 150, 560])
    gx = guest.evaluate("gx")
    assert guest.evaluate(f"!!{HARE.format(hid)}.draw")
    assert gx[-1][1] - gx[0][1] >= 2, "the host's hare did not come down the board"
    steps = [abs(b[1] - a[1]) for a, b in zip(gx, gx[1:])]
    assert max(steps) < 0.3, max(steps)
    # Not stood still at each landing until the next state: few frames in a row without moving.
    moved = [k for k, s in enumerate(steps) if s > 1e-4]
    run = longest = 0
    for s in steps[moved[0]:moved[-1]]:
        run = run + 1 if s < 1e-4 else 0
        longest = max(longest, run)
    assert longest <= 4, longest
    assert host.errors == guest.errors == []


def test_a_late_flick_on_a_slow_link_still_turns_the_guest_without_a_snap(hares):
    # The guest's hare runs behind the host's: a flick let go late in hop n reaches the host after
    # that landing, and is used at the next one; the guest only renumbers its hops.
    host, guest = room(hares)
    start([host, guest])
    still(host)
    guest.wait_for_function("net.myOwn >= 0 && world.ph === 'play'")
    guest.evaluate("""() => {
      const send = AiPelitRooms.send.bind(AiPelitRooms);
      AiPelitRooms.send = (m, to) => setTimeout(() => send(m, to), 200);
      const gs = guestState; guestState = m => setTimeout(() => gs(m), 200);
      const sn = snapMine; window.snaps = 0; snapMine = a => { snaps++; sn(a); };
    }""")
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    guest.wait_for_timeout(700)
    x0 = guest.evaluate("me.x")
    guest.wait_for_function("me.p > 0.6", timeout=2000)
    guest.evaluate(TOUCH, ["pointerdown", 7, 200, 560])
    guest.evaluate(TOUCH, ["pointermove", 7, 140, 560])
    guest.evaluate(TOUCH, ["pointerup", 7, 140, 560])
    host.wait_for_function(f"{HARE.format(gid)}.x === {x0} - 1 && {HARE.format(gid)}.p > 0.9", timeout=3000)
    guest.wait_for_timeout(900)
    assert guest.evaluate("me.x") == x0 - 1
    assert host.evaluate(f"{HARE.format(gid)}.x") == x0 - 1
    assert guest.evaluate("snaps") == 0
    assert host.errors == guest.errors == []


def test_every_phone_sees_the_same_snowball_fly(hares):
    host, g1 = room(hares, 2)
    start([host, g1])
    still(host)
    gid = json.dumps(g1.evaluate("AiPelitRooms.me"))
    # The host's hare takes a snowball; the guest's hare leads.
    host.evaluate(f"""() => {{ const lead = {HARE.format(gid)}; lead.pts = 9; world.rand = () => 0.1;
      world.qbox = {{ x: me.x + 1, y: me.y }}; Object.assign(me, {{ fx: me.x, fy: me.y, x: me.x + 1, p: 0.99 }}); step(world, 0.02); }}""")
    i = host.evaluate(f"world.hares.indexOf({HARE.format(gid)})")
    g1.wait_for_function(f"world.balls.length === 1 && world.balls[0].to === {i}", timeout=3000)
    assert g1.evaluate(f"{HARE.format(gid)}.stun") == 0   # not yet: it is still flying
    # Drawn on the guest's screen too, and gone with a puff when the host says it hit.
    g1.wait_for_function("!V3 || V3.balls[0].b.visible", timeout=3000)
    g1.wait_for_function(f"world.balls.length === 0 && {HARE.format(gid)}.stun > 0 && puffs.length === 1", timeout=3000)
    host.wait_for_function(f"world.balls.length === 0 && {HARE.format(gid)}.stun > 0")
    assert host.errors == [] and g1.errors == []
