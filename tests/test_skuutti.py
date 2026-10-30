"""Skuutti in a phone-sized Chromium: pumping, airs, tricks, falls, the clock and unlocks."""

from conftest import ROOT, turn

URL = "games/skuutti/v1/"

# Rides as a good player would: a finger down while rolling down, let go in the curve on the way
# up; returns when the n-th air starts (or null). The page's own loop is stopped first, so every
# step is the test's.
RIDE = """([nAir, pumpIt]) => {
  const dt = 1 / 60; let airs = 0;
  for (let i = 0; i < 60 * 40; i++) {
    if (phase === 'ride') {
      const p = at(P.s), up = Math.sign(P.v) === Math.sign(P.s) && P.v !== 0;
      if (!up && !crouch) { crouch = true; crouchT = 0; }
      if (pumpIt && up && crouch && p.th > 0.5) pump();
    }
    const was = phase; step(dt);
    if (was === 'ride' && phase === 'air' && ++airs === nAir) return { vy: P.vy, airMax: P.airMax, t: i * dt };
    if (phase === 'air' && airs < nAir) { while (phase === 'air') step(dt); }
  }
  return null;
}"""
# Asks the tricks at the given share of the air, then flies until the landing.
AIR = """([tricks, at]) => {
  const dt = 1 / 60;
  while (phase === 'air' && P.airT < P.airMax * at) step(dt);
  const took = tricks.map(t => trick(t));
  while (phase === 'air') step(dt);
  return { took, phase, lastLand, points };
}"""


