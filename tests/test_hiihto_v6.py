"""Hiihto v6 (#93): a tap lands on the button it is on, and a race works with more than two phones."""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/hiihto/v6/"


def open_game(site, browser, w=360, h=740):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    return page


def on_screen(page, name, i=None):
    """The middle of a menu button where the phone shows it, in screen pixels."""
    return page.evaluate("""([name, i]) => {
      draw();
      const b = i === null ? ui[name] : ui[name][i], r = c.getBoundingClientRect();
      return [r.left + (b.x + b.w / 2) * r.width / W, r.top + (b.y + b.h / 2) * r.height / H];
    }""", [name, i])


def test_the_game_is_drawn_for_the_canvas_as_it_shows(site, browser):
    page = open_game(site, browser, 390, 844)
    assert page.evaluate("[W, H]") == [390, 844]
    assert page.evaluate("[c.getBoundingClientRect().width, c.getBoundingClientRect().height]") == [390, 844]
    page.context.close()


# v5 drew for innerHeight but stretched the canvas to 100dvh; where a phone's two differ, the
# buttons showed lower than where a tap went. A canvas box taller than the window, and one that is
# shorter and lower, stand in for those phones.
@pytest.mark.parametrize("w,h", [(360, 740), (390, 844)])
@pytest.mark.parametrize("box", ["top:0;height:110%", "top:60px;height:calc(100% - 60px)"])
def test_a_tap_on_a_button_as_it_shows_presses_it(site, browser, box, w, h):
    page = open_game(site, browser, w, h)
    page.evaluate(f"c.style.cssText = '{box}'; resize()")
    page.wait_for_function("H === c.getBoundingClientRect().height")
    # The style button, then a wax: each where it is drawn on the screen.
    page.touchscreen.tap(*on_screen(page, "styles", 1))
    assert page.evaluate("style") == "luistelu"
    # Tapped near its bottom edge, the lower-right wax still starts the race alone.
    x, y = on_screen(page, "wax", 3)
    bh = page.evaluate("ui.wax[3].h * c.getBoundingClientRect().height / H")
    page.touchscreen.tap(x, y + bh / 2 - 3)
    page.wait_for_function("mode === 'count'", timeout=2000)
    assert page.evaluate("net === null && document.getElementById('aipr')?.hidden !== false")
    assert page.errors == []
    page.context.close()


def test_the_friends_button_as_it_shows_opens_the_room(site, browser):
    page = open_game(site, browser, 360, 740)
    page.evaluate("c.style.cssText = 'top:0;height:110%'; resize()")
    page.touchscreen.tap(*on_screen(page, "friends"))
    page.wait_for_function("!!document.getElementById('aipr') && !document.getElementById('aipr').hidden", timeout=2000)
    assert page.evaluate("mode") == "wax"
    page.context.close()


NAMES = ["Eero", "Aino", "Ville", "Saara"]


def room_of(site, browser, names, relay=None):
    """The first phone makes a room, the others join with its code, and the round starts."""
    site.build(ROOT / "games")
    relay = relay or Relay()
    pages = []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("typeof course === 'object'")
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.evaluate("draw(); down(1, ui.friends.x + 5, ui.friends.y + 5); up(1, ui.friends.x + 5, ui.friends.y + 5)")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for n, g in enumerate(guests, 2):
        g.evaluate("AiPelitRooms.open()")
        g.fill("#aipr-codeIn", code)
        g.click("#aipr-joinBtn")
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {n}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function(f"net && net.cfg && mode === 'wax' && net.skiers.length === {len(names)}", timeout=6000)
    return pages


CLEAR = "npcs = []; nextVasta = nextSkate = 1e9"


