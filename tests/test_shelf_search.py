"""The shelf once there are many games (#523): one short row per game, athletics events too, a
search box, buttons (Kaikki, Uudet, Päivitetyt, then the categories) and the phone's recently
played games on top. Kaikki and the categories list the most played first (#279's default); the
old sort menu is gone."""

import json

import pytest

from conftest import game_page, make_game, wait_for_worker


def rows(page):
    return page.eval_on_selector_all(".shelf-rows > .shelf-row", "cs => cs.map(c => c.dataset.slug)")


def shelf(site, context, totals):
    # Orava came first but has the newest version: Uudet and Päivitetyt part there.
    make_game(site.games, "orava", [game_page("v1"), game_page("v2")], dates=["2026-01-01", "2026-06-01"],
              title="Orava", category="seikkailu")
    make_game(site.games, "aita", [game_page("v1")], dates=["2026-02-01"], group="yleisurheilu", title="Aita")
    make_game(site.games, "keihas", [game_page("v1")], dates=["2026-03-01"], group="yleisurheilu", title="Keihäs")
    make_game(site.games, "ankka", [game_page("v1")], dates=["2026-04-01"], title="Ankka", category="pallo")
    make_game(site.games, "zorro", [game_page("v1")], dates=["2026-05-01"], title="Zorro", category="vauhti")
    site.build()

    def api(route):
        body = {"games": totals} if route.request.url.split("?")[0].endswith("/api/plays") else {}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
    context.route("**/api/**", api)
    page = context.new_page()
    page.goto(site.url)
    page.wait_for_selector(".shelf-row")
    return page


def press(page, cat):
    page.click(f'.shelf-button[data-cat="{cat}"]')
    assert page.locator(f'.shelf-button[data-cat="{cat}"]').get_attribute("aria-pressed") == "true"


def test_each_button_lists_its_games_in_its_own_order(site, context):
    page = shelf(site, context, {"orava": 20, "aita": 30, "keihas": 5, "ankka": 1})
    page.wait_for_selector('.shelf-row[data-slug="orava"] .plays:text("pelattu 20 kertaa")')
    # No sort menu any more: the buttons are the orders.
    assert page.locator(".top select").count() == 0
    assert page.eval_on_selector_all(".shelf-button", "bs => bs.map(b => b.textContent)") == [
        "Kaikki", "Uudet", "Päivitetyt", "Yleisurheilu", "Pallo ja maali", "Vauhti", "Seikkailu"]
    # Kaikki: every game its own row, most played first; unplayed ones newest version first.
    assert page.locator('.shelf-button[data-cat=""]').get_attribute("aria-pressed") == "true"
    assert rows(page) == ["aita", "orava", "keihas", "ankka", "zorro"]
    press(page, "uudet")
    assert rows(page) == ["zorro", "ankka", "keihas", "aita", "orava"]
    press(page, "paivitetyt")
    assert rows(page) == ["orava", "zorro", "ankka", "keihas", "aita"]
    press(page, "yleisurheilu")
    assert rows(page) == ["aita", "keihas"]
    press(page, "")
    assert len(rows(page)) == 5
    # A row is short: the name, version, plays and ▶, no description.
    assert [t for t in page.locator('.shelf-row[data-slug="orava"]').inner_text().split("\n") if t.strip()] == [
        "Orava", "v2 · pelattu 20 kertaa", "▶"]
    assert page.get_attribute('.shelf-row[data-slug="orava"] a.play', "href") == "games/orava/v2/"


def test_new_counts_reorder_kaikki_but_not_paivitetyt(site, context):
    totals = {}
    page = shelf(site, context, totals)
    assert rows(page) == ["orava", "zorro", "ankka", "keihas", "aita"]
    totals["aita"] = 9
    page.reload()
    page.wait_for_function("document.querySelector('.shelf-rows > .shelf-row')?.dataset.slug === 'aita'")
    press(page, "paivitetyt")
    totals["zorro"] = 50
    page.reload()
    page.wait_for_selector('.shelf-row[data-slug="zorro"] .plays:text("pelattu 50 kertaa")')
    assert rows(page) == ["orava", "zorro", "ankka", "keihas", "aita"]


