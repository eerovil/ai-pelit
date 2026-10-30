"""Trampoliini v5: plays sideways too (#95), and portrait stays as v4 drew it."""

import shutil

import pytest

from conftest import ROOT

URL = "games/trampoliini/v5/"
SIZES = [(740, 360), (844, 390), (640, 360)]


@pytest.fixture
def tramp_site(site, tmp_path):
    # Only this game is built: other games' half-done versions cannot break this test.
    games = tmp_path / "only"
    shutil.copytree(ROOT / "games" / "trampoliini", games / "trampoliini")
    site.build(games)
    return site


def open_at(browser, site, w, h, level=None, url=URL):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + url)
    if level:
        page.evaluate(f"localStorage.setItem('ai-pelit:trampoliini:taso', '{level}')")
        page.reload()
    return ctx, page


def inside(box, w, h):
    return box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


@pytest.mark.parametrize("w,h", SIZES)
def test_the_menu_and_end_screen_fit_sideways(tramp_site, browser, w, h):
    ctx, page = open_at(browser, tramp_site, w, h, level=4)
    # The end screen of a lost go: the longest menu there is (four lines of tricks, a result).
    page.evaluate("lastResult = { won: false, points: 123, level: 4 }; showMenu()")
    assert page.evaluate("[document.documentElement.scrollHeight, document.documentElement.scrollWidth]") == [h, w]
    for sel in ("#menu h1", "#result", "#level", "#tasks", "#go", "#stats", ".help"):
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    # Nothing covers the chips or the button.
    back, chip = page.locator("#ai-pelit-back").bounding_box(), page.locator("#ai-pelit-tulokset-nappi").bounding_box()
    for sel in ("#menu h1", "#go", ".help"):
        box = page.locator(sel).bounding_box()
        assert not overlap(box, back) and not overlap(box, chip), sel
    page.click("#go")
    assert page.evaluate("phase") in ("mat", "air") and page.evaluate("level") == 4
    ctx.close()


@pytest.mark.parametrize("w,h", SIZES)
def test_a_round_runs_sideways_with_the_buttons_in_the_lower_corners(tramp_site, browser, w, h):
    ctx, page = open_at(browser, tramp_site, w, h, level=5)
    page.click("#go")
    page.wait_for_timeout(400)
    assert page.evaluate("wide") is True and page.evaluate("phase") in ("mat", "air")
    y0 = page.evaluate("J.y")
    page.wait_for_timeout(300)
    assert page.evaluate("J.y") != y0   # still bouncing
    boxes = page.evaluate("""() => [...document.querySelectorAll('#pad button')].map(b => {
      const r = b.getBoundingClientRect(); return { act: b.dataset.act, x: r.x, y: r.y, width: r.width, height: r.height }; })""")
    assert len(boxes) == 4
    for b in boxes:
        assert inside(b, w, h) and b["height"] >= 48, b
        assert b["y"] > h / 2, b                        # the lower half, where thumbs rest
        assert b["x"] + b["width"] < w * 0.25 or b["x"] > w * 0.75, b   # at the sides
    left = sorted(b["act"] for b in boxes if b["x"] < w / 2)
    right = sorted(b["act"] for b in boxes if b["x"] > w / 2)
    assert left == ["kierre", "taakse"] and right == ["eteen", "kierre"]
    # The trampoline and the highest bounce stay clear of the buttons and the HUD.
    S, ground, mat_y, cx, half, apex, hud_bottom, jmin = page.evaluate("""() => { const v = view();
      return [v.S, v.ground, v.matY, v.cx, T.half * v.S, COMH + T.vMax * T.vMax / (2 * G), hud().bottom, JMIN]; }""")
    for b in boxes:
        assert cx - half - 0.35 * S > b["x"] + b["width"] or cx + half + 0.35 * S < b["x"], b
    s = max(jmin, min(S, 100))
    assert mat_y - apex * S - (s - S) * 0.95 - 0.81 * s >= hud_bottom
    # The middle of the screen is still the mat: a finger there bends the knees.
    page.touchscreen.tap(w / 2, h / 2)
    assert page.evaluate("kick > 0 || squat")
    # Both 🌀 buttons twist, and the flip buttons flip.
    page.locator("#pad button.side").dispatch_event("pointerdown", {"pointerId": 7})
    assert page.evaluate("twistHeld") is True
    page.locator("#pad button.side").dispatch_event("pointerup", {"pointerId": 7})
    assert page.evaluate("twistHeld") is False
    page.locator("#pad button[data-act=eteen]").dispatch_event("pointerdown", {"pointerId": 8})
    assert page.evaluate("held") == -1
    page.locator("#pad button[data-act=eteen]").dispatch_event("pointerup", {"pointerId": 8})
    ctx.close()


def test_turning_the_phone_mid_round_keeps_the_round(tramp_site, browser):
    ctx, page = open_at(browser, tramp_site, 360, 740, level=2)
    page.click("#go")
    page.wait_for_timeout(300)
    # Some of the go done: a trick, a heart lost.
    page.evaluate("tasks[0].done = true; points = 47; hearts = 2; combo = 1")
    page.evaluate("document.fullscreenElement && document.exitFullscreen()")
    page.wait_for_timeout(200)
    for w, h, wide in ((740, 360, True), (360, 740, False), (844, 390, True)):
        page.set_viewport_size({"width": w, "height": h})
        page.wait_for_timeout(300)
        assert page.evaluate("[innerWidth, wide]") == [w, wide]
        assert page.evaluate("[phase !== 'menu', level, points, hearts, tasks[0].done, tasks[1].done]") == [True, 2, 47, 2, True, False]
        assert page.evaluate("document.getElementById('menu').classList.contains('hidden')")
        y0 = page.evaluate("J.y")
        page.wait_for_timeout(250)
        assert page.evaluate("J.y") != y0
    ctx.close()


@pytest.mark.parametrize("w,h", [(360, 740), (360, 640)])
def test_portrait_looks_as_v4(tramp_site, browser, w, h):
    shots = []
    for url in ("games/trampoliini/v4/", URL):
        ctx, page = open_at(browser, tramp_site, w, h, url=url)
        page.wait_for_timeout(200)
        menu = page.screenshot()
        page.click("#go")
        page.evaluate("step = () => {}; phase = 'air'; J.y = 3; J.a = 1; pops = []")
        page.wait_for_timeout(150)
        shots.append((menu, page.screenshot()))
        if url == URL:
            assert page.evaluate("wide") is False
            assert not page.locator("#pad button.side").is_visible()
        ctx.close()
    assert shots[0][0] == shots[1][0], "menu"
    assert shots[0][1] == shots[1][1], "play"
