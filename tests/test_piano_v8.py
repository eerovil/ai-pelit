"""Piano v8: no-fail mode (#318). One song with no hearts to lose, off the high-score list."""

import pytest

from conftest import ROOT


def open_menu(site, context, size=None, saves=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if size:
        page.set_viewport_size(size)
    if saves:
        page.add_init_script("".join(f"localStorage.setItem('ai-pelit:piano:{k}', '{v}');" for k, v in saves.items()))
    page.goto(site.url + "games/piano/v8/")
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
    assert page.inner_text("#result") == f"Kappale soitettu: {score} pistettä, osuit {hits}/{total}"
    # Off the list and the record; the furthest level is unchanged.
    assert page.evaluate("[_sent.length, best, topLevel]") == [0, 100000, 3]


def test_a_no_fail_song_opens_the_next_level(site, context):
    page = open_menu(site, context)
    page.click("#nofail")
    page.click("#go")
    page.evaluate(FINISH, 1)
    assert page.evaluate("[state, topLevel]") == ["over", 2]
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:taso')") == "2"
    assert page.inner_text("#go") == "Jatka tasolta 2"
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
