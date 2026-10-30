"""Pallorata, the 3D ball run on the shared three.js (#102), in a phone-sized Chromium."""

import pytest

from conftest import ROOT

URL = "games/pallorata/v1/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    # Headless Chromium draws WebGL in software (SwiftShader); without it the page says so instead.
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    return page, errors


def start(site, context):
    page, errors = open_game(site, context)
    page.click("#aloita")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    return page, errors


def test_the_ball_rolls_on_a_wide_straight_start(site, context):
    page, errors = start(site, context)
    assert page.evaluate("[0, 5, 9].map(i => [row(i).cx, row(i).w])") == [[0, 3.2]] * 3
    page.wait_for_function("-ball.z > 8", timeout=5000)
    assert page.evaluate("round.phase") == "run"
    assert page.text_content("#matka").endswith(" m")
    assert errors == []


def test_dragging_a_finger_moves_the_ball_sideways(site, context):
    page, _ = start(site, context)
    page.mouse.move(180, 500)
    page.mouse.down()
    page.mouse.move(240, 500, steps=5)
    page.mouse.up()
    page.wait_for_function("ball.x > 0.5", timeout=2000)
    page.mouse.move(240, 500)
    page.mouse.down()
    page.mouse.move(120, 500, steps=5)
    page.mouse.up()
    page.wait_for_function("ball.x < -0.5", timeout=2000)


def test_a_star_on_the_way_is_collected(site, context):
    page, _ = start(site, context)
    page.evaluate("const s = stars[0]; s.position.x = ball.x; s.position.z = ball.z - 1.5")
    page.wait_for_function("round.stars === 1", timeout=3000)
    assert page.text_content("#tahdet") == "⭐ 1"


def test_rolling_off_the_track_ends_the_round_and_saves_the_record(site, context):
    page, _ = start(site, context)
    page.wait_for_function("-ball.z > 4", timeout=5000)
    page.evaluate("round.stars = 2; ball.aimX = 5")
    page.wait_for_function("round.phase === 'fall'", timeout=2000)
    page.wait_for_function("round.phase === 'over'", timeout=4000)
    assert page.is_visible("#loppu")
    best = page.evaluate("+localStorage.getItem('ai-pelit:pallorata:ennatys')")
    assert best >= 20
    assert f"= {best} pistettä" in page.text_content("#tulos")
    page.click("#uudestaan")
    page.wait_for_function("round.phase === 'run' && round.stars === 0 && ball.z > -2", timeout=2000)
    assert not page.is_visible("#loppu")
