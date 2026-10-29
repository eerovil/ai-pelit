"""Kirkkis v2: playing alone as in v1, and 2-5 phones in one room (#27).

Each phone is its own Chromium context. The room relay (rooms/worker.js on Cloudflare) is played
here by `Relay`, which answers the pages' WebSockets the same way: the host's messages to everyone
(or to `to`), the others' messages to the host with `from`, and `peers` whenever someone comes or
goes.
"""

import asyncio
import json
import re
from urllib.parse import parse_qs, urlparse

import pytest

from conftest import ROOT

RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"
COUNT_PLUS_SEEK = 10 + 100 + 3


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

    def attach(self, page):
        page.route_web_socket(re.compile(r".*/api/rooms/.*"), self.connect)

    def connect(self, ws):
        url = urlparse(ws.url)
        code = url.path.rsplit("/", 1)[1].upper()
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        me, name, host = q["id"], q["name"], q.get("host") == "1"
        if me in self.blocked:
            close(ws, 1001, "")
            return
        room = self.rooms.get(code)
        if host and (room is None or (room["host"] != me and not room["socks"])):
            room = self.rooms[code] = {"host": me, "members": {}, "socks": {}}
        elif host and room["host"] != me:
            close(ws, 4009, "Koodi on jo käytössä")
            return
        elif room is None:
            close(ws, 4004, "Huonetta ei löydy")
            return
        if me not in room["members"] and len(room["members"]) >= 5:
            close(ws, 4001, "Huone on täynnä")
            return
        room["members"][me] = name
        old = room["socks"].get(me)
        room["socks"][me] = ws
        if old:
            close(old, 4000, "Avattu toisaalla")
        ws.on_message(lambda m: self.message(room, me, m))
        ws.on_close(lambda code, reason: self.closed(room, me, ws))
        self.peers(room)

    def message(self, room, me, text):
        msg = json.loads(text)
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
        text = json.dumps({"t": "peers", "host": room["host"], "members": [
            {"id": i, "name": n, "on": i in room["socks"]} for i, n in room["members"].items()]})
        for ws in list(room["socks"].values()):
            ws.send(text)

    def drop(self, page):
        """The phone loses its connection until `back()`."""
        me = page.evaluate("myId")
        self.blocked.add(me)
        for room in self.rooms.values():
            ws = room["socks"].get(me)
            if ws:
                close(ws, 1001, "")

    def back(self, page):
        self.blocked.discard(page.evaluate("myId"))


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name, query=""):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:kirkkis:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}games/kirkkis/v2/{query}")
        return page

    phone.relay = relay
    yield phone
    for ctx in contexts:
        ctx.close()


def make_room(phone):
    host = phone("Eero")
    host.click("#multi")
    host.click("#create")
    host.wait_for_function("net.joined && net.members.length === 1")
    return host, host.evaluate("net.code")


def join(phone, name, code):
    page = phone(name)
    page.click("#multi")
    page.fill("#codeIn", code.lower())
    page.click("#join")
    page.wait_for_function("net.joined")
    return page


def start(host, guests, host_seeks=False):
    if host_seeks:
        host.evaluate("nextSeeker = { id: myId }")
    host.wait_for_function(f"net.members.filter(m => m.on).length === {1 + len(guests)}")
    host.click("#startRound")
    for g in guests:
        g.wait_for_function("phase === 'count' && people.length === 5")
    # Everyone hides at once (far apart, out of the seeker's way), then most of the count is skipped.
    for i, g in enumerate(guests):
        if g.evaluate("seeker !== player"):
            g.evaluate(f"() => {{ const s = SPOTS.filter(s => dist(s, BASE) > 12)[{i} * 9]; player.x = s.x; player.y = s.y; }}")
            host.wait_for_function(f"dist(people.find(p => p.id === {json.dumps(g.evaluate('myId'))}), BASE) > 12")
    host.evaluate("""() => { for (const b of bots) if (b !== seeker) { b.x = b.spot.x; b.y = b.spot.y; b.path = []; }
      if (seeker !== player) { const s = SPOTS.filter(s => dist(s, BASE) > 12).at(-1); player.x = s.x; player.y = s.y; } }""")
    host.evaluate("timer = 0.2")
    host.wait_for_function("phase === 'seek'")
    for g in guests:
        g.wait_for_function("phase === 'seek'")


