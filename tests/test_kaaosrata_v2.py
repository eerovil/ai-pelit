"""Kaaosrata v2: the same race, also played with the phone turned sideways (#95)."""

import shutil

import pytest

from conftest import ROOT

URL = "games/kaaosrata/v2/"


def build(site):
    """A site of only this game: another game's half-made version cannot break it."""
    shutil.copytree(ROOT / "games" / "kaaosrata", site.games / "kaaosrata")
    site.build()


def unfull(page):
    # back.js goes fullscreen on the first tap, and Chromium will not resize a fullscreen window.
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    page.wait_for_timeout(100)


def phone(browser, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    return page


def inside(box, width, height):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


@pytest.mark.parametrize("size", [(740, 360), (844, 390), (640, 360), (360, 640)])
def test_the_menu_fits_without_scrolling(site, browser, size):
    build(site)
    w, h = size
    page = phone(browser, w, h)
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:kaaosrata:ennatys', '63.21'); showMenu('Voitit! 61,20 s 🏆', 'win')")
    for sel in ["#menu h1", "#result", "#foe", "#go", "#multi", "#stats", ".help", "#ai-pelit-back"]:
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    chip = page.locator("#ai-pelit-back").bounding_box()
    for sel in ["#menu h1", "#go", "#multi"]:
        assert not overlap(page.locator(sel).bounding_box(), chip), sel
    assert page.evaluate("document.scrollingElement.scrollHeight <= innerHeight")
    page.click("#go")
    page.wait_for_function("race && race.phase === 'cd'", timeout=2000)
    assert page.errors == []
    page.context.close()


def test_a_round_sideways_runs_and_survives_turning_the_phone(site, browser):
    build(site)
    page = phone(browser, 740, 360)
    page.goto(site.url + URL)
    page.click("#go")
    page.wait_for_function("race && race.phase === 'run'", timeout=6000)
    assert page.evaluate("wide && sc > 20")
    # The jump button in the lower-right corner, the panel on the left, both off the course.
    b = page.evaluate("jumpBtn()")
    assert b["x"] > 740 - 120 and b["y"] > 360 - 120 and b["x"] + b["r"] <= 740 and b["y"] + b["r"] <= 360
    side = page.evaluate("hudSide()")
    course = page.evaluate("[W / 2 - 5 * sc, W / 2 + 5 * sc]")
    assert side["left"] + side["w"] <= course[0] and b["x"] - b["r"] >= course[1]
    chip = page.locator("#ai-pelit-back").bounding_box()
    assert side["top"] >= chip["y"] + chip["height"]
    # A tap on the button jumps; the thumb runs up the course.
    page.evaluate("Object.assign(me, { x: 0, y: 2, z: 0, vx: 0, vy: 0, stun: 0 })")
    page.touchscreen.tap(b["x"], b["y"])
    page.wait_for_function("me.z > 0.3", timeout=1000)
    page.evaluate("input.y = 1")
    page.wait_for_function("me.y > 6", timeout=3000)
    page.evaluate("input.y = 0")
    at = page.evaluate("[race.round, race.clock, me.y, me.cp]")
    unfull(page)
    page.set_viewport_size({"width": 360, "height": 740})
    page.wait_for_timeout(300)
    assert page.evaluate("[!wide, race && race.phase]") == [True, "run"]
    now = page.evaluate("[race.round, race.clock, me.y, me.cp]")
    assert now[0] == at[0] and now[1] > at[1] and abs(now[2] - at[2]) < 1 and now[3] == at[3]
    unfull(page)
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert page.evaluate("wide && race.phase === 'run' && race.clock") > now[1]
    # The round ends sideways as it does upright.
    page.evaluate("finish(standings())")
    page.wait_for_timeout(100)
    assert page.evaluate("race.phase") == "done"
    assert page.errors == []
    page.context.close()
