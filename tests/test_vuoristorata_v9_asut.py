"""Vuoristorata v9 (#574): the rider wears the outfit picked in any 3D game (lib/asut3d-1), changed
from the menu's "👕 Asu" button, and friends in a room see each rider in their own outfit."""
import json

from test_vuoristorata_v9 import build, open_page, room_of  # noqa: F401

SHARED = "ai-pelit:_asut:3d"


def open_with(site, browser, outfit=None, **kw):
    ctx, page = open_page(site, browser, **kw)
    if outfit:
        page.evaluate(f"localStorage.setItem('{SHARED}', {json.dumps(json.dumps(outfit))})")
        page.reload()
        page.wait_for_function("window.drawn === true", timeout=20000)
    return ctx, page


def test_a_fresh_phone_wears_the_snowsuit_and_the_menu_has_asu(site, browser):
    build(site)
    ctx, page = open_page(site, browser)
    try:
        assert page.locator("#asu").inner_text() == "👕 Asu"
        assert page.locator("#asu").is_visible()
        assert page.evaluate("outfit.id") == "haalari"
        assert page.evaluate("VR3D.looks()") == {"me": "haalari"}
        # The countdown first looks back at my rider in the train, then the ride is seen from the seat.
        page.click("#aja")
        page.wait_for_function("VR3D.seatRider() === 'haalari'", timeout=3000)
        page.wait_for_function("game.mode === 'ride' && VR3D.seatRider() === null", timeout=6000)
        assert page.errors == []
    finally:
        ctx.close()


def test_a_pick_is_saved_for_every_3d_game_and_redresses_the_rider(site, browser):
    build(site)
    ctx, page = open_page(site, browser)
    try:
        page.click("#asu")
        ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
        assert ids[0] == "haalari" and {"sankari", "vampyyri", "harry", "joulupukki"} <= set(ids)
        page.click("[data-asu=vampyyri]")
        assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
        page.evaluate("AiPelitOutfits.close()")
        assert page.evaluate("VR3D.looks().me") == "vampyyri"
        page.click("#aja")
        page.wait_for_function("VR3D.seatRider() === 'vampyyri'", timeout=3000)
        assert page.errors == []
    finally:
        ctx.close()


def test_a_pick_made_in_another_3d_game_is_worn(site, browser):
    build(site)
    ctx, page = open_with(site, browser, "harry")
    try:
        assert page.evaluate("outfit.id") == "harry"
        assert page.evaluate("VR3D.looks().me") == "harry"
        # Picked elsewhere while this page was out of view: it follows on coming back.
        page.evaluate(f"localStorage.setItem('{SHARED}', '\"muumio\"')")
        page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_function("VR3D.looks().me === 'muumio'")
        assert page.errors == []
    finally:
        ctx.close()


def test_friends_see_each_riders_own_outfit_and_a_change_mid_race(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino"])
    guest = guests[0]
    try:
        for p, o in [(host, "vampyyri"), (guest, "harry")]:
            p.evaluate("AiPelitOutfits.open()")
            p.click(f"[data-asu={o}]")
            p.evaluate("AiPelitOutfits.close()")
            p.wait_for_function(f"outfit.id === '{o}'")
        hid, gid = host.evaluate("AiPelitRooms.me"), guest.evaluate("AiPelitRooms.me")
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && net.cfg && game.mode === 'ride'", timeout=10000)
        host.wait_for_function(f"VR3D.looks()[{json.dumps(gid)}] === 'harry'", timeout=5000)
        guest.wait_for_function(f"VR3D.looks()[{json.dumps(hid)}] === 'vampyyri'", timeout=5000)
        assert host.evaluate("VR3D.looks().me") == "vampyyri"
        # Aino changes her outfit mid-race: Eero's phone redraws her train.
        guest.evaluate("AiPelitOutfits.open()")
        guest.click("[data-asu=joulupukki]")
        guest.evaluate("AiPelitOutfits.close()")
        host.wait_for_function(f"VR3D.looks()[{json.dumps(gid)}] === 'joulupukki'", timeout=5000)
        assert host.errors == [] and guest.errors == []
    finally:
        for c in ctxs:
            c.close()
