"""Ottelu v7: a "👕 Asu" button on the menu; the outfit picked is worn in every event (#311).

The athletics events and Ottelu share one outfit choice (outfits.js data-share="yleisurheilu"),
so each event of the match, loaded in its frame, wears what was picked here.
"""

import pytest

import test_ottelu as v1
import test_ottelu_v4 as v4
import test_ottelu_v5 as v5
import test_ottelu_v6 as v6
from conftest import turn
from test_ottelu_v4 import in_frame, open_game
# v7 plays as v6 does: a few of v6's tests run on v7 too.
from test_ottelu_v6 import test_every_event_plays_its_newest_version  # noqa: F401
from test_ottelu_v5 import test_a_match_alone_with_the_hurdles_and_the_shot_put  # noqa: F401
from test_ottelu import test_the_menu_and_the_board_fit  # noqa: F401

pytestmark = pytest.mark.games("ottelu", *v6.EVENTS)

URL = "games/ottelu/v7/"
SHARED = "ai-pelit:_asut:yleisurheilu"


@pytest.fixture(autouse=True)
def v7(monkeypatch):
    for m in (v1, v4, v6):
        monkeypatch.setattr(m, "URL", URL)
    for m in (v1, v4):
        monkeypatch.setattr(m, "HELPERS", v5.HELPERS)


@pytest.mark.parametrize("slug", ["pituushyppy", "aitajuoksu"])
def test_the_outfit_picked_on_the_menu_is_worn_in_the_events(site, context, slug):
    page = open_game(site, context, saved={"lajit": [slug, "kuula"]})
    assert page.text_content("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut .asu").count() == 13
    page.click("[data-asu=vampyyri]")
    page.click("#ai-pelit-asut-valmis")
    assert page.text_content("#asu") == "👕 Asu: Vampyyri"
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    page.click("#go")
    page.wait_for_function("frameReady && frameAt === 0", timeout=10000)
    assert in_frame(page, "outfit.id") == "vampyyri"
    if slug == "aitajuoksu":
        page.wait_for_function("document.getElementById('laji').contentWindow.eval('race && race.runners.length > 1')", timeout=10000)
        assert in_frame(page, "race.runners.find(r => r.kind === 'me').asu") == "vampyyri"
    else:
        page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
        assert page.evaluate("Ottelu.K.comp.throwers.find(t => t.p === 'me').fit") == "vampyyri"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (740, 360), (640, 360)])
def test_the_menu_with_the_outfit_button_fits(site, context, size):
    w, h = size
    page = open_game(site, context, saved={"lajit": ["keihas", "moukari"]})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    sels = ["#go", "#multi", "#asu", "#stats", "#lajit"]
    boxes = {s: page.locator(s).bounding_box() for s in sels}
    for s, b in boxes.items():
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, s
    a = boxes["#asu"]
    for s, b in boxes.items():
        if s != "#asu":
            assert not (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
                        and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]), s
    page.click("#asu")
    done = page.locator("#ai-pelit-asut-valmis").bounding_box()
    assert done["y"] >= 0 and done["y"] + done["height"] <= h
    assert page.errors == []
