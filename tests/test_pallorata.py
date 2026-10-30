"""Pallorata, the 3D ball run on the shared three.js (#102), in a phone-sized Chromium."""

import pytest

from conftest import ROOT, wait_for_worker

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


def test_a_drag_steers_only_while_the_ball_is_on_the_track(site, context):
    page, _ = open_game(site, context)
    page.evaluate("steer(200)")
    assert page.evaluate("ball.aimX") == 0
    page.click("#aloita")
    page.wait_for_function("round.phase === 'run'", timeout=2000)
    page.evaluate("ball.aimX = 5")
    page.wait_for_function("round.phase === 'fall'", timeout=2000)
    page.evaluate("steer(-400)")
    assert page.evaluate("ball.aimX") == 5


def test_it_plays_on_a_390_px_phone(site, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    try:
        page, errors = start(site, ctx)
        page.wait_for_function("-ball.z > 4 && innerWidth === 390", timeout=5000)
        box = page.locator("#hud").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390
        assert errors == []
    finally:
        ctx.close()


FIRST_RAMP = "(() => { for (let i = 10; i < 3000; i++) if (row(i).kind === 'ramp') return i; })()"


def test_a_ramp_throws_the_ball_over_the_gap(site, context):
    page, _ = start(site, context)
    ramp = page.evaluate(FIRST_RAMP)
    gaps = page.evaluate(f"[1, 2].filter(n => row({ramp} + n).kind === 'gap').length")
    assert gaps >= 1
    page.evaluate(f"ball.z = -{ramp} * 2 + 1; ball.x = ball.aimX = row({ramp}).cx")
    page.wait_for_function("ball.air && ball.y > 1.2", timeout=3000)
    landing = (ramp + gaps + 2) * 2
    page.wait_for_function(f"-ball.z > {landing} && !ball.air", timeout=5000)
    assert page.evaluate("round.phase") == "run"


def test_rolling_into_a_gap_without_a_jump_drops_the_ball(site, context):
    page, _ = start(site, context)
    ramp = page.evaluate(FIRST_RAMP)
    page.evaluate(f"ball.z = -({ramp} + 1.1) * 2; ball.x = ball.aimX = row({ramp}).cx; ball.ramp = false")
    page.wait_for_function("round.phase === 'fall'", timeout=2000)


def keep_on_the_track(page):
    page.evaluate("setInterval(() => { ball.aimX = row(Math.floor(-ball.z / 2)).cx; }, 16)")


FIRST_TURBO = "(() => { for (let i = 10; i < 3000; i++) if (row(i).kind === 'boost') return i; })()"


def test_a_turbo_strip_speeds_the_ball_up_for_a_while(site, context):
    page, _ = start(site, context)
    turbo = page.evaluate(FIRST_TURBO)
    # No ramp right after a turbo, so the faster jump cannot overshoot its landing.
    assert page.evaluate(f"[...Array(35).keys()].every(n => row({turbo} + n).kind !== 'ramp')")
    page.evaluate(f"ball.z = -{turbo} * 2 + 1; ball.x = ball.aimX = row({turbo}).cx")
    page.wait_for_function("ball.boost > 0", timeout=3000)
    keep_on_the_track(page)
    assert page.is_visible("#vauhti")
    page.wait_for_function("ball.v > 12", timeout=3000)
    page.wait_for_function("ball.boost === 0 && ball.rush < 1", timeout=6000)
    assert not page.is_visible("#vauhti")


def test_a_sliding_block_bumps_the_ball_aside_and_slows_it(site, context):
    page, _ = start(site, context)
    i = page.evaluate("(() => { for (let i = 121; i < 3000; i++) { row(i); if (blocks.length) return blocks[0].i; } })()")
    page.evaluate(f"""() => {{
        const b = blocks[0]; b.sp = 0; b.ph = 0;  // parked in the middle of its row
        ball.z = -{i} * 2 + 0.5; ball.x = ball.aimX = row({i}).cx;
    }}""")
    page.wait_for_function("blocks[0].hit", timeout=3000)
    assert page.evaluate("ball.rush < 0 && Math.abs(ball.aimX - blocks[0].mesh.position.x) > 1")


def test_the_sky_turns_to_sunset_further_on(site, context):
    page, _ = start(site, context)
    day = page.evaluate("document.querySelector('canvas') && window.round.zone")
    assert day == 0
    keep_on_the_track(page)
    page.evaluate("ball.z = -301")
    page.wait_for_function("round.zone === 1", timeout=3000)
    assert page.text_content("#toast") == "Auringonlasku"


def test_the_distance_stops_counting_when_the_ball_leaves_the_track(site, context):
    page, _ = start(site, context)
    page.wait_for_function("-ball.z > 4", timeout=5000)
    page.evaluate("ball.aimX = 5")
    page.wait_for_function("round.phase === 'fall'", timeout=2000)
    left = page.evaluate("Math.floor(-round.endZ)")
    page.wait_for_function("round.phase === 'over'", timeout=4000)
    # The ball flew on while falling, but the score counts only where it left the track.
    assert page.evaluate("-ball.z") > left + 3
    assert page.text_content("#tulos").startswith(f"{left} m ")
    assert page.evaluate("+localStorage.getItem('ai-pelit:pallorata:ennatys')") == left + 10 * page.evaluate("round.stars")


def test_it_plays_offline_from_the_phones_cache(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url)
    wait_for_worker(page)
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=15000)
    if page.evaluate("window.noWebgl === true"):
        pytest.skip("this Chromium has no WebGL")
    context.set_offline(True)
    try:
        page.reload()
        page.wait_for_function("window.drawn === true", timeout=15000)
        page.click("#aloita")
        page.wait_for_function("round.phase === 'run' && -ball.z > 4", timeout=5000)
    finally:
        context.set_offline(False)
    assert errors == []
