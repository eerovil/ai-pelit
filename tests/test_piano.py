"""Piano in a phone-sized Chromium."""

from conftest import ROOT

URL = "games/piano/v1/"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    return page


def test_every_song_uses_all_four_lanes(site, context):
    page = start(site, context)
    lanes = page.evaluate("SONGS.map((s, i) => [...new Set(levelNotes(i + 1).notes.map(n => n.lane))].sort())")
    assert lanes == [[0, 1, 2, 3]] * 4


def test_a_tap_on_time_scores_and_plays_the_note(site, context):
    page = start(site, context)
    page.evaluate("state = 'menu'")  # hold the clock still
    page.evaluate("const n = cur.notes[0]; now = n.t + 0.02; state = 'play'; tap(n.lane); state = 'menu'")
    assert page.evaluate("[cur.notes[0].hit, score, combo, lives]") == [True, 100, 1, 3]


def test_a_tap_in_an_empty_lane_costs_a_heart(site, context):
    page = start(site, context)
    page.evaluate("state = 'menu'")
    page.evaluate("const n = cur.notes[0]; now = n.t; state = 'play'; tap((n.lane + 1) % 4); state = 'menu'")
    assert page.evaluate("[cur.notes[0].hit, combo, lives]") == [False, 0, 2]


def test_notes_that_fall_past_the_line_end_the_game_and_save_the_record(site, context):
    page = start(site, context)
    page.evaluate("score = 1234; now = cur.notes[2].t + 0.5; update(0.01)")
    assert page.evaluate("state") == "over"
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:ennatys')") == "1234"
    assert "1234 pistettä" in page.inner_text("#result")


def test_a_finished_song_moves_on_to_a_faster_one(site, context):
    page = start(site, context)
    page.evaluate("for (const n of cur.notes) n.hit = true; now = cur.end + 1; update(0.01)")
    assert page.evaluate("[level, cur.song.name, lives]") == [2, "Ukko Nooa", 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:taso')") == "2"
    page.reload()
    assert "paras taso 2" in page.inner_text("#stats")
