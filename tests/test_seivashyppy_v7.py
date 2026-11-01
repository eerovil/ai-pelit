"""Seiväshyppy v7: outfits, one choice for every athletics event (#311)."""

import pytest

import yleisurheilu_asut as asut

URL = "games/seivashyppy/v7/"
SLUG = "seivashyppy"


def test_picking_an_outfit_saves_it_for_every_event_and_the_jumper_wears_it(site, context):
    asut.picking_saves_for_every_event(site, context, URL, SLUG)


def test_an_outfit_picked_in_another_event_is_worn_here(site, browser):
    asut.wears_what_another_event_picked(site, browser.new_context(), URL, SLUG)


def test_the_games_own_older_choice_is_kept(site, context):
    asut.reads_its_own_older_choice(site, context, URL, SLUG)


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_with_the_outfit_button_fits(site, context, size):
    asut.menu_fits(site, context, URL, size)


def test_friends_see_each_others_outfits(site, browser):
    asut.friends_see_each_others_outfits(site, browser, URL)
