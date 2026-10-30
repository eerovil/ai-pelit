"""Areena v4: playable with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT

LANDSCAPE = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def phone(site, browser):
    # Only this game is built, so another game's unfinished folder cannot break the build.
    shutil.copytree(ROOT / "games" / "areena", site.games / "areena")
    site.build()
    contexts = []

    def open_at(width, height):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(f"{site.url}games/areena/v4/")
        page.evaluate("localStorage.setItem('ai-pelit:areena:voitot', '3'); localStorage.setItem('ai-pelit:areena:haviot', '2')")
        page.reload()
        return page

    yield open_at
    for ctx in contexts:
        ctx.close()


def inside(box, width, height):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height


@pytest.mark.parametrize("size", LANDSCAPE)
def test_v4_menu_fits_sideways(phone, size):
    w, h = size
    page = phone(w, h)
    # The end-of-fight menu is the longest one.
    page.evaluate("showMenu('🏆 Sankari voitti!', 'win')")
    for sel in ("#menu h1", "#result", "#name", "#foe", "#go", "#multi", "#stats", "#menu .help", "#ai-pelit-back"):
        box = page.locator(sel).bounding_box()
        assert box and inside(box, w, h), (sel, box)
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    # The chip does not cover the menu's title.
    chip, title = page.locator("#ai-pelit-back").bounding_box(), page.locator("#menu h1").bounding_box()
    assert chip["y"] + chip["height"] <= title["y"] or chip["x"] + chip["width"] <= title["x"]
    page.click("#multi")
    page.wait_for_selector("#aipr-create", state="visible")
    assert page.errors == []


def test_v4_a_fight_runs_sideways_and_survives_turning_the_phone(phone):
    page = phone(740, 360)
    page.fill("#name", "Testi")
    page.click("#go")
    page.wait_for_function("state === 'fight'", timeout=6000)
    # The arena fills the height in the middle; stick on the left and buttons on the right, beside it.
    lay = page.evaluate("({land, ox, right: ox + AW * scale, top: oy, bottom: oy + AH * scale, pad: padHome(), b: buttons()})")
    assert lay["land"] and lay["top"] >= 0 and lay["bottom"] <= 360 and lay["bottom"] - lay["top"] > 320
    assert lay["pad"]["x"] + 50 <= lay["ox"]
    for b in lay["b"]:
        assert b["x"] - b["r"] >= lay["right"] and b["x"] + b["r"] <= 740 and b["y"] + b["r"] <= 360
    # Real touches: walk with the stick and shoot with the bow.
    page.evaluate("""(() => { const c = document.getElementById('c'), h = padHome(), b = buttons().find(b => b.k === 'bow');
      const ev = (t, id, x, y) => c.dispatchEvent(new PointerEvent(t, {pointerId: id, clientX: x, clientY: y, bubbles: true, cancelable: true}));
      ev('pointerdown', 1, h.x, h.y); ev('pointermove', 1, h.x, h.y - 45); ev('pointerdown', 2, b.x, b.y); })()""")
    y0 = page.evaluate("me.y")
    page.wait_for_function(f"me.y < {y0} - 30 && me.ammo < 5", timeout=4000)
    before = page.evaluate("({x: me.x, y: me.y, hp: foe.hp + me.hp, foe: foe.name})")
    # Turn the phone mid-fight, and back: the fight goes on where it was. (The tap on the
    # button took the page full screen, and Chromium only resizes a window that is not.)
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_function("!document.fullscreenElement")
    for w, h in ((360, 740), (740, 360)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(300)
        state = page.evaluate("({state, land, x: me.x, y: me.y, hp: foe.hp + me.hp, foe: foe.name, W})")
        assert state["state"] == "fight" and state["W"] == w and state["land"] == (w > h)
        assert state["foe"] == before["foe"] and state["hp"] <= before["hp"]
        assert abs(state["y"] - before["y"]) < 200
    assert page.errors == []


def test_v4_portrait_layout_is_v3s(site, browser):
    shutil.copytree(ROOT / "games" / "areena", site.games / "areena")
    site.build()
    found = {}
    for version in ("v3", "v4"):
        ctx = browser.new_context(viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.goto(f"{site.url}games/areena/{version}/")
        menu = [page.locator(s).bounding_box() for s in ("#menu h1", "#name", "#foe", "#go", "#multi", "#menu .help")]
        page.click("#go")
        found[version] = (menu, page.evaluate("JSON.stringify([scale, ox, oy, ctrlTop, buttons(), padHome()])"))
        ctx.close()
    assert found["v3"] == found["v4"]
