"""Aitajuoksu v5: the runner's outfit, Halloween costumes too, and friends see each other's (#158)."""

import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/aitajuoksu/v5/"


def build(site):
    # Only this game, so another game's work in progress does not stop the build.
    if not (site.games / "aitajuoksu").exists():
        shutil.copytree(ROOT / "games" / "aitajuoksu", site.games / "aitajuoksu")
        site.build()


def open_game(site, browser, w=360, h=740, name=None):
    build(site)
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    if name:
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


def inside(box, w, h):
    return box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= w and box["y"] + box["height"] <= h


def test_picking_an_outfit_saves_it_and_the_runner_wears_it(site, browser):
    page = open_game(site, browser)
    assert page.inner_text("#asu") == "👕 Asu: Perus"
    page.click("#asu")
    assert page.locator("#ai-pelit-asut [data-asu]").count() == 10
    page.click("[data-asu=kurpitsa]")
    page.click("#ai-pelit-asut-valmis")
    assert page.locator("#ai-pelit-asut").count() == 0
    assert page.evaluate("localStorage.getItem('ai-pelit:_asut:aitajuoksu')") == '"kurpitsa"'
    assert page.inner_text("#asu") == "👕 Asu: Kurpitsa"
    page.click("#go")
    assert page.evaluate("me.asu") == "kurpitsa"
    # The computer's runners keep their own looks.
    assert page.evaluate("race.runners.filter(r => r !== me).every(r => !r.asu)")
    page.wait_for_timeout(300)
    # Remembered on the next visit.
    page.reload()
    assert page.inner_text("#asu") == "👕 Asu: Kurpitsa"
    assert page.errors == []
    page.context.close()


@pytest.mark.parametrize("w,h", [(740, 360), (360, 740), (640, 360)])
def test_the_menu_with_the_outfit_button_fits(site, browser, w, h):
    page = open_game(site, browser, w, h)
    page.evaluate("localStorage.setItem('ai-pelit:aitajuoksu:juoksut', '3')")
    page.evaluate("showMenu('Voitit! 14,20 s 🏆', 'win')")
    for sel in ["#menu h1", "#result", "#go", "#multi", "#asu", "#dists", "#hurd"]:
        assert inside(page.locator(sel).bounding_box(), w, h), sel
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight")
    boxes = [page.locator(s).bounding_box() for s in ["#go", "#multi", "#asu", "#dists", "#hurd"]]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])
    page.click("#asu")
    assert page.locator("#ai-pelit-asut-valmis").is_visible()
    assert page.errors == []
    page.context.close()


def test_in_a_room_friends_see_each_others_outfits(site, browser):
    build(site)
    relay = Relay()
    pages = []
    for name, asu in [("Eero", "vampyyri"), ("Aino", "haamu")]:
        page = open_game(site, browser, name=name)
        page.evaluate(f"localStorage.setItem('ai-pelit:_asut:aitajuoksu', '\"{asu}\"')")
        relay.attach(page)
        page.reload()
        pages.append(page)
    host, guest = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net'", timeout=6000)
    host.evaluate("race.gunAt = 0.05")
    for p in pages:
        p.wait_for_function("race.phase === 'run'", timeout=4000)
    # The host learns the guest's outfit from its runner's messages, the guest the host's from the race.
    host.wait_for_function("race.runners.find(r => r !== me).asu === 'haamu'", timeout=4000)
    guest.wait_for_function("race.runners.find(r => r !== me).asu === 'vampyyri'", timeout=4000)
    assert host.evaluate("me.asu") == "vampyyri" and guest.evaluate("me.asu") == "haamu"
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()
