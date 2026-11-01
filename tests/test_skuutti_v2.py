"""Skuutti v2: recorded sounds from the shared library public/lib/aanet-2/ (#228)."""

import pytest

import test_skuutti as v1
from test_skuutti import AIR, RIDE
# v2 plays as v1 did: every v1 test runs again here, on v2 (the fixture below points them at it).
from test_skuutti import *  # noqa: F401,F403

URL = "games/skuutti/v2/"
SOUNDS = ['suhahdus', 'lasku', 'onnistui', 'ohhoo', 'rima', 'voitto', 'tappio', 'rullaus']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


@pytest.fixture(autouse=True)
def v2_url():
    old = v1.URL
    v1.URL = URL
    yield
    v1.URL = old


def open_game(site, context, best=None):
    page = v1.open_game(site, context, best)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    return page


def begin(site, context, best=None):
    page = open_game(site, context, best)
    v1.start(page)   # the tap on "Aja!" turns sound on
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


def test_a_wobble_is_an_ooh_and_a_fall_a_clatter(site, context):
    page = begin(site, context)
    page.evaluate(RIDE, [3, True])
    played(page)
    # A barspin a little short at the wheels' touch: a wobble.
    page.evaluate("P.asked = ['bar']; P.barTo = 1; P.bar = 0.85; P.h = 0; P.vy = -1; land()")
    assert played(page) == ["lasku", "ohhoo"]
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
    v1.start(page)
    page.evaluate(RIDE, [3, True])
    r = page.evaluate(AIR, [["up", "down"], 0.2])
    assert r["lastLand"]["clean"] and r["points"] > 300
    assert page.errors == []
