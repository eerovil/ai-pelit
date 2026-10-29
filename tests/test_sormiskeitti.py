"""Sormiskeitti in a phone-sized Chromium: the level and record survive closing the game (v3)."""

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


def test_sormiskeitti_keeps_the_level_and_record_after_a_reload(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    url = f"{site.url}games/sormiskeitti/v3/"
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
