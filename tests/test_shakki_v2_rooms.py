"""Shakki v2 (#465) with a friend: the host's phone keeps the game, both play by taps."""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay
from test_shakki_v2 import tap


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / "games")
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
        p.goto(site.url + "games/shakki/v2/")
        p.wait_for_function("view.s > 0")
        return p

    yield phone
    for c in contexts:
        for p in c.pages:
            if not p.is_closed():
                p.evaluate("R.leave()")
    for c in contexts:
        c.close()


def room(phone):
    host = phone("Testi1")
    host.click("#friends")
    host.click("#aipr-create")
    host.wait_for_function("R.isHost && R.members.length === 1")
    code = host.evaluate("R.code")
    guest = phone("Testi2")
    guest.click("#friends")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("R.inRoom")
    host.wait_for_function("R.members.filter(p => p.on).length === 2")
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("game && derived && derived.uci.length === 0")
    return host, guest


def test_two_phones_play_by_taps_reload_and_resign(phones):
    host, guest = room(phones)
    # Round 1: the host is white at the bottom, the guest black with the board turned.
    assert host.evaluate("[game.mine, flipped()]") == ["w", False]
    assert guest.evaluate("[game.mine, flipped()]") == ["b", True]
    assert guest.locator("#oppoName").inner_text().endswith("Testi1")
    # Not the guest's turn: its taps select nothing, and a move it sends anyway is refused.
    tap(guest, "e7")
    assert guest.evaluate("selected") == -1
    guest.evaluate("R.send({t: 'move', round: roomRound, ply: 0, m: 'e7e5'})")
    tap(host, "e2")
    tap(host, "e4")
    for p in (host, guest):
        p.wait_for_function("derived.uci.join() === 'e2e4'")
    assert guest.locator("#status").inner_text() == "Sinun vuorosi"
    tap(guest, "e7")
    tap(guest, "e5")
    host.wait_for_function("derived.uci.join() === 'e2e4,e7e5'")
    # The same move arriving twice is one move.
    guest.evaluate("R.send({t: 'move', round: roomRound, ply: 1, m: 'e7e5'})")
    tap(host, "g1")
    tap(host, "f3")
    guest.wait_for_function("derived.uci.length === 3")
    assert host.evaluate("derived.uci") == ["e2e4", "e7e5", "g1f3"]
    # A guest reloading gets the game back as it is.
    guest.reload()
    guest.wait_for_function("game && derived && derived.uci.length === 3 && game.mine === 'b'")
    tap(guest, "b8")
    tap(guest, "c6")
    host.wait_for_function("derived.uci.length === 4")
    # The guest resigns (two taps); both phones see it and count it once.
    guest.click("#resign")
    guest.click("#resign")
    for p in (host, guest):
        p.wait_for_selector("#end:not(.hidden)")
    assert host.locator("#endTitle").inner_text() == "Voitit!"
    assert host.locator("#endSub").inner_text() == "Vastustaja luovutti."
    assert guest.locator("#endSub").inner_text() == "Luovutit."
    assert host.evaluate("load('kaverit', null)") == {"v": 1, "h": 0, "t": 0}
    assert guest.evaluate("load('kaverit', null)") == {"v": 0, "h": 1, "t": 0}
    # Room games are not solo stats, and leave no solo save.
    for p in (host, guest):
        assert p.evaluate("load('tilasto:2', null)") is None
        assert p.evaluate("localStorage.getItem('ai-pelit:shakki:peli')") is None
    guest.reload()
    guest.wait_for_function("game && result")
    assert guest.evaluate("load('kaverit', null)") == {"v": 0, "h": 1, "t": 0}
    # Next round: colours swap.
    for p in (host, guest):
        if not p.locator("#aipr").is_visible():
            p.click("#again")
    host.wait_for_function("R.isHost && !R.canStop")
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("game && derived.uci.length === 0 && !result")
    assert host.evaluate("game.mine") == "b"
    assert guest.evaluate("game.mine") == "w"
    tap(guest, "d2")
    tap(guest, "d4")
    host.wait_for_function("derived.uci.join() === 'd2d4'")
    for p in (host, guest):
        assert p.errors == []


