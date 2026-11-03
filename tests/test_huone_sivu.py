"""The room page (#388): a phone that makes or joins a room moves onto /huone/, which keeps the
room's connection and the voice calls, and plays the game in its frame. When the host switches
games, only the frame changes.

On the test-only game of test_rooms_lib.py and its `Relay`, with Chromium's fake microphone as in
test_rooms_voice.py. Each phone opts into the room page (the other room tests keep the room in the
game's own page, see ROOMS_IN_GAME in conftest.py).
"""

import json
import re
import shutil

import pytest

from conftest import keep_rooms_in_game, make_game
from test_rooms_lib import Relay, demo_page
from test_rooms_voice import COUNT_CALLS, FAKE_MIC

# The game in the room page's frame, from the room page.
ROOMS = "document.getElementById('game')?.contentWindow?.AiPelitRooms"
DEMO = "document.getElementById('game')?.contentWindow?.demo"
# Counts the WebSockets the room page itself makes, and marks the page, so a test sees it was not
# loaded again.
COUNT_SOCKETS = """
if (window.top === window) {
  const Real = window.WebSocket;
  window.__sockets = 0;
  window.WebSocket = function (url, p) { window.__sockets++; return new Real(url, p); };
  window.WebSocket.prototype = Real.prototype;
  Object.assign(window.WebSocket, { CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3 });
}
"""


@pytest.fixture(scope="module")
def browser(_playwright):
    b = keep_rooms_in_game(_playwright.chromium.launch(args=FAKE_MIC))
    yield b
    b.close()


@pytest.fixture
def phones(site, browser):
    make_game(site.games, "huonetesti", [demo_page(), demo_page()])
    make_game(site.games, "iso", [demo_page("iso", 8)])
    site.build()
    shutil.copytree(site.out / "games" / "huonetesti" / "v2", site.out / "games" / "huonetesti" / "v1")
    relay = Relay()
    contexts = []

    def phone(name, path="huonetesti/v2/"):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.grant_permissions(["microphone"])
        ctx.add_init_script("window.__aiPelitHuoneSivu = true;")
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        ctx.add_init_script(COUNT_CALLS)
        ctx.add_init_script(COUNT_SOCKETS)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}games/{path}")
        return page

    phone.relay = relay
    phone.site = site
    yield phone
    for ctx in contexts:
        ctx.close()


def game(page):
    return page.frame_locator("#game")


def make_room(phones):
    host = phones("Eero")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_url(re.compile(r"/huone/\?koodi=[A-Z]{4}&peli=huonetesti&v=2$"))
    host.wait_for_function(f"{ROOMS}?.isHost && {ROOMS}.members.length === 1 && {ROOMS}.connected")
    return host, host.evaluate(f"{ROOMS}.code")


def join(phones, name, code):
    page = phones(name, f"huonetesti/v2/?huone={code}")
    page.wait_for_url(re.compile(rf"/huone/\?koodi={code}&peli=huonetesti&v=2$"))
    page.wait_for_function(f"{ROOMS}?.inRoom && {ROOMS}.members.length > 1")
    return page


