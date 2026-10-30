"""Piano v3: go on from the furthest level reached, three fresh hearts a level, hard songs."""

from conftest import ROOT

URL = "games/piano/v3/"


def open_game(site, context, saves=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    if saves:
        for k, v in saves.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:piano:{k}', '{v}')")
        page.reload()
    return page


def test_thirteen_songs_on_all_four_lanes_and_playable_gaps(site, context):
    page = open_game(site, context)
    assert page.evaluate("SONGS.length") == 13
    lanes = page.evaluate("SONGS.map((s, i) => [...new Set(levelNotes(i + 1).notes.map(n => n.lane))].sort())")
    assert lanes == [[0, 1, 2, 3]] * 13
    # The first time round even the fastest song leaves 0.09 s between notes.
    gaps = page.evaluate("SONGS.map((s, i) => { const n = levelNotes(i + 1).notes; let g = 9; for (let k = 1; k < n.length; k++) g = Math.min(g, n[k].t - n[k - 1].t); return g; })")
    assert min(gaps) >= 0.09
    assert page.evaluate("[speedOf(1), speedOf(13), speedOf(14)]") == [1, 1, 1.15]


def test_every_level_starts_with_three_fresh_hearts(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("lives = 1; for (const n of cur.notes) n.hit = true; now = cur.end + 1; update(0.01)")
    assert page.evaluate("[level, lives]") == [2, 3]


def test_after_a_game_over_it_goes_on_from_the_level_reached(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("level = 4; startLevel(); lives = 1; now = cur.notes[0].t + 0.5; update(0.01)")
    assert page.evaluate("state") == "over"
    assert page.inner_text("#go") == "Jatka tasolta 4"
    assert "Taso 4 · Piippolan vaari" in page.inner_text("#pick")
    page.click("#go")
    assert page.evaluate("[state, level, lives, score]") == ["play", 4, 3, 0]


def test_an_earlier_level_can_be_picked(site, context):
    page = open_game(site, context, {"taso": 11, "ennatys": 5000})
    assert page.inner_text("#go") == "Jatka tasolta 11"
    assert page.is_disabled("#next")
    page.click("#prev")
    page.click("#prev")
    assert page.inner_text("#go") == "Soita tasolta 9"
    page.click("#go")
    assert page.evaluate("[level, cur.song.name]") == [9, "Kulkuset"]


def test_a_first_game_has_no_picker(site, context):
    page = open_game(site, context)
    assert not page.is_visible("#pickrow")
    assert page.inner_text("#go") == "Soita!"


def test_progress_survives_a_reload_mid_game(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("for (let i = 0; i < 2; i++) { for (const n of cur.notes) n.hit = true; now = cur.end + 1; update(0.01); }")
    assert page.evaluate("level") == 3
    page.reload()
    assert page.inner_text("#go") == "Jatka tasolta 3"
    page.click("#go")
    assert page.evaluate("[level, lives]") == [3, 3]


def test_two_lanes_at_once_on_a_fast_song(site, context):
    page = open_game(site, context, {"taso": 13})
    page.click("#go")
    # Two thumbs: the two notes nearest the line in different lanes, pressed in the same frame.
    page.evaluate("""() => {
      const [a] = cur.notes; const b = cur.notes.find(n => n.lane !== a.lane);
      now = (a.t + b.t) / 2; tap(a.lane); tap(b.lane);
    }""")
    assert page.evaluate("[cur.notes.filter(n => n.hit).length, lives]") == [2, 3]


def test_the_menu_fits_a_390_px_phone(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:piano:taso', '12')")
    page.reload()
    row = page.locator("#pickrow").bounding_box()
    assert row["x"] >= 0 and row["x"] + row["width"] <= 390
    assert "Kimalaisen lento" in page.inner_text("#pick")
    ctx.close()
