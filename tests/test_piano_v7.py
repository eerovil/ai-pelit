"""Piano v7: a wider hit window (#316), so a press a little early or late still counts."""

import pytest

from conftest import ROOT
from test_piano_v5 import PLAY


def open_game(site, context, version="v7", size=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if size:
        page.set_viewport_size(size)
    page.goto(site.url + f"games/piano/{version}/")
    page.click("#go")
    return page


def test_the_window_is_half_as_wide_again_as_v6(site, context):
    assert open_game(site, context, "v6").evaluate("[PERFECT, GOOD]") == [0.07, 0.16]
    assert open_game(site, context).evaluate("[PERFECT, GOOD]") == [0.1, 0.24]


@pytest.mark.parametrize("bias", [-0.2, 0.2])
def test_a_press_a_fifth_of_a_second_off_counts_in_v7_not_in_v6(site, context, bias):
    old = open_game(site, context, "v6").evaluate(PLAY, [1, bias, 12])
    assert old == old.lower(), old
    new = open_game(site, context).evaluate(PLAY, [1, bias, 12])
    assert new == new.upper(), new


def test_a_press_just_off_is_nappiin(site, context):
    page = open_game(site, context)
    page.evaluate("level = 1; startLevel(); state = 'play'; score = 0;"
                  "const n = cur.notes[0]; update(n.t + 0.09 - now); tap(n.lane);")
    assert page.evaluate("score") == 100


def test_every_hard_song_through_with_early_and_late_presses(site, context):
    page = open_game(site, context)
    for lv in (10, 11, 12, 13):
        for bias in (-0.2, 0.22):
            played = page.evaluate(PLAY, [lv, bias, 400])
            assert played == played.upper(), (lv, bias, played)
            assert page.evaluate("lives") == 99, (lv, bias)


def test_a_note_falls_past_only_after_the_wider_window(site, context):
    page = open_game(site, context)
    page.evaluate("level = 1; startLevel(); state = 'play'; window._n = cur.notes[0]; update(_n.t + 0.2 - now)")
    assert page.evaluate("_n.missed") is False
    page.evaluate("update(0.06)")
    assert page.evaluate("_n.missed") is True


@pytest.mark.parametrize("w,h", [(360, 640), (360, 740), (740, 360), (640, 360)])
def test_the_taller_zone_fits_between_the_top_bar_and_the_keys(site, context, w, h):
    page = open_game(site, context, size={"width": w, "height": h})
    for lv in range(1, 27):  # two laps of the songs, the second 15 % faster
        fits = page.evaluate(f"level = {lv}; startLevel();"
                             "[hitY - zonePx(GOOD) > topY, hitY + zonePx(GOOD) <= btnTop]")
        assert fits == [True, True], (w, h, lv)
