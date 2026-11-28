"""Pingis v1 with a friend (#502): two phones, one game; each judges the flights coming its way."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/pingis/v3/"
# A bat that goes where the ball will cross its line, on a timer, as a finger would.
AUTO = """() => { clearInterval(window.auto); window.auto = setInterval(() => {
  if (!net || !game || !bats) return;
  const f = game.flight, s = sgn(view); let tx = 0;
  if (f && f.by !== view && !f.over) { const q = predict(f, view, 0.35); if (q) tx = q.x; }
  bats[view].tx = tx; bats[view].tz = s * (HL + 0.35); }, 8); }"""
STOP = "() => { clearInterval(window.auto); bats[view].tx = 1.1; }"


@pytest.fixture
def phones(site, browser):
    shutil.copytree(ROOT / "games" / "pingis", site.games / "pingis")
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
        p.wait_for_function("typeof mode !== 'undefined' && (V3 || no3d)", timeout=20000)
        return p

    phone.relay = relay
    yield phone
    for c in contexts:
        c.close()


def room(phone):
    host = phone("Testi1")
    host.click("#friends")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest = phone("Testi2")
    guest.click("#friends")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("AiPelitRooms.inRoom")
    host.wait_for_function("AiPelitRooms.members.filter(p => p.on).length === 2")
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("mode === 'netplay' && game && net.r === 0", timeout=12000)
    return host, guest


def serve(page):
    """The phone serves as soon as it may (the test's flick)."""
    page.wait_for_function("game.ph === 'serve' && game.wait <= 0 && netCanPlay()", timeout=8000)
    assert page.evaluate("tryServe(view, 0)")


def test_two_phones_play_one_rally_from_both_ends(phones):
    host, guest = room(phones)
    assert host.evaluate("[view, names]") == [0, ["Sinä", "Testi2"]]
    assert guest.evaluate("[view, names]") == [1, ["Testi1", "Sinä"]]
    # The guest's camera is behind its own end, the other way round. V3.view is set by the next
    # 3D frame (render3d), which on a busy run comes a moment after the game state, so wait for it.
    guest.wait_for_function("no3d || V3.view === 1 || V3.view === -1", timeout=5000)
    # v2 (#531): the pause button is for a game alone; a room game has the "‹ Pelit" chip.
    for p in (host, guest):
        assert p.locator("#pause").is_hidden()
    for p in (host, guest):
        p.evaluate(AUTO)
    server = host if host.evaluate("game.sv") == 0 else guest
    serve(server)
    # Both phones play the same flights: the same launch for each number.
    for p in (host, guest):
        p.wait_for_function("game.flight && game.flight.n >= 4", timeout=20000)
    h = host.evaluate("[game.flight.n, game.flight.by, game.flight.launch]")
    guest.wait_for_function(f"game.flight.n >= {h[0]}", timeout=5000)
    if guest.evaluate("game.flight.n") == h[0]:
        assert guest.evaluate("[game.flight.n, game.flight.by, game.flight.launch]") == h
    assert host.evaluate("game.sc") == [0, 0]
    # The guest stops following: the host's next shot passes it, the guest calls the point,
    # and the host's new rally brings the score to both.
    guest.evaluate(STOP)
    host.wait_for_function("game.sc[0] + game.sc[1] === 1", timeout=20000)
    guest.wait_for_function("game.sc[0] + game.sc[1] === 1 && net.r === 1", timeout=5000)
    assert host.evaluate("[game.sc, net.r]") == guest.evaluate("[game.sc, net.r]")
    assert host.errors == guest.errors == []


def test_a_rally_heard_twice_and_a_second_serve_change_nothing(phones):
    host, guest = room(phones)
    host.evaluate("() => { game.first = 0; game.sv = 0; }")
    serve(host)
    guest.wait_for_function("game.flight && game.flight.n === 0", timeout=5000)
    # The same rally again (a drop and a hello): the guest keeps its flight.
    host.evaluate("RM.send(net.lastRally)")
    guest.wait_for_timeout(200)
    assert guest.evaluate("game.flight && game.flight.n === 0 && game.ph === 'play'")
    # A second serve for a rally that has its flight is dropped by the host.
    a = host.evaluate("game.flight.launch")
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.evaluate(f"hostHeard({{ t: 'l', round: net.round, r: net.r, n: 0, by: 1, s: 1, a: [0,0.3,-1.5,0,0,3,0] }}, {gid})")
    assert host.evaluate("game.flight.launch") == a and host.evaluate("game.flight.by") == 0
    # A point from an older rally, or for another flight, is dropped too.
    host.evaluate(f"hostHeard({{ t: 'pt', round: net.round, r: net.r - 1, n: 0, w: 1 }}, {gid})")
    host.evaluate(f"hostHeard({{ t: 'pt', round: net.round, r: net.r, n: 5, w: 1 }}, {gid})")
    assert host.evaluate("game.sc") == [0, 0]
    assert host.errors == guest.errors == []


def test_a_serve_reaches_a_phone_still_in_its_pause_after_the_point(phones):
    """Each phone counts its own pause after a point; a slow one may still be in it when the
    other serves. The serve is taken for the new rally all the same, both ways (#509 review)."""
    host, guest = room(phones)
    # The guest serves next (first = 1, one point played) while the host's pause runs on.
    host.evaluate("() => { game.first = 1; game.ph = 'play'; hostPoint(0); game.wait = 99; }")
    guest.wait_for_function("net.r === 1 && game.sv === 1 && game.ph === 'point'", timeout=5000)
    guest.evaluate("() => { game.wait = 0; }")
    serve(guest)
    host.wait_for_function("game.flight && game.flight.by === 1 && game.flight.n === 0 && game.ph === 'play'", timeout=5000)
    # The host serves next (two points played) while the guest still holds the last rally's
    # flight in its pause.
    r = host.evaluate("() => { game.flight = null; game.sc = [1, 0]; game.first = 1; game.ph = 'play'; hostPoint(0); return net.r; }")
    guest.wait_for_function(f"net.r === {r} && game.sv === 0 && game.ph === 'point'", timeout=5000)
    guest.evaluate("() => { game.wait = 99; game.flight = newFlight(5, 0, false, [0,0.3,-1,0,0,3,0]); game.flight.over = { w: 0 }; }")
    host.evaluate("() => { game.wait = 0; }")
    serve(host)
    guest.wait_for_function("game.flight && game.flight.by === 0 && game.flight.n === 0 && game.ph === 'play'", timeout=5000)
    # A second serve for the same rally is still dropped.
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    a = host.evaluate("game.flight.launch")
    host.evaluate(f"hostHeard({{ t: 'l', round: net.round, r: net.r, n: 0, by: 1, s: 1, a: [0,0.3,-1.5,0,0,3,0] }}, {gid})")
    assert host.evaluate("game.flight.launch") == a
    assert host.errors == guest.errors == []


def test_away_and_back_replays_the_rally_with_no_point(phones):
    host, guest = room(phones)
    host.evaluate("() => { game.first = 1; game.sv = 1; }")
    host.evaluate("() => { net.r++; game.r = net.r; sendRally(-1); }")
    guest.wait_for_function("net.r === 1 && game.sv === 1")
    serve(guest)
    host.wait_for_function("game.flight && game.flight.by === 1", timeout=5000)
    r = host.evaluate("net.r")
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=10000)
    guest.wait_for_function("net.stale", timeout=10000)
    # Stale: the guest neither serves nor judges.
    assert guest.evaluate("[netCanPlay(), judgeHere(1)]") == [False, False]
    phones.relay.back(guest)
    host.wait_for_function(f"net.r > {r} && !AiPelitRooms.paused", timeout=15000)
    guest.wait_for_function(f"net.r > {r} && !net.stale", timeout=10000)
    # A replay: the same server, no point, no flight.
    assert host.evaluate("[game.sc, game.sv]") == [[0, 0], 1]
    assert guest.evaluate("[game.sc, game.sv, !!game.flight]") == [[0, 0], 1, False]
    # A point the guest sent for the old rally lands nowhere.
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    host.evaluate(f"hostHeard({{ t: 'pt', round: net.round, r: {r}, n: 0, w: 1 }}, {gid})")
    assert host.evaluate("game.sc") == [0, 0]
    serve(guest)
    host.wait_for_function("game.flight && game.flight.by === 1 && game.flight.n === 0", timeout=5000)
    assert host.errors == guest.errors == []


