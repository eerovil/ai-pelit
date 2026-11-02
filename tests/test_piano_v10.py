"""Piano v8: no-fail mode (#318). One song with no hearts to lose, off the high-score list.

v9 (#356): the menu has the song last played ready, and a no-fail song opens no level.
v10 (#356): a furthest level above 5 goes down to 5, once per phone."""

import pytest

from conftest import ROOT


def open_menu(site, context, size=None, saves=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if size:
        page.set_viewport_size(size)
    if saves:
        page.add_init_script("".join(f"localStorage.setItem('ai-pelit:piano:{k}', '{v}');" for k, v in saves.items()))
    page.goto(site.url + "games/piano/v10/")
    page.evaluate("window._sent = []; window.AiPelitScores = {submit: s => _sent.push(s)}")
    return page


# Plays the current song to its end, pressing every k-th note on its beat; the rest fall past.
FINISH = """(k) => {
  const lv0 = level;
  cur.notes.forEach((n, i) => { update(n.t - now); if (i % k === 0) tap(n.lane); });
  for (let i = 0; i < 100 && state === 'play' && level === lv0; i++) update(0.05);
}"""


def test_the_switch_is_off_at_first_and_kept(site, context):
    page = open_menu(site, context)
    assert page.inner_text("#nofail") == "🛡️ Ei häviötä: pois"
    page.click("#nofail")
    assert page.inner_text("#nofail") == "🛡️ Ei häviötä: päällä"
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:eihaviota')") == "true"
    page.reload()
    assert page.inner_text("#nofail") == "🛡️ Ei häviötä: päällä"


def test_a_no_fail_song_plays_through_its_misses_and_ends_in_the_menu(site, context):
    page = open_menu(site, context, saves={"ennatys": 100000, "taso": 3})
    page.click("#nofail")
    page.click("#prev")  # level 2, so finishing it does not raise the furthest level
    page.click("#go")
    assert page.evaluate("[safe, level]") == [True, 2]
    page.evaluate(FINISH, 3)  # two notes in three fall past: far more than three hearts
    assert page.evaluate("state") == "over"
    assert page.is_visible("#menu")
    hits, total, score = page.evaluate("[cur.notes.filter(n => n.hit).length, cur.notes.length, score]")
    assert hits < total - 3 and score > 0
    assert page.inner_text("#result") == f"Kappale soitettu: {score} pistettä, osuit {hits}/{total}\nEi häviötä -tila ei avaa tasoja"
    # Off the list and the record; the furthest level is unchanged.
    assert page.evaluate("[_sent.length, best, topLevel]") == [0, 100000, 3]


def test_a_no_fail_song_opens_no_level(site, context):
    # v9 (#356): v8 opened the next level here, so no-fail was a way past a hard song.
    page = open_menu(site, context)
    page.click("#nofail")
    page.click("#go")
    page.evaluate(FINISH, 1)
    assert page.evaluate("[state, topLevel]") == ["over", 1]
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:taso')") == "1"
    assert page.inner_text("#go") == "Soita!"
    assert not page.is_visible("#pickrow")
    assert page.inner_text("#result").endswith("Ei häviötä -tila ei avaa tasoja")
    assert page.evaluate("[_sent.length, localStorage.getItem('ai-pelit:piano:ennatys')]") == [0, None]


def test_a_normal_game_still_loses_hearts_and_keeps_its_score(site, context):
    page = open_menu(site, context)
    page.click("#go")
    assert page.evaluate("safe") is False
    page.evaluate(FINISH, 1)  # a clean song: on to level 2, score kept
    assert page.evaluate("[state, level, _sent.length]") == ["play", 2, 1]
    page.evaluate("for (let i = 0; i < 3; i++) tap(0)")  # three stray taps
    assert page.evaluate("[state, lives]") == ["over", 0]


@pytest.mark.parametrize("w,h", [(360, 640), (740, 360)])
def test_the_menu_fits_with_the_switch(site, context, w, h):
    page = open_menu(site, context, size={"width": w, "height": h}, saves={"taso": 5})
    box = page.locator("#nofail").bounding_box()
    assert box["y"] >= 0 and box["y"] + box["height"] <= h
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")


def test_a_normal_game_after_a_no_fail_one_has_hearts_again(site, context):
    page = open_menu(site, context)
    page.click("#nofail")
    page.click("#go")
    page.evaluate(FINISH, 2)
    page.click("#nofail")  # off again; level 1 is ready, as the song just played
    page.click("#go")
    assert page.evaluate("[safe, lives, level]") == [False, 3, 1]
    page.evaluate("tap(0)")
    assert page.evaluate("lives") == 2


def test_a_reload_mid_song_keeps_the_switch_and_the_level(site, context):
    page = open_menu(site, context, saves={"taso": 2})
    page.click("#nofail")
    page.click("#go")
    page.evaluate("update(cur.notes[3].t - now)")
    page.reload()
    assert page.is_visible("#menu")
    assert page.inner_text("#nofail") == "🛡️ Ei häviötä: päällä"
    assert page.inner_text("#go") == "Jatka tasolta 2"
    assert page.evaluate("[best, topLevel]") == [0, 2]


def test_real_taps_on_a_390_px_phone_cost_nothing_in_no_fail(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + "games/piano/v10/")
    page.tap("#nofail")
    page.tap("#go")
    lane_x, lane_w, btn = page.evaluate("[laneX, laneW, btnTop]")
    for _ in range(5):  # five stray taps with no note near: more than three hearts
        page.touchscreen.tap(lane_x + 0.5 * lane_w, (btn + 844) / 2)
    assert page.evaluate("[state, safe, lives]") == ["play", True, 3]
    page.evaluate("""() => {
      const n = cur.notes[0];
      for (const m of cur.notes) { m.hit = m !== n; m.missed = false; }
      now = n.t - 0.2; window._n = n;
    }""")
    page.touchscreen.tap(lane_x + (page.evaluate("_n.lane") + 0.5) * lane_w, (btn + 844) / 2)
    assert page.evaluate("_n.hit") is True
    ctx.close()


def test_the_menu_has_the_no_fail_song_just_played_ready(site, context):
    page = open_menu(site, context, saves={"taso": 3})
    assert page.inner_text("#go") == "Jatka tasolta 3"  # nothing played yet: the furthest
    page.click("#nofail")
    page.click("#prev")
    page.click("#prev")
    page.click("#go")
    page.evaluate(FINISH, 1)
    assert page.evaluate("state") == "over"
    assert page.inner_text("#pick") == "Taso 1 · " + page.evaluate("songOf(1).name")
    assert page.inner_text("#go") == "Soita!"
    page.click("#next")
    assert page.inner_text("#go") == "Soita tasolta 2"
    page.click("#next")
    assert page.inner_text("#go") == "Jatka tasolta 3"


def test_the_menu_has_the_level_of_a_game_over_ready(site, context):
    page = open_menu(site, context, saves={"taso": 4})
    page.click("#prev")
    page.click("#prev")
    page.click("#go")
    assert page.evaluate("level") == 2
    page.evaluate("for (let i = 0; i < 3; i++) tap(0)")
    assert page.evaluate("state") == "over"
    assert page.inner_text("#go") == "Soita tasolta 2"
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:viimeisin')") == "2"


def test_a_reload_has_the_song_last_played_ready(site, context):
    page = open_menu(site, context, saves={"taso": 3})
    page.click("#prev")
    page.click("#prev")
    page.click("#go")
    page.evaluate("update(cur.notes[3].t - now)")
    page.reload()
    assert page.inner_text("#pick").startswith("Taso 1 · ")
    assert page.inner_text("#go") == "Soita!"


def test_a_saved_last_level_past_the_furthest_is_clamped(site, context):
    page = open_menu(site, context, saves={"taso": 3, "viimeisin": 9})
    assert page.inner_text("#go") == "Jatka tasolta 3"


def test_real_taps_on_a_390_px_phone_bring_back_the_no_fail_song(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.add_init_script("if (!sessionStorage.x) { sessionStorage.x = 1; localStorage.setItem('ai-pelit:piano:taso', '3'); }")
    page.goto(site.url + "games/piano/v10/")
    page.evaluate("window.AiPelitScores = {submit() {}}")
    page.tap("#nofail")
    page.tap("#prev")
    page.tap("#go")
    page.evaluate(FINISH, 2)
    assert page.evaluate("[state, topLevel]") == ["over", 3]
    # The menu fits the phone with the end text's second line, and the same song is one tap away.
    assert page.evaluate("document.getElementById('menu').scrollHeight <= innerHeight")
    assert page.inner_text("#go") == "Soita tasolta 2"
    page.tap("#go")
    assert page.evaluate("[state, level, safe]") == ["play", 2, True]
    page.reload()
    assert page.inner_text("#go") == "Soita tasolta 2"
    ctx.close()


def test_a_furthest_level_above_5_goes_down_to_5_once(site, context):
    page = open_menu(site, context, saves={"taso": 9, "viimeisin": 8})
    assert page.evaluate("[topLevel, localStorage.getItem('ai-pelit:piano:taso')]") == [5, "5"]
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:tasoraja')") == "true"
    assert page.inner_text("#go") == "Jatka tasolta 5"  # the last played (8) is clamped too
    assert page.inner_text("#stats").endswith("paras taso 5")


def test_a_level_reached_past_5_after_the_cut_is_kept(site, context):
    page = open_menu(site, context, saves={"taso": 7, "tasoraja": "true"})
    assert page.evaluate("topLevel") == 7
    page.evaluate("newGame(5, false); songDone()")  # a song finished with hearts still opens the next
    assert page.evaluate("[level, topLevel]") == [6, 7]


def test_a_level_at_or_below_5_is_untouched(site, context):
    page = open_menu(site, context, saves={"taso": 4})
    assert page.evaluate("[topLevel, localStorage.getItem('ai-pelit:piano:taso')]") == [4, "4"]


def test_the_cut_happens_only_on_the_first_open(site, context):
    page = open_menu(site, context, saves={"taso": 9})
    assert page.evaluate("topLevel") == 5
    # A restart: the test's init script writes 9 again, as if reached anew; the cut is not repeated.
    page.reload()
    assert page.evaluate("[topLevel, localStorage.getItem('ai-pelit:piano:tasoraja')]") == [9, "true"]
