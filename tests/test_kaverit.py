"""Friends (#324): public/kaverit.js, the friend buttons on rooms.js's room screen, the banner
back.js brings to every game, and the shelf's friends page.

Each phone is its own Chromium context. The room is test_rooms_lib's `Relay`, which passes each
member's `fid` on as rooms/worker.js does. The friends API (server/api.js, tested on its own by
tests/server/friends.test.mjs) is played by `FriendsApi`, which keeps the same state in memory.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from conftest import make_game
from test_rooms_lib import Relay, demo_page


def pid_of(player):
    return hashlib.sha256(player.encode()).hexdigest()[:32]


def now_iso(seconds_ago=0):
    t = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class FriendsApi:
    def __init__(self):
        self.names = {}  # player id -> nickname
        self.requests = set()  # (sender id, receiver pid)
        self.friends = set()  # frozenset of two player ids
        self.presence = {}  # player id -> (game, version, at)
        self.invites = []  # dicts
        self.next_invite = 1
        self.calls = []

    def attach(self, context):
        context.route(re.compile(r".*/api/(players|friends|presence|invites)(\b.*)?$"), self.answer)

    def by_pid(self, pid):
        return next((p for p in self.names if pid_of(p) == pid), None)

    def state(self, me):
        mine = pid_of(me)
        friends = []
        for pair in self.friends:
            if me in pair:
                other = next(p for p in pair if p != me)
                game, version, at = self.presence.get(other, (None, None, None))
                now = bool(at) and at > now_iso(90)
                friends.append({"pid": pid_of(other), "name": self.names[other], "game": game, "version": version, "at": at, "now": now})
        friends.sort(key=lambda f: (not f["now"], f["name"].lower()))
        return {
            "pid": mine,
            "friends": friends,
            "requests": [{"pid": pid_of(s), "name": self.names[s]} for s, r in self.requests if r == mine and s in self.names],
            "asked": [r for s, r in self.requests if s == me],
            "invites": [{k: i[k] for k in ("id", "from", "name", "game", "version", "room")} for i in self.invites if i["to"] == me],
        }

    def answer(self, route):
        req = route.request
        url = urlparse(req.url)
        path = url.path.split("/api/", 1)[1].rstrip("/")
        body = json.loads(req.post_data or "{}") if req.method != "GET" else {}
        self.calls.append((req.method, path, body))

        def ok(data=None, status=200):
            route.fulfill(status=status, content_type="application/json", body=json.dumps(data if data is not None else {"ok": True}))

        if path == "players" and req.method == "POST":
            self.names[body["id"]] = body["name"]
            return ok({"name": body["name"], "status": "pending"})
        if path == "friends" and req.method == "GET":
            return ok(self.state(parse_qs(url.query)["player"][0]))
        if path == "presence":
            me = body["player"]
            if me not in self.names:
                return ok({"error": "unknown player"}, 404)
            self.presence[me] = (body.get("game"), body.get("version"), now_iso())
            return ok(self.state(me))
        if path == "friends/requests":
            me, to = body["player"], body["to"]
            if me not in self.names:
                return ok({"error": "nickname needed"}, 403)
            other = self.by_pid(to)
            if other and (other, pid_of(me)) in self.requests:
                self.requests.discard((other, pid_of(me)))
                self.friends.add(frozenset((me, other)))
                return ok({"ok": True, "friends": True})
            self.requests.add((me, to))
            return ok({"ok": True, "friends": False})
        if path == "friends/requests/answer":
            me, other = body["player"], self.by_pid(body["from"])
            if not other or (other, pid_of(me)) not in self.requests:
                return ok({"error": "no such request"}, 404)
            if body.get("yes") and me not in self.names:
                return ok({"error": "nickname needed"}, 403)
            self.requests.discard((other, pid_of(me)))
            if body.get("yes"):
                self.friends.add(frozenset((me, other)))
            return ok()
        if path == "friends" and req.method == "DELETE":
            other = self.by_pid(body["pid"])
            self.friends.discard(frozenset((body["player"], other)))
            return ok()
        if path == "invites":
            me, other = body["player"], self.by_pid(body["to"])
            if frozenset((me, other)) not in self.friends:
                return ok({"error": "friends only"}, 403)
            self.invites = [i for i in self.invites if not (i["sender"] == me and i["to"] == other)]
            self.invites.append({"id": self.next_invite, "sender": me, "to": other, "from": pid_of(me), "name": self.names[me],
                                 "game": body["game"], "version": body["version"], "room": body["room"]})
            self.next_invite += 1
            return ok()
        m = re.fullmatch(r"invites/(\d+)/answer", path)
        if m:
            self.invites = [i for i in self.invites if not (i["id"] == int(m[1]) and i["to"] == body["player"])]
            return ok()
        return ok({"error": "no such route"}, 404)


class RelayWithFids(Relay):
    """test_rooms_lib's Relay, keeping each member's friend id as rooms/worker.js does."""

    def connect(self, ws):
        q = {k: v[0] for k, v in parse_qs(urlparse(ws.url).query).items()}
        me = hashlib.sha256(q["key"].encode()).hexdigest()[:32]
        self.fids = getattr(self, "fids", {})
        if re.fullmatch(r"[a-f0-9]{32}", q.get("fid", "")):
            self.fids[me] = q["fid"]
        else:
            self.fids.pop(me, None)
        super().connect(ws)

    def peers(self, room):
        msg = {"t": "peers", "host": room["host"], "members": [
            {"id": i, "name": n, "on": i in room["socks"], **({"fid": self.fids[i]} if i in getattr(self, "fids", {}) else {})}
            for i, n in room["members"].items()]}
        if room["game"]:
            msg.update(game=room["game"], v=room["v"])
        for ws in list(room["socks"].values()):
            ws.send(json.dumps(msg))


@pytest.fixture
def phones(site, browser):
    make_game(site.games, "huonetesti", [demo_page()], title="Huonetesti")
    make_game(site.games, "toinen", [demo_page("toinen")], title="Toinen peli")
    site.build()
    relay, api, contexts = RelayWithFids(), FriendsApi(), []

    def phone(name, path="huonetesti/v1/", player=None, width=360, height=740):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        script = ""
        if name:
            script += f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))});"
        if player:
            script += f"localStorage.setItem('ai-pelit:_pelaaja:id', {json.dumps(json.dumps(player))});"
        if script:
            ctx.add_init_script(f"if (!sessionStorage.getItem('init')) {{ sessionStorage.setItem('init', 1); {script} }}")
        api.attach(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}{'games/' + path if path is not None else ''}")
        return page

    phone.api = api
    phone.site = site
    yield phone
    for ctx in contexts:
        ctx.close()


A, B = "a" * 32, "b" * 32


def room_of_two(phones, b_name="Bertta"):
    host = phones("Aino", player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest = phones(b_name, player=B)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.length === 2 && AiPelitRooms.members.every(m => m.fid)")
    return host, guest, code


def test_a_friend_is_made_in_the_room_and_accepted(phones):
    host, guest, _ = room_of_two(phones)
    # Each player's friend id is a hash of the phone's player id, never the id itself.
    assert sorted(m["fid"] for m in host.evaluate("AiPelitRooms.members")) == sorted([pid_of(A), pid_of(B)])
    ask = host.locator("#aipr-members li", has_text="Bertta").locator("button.fr")
    ask.wait_for()
    assert ask.inner_text() == "➕ Kaveriksi"
    assert host.locator("#aipr-members li", has_text="Aino").locator(".fr, .frs").count() == 0
    ask.click()
    host.wait_for_function("document.querySelector('#aipr-members .frs') && document.querySelector('#aipr-members .frs').textContent === 'Pyydetty'")
    # Bertta's room screen shows the request within its 10 s check.
    guest.wait_for_selector("#aipr-friends .ask", timeout=15_000)
    assert "Aino haluaa kaveriksi" in guest.locator("#aipr-friends .ask").inner_text()
    guest.locator("#aipr-friends .ask button", has_text="Hyväksy").click()
    guest.wait_for_function("document.querySelector('#aipr-members .frs') && document.querySelector('#aipr-members .frs').textContent === '👫 Kaveri'")
    assert phones.api.friends == {frozenset((A, B))}
    host.wait_for_function("document.querySelector('#aipr-members .frs').textContent === '👫 Kaveri'", timeout=15_000)
    assert host.errors == [] and guest.errors == []


def test_no_nickname_asks_for_one_first(phones):
    host = phones(None, player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest = phones("Bertta", player=B)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    # The host has an animal name, so others get no ➕ beside it; it still sees one beside Bertta.
    host.wait_for_function("AiPelitRooms.members.length === 2")
    guest.wait_for_timeout(500)
    assert guest.locator("#aipr-members button.fr").count() == 0
    host.locator("#aipr-members button.fr").click()
    host.fill("#aipr-friends .ask input", "Aino")
    host.locator("#aipr-friends .ask button").click()
    host.wait_for_function("document.querySelector('#aipr-members .frs') && document.querySelector('#aipr-members .frs').textContent === 'Pyydetty'")
    assert phones.api.names[A] == "Aino"
    assert (A, pid_of(B)) in phones.api.requests


def test_an_invite_reaches_a_friend_in_another_game_and_joins_the_room(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    # Bertta has friends on this phone already, so she tells what she plays.
    bertta = phones("Bertta", "toinen/v1/", player=B)
    bertta.evaluate("localStorage.setItem('ai-pelit:_kaverit:on', 'true')")
    bertta.reload()
    bertta.wait_for_function("window.AiPelitKaverit && AiPelitKaverit.state")
    assert phones.api.presence[B][:2] == ("toinen", 1)
    host = phones("Aino", player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    host.locator("#aipr-friends button", has_text="Kutsu kaveri").click()
    row = host.locator("#aipr-invList li", has_text="Bertta")
    assert "Pelaa: Toinen peli" in row.inner_text()
    row.locator("button").click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsuttu ✓'")
    # Bertta's next "now playing" brings the invite; the banner's Liity opens the room.
    bertta.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    bertta.wait_for_selector("#aipk")
    assert bertta.locator("#aipk p").inner_text() == "Aino kutsuu sinut pelaamaan: Huonetesti"
    bertta.locator("#aipk button", has_text="Liity").click()
    bertta.wait_for_url(re.compile(r".*/games/huonetesti/v1/.*"))
    host.wait_for_function("AiPelitRooms.members.length === 2")
    assert phones.api.invites == []
    host.locator("#aipr-invClose").click()
    assert host.locator("#aipr-inv").is_hidden()


def test_the_room_screen_with_friends_fits_a_phone_both_ways(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.requests.add((B, pid_of(A)))
    phones.api.friends.add(frozenset((A, "c" * 32)))
    phones.api.names["c" * 32] = "Ceci"
    for size in ({"width": 360, "height": 740}, {"width": 740, "height": 360}):
        host = phones("Aino", player=A, **size)
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_selector("#aipr-friends .ask")
        host.wait_for_selector("#aipr-friends > button")
        box = host.evaluate("[document.getElementById('aipr').scrollHeight, innerHeight, document.documentElement.scrollWidth, innerWidth]")
        assert box[0] <= box[1] and box[2] <= box[3], size


def test_the_shelf_lists_friends_and_requests_and_shows_who_plays(phones):
    phones.api.names.update({A: "Aino", B: "Bertta", "c" * 32: "Ceci"})
    phones.api.friends.add(frozenset((A, B)))
    phones.api.requests.add(("c" * 32, pid_of(A)))
    phones.api.presence[B] = ("huonetesti", 1, now_iso(10))
    shelf = phones("Aino", None, player=A)
    shelf.wait_for_selector(".friends-playing:not([hidden]) .friend")
    assert "Bertta" in shelf.locator(".friends-playing").inner_text()
    assert "Pelaa: Huonetesti" in shelf.locator(".friends-playing").inner_text()
    shelf.click(".friends-link")
    shelf.wait_for_selector(".friend.ask")
    assert "Ceci" in shelf.locator(".friend.ask").inner_text()
    shelf.locator(".friend.ask button", has_text="Hyväksy").click()
    shelf.wait_for_function("document.querySelectorAll('.friend:not(.ask)').length === 2")
    assert frozenset((A, "c" * 32)) in phones.api.friends
    assert shelf.evaluate("document.documentElement.scrollWidth") <= 360
    shelf.once("dialog", lambda d: d.accept())
    shelf.locator('.friend[data-pid="%s"] .friend-remove' % pid_of(B)).click()
    shelf.wait_for_function("document.querySelectorAll('.friend:not(.ask)').length === 1")
    assert frozenset((A, B)) not in phones.api.friends
    assert shelf.errors == []


def test_no_friends_no_network_traffic_in_a_game(phones):
    page = phones("Aino", player=A)
    page.wait_for_function("window.AiPelitKaverit")
    page.wait_for_timeout(500)
    assert [c for c in phones.api.calls if c[1] == "presence"] == []
    assert page.locator("#aipk").count() == 0
    assert page.errors == []