def test_the_computer_takes_an_away_guest_and_gives_the_bat_back_at_the_next_rally(phones):
    host, guest = room(phones)
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=10000)
    host.click("#aipr-goOn")
    host.wait_for_function("net.g === 'c' && !AiPelitRooms.paused", timeout=5000)
    # The computer plays the guest's end on the host: it serves and judges there, and a point
    # the guest phone sends meanwhile is dropped.
    assert host.evaluate("[cpuAt(1), judgeHere(1)]") == [True, True]
    gid = json.dumps(guest.evaluate("AiPelitRooms.me"))
    sc = host.evaluate("game.sc")
    host.evaluate(f"hostHeard({{ t: 'pt', round: net.round, r: net.r, n: game.flight ? game.flight.n : 0, w: 1 }}, {gid})")
    assert host.evaluate("game.sc") == sc
    phones.relay.back(guest)
    host.wait_for_function("net.gNext === 'p'", timeout=15000)
    # The bat comes back with a new rally, never in the middle of one.
    # The bat stays the computer's until this rally ends; then the next one is the guest's.
    assert host.evaluate("[net.g, cpuAt(1)]") == ["c", True]
    host.evaluate("() => { game.ph = 'play'; hostPoint(0); }")
    guest.wait_for_function("net.g === 'p' && netCanPlay()", timeout=10000)
    host.wait_for_function("net.g === 'p'", timeout=5000)
    assert host.evaluate("[cpuAt(1), judgeHere(1)]") == [False, False]
    # While a rally names the computer, the guest phone neither serves nor judges.
    guest.evaluate("() => guestRally(Object.assign({}, { t: 'rally', round: net.round, r: net.r + 1, p: 0, sc: game.sc, sv: 1, g: 'c', ph: 'serve', wait: 0, lw: -1, nm: net.names, first: 0 }))")
    assert guest.evaluate("[netCanPlay(), judgeHere(1)]") == [False, False]
    guest.wait_for_function("net.note === 'Kone pelaa puolestasi'", timeout=3000)
    assert host.errors == guest.errors == []


