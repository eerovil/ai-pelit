"""Seittisankari v6 (#568): the hero wears the outfit picked in any 3D game (lib/asut3d-1), in the
city, in the story's cutscenes and on friends' phones."""
import json
import shutil

from conftest import ROOT

from test_seittisankari_v6 import go, open_game
from test_seittisankari_v6_rooms import phone, room, start  # noqa: F401  (phone is a fixture)

SHARED = "ai-pelit:_asut:3d"


def looks(page):
    page.wait_for_timeout(150)
    return page.evaluate("L3D.looks()")


def test_a_fresh_phone_wears_the_hero_suit_and_the_menu_has_asu(site, context):
    page = open_game(site, context)
    assert page.locator("#asu").inner_text() == "👕 Asu"
    assert page.locator("#asu").is_visible()
    go(page)
    page.wait_for_function("window.L3D && L3D.ready && !L3D.failed", timeout=20000)
    assert looks(page) == {"me": "sankari"}
    assert page.errors == []


def test_a_pick_is_saved_for_every_3d_game_and_redresses_the_hero(site, context):
    page = open_game(site, context)
    page.click("#asu")
    # The common set and the seasons' costumes, the game's own suit first.
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[0] == "sankari" and {"haalari", "yosankari", "vampyyri", "kurpitsa", "harry", "joulupukki"} <= set(ids)
    page.click("[data-asu=vampyyri]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    assert page.evaluate(f"localStorage.getItem('ai-pelit:_asut:seittisankari')") == '"vampyyri"'
    page.evaluate("AiPelitOutfits.close()")
    go(page)
    page.wait_for_function("L3D.ready", timeout=20000)
    assert looks(page) == {"me": "vampyyri"}
    # Picked again mid-play: the hero is rebuilt in the new one, in the same place.
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=yosankari]")
    page.wait_for_function("L3D.looks().me === 'yosankari'")
    assert page.errors == []


def test_an_open_game_follows_a_pick_made_in_another_3d_game(site, context):
    shutil.copytree(ROOT / "games" / "pulkkamaki", site.games / "pulkkamaki")
    page = open_game(site, context)
    go(page)
    page.wait_for_function("L3D.ready && L3D.looks().me === 'sankari'", timeout=20000)
    other = context.new_page()
    other.goto(site.url + "games/pulkkamaki/v7/")
    other.wait_for_function("window.AiPelitOutfits && outfit")
    other.evaluate("AiPelitOutfits.open()")
    other.click("[data-asu=muumio]")
    other.close()
    # Back in view (another tab, or the page cache): the hero, and what friends are sent, follow.
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate("outfit.id") == "muumio"
    page.wait_for_function("L3D.looks().me === 'muumio'")
    assert page.errors == []


def test_a_pulkkamaki_riders_pick_carries_over(site, context):
    context.add_init_script("localStorage.setItem('ai-pelit:_asut:pulkkamaki', '\"liila\"')")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "liila"
    # Taken over, not moved: the rider's own key stays.
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:pulkkamaki')") == '"liila"'


def test_the_story_cutscene_hero_wears_the_outfit(site, context):
    context.add_init_script(f"localStorage.setItem('{SHARED}', '\"kurpitsa\"')")
    page = open_game(site, context)
    page.click("#story")
    page.click("#chList button >> nth=0")
    page.wait_for_function("mode === 'cut'")
    page.click("#cut")                                  # past the city shot, to Kallio and the hero
    page.wait_for_function("L3D.looks().sankari === 'kurpitsa'")
    got = looks(page)
    assert got["kallio"] == page.evaluate("CUT_COL.K")    # the others keep their own looks
    assert page.errors == []


def test_friends_see_each_others_outfits_and_the_name_colours_stay(phone):
    pages = room(phone, 2)
    for p, o in zip(pages, ["vampyyri", "harry"]):
        p.evaluate(f"localStorage.setItem('{SHARED}', {json.dumps(json.dumps(o))})")
        p.evaluate(f"outfit = AiPelitOutfits.get({json.dumps(o)})")
    start(pages)
    host, guest = pages
    hid, gid = host.evaluate("RM.me"), guest.evaluate("RM.me")
    for p in pages:
        p.wait_for_function(f"(() => {{ const l = L3D.looks(); return l['{hid}'] === 'vampyyri' && l['{gid}'] === 'harry'; }})()",
                            timeout=10000)
    # The colours by the names are the room's own, whatever anyone wears.
    cols = host.evaluate("net.players.map(p => p.col)")
    assert cols == host.evaluate("HERO_COLS.slice(0, 2)")
    # A pick mid-round reaches the other phone.
    guest.evaluate("AiPelitOutfits.open()")
    guest.click("[data-asu=noita]")
    host.wait_for_function(f"L3D.looks()['{gid}'] === 'noita'", timeout=10000)
    # And the host's, here or in another 3D game while its page was out of view.
    host.evaluate("AiPelitOutfits.open()")
    host.click("[data-asu=haamu]")
    guest.wait_for_function(f"L3D.looks()['{hid}'] === 'haamu'", timeout=10000)
    host.evaluate("localStorage.setItem('ai-pelit:_asut:3d', '\"muumio\"'); document.dispatchEvent(new Event('visibilitychange'))")
    guest.wait_for_function(f"L3D.looks()['{hid}'] === 'muumio'", timeout=10000)
    assert all(p.errors == [] for p in pages)
