"""Playing right now (#325): an open game page tells the server it is still there (back.js), and
the shelf shows how many have each game open now, only the number. The real /api/playing is
server/api.js, tested in tests/server/; here a stand-in answers it."""

import json

from conftest import game_page, make_game


class FakePlaying:
    def __init__(self):
        self.online = True
        self.sent = []
        self.now = {}

    def handle(self, route):
        if not self.online:
            return route.abort()
        req = route.request
        if req.url.endswith("/api/playing") and req.method == "POST":
            self.sent.append(json.loads(req.post_data))
            return route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
        if req.url.split("?")[0].endswith("/api/playing"):
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"games": self.now}))
        if req.url.split("?")[0].endswith("/api/plays") and req.method == "GET":
            return route.fulfill(status=200, content_type="application/json", body='{"games": {"pomppu": 12}}')
        return route.fulfill(status=200, content_type="application/json", body='{"ok": true}')


def playing_on(context):
    fake = FakePlaying()
    context.route("**/api/**", fake.handle)
    return fake


def test_an_open_game_says_it_is_there_and_that_it_left(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    fake = playing_on(context)
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    # Leaving the page (the real unload's beacon never reaches Playwright's routes).
    page.evaluate("dispatchEvent(new PageTransitionEvent('pagehide'))")
    page.wait_for_function("() => true")
    page.wait_for_timeout(300)
    here = [m for m in fake.sent if not m.get("gone")]
    gone = [m for m in fake.sent if m.get("gone")]
    assert here and here[0]["game"] == "pomppu"
    assert gone and gone[0]["id"] == here[0]["id"]
    assert set(gone[0]) == {"id", "gone"}


def test_a_game_inside_another_games_frame_is_not_counted_apart(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    make_game(site.games, "kehys", [game_page("v1", body='<iframe src="../../pomppu/v1/"></iframe>')])
    site.build()
    fake = playing_on(context)
    page = context.new_page()
    page.goto(f"{site.url}games/kehys/v1/")
    page.frame_locator("iframe").locator("#ai-pelit-back").wait_for()
    page.wait_for_timeout(200)
    assert {m["game"] for m in fake.sent if not m.get("gone")} == {"kehys"}


def test_the_shelf_shows_how_many_play_now_and_nothing_offline(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    fake = playing_on(context)
    fake.now = {"pomppu": 2}
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector('.card[data-slug="pomppu"] .now:text("● 2")')
    assert page.locator('.card[data-slug="pomppu"] .now').get_attribute("aria-label") == "2 pelaa nyt"
    # A game nobody plays now shows nothing.
    assert page.locator('.card[data-slug="hyppy"] .now').inner_text() == ""
    # The game's own page shows it too.
    page.goto(f"{site.url}#/pomppu")
    page.wait_for_selector('.game-head .now:text("● 2")')

    # Offline an old number would be wrong: none shows.
    fake.online = False
    page.goto(site.url)
    page.reload()
    page.wait_for_selector(".card")
    page.wait_for_timeout(300)
    assert page.locator('.card[data-slug="pomppu"] .now').inner_text() == ""


def test_a_group_card_adds_up_its_games(site, context):
    make_game(site.games, "keihas", [game_page("v1")], group="yleisurheilu")
    make_game(site.games, "kuula", [game_page("v1")], group="yleisurheilu")
    site.build()
    fake = playing_on(context)
    fake.now = {"keihas": 1, "kuula": 3}
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector('.card[data-slug="yleisurheilu"] .now:text("● 4")')
