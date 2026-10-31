"""Keihäänheitto v2: the outfit picker, with Halloween costumes, and friends see your outfit (#158)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/keihas/v2/"
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); };
  window.go = (v, ang, at) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    th.phase = 'run'; th.v = v; th.x = at;
    startAim(1); th.aimT = (ang - AIM0) / AIM_RATE; th.ang = ang; release();
  };
  window.quick = () => {
    if (th.jav) { th.jav.acc = 30; step(0.001); }
    th.t = 99; step(0.001);
  };
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def test_picking_an_outfit_saves_it_and_the_thrower_wears_it(site, context):
    page = open_game(site, context)
    assert page.text_content("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut .asu").count() == 10
    page.click("[data-asu=noita]")
    page.click("#ai-pelit-asut-valmis")
    assert page.locator("#ai-pelit-asut").count() == 0
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:keihas')") == '"noita"'
    assert page.text_content("#asu") == "👕 Asu: Noita"
    page.click("#go")
    assert page.evaluate("comp.throwers.find(t => t.p === 'me').fit") == "noita"
    assert page.evaluate("looks(comp.throwers.find(t => t.p === 'me')).head") == "witch"
    # The computer keeps its own look: v1's, a shirt in its own colour.
    assert page.evaluate("comp.throwers.filter(t => t.p === null).every(t => looks(t) === null)")
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.v = 7; th.x = -12; draw()")
    # The choice outlasts a reload, and a meet kept from before wears the outfit picked now.
    page.reload()
    page.evaluate(HELPERS)
    assert page.text_content("#asu") == "👕 Asu: Noita"
    page.click("#asu")
    page.click("[data-asu=vihrea]")
    page.click("#ai-pelit-asut-valmis")
    page.click("#cont")
    assert page.evaluate("comp.throwers.find(t => t.p === 'me').fit") == "vihrea"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (740, 360), (640, 360)])
def test_the_menu_with_the_outfit_button_fits(site, context, size):
    w, h = size
    page = open_game(site, context)
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
            assert not (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]), sel
    page.click("#asu")
    done = page.locator("#ai-pelit-asut-valmis").bounding_box()
    assert done["y"] >= 0 and done["y"] + done["height"] <= h
    assert page.errors == []


def test_friends_see_each_others_outfits(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name, fit in (("Eero", "kurpitsa"), ("Aino", "luuranko")):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))});"
                            f"localStorage.setItem('ai-pelit:_asut:keihas', {json.dumps(json.dumps(fit))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
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
    ainoId = aino.evaluate("AiPelitRooms.me")
    for p in pages:
        p.wait_for_function(f"comp && comp.throwers.length === 12 && (comp.throwers.find(t => t.p === {json.dumps(ainoId)}) || {{}}).fit === 'luuranko'", timeout=8000)
        assert p.evaluate("comp.throwers.find(t => t.p === AiPelitRooms.host || t.name === 'Eero').fit") == "kurpitsa"
        assert p.errors == []
    for p in pages:
        p.context.close()
