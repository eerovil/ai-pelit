"""Every game's public rooms on the shelf's front page (#203)."""

import json

from conftest import game_page, make_game


def answer_rooms(context, rooms):
    context.route("**/api/rooms", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"rooms": rooms})))


def test_the_shelf_lists_open_rooms_and_a_tap_joins_in_the_rooms_version(site, context):
    make_game(site.games, "pallo", [game_page("v1"), game_page("v2")], title="Pallo")
    make_game(site.games, "hyppy", [game_page("v1")], title="Hyppy", group="yleisurheilu")
    site.build()
    answer_rooms(context, [
        {"code": "KISA", "game": "hyppy", "v": 1, "n": 2, "max": 8},
        {"code": "PELI", "game": "pallo", "v": 1, "n": 1, "max": 5},
        {"code": "VANH", "game": "pallo", "v": 4, "n": 1, "max": 5},  # a version the shelf lacks
        {"code": "MUUT", "game": "eiole", "v": 1, "n": 1, "max": 5},  # a game the shelf lacks
    ])
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".open-rooms:not([hidden]) .room")
    assert page.locator(".open-rooms h2").text_content() == "Avoimet huoneet"
    assert [page.locator(".room").nth(i).get_attribute("data-code") for i in range(page.locator(".room").count())] \
        == ["KISA", "PELI"]
    assert "Pallo" in page.locator('.room[data-code="PELI"]').text_content()
    assert "1/5 pelaajaa" in page.locator('.room[data-code="PELI"]').text_content()
    assert page.evaluate("document.documentElement.scrollWidth") <= 360
    # A tap opens the room's own version with its code; back goes to the game's page, then the shelf.
    page.click('.room[data-code="PELI"] a')
    page.wait_for_url("**/games/pallo/v1/?huone=PELI")
    page.go_back()
    page.wait_for_url(f"{site.url}#/pallo")
    page.go_back()
    page.wait_for_url(site.url)


def test_no_open_rooms_or_no_connection_shows_nothing(site, context):
    make_game(site.games, "pallo", [game_page("v1")])
    site.build()
    answer_rooms(context, [])
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    page.wait_for_timeout(300)
    assert page.locator(".open-rooms").is_hidden()
    context.unroute("**/api/rooms")
    context.route("**/api/rooms", lambda route: route.abort())
    page.reload()
    page.wait_for_selector(".card")
    page.wait_for_timeout(300)
    assert page.locator(".open-rooms").is_hidden()
