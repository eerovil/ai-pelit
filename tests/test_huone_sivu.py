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
    # Sound still goes through: the guest holds the 🎤 chip, where it sits in the game alone (on the
    # right edge above the middle), and the host hears it. It is the page's, not the game's (#394).
    assert game(guest).locator("#aipr-mic").count() == 0
    chip = guest.locator("#aipr-mic")
    chip.wait_for(state="visible")
    assert guest.locator("#bar #mic").count() == 0
    box, stage = chip.bounding_box(), guest.locator("#stage").bounding_box()
    assert box["x"] + box["width"] > stage["width"] - 70 and box["y"] < stage["y"] + stage["height"] / 2
    before = host.evaluate("window.__bytes")
    chip.dispatch_event("pointerdown", {"pointerId": 1})
    guest.wait_for_function(f"{ROOMS}.voice.talking")
    guest.locator("#aipr-mic.live").wait_for()
    host.wait_for_function(f"window.__bytes > {before} + 2000", timeout=10_000)
    # The host's page says who talks, and its bar lights the name.
    host.locator("#aipr-talk", has_text="🔊 Aino").wait_for()
    host.locator("#who span.talk", has_text="Aino").wait_for()
    chip.dispatch_event("pointerup", {"pointerId": 1})
    guest.wait_for_function(f"!{ROOMS}.voice.talking")
    assert host.errors == guest.errors == []


def hold_chip(page):
    chip = page.locator("#aipr-mic")
    chip.wait_for(state="visible")
    box = chip.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.wait_for_function(f"{ROOMS}.voice.talking")


def switch_to_iso(host, code, *others):
    game(host).locator("#aipr-switchGame").click()
    game(host).locator("#aipr-gameList button[data-game='iso']").click()
    for page in (host, *others):
        page.wait_for_url(re.compile(rf"/huone/\?koodi={code}&peli=iso&v=1$"))
        page.wait_for_function(f"{ROOMS}?.game === 'iso' && {ROOMS}.inRoom && {ROOMS}.members.length === 2")


def test_a_sentence_goes_on_through_a_game_switch(phones):
    # The host switches while the guest's finger is on the chip (#394): the old game's page going
    # away must not let go of the microphone, and the finger's lift still ends it.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
    hold_chip(guest)
    host.locator("#who span.talk", has_text="Aino").wait_for()
    switch_to_iso(host, code, guest)
    assert guest.evaluate(f"{ROOMS}.voice.talking")
    assert guest.locator("#aipr-mic.live").is_visible()
    # The sound still arrives after the switch, and the host still sees who talks.
    before = host.evaluate("window.__bytes")
    host.wait_for_function(f"window.__bytes > {before} + 2000", timeout=10_000)
    host.locator("#aipr-talk", has_text="🔊 Aino").wait_for()
    host.locator("#who span.talk", has_text="Aino").wait_for()
    guest.mouse.up()
    guest.wait_for_function(f"!{ROOMS}.voice.talking")
    host.locator("#who span.talk").wait_for(state="detached")
    assert host.errors == guest.errors == []


def test_a_lift_during_the_hosts_reconnect_still_reaches_the_others(phones):
    # The host's connection is made anew at a switch: a `talk` sent in that gap is lost, and the
    # greeting after it says the phone no longer talks (#394).
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
    hold_chip(host)
    guest.locator("#who span.talk", has_text="Eero").wait_for()
    phones.relay.lose_rtc["talk"] = 1
    host.mouse.up()
    host.wait_for_function(f"!{ROOMS}.voice.talking")
    guest.wait_for_timeout(300)
    assert guest.locator("#who span.talk", has_text="Eero").count() == 1
    switch_to_iso(host, code, guest)
    guest.locator("#who span.talk").wait_for(state="detached", timeout=6_000)
    assert guest.evaluate(f"{ROOMS}.voice.heals") == 0
    assert host.errors == guest.errors == []