def test_alone_it_plays_as_v1_and_keeps_v1_saves(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("localStorage.setItem('ai-pelit:kirkkis:tilasto', JSON.stringify({ kierrokset: 3, pelastuit: 2, kirkattiin: 1, kirkkasit: 4 }))")
    page.goto(f"{site.url}games/kirkkis/v2/")
    assert page.locator("#total").inner_text() == "Kierroksia 3 · pelastuit 2 · kirkkasit 4"
    results = page.evaluate("""() => { const out = [];
      for (let r = 0; r < 4; r++) {
        newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
        while (phase !== 'menu' && t < 130) { step(1 / 30); t += 1 / 30; }
        out.push({ t, menu: phase === 'menu', next: nextSeeker.name, first: firstCaught ? firstCaught.name : null, seeker: seeker.name, n: people.length });
      } return out; }""")
    for r in results:
        assert r["menu"] and r["t"] < COUNT_PLUS_SEEK and r["n"] == 5
        assert r["next"] == (r["first"] or r["seeker"])
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto')).kierrokset") == 7
    # The hider who reaches the base first is saved, and hears it.
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    page.evaluate("seeker.x = 26; seeker.y = 42; seeker.goal = { x: 26, y: 43 }; seeker.path = []")
    page.evaluate("player.x = 15; player.y = 20.9; step(1 / 30)")
    assert page.evaluate("[player.st, msg]") == ["saved", "Pelastuit! 🎉"]
    assert errors == []


def test_the_qr_code_reads_back_as_the_join_link(site, context):
    cv2 = pytest.importorskip("cv2")
    import numpy as np

    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/kirkkis/v2/")
    detector = cv2.QRCodeDetector()
    for text in ["https://pelit.vilpponen.fi/games/kirkkis/v2/?huone=KISA", "AB",
                 "http://127.0.0.1:8000/games/kirkkis/v2/?huone=ABCD", "x" * 150]:
        m = page.evaluate("t => qrMatrix(t).map(r => r.map(Number))", text)
        img = (1 - np.pad(np.array(m, dtype=np.uint8), 4)) * 255
        img = np.kron(img, np.ones((8, 8))).astype(np.uint8)
        got, _, _ = detector.detectAndDecode(img)
        assert got == text, (len(m), text)


def test_two_phones_meet_in_a_room_by_its_code(phones):
    host, code = make_room(phones)
    assert re.fullmatch(r"[A-Z]{4}", code)
    assert host.locator("#code").inner_text() == code
    assert host.locator("#startRound").is_disabled()
    guest = join(phones, "Aino", code)
    host.wait_for_function("net.members.length === 2")
    assert host.locator("#members li").all_inner_texts() == ["👑 Eero (sinä)", "Aino"]
    assert guest.locator("#members li").all_inner_texts() == ["👑 Eero", "Aino (sinä)"]
    assert guest.locator("#roomInfo").inner_text() == "Odotetaan, että Eero aloittaa kierroksen…"
    assert host.locator("#startRound").is_enabled()
    # A wrong code says so.
    lost = phones("Iida")
    lost.click("#multi")
    lost.fill("#codeIn", "ZZZZ" if code != "ZZZZ" else "YYYY")
    lost.click("#join")
    lost.wait_for_function("document.getElementById('netErr').textContent === 'Huonetta ei löydy'")
    assert not lost.evaluate("net.on")
    assert host.errors == guest.errors == []


def test_a_join_link_joins_at_once(phones):
    host, code = make_room(phones)
    assert host.evaluate("joinLink()").endswith(f"/games/kirkkis/v2/?huone={code}")
    guest = phones("Onni", f"?huone={code}")
    guest.wait_for_function("net.joined && net.members.length === 2")
    assert guest.evaluate("location.search") == ""
    # A reload goes back to the same room.
    guest.reload()
    guest.wait_for_function("net.joined")
    assert guest.evaluate("[net.code, net.host]") == [code, False]


def test_each_phone_sees_its_own_view_and_the_host_runs_the_rules(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest], host_seeks=True)
    # Same cast on both phones: two people and three computer players.
    names = "people.map(p => p.name)"
    assert host.evaluate(names) == guest.evaluate(names) == ["Eero", "Aino", "Eetu", "Iida", "Onni"]
    assert guest.evaluate("[seeker.name, player.name, player.role]") == ["Eero", "Aino", "hider"]
    # The guest's finger moves the guest; the host sees the guest arrive where they went.
    guest.evaluate("player.x = 15; player.y = 31; player.a = 0")
    host.wait_for_function("Math.abs(people[1].x - 15) < 0.05 && Math.abs(people[1].y - 31) < 0.05")
    # The host looks at the guest, standing in the open: the guest is seen, and hears it.
    host.evaluate("""() => { player.x = 15; player.y = 26; player.a = Math.PI / 2;
      for (const b of bots) { b.x = 2.5; b.y = 24; b.goal = b.spot = { x: 2.5, y: 24 }; b.path = []; b.brave = 999; } }""")
    guest.wait_for_function("player.st === 'spotted' && msg === 'Sinut nähtiin! Juokse pesään!'")
    assert host.evaluate("msg") == "Näit Ainon! Pesään!"
    # Each phone draws only what its own player sees: the guest does not see the far bots.
    assert guest.evaluate("canSee(player, people[2])") is False
    # The host reaches the base first: the guest is caught on both phones.
    host.evaluate("player.x = 15; player.y = 23")
    guest.wait_for_function("player.st === 'caught' && msg === 'Sinut kirkattiin! 😱'")
    # The round plays out; both phones go back to the room and keep their own tally.
    host.evaluate("timer = 0.1")
    host.wait_for_function("phase === 'room'", timeout=8000)
    guest.wait_for_function("phase === 'room'", timeout=8000)
    assert guest.locator("#roomResult").inner_text() == "Sinut kirkattiin!"
    assert guest.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))")["kirkattiin"] == 1
    assert host.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))")["kirkkasit"] >= 1
    # The first one caught seeks next.
    assert host.locator("#roomInfo").inner_text().endswith("Seuraavaksi etsii Aino.")
    assert host.locator("#startRound").inner_text() == "Uusi kierros"
    host.click("#startRound")
    guest.wait_for_function("phase === 'count' && seeker === player")
    assert host.errors == guest.errors == []


