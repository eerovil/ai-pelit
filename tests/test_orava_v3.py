"""Orava v3: the squirrel's outfit, Halloween costumes too (#158)."""

import shutil

import pytest
from conftest import ROOT

URL = "games/orava/v3/"


def open_game(site, browser, viewport):
    # Only this game, so another game's half-done version cannot break the build.
    shutil.copytree(ROOT / "games" / "orava", site.games / "orava")
    site.build()
    ctx = browser.new_context(viewport=viewport, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    return ctx, page, errors


def inside(box, w, h):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and \
        a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


def test_a_picked_costume_is_saved_shown_and_worn_in_play(site, browser):
    ctx, page, errors = open_game(site, browser, {"width": 360, "height": 740})
    try:
        assert page.locator("#asu").inner_text() == "👕 Asu: Punaorava"
        page.locator("#asu").tap()
        cards = page.locator("#ai-pelit-asut [data-asu]")
        assert cards.count() == 10   # four squirrels, six costumes
        page.locator("[data-asu=kurpitsa]").tap()
        assert page.evaluate("localStorage.getItem('ai-pelit:_asut:orava')") == '"kurpitsa"'
        page.locator("#ai-pelit-asut-valmis").tap()
        assert page.locator("#ai-pelit-asut").count() == 0
        assert page.locator("#asu").inner_text() == "👕 Asu: Kurpitsa"
        # A reload keeps it, and every costume draws in a round without an error.
        page.reload()
        assert page.locator("#asu").inner_text() == "👕 Asu: Kurpitsa"
        page.locator("#go").tap()
        for o in page.evaluate("AiPelitOutfits.list().map(o => o.id)"):
            page.evaluate(f"outfit = AiPelitOutfits.get('{o}'); S.mode = 'air'; draw(); S.mode = 'ground'; draw()")
        assert errors == []
    finally:
        ctx.close()


@pytest.mark.parametrize("size", [(740, 360), (640, 360)])
def test_the_outfit_button_fits_the_sideways_menu(site, browser, size):
    w, h = size
    ctx, page, errors = open_game(site, browser, {"width": w, "height": h})
    try:
        assert page.evaluate("document.scrollingElement.scrollHeight") <= h
        boxes = page.evaluate("""() => [...document.querySelectorAll('#menu > *')].filter(e => e.offsetParent)
            .map(e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; })""")
        for b in boxes:
            assert inside(b, w, h)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert not overlap(a, b)
        asu = page.locator("#asu")
        assert inside(asu.bounding_box(), w, h)
        asu.tap()
        done = page.locator("#ai-pelit-asut-valmis")
        assert inside(done.bounding_box(), w, h)
        done.tap()
        assert page.evaluate("phase") == "menu"
        assert errors == []
    finally:
        ctx.close()