def open_game(site, context, best=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if best is not None:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('ai-pelit:skuutti:ennatys', '{best}')")
    page.goto(site.url + URL)
    page.evaluate("requestAnimationFrame = () => 0")
    page.wait_for_timeout(50)
    return page


def start(page):
    page.click("#go")
    assert page.evaluate("[phase, timeLeft, points]") == ["ride", 60, 0]


def test_the_menu_lists_the_open_and_locked_tricks_and_starts_a_run(site, context):
    page = open_game(site, context)
    assert page.inner_text("#tricks").split("\n") == [
        "↑ Barspin: pyyhkäise ylös", "↓ Tailwhip: pyyhkäise alas",
        "🔒 Takavoltti: ennätys 600 p", "🔒 Etuvoltti: ennätys 1500 p",
    ]
    assert page.locator("#colors button:not([disabled])").count() == 2
    start(page)


def test_pumping_takes_you_over_the_coping_and_rolling_alone_does_not(site, context):
    page = open_game(site, context)
    start(page)
    assert page.evaluate(RIDE, [1, False]) is None
    page.evaluate("startRun()")
    first = page.evaluate(RIDE, [1, True])
    assert first and first["t"] < 4
    # A few good pumps more and the air is as big as it gets, about a second and a half.
    later = page.evaluate(RIDE, [3, True])
    assert 1.3 < later["airMax"] < 1.6


def test_a_trick_finished_before_the_landing_scores_and_one_left_late_is_a_fall(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    r = page.evaluate(AIR, [["up", "down"], 0.2])
    assert r["took"] == [True, True] and r["phase"] == "ride"
    assert r["lastLand"]["name"] == "Barspin + Tailwhip" and r["lastLand"]["clean"]
    assert r["points"] > 300
    # A tailwhip asked just before the wheels touch is still turning: a fall, then back in.
    page.evaluate(RIDE, [1, True])
    r = page.evaluate(AIR, [["down"], 0.9])
    assert r["phase"] == "down" and r["lastLand"] == {"crash": "kesken"}
    assert page.evaluate("for (let i = 0; i < 120; i++) step(1 / 60); [phase, Math.abs(P.s) > 4]") == ["ride", True]


def test_a_rider_stopped_on_the_flat_kicks_off_again(site, context):
    page = open_game(site, context)
    start(page)
    assert page.evaluate("P.s = 0.3; P.v = 0; crouch = true; crouchT = 0.3; pump(); Math.abs(P.v)") > 2


def test_the_same_air_twice_in_a_row_pays_half(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    one = page.evaluate(AIR, [["up"], 0.2])["lastLand"]["points"]
    page.evaluate(RIDE, [1, True])
    two = page.evaluate(AIR, [["up"], 0.2])["lastLand"]["points"]
    assert two < one * 0.7


def test_flips_open_with_the_record_and_go_the_way_of_the_swipe(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    assert page.evaluate(AIR, [["left", "right"], 0.2])["took"] == [False, False]
    page = open_game(site, context, best=2000)
    start(page)
    page.evaluate(RIDE, [3, True])
    # Towards the middle of the ramp is a back flip, away from it a front flip.
    inward = "left" if page.evaluate("P.side") > 0 else "right"
    r = page.evaluate(AIR, [[inward], 0.1])
    assert r["lastLand"]["name"] == "Takavoltti" and r["lastLand"]["clean"]


def test_a_real_swipe_on_the_screen_is_a_trick(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    page.evaluate("for (let i = 0; i < 6; i++) step(1 / 60)")
    page.mouse.move(180, 400)
    page.mouse.down()
    page.mouse.move(180, 330, steps=4)
    page.mouse.up()
    assert page.evaluate("[P.barTo, P.asked]") == [1, ["bar"]]


def test_two_fingers_crouch_until_both_lift_and_a_second_finger_can_swipe(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    page.evaluate("for (let i = 0; i < 6; i++) step(1 / 60)")
    ev = "([type, id, x, y]) => c.dispatchEvent(new PointerEvent(type, { pointerId: id, clientX: x, clientY: y, bubbles: true }))"
    page.evaluate(ev, ["pointerdown", 1, 100, 500])
    page.evaluate(ev, ["pointerdown", 2, 250, 500])
    page.evaluate(ev, ["pointermove", 2, 250, 560])
    page.evaluate(ev, ["pointerup", 1, 100, 500])
    assert page.evaluate("[crouch, P.whipTo]") == [True, 1]
    page.evaluate(ev, ["pointerup", 2, 250, 560])
    assert page.evaluate("crouch") is False


def test_turning_the_phone_mid_run_keeps_the_run(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [2, True])
    before = page.evaluate("[phase, P.s, P.h, points, timeLeft]")
    turn(page, {"width": 740, "height": 360})
    assert page.evaluate("[phase, P.s, P.h, points, timeLeft]") == before
    page.wait_for_function("wide && W === 740")
    page.evaluate("draw()")


def test_time_up_ends_the_run_saves_the_record_and_opens_what_it_reached(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("points = 700; timeLeft = 0.01; step(1 / 60)")
    assert page.evaluate("phase") == "menu"
    assert page.inner_text("#result") == "Uusi ennätys! 700 p"
    assert page.inner_text("#unlocked") == "🔓 Avattu: Takavoltti, Vihreä skuutti"
    assert page.evaluate("localStorage.getItem('ai-pelit:skuutti:ennatys')") == "700"
    assert "⇥ Takavoltti" in page.inner_text("#tricks")
    assert page.inner_text("#go") == "Uudestaan"


def test_an_air_under_way_when_time_runs_out_still_lands_and_counts(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    page.evaluate("timeLeft = 0.01")
    r = page.evaluate(AIR, [["up"], 0.2])
    assert r["phase"] == "menu"
    assert page.evaluate("lastResult.points") > 0


def test_a_picked_colour_is_kept(site, context):
    page = open_game(site, context, best=400)
    page.locator("#colors button").nth(2).click()
    assert page.evaluate("localStorage.getItem('ai-pelit:skuutti:vari')") == "2"
    page.reload()
    assert page.evaluate("colorIx") == 2


def test_the_menu_fits_upright_and_sideways(site, context, browser):
    site.build(ROOT / "games")
    for w, h in [(360, 640), (390, 844), (740, 360)]:
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        page.goto(site.url + URL)
        page.evaluate("localStorage.setItem('ai-pelit:skuutti:ennatys', '700')")
        page.goto(site.url + URL)
        page.evaluate("lastResult = { points: 700, record: true, opened: ['Takavoltti', 'Vihreä skuutti'] }; showMenu()")
        box = page.locator("#go").bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= h, (w, h)
        assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight + 1"), (w, h)
        ctx.close()