def test_the_round_waits_for_a_phone_that_drops_off(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    phones.relay.drop(guest)
    host.wait_for_function("document.getElementById('pauseText').textContent === '⏸ Odotetaan: Aino'")
    assert host.locator("#goOn").is_visible()
    guest.wait_for_function("document.getElementById('pauseText').textContent === 'Yhteys katkesi – yhdistetään…'")
    held = host.evaluate("timer")
    host.wait_for_timeout(600)
    assert host.evaluate("timer") == held
    # Back again: the round goes on where it was.
    phones.relay.back(guest)
    host.wait_for_function("waiting.length === 0 && timer < " + str(held), timeout=8000)
    guest.wait_for_function("net.connected && phase === 'seek' && document.getElementById('pause').classList.contains('hidden')")
    # Dropped again, and the host goes on without them: a computer player takes over.
    phones.relay.drop(guest)
    host.wait_for_function("waiting.length === 1")
    host.click("#goOn")
    host.wait_for_function("people[1].ctrl === 'bot' && timer < " + str(host.evaluate("timer")))
    # When the phone comes back, it takes its player back.
    phones.relay.back(guest)
    host.wait_for_function("people[1].ctrl === 'remote'", timeout=8000)
    guest.wait_for_function("phase === 'seek' && net.connected")
    assert host.errors == guest.errors == []


def test_a_room_takes_five_phones_and_the_host_leaving_closes_it(phones):
    host, code = make_room(phones)
    guests = [join(phones, n, code) for n in ["Aino", "Eetu", "Iida", "Onni"]]
    host.wait_for_function("net.members.length === 5")
    full = phones("Kuudes")
    full.click("#multi")
    full.fill("#codeIn", code)
    full.click("#join")
    full.wait_for_function("document.getElementById('netErr').textContent === 'Huone on täynnä'")
    start(host, guests)
    # Five people, no computer players; the cast's names clash with no bot's.
    assert host.evaluate("[people.length, bots.length]") == [5, 0]
    host.click("#netBack") if host.locator("#netBack").is_visible() else host.evaluate("leaveRoom()")
    for g in guests:
        g.wait_for_function("!net.on && document.getElementById('netErr').textContent === 'Huone suljettiin.'")
