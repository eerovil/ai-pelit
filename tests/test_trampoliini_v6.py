"""Trampoliini v6: the jumper's outfit, Halloween costumes too (#158)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/trampoliini/v6/"


@pytest.fixture
def tramp_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "trampoliini", games / "trampoliini")
    site.build(games)
    return site


def open_at(browser, site, w, h, level=None):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    if level:
        page.evaluate(f"localStorage.setItem('ai-pelit:trampoliini:taso', '{level}')")
        page.reload()
    return ctx, page, errors


def inside(box, w, h):
    return box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


def test_picking_a_costume_dresses_the_jumper_and_is_kept(tramp_site, browser):
    ctx, page, errors = open_at(browser, tramp_site, 360, 740)
    assert page.locator("#asu").inner_text() == "👕 Asu: Perus"
    page.click("#asu")
    cards = page.locator("#ai-pelit-asut .asu")
    assert cards.count() == 10   # four everyday outfits and six costumes
    page.click("[data-asu=vampyyri]")
    assert page.locator("[data-asu=vampyyri]").get_attribute("class") == "asu valittu"
    page.click("#ai-pelit-asut-valmis")
    assert page.locator("#ai-pelit-asut").count() == 0
    assert page.locator("#asu").inner_text() == "👕 Asu: Vampyyri"
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:trampoliini')") == '"vampyyri"'
    # Still there after a reload, and the round plays in it.
    page.reload()
    assert page.evaluate("outfit.id") == "vampyyri"
    page.click("#go")
    page.wait_for_timeout(400)
    assert page.evaluate("phase") in ("mat", "air")
    assert errors == []
    ctx.close()


def test_an_unknown_saved_outfit_falls_back_to_the_first(tramp_site, browser):
    ctx, page, errors = open_at(browser, tramp_site, 360, 740)
    page.evaluate("localStorage.setItem('ai-pelit:_asut:trampoliini', '\"ei-ole\"')")
    page.reload()
    assert page.evaluate("outfit.id") == "perus"
    assert errors == []
    ctx.close()


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844), (740, 360), (640, 360), (844, 390)])
def test_the_menu_with_the_outfit_button_fits(tramp_site, browser, w, h):
    ctx, page, errors = open_at(browser, tramp_site, w, h, level=4)
    page.evaluate("lastResult = { won: false, points: 123, level: 4 }; showMenu()")
    assert page.evaluate("[document.documentElement.scrollHeight, document.documentElement.scrollWidth]") == [h, w]
    for sel in ("#menu h1", "#go", "#asu", "#stats"):
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    back, chip = page.locator("#ai-pelit-back").bounding_box(), page.locator("#ai-pelit-tulokset-nappi").bounding_box()
    asu = page.locator("#asu").bounding_box()
    assert not overlap(asu, back) and not overlap(asu, chip)
    assert not overlap(asu, page.locator("#go").bounding_box())
    # The picker fits too, its ready button on the screen.
    page.click("#asu")
    assert inside(page.locator("#ai-pelit-asut-valmis").bounding_box(), w, h)
    box = page.locator("#ai-pelit-asut > div").bounding_box()
    assert not overlap(box, back)
    assert page.evaluate("[document.documentElement.scrollHeight, document.documentElement.scrollWidth]") == [h, w]
    assert errors == []
    ctx.close()
