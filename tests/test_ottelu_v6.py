"""Ottelu v6: each event plays its newest published version by itself (#303).

The match reads the shelf's catalog.json as it opens and plays the newest version of each event
there (one whose game.json entry says `"ottelu": false` is left out), so the athletics events' turns,
spectators and "📣 Kannusta" (yleisurheilu-5, #297) are in the match too. With friends a field event
waits only for the phone on turn, and the host skips an away phone's attempt.

These tests also run when any event's game changes (the marker below): a new event version that
does not play in the match fails its own pull request.
"""

import json

import pytest

import test_ottelu as v1
import test_ottelu_v4 as v4
import test_ottelu_v5 as v5
from conftest import ROOT
from test_ottelu_v4 import finish_event, in_frame, open_game, room
# v6 plays as v5 does once its events are loaded: v5's tests run on v6 too.
from test_ottelu_v5 import (  # noqa: F401
    test_a_match_alone_with_the_hurdles_and_the_shot_put, test_alone_the_podium_shows_only_at_the_end_of_the_match,
    test_all_seven_events_can_be_picked, test_an_event_ends_on_its_results_not_a_podium,
    test_the_bar_rises_in_twice_the_events_steps, test_two_phones_run_the_hurdles_and_see_the_same_points,
    test_with_friends_every_phone_sees_the_podium_at_the_end, test_a_reload_during_the_podium_still_sends_the_score,
    test_the_podium_fills_the_screen, test_a_reload_mid_race_runs_the_race_again_and_keeps_the_points,
    test_each_newer_field_event_plays_to_its_results_in_the_match)
from test_ottelu_v4 import test_the_race_and_its_results_fit  # noqa: F401
from test_ottelu import test_the_menu_and_the_board_fit  # noqa: F401

EVENTS = ["aitajuoksu", "pituushyppy", "kuula", "korkeushyppy", "seivashyppy", "keihas", "moukari"]
pytestmark = pytest.mark.games("ottelu", *EVENTS)

URL = "games/ottelu/v6/"


@pytest.fixture(autouse=True)
def v6(monkeypatch):
    for m in (v1, v4):
        monkeypatch.setattr(m, "URL", URL)
        monkeypatch.setattr(m, "HELPERS", v5.HELPERS)


def newest(slug):
    return max(v["n"] for v in json.loads((ROOT / "games" / slug / "game.json").read_text())["versions"] if v.get("ottelu") is not False)


def ready(page):
    """Waits until the match has read the catalog."""
    page.evaluate("newest.then(() => true)")


def test_every_event_plays_its_newest_version(site, context):
    page = open_game(site, context, saved={"lajit": EVENTS})
    ready(page)
    assert page.evaluate("NEWEST") == {s: newest(s) for s in EVENTS}
    page.click("#go")
    page.wait_for_function("frameReady && frameAt === 0", timeout=10000)
    assert page.evaluate("M.v") == {s: newest(s) for s in EVENTS}
    assert in_frame(page, "document.baseURI").endswith(f"/games/aitajuoksu/v{newest('aitajuoksu')}/")
    assert page.errors == []


def test_a_new_version_joins_by_itself_unless_it_is_kept_out(site, context):
    site.build(ROOT / "games")
    catalog = json.loads((site.out / "catalog.json").read_text())
    for g in catalog["games"]:
        if g["slug"] == "kuula":
            g["versions"].append({"n": 99, "date": "2026-12-01", "note": "x"})
        if g["slug"] == "keihas":
            g["versions"].append({"n": 98, "date": "2026-12-01", "note": "x", "ottelu": False})
    page = context.new_page()
    page.route("**/catalog.json", lambda r: r.fulfill(json=catalog))
    page.goto(site.url + URL)
    ready(page)
    assert page.evaluate("NEWEST.kuula") == 99
    assert page.evaluate("NEWEST.keihas") == newest("keihas")
    # With no catalog (offline on its first open), the versions v6 was made with.
    page = context.new_page()
    page.route("**/catalog.json", lambda r: r.abort())
    page.goto(site.url + URL)
    ready(page)
    assert page.evaluate("JSON.stringify(NEWEST)") == page.evaluate("JSON.stringify(Object.fromEntries(Object.entries(LAJIT).map(([s, l]) => [s, l.v])))")


def test_a_match_saved_by_v5_goes_on_with_its_versions(site, context):
    kept = {"mode": "solo", "round": "solo", "level": 1, "events": ["kuula", "keihas"], "at": 0, "phase": "event",
            "humans": [{"id": "me", "name": "Sinä"}], "bots": [], "rows": []}
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"], "kesken": kept})
    ready(page)
    assert page.is_visible("#cont")
    page.click("#cont")
    page.wait_for_function("frameReady && Ottelu.K && Ottelu.K.comp", timeout=10000)
    assert in_frame(page, "document.baseURI").endswith("/games/kuula/v1/")
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:ottelu:kesken')).v.keihas") == 6
    assert page.errors == []


