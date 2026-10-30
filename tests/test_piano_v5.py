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


def test_real_taps_reach_every_lane_on_a_390_px_phone(site, browser):
    # Through the browser's own hit testing, not straight into tap(): nothing on the page may
    # cover a lane, the red one included.
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:piano:taso', '12')")
    page.reload()
    page.click("#go")
    for lane in range(4):
        for y in ("btnTop + 40", "hitY"):  # on the key, and on the line itself
            # One note of this lane on the line; every other note out of the way.
            page.evaluate(f"""() => {{
              const n = cur.notes.filter(m => m.lane === {lane})[2];
              for (const m of cur.notes) {{ m.hit = m !== n; m.missed = false; }}
              now = n.t; window._n = n;
            }}""")
            box = page.evaluate(f"[({lane} + 0.5) * laneW, {y}]")
            page.touchscreen.tap(box[0], box[1])
            assert page.evaluate("_n.hit") is True, (lane, y)
    assert page.evaluate("lives") == 3
    ctx.close()


def test_a_skipped_note_does_not_take_the_next_press(site, context):
    page = open_game(site, context)
    played = page.evaluate("""() => {
      level = 12; startLevel(); state = 'play'; lives = 99;
      const reds = cur.notes.filter(n => n.lane === 0);
      for (const n of cur.notes) if (n.lane !== 0) n.hit = true;  // only the red lane plays
      // Leave the first red alone, then press the second red on its beat.
      update(reds[1].t - now); tap(0);
      state = 'menu';
      return [reds[0].hit, reds[0].missed, reds[1].hit, lives];
    }""")
    # The skipped red costs its one heart; the press still goes to the second red.
    assert played == [False, True, True, 98]


def test_two_lanes_pressed_together_late_on_a_fast_song(site, context):
    page = open_game(site, context)
    played = page.evaluate("""() => {
      level = 13; startLevel(); state = 'play'; lives = 99;
      const [a] = cur.notes; const b = cur.notes.find(n => n.lane !== a.lane);
      update(b.t + 0.03 - now); tap(b.lane); tap(a.lane);  // a is 0.13 s late
      state = 'menu';
      return [a.hit, b.hit, lives];
    }""")
    assert played == [True, True, 99]


def test_after_a_reload_mid_song_presses_still_land(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:piano:taso', '12')")
    page.reload()
    page.click("#go")
    played = page.evaluate(PLAY, [12, 0.13, 24])
    assert played == played.upper(), played
