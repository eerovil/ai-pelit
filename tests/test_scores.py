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
        self.hold = False  # True: POST /api/scores waits in self.held until the test lets it go
        self.held = []
        self.hold_lists = False  # True: GET /api/scores waits in self.held too

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
        if path == "scores" and req.method == "POST" and self.hold:
            self.held.append(route)
            return None
        if path == "scores" and req.method == "POST" and self.score_refusals:
            return self.reply(route, {"error": "refused"}, self.score_refusals.pop(0))
        if path == "scores" and req.method == "POST":
            if body["player"] not in self.players:
                return self.reply(route, {"error": "unknown player"}, 404)
            k = (body["game"], body["board"], body["player"])
            old = self.scores.get(k)
            old_level = (old or {}).get("level")
            # Like the server: the best score stays (lower is better in Hiihto).
            beats = not old or (body["score"] < old["score"] if body["game"] == "hiihto" else body["score"] > old["score"])
            self.scores[k] = {"score": body["score"], "version": body["version"]} if beats else {"score": old["score"], "version": old["version"]}
            if body.get("level") or old_level:
                self.scores[k]["level"] = max(body.get("level") or 0, old_level or 0)
            return self.reply(route, {"best": body["score"], "rank": 1})
        if path == "scores/top":
            games = {}
            for (game, board, player), sc in self.scores.items():
                first = "taso-1" if game == "hiihto" else "main"
                if board != first or self.players[player]["status"] != "approved":
                    continue
                low = game == "hiihto"
                cur = games.get(game)
                if not cur or (sc["score"] < cur["score"] if low else sc["score"] > cur["score"]):
                    games[game] = {"board": board, "name": self.players[player]["name"], "level": sc.get("level"), **sc}
            return self.reply(route, {"games": games})
        if path == "scores" and self.hold_lists:
            self.held.append(route)
            return None
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



