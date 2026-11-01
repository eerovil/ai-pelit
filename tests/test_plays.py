"""Play counts (#26): back.js counts each opened version, and the shelf shows each game's total.
The real /api/plays is server/api.js, tested in tests/server/; here a stand-in answers it."""

import json

from conftest import game_page, make_game


class FakePlays:
    def __init__(self):
        self.online = True
        self.sent = []
        self.totals = {}

    def handle(self, route):
        if not self.online:
            return route.abort()
        req = route.request
        if req.url.endswith("/api/plays") and req.method == "POST":
            self.sent.append(json.loads(req.post_data))
            return route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
        if req.url.split("?")[0].endswith("/api/plays"):
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"games": self.totals}))
        return route.fulfill(status=404, content_type="application/json", body='{"error": "no such route"}')


def plays_on(context):
    fake = FakePlays()
    context.route("**/api/**", fake.handle)
    return fake


def test_opening_a_version_counts_one_play(site, context):
    # Only each game's newest version is on the site (#346).
    make_game(site.games, "pomppu", [game_page("v1"), game_page("v2")])
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    fake = plays_on(context)
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v2/")
    page.wait_for_selector("#ai-pelit-back")
    page.goto(f"{site.url}games/hyppy/v1/index.html")
    page.wait_for_selector("#ai-pelit-back")
    page.goto(site.url)  # leaving the page must not lose the beacon
    page.wait_for_selector(".card")
    assert fake.sent == [{"game": "pomppu", "version": 2}, {"game": "hyppy", "version": 1}]


def test_the_shelf_shows_each_games_total_and_keeps_it_offline(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    fake = plays_on(context)
    fake.totals = {"pomppu": 412, "vanha": 3}
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector('.card[data-slug="pomppu"] .plays:text("pelattu 412 kertaa")')
    # A game nobody has opened yet shows no count.
    assert page.locator('.card[data-slug="hyppy"] .plays').inner_text() == ""

    fake.totals = {"pomppu": 1, "hyppy": 2}
    page.reload()
    page.wait_for_selector('.card[data-slug="pomppu"] .plays:text("pelattu 1 kerran")')
    assert page.locator('.card[data-slug="hyppy"] .plays').inner_text() == " · pelattu 2 kertaa"

    # Without the network the last totals still show.
    fake.online = False
    page.reload()
    page.wait_for_selector(".card")
    assert page.locator('.card[data-slug="hyppy"] .plays').inner_text() == " · pelattu 2 kertaa"
