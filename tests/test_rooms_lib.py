"""public/rooms.js, the shared room client (#34), on a test-only game (tests/fixtures/rooms-demo.html).

Each phone is its own Chromium context. The room (rooms/worker.js on Cloudflare) is played by
`Relay`, which answers the pages' WebSockets the same way: the host's messages to everyone (or to
`to`), the others' to the host with `from`, and `peers` (with the host's game and version) whenever
someone comes or goes. It keeps the list of public rooms (#50) too, read with GET /api/rooms?game=.
"""

import asyncio
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from conftest import make_game

DEMO = (Path(__file__).parent / "fixtures" / "rooms-demo.html").read_text()


def demo_page(game="huonetesti", most=5):
    return DEMO.replace("__GAME__", game).replace("__MAX__", str(most))


def close(ws, code, reason=""):
    # Inside a route handler the sync API's close() waits on the loop that runs the handler.
    try:
        asyncio.get_running_loop().create_task(ws._impl_obj.close(code=code, reason=reason))
    except RuntimeError:
        ws.close(code=code, reason=reason)


class Relay:
    def __init__(self):
        self.rooms = {}
        self.blocked = set()  # ids whose phone has no connection
        self.slow = {}  # id -> its held hellos, for a phone whose hello is late

    def attach(self, page):
        page.route_web_socket(re.compile(r".*/api/rooms/.*"), self.connect)
        page.route(re.compile(r".*/api/rooms\?.*"), self.listing)

    def listing(self, route):
        game = parse_qs(urlparse(route.request.url).query).get("game", [""])[0]
        rooms = [{"code": code, "v": r["v"], "n": len(r["members"]), "max": r["max"]}
                 for code, r in reversed(self.rooms.items())
                 if r.get("listed") and r["game"] == game and r["host"] in r["socks"] and len(r["members"]) < r["max"]]
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"rooms": rooms}))

    def connect(self, ws):
        url = urlparse(ws.url)
        code = url.path.rsplit("/", 1)[1].upper()
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        me, name, host = hashlib.sha256(q["key"].encode()).hexdigest()[:32], q["name"], q.get("host") == "1"
        if me in self.blocked:
            close(ws, 1001, "")
            return
        room = self.rooms.get(code)
        if host and (room is None or (room["host"] != me and not room["socks"])):
            room = self.rooms[code] = {"host": me, "members": {}, "socks": {}, "game": q.get("game"),
                                       "v": int(q.get("v", 0)) or None, "max": min(8, int(q.get("max", 5)))}
        elif host and room["host"] != me:
            close(ws, 4009, "Koodi on jo käytössä")
            return
        elif room is None:
            close(ws, 4004, "Huonetta ei löydy")
            return
        if me not in room["members"] and len(room["members"]) >= room["max"]:
            close(ws, 4001, "Huone on täynnä")
            return
        room["members"][me] = name
        old = room["socks"].get(me)
        room["socks"][me] = ws
        if old:
            close(old, 4000, "Avattu toisaalla")
        ws.on_message(lambda m: self.message(room, me, m))
        ws.on_close(lambda code, reason: self.closed(room, me, ws))
        ws.send(json.dumps({"t": "you", "id": me}))
        self.peers(room)

    def message(self, room, me, text):
        msg = json.loads(text)
        if msg.get("t") == "hello" and me in self.slow:
            self.slow[me].append((room, text))
            return
        if msg.get("t") == "_list":
            if me == room["host"]:
                room["listed"] = msg.get("on") is True
            return
        if msg.get("t") == "bye":
            room["members"].pop(me, None)
            room["socks"].pop(me, None)
            self.peers(room)
            return
        if me == room["host"]:
            for other, ws in list(room["socks"].items()):
                if other != me and (not msg.get("to") or msg["to"] == other):
                    ws.send(text)
        else:
            msg["from"] = me
            host = room["socks"].get(room["host"])
            if host:
                host.send(json.dumps(msg))

    def closed(self, room, me, ws):
        if room["socks"].get(me) is ws:
            del room["socks"][me]
            self.peers(room)

    def peers(self, room):
        msg = {"t": "peers", "host": room["host"], "members": [
            {"id": i, "name": n, "on": i in room["socks"]} for i, n in room["members"].items()]}
        if room["game"]:
            msg.update(game=room["game"], v=room["v"])
        for ws in list(room["socks"].values()):
            ws.send(json.dumps(msg))

    def drop(self, page):
        """The phone loses its connection until `back()`."""
        me = page.evaluate("AiPelitRooms.me")
        self.blocked.add(me)
        for room in self.rooms.values():
            ws = room["socks"].get(me)
            if ws:
                close(ws, 1001, "")

    def hold_hello(self, page):
        """The phone's hellos wait until `let_hello()`: it is connected, but has not said hello."""
        self.slow[page.evaluate("AiPelitRooms.me")] = []

    def let_hello(self, page):
        for room, text in self.slow.pop(page.evaluate("AiPelitRooms.me"), []):
            self.message(room, page.evaluate("AiPelitRooms.me"), text)

    def back(self, page):
        self.blocked.discard(page.evaluate("AiPelitRooms.me"))


