"""Feedback on a game's page in the shelf (#184), in a phone-sized Chromium against the stand-in
for /api/ from test_scores.py. Only an approved nickname may write it; the server's own rules are
tested in tests/server/feedback.test.mjs."""

import json

import pytest

from conftest import game_page, make_game
from test_scores import ADMIN_KEY, FakeApi

ME = "a" * 32


class FeedbackApi(FakeApi):
    def __init__(self):
        super().__init__()
        self.feedback = []
        self.feedback_status = None  # an HTTP status POST /api/feedback answers instead

    def handle(self, route):
        req = route.request
        path = req.url.split("/api/", 1)[1].split("?")[0]
        if self.online and path == "feedback" and req.method == "POST":
            body = json.loads(req.post_data)
            if self.feedback_status:
                return self.reply(route, {"error": "refused"}, self.feedback_status)
            if self.players.get(body["player"], {}).get("status") != "approved":
                return self.reply(route, {"error": "approved nickname needed"}, 403)
            self.feedback.append(body)
            return self.reply(route, {"ok": True})
        if self.online and path == "admin/feedback":
            if req.headers.get("x-admin-key") != ADMIN_KEY:
                return self.reply(route, {"error": "admin key needed"}, 403)
            rows = [{"id": i + 1, "name": self.players[f["player"]]["name"], "game": f["game"], "version": f.get("version"),
                     "text": f["text"], "at": "2026-10-31T18:00:00Z", "issue": 190 if i == 0 else None}
                    for i, f in enumerate(self.feedback)]
            return self.reply(route, {"feedback": rows[::-1]})
        return super().handle(route)


@pytest.fixture
def fake(context):
    f = FeedbackApi()
    context.route("**/api/**", f.handle)
    return f


def shelf(site, context, name=None):
    make_game(site.games, "kissa", [game_page("Kissa v1"), game_page("Kissa v2")], title="Kissa")
    site.build()
    page = context.new_page()
    page.goto(site.url)
    if name is not None:
        page.evaluate("([id, name]) => { localStorage.setItem('ai-pelit:_pelaaja:id', JSON.stringify(id));"
                      "localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify(name)); }", [ME, name])
    page.goto(f"{site.url}#/kissa")
    page.click("button:has-text('Anna palautetta')")
    return page


def test_an_approved_player_sends_feedback_on_a_version(site, context, fake):
    fake.players = {ME: {"name": "Aino", "status": "approved"}}
    page = shelf(site, context, "Aino")
    page.wait_for_selector(".feedback-text")
    assert "Nimimerkillä Aino" in page.locator(".feedback").inner_text()
    assert page.locator(".feedback-version").input_value() == "2"
    page.select_option(".feedback-version", "1")
    page.fill(".feedback-text", "Hyppy on liian korkea\nja kissa liian nopea")
    page.click(".feedback button:has-text('Lähetä')")
    page.wait_for_selector(".feedback-note:text('Kiitos, Aino! Palaute meni perille.')")
    assert fake.feedback == [{"player": ME, "game": "kissa", "version": 1, "text": "Hyppy on liian korkea\nja kissa liian nopea"}]
    assert page.locator(".feedback-text").input_value() == ""

    # Too much today, or no network: said plainly, and the text stays to send again.
    fake.feedback_status = 429
    page.fill(".feedback-text", "Vielä yksi")
    page.click(".feedback button:has-text('Lähetä')")
    page.wait_for_selector(".feedback-note:text('Jatka huomenna')")
    fake.online = False
    page.click(".feedback button:has-text('Lähetä')")
    page.wait_for_selector(".feedback-note:text('Ei verkkoyhteyttä')")
    assert page.locator(".feedback-text").input_value() == "Vielä yksi"


def test_a_phone_with_no_name_chooses_one_and_waits_for_the_admin(site, context, fake):
    page = shelf(site, context)
    page.wait_for_selector(".feedback-name")
    assert "hyväksytyllä nimimerkillä" in page.locator(".feedback").inner_text()
    page.fill(".feedback-name", "Bertta")
    page.click(".feedback button:has-text('Tallenna')")
    page.wait_for_selector(".feedback-waiting:text('Bertta odottaa ylläpitäjän hyväksyntää')")
    [(player, p)] = fake.players.items()
    assert p == {"name": "Bertta", "status": "pending"}
    assert page.locator(".feedback-text").count() == 0

    # Once approved, the box opens the form the next time.
    p["status"] = "approved"
    page.reload()
    page.click("button:has-text('Anna palautetta')")
    page.wait_for_selector(".feedback-text")


def test_a_rejected_name_is_asked_again(site, context, fake):
    fake.players = {ME: {"name": "Huono", "status": "rejected"}}
    page = shelf(site, context, "Huono")
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:lahetetty', JSON.stringify('Huono'))")
    page.reload()
    page.click("button:has-text('Anna palautetta')")
    page.wait_for_selector(".feedback:has-text('Nimimerkkiä Huono ei hyväksytty. Valitse toinen.')")
    assert page.locator(".feedback-name").input_value() == ""


def test_the_admin_page_lists_the_feedback(site, context, fake):
    fake.players = {ME: {"name": "Aino", "status": "approved"}}
    fake.feedback = [{"player": ME, "game": "kissa", "version": 2, "text": "Eka"},
                     {"player": ME, "game": "kissa", "version": 1, "text": "Toka\nrivi"}]
    shelf(site, context)
    page = context.new_page()
    page.goto(f"{site.url}yllapito/#avain={ADMIN_KEY}")
    page.wait_for_selector(".palaute")
    rows = page.locator(".palaute").all_inner_texts()
    assert rows[0].startswith("Kissa v1 · Aino") and "uusi" in rows[0] and rows[0].endswith("Toka\nrivi")
    assert "#190" in rows[1]


def test_a_double_tap_sends_once_and_the_box_fits_a_390px_phone(site, context, fake):
    fake.players = {ME: {"name": "Aino", "status": "approved"}}
    page = shelf(site, context, "Aino")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_selector(".feedback-text")
    page.fill(".feedback-text", "Kaksi kertaa")
    page.locator(".feedback button:has-text('Lähetä')").dispatch_event("click")
    page.locator(".feedback button:has-text('Lähetä')").dispatch_event("click")
    page.wait_for_selector(".feedback-note:text('Kiitos')")
    page.wait_for_timeout(200)
    assert len(fake.feedback) == 1
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    box = page.locator(".feedback-box").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