def test_the_level_comes_from_the_game_s_own_save_with_no_new_version(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v5/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    fake.online = False
    won = page.evaluate(PLAY, [6, True])
    lost = page.evaluate(PLAY, [30, False])  # a lower ollie on level 2
    assert won["won"] and not lost["won"]
    fake.online = True
    page.reload()
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    [(key, row)] = fake.scores.items()
    assert row == {"score": round(won["best"] / 10), "version": 5, "level": 2}
    fake.players[key[2]]["status"] = "approved"
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-tulokset .tulos:has-text('taso 2')")

    # A round that beats neither the score nor the level is not sent at all.
    sent = len(fake.posts)
    page.click("#ai-pelit-tulokset button:has-text('Sulje')")
    page.evaluate(PLAY, [30, False])
    page.wait_for_timeout(500)
    assert len(fake.posts) == sent
    # A higher level is sent, even with a lower ollie.
    page.evaluate("localStorage.setItem('ai-pelit:sormiskeitti:level', '4'); level = 4")
    page.evaluate(PLAY, [30, False])
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    assert len(fake.posts) == sent + 1
    assert fake.scores[key] == {"score": round(won["best"] / 10), "version": 5, "level": 4}


def test_hiihto_sends_courses_passed(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/hiihto/v2/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    # Passing the first course: v2 sends before it saves the next level, and the level is read
    # only when sending, so it still counts.
    page.evaluate("level = maxLevel = 1; newRace(); P.t = 60; finish()")
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    [(key, row)] = fake.scores.items()
    assert key[:2] == ("hiihto", "taso-1") and row["level"] == 1
    fake.players[key[2]]["status"] = "approved"
    page.click("#ai-pelit-tulokset-nappi")
    page.wait_for_selector("#ai-pelit-tulokset .tulos:has-text('1 rata läpi')")
    assert "1.00,0" in page.locator("#ai-pelit-tulokset").inner_text()


def test_the_shelf_shows_each_game_s_no_1_and_its_lists(site, context, fake):
    site.build(ROOT / "games")
    a, b = "a" * 32, "b" * 32
    fake.players = {a: {"name": "Aino", "status": "approved"}, b: {"name": "Bertta", "status": "approved"}}
    fake.scores = {
        ("sormiskeitti", "main", a): {"score": 64, "version": 5, "level": 7},
        ("sormiskeitti", "main", b): {"score": 58, "version": 5},
        ("hiihto", "taso-1", a): {"score": 71.5, "version": 2, "level": 3},
        ("hiihto", "taso-2", b): {"score": 95, "version": 2, "level": 2},
    }
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector('.top-score[data-top="sormiskeitti"]:has-text("Aino")')
    assert page.locator('.top-score[data-top="sormiskeitti"]').inner_text() == "🏆 Aino · 64 cm"
    assert page.locator('.top-score[data-top="hiihto"]').inner_text() == "🏆 Taso 1: Aino · 1.11,5"
    assert page.locator('.top-score[data-top="voimistelu"]').is_hidden()
    assert page.locator("#ai-pelit-tulokset-nappi").count() == 0  # no chip on the shelf

    page.click('.card[data-slug="sormiskeitti"] .card-main')
    page.wait_for_selector(".score-list .tulos")
    rows = page.locator(".score-list .tulos").all_inner_texts()
    assert [" ".join(r.split()) for r in rows] == ["1. Aino 64 cm taso 7 v5", "2. Bertta 58 cm v5"]

    page.goto(site.url + "#/hiihto")
    page.wait_for_selector(".score-list .tulos:has-text('Aino')")
    page.click(".score-list .board-next")
    page.wait_for_selector(".score-list .tulos:has-text('Bertta')")
    assert "2 rataa läpi" in page.locator(".score-list").inner_text()
    # A phone that has never played Hiihto can still look at any course.
    fake.scores[("hiihto", "taso-11", a)] = {"score": 300, "version": 2, "level": 11}
    page.fill(".score-list .board", "11")
    page.dispatch_event(".score-list .board", "change")
    page.wait_for_selector(".score-list .tulos:has-text('11 rataa läpi')")

    # Offline the cards keep the last no. 1 they saw.
    fake.online = False
    page.goto(site.url)
    page.wait_for_selector('.top-score[data-top="sormiskeitti"]:has-text("Aino")')


def test_a_won_level_is_sent_even_when_the_ollie_is_no_record(site, context, fake):
    """Sormiskeitti v5 hands over its score before it saves the next level: the level is read when sending."""
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v5/")
    page.evaluate("""localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'));
        localStorage.setItem('ai-pelit:_tulokset:lahetetyt', JSON.stringify({'sormiskeitti|main': {score: 999, level: 1}}))""")
    page.reload()
    won = page.evaluate(PLAY, [6, True])
    assert won["won"] and round(won["best"] / 10) < 999
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    [row] = fake.scores.values()
    assert row["level"] == 2
    page.goto(site.url)  # the player leaves the game: nothing more to send
    assert page.evaluate("localStorage.getItem('ai-pelit:_tulokset:jono')") == "{}"


def test_a_level_won_while_a_score_is_on_its_way_is_sent_too(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v5/")
    page.evaluate("""localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'));
        localStorage.setItem('ai-pelit:_tulokset:lahetetyt', JSON.stringify({'sormiskeitti|main': {score: 999, level: 1}}))""")
    page.reload()
    win = "lv => { level = lv; maxH = 300; st = 'air'; finish(true); }"  # a won level, no record ollie
    fake.hold = True
    page.evaluate(win, 1)  # level 2 reached: its send is held on the way
    page.wait_for_timeout(300)
    assert len(fake.held) == 1 and json.loads(fake.held[0].request.post_data)["level"] == 2
    page.evaluate(win, 2)  # level 3 reached while level 2 is still on its way
    page.wait_for_timeout(300)
    fake.hold = False
    fake.handle(fake.held.pop())  # the server takes level 2 ...
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    page.wait_for_timeout(300)
    [row] = fake.scores.values()
    assert row["level"] == 3  # ... and level 3 follows by itself
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:lahetetyt'))['sormiskeitti|main'].level") == 3


def test_a_slow_answer_for_an_earlier_course_never_shows_under_a_later_one(site, context, fake):
    site.build(ROOT / "games")
    a, b = "a" * 32, "b" * 32
    fake.players = {a: {"name": "Aino", "status": "approved"}, b: {"name": "Bertta", "status": "approved"}}
    fake.scores = {("hiihto", "taso-1", a): {"score": 71.5, "version": 2}, ("hiihto", "taso-2", b): {"score": 95, "version": 2}}
    page = context.new_page()
    page.goto(site.url + "#/hiihto")
    page.wait_for_selector(".score-list .tulos:has-text('Aino')")
    fake.hold_lists = True
    page.click(".score-list .board-prev")  # course 1 again: its answer is held
    page.click(".score-list .board-next")  # course 2: also held
    page.wait_for_timeout(300)
    assert len(fake.held) == 2
    fake.hold_lists = False
    second = fake.held.pop()
    fake.handle(second)  # course 2 answers first ...
    page.wait_for_selector(".score-list .tulos:has-text('Bertta')")
    fake.handle(fake.held.pop())  # ... then the slow course 1 answer
    page.wait_for_timeout(300)
    assert page.locator(".score-list .board").input_value() == "2"
    assert "Bertta" in page.locator(".score-list").inner_text()
    assert "Aino" not in page.locator(".score-list").inner_text()


def test_piano_sends_its_level_even_from_a_first_game_on_level_1(site, context, fake):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/piano/v1/")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    page.click("#go")
    page.evaluate("score = 300; lives = 1; miss(0, 'Ohi!')")
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    [(key, row)] = fake.scores.items()
    assert key[:2] == ("piano", "main")
    assert row == {"score": 300, "version": 1, "level": 1}