@pytest.fixture
def phones(site, browser):
    make_game(site.games, "huonetesti", [demo_page(), demo_page()])
    make_game(site.games, "pieni", [demo_page("pieni", 3)])
    site.build()
    relay = Relay()
    contexts = []

    def phone(name, path="huonetesti/v2/", height=740, nickname=None):
        ctx = browser.new_context(viewport={"width": 360, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        if name:
            ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}games/{path}")
        return page

    phone.relay = relay
    yield phone
    for ctx in contexts:
        ctx.close()


def text(page, id_):
    return page.locator(f"#aipr-{id_}").inner_text()


def make_room(phone, path="huonetesti/v2/"):
    host = phone("Eero", path)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    return host, host.evaluate("AiPelitRooms.code")


def join(phone, name, code, path="huonetesti/v2/"):
    page = phone(name, path)
    page.click("#multi")
    page.fill("#aipr-codeIn", code.lower())
    page.click("#aipr-joinBtn")
    page.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    return page


def start(host, guests):
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {1 + len(guests)}")
    host.click("#aipr-start")
    for p in [host, *guests]:
        p.wait_for_function("demo.phase === 'play'")
    host.wait_for_function("demo.clock > 1")


def test_phones_meet_by_code_and_by_link(phones):
    host, code = make_room(phones)
    assert re.fullmatch(r"[A-Z]{4}", code)
    assert text(host, "code") == code
    assert host.locator("#aipr-start").is_disabled()
    guest = join(phones, "Aino", code)
    host.wait_for_function("AiPelitRooms.members.length === 2")
    assert host.locator("#aipr-members li").all_inner_texts() == ["👑 Eero (sinä)", "Aino"]
    assert guest.locator("#aipr-members li").all_inner_texts() == ["👑 Eero", "Aino (sinä)"]
    assert text(guest, "info") == "Odotetaan, että Eero aloittaa kierroksen…"
    assert host.locator("#aipr-start").is_enabled()
    # A link joins at once, and a reload goes back to the same room.
    linked = phones("Onni", f"huonetesti/v2/?huone={code}")
    linked.wait_for_function("AiPelitRooms.members.length === 3")
    assert linked.evaluate("location.search") == ""
    linked.reload()
    linked.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 3")
    assert linked.evaluate("[AiPelitRooms.code, AiPelitRooms.isHost]") == [code, False]
    # A wrong code says so, on the first page of the room screen.
    lost = phones("Iida")
    lost.click("#multi")
    lost.fill("#aipr-codeIn", "ZZZZ" if code != "ZZZZ" else "YYYY")
    lost.click("#aipr-joinBtn")
    lost.wait_for_function("document.getElementById('aipr-err').textContent === 'Huonetta ei löydy'")
    assert not lost.evaluate("AiPelitRooms.inRoom")
    assert lost.evaluate("demo.log") == [["leave", "Huonetta ei löydy"]]
    assert host.errors == guest.errors == linked.errors == []


def test_the_qr_code_reads_back_as_the_join_link(phones):
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    host, code = make_room(phones)
    img = np.frombuffer(host.locator("#aipr-qr").screenshot(), dtype=np.uint8)
    got, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imdecode(img, cv2.IMREAD_GRAYSCALE))
    assert got.endswith(f"/games/huonetesti/v2/?huone={code}")


def test_a_round_goes_both_ways(phones):
    host, code = make_room(phones)
    a, b = join(phones, "Aino", code), join(phones, "Iida", code)
    start(host, [a, b])
    assert a.evaluate("demo.players.map(p => p.name)") == ["Eero", "Aino", "Iida"]
    assert a.locator("#aipr").is_hidden()
    a.evaluate("move(7, 8)")
    aino = a.evaluate("AiPelitRooms.me")
    host.wait_for_function(f"demo.dots[{json.dumps(aino)}][0] === 7")
    b.wait_for_function(f"demo.dots[{json.dumps(aino)}][0] === 7")
    host.evaluate("end()")
    for p in [host, a, b]:
        p.wait_for_function("demo.results.length === 1")
        assert p.locator("#aipr").is_visible()
        assert text(p, "result") == "Kierros 1 valmis"
    assert host.locator("#aipr-start").inner_text() == "Uusi kierros"
    # A second round.
    start(host, [a, b])
    host.evaluate("end()")
    a.wait_for_function("demo.results.length === 2")
    assert host.errors == a.errors == b.errors == []


