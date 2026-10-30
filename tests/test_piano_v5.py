"""Piano v5: a press takes the oldest note in the zone, so a late press never steals the next."""

import pytest

from conftest import ROOT

URL = "games/piano/v5/"

# Play the first notes of a level, each pressed `bias` seconds off its beat, running the game's
# own clock between presses as a phone would; returns the lanes as hit (upper case) or missed.
PLAY = """([lv, bias, count]) => {
  level = lv; startLevel(); state = 'play'; lives = 99;
  const notes = cur.notes.slice(0, count);
  for (const n of notes) {
    update(n.t + bias - now);
    tap(n.lane);
  }
  update(0.5);
  state = 'menu';
  return notes.map(n => n.hit ? 'RYGB'[n.lane] : 'rygb'[n.lane]).join('');
}"""


def open_game(site, context, version="v5"):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + f"games/piano/{version}/")
    page.click("#go")
    return page


@pytest.mark.parametrize("bias", [-0.15, -0.1, 0, 0.1, 0.13, 0.15])
def test_kimalaisen_lento_every_note_hits_within_the_window(site, context, bias):
    page = open_game(site, context)
    played = page.evaluate(PLAY, [12, bias, 24])
    assert played == played.upper(), played


def test_v4_lost_notes_to_a_late_press_which_v5_fixes(site, context):
    # The bug as reported: in v4 a press 0.13 s late on Kimalaisen lento went to the next red.
    old = open_game(site, context, "v4").evaluate(PLAY, [12, 0.13, 24])
    assert old != old.upper()
    new = open_game(site, context).evaluate(PLAY, [12, 0.13, 24])
    assert new == new.upper()


def test_every_hard_song_through_with_late_presses(site, context):
    page = open_game(site, context)
    for lv in (10, 11, 12, 13):
        played = page.evaluate(PLAY, [lv, 0.14, 400])
        assert played == played.upper(), (lv, played)
        assert page.evaluate("lives") == 99, lv
