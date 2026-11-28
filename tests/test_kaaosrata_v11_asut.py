"""Kaaosrata v11 (#571): the player's runner wears the outfit picked in any 3D game (lib/asut3d-1, one choice
saved as ai-pelit:_asut:3d), the menu's "👕 Asu" button changes it for every 3D game, and in a room each phone
sees every player in their own outfit. The computer's runners stay jellybeans."""
import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaaosrata/v11/"
SHARED = "ai-pelit:_asut:3d"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


def go(page):
    """A solo race, drawn in 3D."""
    page.click("#go")
    page.wait_for_function("window.K3D && K3D.ready && !K3D.failed && race && race.runners.length", timeout=20000)


def looks(page):
    page.wait_for_timeout(150)
    return page.evaluate("K3D.looks()")


def test_a_fresh_phone_wears_the_default_and_the_computers_runners_are_jellybeans(site, context):
    page = open_game(site, context)
    assert page.locator("#asu").inner_text() == "👕 Asu"
    assert page.locator("#asu").is_visible()
    go(page)
    got = looks(page)
    assert got.pop("me") == "punainen"
    assert len(got) == 7 and set(got.values()) == {"bean"}
    assert page.errors == []


def test_a_pick_is_saved_for_every_3d_game_and_redresses_the_runner(site, context):
    page = open_game(site, context)
    page.click("#asu")
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[0] == "punainen" and {"haalari", "sankari", "yosankari", "vampyyri"} <= set(ids)
    page.click("[data-asu=vampyyri]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"vampyyri"'
    page.evaluate("AiPelitOutfits.close()")
    go(page)
    page.wait_for_function("K3D.looks().me === 'vampyyri'", timeout=5000)
    # Picked again mid-race: the runner is rebuilt in the new one.
    page.evaluate("AiPelitOutfits.open()")
    page.click("[data-asu=yosankari]")
    page.wait_for_function("K3D.looks().me === 'yosankari'", timeout=5000)
    assert page.errors == []


def test_the_outfit_picked_in_another_3d_game_is_worn_and_followed(site, context):
    context.add_init_script(f"localStorage.setItem('{SHARED}', '\"sankari\"')")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "sankari"
    go(page)
    page.wait_for_function("K3D.looks().me === 'sankari'", timeout=5000)
    # Another 3D game changed it while this page was out of view: back in view, the runner follows.
    page.evaluate(f"localStorage.setItem('{SHARED}', '\"muumio\"'); document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate("outfit.id") == "muumio"
    page.wait_for_function("K3D.looks().me === 'muumio'", timeout=5000)
    assert page.errors == []


def room(site, browser, outfits):
    """Phones in a room, each in its own outfit, the race on."""
    site.build(ROOT / "games")
    relay, pages = Relay(), []
    for i, o in enumerate(outfits):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                                  service_workers="block")
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps('Testi ' + str(i)))});"
                            f"localStorage.setItem('{SHARED}', {json.dumps(json.dumps(o))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.click("#multi")
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    for g in guests:
        g.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
        g.click("#aipr-joinBtn")
        g.wait_for_function("AiPelitRooms.inRoom")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(pages)}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && window.K3D && K3D.ready && !K3D.failed", timeout=20000)
    return pages


def test_friends_see_each_others_outfits(site, browser):
    host, guest = pages = room(site, browser, ["vampyyri", "harry"])
    hid, gid = host.evaluate("AiPelitRooms.me"), guest.evaluate("AiPelitRooms.me")
    want = f"(() => {{ const l = K3D.looks(); return l['{hid}'] === 'vampyyri' && l['{gid}'] === 'harry'; }})()"
    for p in pages:
        p.wait_for_function(want, timeout=10000)
        # The computer's runners stay jellybeans, and the name colours are the game's own.
        got = p.evaluate("K3D.looks()")
        assert [v for k, v in got.items() if k not in (hid, gid)] == ["bean"] * 4, got
        assert p.evaluate("race.runners.map(r => r.color)") == p.evaluate("COLORS.slice(0, 6)")
    # A pick mid-race reaches the other phone, from a guest and from the host.
    guest.evaluate("AiPelitOutfits.open()")
    guest.click("[data-asu=noita]")
    host.wait_for_function(f"K3D.looks()['{gid}'] === 'noita'", timeout=10000)
    host.evaluate("AiPelitOutfits.open()")
    host.click("[data-asu=haamu]")
    guest.wait_for_function(f"K3D.looks()['{hid}'] === 'haamu'", timeout=10000)
    assert all(p.errors == [] for p in pages)
