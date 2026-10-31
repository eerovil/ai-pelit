"""Yöajo v3 (#181 feedback): one thumb a side, steering and gas by how far each slides."""

import pytest

from conftest import ROOT, turn
from test_yoajo import BOT as BOT_V1

URL = "games/yoajo/v3/"
# v1's careful driver, on v3's pedal: full gas unless it brakes.
BOT = BOT_V1.replace("      step(1 / 60);", "      input.gas = input.brake ? 0 : 1; step(1 / 60);", 1)


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof newLeg === 'function' && mode === 'menu'")
    return page


def test_every_leg_can_still_be_driven(site, context):
    page = open_game(site, context)
    legs = page.evaluate(BOT, list(range(1, 9)))
    assert all(r["mode"] == "done" for r in legs), legs
    assert page.errors == []


def test_a_small_slide_turns_gently_and_a_long_one_sharper_than_v1(site, context):
    page = open_game(site, context)
    moved = page.evaluate("""() => { HOLD = true; const out = [];
      for (const s of [0.2, 0.5, 1]) { newLeg(1); things = []; events = []; P.v = 25; input.gas = 1; input.steer = s; const lat = P.lat;
        for (let i = 0; i < 30; i++) step(1 / 60); out.push(P.lat - lat); }
      return out; }""")
    assert 0 < moved[0] < moved[1] < moved[2], moved
    # Full steer moves more than v1's buttons did in the same half second (about 1.9 m at 90 km/h).
    assert moved[2] > 2.3, moved


def test_the_pedal_gives_as_much_gas_as_asked_and_brakes(site, context):
    page = open_game(site, context)
    v = page.evaluate("""() => { HOLD = true; const out = {};
      for (const [k, g, b] of [['none', 0, 0], ['little', 0.35, 0], ['full', 1, 0], ['brake', 0, 1]]) {
        newLeg(1); things = []; events = []; P.v = 15; input.gas = g; input.brake = b;
        for (let i = 0; i < 120; i++) { P.lat = LANE; step(1 / 60); } out[k] = P.v; }
      return out; }""")
    # Off the gas the car slows a little; a light press speeds up slowly, full gas fast; the brake stops.
    assert v["brake"] < 1 < v["none"] < 15 < v["little"] < v["full"], v


def thumb(cdp, kind, points):
    cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})


def test_the_thumbs_steer_and_press_the_gas_at_once(site, context):
    page = open_game(site, context)
    page.evaluate("newLeg(1); HOLD = true")
    cdp = page.context.new_cdp_session(page)
    left, right = {"x": 90, "y": 560, "id": 1}, {"x": 270, "y": 560, "id": 2}
    thumb(cdp, "touchStart", [left])
    thumb(cdp, "touchStart", [left, right])
    page.wait_for_function("thumbs.size === 2")
    # A thumb that lands is a light press of the gas, and no steering yet.
    assert page.evaluate("[input.steer, input.gas, input.brake]") == [0, 0.35, 0]
    # A short slide right is a gentle turn, a long one full; the gas thumb slides up for more.
    thumb(cdp, "touchMove", [dict(left, x=110), dict(right, y=520)])
    page.wait_for_function("input.steer > 0")
    gentle, gas = page.evaluate("[input.steer, input.gas]")
    assert 0 < gentle < 0.2 and 0.5 < gas < 1, (gentle, gas)
    thumb(cdp, "touchMove", [dict(left, x=250), dict(right, y=400)])
    page.wait_for_function("input.steer === 1")
    assert page.evaluate("input.gas") == 1
    # Down past where it landed, the gas thumb brakes.
    thumb(cdp, "touchMove", [dict(left, x=250), dict(right, y=650)])
    page.wait_for_function("input.brake > 0.5")
    assert page.evaluate("input.gas") == 0
    # Lifting both lets go of everything.
    thumb(cdp, "touchEnd", [])
    page.wait_for_function("thumbs.size === 0")
    assert page.evaluate("[input.steer, input.gas, input.brake]") == [0, 0, 0]
    assert page.errors == []


def test_the_lights_button_is_not_a_thumb(site, context):
    page = open_game(site, context)
    page.evaluate("newLeg(1); HOLD = true")
    b = page.evaluate("(() => { draw(); const b = btns.find(b => b.id === 'lights'); return [b.x + b.w / 2, b.y + b.h / 2]; })()")
    page.touchscreen.tap(*b)
    assert page.evaluate("[P.high, thumbs.size, input.gas]") == [True, 0, 0]
    # Above the dashboard's top line nothing starts either (the pause button and the route live there).
    page.touchscreen.tap(180, 30)
    assert page.evaluate("thumbs.size") == 0
    assert page.errors == []


@pytest.mark.parametrize("size", [{"width": 360, "height": 640}, {"width": 390, "height": 844}, {"width": 740, "height": 360}])
def test_everything_fits_on_the_screen(site, context, size):
    page = open_game(site, context)
    turn(page, size)
    page.wait_for_function(f"W === {size['width']} && H === {size['height']}")
    for setup in ["preview(1)", "newLeg(1)", "newLeg(1); P.s = leg.len; step(1 / 60)", "newLeg(1); crash('Kolari!')"]:
        boxes = page.evaluate(f"() => {{ HOLD = true; maxLeg = 8; {setup}; draw(); return btns.map(b => [b.id, b.x, b.y, b.w, b.h]); }}")
        for id_, bx, by, bw, bh in boxes:
            assert bx >= 0 and by >= 0 and bx + bw <= size["width"] + 0.5 and by + bh <= size["height"] + 0.5, (setup, id_)
    # Turning the phone mid-leg keeps the leg and a thumb's slide reads against the new size.
    page.evaluate("newLeg(1); P.s = 500; thumbs.set(9, { kind: 'steer', x0: 60, y0: H - 80, x: 60 + slide(), y: H - 80 }); setThumbs()")
    assert page.evaluate("[mode, P.s, input.steer]") == ["drive", 500, 1]
    assert page.errors == []


def test_saves_from_v2_carry_on(site, context):
    context.add_init_script("""if (!sessionStorage.seeded) { sessionStorage.seeded = 1;
      localStorage.setItem('ai-pelit:yoajo:taso', '4'); localStorage.setItem('ai-pelit:yoajo:ajettu', '3');
      localStorage.setItem('ai-pelit:yoajo:tahdet', '{"3":2}'); }""")
    page = open_game(site, context)
    assert page.evaluate("[maxLeg, driven, stars[3], level]") == [4, 3, 2, 4]
