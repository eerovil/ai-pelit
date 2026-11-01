"""Ottelu v5: the medal ceremony only when the whole match ends (#294).

Between events the points table shows as in v4, and the high jump and pole vault bars rise in twice
the events' own steps; after the last event the top three by the match's
points stand on the podium (the shared athletics library's ceremony), and a tap leaves it for the
final standings. The high score is sent only then, so the nickname question opens after the podium.
"""

import json

import pytest

import test_ottelu as v1
import test_ottelu_v4 as v4
from conftest import turn
from test_ottelu_v4 import finish_event, in_frame, open_game, room
# v5 plays as v4 up to the end of the match: v4's tests that play a match to its end run on v5
# too, their play() also tapping the ceremony away.
from test_ottelu_v4 import (  # noqa: F401
    test_a_match_alone_with_the_hurdles_and_the_shot_put, test_a_reload_mid_race_runs_the_race_again_and_keeps_the_points,
    test_all_seven_events_can_be_picked, test_an_event_ends_on_its_results_not_a_podium, test_the_menu_and_the_board_fit,
    test_each_newer_field_event_plays_to_its_results_in_the_match, test_two_phones_run_the_hurdles_and_see_the_same_points)

URL = "games/ottelu/v5/"
# play() also leaves the ceremony: to its end, then the tap that goes on.
HELPERS = v4.HELPERS.replace("""  window.play = () => {
""", """  window.play = () => {
    if (window.leavePodium !== false && typeof cer !== 'undefined' && cer && cer.K.ending) {
      const tap = () => document.getElementById('pallit').dispatchEvent(new Event('pointerdown'));
      tap(); tap();
      return 'podium';
    }
""")
assert HELPERS != v4.HELPERS


@pytest.fixture(autouse=True)
def v5(monkeypatch):
    for m in (v1, v4):
        monkeypatch.setattr(m, "URL", URL)
        monkeypatch.setattr(m, "HELPERS", HELPERS)


def podium_up(page):
    return page.evaluate("!document.getElementById('pallit').classList.contains('hidden') && !!cer")


def play_to_podium(pages):
    for p in pages:
        p.evaluate("window.leavePodium = false")
    for _ in range(1500):
        for p in pages:
            p.evaluate("play()")
        if all(podium_up(p) for p in pages):
            return
        pages[0].wait_for_timeout(20)
    raise AssertionError("no ceremony at the end of the match")


