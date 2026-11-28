"""Hiihto v14 (#570): the player's skier wears the outfit shared by every 3D game (lib/asut3d-1,
`ai-pelit:_asut:3d`), the wax screen has a 👕 Asu button that changes it for every 3D game, and in
a room each phone sees every skier in their own outfit."""
import json

from conftest import ROOT
from test_hiihto_v14 import open_game
from test_rooms_lib import Relay

URL = "games/hiihto/v14/"
SHARED = "ai-pelit:_asut:3d"

# The rig drawing skier `obj` (P, or one of net.skiers), once the next frame has drawn it.
RIG = "(() => { draw(); const r = V3.rigs.get(%s); return r ? r.wearId : null; })()"


def meshes(page, expr):
    return page.evaluate(f"(() => {{ let n = 0; ({expr}).traverse(m => {{ if (m.isMesh) n++; }}); return n; }})()")


def test_the_skier_wears_the_3d_games_outfit_and_its_own_head_and_hat_hide(site, context):
    context.add_init_script(f"localStorage.setItem('{SHARED}', '\"vampyyri\"')")
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "vampyyri"
    page.wait_for_function("typeof V3 === 'object' && V3 && V3.scene")
    assert page.evaluate(RIG % "P") == "vampyyri"
    r = "V3.rigs.get(P)"
    # The library's own head, mesh for mesh, and the vampire's cape; the skier's own head, hair,
    # hat and bobble are hidden.
    assert meshes(page, f"{r}.wear.head") == meshes(page, "AiPelitAsut3d.head(THREE, AiPelitOutfits.get('vampyyri'))") >= 3
    assert page.evaluate(f"!!{r}.wear.cape && {r}.wear.head.parent === {r}.root && {r}.wear.cape.parent === {r}.root")
    assert page.evaluate(f"[{r}.head, {r}.hair, {r}.hat, {r}.pom, {r}.extra.brim].every(p => !p.visible)")
    # The coat and trousers are the outfit's.
    assert page.evaluate(f"'#' + {r}.mats.coat.color.getHexString(THREE.SRGBColorSpace)") == page.evaluate("AiPelitOutfits.get('vampyyri').top").lower()
    assert page.errors == []


def test_a_phone_that_never_picked_wears_the_overall_and_the_grannies_keep_their_own_heads(site, context):
    page = open_game(site, context)
    assert page.evaluate("outfit.id") == "haalari"
    page.wait_for_function("typeof V3 === 'object' && V3 && V3.scene")
    assert page.evaluate(RIG % "P") == "haalari"
    # The overall's stripe goes round the body.
    assert page.evaluate("!!V3.rigs.get(P).wear.chest")
    # A computer skier is drawn as in v13, its own head and hat showing.
    got = page.evaluate("""(() => { newRace(); P.z = 0; npcs = [{ kind: 'mummo', z: 6, x: 0, lane: 1, ph: 0, coat: '#aa3344', hat: '#334455' }]; draw();
        const r = V3.rigs.get(npcs[0]); return [r.wearId, r.head.visible, r.hat.visible]; })()""")
    assert got == ["", True, True]
    assert page.errors == []


def tap(page, rect):
    r = page.evaluate(f"ui.{rect}")
    page.mouse.click(r["x"] + r["w"] / 2, r["y"] + r["h"] / 2)


