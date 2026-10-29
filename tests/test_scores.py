"""High-score lists in a phone-sized Chromium (#25): public/scores.js, the admin page and the
shelf, against a stand-in for /api/ (the real one, server/api.js, has its own tests in
tests/server/). The games still play when the network is gone."""

import json
import re
from urllib.parse import parse_qs, urlparse

import pytest

from conftest import ROOT
from test_sormiskeitti import PLAY

ADMIN_KEY = "avain"


class FakeApi:
    """Just enough of server/api.js for the browser side; `online = False` drops every request."""

    def __init__(self):
        self.online = True
        self.players = {}  # id -> {name, status}
        self.scores = {}  # (game, board, player) -> {score, version}
        self.posts = []
        self.taken = set()  # player ids whose name another phone holds now
        self.refuse = {}  # name -> HTTP status that POST /api/players answers for it
        self.score_refusals = []  # HTTP statuses the next POST /api/scores answer, in turn

    def handle(self, route):
        if not self.online:
            return route.abort()
        req = route.request
        url = urlparse(req.url)
        path = url.path.split("/api/", 1)[1]
        body = json.loads(req.post_data) if req.post_data else {}
        if req.method == "POST":
            self.posts.append((path, body))
        if path == "players" and req.method == "POST" and body["name"] in self.refuse:
            return self.reply(route, {"error": "refused"}, self.refuse[body["name"]])
        if path == "players" and req.method == "POST":
            old = self.players.get(body["id"])
            if not old or old["name"] != body["name"]:
                self.players[body["id"]] = {"name": body["name"], "status": "pending"}
            return self.reply(route, self.players[body["id"]])
        if m := re.fullmatch(r"players/(\w+)", path):
            p = self.players.get(m[1])
            return self.reply(route, p, 200 if p else 404)
        if path == "scores" and req.method == "POST" and self.score_refusals:
            return self.reply(route, {"error": "refused"}, self.score_refusals.pop(0))
        if path == "scores" and req.method == "POST":
            if body["player"] not in self.players:
                return self.reply(route, {"error": "unknown player"}, 404)
            self.scores[(body["game"], body["board"], body["player"])] = {"score": body["score"], "version": body["version"]}
            return self.reply(route, {"best": body["score"], "rank": 1})
        if path == "scores":
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            rows, mine = [], None
            for (game, board, player), s in self.scores.items():
                if game != q["game"] or board != q.get("board", "main"):
                    continue
                p = self.players[player]
                if p["status"] == "approved":
                    rows.append({"name": p["name"], **s, "me": player == q.get("player")})
                if player == q.get("player"):
                    mine = {**p, **s}
            rows.sort(key=lambda r: -r["score"])
            for i, r in enumerate(rows):
                r["rank"] = i + 1
            return self.reply(route, {"rows": rows, "mine": mine})
        if path == "admin/players":
            if req.headers.get("x-admin-key") != ADMIN_KEY:
                return self.reply(route, {"error": "admin key needed"}, 403)
            if req.method == "POST" and body.get("name") != self.players[body["id"]]["name"]:
                return self.reply(route, {"error": "name changed"}, 409)
            if req.method == "POST" and body["id"] in self.taken:
                return self.reply(route, {"error": "name taken by another player"}, 409)
            if req.method == "POST":
                self.players[body["id"]]["status"] = body["status"]
                return self.reply(route, self.players[body["id"]])
            return self.reply(route, {"players": [{"id": i, **p} for i, p in self.players.items()]})
        return self.reply(route, {"error": "no such route"}, 404)

    @staticmethod
    def reply(route, body, status=200):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))


@pytest.fixture
def fake(context):
    f = FakeApi()
    context.route("**/api/**", f.handle)
    return f


def win_puhelinkoppi(page):
    page.evaluate("noise = 0; newRound(); launch({ v0: 3 });"
                  "for (let t = 0; t < 3 && state !== 'result'; t += 1 / 60) step(1 / 60);")
    assert page.evaluate("result.kind") == "win"