def test_a_phone_reloaded_mid_round_gets_the_round_back(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    round_ = host.evaluate("demo.round")
    guest.reload()
    guest.wait_for_function(f"demo.phase === 'play' && demo.round === {json.dumps(round_)} && demo.clock > 0")
    assert guest.locator("#aipr").is_hidden()
    # A second tab of the same phone takes over; the old one is told so.
    tab = guest.context.new_page()
    tab.errors = []
    phones.relay.attach(tab)
    tab.goto(f"{guest.url}?huone={code}")
    guest.wait_for_function("!AiPelitRooms.inRoom && document.getElementById('aipr-err').textContent === 'Avattu toisaalla'")
    tab.wait_for_function(f"demo.phase === 'play' && demo.round === {json.dumps(round_)}")
    assert host.errors == guest.errors == tab.errors == []


def test_a_host_reload_sends_everyone_back_to_the_room(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    host.reload()
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 2")
    guest.wait_for_function("demo.log.some(l => l[0] === 'lobby') && demo.phase === 'room'")
    assert guest.locator("#aipr-room").is_visible()
    assert not guest.evaluate("AiPelitRooms.paused")
    start(host, [guest])
    assert host.errors == guest.errors == []


def test_a_phone_away_while_the_host_reloads_comes_back_to_the_room(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    phones.relay.drop(guest)
    host.reload()
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 2")
    phones.relay.back(guest)
    guest.wait_for_function("demo.log.some(l => l[0] === 'lobby') && AiPelitRooms.connected", timeout=8000)
    assert guest.locator("#aipr-room").is_visible()


def test_the_round_waits_for_a_phone_that_drops_off(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    other = join(phones, "Iida", code)
    start(host, [guest, other])
    phones.relay.drop(guest)
    host.wait_for_function("document.getElementById('aipr-pauseText').textContent === '⏸ Odotetaan: Aino'")
    other.wait_for_function("document.getElementById('aipr-pauseText').textContent === '⏸ Odotetaan: Aino'")
    guest.wait_for_function("document.getElementById('aipr-pauseText').textContent === 'Yhteys katkesi – yhdistetään…'")
    assert host.locator("#aipr-goOn").is_visible()
    assert other.locator("#aipr-goOn").is_hidden()
    held = host.evaluate("demo.clock")
    host.wait_for_timeout(500)
    assert host.evaluate("[demo.clock, AiPelitRooms.paused]") == [held, True]
    # Back again: the round goes on.
    phones.relay.back(guest)
    host.wait_for_function(f"!AiPelitRooms.paused && demo.clock > {held}", timeout=8000)
    other.wait_for_function("document.getElementById('aipr-pause').hidden")
    # Dropped again, and the host goes on without them; the game hears who the computer takes.
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    aino = guest.evaluate("AiPelitRooms.me")
    host.click("#aipr-goOn")
    host.wait_for_function(f"!AiPelitRooms.paused && demo.bots.includes({json.dumps(aino)})")
    other.wait_for_function("!AiPelitRooms.paused")
    # When the phone comes back, it takes its player back.
    phones.relay.back(guest)
    host.wait_for_function("demo.bots.length === 0", timeout=8000)
    guest.wait_for_function("demo.phase === 'play' && AiPelitRooms.connected && !AiPelitRooms.paused")
    assert host.errors == guest.errors == other.errors == []


def test_a_phone_away_when_the_round_ends_gets_its_result_once(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    third = join(phones, "Iida", code)
    start(host, [guest, third])
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.evaluate("end()")
    third.wait_for_function("demo.results.length === 1")
    first = host.evaluate("demo.round")
    # Another round without Aino, then she is back: she still gets the round she was in, once.
    start(host, [third])
    host.evaluate("end()")
    third.wait_for_function("demo.results.length === 2")
    phones.relay.back(guest)
    guest.wait_for_function("demo.results.length === 1 && demo.phase === 'room'", timeout=8000)
    assert guest.evaluate("demo.results") == [first]
    assert text(guest, "result") == "Kierros 1 valmis"
    assert guest.locator("#aipr-room").is_visible()
    assert host.errors == guest.errors == third.errors == []


def test_a_phone_reloaded_while_away_hears_the_round_before_its_end(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    third = join(phones, "Iida", code)
    start(host, [guest, third])
    first = host.evaluate("demo.round")
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.evaluate("end()")
    start(host, [third])
    # Aino's page reloads as her phone comes back: a fresh page, which knows no round yet.
    phones.relay.back(guest)
    guest.reload()
    guest.wait_for_function("demo.results.length === 1 && demo.phase === 'room'", timeout=8000)
    assert guest.evaluate("demo.results") == [first]
    starts = guest.evaluate("demo.log.filter(l => l[0] === 'start')")
    assert starts == [["start", first, True]]
    assert text(guest, "result") == "Kierros 1 valmis"
    # The round Iida is playing now is not Aino's: she waits for the next one.
    assert text(guest, "info") == "Kierros on käynnissä – pääset mukaan seuraavaan."
    assert host.errors == guest.errors == third.errors == []


def test_a_phone_that_joins_mid_round_hears_none_of_it(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    late = join(phones, "Onni", code)
    late.wait_for_function("document.getElementById('aipr-info').textContent === 'Kierros on käynnissä – pääset mukaan seuraavaan.'")
    host.wait_for_timeout(400)  # the host keeps sending the round to everyone
    host.evaluate("end()")
    guest.wait_for_function("demo.results.length === 1")
    late.wait_for_timeout(400)
    assert late.evaluate("demo.heard") == []
    assert late.evaluate("[demo.results.length, demo.phase]") == [0, "menu"]
    # The next round is everyone's.
    start(host, [guest, late])
    late.wait_for_function("demo.heard.includes('s')")
    host.evaluate("end()")
    late.wait_for_function("demo.results.length === 1")
    assert host.errors == guest.errors == late.errors == []


def test_a_page_reloading_as_the_round_ends_still_gets_its_result(phones):
    # The host sees the phone connected again before its hello: the end it sends then reaches a
    # page that does not know the round yet. Unconfirmed, it is sent again after the hello.
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    first = host.evaluate("demo.round")
    phones.relay.hold_hello(guest)
    guest.reload()
    guest.wait_for_function("AiPelitRooms.connected")
    host.wait_for_function("AiPelitRooms.members.every(m => m.on)")
    host.evaluate("end()")
    guest.wait_for_timeout(300)
    assert guest.evaluate("demo.results") == []
    phones.relay.let_hello(guest)
    guest.wait_for_function("demo.results.length === 1 && demo.phase === 'room'")
    assert guest.evaluate("demo.results") == [first]
    # Confirmed now: another hello (a second reload) does not send it again.
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.connected")
    guest.wait_for_timeout(400)
    assert guest.evaluate("demo.heard") == []
    assert host.errors == guest.errors == []


def test_a_result_heard_twice_counts_once(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    host.evaluate("end()")
    guest.wait_for_function("demo.results.length === 1")
    r = guest.evaluate("demo.round")
    assert guest.evaluate(f"AiPelitRooms.once({json.dumps(r)})") is False
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.connected")
    assert guest.evaluate(f"AiPelitRooms.once({json.dumps(r)})") is False


def test_a_typed_code_from_another_version_opens_the_rooms_version(phones):
    host, code = make_room(phones, "huonetesti/v2/")
    guest = phones("Aino", "huonetesti/v1/")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    guest.wait_for_url(re.compile(r".*/games/huonetesti/v2/$"))
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 2")
    host.wait_for_function("AiPelitRooms.members.length === 2")
    # Another game altogether works the same way.
    small, small_code = make_room(phones, "pieni/v1/")
    away = phones("Onni", "huonetesti/v2/")
    away.click("#multi")
    away.fill("#aipr-codeIn", small_code)
    away.click("#aipr-joinBtn")
    away.wait_for_url(re.compile(r".*/games/pieni/v1/$"))
    away.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 2")
    assert guest.errors == away.errors == []


def test_a_room_that_does_not_say_its_game_is_refused(phones):
    # Kirkkis v2 makes its rooms without saying its game; a game on rooms.js must not join one.
    old = phones("Eero")
    old.evaluate("""() => { const u = new URL('../../../api/rooms/VANH', location.href); u.protocol = 'ws:';
      u.search = new URLSearchParams({ key: 'f'.repeat(32), name: 'Eero', host: '1' }); window.oldWs = new WebSocket(u); }""")
    old.wait_for_function("window.oldWs.readyState === 1")
    guest = phones("Aino")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", "VANH")
    guest.click("#aipr-joinBtn")
    guest.wait_for_function("document.getElementById('aipr-err').textContent === 'Huone on toisessa pelissä.'")
    assert not guest.evaluate("AiPelitRooms.inRoom")
    assert guest.evaluate("location.pathname").endswith("/games/huonetesti/v2/")
    # It left the room again: only the old game's phone is in it.
    assert list(phones.relay.rooms["VANH"]["members"].values()) == ["Eero"]
    assert guest.errors == []


def test_a_room_takes_as_many_phones_as_the_game_says(phones):
    host, code = make_room(phones, "pieni/v1/")
    guests = [join(phones, n, code, "pieni/v1/") for n in ["Aino", "Eetu"]]
    host.wait_for_function("AiPelitRooms.members.length === 3")
    assert text(host, "info") == "3 pelaajaa – huone on täynnä."
    full = phones("Kuudes", "pieni/v1/")
    full.click("#multi")
    full.fill("#aipr-codeIn", code)
    full.click("#aipr-joinBtn")
    full.wait_for_function("document.getElementById('aipr-err').textContent === 'Huone on täynnä'")
    # The host leaving closes the room for everyone.
    host.click("#aipr-back")
    host.wait_for_function("demo.phase === 'menu' && document.getElementById('aipr').hidden")
    for g in guests:
        g.wait_for_function("!AiPelitRooms.inRoom && document.getElementById('aipr-err').textContent === 'Huone suljettiin.'")


def test_the_name_is_the_phones_one_nickname(phones):
    # No nickname: an animal name, kept through a reload, but not made the high-score nickname.
    page = phones(None)
    page.click("#multi")
    picked = page.input_value("#aipr-name")
    assert picked
    page.reload()
    page.click("#multi")
    assert page.input_value("#aipr-name") == picked
    assert page.evaluate("localStorage.getItem('ai-pelit:_pelaaja:nimi')") is None
    # A typed name is the phone's nickname, for the high-score lists too.
    page.fill("#aipr-name", "  Pikku   Myy ")
    page.click("#aipr-create")
    page.wait_for_function("AiPelitRooms.members.length === 1")
    assert page.locator("#aipr-members li").all_inner_texts() == ["👑 Pikku Myy (sinä)"]
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_pelaaja:nimi'))") == "Pikku Myy"


def test_the_room_screen_fits_a_small_phone(phones):
    host = phones("Eero", height=640)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for n in ["Aino", "Eetu", "Iida", "Onni"]:
        join(phones, n, code)
    host.wait_for_function("AiPelitRooms.members.length === 5")
    # Everything is on the screen without scrolling, the way out included.
    for part in ["#aipr-qr", "#aipr-pub", "#aipr-start", "#aipr-back"]:
        box = host.locator(part).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= 640, part


def test_a_public_room_is_listed_for_the_game_and_joined_with_a_tap(phones):
    host, code = make_room(phones)
    stranger = phones("Aino", "huonetesti/v1/")
    stranger.click("#multi")
    stranger.wait_for_function("!document.getElementById('aipr-none').hidden")
    assert text(stranger, "none") == "Ei avoimia huoneita juuri nyt."
    # The host makes the room public; a phone on another version of the game sees it.
    host.check("#aipr-pub")
    stranger.wait_for_selector("#aipr-rooms button", timeout=8000)
    assert stranger.locator("#aipr-rooms button").all_inner_texts() == [f"{code} · 1/5 pelaajaa"]
    # A phone on another game does not.
    other = phones("Iida", "pieni/v1/")
    other.click("#multi")
    other.wait_for_function("!document.getElementById('aipr-none').hidden")
    # One tap joins, in the room's own version; a guest has no switch.
    stranger.click("#aipr-rooms button")
    stranger.wait_for_url(re.compile(r".*/huonetesti/v2/$"))
    stranger.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 2")
    assert stranger.locator("#aipr-pubRow").is_hidden()
    # While a round runs the room is off the list, and back on once it ends.
    watcher = phones("Onni")
    watcher.click("#multi")
    watcher.wait_for_selector("#aipr-rooms button", timeout=8000)
    start(host, [stranger])
    watcher.wait_for_function("!document.querySelector('#aipr-rooms button')", timeout=8000)
    host.evaluate("end()")
    watcher.wait_for_selector("#aipr-rooms button", timeout=8000)
    # A host reload keeps the room public; switched off, it leaves the list.
    host.reload()
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 2")
    assert host.locator("#aipr-pub").is_checked()
    host.uncheck("#aipr-pub")
    watcher.wait_for_function("!document.querySelector('#aipr-rooms button')", timeout=8000)
    assert host.errors == stranger.errors == watcher.errors == other.errors == []