def test_the_asu_button_changes_the_outfit_for_every_3d_game(site, context):
    page = open_game(site, context)
    page.wait_for_function("typeof V3 === 'object' && V3 && V3.scene")
    page.evaluate("draw()")
    tap(page, "asu")
    page.wait_for_selector("#ai-pelit-asut")
    ids = page.evaluate("AiPelitOutfits.list().map(o => o.id)")
    assert ids[0] == "haalari" and {"sankari", "yosankari"} <= set(ids)
    page.click("[data-asu=sankari]")
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"sankari"'
    assert page.evaluate("outfit.id") == "sankari"
    page.evaluate("AiPelitOutfits.close()")
    assert page.evaluate(RIG % "P") == "sankari"
    # Still on the wax screen, the race not started by the tap.
    assert page.evaluate("mode") == "wax"
    # A pick made in another 3D game is worn once the page is back in view.
    page.evaluate(f"localStorage.setItem('{SHARED}', '\"liila\"'); document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate(RIG % "P") == "liila"
    assert page.errors == []


OVERLAP = """() => { draw(); const rs = [...ui.styles, ui.asu, ui.prev, ui.next, ui.friends, ...ui.wax].filter(Boolean);
  const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const bad = [];
  rs.forEach((a, i) => rs.slice(i + 1).forEach(b => { if (hit(a, b)) bad.push([a, b]); }));
  rs.forEach(a => { if (a.x < 0 || a.y < 0 || a.x + a.w > W || a.y + a.h > H) bad.push([a]); });
  return bad; }"""


def test_the_asu_button_fits_upright_and_sideways(site, browser):
    site.build(ROOT / "games")
    for w, h in ((360, 640), (360, 740), (740, 360), (640, 360)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True, service_workers="block")
        page = ctx.new_page()
        page.goto(site.url + URL)
        page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
        assert page.evaluate("!!ui.asu"), (w, h)
        assert page.evaluate(OVERLAP) == [], (w, h)
        # The style buttons keep their names inside them.
        assert page.evaluate("ui.styles.every(r => { x.font = '800 15px system-ui,sans-serif'; return x.measureText(STYLE_NAME[r.style]).width < r.w - 8; })"), (w, h)
        ctx.close()


def phones(site, browser, outfits, view=(360, 740)):
    """Phones in a room, each wearing its outfit, on the wax screen."""
    site.build(ROOT / "games")
    relay, pages = Relay(), []
    for i, of in enumerate(outfits):
        ctx = browser.new_context(viewport={"width": view[0], "height": view[1]}, is_mobile=True, has_touch=True, service_workers="block")
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps('Testi ' + 'ABC'[i]))});"
                            f"localStorage.setItem('{SHARED}', {json.dumps(json.dumps(of))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
        page.evaluate("AiPelitRooms.open()")
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
        p.wait_for_function("net && net.cfg && mode === 'wax'", timeout=10000)
    return pages


def friend(page, other):
    """The outfit `page` draws the skier of phone `other` in, by the rig drawing it."""
    oid = other.evaluate("AiPelitRooms.me")
    return page.evaluate(RIG % f"net.skiers.find(k => k.id === {json.dumps(oid)})")


def test_in_a_room_each_phone_sees_every_skier_in_their_own_outfit(site, browser):
    host, guest, third = phones(site, browser, ["vampyyri", "punainen", "sankari"])
    # The guest changes its outfit on the wax screen, with the Asu button there too.
    guest.evaluate("draw()")
    assert guest.evaluate("!!ui.asu && ui.styles.length === 0")
    tap(guest, "asu")
    guest.wait_for_selector("#ai-pelit-asut")
    guest.click("[data-asu=harry]")
    guest.evaluate("AiPelitOutfits.close()")
    assert guest.evaluate("mode") == "wax"
    for p in (host, guest, third):
        p.evaluate("chooseWax(bestWax(course.weather.T))")
    for p in (host, guest, third):
        p.wait_for_function("mode === 'race'", timeout=15000)
    want = {id(host): "vampyyri", id(guest): "harry", id(third): "sankari"}
    for watch in (host, guest, third):
        for other in (host, guest, third):
            if other is watch:
                continue
            watch.wait_for_function(f"net.skiers.find(k => k.id === {json.dumps(other.evaluate('AiPelitRooms.me'))}).o === {json.dumps(want[id(other)])}", timeout=8000)
            assert friend(watch, other) == want[id(other)]
    # The names keep the room's colours.
    assert host.evaluate("net.skiers.map(k => k.color).join()") == guest.evaluate("net.skiers.map(k => k.color).join()")
    # A pick the host makes mid-race (in another 3D game, back in view) reaches the others.
    host.evaluate(f"localStorage.setItem('{SHARED}', '\"liila\"'); document.dispatchEvent(new Event('visibilitychange'))")
    hid = host.evaluate("AiPelitRooms.me")
    for watch in (guest, third):
        watch.wait_for_function(f"net.skiers.find(k => k.id === {json.dumps(hid)}).o === 'liila'", timeout=8000)
        assert friend(watch, host) == "liila"
    errors = [e for p in (host, guest, third) for e in p.errors]
    assert not errors, errors