def test_mate_ends_the_round(phones):
    host, guest = room(phones)
    host.evaluate("game.moves = ['f2f3', 'e7e5']; derived = playGame(game.moves); sendState(); updateHUD(); askDraw();")
    guest.wait_for_function("derived.uci.length === 2")
    tap(host, "g2")
    tap(host, "g4")
    guest.wait_for_function("derived.uci.length === 3")
    tap(guest, "d8")
    tap(guest, "h4")
    for p in (host, guest):
        p.wait_for_selector("#end:not(.hidden)")
    assert guest.locator("#endTitle").inner_text() == "Voitit!"
    assert host.locator("#endTitle").inner_text() == "Hävisit"
    assert host.locator("#endSub").inner_text() == "Shakkimatti."
    # Back in the room the result line takes the win or loss colour.
    guest.click("#again")
    guest.wait_for_selector("#aipr-result.win")
    assert guest.locator("#aipr-result").inner_text() == "Voitit! Shakkimatti."
    for p in (host, guest):
        assert p.errors == []


def test_an_away_friends_turn_is_played_by_the_computer_and_they_come_back(phones):
    host, guest = room(phones)
    tap(host, "e2")
    tap(host, "e4")
    guest.wait_for_function("derived.uci.length === 1")
    guest.evaluate("R.leave()")
    host.wait_for_function("R.paused")
    assert host.locator("#status").inner_text() == "Peli odottaa…"
    # A move that reaches the host while the round waits is sent back, not kept.
    host.evaluate("receive({t: 'move', round: roomRound, ply: 1, m: 'e7e5'}, game.black.id)")
    assert host.evaluate("derived.uci.length") == 1
    host.click("#aipr-goOn")
    host.wait_for_function("derived.uci.length === 2")
    assert host.locator("#lastMove").inner_text() == "Kone siirsi pelaajan Testi2 puolesta."
    assert host.evaluate("derived.pos.turn") == "w"
    tap(host, "d2")
    tap(host, "d4")
    guest.click("#friends")
    guest.click("#aipr-again")
    guest.wait_for_function("game && derived && derived.uci.length === 3 && game.mine === 'b'")
    # The computer's move for black is random (g8f6 itself, or f7f6 blocking it): play g8f6 when legal.
    frm, to = ("g8", "f6") if guest.evaluate("!!findMove(derived.pos, 'g8f6')") else ("b8", "c6")
    tap(guest, frm)
    tap(guest, to)
    host.wait_for_function("derived.uci.length === 4")
    for p in (host, guest):
        assert p.errors == []


def test_a_draw_and_a_move_after_the_end(phones):
    host, guest = room(phones)
    # Stalemate after black's move: f7... the fastest known stalemate, played to its last move by taps.
    moves = ["e2e3", "a7a5", "d1h5", "a8a6", "h5a5", "h7h5", "h2h4", "a6h6", "a5c7", "f7f6", "c7d7", "e8f7",
             "d7b7", "d8d3", "b7b8", "d3h7", "b8c8", "f7g6"]
    host.evaluate("ms => { game.moves = ms; derived = playGame(ms); sendState(); updateHUD(); askDraw(); }", moves)
    guest.wait_for_function("derived.uci.length === 18")
    tap(host, "c8")
    tap(host, "e6")
    for p in (host, guest):
        p.wait_for_selector("#end:not(.hidden)")
        assert p.locator("#endTitle").inner_text() == "Tasapeli"
    assert guest.evaluate("load('kaverit', null)") == {"v": 0, "h": 0, "t": 1}
    # A move that arrives after the end is answered with the ended game.
    guest.evaluate("R.send({t: 'move', round: roomRound, ply: 19, m: 'h7h8'})")
    guest.wait_for_timeout(300)
    assert host.evaluate("derived.uci.length") == 19 and guest.evaluate("derived.uci.length") == 19
    # A draw's line in the room is neither the win nor the loss colour.
    guest.click("#again")
    guest.wait_for_selector("#aipr-result:not(:empty)")
    assert guest.evaluate("document.getElementById('aipr-result').className") == ""
    for p in (host, guest):
        assert p.errors == []
