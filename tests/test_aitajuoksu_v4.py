"""Aitajuoksu v4: v3's races with the phone on its side, the foot pads at the edges under the thumbs."""

import shutil

import pytest

from conftest import ROOT

URL = "games/aitajuoksu/v4/"
LANDSCAPES = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def landscape(browser):
    ctx = browser.new_context(viewport={"width": 740, "height": 360}, is_mobile=True, has_touch=True)
    yield ctx
    ctx.close()


def open_game(site, context, url=URL):
    # Only this game, so another game's work in progress does not stop the build.
    if not (site.games / "aitajuoksu").exists():
        shutil.copytree(ROOT / "games" / "aitajuoksu", site.games / "aitajuoksu")
        site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + url)
    return page


def start_running(page):
    page.click("#go")
    page.evaluate("race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 0.2")
    page.wait_for_function("race && race.phase === 'run'", timeout=5000)


def inside(box, w, h):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


@pytest.mark.parametrize("w,h", LANDSCAPES)
def test_the_menu_fits_on_its_side(site, browser, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx)
    page.evaluate("localStorage.setItem('ai-pelit:aitajuoksu:juoksut', '3')")
    page.evaluate("showMenu('Voitit! 14,20 s 🏆', 'win')")
    sels = ["#menu h1", "#result", "#stats", ".help.side", "#go", "#multi"]
    sels += [f"#dists [data-d='{d}']" for d in (100, 200, 400)] + ["#hurd [data-h='1']", "#hurd [data-h='0']"]
    for sel in sels:
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    assert not page.locator(".help:not(.side)").is_visible()
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight")
    # The buttons are clear of the chips in the top corners.
    chips = [page.locator(s).bounding_box() for s in ["#ai-pelit-back", "#ai-pelit-tulokset-nappi"]]
    for sel in ["#go", "#multi", "#dists", "#hurd"]:
        b = page.locator(sel).bounding_box()
        assert all(b["y"] >= c["y"] + c["height"] or b["x"] >= c["x"] + c["width"] or b["x"] + b["width"] <= c["x"] for c in chips), sel
    # The race picker works sideways.
    page.click("#dists [data-d='400']")
    page.click("#hurd [data-h='0']")
    assert page.evaluate("[dist, hurdles]") == [400, False]
    page.click("#multi")
    page.wait_for_selector("#aipr-create", state="visible")
    assert page.errors == []
    ctx.close()


def test_a_round_on_its_side_runs_from_the_side_pads(site, landscape):
    page = open_game(site, landscape)
    start_running(page)
    assert page.evaluate("land") is True
    pads = page.evaluate("pads()")
    assert [p["k"] for p in pads] == [3, 1, 3, 2]
    for p in pads:
        assert inside({"x": p["x"], "y": p["y"], "width": p["w"], "height": p["h"]}, 740, 360)
    # The feet are in the lower corners, the scene between them.
    left, right = pads[1], pads[3]
    assert left["x"] < 40 and right["x"] + right["w"] > 700 and left["y"] + left["h"] > 330
    sx, sw = page.evaluate("[SX, SW]")
    assert sx >= left["x"] + left["w"] and sx + sw <= right["x"]
    page.mouse.click(left["x"] + left["w"] / 2, left["y"] + left["h"] / 2)
    page.mouse.click(right["x"] + right["w"] / 2, right["y"] + right["h"] / 2)
    page.mouse.click(left["x"] + left["w"] / 2, left["y"] + left["h"] / 2)
    assert page.evaluate("me.v") > 2
    # The jump pad and a tap on the track both jump.
    page.evaluate("Object.assign(me, { x: 5, y: 0, vy: 0, stum: 0 })")
    jp = pads[2]
    page.mouse.click(jp["x"] + jp["w"] / 2, jp["y"] + jp["h"] / 2)
    assert page.evaluate("me.vy > 0")
    page.wait_for_function("me.y === 0 && me.vy === 0", timeout=3000)
    page.mouse.click(370, 250)
    assert page.evaluate("me.vy > 0")
    page.wait_for_function("me.x > 8", timeout=5000)
    assert page.errors == []


def test_a_400_m_race_on_its_side_finishes(site, landscape):
    page = open_game(site, landscape)
    page.click("#dists [data-d='400']")
    page.click("#hurd [data-h='0']")
    start_running(page)
    assert page.evaluate("[land, TRACK, H_N]") == [True, 400, 0]
    page.evaluate("race.runners.forEach(r => { if (r !== me) r.rate = 1; }); Object.assign(me, { x: 399.5, v: 9 })")
    page.wait_for_function("race.phase === 'done'", timeout=5000)
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=12000)
    assert page.inner_text("#result").startswith("Voitit!")
    assert page.errors == []


def test_turning_the_phone_mid_round_keeps_the_round(site, landscape):
    page = open_game(site, landscape)
    page.click("#dists [data-d='200']")
    start_running(page)
    page.evaluate("Object.assign(me, { x: 30, v: 8 }); window.theRace = race")
    # The tap on "Juokse!" took the page full screen; Chromium only resizes a window that is not.
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_function("!document.fullscreenElement")
    for w, h in [(360, 740), (740, 360), (360, 640), (844, 390)]:
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_function(f"innerWidth === {w} && land === {'true' if w > h else 'false'}", timeout=3000)
        page.wait_for_timeout(150)
        assert page.evaluate("race === theRace && race.phase === 'run' && me.x > 30 && TRACK === 200 && H_N === 10")
        if w > h:
            assert page.evaluate("SX > 0 && SX + SW < innerWidth")
        else:
            assert page.evaluate("SX === 0 && SW === innerWidth && ctrlTop < innerHeight")
    page.evaluate("race.runners.forEach(r => { if (r !== me) r.rate = 1; }); Object.assign(me, { x: 199.5, v: 9, down: 1023 })")
    page.wait_for_function("race.phase === 'done'", timeout=5000)
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=12000)
    assert page.inner_text("#result").startswith("Voitit!")
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 740), (360, 640)])
def test_upright_is_as_v3(site, browser, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    layout = """[...document.querySelectorAll('#menu > *')].map(e => {
      const b = e.getBoundingClientRect(); return [e.id || e.className, b.x, b.y, b.width, b.height]; })"""
    play = "[ctrlTop, ctrlH, trackTop, laneH, sc, sv, pads().map(p => [p.k, p.x, p.y, p.w, p.h])]"
    seen = {}
    for v in ("v3", "v4"):
        page = open_game(site, ctx, f"games/aitajuoksu/{v}/")
        menu = [m for m in page.evaluate(layout) if m[0] != "help side"]
        start_running(page)
        seen[v] = (menu, page.evaluate(play))
        page.close()
    assert seen["v4"] == seen["v3"]
    ctx.close()
