"""Lattia on laavaa v4 (#572): the phone's own kid wears the outfit shared by every 3D game
(lib/asut3d-1, ai-pelit:_asut:3d), a 👕 Asu button changes it, and in a room every phone sees
each player's own outfit. The computer's kids keep their own colours."""
import json

from test_lattia_on_laavaa_v4 import go, open_game
from test_lattia_on_laavaa_v4_rooms import kids, room, start  # noqa: F401  (kids is a fixture)

SHARED = "ai-pelit:_asut:3d"


def test_the_kid_wears_the_outfit_picked_in_another_3d_game(site, context):
    context.add_init_script(f"localStorage.setItem('{SHARED}', '\"kurpitsa\"')")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "kurpitsa"
    assert page.locator("#asu").is_visible()
    go(page)
    page.wait_for_function("L3D.kidOutfit && L3D.kidOutfit('me') === 'kurpitsa'")
    # The pumpkin head is the library's own, mesh for mesh; the computer's kids wear their colours.
    n = page.evaluate("L3D.kidHead('me')")
    lib = page.evaluate("""import('../../../lib/three-r187/three.module.js').then(T => {
        let n = 0; AiPelitAsut3d.head(T, AiPelitOutfits.get('kurpitsa')).traverse(m => { if (m.isMesh) n++; }); return n; })""")
    assert n == lib >= 3
    assert page.evaluate("world.kids.filter(k => k.kind === 'cpu').map(k => L3D.kidOutfit(k.id))") == [""] * 5
    assert page.errors == []


def test_the_asu_button_changes_the_shared_choice_and_dresses_the_kid_mid_round(site, context):
    page = open_game(site, context)
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[0] == "haalari" and {"sankari", "kurpitsa", "vampyyri", "harry"} <= set(ids)
    page.click("#asu")
    page.click("[data-asu=vampyyri]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    page.evaluate("AiPelitOutfits.close()")
    go(page)
    page.wait_for_function("L3D.kidOutfit('me') === 'vampyyri'")
    # A pick in another 3D game while this page was out of view: the kid changes when it is back.
    page.evaluate(f"localStorage.setItem('{SHARED}', '\"harry\"'); document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function("me.o === 'harry' && L3D.kidOutfit('me') === 'harry'")
    assert page.errors == []


def test_in_a_room_every_phone_sees_each_players_own_outfit(kids):
    host, guest = room(kids)
    for p, o in ((host, "vampyyri"), (guest, "harry")):
        assert p.locator("#lol-asu").is_visible()
        p.click("#lol-asu"); p.click(f"[data-asu={o}]"); p.evaluate("AiPelitOutfits.close()")
    start([host, guest])
    hid, gid = json.dumps(host.evaluate("AiPelitRooms.me")), json.dumps(guest.evaluate("AiPelitRooms.me"))
    for p in (host, guest):
        p.wait_for_function(f"L3D.kidOutfit({hid}) === 'vampyyri' && L3D.kidOutfit({gid}) === 'harry'", timeout=8000)
    # A pick mid-round reaches the other phone too, the host's and a guest's.
    host.evaluate("AiPelitOutfits.open()"); host.click("[data-asu=muumio]"); host.evaluate("AiPelitOutfits.close()")
    guest.wait_for_function(f"L3D.kidOutfit({hid}) === 'muumio'", timeout=8000)
    guest.evaluate("AiPelitOutfits.open()"); guest.click("[data-asu=sankari]"); guest.evaluate("AiPelitOutfits.close()")
    host.wait_for_function(f"L3D.kidOutfit({gid}) === 'sankari'", timeout=8000)
    assert host.errors == [] and guest.errors == []
