"""Ottelu v3: alone, each next event starts in a freshly loaded page (#168).

On Eero's phone the second event's frame in the same page took no taps at all, every time; the
same event after a reload played. v3 reloads the page for each next event when playing alone.
"""

import pytest
from conftest import ROOT

import test_ottelu as v1
from test_ottelu import HELPERS
# Rooms still change events in place: v1's room tests run on v3.
from test_ottelu import (  # noqa: F401
    test_an_away_phone_is_played_for_in_this_event_and_the_next, test_points_follow_the_combined_event_tables,
    test_the_menu_and_the_board_fit, test_two_phones_play_a_match_and_see_the_same_points)

URL = "games/ottelu/v3/"


@pytest.fixture(autouse=True)
def v3(monkeypatch):
    monkeypatch.setattr(v1, "URL", URL)


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    # The helpers again in every page load, as the match reloads between events.
    page.add_init_script("addEventListener('DOMContentLoaded', () => { if (window.top === window) (" + HELPERS + ")(); })")
    page.goto(site.url + URL)
    return page


def finish_event(page):
    for _ in range(1500):
        page.evaluate("play()")
        if page.evaluate("frameAt === -1 && !document.getElementById('board').classList.contains('hidden')"):
            return
        page.wait_for_timeout(20)
    raise AssertionError("the event did not end")


def test_alone_each_next_event_starts_in_a_new_page(site, context):
    page = open_game(site, context)
    page.evaluate("picked.splice(0); ['keihas', 'moukari', 'pituushyppy'].forEach(s => picked.push(s)); drawPick()")
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    page.evaluate("window.samePage = true")
    finish_event(page)
    assert page.inner_text("#bTitle") == "Keihäänheitto · laji 1/3"
    with page.expect_navigation():
        page.click("#next")
    # A new page: the match from storage, the hammer from its start, the menu not in the way.
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    assert page.evaluate("window.samePage === undefined && document.getElementById('menu').classList.contains('hidden')")
    assert page.evaluate("[M.events.join(), M.rows.find(r => r.p === 'me').pts.join(), Ottelu.K.comp.seq <= 8]") == ["keihas,moukari,pituushyppy", "738", True]
    assert page.evaluate("sessionStorage.getItem('ai-pelit:ottelu:seuraava')") is None
    finish_event(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 2", timeout=10000)
    finish_event(page)
    assert page.inner_text("#bTitle") == "Lopputulokset"
    assert page.evaluate("M.rows.find(r => r.p === 'me').pts.length") == 3
    assert page.errors == []


def test_a_plain_reload_still_shows_the_menu_with_the_match_to_go_on(site, context):
    page = open_game(site, context)
    page.evaluate("picked.splice(0); ['keihas', 'moukari'].forEach(s => picked.push(s)); drawPick()")
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    page.reload()
    # Only the "next event" tap starts an event by itself; a reload shows the menu.
    assert page.is_visible("#menu") and page.inner_text("#cont") == "Jatka ottelua (laji 2/2)"
    page.click("#cont")
    assert page.inner_text("#bTitle") == "Keihäänheitto · laji 1/2"
    assert page.errors == []
