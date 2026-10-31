"""Pituushyppy v4: the jump bar sits higher, and the gap under it belongs to the feet (#177)."""

import pytest
from conftest import turn
from test_pituushyppy_v2 import open_game

import test_pituushyppy_v2 as v2


@pytest.fixture(autouse=True)
def v4(monkeypatch):
    monkeypatch.setattr(v2, "URL", "games/pituushyppy/v4/")


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844)])
def test_upright_the_jump_is_well_above_the_feet_and_the_gap_is_the_feet(site, context, size):
    page = open_game(site, context)
    turn(page, {"width": size[0], "height": size[1]})
    page.click("#go")
    jump, left, right = page.evaluate("pads()")
    assert [jump["k"], left["k"], right["k"]] == [3, 1, 2]
    bottom = jump["y"] + jump["h"]
    assert left["y"] - bottom >= 40 and left["h"] >= 80
    # A thumb drumming the feet that lands short of them, in the gap or on the jump's bottom edge, is a step.
    for y in (left["y"] - 2, bottom + 20, bottom + 2, bottom - 8):
        assert page.evaluate(f"[padAt(60, {y}), padAt(300, {y})]") == [1, 2], y
    # The jump bar itself, and the scene above it, still jump.
    assert page.evaluate(f"[padAt(180, {jump['y'] + 10}), padAt(180, {bottom - 14}), padAt(180, {jump['y'] - 40})]") == [3, 3, 3]
    assert page.errors == []


def test_sideways_the_gap_under_each_jump_pad_is_that_sides_foot(site, context):
    page = open_game(site, context)
    turn(page, {"width": 740, "height": 360})
    page.click("#go")
    page.wait_for_function("land")
    pl = page.evaluate("pads()")
    for top, foot in ((pl[0], pl[1]), (pl[2], pl[3])):
        cx = top["x"] + top["w"] / 2
        bottom = top["y"] + top["h"]
        assert foot["y"] - bottom >= 40
        assert page.evaluate(f"[padAt({cx}, {bottom - 8}), padAt({cx}, {bottom + 20}), padAt({cx}, {foot['y'] + 20})]") == [foot["k"]] * 3
        assert page.evaluate(f"[padAt({cx}, {top['y'] + 10}), padAt({cx}, {bottom - 14})]") == [3, 3]
    assert page.evaluate("padAt(370, 200)") == 3
    assert page.errors == []