def test_four_phones_race_and_all_get_the_same_places(site, browser):
    pages = room_of(site, browser, NAMES)
    host = pages[0]
    # Everyone skis the same course, and each phone has the same four skiers in the same colours.
    assert len({json.dumps(p.evaluate("[level, style, course.len, net.skiers.map(k => [k.name, k.color])]")) for p in pages}) == 1
    # The start waits until all four have waxed.
    for p in pages[:3]:
        p.evaluate("draw(); const r = ui.wax[bestFor(style, course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1, r.x + 5, r.y + 5)")
    host.wait_for_timeout(800)
    assert host.evaluate("[mode, net.phase]") == ["ready", "wax"]
    assert "Saara" in host.evaluate("net.skiers.filter(k => k.wax < 0).map(k => k.name).join()")
    pages[3].evaluate("draw(); const r = ui.wax[bestFor(style, course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1, r.x + 5, r.y + 5)")
    for p in pages:
        p.wait_for_function("mode === 'race'", timeout=8000)
        p.evaluate(CLEAR)
    # Each phone sees every other skier where that phone put it.
    for i, p in enumerate(pages):
        p.evaluate(f"P.z = {40 + 30 * i}")
    for p in pages:
        p.wait_for_function("net.skiers.every((k, i) => k.kind === 'me' || Math.abs(k.z - (40 + 30 * i)) < 15)", timeout=4000)
    assert [p.evaluate("livePlace()") for p in pages] == [4, 3, 2, 1]
    # Ville's phone reloads mid-race: it skis on from where it was, and the others still see it.
    pages[2].reload()
    pages[2].wait_for_function("net && mode === 'race' && P.z >= 95 && net.skiers.length === 4", timeout=8000)
    pages[2].evaluate(CLEAR)
    host.wait_for_function("net.skiers[2].z >= 95", timeout=4000)
    # They finish in the order Ville, Eero, Saara, Aino.
    for i in [2, 0, 3, 1]:
        pages[i].evaluate("P.z = course.len - 0.5; P.v = 8")
        host.wait_for_function(f"net.skiers[{i}].at != null", timeout=4000)
    for p in pages:
        p.wait_for_function("net && net.res", timeout=6000)
        assert p.evaluate("net.res.map(r => r.name)") == ["Ville", "Eero", "Saara", "Aino"]
    for p in pages:
        p.evaluate("resultT = 2; down(1, W / 2, H / 2); up(1, W / 2, H / 2)")
        p.wait_for_function("AiPelitRooms.inRoom && !net && document.getElementById('aipr-result').textContent !== ''", timeout=6000)
    assert [p.inner_text("#aipr-result").split(" ·")[0] for p in pages] == ["2. sija", "4. sija", "1. sija", "3. sija"]
    assert all(p.errors == [] for p in pages)
    for p in pages:
        p.context.close()


def test_the_computer_skis_for_one_of_three_who_left(site, browser):
    relay = Relay()
    pages = room_of(site, browser, NAMES[:3], relay)
    host = pages[0]
    for p in pages:
        p.evaluate("draw(); const r = ui.wax[bestFor(style, course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1, r.x + 5, r.y + 5)")
    for p in pages:
        p.wait_for_function("mode === 'race'", timeout=8000)
        p.evaluate(CLEAR)
    # Aino's phone goes; the host lets the computer ski for her and the race goes on for the rest.
    relay.drop(pages[1])
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.click("#aipr-goOn")
    host.wait_for_function("net.skiers[1].kind === 'cpu' && !AiPelitRooms.paused", timeout=4000)
    host.evaluate(CLEAR)
    pages[2].wait_for_function("!AiPelitRooms.paused", timeout=4000)
    for p in (host, pages[2]):
        p.evaluate("P.z = course.len - 0.5; P.v = 8")
    host.evaluate("net.skiers[1].p.z = course.len - 0.5")
    for p in (host, pages[2]):
        p.wait_for_function("net && net.res", timeout=8000)
        assert sorted(p.evaluate("net.res.map(r => r.name)")) == ["Aino", "Eero", "Ville"]
    assert host.errors == pages[2].errors == []
    for p in pages:
        p.context.close()
