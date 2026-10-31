"""Ottelu v2: a room's match starts only with at least two events picked (#168)."""

import json

import pytest
from conftest import ROOT
from test_rooms_lib import Relay

import test_ottelu as v1
from test_ottelu import HELPERS
# v2 plays as v1: all of v1's tests run on v2 too.
from test_ottelu import (  # noqa: F401
    test_a_match_alone_adds_up_saves_and_leaves_the_events_own_saves_alone, test_a_match_goes_on_after_a_reload,
    test_a_reload_while_an_events_results_show_keeps_its_points, test_an_away_phone_is_played_for_in_this_event_and_the_next,
    test_events_are_picked_in_the_order_tapped, test_points_follow_the_combined_event_tables,
    test_the_event_pages_are_fetched_ahead_for_offline_play, test_the_menu_and_the_board_fit,
    test_two_phones_play_a_match_and_see_the_same_points)

URL = "games/ottelu/v2/"


@pytest.fixture(autouse=True)
def v2(monkeypatch):
    monkeypatch.setattr(v1, "URL", URL)


def join(site, browser, names):
    """The first phone makes a room and the others join it; nobody starts yet."""
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(HELPERS)
        pages.append(page)
    host = pages[0]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for guest in pages[1:]:
        guest.click("#multi")
        guest.fill("#aipr-codeIn", code)
        guest.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    return relay, pages


@pytest.mark.parametrize("left", [0, 1])
def test_the_host_cannot_start_a_room_match_with_fewer_than_two_events(site, browser, left):
    relay, pages = join(site, browser, ["Eero", "Aino"])
    host, aino = pages
    assert not host.is_disabled("#aipr-start")
    keep = ["keihas"][:left]
    for s in ["pituushyppy", "korkeushyppy", "seivashyppy", "keihas", "moukari"]:
        if s not in keep:
            host.click(f".laji[data-slug={s}]")
    assert host.is_disabled("#aipr-start")
    assert "Valitse ainakin kaksi lajia." in host.inner_text("#aipr")
    # rooms.js sets the button again on each render; it stays off.
    host.evaluate("document.getElementById('aipr-start').disabled = false")
    host.wait_for_function("document.getElementById('aipr-start').disabled")
    # A tap that gets through anyway starts nothing.
    host.evaluate("document.getElementById('aipr-start').removeAttribute('disabled'); document.getElementById('aipr-start').dispatchEvent(new MouseEvent('click', { bubbles: true }))")
    host.wait_for_timeout(500)
    assert host.evaluate("M === null && !AiPelitRooms.round")
    # Two events: the start comes back, and the match plays exactly those, in the order tapped.
    for s in ["moukari", "keihas"][:2 - left]:
        host.click(f".laji[data-slug={s}]")
    host.wait_for_function("!document.getElementById('aipr-start').disabled")
    assert "Valitse ainakin kaksi lajia." not in host.inner_text("#aipr")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("M && M.events && M.events.length === 2", timeout=10000)
    assert aino.evaluate("M.events.join()") == ("keihas,moukari" if left else "moukari,keihas")
    for p in pages:
        assert p.errors == []
        p.context.close()
