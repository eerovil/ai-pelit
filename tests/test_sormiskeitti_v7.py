"""Sormiskeitti v7: recorded sounds from the shared library public/lib/aanet-2/ (#229)."""

import pytest

from conftest import ROOT

URL = "games/sormiskeitti/v7/"
SOUNDS = ['pop', 'lasku', 'puu', 'onnistui', 'voitto', 'tappio', 'rullaus']

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Plays one round synchronously through the game's own step(), so the result does not hang on
# frame timing. `push` is frames between pushes; `trick` adds a late ollie and a let-go at the top.
PLAY = """([push, trick]) => {
  reset(); tap();
  for (let f = 1; f < 5000 && st !== 'end'; f++) {
    if (st === 'roll' && s < L && f % push === 0) tap();
    if (trick && st === 'roll' && s > L && !ollie && theta() > 1.43) tap();
    if (trick && st === 'air' && !letGo && Math.abs(avy) <= 0.6) tap();
    step();
  }
  return { won, level, best };
}"""

# One round through step(), like PLAY, but the ollie is tapped at a chosen angle and there is no
# let-go at the top: level 1's ceiling is in reach, level 30's far above it.
ROUND = """([level_, th]) => {
  won = false; level = level_; reset(); tap();
  for (let f = 1; f < 5000 && st !== 'end'; f++) {
    if (st === 'roll' && s < L && f % 6 === 0) tap();
    if (th !== null && st === 'roll' && s > L && !ollie && theta() > th) tap();
    if (st === 'air' && !letGo && Math.abs(avy) <= 0.6) tap();
    step();
  }
  return { won, bonk, ollie };
}"""


def start(site, context, ready=True):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_selector("#ai-pelit-back")
    page.evaluate(SPY)
    if ready:
        page.mouse.click(180, 400)  # the tap that turns sound on (and starts the round)
        page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('pop', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")
    return page


def saved(page):
    return page.evaluate("({ level, best })")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_won_round_pops_bonks_the_ceiling_lands_and_wins(site, context):
    page = start(site, context)
    r = page.evaluate(ROUND, [1, 1.43])
    assert r["won"] and r["bonk"] and r["ollie"] == 1.3
    assert played(page) == ["pop", "onnistui", "puu", "lasku", "voitto"]
    assert page.errors == []


def test_a_short_round_with_a_weaker_ollie_lands_and_loses(site, context):
    page = start(site, context)
    r = page.evaluate(ROUND, [30, 1.15])
    assert not r["won"] and r["ollie"] == 1.15
    assert played(page) == ["pop", "lasku", "tappio"]


def test_a_late_ollie_just_after_the_lip_still_pops_and_counts_as_perfect(site, context):
    page = start(site, context)
    page.evaluate("""() => {
      won = false; level = 30; reset(); tap();
      for (let f = 1; f < 5000 && st !== 'air'; f++) { if (st === 'roll' && s < L && f % 6 === 0) tap(); step(); }
      step(); step(); tap();
    }""")
    assert page.evaluate("ollie") == 1.3
    assert played(page) == ["pop", "onnistui"]


def test_rolling_back_down_is_only_the_loss_tune(site, context):
    page = start(site, context)
    # Too slow for the lip: up the ramp a little and back down, no air.
    page.evaluate("won = false; reset(); tap(); s = L + 10; v = 2; for (let f = 0; f < 5000 && st !== 'end'; f++) step()")
    assert page.evaluate("st") == "end"
    assert played(page) == ["tappio"]


def test_the_wheels_roll_with_the_speed_and_stop_in_the_air(site, context):
    page = start(site, context)
    page.evaluate("won = false; level = 30; reset(); tap(); step()")
    assert page.evaluate("wheels.name") == "rullaus"
    page.evaluate("v = 4; step()")
    slow = page.evaluate("[wheels.vol, wheels.rate]")
    page.evaluate("v = 15; step()")
    fast = page.evaluate("[wheels.vol, wheels.rate]")
    assert 0 < slow[0] < fast[0] and slow[1] < fast[1]
    page.evaluate("st = 'air'; avy = 5; ay = LIP_Y + 10; airF = 20; step()")
    assert page.evaluate("wheels.vol") == 0
    page.wait_for_function("wheels.playing()", timeout=5000)
    assert page.errors == []


def test_without_the_sound_files_it_plays_as_before(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = start(site, ctx, ready=False)
        page.mouse.click(180, 400)
        won = page.evaluate(PLAY, [6, True])
        assert won["won"]
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v6_saves_are_read_as_they_are(site, context):
    page = start(site, context, ready=False)
    page.evaluate("localStorage.setItem('ai-pelit:sormiskeitti:level', '4'); localStorage.setItem('ai-pelit:sormiskeitti:best', '321')")
    page.reload()
    assert saved(page) == {"level": 4, "best": 321}
    assert page.errors == []
