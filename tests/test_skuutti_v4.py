"""Skuutti v2: recorded sounds from the shared library public/lib/aanet-2/ (#228). v2 plays as
v1 did (pumping, airs, tricks, falls, the clock and unlocks), and those tests run here too."""

from conftest import ROOT, turn

URL = "games/skuutti/v4/"
SOUNDS = ['suhahdus', 'lasku', 'onnistui', 'rima', 'voitto', 'tappio', 'rullaus']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

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
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    return page


def start(page):
    page.click("#go")
    assert page.evaluate("[phase, timeLeft, points]") == ["ride", 60, 0]


def begin(site, context, best=None):
    page = open_game(site, context, best)
    start(page)   # the tap on "Aja!" turns sound on
    page.evaluate(SPY)
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('lasku', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")
    return page


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_pumps_and_the_take_off_whoosh_and_a_clean_trick_lands_with_a_clack_and_a_chime(site, context):
    page = begin(site, context)
    page.evaluate(RIDE, [3, True])
    # The pumps and the take-offs whoosh, and the airs without a trick land with a clack only.
    assert set(played(page)) == {"suhahdus", "lasku"}
    r = page.evaluate(AIR, [["up"], 0.2])
    assert r["lastLand"]["clean"]
    assert played(page) == ["suhahdus", "lasku", "onnistui"]
    assert page.errors == []


def test_a_wobble_is_only_its_landing_and_a_fall_a_clatter(site, context):  # #337: no ooh
    page = begin(site, context)
    page.evaluate(RIDE, [3, True])
    played(page)
    # A barspin a little short at the wheels' touch: a wobble.
    page.evaluate("P.asked = ['bar']; P.barTo = 1; P.bar = 0.85; P.h = 0; P.vy = -1; land()")
    assert played(page) == ["lasku"]
    page.evaluate(RIDE, [1, True])
    played(page)
    r = page.evaluate(AIR, [["down"], 0.9])
    assert r["phase"] == "down"
    assert played(page) == ["suhahdus", "rima"]


def test_a_record_ends_with_the_win_tune_and_a_run_below_it_with_the_loss_tune(site, context):
    page = begin(site, context)
    page.evaluate("points = 700; timeLeft = 0.01; step(1 / 60)")
    assert played(page) == ["voitto"]
    page.evaluate("startRun(); points = 100; timeLeft = 0.01; step(1 / 60)")
    assert played(page) == ["tappio"]


def test_the_wheels_roll_louder_with_speed_and_go_quiet_in_the_air(site, context):
    page = begin(site, context)
    page.evaluate("P.s = 0; P.v = 3; wheelSound()")
    slow = page.evaluate("[wheels.vol, wheels.rate]")
    page.wait_for_function("wheels.playing()", timeout=5000)
    page.evaluate("P.v = 9; wheelSound()")
    fast = page.evaluate("[wheels.vol, wheels.rate]")
    assert fast[0] > slow[0] > 0 and fast[1] > slow[1]
    page.evaluate("phase = 'air'; wheelSound()")
    assert page.evaluate("wheels.vol") == 0
    page.evaluate("phase = 'menu'; wheelSound()")
    assert page.evaluate("wheels.vol") == 0


def test_without_the_library_it_still_plays_with_its_own_beeps(site, context):
    page = open_game(site, context)
    page.evaluate("AiPelitAanet.play = () => false")
    start(page)
    page.evaluate(RIDE, [3, True])
    r = page.evaluate(AIR, [["up", "down"], 0.2])
    assert r["lastLand"]["clean"] and r["points"] > 300
    assert page.errors == []


def test_after_a_run_ends_the_next_run_rolls_again_and_the_end_tune_plays_once(site, context):
    page = begin(site, context)
    page.evaluate("P.s = 0; P.v = 5; wheelSound()")
    page.wait_for_function("wheels.playing()", timeout=5000)
    # The run ends while rolling: the wheels go quiet, one tune, nothing more on later steps.
    page.evaluate("points = 0; timeLeft = 0.01; step(1 / 60); for (let i = 0; i < 30; i++) step(1 / 60); wheelSound()")
    assert played(page) == ["tappio"]
    assert page.evaluate("wheels.vol") == 0
    # Again: the same loop rolls once more, it is not started twice.
    page.evaluate("const w = wheels; startRun(); P.s = 0; P.v = 5; wheelSound(); window.same = w === wheels")
    assert page.evaluate("[same, wheels.vol > 0]") == [True, True]


# v1's play, unchanged in v2.
def test_the_menu_lists_the_open_and_locked_tricks_and_starts_a_run(site, context):
    page = open_game(site, context)
    assert page.inner_text("#tricks").split("\n") == [
        "↑ Barspin: pyyhkäise ylös", "↓ Tailwhip: pyyhkäise alas",
        "🔒 360: ennätys 600 p", "🔒 Takavoltti: ennätys 1500 p",
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


def test_the_360_and_the_back_flip_open_with_the_record_and_go_the_way_of_the_swipe(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(RIDE, [3, True])
    assert page.evaluate(AIR, [["left", "right"], 0.2])["took"] == [False, False]
    page = open_game(site, context, best=2000)
    start(page)
    # On both walls: towards the middle of the ramp is a back flip, away from it a 360.
    sides = set()
    for air in range(2):
        page.evaluate(RIDE, [3 if air == 0 else 1, True])
        side = page.evaluate("P.side")
        sides.add(side)
        inward, outward = ("left", "right") if side > 0 else ("right", "left")
        r = page.evaluate(AIR, [[inward] if air == 0 else [outward], 0.1])
        assert r["lastLand"]["name"] == ("Takavoltti" if air == 0 else "360") and r["lastLand"]["clean"], side
    assert sides == {-1, 1}


def test_a_360_and_a_back_flip_in_one_air_both_have_to_turn_all_the_way(site, context):
    page = open_game(site, context, best=2000)
    start(page)
    page.evaluate(RIDE, [3, True])
    # Asked together early, both finish: one air with two tricks.
    r = page.evaluate(AIR, [["left", "right"], 0.05])
    assert r["lastLand"]["name"] == "360 + Takavoltti" and r["lastLand"]["clean"]
    # Asked together late, neither undoes the other: the back flip is not done, so a fall.
    page.evaluate(RIDE, [1, True])
    r = page.evaluate(AIR, [["left", "right"], 0.7])
    assert r["phase"] == "down" and r["lastLand"] == {"crash": "kesken"}


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
    # Checked on a timer: after the turn this headless page drew no frame to check on (seen on main, #337).
    page.wait_for_function("wide && W === 740", polling=100)
    page.evaluate("draw()")


def test_time_up_ends_the_run_saves_the_record_and_opens_what_it_reached(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("points = 700; timeLeft = 0.01; step(1 / 60)")
    assert page.evaluate("phase") == "menu"
    assert page.inner_text("#result") == "Uusi ennätys! 700 p"
    assert page.inner_text("#unlocked") == "🔓 Avattu: 360, Vihreä skuutti"
    assert page.evaluate("localStorage.getItem('ai-pelit:skuutti:ennatys')") == "700"
    assert "↔ 360: pyyhkäise sivulle rampista ulospäin" in page.inner_text("#tricks")
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
        page.evaluate("lastResult = { points: 700, record: true, opened: ['360', 'Vihreä skuutti'] }; showMenu()")
        box = page.locator("#go").bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= h, (w, h)
        assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight + 1"), (w, h)
        ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/skuutti/v4")
