"""Mäkihyppy v12: the jumper wears the athletics outfit (#469).

The same "👕 Asu" choice as the other events (data-share="yleisurheilu"), worn on the hill, sent to
friends with `fit`, and drawn on the podium; the computer's jumpers keep the plain kit.
"""

from test_makihyppy_v14_viikko import HELPERS, open_game as open_week
import yleisurheilu_asut as A

URL = "games/makihyppy/v14/"


def test_picking_saves_for_every_event(site, context):
    A.picking_saves_for_every_event(site, context, URL, "makihyppy")


def test_wears_what_another_event_picked(site, context):
    A.wears_what_another_event_picked(site, context, URL, "makihyppy")


def test_reads_its_own_older_choice(site, context):
    A.reads_its_own_older_choice(site, context, URL, "makihyppy")


def test_menu_fits_upright(site, context):
    A.menu_fits(site, context, URL, (360, 740))


def test_menu_fits_sideways(site, context):
    A.menu_fits(site, context, URL, (740, 360))


def test_friends_see_each_others_outfits(site, browser):
    A.friends_see_each_others_outfits(site, browser, URL)


def test_the_podium_draws_the_outfit_and_the_plain_kits(site, context):
    page = open_week(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:_asut:yleisurheilu', '\"noita\"')")
    page.reload()
    page.evaluate(HELPERS)
    page.click("#go")
    for _ in range(4):
        page.wait_for_function("th && th.mine", timeout=3000)
        page.evaluate("strong()")
    assert page.evaluate("K.ending && K.ending.res.length") == 12
    # Every figure on the podium gets its look from the game: mine the witch, the rest their colour.
    looks = page.evaluate("""K.ending.res.map(r => { const k = kit(r.fit, r.col); return [r.p === 'me', k.head, k.top === r.col]; })""")
    mine = [l for l in looks if l[0]]
    assert mine == [[True, "witch", False]]
    assert all(l[1] is None and l[2] for l in looks if not l[0])
    page.wait_for_timeout(1500)
    assert page.errors == []
