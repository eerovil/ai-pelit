"""Pingis v3 (#573): the players wear the outfit shared by every 3D game (lib/asut3d-1).

The owner's words: my player wears the outfit picked in the other 3D games (one choice,
`ai-pelit:_asut:3d`); the game has a "👕 Asu" button that changes it for every 3D game; in a room
each phone sees the other player's own outfit."""
from test_pingis_v3 import go, open_game
from test_pingis_v3_rooms import phones, room  # noqa: F401  (phones is a fixture)

SHARED = "ai-pelit:_asut:3d"


def test_my_player_wears_the_outfit_picked_in_another_3d_game(site, context):
    context.add_init_script(f"if (!localStorage.getItem('x')) {{ localStorage.setItem('x', 1); localStorage.setItem('{SHARED}', '\"sankari\"'); }}")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "sankari"
    # The menu looks at my player from the far end, so the outfit shows there.
    page.wait_for_function("V3.figs[0] && V3.figs[0].id === 'sankari' && V3.figs[0].g.visible")
    # The figure is the library's own person, mesh for mesh.
    n = page.evaluate("""(() => { const c = g => { let n = 0; g.traverse(m => { if (m.isMesh) n++; }); return n; };
        return [c(V3.figs[0].g), c(AiPelitAsut3d.figure(THREE, AiPelitOutfits.get('sankari')))]; })()""")
    assert n[0] == n[1] > 10
    assert page.errors == []


def test_the_asu_button_changes_the_outfit_for_every_3d_game(site, context):
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "punainen"   # Pingis's default, red like its first bat
    assert page.locator("#asu").is_visible()
    assert page.locator("#asu").inner_text().strip() == "👕 Asu"
    page.click("#asu")
    page.click("[data-asu=vampyyri]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    page.evaluate("AiPelitOutfits.close()")
    page.wait_for_function("V3.figs[0].id === 'vampyyri'")
    # The pick holds on the next visit, and the other 3D games read the same key.
    page.reload()
    page.wait_for_function("V3 || no3d", timeout=20000)
    assert page.evaluate("outfit.id") == "vampyyri"
    assert page.errors == []


def test_against_the_computer_it_wears_another_outfit(site, context):
    page = open_game(site, context)
    go(page)
    # My figure is behind the camera; the computer's is drawn at the far end.
    page.wait_for_function("V3.figs[1] && V3.figs[1].g.visible && V3.figs[0] && !V3.figs[0].g.visible")
    assert page.evaluate("[V3.figs[0].id, V3.figs[1].id]") == ["punainen", "haalari"]
    page.evaluate(f"localStorage.setItem('{SHARED}', '\"haalari\"'); document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function("V3.figs[0].id === 'haalari' && V3.figs[1].id === 'punainen'")
    assert page.errors == []


def test_in_a_room_each_phone_sees_the_other_players_own_outfit(phones):
    host, guest = room(phones)
    host.evaluate(f"localStorage.setItem('{SHARED}', '\"liila\"'); document.dispatchEvent(new Event('visibilitychange'))")
    guest.evaluate(f"localStorage.setItem('{SHARED}', '\"musta\"'); document.dispatchEvent(new Event('visibilitychange'))")
    # The guest plays at the -z end (side 1): it draws the host at side 0, and the other way round.
    guest.wait_for_function("net.foeO === 'liila' && V3.figs[0] && V3.figs[0].id === 'liila' && V3.figs[0].g.visible", timeout=8000)
    host.wait_for_function("net.foeO === 'musta' && V3.figs[1] && V3.figs[1].id === 'musta' && V3.figs[1].g.visible", timeout=8000)
    # A new pick mid-game reaches the other phone too.
    host.evaluate("AiPelitOutfits.open()")
    host.click("[data-asu=harry]")
    guest.wait_for_function("V3.figs[0].id === 'harry'", timeout=8000)
    assert host.errors == [] and guest.errors == []
