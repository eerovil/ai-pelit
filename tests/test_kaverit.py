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
        self.declined = set()  # requests declined: still "asked" for the sender, unseen by the receiver
        self.friends = set()  # frozenset of two player ids
        self.presence = {}  # player id -> (game, version, at)
        self.invites = []  # dicts
        self.next_invite = 1
        self.calls = []
        self.taken = set()  # nicknames another phone owns: POST /api/players answers 409
        self.status = {}  # player id -> 'pending', 'approved' or 'rejected' (the admin's word)

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
            "me": {"name": self.names[me], "status": self.status.get(me, "pending")} if me in self.names else None,
            "friends": friends,
            "requests": [{"pid": pid_of(s), "name": self.names[s]} for s, r in self.requests
                         if r == mine and s in self.names and (s, r) not in self.declined],
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
            if body["name"].lower() in self.taken:
                return ok({"error": "name taken"}, 409)
            self.names[body["id"]] = body["name"]
            self.status[body["id"]] = "pending"
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
            if me not in self.names or self.status.get(me) == "rejected":
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
            if body.get("yes"):
                self.requests.discard((other, pid_of(me)))
                self.friends.add(frozenset((me, other)))
            else:
                self.declined.add((other, pid_of(me)))
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
        self.joins = getattr(self, "joins", [])
        self.joins.append((q["name"], q.get("fid")))
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


    def phone(name, path="huonetesti/v1/", player=None, width=360, height=740, clock=False):
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
        if clock:
            page.clock.install()
        page.goto(f"{site.url}{'games/' + path if path is not None else ''}")
        return page

    phone.api = api
    phone.site = site
    phone.relay = relay
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
    # The host joined again with its friend id and nickname: Bertta now sees Aino, with a way to
    # answer, and the round's room stayed the same.
    guest.wait_for_function(f"AiPelitRooms.members.some(m => m.fid === '{pid_of(A)}' && m.name === 'Aino' && m.on)")
    assert host.evaluate("[AiPelitRooms.inRoom, AiPelitRooms.code, AiPelitRooms.isHost]") == [True, code, True]
    guest.wait_for_selector("#aipr-members .frs", timeout=15_000)
    assert guest.locator("#aipr-members li", has_text="Aino").locator(".frs").inner_text() == "Pyytää kaveriksi"


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
    # Back goes up from the invited game, never into the game Bertta was playing: the chip to the
    # invited game's page (through its menu, #336), then the phone's back to the shelf.
    bertta.wait_for_function("AiPelitRooms.inRoom")
    bertta.click("#ai-pelit-back")
    bertta.click("#ai-pelit-takaisin")
    bertta.wait_for_url(re.compile(r".*/#/huonetesti$"))
    bertta.go_back()
    bertta.wait_for_timeout(500)
    assert "/games/" not in bertta.url


