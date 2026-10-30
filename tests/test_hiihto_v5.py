"""Hiihto v5 (#61): picking a wax never opens the friends game by mistake."""

import pytest

from conftest import ROOT

URL = "games/hiihto/v5/"


def open_game(site, browser, w, h):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    return page


ROOM_OPEN = "!!document.getElementById('aipr') && !document.getElementById('aipr').hidden"


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844), (412, 915)])
def test_the_friends_button_is_clear_of_the_waxes(site, browser, w, h):
    page = open_game(site, browser, w, h)
    for lv, st in [(1, 0), (3, 2)]:
        gap = page.evaluate(f"maxLevel = 3; level = {lv}; stars[{lv}] = {st}; newRace(); draw();"
                            "ui.friends.y - Math.max(...ui.wax.map(r => r.y + r.h))")
        assert gap >= 24, (lv, gap)
    page.context.close()


def test_a_tap_at_the_bottom_of_a_wax_starts_the_race_alone(site, browser):
    page = open_game(site, browser, 390, 844)
    # A finger landing at the very bottom edge of the lower-right wax, as a thumb does.
    page.evaluate("draw(); const r = ui.wax[3]; down(1, r.x + r.w / 2, r.y + r.h - 1); up(1, r.x + r.w / 2, r.y + r.h - 1)")
    assert page.evaluate("[mode, net === null]") == ["count", True]
    assert page.evaluate(ROOM_OPEN) is False
    page.context.close()


def test_the_friends_button_opens_on_a_finished_tap(site, browser):
    page = open_game(site, browser, 390, 844)
    page.evaluate("draw()")
    b = page.evaluate("ui.friends")
    cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    # A finger that lands on it but slides off before lifting does nothing.
    page.evaluate("([x, y]) => down(2, x, y)", [cx, cy])
    assert page.evaluate(ROOM_OPEN) is False
    page.evaluate("([x, y]) => up(2, x, y - 120)", [cx, cy])
    assert page.evaluate(ROOM_OPEN) is False and page.evaluate("mode") == "wax"
    # Down and up on it opens the friends screen.
    page.evaluate("([x, y]) => { down(3, x, y); up(3, x, y); }", [cx, cy])
    assert page.evaluate(ROOM_OPEN) is True
    assert page.errors == []
    page.context.close()


def test_a_real_tap_on_each_wax_starts_the_race(site, browser):
    # Through the page's own touch events, as on a phone.
    for i in range(4):
        page = open_game(site, browser, 360, 640)
        r = page.evaluate(f"draw(), ui.wax[{i}]")
        page.touchscreen.tap(r["x"] + r["w"] / 2, r["y"] + r["h"] - 2)
        page.wait_for_function("mode === 'count'", timeout=2000)
        assert page.evaluate(ROOM_OPEN) is False
        page.context.close()


def test_two_fingers_a_wax_wins(site, browser):
    # One finger rests on the friends button while another taps a wax: the race starts, and
    # lifting the first finger afterwards does not open the friends screen.
    page = open_game(site, browser, 390, 844)
    page.evaluate("draw()")
    b = page.evaluate("ui.friends")
    cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    page.evaluate("([x, y]) => down(4, x, y)", [cx, cy])
    page.evaluate("const r = ui.wax[1]; down(5, r.x + 5, r.y + 5); up(5, r.x + 5, r.y + 5)")
    page.evaluate("([x, y]) => up(4, x, y)", [cx, cy])
    assert page.evaluate("[mode, net === null]") == ["count", True]
    assert page.evaluate(ROOM_OPEN) is False
    page.context.close()