def test_a_picked_outfit_casts_shadows_and_an_unknown_friend_id_keeps_the_room_colour(site, context):
    page = open_game(site, context)
    page.wait_for_function("typeof V3 === 'object' && V3 && V3.scene")
    page.evaluate("draw()")
    # Picked after the rig was built: the new pieces cast shadows like the rest of the near skier.
    page.evaluate("localStorage.setItem('ai-pelit:_asut:3d', '\"vampyyri\"'); document.dispatchEvent(new Event('visibilitychange'))")
    assert page.evaluate(RIG % "P") == "vampyyri"
    assert page.evaluate("(() => { const w = V3.rigs.get(P).wear; let all = true; w.parts.forEach(p => p.traverse(m => { if (m.isMesh && !m.castShadow) all = false; })); return all; })()")
    assert page.evaluate("[friendOutfit({ o: 'ei-tallaista' }), friendOutfit({ o: null }), friendOutfit({ o: 'harry' }).id]") == [None, None, "harry"]
    assert page.errors == []


def test_a_skier_far_ahead_drops_the_outfits_pieces_like_its_other_small_parts(site, context):
    context.add_init_script(f"localStorage.setItem('{SHARED}', '\"harry\"')")
    page = open_game(site, context)
    page.wait_for_function("typeof V3 === 'object' && V3 && V3.scene")
    got = page.evaluate("""(() => { const r = makeRig(), at = [0, 1, 0], hd = [0, 1.6, 0], out = [];
      for (const fine of [false, true, false]) { r.fine = fine; wear(r, outfit, at, [0, 1.4, 0], hd, 0);
        out.push([r.wear.parts.some(p => p.visible), r.head.visible, r.hat.visible]); }
      return out; })()""")
    # Far (40 m or more): its own head and hat in the outfit's colours; near: the outfit's pieces.
    assert got == [[False, True, True], [True, False, False], [False, True, True]]
    assert page.errors == []


def test_a_guest_still_picking_a_wax_is_seen_in_their_outfit(site, browser):
    host, guest, third = phones(site, browser, ["vampyyri", "punainen", "sankari"])
    gid = guest.evaluate("AiPelitRooms.me")
    for watch in (host, third):
        watch.wait_for_function(f"net.skiers.find(k => k.id === {json.dumps(gid)}).o === 'punainen'", timeout=8000)
        assert friend(watch, guest) == "punainen"
    # A change while still on the wax screen reaches them too, and starts nothing.
    tap(guest, "asu")
    guest.wait_for_selector("#ai-pelit-asut")
    guest.click("[data-asu=harry]")
    guest.evaluate("AiPelitOutfits.close()")
    for watch in (host, third):
        watch.wait_for_function(f"net.skiers.find(k => k.id === {json.dumps(gid)}).o === 'harry'", timeout=8000)
        assert friend(watch, guest) == "harry"
    assert host.evaluate(f"net.skiers.find(k => k.id === {json.dumps(gid)}).wax") == -1
    assert all(p.evaluate("mode") == "wax" for p in (host, guest, third))
    errors = [e for p in (host, guest, third) for e in p.errors]
    assert not errors, errors
