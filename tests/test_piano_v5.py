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


# Records every note handed to the audio: [pitch, the game clock, how far ahead it was put].
# (It ends with `true`: Playwright would call a function the string evaluates to.)
SPY = "window._played = []; piano = (p, d, delay = 0) => _played.push([p, now, delay]); true"


def test_the_tune_plays_each_note_on_its_beat_without_presses(site, context):
    page = open_game(site, context)
    page.evaluate(SPY)
    played = page.evaluate("""() => {
      level = 1; startLevel(); state = 'play'; lives = 99;
      const notes = cur.notes.slice(0, 8);
      while (now < notes[7].t + 0.01) update(1 / 60);
      state = 'menu';
      return [notes.map(n => n.pitch), _played.slice(0, 8).map(([p, at, d]) => [p, at + d]), notes.map(n => n.t)];
    }""")
    pitches, sounded, beats = played
    assert [p for p, _ in sounded] == pitches
    # Each lands on its beat, give or take a millisecond.
    assert all(abs(at - t) < 0.001 for (_, at), t in zip(sounded, beats))


def test_a_press_makes_no_sound_and_a_late_press_does_not_move_the_note(site, context):
    page = open_game(site, context)
    page.evaluate(SPY)
    played = page.evaluate("""() => {
      level = 12; startLevel(); state = 'play'; lives = 99;
      const [n] = cur.notes;
      while (now < n.t + 0.1) update(1 / 60);
      const before = _played.length;
      tap(n.lane);  // 0.1 s late
      state = 'menu';
      return [n.hit, _played.length - before, _played[0][1] + _played[0][2] - n.t];
    }""")
    hit, sounds_from_press, off_beat = played
    assert hit is True and sounds_from_press == 0 and abs(off_beat) < 0.001


def test_the_next_song_plays_from_its_start_and_the_list_holds_the_tune(site, context):
    page = open_game(site, context)
    page.evaluate(SPY)
    played = page.evaluate("""() => {
      level = 1; startLevel(); state = 'play'; lives = 99;
      for (const n of cur.notes) n.hit = true;
      while (level === 1) update(1 / 30);  // song 1 to its end, then song 2 starts
      const first = cur.notes[0];
      _played.length = 0;
      // The high-score list over the game: the clock and the tune wait.
      const panel = document.createElement('div'); panel.id = 'ai-pelit-tulokset'; document.body.append(panel);
      const held = now;
      for (let i = 0; i < 300; i++) update(1 / 30);
      const whileOpen = [_played.length, now === held];
      panel.remove();
      while (now < first.t + 0.01) update(1 / 60);
      state = 'menu';
      return [whileOpen, _played[0][0] === first.pitch, Math.abs(_played[0][1] + _played[0][2] - first.t) < 0.001];
    }""")
    assert played == [[0, True], True, True]