def test_the_page_going_hidden_still_lets_go_of_the_microphone(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
    hold_chip(guest)
    guest.evaluate("""() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    guest.wait_for_function(f"!{ROOMS}.voice.talking")
    guest.mouse.up()
    assert host.errors == guest.errors == []


def test_the_chip_moves_to_the_next_games_place_only_after_the_lift(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
    chip = guest.locator("#aipr-mic")
    chip.wait_for(state="visible")
    at = chip.bounding_box()
    hold_chip(guest)
    held = chip.bounding_box()  # a live chip is a little bigger
    guest.evaluate("AiPelitRoomShell.chip('bottom-left', true)")
    guest.wait_for_timeout(400)
    assert chip.bounding_box()["x"] == held["x"]
    guest.mouse.up()
    guest.wait_for_function("document.getElementById('aipr-mic').getBoundingClientRect().left < 60")
    # A game with no voice has no chip; the next one brings it back.
    guest.evaluate("AiPelitRoomShell.chip('right', false)")
    chip.wait_for(state="hidden")
    guest.evaluate("AiPelitRoomShell.chip('right', true)")
    chip.wait_for(state="visible")
    assert chip.bounding_box()["x"] == at["x"]
    assert host.errors == guest.errors == []


LOG_TOUCHES = """() => {
  const w = document.getElementById('game').contentWindow;
  w.__seen = [];
  for (const t of ['pointerdown', 'pointerup']) w.addEventListener(t, () => w.__seen.push(t), true);
}"""
SEEN = "document.getElementById('game').contentWindow.__seen"


def touch(cdp, kind, *points):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [
        {"x": x, "y": y, "id": i} for i, x, y in points]})


def test_the_game_hears_a_second_finger_while_the_chip_is_held(phones):
    # Talking while playing: one finger on the page's chip, the other in the game's frame. Pointer
    # events only: with the first finger in another document Chromium sends the frame no touch
    # events, and every room game reads pointers.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for page in (host, guest):
        page.wait_for_function(f"{ROOMS}.voice.calls === 1", timeout=15_000)
    guest.locator("#aipr-mic").wait_for(state="visible")
    box = guest.locator("#aipr-mic").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    guest.evaluate(LOG_TOUCHES)
    cdp = guest.context.new_cdp_session(guest)
    # The chip first, then the game.
    touch(cdp, "touchStart", (1, cx, cy))
    guest.wait_for_function(f"{ROOMS}.voice.talking")
    touch(cdp, "touchStart", (1, cx, cy), (2, 100, 500))
    guest.wait_for_function(f"{SEEN}.includes('pointerdown')")
    touch(cdp, "touchEnd")
    guest.wait_for_function(f"{SEEN}.includes('pointerup') && !{ROOMS}.voice.talking")
    # The game first, then the chip.
    guest.evaluate(f"{SEEN}.length = 0")
    touch(cdp, "touchStart", (2, 100, 500))
    guest.wait_for_function(f"{SEEN}.includes('pointerdown')")
    touch(cdp, "touchStart", (2, 100, 500), (1, cx, cy))
    guest.wait_for_function(f"{ROOMS}.voice.talking")
    touch(cdp, "touchEnd")
    guest.wait_for_function(f"{SEEN}.includes('pointerup') && !{ROOMS}.voice.talking")
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


def test_a_held_press_on_the_room_screen_survives_the_pages_ticks(phones):
    # The room page tells its frame four times a second; the room screen's buttons must stay the
    # same nodes, or a slow finger's tap gets no click.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    mute = game(host).locator("#aipr .mute")
    mute.wait_for(timeout=15_000)
    mute.evaluate("b => { b.__kept = 1 }")
    box = mute.bounding_box()
    stage = host.locator("#stage").bounding_box()
    host.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    host.mouse.down()
    host.wait_for_timeout(900)
    assert mute.evaluate("b => b.__kept") == 1
    host.mouse.up()
    host.wait_for_function(f"{ROOMS}?.inRoom && document.getElementById('game').contentWindow.document.querySelector('#aipr .mute').textContent === '🔇'")
    assert stage["y"] < box["y"]
    assert host.errors == guest.errors == []


def test_the_host_stops_a_round_from_the_chip_on_the_room_page(phones):
    # #392 in the room page's frame: the host's "‹ Pelit" menu ends the round on every phone, and
    # everyone stays on the room page.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    host.wait_for_function(f"{ROOMS}.members.filter(m => m.on).length === 2")
    game(host).locator("#aipr-start").click()
    for page in (host, guest):
        page.wait_for_function(f"{DEMO}.phase === 'play'")
        page.evaluate("window.__mark = 1")
    game(host).locator("#ai-pelit-back").click()
    stop = game(host).locator("#ai-pelit-lopeta")
    stop.click()
    stop.click()
    for page in (host, guest):
        page.wait_for_function(f"{DEMO}.phase === 'room'")
        assert page.evaluate("window.__mark") == 1
        assert "/huone/" in page.url
    assert host.errors == guest.errors == []


def test_switching_games_twice_leaves_one_frame_watcher(phones):
    # The frame keeps its window when it loads the next game: the page must let go of the old
    # game's watcher, or every game the room has played would be called and kept.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    for slug in ("iso", "huonetesti"):
        game(host).locator("#aipr-switchGame").click()
        game(host).locator(f"#aipr-gameList button[data-game='{slug}']").click()
        for page in (host, guest):
            page.wait_for_function(f"{ROOMS}?.game === '{slug}' && {ROOMS}.inRoom && {ROOMS}.members.length === 2")
    for page in (host, guest):
        # The room page's own bar, and the game in the frame now.
        page.wait_for_function("AiPelitRoomShell.watching === 2")
        page.wait_for_timeout(600)
        assert page.evaluate("AiPelitRoomShell.watching") == 2
    assert host.errors == guest.errors == []
