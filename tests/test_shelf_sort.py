"""The shelf's order (#279): Suosituimmat (most played, the default), Päivitetyt (newest version
first, the catalog's order) or A–Ö, picked in the header and kept on the phone."""

import json

import pytest

from conftest import game_page, make_game


def cards(page):
    return page.eval_on_selector_all(".cards > .card", "cs => cs.map(c => c.dataset.slug)")


def shelf(site, context, totals):
    make_game(site.games, "orava", [game_page("v1")], dates=["2026-01-01"], title="Orava")
    make_game(site.games, "aita", [game_page("v1")], dates=["2026-02-01"], group="yleisurheilu", title="Aita")
    make_game(site.games, "keihas", [game_page("v1")], dates=["2026-03-01"], group="yleisurheilu", title="Keihäs")
    make_game(site.games, "ankka", [game_page("v1")], dates=["2026-04-01"], title="Ankka")
    make_game(site.games, "zorro", [game_page("v1")], dates=["2026-05-01"], title="Zorro")
    site.build()

    def api(route):
        body = {"games": totals} if route.request.url.split("?")[0].endswith("/api/plays") else {}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
    context.route("**/api/**", api)
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".card")
    return page


def test_most_played_first_by_default_then_updated_and_by_name(site, context):
    # The group's card counts its games together: 30 + 5 beats Orava's 20.
    page = shelf(site, context, {"orava": 20, "aita": 30, "keihas": 5, "ankka": 1})
    page.wait_for_selector('.card[data-slug="orava"] .plays:text("pelattu 20 kertaa")')
    assert page.locator(".top select.sort").input_value() == "suosituimmat"
    assert cards(page) == ["yleisurheilu", "orava", "ankka", "zorro"]
    # The group's page follows the same order.
    page.click('.card[data-slug="yleisurheilu"] .card-main')
    page.wait_for_selector('.card[data-slug="keihas"]')
    assert page.eval_on_selector_all(".card", "cs => cs.map(c => c.dataset.slug)") == ["aita", "keihas"]
    assert page.locator(".top select.sort").count() == 0
    page.click("a.back")
    page.wait_for_selector('.card[data-slug="zorro"]')

    page.select_option(".top select.sort", "paivitetyt")
    assert cards(page) == ["zorro", "ankka", "yleisurheilu", "orava"]
    page.select_option(".top select.sort", "a-o")
    assert cards(page) == ["ankka", "orava", "yleisurheilu", "zorro"]
    # Each card still shows its count and plays as before.
    assert page.locator('.card[data-slug="orava"] .plays').inner_text() == " · pelattu 20 kertaa"

    # The choice is kept on the phone.
    page.reload()
    page.wait_for_selector(".card")
    assert page.locator(".top select.sort").input_value() == "a-o"
    assert cards(page) == ["ankka", "orava", "yleisurheilu", "zorro"]


def test_the_most_played_order_follows_new_counts(site, context):
    totals = {}
    page = shelf(site, context, totals)
    # No counts yet: newest first, as before.
    assert cards(page) == ["zorro", "ankka", "yleisurheilu", "orava"]
    totals["orava"] = 9
    page.reload()
    page.wait_for_function("document.querySelector('.cards > .card')?.dataset.slug === 'orava'")
    assert cards(page) == ["orava", "zorro", "ankka", "yleisurheilu"]


def test_new_counts_leave_another_chosen_order_alone(site, context):
    # Counts arriving after the player picked A–Ö (or Päivitetyt) must not reorder the cards.
    totals = {}
    page = shelf(site, context, totals)
    page.select_option(".top select.sort", "a-o")
    totals.update({"zorro": 50, "orava": 9})
    page.reload()
    page.wait_for_selector('.card[data-slug="zorro"] .plays:text("pelattu 50 kertaa")')
    assert cards(page) == ["ankka", "orava", "yleisurheilu", "zorro"]
    # A game's page shows no menu; back on the shelf it is there with the same choice.
    page.click('.card[data-slug="orava"] .card-main')
    page.wait_for_selector(".version")
    assert page.locator(".top select.sort").count() == 0
    page.go_back()
    page.wait_for_selector(".top select.sort")
    assert page.locator(".top select.sort").input_value() == "a-o"


@pytest.mark.parametrize("width,height", [(360, 740), (390, 844), (740, 360)])
def test_the_menu_fits_the_header_on_a_phone(site, context, width, height):
    page = shelf(site, context, {})
    page.set_viewport_size({"width": width, "height": height})
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    box = page.locator(".top select.sort").bounding_box()
    brand = page.locator(".top .brand").bounding_box()
    assert box["x"] > brand["x"] + brand["width"] and box["x"] + box["width"] <= width
    # On the brand's line, so the shelf is no taller.
    assert box["y"] < brand["y"] + brand["height"]