def test_search_finds_names_and_descriptions_and_lasts_until_the_app_closes(site, context):
    page = shelf(site, context, {})
    page.fill(".shelf-search", "ORA")
    assert rows(page) == ["orava"]
    # The description too ("Peli keihas"), ignoring case.
    page.fill(".shelf-search", "peli KEI")
    assert rows(page) == ["keihas"]
    page.fill(".shelf-search", "xyz")
    assert rows(page) == []
    assert page.locator(".no-hits").inner_text() == "Ei osumia."
    page.fill(".shelf-search", "")
    assert len(rows(page)) == 5
    # A search inside a button.
    press(page, "yleisurheilu")
    page.fill(".shelf-search", "kei")
    assert rows(page) == ["keihas"]
    # To a game's page and back: the same list.
    page.click('.shelf-row[data-slug="keihas"] .shelf-row-main')
    page.wait_for_selector(".version")
    page.click("a.back")
    page.wait_for_selector(".shelf-search")
    assert page.input_value(".shelf-search") == "kei"
    assert page.locator('.shelf-button[data-cat="yleisurheilu"]').get_attribute("aria-pressed") == "true"
    assert rows(page) == ["keihas"]
    # A new start shows everything.
    fresh = context.new_page()
    fresh.goto(site.url)
    fresh.wait_for_selector(".shelf-row")
    assert fresh.input_value(".shelf-search") == ""
    assert len(rows(fresh)) == 5


def test_recently_played_shows_the_games_this_phone_opened(site, context):
    page = shelf(site, context, {})
    # A fresh phone has none: no row at all.
    assert page.locator(".recent-games").count() == 0
    for slug, n in (("aita", 1), ("orava", 2), ("aita", 1)):
        page.goto(f"{site.url}games/{slug}/v{n}/")
        page.wait_for_selector("#ai-pelit-back")
    page.goto(site.url)
    page.wait_for_selector(".recent-games")
    assert page.eval_on_selector_all(".recent", "ts => ts.map(t => t.dataset.slug)") == ["aita", "orava"]
    assert page.locator(".recent-games h2").inner_text() == "Viimeksi pelatut"
    # A tap plays the game, and the chip goes back to the game's page, then the shelf.
    page.click('.recent[data-slug="orava"]')
    page.wait_for_url("**/games/orava/v2/")
    page.click("#ai-pelit-back")
    page.click("#ai-pelit-takaisin")
    page.wait_for_url(f"{site.url}#/orava")
    page.click("a.back")
    page.wait_for_selector(".recent-games")
    assert page.eval_on_selector_all(".recent", "ts => ts.map(t => t.dataset.slug)") == ["orava", "aita"]


def test_recently_played_keeps_eight_and_skips_a_game_no_longer_listed(site, context):
    page = shelf(site, context, {})
    many = ["poistettu"] + [f"peli{i}" for i in range(10)] + ["zorro"]
    page.evaluate("s => localStorage.setItem('ai-pelit:_hylly:viimeksi', JSON.stringify(s))", many)
    page.reload()
    page.wait_for_selector(".recent-games")
    assert page.eval_on_selector_all(".recent", "ts => ts.map(t => t.dataset.slug)") == ["zorro"]
    for slug in ("orava", "aita", "keihas", "ankka", "zorro"):
        page.goto(f"{site.url}games/{slug}/v{2 if slug == 'orava' else 1}/")
        page.wait_for_selector("#ai-pelit-back")
    saved = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_hylly:viimeksi'))")
    assert saved[:5] == ["zorro", "ankka", "keihas", "aita", "orava"] and len(saved) == 8


def test_the_shelf_searches_offline(site, context):
    page = shelf(site, context, {})
    wait_for_worker(page)
    page.goto(f"{site.url}games/zorro/v1/")
    page.wait_for_selector("#ai-pelit-back")
    context.set_offline(True)
    try:
        page.goto(site.url)
        page.wait_for_selector(".recent-games")
        page.fill(".shelf-search", "zor")
        assert rows(page) == ["zorro"]
        press(page, "uudet")
        assert rows(page) == ["zorro"]
    finally:
        context.set_offline(False)


@pytest.mark.parametrize("width,height", [(360, 640), (360, 740), (740, 360)])
def test_the_search_and_buttons_fit_a_phone(site, context, width, height):
    page = shelf(site, context, {})
    page.goto(f"{site.url}games/zorro/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.set_viewport_size({"width": width, "height": height})
    page.goto(site.url)
    page.wait_for_selector(".recent-games")
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    for sel in (".shelf-search", ".shelf-buttons", ".shelf-row"):
        box = page.locator(sel).first.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width, sel
    # The buttons scroll sideways in their own row; the last one is reachable.
    press(page, "seikkailu")
    assert rows(page) == ["orava"]
