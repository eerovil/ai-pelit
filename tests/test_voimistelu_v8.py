"""Voimistelu v8: an outfit picker with Halloween costumes (#158)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/voimistelu/v8/"


@pytest.fixture
def voim_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "voimistelu", games / "voimistelu")
    site.build(games)
    return site


def open_at(browser, site, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#asu:not(.off)")
    return ctx, page, errors


def inside(box, w, h):
    return box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


def test_picking_a_costume_saves_it_and_dresses_the_gymnast(voim_site, browser):
    ctx, page, errors = open_at(browser, voim_site, 360, 740)
    assert page.inner_text("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut [data-asu]").count() == 10
    page.click("[data-asu=luuranko]")
    page.click("#ai-pelit-asut-valmis")
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:voimistelu')") == '"luuranko"'
    assert page.inner_text("#asu") == "👕 Asu: Luuranko"
    assert page.evaluate("outfit.head") == "skull"
    # Kept after a reload, as every later version will read it.
    page.reload()
    page.wait_for_selector("#asu:not(.off)")
    assert page.inner_text("#asu") == "👕 Asu: Luuranko"
    assert errors == []
    ctx.close()


def test_the_button_hides_during_a_routine_and_returns_on_the_score_board(voim_site, browser):
    ctx, page, errors = open_at(browser, voim_site, 360, 740)
    page.mouse.click(180, 500)
    page.wait_for_selector("#asu.off", state="attached")
    page.evaluate("touch = { fall: false, stuck: true, saltos: 0, halves: 0 }; finish()")
    page.wait_for_selector("#asu:not(.off)")
    # The board sits below the button.
    page.wait_for_timeout(100)
    assert page.evaluate("resultLayout.bottom") <= 740
    btn = page.locator("#asu").bounding_box()
    assert page.evaluate("resultLayout.top") >= btn["y"] + btn["height"]
    assert errors == []
    ctx.close()


@pytest.mark.parametrize("w,h", [(740, 360), (360, 740)])
def test_the_picker_and_the_button_fit_the_screen(voim_site, browser, w, h):
    ctx, page, errors = open_at(browser, voim_site, w, h)
    btn = page.locator("#asu").bounding_box()
    assert inside(btn, w, h)
    assert not overlap(btn, page.locator("#ai-pelit-back").bounding_box())
    assert not overlap(btn, page.locator("#ai-pelit-tulokset-nappi").bounding_box())
    page.click("#asu")
    assert inside(page.locator("#ai-pelit-asut-valmis").bounding_box(), w, h)
    assert errors == []
    ctx.close()
