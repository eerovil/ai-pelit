"""Ottelu v7: a "👕 Asu" button on the menu; the outfit picked is worn in every event (#311).

The athletics events and Ottelu share one outfit choice (outfits.js data-share="yleisurheilu"),
so each event of the match, loaded in its frame, wears what was picked here.
"""

import pytest

import test_ottelu as v1
import test_ottelu_v4 as v4
import test_ottelu_v5 as v5
import test_ottelu_v6 as v6
from conftest import ROOT, turn
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


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
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


def test_the_player_wears_the_outfit_on_the_podium_at_the_end_of_the_match(site, context):
    # Review of #315: the match's own medal ceremony drew everyone in the plain kit.
    from test_ottelu_v4 import finish_event
    context.add_init_script(f"localStorage.setItem('{SHARED}', JSON.stringify('noita'))")
    page = open_game(site, context, saved={"lajit": ["kuula", "keihas"]})
    assert page.text_content("#asu") == "👕 Asu: Noita"
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    finish_event(page)
    with page.expect_navigation():
        page.click("#next")
    page.wait_for_function("window.Ottelu && Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers && M.at === 1", timeout=10000)
    v5.play_to_podium([page])
    rows = page.evaluate("cer.K.ending.res.map(r => [r.p, (podiumLook(r) || {}).head || null])")
    assert [h for p, h in rows if p == "me"] == ["witch"]
    assert all(h is None for p, h in rows if p != "me")
    page.wait_for_function("cer.K.ending.t > 2", timeout=8000)
    page.screenshot(path="/var/tmp/i311/ottelu-podium.png")
    assert page.errors == []


def test_a_kept_match_with_the_outfit_button_fits_a_short_phone(site, context):
    # CI on #315: at 360 × 640 the fourth button pushed the menu off the screen.
    page = open_game(site, context, saved={"lajit": ["keihas", "moukari"]})
    turn(page, {"width": 360, "height": 640})
    page.click("#go")
    page.wait_for_function("Ottelu.K && Ottelu.K.comp && Ottelu.K.comp.throwers", timeout=10000)
    page.reload()
    assert page.is_visible("#cont") and page.is_visible("#asu")
    for s in ("#menu h1", "#go", "#cont", "#multi", "#asu", "#stats"):
        b = page.locator(s).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= 640, s
    assert page.errors == []


GAMES = {"ottelu": "games/ottelu/v7/", "keihas": "games/keihas/v8/", "kuula": "games/kuula/v3/",
         "aitajuoksu": "games/aitajuoksu/v9/", "pituushyppy": "games/pituushyppy/v9/",
         "korkeushyppy": "games/korkeushyppy/v6/", "seivashyppy": "games/seivashyppy/v6/", "moukari": "games/moukari/v6/"}


@pytest.mark.parametrize("order", [
    ["kuula", "ottelu", "pituushyppy", "keihas", "aitajuoksu", "moukari"],
    ["ottelu", "aitajuoksu", "kuula", "korkeushyppy", "keihas", "seivashyppy"],
])
def test_choices_made_before_in_different_games_become_one_whichever_opens_first(site, browser, order):
    # Review of #315: a phone with Noita in Keihäs and Kulta in Kuula (and Neon in Aitajuoksu)
    # showed three outfits. The first game opened takes Keihäs's (the fixed order), and every
    # game shows it, with no pick in between.
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    ctx.add_init_script("""if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');
      if (!localStorage.getItem('seeded')) { localStorage.setItem('seeded', '1');
        localStorage.setItem('ai-pelit:_asut:keihas', '"noita"');
        localStorage.setItem('ai-pelit:_asut:kuula', '"kulta"');
        localStorage.setItem('ai-pelit:_asut:aitajuoksu', '"neon"'); } }""")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    for slug in order:
        page.goto(site.url + GAMES[slug])
        assert page.text_content("#asu") == "👕 Asu: Noita", slug
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"noita"'
    # The older versions' own keys are left as they were until the next pick.
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:kuula')") == '"kulta"'
    assert errors == []
    ctx.close()