def test_the_first_score_asks_for_a_name_and_the_list_shows_it_once_approved(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v2/")
    assert page.locator("#ai-pelit-tulokset-nappi").is_visible()
    win_puhelinkoppi(page)
    # Asked once, on this phone's first score.
    page.wait_for_selector("#ai-pelit-nimi")
    page.fill("#ai-pelit-nimi", " Eero ")
    page.click("#ai-pelit-tulokset button:has-text('Tallenna')")
    page.wait_for_selector("#ai-pelit-tulokset :text('odottaa hyväksyntää')")
    page.wait_for_function("Object.keys(JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono') || '{}')).length === 0")
    [(player, name)] = [(i, p["name"]) for i, p in fake.players.items()]
    assert name == "Eero"
    assert fake.scores == {("puhelinkoppi", "main", player): {"score": 2, "version": 2}}
    # Pending: only the player's own row, marked as theirs.
    assert page.locator("#ai-pelit-tulokset").inner_text().count("taso 2") == 1
    page.click("#ai-pelit-tulokset button:has-text('Sulje')")

    # Another win is sent without asking again; once approved the list shows the name with its rank.
    win_puhelinkoppi(page)
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    assert fake.scores[("puhelinkoppi", "main", player)]["score"] == 3
    assert page.locator("#ai-pelit-tulokset").count() == 0
    fake.players[player]["status"] = "approved"
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-tulokset :text('taso 3')")
    text = page.locator("#ai-pelit-tulokset").inner_text()
    assert "odottaa" not in text and "Eero" in text and "taso 3" in text and "v2" in text


def test_scores_wait_on_the_phone_while_offline(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v5/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    fake.online = False
    page.evaluate(PLAY, [6, True])
    page.evaluate(PLAY, [30, False])  # a lower score later does not replace the best one waiting
    queue = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    best_cm = round(page.evaluate("best") / 10)
    assert queue == {"sormiskeitti|main": {"game": "sormiskeitti", "board": "main", "version": 5, "score": best_cm}}
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-tulokset :text('Ei verkkoyhteyttä')")
    assert fake.scores == {}

    fake.online = True
    page.reload()
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    assert [s["score"] for s in fake.scores.values()] == [best_cm]


def test_a_tap_on_the_list_never_reaches_the_game(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v5/")
    st = page.evaluate("st")
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-nimi")
    page.fill("#ai-pelit-nimi", "Pekka ja Space")  # a space is the game's own key for a tap
    page.click("#ai-pelit-tulokset button:has-text('Sulje')")
    assert page.evaluate("st") == st


def test_hiihto_keeps_one_list_per_course(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/hiihto/v2/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    page.evaluate("maxLevel = 3; level = 2; newRace(); AiPelitScores.submit(71.5)")
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    assert [k[:2] for k in fake.scores] == [("hiihto", "taso-2")]
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-tulokset :text('1.11,5')")
    assert "Taso 2" in page.locator("#ai-pelit-tulokset").inner_text()


def test_the_admin_approves_names_and_the_shelf_says_how_many_wait(site, context, fake):
    site.build(ROOT / "games")
    fake.players = {"a" * 32: {"name": "Aino", "status": "pending"}, "b" * 32: {"name": "Bertta", "status": "pending"}}
    page = context.new_page()
    page.goto(f"{site.url}yllapito/")
    page.fill("#key", "väärä")
    page.click("button:has-text('Avaa')")
    page.wait_for_selector("#msg:text('Väärä avain.')")
    page.goto(f"{site.url}yllapito/#avain={ADMIN_KEY}")
    page.wait_for_selector(".player")
    assert "avain" not in page.url
    assert page.locator("#login").is_hidden()
    page.click(".player:has-text('Aino') button:has-text('Hyväksy')")
    page.wait_for_selector(".player[data-status='approved']:has-text('Aino')")
    assert fake.players["a" * 32]["status"] == "approved"

    page.goto(site.url)
    page.wait_for_selector(".waiting-names")
    assert page.locator(".waiting-names").inner_text() == "1 nimimerkki odottaa hyväksyntää"
    page.click(".waiting-names")
    page.wait_for_selector(".player")


def test_the_shelf_shows_no_admin_link_without_the_key(site, context, fake):
    site.build(ROOT / "games")
    fake.players = {"a" * 32: {"name": "Aino", "status": "pending"}}
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    page.wait_for_timeout(300)
    assert page.locator(".waiting-names").count() == 0


def test_the_admin_is_told_when_a_name_is_already_someone_elses(site, context, fake):
    site.build(ROOT / "games")
    fake.players = {"a" * 32: {"name": "Aino", "status": "rejected"}}
    fake.taken = {"a" * 32}
    page = context.new_page()
    page.goto(f"{site.url}yllapito/#avain={ADMIN_KEY}")
    page.click(".player:has-text('Aino') button:has-text('Hyväksy')")
    page.wait_for_selector("#msg:has-text('Nimi on jo toisella pelaajalla')")
    assert fake.players["a" * 32]["status"] == "rejected"


@pytest.mark.parametrize("status, says", [(409, "nimi on jo käytössä"), (429, "ei voitu vielä tallentaa")])
def test_a_refused_name_says_why_instead_of_waiting(site, context, fake, status, says):
    site.build(ROOT / "games")
    fake.refuse = {"Aino": status}
    page = context.new_page()
    page.goto(f"{site.url}games/puhelinkoppi/v2/")
    page.click("#ai-pelit-tulokset-nappi")
    page.fill("#ai-pelit-nimi", "Aino")
    page.click("#ai-pelit-tulokset button:has-text('Tallenna')")
    page.wait_for_selector(f"#ai-pelit-tulokset :text('{says}')")
    assert "odottaa hyväksyntää" not in page.locator("#ai-pelit-tulokset").inner_text()
    # The same on the next opening.
    page.click("#ai-pelit-tulokset button:has-text('Sulje')")
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector(f"#ai-pelit-tulokset :text('{says}')")


def test_the_admin_never_approves_a_name_they_did_not_see(site, context, fake):
    site.build(ROOT / "games")
    fake.players = {"a" * 32: {"name": "Aino", "status": "pending"}}
    page = context.new_page()
    page.goto(f"{site.url}yllapito/#avain={ADMIN_KEY}")
    page.wait_for_selector(".player:has-text('Aino')")
    fake.players["a" * 32]["name"] = "Rumanimi"  # the phone changes name while the page is open
    page.click(".player:has-text('Aino') button:has-text('Hyväksy')")
    page.wait_for_selector("#msg:has-text('Pelaaja vaihtoi nimeään')")
    page.wait_for_selector(".player:has-text('Rumanimi')")
    assert fake.players["a" * 32]["status"] == "pending"


@pytest.mark.parametrize("refusal", [429, 403, 503])
def test_a_score_the_server_turns_away_for_now_is_sent_later(site, context, fake, refusal):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/hiihto/v2/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    fake.score_refusals = [refusal]
    page.evaluate("AiPelitScores.submit(71.5)")
    page.wait_for_timeout(500)
    assert fake.scores == {}
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))['hiihto|taso-1'].score") == 71.5
    page.reload()
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    assert [s["score"] for s in fake.scores.values()] == [71.5]