def test_an_invite_into_another_game_opened_from_the_shelf_keeps_the_way_up(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    # Bertta opens Toinen peli from the shelf: shelf → its page → the game.
    bertta = phones("Bertta", None, player=B)
    bertta.evaluate("localStorage.setItem('ai-pelit:_kaverit:on', 'true')")
    bertta.reload()
    bertta.wait_for_selector('.card[data-slug="toinen"]')
    bertta.click('.card[data-slug="toinen"] .button.play')
    bertta.wait_for_url(re.compile(r".*/games/toinen/v1/$"))
    bertta.wait_for_function("window.AiPelitKaverit && AiPelitKaverit.state")
    host = phones("Aino", player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    host.locator("#aipr-friends button", has_text="Kutsu kaveri").click()
    host.locator("#aipr-invList li", has_text="Bertta").locator("button").click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsuttu ✓'")
    bertta.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    bertta.wait_for_selector("#aipk")
    bertta.locator("#aipk button", has_text="Liity").click()
    bertta.wait_for_url(re.compile(r".*/games/huonetesti/v1/.*"))
    host.wait_for_function("AiPelitRooms.members.length === 2")
    # The phone's back: the invited game's page, then the shelf; Toinen peli never comes back.
    bertta.go_back()
    bertta.wait_for_url(re.compile(r".*/#/huonetesti$"))
    bertta.go_back()
    bertta.wait_for_url(re.compile(r".*/(#/?)?$"))
    assert "toinen" not in bertta.url
    # And the chip, after opening the game again from its page, goes to the same page.
    bertta.go_forward()
    bertta.wait_for_url(re.compile(r".*/#/huonetesti$"))


def test_the_room_screen_with_friends_fits_a_phone_both_ways(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.requests.add((B, pid_of(A)))
    phones.api.friends.add(frozenset((A, "c" * 32)))
    phones.api.names["c" * 32] = "Ceci"
    for size in ({"width": 360, "height": 740}, {"width": 390, "height": 844}, {"width": 740, "height": 360}):
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


def test_a_reload_keeps_the_friend_id_and_a_declined_request_stays_quiet(phones):
    host, guest, code = room_of_two(phones)
    # Bertta reloads in the room: she comes back with her friend id, and Aino's ➕ is still there.
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 2")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on && m.fid).length === 2")
    host.locator("#aipr-members button.fr").click()
    guest.wait_for_selector("#aipr-friends .ask", timeout=15_000)
    guest.locator("#aipr-friends .ask button", has_text="Ei").click()
    guest.wait_for_function("!document.querySelector('#aipr-friends .ask')")
    # Aino is not told: her row for Bertta still says "Pyydetty", and Bertta's shows ➕ again.
    host.wait_for_timeout(11_000)
    assert host.locator("#aipr-members .frs").inner_text() == "Pyydetty"
    assert guest.locator("#aipr-members button.fr").inner_text() == "➕ Kaveriksi"
    assert phones.api.friends == set()


def test_the_shelf_shows_a_friend_start_playing_without_a_reload(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    shelf = phones("Aino", None, player=A, width=390, height=844)
    shelf.wait_for_function("window.AiPelitKaverit && AiPelitKaverit.state")
    shelf.wait_for_timeout(300)
    assert shelf.locator(".friends-playing").is_hidden()
    # Bertta opens a game; the shelf's next 30 s check shows her playing.
    phones.api.presence[B] = ("huonetesti", 1, now_iso())
    shelf.wait_for_selector(".friends-playing:not([hidden]) .friend", timeout=40_000)
    assert "Pelaa: Huonetesti" in shelf.locator(".friends-playing").inner_text()
    assert shelf.evaluate("document.documentElement.scrollWidth") <= 390


def test_the_very_first_join_carries_the_friend_id(phones):
    host = phones("Aino", player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    # A room link opens the game straight into the room.
    phones("Bertta", f"huonetesti/v1/?huone={code}", player=B)
    # A phone with no nickname types one on the room screen and joins at once.
    c = "c" * 32
    ceci = phones(None, player=c)
    ceci.click("#multi")
    ceci.fill("#aipr-name", "Ceci")
    ceci.fill("#aipr-codeIn", code)
    ceci.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.length === 3 && AiPelitRooms.members.every(m => m.fid)")
    first = {}
    for name, fid in phones.relay.joins:
        first.setdefault(name, fid)
    assert first == {"Aino": pid_of(A), "Bertta": pid_of(B), "Ceci": pid_of(c)}
    assert host.locator("#aipr-members button.fr").count() == 2


def test_a_first_request_shows_on_an_open_shelf_with_no_friends(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    shelf = phones("Bertta", None, player=B, width=390, height=844)
    shelf.wait_for_function("window.AiPelitKaverit && AiPelitKaverit.state")
    shelf.wait_for_timeout(300)
    assert shelf.locator(".friends-playing").is_hidden()
    # Aino asks while Bertta's shelf is open; it shows within the front page's 30 s read, with
    # no "now playing" sent by a phone with no friends.
    phones.api.requests.add((A, pid_of(B)))
    shelf.wait_for_selector(".friends-playing:not([hidden]) .friend.ask", timeout=40_000)
    assert "Aino" in shelf.locator(".friends-playing").inner_text()
    assert [c for c in phones.api.calls if c[1] == "presence"] == []
    assert shelf.locator("#aipk").count() == 0  # on the shelf a request shows on the page
    shelf.locator(".friends-playing .friend.ask button", has_text="Hyväksy").click()
    shelf.wait_for_function("!document.querySelector('.friends-playing .friend.ask')")
    assert phones.api.friends == {frozenset((A, B))}


def test_friends_only_browsing_the_shelf_are_not_listed_as_playing(phones):
    c = "c" * 32
    phones.api.names.update({A: "Aino", B: "Bertta", c: "Ceci"})
    phones.api.friends.update({frozenset((A, B)), frozenset((A, c))})
    phones.api.presence[B] = (None, None, now_iso(5))
    phones.api.presence[c] = (None, None, now_iso(5))
    shelf = phones("Aino", None, player=A)
    shelf.wait_for_function("window.AiPelitKaverit && AiPelitKaverit.state && AiPelitKaverit.state.friends.length === 2")
    shelf.wait_for_timeout(300)
    assert shelf.locator(".friends-playing").is_hidden()
    shelf.click(".friends-link")
    shelf.wait_for_selector(".friend")
    assert shelf.locator(".friend .meta").all_inner_texts() == ["Selaa pelejä", "Selaa pelejä"]


def test_a_request_on_a_games_page_comes_as_a_banner(phones):
    phones.api.names.update({A: "Aino", B: "Bertta", "c" * 32: "Ceci"})
    phones.api.friends.add(frozenset((A, B)))
    shelf = phones("Aino", None, player=A)
    shelf.wait_for_selector('.card[data-slug="huonetesti"]')
    shelf.click('.card[data-slug="huonetesti"] .card-main')
    shelf.wait_for_selector(".game-head")
    # Ceci asks while Aino reads a game's page; her next "now playing" brings it as a banner.
    phones.api.requests.add(("c" * 32, pid_of(A)))
    shelf.wait_for_selector("#aipk", timeout=40_000)
    assert shelf.locator("#aipk p").inner_text() == "Ceci haluaa kaveriksi"
    # Back on the front page the request shows in the page, not as a banner.
    shelf.click(".back")
    shelf.wait_for_selector(".friends-playing:not([hidden]) .friend.ask")
    assert shelf.locator("#aipk").count() == 0


def test_an_old_invite_can_be_sent_again_while_the_room_is_open(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    host = phones("Aino", player=A, clock=True)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    host.locator("#aipr-friends button", has_text="Kutsu kaveri").click()
    button = host.locator("#aipr-invList li", has_text="Bertta").locator("button")
    button.click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsuttu ✓'")
    assert button.is_disabled()
    # Ten minutes later the server has dropped the unanswered invite: it may be sent again.
    host.clock.fast_forward(10 * 60_000 + 1000)
    host.locator("#aipr-invClose").click()
    host.locator("#aipr-friends button", has_text="Kutsu kaveri").click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsu'")
    button.click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsuttu ✓'")
    assert len([c for c in phones.api.calls if c[1] == "invites"]) == 2


def test_a_taken_nickname_on_the_friends_page_keeps_the_field(phones):
    phones.api.taken.add("aino")
    shelf = phones(None, None, player=A)
    shelf.wait_for_selector(".card")
    shelf.click(".friends-link")
    shelf.fill(".friends-name", "Aino")
    shelf.locator(".friends-form button").click()
    shelf.wait_for_selector(".friends-name-error")
    assert shelf.locator(".friends-name-error").inner_text() == "Nimimerkki Aino on jo käytössä. Valitse toinen."
    assert shelf.locator(".friends-name").is_visible()
    assert shelf.evaluate("localStorage.getItem('ai-pelit:_pelaaja:nimi')") is None
    shelf.fill(".friends-name", "Aino2")
    shelf.locator(".friends-form button").click()
    shelf.wait_for_function("!document.querySelector('.friends-name')")
    assert phones.api.names[A] == "Aino2"
    assert shelf.locator(".friends-name-error").count() == 0


def test_a_taken_nickname_in_the_room_asks_again_and_sends_nothing(phones):
    phones.api.taken.add("aino")
    host = phones(None, player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest = phones("Bertta", player=B)
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.length === 2")
    joins = len(phones.relay.joins)
    host.locator("#aipr-members button.fr").click()
    host.fill("#aipr-friends .ask input", "Aino")
    host.locator("#aipr-friends .ask button").click()
    host.wait_for_function("[...document.querySelectorAll('#aipr-friends .small')].some(p => p.textContent === 'Nimimerkki Aino on jo käytössä. Valitse toinen.')")
    # No request, no new join, the field is still there and ready.
    assert [c for c in phones.api.calls if c[1] == "friends/requests"] == []
    assert len(phones.relay.joins) == joins
    assert host.locator("#aipr-friends .ask button").is_enabled()
    host.fill("#aipr-friends .ask input", "Aino2")
    host.locator("#aipr-friends .ask button").click()
    host.wait_for_function("document.querySelector('#aipr-members .frs') && document.querySelector('#aipr-members .frs').textContent === 'Pyydetty'")
    assert (A, pid_of(B)) in phones.api.requests
    guest.wait_for_function(f"AiPelitRooms.members.some(m => m.fid === '{pid_of(A)}' && m.name === 'Aino2')")


def registered(page, name):
    """The phone's nickname as the server already has it (sent before, so not sent again)."""
    page.evaluate(f"""localStorage.setItem('ai-pelit:_pelaaja:lahetetty', JSON.stringify({json.dumps(name)}));
        localStorage.setItem('ai-pelit:_pelaaja:tila', JSON.stringify('approved'))""")


def test_a_name_rejected_while_the_friends_page_is_open_offers_a_new_one(phones):
    phones.api.names[A] = "Aino"
    phones.api.status[A] = "approved"
    shelf = phones("Aino", None, player=A)
    registered(shelf, "Aino")
    shelf.reload()
    shelf.wait_for_selector(".card")
    shelf.click(".friends-link")
    shelf.wait_for_selector(".friends-none, .friend")
    assert shelf.locator(".friends-name").count() == 0
    # The admin rejects the name; the page's next 10 s read brings it, and a field for a new one.
    phones.api.status[A] = "rejected"
    shelf.wait_for_selector(".friends-name", timeout=15_000)
    assert "Ylläpitäjä ei hyväksynyt nimimerkkiä Aino" in shelf.locator("main").inner_text()
    shelf.fill(".friends-name", "Aino2")
    shelf.locator(".friends-form button").click()
    shelf.wait_for_function("!document.querySelector('.friends-name')")
    assert phones.api.names[A] == "Aino2" and phones.api.status[A] == "pending"


def test_a_name_rejected_while_in_the_room_offers_a_new_one_then_asks(phones):
    host, guest, code = room_of_two(phones)
    host.wait_for_selector("#aipr-members button.fr")
    # Aino's name was registered (room_of_two sends it on the first ask); the admin rejects it.
    phones.api.names[A] = "Aino"
    phones.api.status[A] = "rejected"
    registered(host, "Aino")
    host.locator("#aipr-members button.fr").click()
    host.wait_for_selector("#aipr-friends .ask input")
    assert "Ylläpitäjä ei hyväksynyt nimimerkkiä Aino" in host.locator("#aipr-friends .ask").inner_text()
    assert phones.api.requests == set()
    host.fill("#aipr-friends .ask input", "Aino2")
    host.locator("#aipr-friends .ask button").click()
    host.wait_for_function("document.querySelector('#aipr-members .frs') && document.querySelector('#aipr-members .frs').textContent === 'Pyydetty'")
    assert (A, pid_of(B)) in phones.api.requests
    guest.wait_for_function(f"AiPelitRooms.members.some(m => m.fid === '{pid_of(A)}' && m.name === 'Aino2')")


def test_joining_by_an_invite_leaves_the_room_the_phone_was_in(phones):
    phones.api.names.update({A: "Aino", B: "Bertta"})
    phones.api.friends.add(frozenset((A, B)))
    c = "c" * 32
    # Ceci hosts a room in Toinen peli, and Bertta is in it.
    ceci = phones("Ceci", "toinen/v1/", player=c)
    ceci.click("#multi")
    ceci.click("#aipr-create")
    ceci.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    old = ceci.evaluate("AiPelitRooms.code")
    bertta = phones("Bertta", f"toinen/v1/?huone={old}", player=B)
    bertta.evaluate("localStorage.setItem('ai-pelit:_kaverit:on', 'true')")
    ceci.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    # Aino invites Bertta into her room in Huonetesti.
    host = phones("Aino", player=A)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    host.locator("#aipr-friends button", has_text="Kutsu kaveri").click()
    host.locator("#aipr-invList li", has_text="Bertta").locator("button").click()
    host.wait_for_function("document.querySelector('#aipr-invList button').textContent === 'Kutsuttu ✓'")
    bertta.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    bertta.wait_for_selector("#aipk")
    bertta.locator("#aipk button", has_text="Liity").click()
    bertta.wait_for_url(re.compile(r".*/games/huonetesti/v1/.*"))
    host.wait_for_function("AiPelitRooms.members.length === 2")
    # Ceci's room saw her leave for good, not drop off.
    ceci.wait_for_function("AiPelitRooms.members.length === 1")
    # The tab now keeps the new room, not Ceci's, so opening Toinen peli again does not rejoin it.
    here = json.loads(bertta.evaluate("sessionStorage.getItem('ai-pelit:_huone:nyt')"))
    assert here["game"] == "huonetesti" and here["code"] != old
