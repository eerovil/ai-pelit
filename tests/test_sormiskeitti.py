"""Sormiskeitti in a phone-sized Chromium: saved progress (v3 on) and the late-ollie grace (v4)."""

import pytest

from conftest import ROOT

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


def saved(page):
    return page.evaluate("({ level, best })")


@pytest.mark.parametrize("version", ["v3", "v4", "v5"])
def test_sormiskeitti_keeps_the_level_and_record_after_a_reload(site, context, version):
    site.build(ROOT / "games")
    page = context.new_page()
    url = f"{site.url}games/sormiskeitti/{version}/"
    page.goto(url)
    assert saved(page) == {"level": 1, "best": 0}

    # A lost round with some height: the record is saved, the level is not.
    lost = page.evaluate(PLAY, [30, False])
    assert not lost["won"] and lost["best"] > 0
    page.reload()
    assert saved(page) == {"level": 1, "best": lost["best"]}

    # A won round: a reload opens the next level with the new record.
    won = page.evaluate(PLAY, [6, True])
    assert won["won"] and won["best"] > lost["best"]
    page.reload()
    assert saved(page) == {"level": 2, "best": won["best"]}


# Pushes to the lip with no ollie on the ramp, then taps `late` frames after the lip
# (or never, with null) and flies without a let-go, under a ceiling too high to reach.
LATE = """(late) => {
  won = false; level = 30; reset(); tap();
  for (let f = 1; f < 5000 && st !== 'end'; f++) {
    if (st === 'roll' && s < L && f % 6 === 0) tap();
    if (late !== null && st === 'air' && airF === late && !ollie) tap();
    step();
  }
  return { ollie, maxH, letGo: !!letGo };
}"""


def test_sormiskeitti_v4_counts_a_tap_just_after_the_lip_as_a_perfect_ollie(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/sormiskeitti/v4/")
    at_lip = page.evaluate(LATE, 0)
    assert at_lip["ollie"] == 1.3 and not at_lip["letGo"]
    for late in (1, 4, 7):
        r = page.evaluate(LATE, late)
        # The same flight as an ollie right at the lip, not a let-go.
        assert r["ollie"] == 1.3 and not r["letGo"]
        assert r["maxH"] == pytest.approx(at_lip["maxH"], abs=0.01)
    # Past the grace the tap is the mid-air let-go, as before.
    too_late = page.evaluate(LATE, 8)
    assert too_late["ollie"] == 0 and too_late["letGo"]
    assert page.evaluate(LATE, None)["maxH"] < at_lip["maxH"]