def test_making_and_joining_a_room_moves_onto_the_room_page(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    # The bar names the room and everyone in it.
    for page in (host, guest):
        page.wait_for_function("document.querySelectorAll('#who span').length === 2")
        assert page.locator("#code b").inner_text() == code
        assert page.locator("#state").is_hidden()
    assert "Eero (sinä)" in host.locator("#who").inner_text()
    assert "Aino" in host.locator("#who").inner_text()
    # A round plays in the frames as in a game's own page.
    host.wait_for_function(f"{ROOMS}.members.filter(m => m.on).length === 2")
    game(host).locator("#aipr-start").click()
    for page in (host, guest):
        page.wait_for_function(f"{DEMO}.phase === 'play'")
    host.evaluate(f"document.getElementById('game').contentWindow.end()")
    guest.wait_for_function(f"{DEMO}.results.length === 1")
    assert host.errors == guest.errors == []


def test_a_switch_changes_only_the_frame_and_keeps_the_call(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
        page.evaluate("window.__mark = 1")
    calls = [p.evaluate("window.__pcs.length") for p in (host, guest)]
    guest_sockets = guest.evaluate("window.__sockets")
    game(host).locator("#aipr-switchGame").click()
    game(host).locator("#aipr-gameList button[data-game='iso']").click()
    for page in (host, guest):
        page.wait_for_url(re.compile(rf"/huone/\?koodi={code}&peli=iso&v=1$"))
        page.wait_for_function(f"{ROOMS}?.game === 'iso' && {ROOMS}.inRoom && {ROOMS}.members.length === 2")
        # The room page itself stayed: same page, same call.
        assert page.evaluate("window.__mark") == 1
    assert host.evaluate(f"{ROOMS}.isHost") and not guest.evaluate(f"{ROOMS}.isHost")
    # The guest's page kept its one connection; the host's told the room its new game.
    assert guest.evaluate("window.__sockets") == guest_sockets
    for page, n in zip((host, guest), calls):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1")
        assert page.evaluate("window.__pcs.length") == n
    # Sound still goes through: the guest holds the game's own 🎤 chip, where it sits in the game
    # alone (on the right edge above the middle), and the host hears it.
    chip = game(guest).locator("#aipr-mic")
    chip.wait_for(state="visible")
    assert guest.locator("#bar #mic").count() == 0
    box, stage = chip.bounding_box(), guest.locator("#stage").bounding_box()
    assert box["x"] + box["width"] > stage["width"] - 70 and box["y"] < stage["y"] + stage["height"] / 2
    before = host.evaluate("window.__bytes")
    chip.dispatch_event("pointerdown", {"pointerId": 1})
    guest.wait_for_function(f"{ROOMS}.voice.talking")
    game(guest).locator("#aipr-mic.live").wait_for()
    host.wait_for_function(f"window.__bytes > {before} + 2000", timeout=10_000)
    # The host's game says who talks, and its bar lights the name.
    game(host).locator("#aipr-talk", has_text="🔊 Aino").wait_for()
    host.locator("#who span.talk", has_text="Aino").wait_for()
    chip.dispatch_event("pointerup", {"pointerId": 1})
    guest.wait_for_function(f"!{ROOMS}.voice.talking")
    assert host.errors == guest.errors == []


def test_leaving_goes_back_to_the_game_alone(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    game(guest).locator("#aipr-back").click()
    guest.wait_for_url(re.compile(r"/games/huonetesti/v2/$"))
    guest.wait_for_function("window.AiPelitRooms && !AiPelitRooms.inRoom")
    host.wait_for_function(f"{ROOMS}.members.length === 1")
    # The host leaving closes the room: the guest who is back in it lands in the game alone,
    # where the room screen says why.
    guest.goto(f"{phones.site.url}games/huonetesti/v2/?huone={code}")
    guest.wait_for_function(f"{ROOMS}?.inRoom && {ROOMS}.members.length === 2")
    game(host).locator("#aipr-back").click()
    host.wait_for_url(re.compile(r"/games/huonetesti/v2/$"))
    guest.wait_for_url(re.compile(r"/games/huonetesti/v2/$"))
    guest.wait_for_function("document.getElementById('aipr-err')?.textContent === 'Huone suljettiin.'")
    assert host.errors == guest.errors == []


def test_a_reloaded_room_page_rejoins(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    guest.reload()
    guest.wait_for_function(f"{ROOMS}?.inRoom && {ROOMS}.members.length === 2 && {ROOMS}.connected")
    host.reload()
    host.wait_for_function(f"{ROOMS}?.isHost && {ROOMS}.members.filter(m => m.on).length === 2")
    assert host.evaluate(f"{ROOMS}.code") == code
    assert host.errors == guest.errors == []


def test_the_back_chip_goes_up_past_the_room_page(phones):
    host, code = make_room(phones)
    game(host).locator("#ai-pelit-back").click()
    game(host).locator("#ai-pelit-takaisin").click()
    host.wait_for_url(re.compile(r"/#/?$|/#/huonetesti$"))
    host.wait_for_timeout(300)
    # Alone in it, the host's room went with it.
    assert code not in phones.relay.rooms
    assert host.errors == []


def test_a_room_page_with_no_room_goes_to_the_shelf(phones):
    page = phones("Eero")
    page.goto(f"{phones.site.url}huone/?koodi=xx")
    page.wait_for_url(re.compile(r"/$|/#/?$"))