def test_with_friends_the_others_cheer_and_an_away_phones_turn_is_skipped(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"], ["kuula", "keihas"])
    host, aino, ville = pages
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && Ottelu.K.current()", timeout=10000)
    assert all(p.evaluate("M.v.kuula") == newest("kuula") for p in pages)
    ids = {p.evaluate("AiPelitRooms.me"): p for p in pages}
    me_aino = aino.evaluate("AiPelitRooms.me")
    # The phones not on turn stand by as spectators, with the cheer button in the event.
    on = host.evaluate("Ottelu.K.current().p")
    fan = next(p for i, p in ids.items() if i != on)
    fan.wait_for_function("(() => { const b = document.getElementById('laji').contentDocument.getElementById('kisa-cheer'); return b && !b.hidden; })()", timeout=5000)
    assert sorted(host.evaluate("Ottelu.K.fans().map(f => f.p)")) == sorted(i for i in ids if i != on)
    fan.evaluate("document.getElementById('laji').contentDocument.getElementById('kisa-cheer').click()")
    fan_id = fan.evaluate("Ottelu.K.mine().id")
    host.wait_for_function(f"!!Ottelu.K.cheers[{json.dumps(fan_id)}]", timeout=5000)
    # Aino goes away. Nothing waits for her until her own turn; then the host skips it.
    relay.drop(aino)
    host.wait_for_function(f"!AiPelitRooms.members.find(m => m.id === {json.dumps(me_aino)}).on", timeout=8000)
    for _ in range(80):
        pid = host.evaluate("Ottelu.K.current() && Ottelu.K.current().p")
        if pid == me_aino:
            break
        assert host.evaluate("AiPelitRooms.paused") is False
        n = host.evaluate("Ottelu.K.comp.seq")
        ids[pid].wait_for_function(f"Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq === {n}", timeout=5000)
        ids[pid].evaluate(f"Ottelu.K.report({n}, 15)")
        host.wait_for_function(f"Ottelu.K.comp.seq > {n}", timeout=5000)
    else:
        raise AssertionError("Aino's turn never came")
    host.wait_for_function("AiPelitRooms.paused", timeout=5000)
    assert host.inner_text("#aipr-goOn") == "Ohita vuoro"
    before = host.evaluate("Ottelu.K.comp.seq")
    host.click("#aipr-goOn")
    host.wait_for_function(f"Ottelu.K.comp.seq > {before}", timeout=5000)
    t = host.evaluate(f"Ottelu.K.comp.throwers.find(t => t.p === {json.dumps(me_aino)})")
    assert -1 in t["marks"] and "bot" not in t
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_in_the_race_an_away_phones_runner_goes_to_the_computer_until_it_is_back(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"], ["aitajuoksu", "kuula"])
    host, aino = pages
    for p in pages:
        p.wait_for_function("frameReady && document.getElementById('laji').contentWindow.eval('race')", timeout=10000)
    me_aino = aino.evaluate("AiPelitRooms.me")
    relay.drop(aino)
    # The race needs every runner: it waits for her, and "Ohita vuoro" gives her runner to the computer.
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    assert host.inner_text("#aipr-goOn") == "Ohita vuoro"
    host.click("#aipr-goOn")
    host.wait_for_function(f"M.bots.includes({json.dumps(me_aino)}) && !AiPelitRooms.paused", timeout=5000)
    assert in_frame(host, f"race.runners.find(r => r.id === {json.dumps(me_aino)}).kind") == "cpu"
    # Back again: her runner is hers.
    relay.back(aino)
    host.wait_for_function(f"!M.bots.includes({json.dumps(me_aino)})", timeout=15000)
    assert in_frame(host, f"race.runners.find(r => r.id === {json.dumps(me_aino)}).kind") == "net"
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_an_away_friend_comes_back_into_the_event_and_a_reload_keeps_the_versions(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"], ["keihas", "pituushyppy"])
    host, aino = pages
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    me_aino = aino.evaluate("AiPelitRooms.me")
    relay.drop(aino)
    host.wait_for_function(f"!AiPelitRooms.members.find(m => m.id === {json.dumps(me_aino)}).on", timeout=8000)
    relay.back(aino)
    # Back in the room: the match and the meet where they are, on the versions the host started.
    aino.wait_for_function("M && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq === parent.Ottelu.K.comp.seq", timeout=15000)
    host.wait_for_function(f"AiPelitRooms.members.find(m => m.id === {json.dumps(me_aino)}).on", timeout=8000)
    # A reload mid-event, too.
    aino.reload()
    aino.wait_for_function("M && M.at === 0 && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=15000)
    assert aino.evaluate("JSON.stringify(M.v)") == host.evaluate("JSON.stringify(M.v)")
    assert in_frame(aino, "document.baseURI").endswith(f"/games/keihas/v{newest('keihas')}/")
    assert host.evaluate("AiPelitRooms.paused") is False or host.evaluate(f"Ottelu.K.current().p") == me_aino
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_a_reload_mid_event_goes_on_with_the_same_versions(site, context):
    page = open_game(site, context, saved={"lajit": ["seivashyppy", "pituushyppy", "moukari"]})
    ready(page)
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq >= 0", timeout=10000)
    for _ in range(40):
        page.evaluate("play()")
        if page.evaluate("Ottelu.K.comp.seq >= 3"):
            break
        page.wait_for_timeout(50)
    seq = page.evaluate("Ottelu.K.comp.seq")
    v = page.evaluate("M.v")
    page.reload()
    assert page.inner_text("#cont") == "Jatka ottelua (laji 1/3)"
    page.click("#cont")
    page.wait_for_function(f"Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.seq === {seq}", timeout=10000)
    assert page.evaluate("M.v") == v
    assert in_frame(page, "document.baseURI").endswith(f"/games/seivashyppy/v{newest('seivashyppy')}/")
    assert page.errors == []


def test_the_newest_event_pages_are_fetched_ahead_for_offline_play(site, context):
    page = open_game(site, context)
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    page.reload()
    page.wait_for_timeout(2500)
    for slug in EVENTS:
        assert any(u.endswith(f"/games/{slug}/v{newest(slug)}/") for u in urls), slug
    assert any(u.endswith("/lib/yleisurheilu-5/korkeus.js") for u in urls)