def test_alone_the_podium_shows_only_at_the_end_of_the_match(site, context):
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    # After the first event: the points table, no ceremony.
    assert page.inner_text("#bTitle") == "Kuulantyöntö · laji 1/2" and not podium_up(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_to_podium([page])
    # The ceremony is the match's: its standings by points, the player's total among them.
    res = page.evaluate("cer.K.ending.res.map(r => [r.place, r.name, r.best])")
    totals = page.evaluate("standings().map(r => [r.name, total(r)])")
    assert [[n, b] for _, n, b in res] == totals and [p for p, _, _ in res] == list(range(1, 9))
    assert page.evaluate("cer.K.ending.res.find(r => r.p === 'me').best") == page.evaluate("total(mine())")
    assert page.evaluate("cer.K.fmt(1435) === space(1435) + ' p'")
    assert page.is_hidden("#board")
    # The first score on this phone asks for a nickname, but not over the podium.
    assert not page.is_visible("#ai-pelit-tulokset")
    assert page.evaluate("pendingScore && pendingScore.pts") == page.evaluate("total(mine())")
    # It runs by itself; a tap during it finishes it, the next tap leaves it for the final standings.
    page.wait_for_function("cer.K.ending.t > 0.5", timeout=5000)
    page.mouse.click(180, 400)
    assert page.evaluate("cer.K.ending.t >= AiPelitKisa.PODIUM_DONE") and podium_up(page)
    page.wait_for_timeout(200)
    page.screenshot(path="/var/tmp/ottelu-v5-podium.png")
    page.mouse.click(180, 400)
    assert not podium_up(page)
    page.screenshot(path="/var/tmp/ottelu-v5-after.png")
    assert page.inner_text("#bTitle") == "Lopputulokset"
    # Only now the score goes, and the nickname question opens over the final standings.
    assert page.evaluate("pendingScore") is None
    queued = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono'))")
    assert [q["score"] for q in queued.values()] == [page.evaluate("total(mine())")]
    assert page.is_visible("#ai-pelit-nimi")
    assert page.errors == []


def test_with_friends_every_phone_sees_the_podium_at_the_end(site, browser):
    names = ["Eero", "Aino", "Ville"]
    relay, pages = room(site, browser, names, ["kuula", "keihas"])
    host = pages[0]
    v1.play_event(pages)
    assert not any(podium_up(p) for p in pages)
    host.click("#next")
    for p in pages:
        p.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_to_podium(pages)
    # Every phone stands the same match standings on its podium, its own player among them.
    order = host.evaluate("standings().map(r => r.id + ':' + total(r)).join()")
    for p, name in zip(pages, names):
        assert p.evaluate("cer.K.ending.res.map(r => r.id + ':' + r.best).join()") == order
        me = p.evaluate("cer.K.ending.res.find(r => r.p === AiPelitRooms.me)")
        assert me["name"] == name and me["best"] == p.evaluate("total(mine())")
        assert p.evaluate("cer.K.ending.place") == me["place"]
    # Each phone leaves the ceremony on its own taps, for the final standings and the room.
    for p in pages:
        p.evaluate("window.leavePodium = true; play()")
        assert not podium_up(p)
        assert p.inner_text("#bTitle") == "Lopputulokset"
        assert p.inner_text("#next") == "Takaisin huoneeseen"
    host.click("#next")
    assert host.is_hidden("#board")
    for p in pages:
        assert p.errors == []
        p.context.close()


@pytest.mark.parametrize("slug", ["korkeushyppy", "seivashyppy"])
def test_the_bar_rises_in_twice_the_events_steps(site, context, slug):
    page = open_game(site, context, saved={"lajit": [slug, "keihas"]})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && Ottelu.K.comp.heights.length", timeout=10000)
    own = json.loads(in_frame(page, "JSON.stringify(heightsFor(K.comp.level))"))
    kept = json.loads(in_frame(page, "JSON.stringify(K.comp.heights)"))
    assert kept == own[::2] and len(kept) < len(own)
    # The computer's plan moved onto the kept heights.
    for first, skip in json.loads(in_frame(page, "JSON.stringify(K.comp.throwers.filter(t => t.p === null).map(t => [t.first, t.skip || []]))")):
        assert 0 <= first < len(kept) and all(0 <= i < len(kept) for i in skip)
    assert page.errors == []


def test_a_reload_during_the_podium_still_sends_the_score(site, context):
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Eero'))")
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    play_to_podium([page])
    pts = page.evaluate("total(mine())")
    assert page.evaluate("localStorage.getItem('ai-pelit:_tulokset:jono')") is None
    page.reload()
    # The match is over: the menu, with the score sent and nothing kept to send again.
    assert page.is_visible("#menu") and page.is_hidden("#cont")
    queued = json.loads(page.evaluate("localStorage.getItem('ai-pelit:_tulokset:jono')"))
    assert [q["score"] for q in queued.values()] == [pts]
    assert page.evaluate("localStorage.getItem('ai-pelit:ottelu:lahettamatta')") is None
    assert page.errors == []


@pytest.mark.parametrize("size", [(390, 844), (740, 360)])
def test_the_podium_fills_the_screen(site, context, size):
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    turn(page, {"width": size[0], "height": size[1]})
    page.evaluate("picked.splice(0); ['kuula', 'keihas'].forEach(s => picked.push(s)); M = newMatch('solo', [{ id: 'me', name: 'Sinä' }]); M.at = 1;"
                  "M.rows = field().map((f, i) => ({ ...f, marks: [10, 50], pts: [500 + i, 600 - i * 20] })); eventScored([]);")
    # eventScored took no event: end the match by hand, as after the last event.
    page.evaluate("M.phase = 'over'; finish(); after()")
    assert podium_up(page)
    page.wait_for_timeout(300)
    box = page.evaluate("(() => { const c = document.getElementById('pallit'); return [c.clientWidth, c.clientHeight, innerWidth, innerHeight]; })()")
    assert box[0] == box[2] and box[1] == box[3]
    assert page.evaluate("cer.K.ending.res.slice(0, 3).map(r => r.place).join()") == "1,2,3"
    assert page.errors == []
