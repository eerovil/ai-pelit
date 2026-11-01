"""Outfits shared by the athletics events (#311): the tests every event's outfit version runs.

Each event version that loads outfits.js with data-share="yleisurheilu" has a "👕 Asu" button,
draws its own athlete in kit(fit, col), and sends the outfit to the meet with `fit`.
"""

import json

from conftest import ROOT, turn

SHARED = "ai-pelit:_asut:yleisurheilu"


def open_game(site, context, url, store=None):
    site.build(ROOT / "games")
    for k, v in (store or {}).items():
        context.add_init_script(f"localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))})")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + url)
    return page


def me(page):
    return page.evaluate("K.comp.throwers.find(t => t.p === 'me').fit")


def picking_saves_for_every_event(site, context, url, slug):
    page = open_game(site, context, url)
    assert page.text_content("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    # The athletics set (seven kits) and the six costumes.
    assert page.locator("#ai-pelit-asut .asu").count() == 13
    page.click("[data-asu=noita]")
    page.click("#ai-pelit-asut-valmis")
    assert page.locator("#ai-pelit-asut").count() == 0
    assert page.evaluate(f"localStorage.getItem('{SHARED}')") == '"noita"'
    # Saved for the game's older versions too, which read only their own key.
    assert page.evaluate(f"localStorage.getItem('ai-pelit:_asut:{slug}')") == '"noita"'
    assert page.text_content("#asu") == "👕 Asu: Noita"
    page.click("#go")
    assert me(page) == "noita"
    assert page.evaluate("kit(K.comp.throwers.find(t => t.p === 'me').fit).head") == "witch"
    # The computer keeps the plain kit in its own shirt colour.
    assert page.evaluate("K.comp.throwers.filter(t => t.p === null).every(t => kit(t.fit, t.col).top === t.col)")
    page.wait_for_timeout(300)
    # A kept meet wears the outfit picked since.
    page.reload()
    page.click("#asu")
    page.click("[data-asu=kulta]")
    page.click("#ai-pelit-asut-valmis")
    page.click("#cont")
    assert me(page) == "kulta"
    assert page.errors == []


def wears_what_another_event_picked(site, context, url, slug):
    # Picked in Keihäs v9 (or Ottelu): worn here too, over this game's own older choice.
    page = open_game(site, context, url, {SHARED: "suomi", f"ai-pelit:_asut:{slug}": "luuranko"})
    assert page.text_content("#asu") == "👕 Asu: Sinivalkoinen"
    page.context.close()


def reads_its_own_older_choice(site, context, url, slug):
    page = open_game(site, context, url, {f"ai-pelit:_asut:{slug}": "vampyyri"})
    assert page.text_content("#asu") == "👕 Asu: Vampyyri"


def menu_fits(site, context, url, size):
    w, h = size
    page = open_game(site, context, url)
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    boxes = {}
    for sel in ("#go", "#multi", "#asu", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
        boxes[sel] = b
    a = boxes["#asu"]
    for sel, b in boxes.items():
        if sel != "#asu":
            assert not (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
                        and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]), sel
    page.click("#asu")
    done = page.locator("#ai-pelit-asut-valmis").bounding_box()
    assert done["y"] >= 0 and done["y"] + done["height"] <= h
    assert page.errors == []


def friends_see_each_others_outfits(site, browser, url):
    from test_rooms_lib import Relay
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name, fit in (("Eero", "kurpitsa"), ("Aino", "luuranko")):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))});"
                            f"localStorage.setItem('{SHARED}', {json.dumps(json.dumps(fit))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + url)
        pages.append(page)
    host, aino = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    aino.click("#multi")
    aino.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    aino.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    aino_id = json.dumps(aino.evaluate("AiPelitRooms.me"))
    host_id = json.dumps(host.evaluate("AiPelitRooms.me"))
    for p in pages:
        p.wait_for_function(f"K.comp && K.comp.throwers.length === 12 && (K.comp.throwers.find(t => t.p === {aino_id}) || {{}}).fit === 'luuranko'", timeout=8000)
        assert p.evaluate(f"K.comp.throwers.find(t => t.p === {host_id}).fit") == "kurpitsa"
        # Each phone draws the other in that outfit.
        assert p.evaluate(f"kit(K.comp.throwers.find(t => t.p === {aino_id}).fit).head") == "skull"
        assert p.errors == []
    for p in pages:
        p.context.close()
