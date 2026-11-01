"""Every game's public rooms on the shelf's front page (#203)."""

import json

import pytest

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


def test_the_list_updates_while_the_shelf_shows_and_after_a_round_trip(site, context):
    make_game(site.games, "pallo", [game_page("v1")], title="Pallo")
    site.build()
    rooms = [{"code": "PELI", "game": "pallo", "v": 1, "n": 1, "max": 5}]
    reads = []

    def answer(route):
        reads.append(1)
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"rooms": rooms}))
    context.route("**/api/rooms", answer)
    page = context.new_page()
    page.clock.install()
    page.goto(site.url)
    page.wait_for_selector('.room[data-code="PELI"]')
    # Another phone's room opens, and this one fills up: the next read, 10 s later, shows it.
    rooms[:] = [{"code": "UUSI", "game": "pallo", "v": 1, "n": 2, "max": 5}]
    page.clock.run_for(10_500)
    page.wait_for_selector('.room[data-code="UUSI"]')
    assert page.locator(".room").count() == 1
    # Away on a game's page the list is not read; back on the shelf it is read again at once,
    # and only one refresh keeps going (no second timer from the earlier shelf).
    page.click('.card[data-slug="pallo"] .card-main')
    page.wait_for_url(f"{site.url}#/pallo")
    before = len(reads)
    page.clock.run_for(30_000)
    assert len(reads) == before
    rooms[:] = []
    page.go_back()
    page.wait_for_url(site.url)
    page.wait_for_function("document.querySelector('.open-rooms').hidden")
    after = len(reads)
    page.clock.run_for(10_500)
    page.wait_for_timeout(200)
    assert len(reads) == after + 1


@pytest.mark.parametrize("width", [360, 390])
def test_a_long_game_name_in_the_list_fits_the_phone(site, context, width):
    make_game(site.games, "pitka", [game_page("v1")], title="Hyvin pitkä pelin nimi joka jatkuu ja jatkuu vielä")
    site.build()
    answer_rooms(context, [{"code": "PITK", "game": "pitka", "v": 1, "n": 7, "max": 8}])
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": 740})
    page.goto(site.url)
    page.wait_for_selector(".room")
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    box = page.locator(".room a").bounding_box()
    assert box["x"] + box["width"] <= width