def test_the_end_reaches_both_phones_once(phones):
    host, guest = room(phones)
    host.evaluate("() => { game.sc = [10, 4]; game.ph = 'play'; hostPoint(0); game.wait = 0; }")
    for p in (host, guest):
        p.wait_for_function("mode === 'end'", timeout=10000)
        assert p.locator("#again").inner_text() == "Takaisin huoneeseen"
        assert p.locator("#toMenu").is_hidden()
    assert host.locator("#endTitle").inner_text() == "Voitit!"
    assert host.locator("#endScore").inner_text() == "11–4"
    assert guest.locator("#endTitle").inner_text() == "Hävisit"
    assert guest.locator("#endScore").inner_text() == "4–11"
    assert host.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pingis:kaverit'))") == {"voitot": 1}
    assert guest.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pingis:kaverit'))") == {"haviot": 1}
    # Heard again (a phone back after the end): counted once.
    guest.evaluate("() => { const m = net.res; net.res = null; netEnd(m); }")
    assert guest.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pingis:kaverit'))") == {"haviot": 1}
    # Nothing of a room game is saved as a game alone.
    assert host.evaluate("localStorage.getItem('ai-pelit:pingis:kesken')") is None
    host.click("#again")
    host.wait_for_function("!net && document.getElementById('aipr-start')", timeout=5000)
    assert host.errors == guest.errors == []
