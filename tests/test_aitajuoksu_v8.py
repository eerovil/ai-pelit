"""Aitajuoksu v8: the jump is a bar above the feet, as in Pituushyppy, and the gap under it is the feet (#308)."""

import pytest

from conftest import turn
from test_aitajuoksu_v4 import open_game, start_running

URL = "games/aitajuoksu/v8/"


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844)])
def test_upright_the_jump_is_a_bar_above_the_feet_and_the_gap_is_the_feet(site, browser, size):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx, URL)
    start_running(page)
    jump, left, right = page.evaluate("pads()")
    assert [jump["k"], left["k"], right["k"]] == [3, 1, 2]
    # The bar spans the screen above the two feet, side by side.
    assert jump["w"] > size[0] - 20 and left["y"] == right["y"] and left["x"] < right["x"]
    bottom = jump["y"] + jump["h"]
    assert left["y"] - bottom >= 40 and left["h"] >= 80
    assert left["y"] + left["h"] <= size[1]
    # Four lanes still have room on the track above the controls.
    assert page.evaluate("laneH") >= 50
    # A thumb drumming the feet that lands short of them, in the gap or on the jump's bottom edge, is a step.
    for y in (left["y"] - 2, bottom + 20, bottom + 2, bottom - 8):
        assert page.evaluate(f"[padAt(60, {y}), padAt(300, {y})]") == [1, 2], y
    # The bar itself, and the track above it, still jump.
    assert page.evaluate(f"[padAt(180, {jump['y'] + 10}), padAt(180, {bottom - 14}), padAt(180, {jump['y'] - 40})]") == [3, 3, 3]
    # Real taps: the feet run, the bar jumps.
    cy = left["y"] + left["h"] / 2
    page.mouse.click(left["x"] + left["w"] / 2, cy)
    page.mouse.click(right["x"] + right["w"] / 2, cy)
    assert page.evaluate("me.v") > 0
    page.mouse.click(180, jump["y"] + jump["h"] / 2)
    assert page.evaluate("me.y > 0 || me.vy > 0")
    assert page.errors == []
    ctx.close()


def test_sideways_the_gap_under_each_jump_pad_is_that_sides_foot(site, browser):
    ctx = browser.new_context(viewport={"width": 740, "height": 360}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx, URL)
    start_running(page)
    page.wait_for_function("land")
    pl = page.evaluate("pads()")
    assert [p["k"] for p in pl] == [3, 1, 3, 2]
    for top, foot in ((pl[0], pl[1]), (pl[2], pl[3])):
        cx = top["x"] + top["w"] / 2
        bottom = top["y"] + top["h"]
        assert foot["y"] - bottom >= 40
        assert page.evaluate(f"[padAt({cx}, {bottom - 8}), padAt({cx}, {bottom + 20}), padAt({cx}, {foot['y'] + 20})]") == [foot["k"]] * 3
        assert page.evaluate(f"[padAt({cx}, {top['y'] + 10}), padAt({cx}, {bottom - 14})]") == [3, 3]
    assert page.evaluate("padAt(370, 200)") == 3
    # Turned upright mid-race, the bar is above the feet and the gap is the feet's again.
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    assert page.evaluate("race.phase") == "run"
    jump, left, right = page.evaluate("pads()")
    gap = jump["y"] + jump["h"] + 20
    assert page.evaluate(f"[padAt(60, {gap}), padAt(300, {gap})]") == [1, 2]
    assert page.errors == []
    ctx.close()

