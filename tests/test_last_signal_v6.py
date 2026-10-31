"""Last Signal v6 (#143): the sea is frozen over. SISU comes up only in a few openings in the ice, the person climbs out
through the tower onto the ice, and the abandoned station A-3 on the ice shelf is walked like SISU's rooms, with a
cold meter that runs down outside and fills again indoors. Everything else plays as v5: v5's tests (and through
them v4's) run here on v6 too."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)
from test_last_signal_v5 import close_cards, room, save_with, stand, toast

URL = "games/last-signal/v6/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v6(monkeypatch):
    monkeypatch.setattr(v4, "URL", URL)
    monkeypatch.setattr(v5, "URL", URL)


# v6 is v5 with the ice: every v5 test (its own and v4's, alone), on v6.
for _name in dir(v5):
    if _name.startswith("test_"):
        globals()[_name + "_v5"] = getattr(v5, _name)


def ready(page, **flags):
    """A new game past the first cards, held still for the test to step."""
    v4.new_game(page)
    page.evaluate(f"Object.assign(G.s.flags, {json.dumps({'pinged': True, 'kontti': True, 'asema': True, 'koti': True, **flags})})")


def surface(page, x=270):
    """Drives SISU up from below the first opening until it lies surfaced in it."""
    page.evaluate(f"sub.x = {x}; sub.y = 24; sub.vx = sub.vy = 0; input.y = -1; run(() => sub.y > SURF, 12); input.y = 0;"
                  " sub.vx = sub.vy = 0")
    assert page.evaluate("surfaced()")


def out_on_the_ice(page):
    """From the helm in the opening: inside, up the ladder and out through the tower, down onto SISU's back."""
    v4.inside(page)
    page.evaluate("drawHud()")
    v4.act(page, "Tornista jäälle")
    assert page.evaluate("G.mode") == "ice"
    if page.is_visible("#panel"):
        page.click("#card button:has-text('Selvä')")
    page.evaluate("run(() => walker.climbing, 5)")


def walk_to(page, x):
    """Walks the person on the ice towards x with the stick, reading every note on the way."""
    page.evaluate(f"""(() => {{ input.x = Math.sign({x} - walker.x);
      for (let i = 0; i < 6000 && Math.abs(walker.x - {x}) > 0.3 && G.mode === 'ice'; i++) {{
        step(1 / 60); if (G.paused) closeCard();
        if (Math.sign({x} - walker.x) !== Math.sign(input.x)) break; }}
      input.x = 0; step(1 / 60); drawHud(); }})()""")


def test_the_ice_stops_sisu_softly_and_the_openings_let_it_up(site, browser):
    page = v4.open_game(site, browser)
    ready(page)
    # Under the ice, away from an opening: SISU stops below it, unhurt, and is told where the way up is.
    page.evaluate("sub.x = 400; sub.y = 20; G.s.m.hull = 100; input.y = -1; run(() => true, 4); input.y = 0")
    assert page.evaluate("sub.y") >= 7.9
    assert page.evaluate("G.s.m.hull") == 100
    assert "railoista" in toast(page)
    # Under the first opening, a little off its middle: SISU is drawn to the middle and comes up.
    surface(page, 266)
    assert abs(page.evaluate("sub.x") - page.evaluate("holeMid(0)")) < 1.5
    assert page.evaluate("[sub.y, G.s.m.hull]") == [1.2, 100]
    assert "Pinnalla" in toast(page)
    # Every opening fits SISU, and each is a sonar contact; the first is where the goal points while parts are short.
    for n in range(4):
        page.evaluate(f"sub.x = holeMid({n}); sub.y = 20; sub.vx = sub.vy = 0; input.y = -1; run(() => !surfaced(), 12); input.y = 0")
        assert page.evaluate("surfaced()"), f"SISU cannot come up in opening {n}"
    page.evaluate("sub.x = 330; sub.y = 30; G.pingCd = 0; doPing(); drawHud()")
    assert page.evaluate("G.s.known.railo0") is True
    assert page.evaluate("goalNow().target") == "railo0"
    assert "nouse railosta pintaan" in page.inner_text("#goal")
    assert page.errors == []


def test_out_through_the_tower_to_the_station_and_its_finds_come_home(site, browser):
    page = v4.open_game(site, browser)
    ready(page)
    page.evaluate("G.s.inv.osat = 0")
    surface(page)
    out_on_the_ice(page)
    # Down the tower onto SISU's back, the cold meter full.
    assert page.evaluate("[walker.climbing, walker.y === sub.y - 2.3, walker.warm > 95]") == [False, True, True]
    assert page.is_visible("#mWarm")
    assert not page.is_visible("#home")
    # Across the planks and the ice to the station: the cold bites outside, the rooms warm.
    walk_to(page, 215)
    assert page.evaluate("walker.warm") < 90
    walk_to(page, 205)
    assert page.evaluate("[inStation(walker.x), walker.room]") == [True, "seteinen"]
    assert page.inner_text("#roomName") == "A-3 · ETEINEN"
    warm = page.evaluate("walker.warm = 50")
    page.evaluate("run(() => true, 2)")
    assert page.evaluate("walker.warm") > warm
    # The radio room's diary and the lab's whiteboard tell the story; the store's crates are carried.
    page.evaluate("input.x = -1; run(() => !G.paused, 10); input.x = 0")
    assert "A-3:n radiopäiväkirja" in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    walk_to(page, 121)
    assert page.evaluate("G.s.flags.taulu") is True
    assert sorted(page.evaluate("G.carry")) == ["pinta:l", "pinta:o1", "pinta:o2", "pinta:r1", "pinta:r2"]
    assert page.evaluate("[G.s.inv.ruoka, G.s.inv.osat]") == [2, 0]
    # The station's far wall stops the walk.
    page.evaluate("input.x = -1; run(() => true, 1); input.x = 0")
    assert page.evaluate("walker.x") >= 120.5
    # Back to SISU's tower and down the hatch: the haul goes into the stores.
    walk_to(page, page.evaluate("hatchX()"))
    assert page.inner_text("#act") == "⬇️ Alas torniin"
    page.click("#act")
    assert page.evaluate("[G.mode, crew.room, crew.x === LADDER]") == ["home", "ohjaamo", True]
    assert page.evaluate("[G.s.inv.ruoka, G.s.inv.osat, G.s.inv.laake, G.s.flags.pinta]") == [4, 2, 2, True]
    assert "Kotona" in toast(page)
    page.evaluate("drawHud()")
    assert "nouse railosta" not in page.inner_text("#goal")
    # The notes are in the logbook, and the save keeps it all.
    page.evaluate("logBook()")
    assert "A-3:n radiopäiväkirja" in page.inner_text("#card")
    assert "Laboratorion valkotaulu" in page.inner_text("#card")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).inv.osat") == 2
    assert page.errors == []


def test_the_stick_up_the_ladder_climbs_out_only_when_sisu_is_surfaced(site, browser):
    page = v4.open_game(site, browser)
    ready(page)
    page.evaluate("sub.x = 273; sub.y = 30")
    v4.inside(page)
    page.evaluate("crew.x = LADDER; crew.y = UP; input.y = -1; run(() => true, 1); input.y = 0")
    assert page.evaluate("G.mode") == "home"
    v4.walk(page, "ohjaamo")
    assert "Tornista jäälle" not in page.inner_text("#pad")
    page.evaluate("closeHome()")
    surface(page)
    v4.inside(page)
    page.evaluate("crew.x = LADDER; crew.y = UP; input.y = -1; run(() => G.mode === 'home', 1); input.y = 0")
    assert page.evaluate("G.mode") == "ice"
    assert "Jäällä" in page.inner_text("#card")


def test_the_cold_sends_the_person_back_and_the_finds_wait_in_the_station(site, browser):
    page = v4.open_game(site, browser)
    ready(page)
    surface(page)
    out_on_the_ice(page)
    walk_to(page, 135)
    assert len(page.evaluate("G.carry")) >= 2
    # Out of the door into the cold, and it runs out.
    walk_to(page, 220)
    page.evaluate("walker.warm = 3; G.hold = false")
    page.wait_for_function("G.mode === 'home'")
    page.evaluate("G.hold = true")
    assert "Kylmä voitti" in page.inner_text("#card")
    assert page.evaluate("[crew.room, G.s.inv.ruoka, G.s.m.health, G.carry.length]") == ["ohjaamo", 2, 75, 0]
    assert page.evaluate("ICE_ITEMS.filter(it => it.k !== 'loki').every(itemHere)") is True
    # Outside the meter runs down in a minute, inside SISU it is full again on the next climb.
    page.evaluate("closeCard(); goIce(); closeCard(); run(() => walker.climbing, 5)")
    assert page.evaluate("walker.warm") > 95
    page.evaluate("run(() => true, 30)")
    assert 40 < page.evaluate("walker.warm") < 55
    assert page.errors == []


def test_open_water_stops_the_walk_and_a_tap_walks_there(site, browser):
    page = v4.open_game(site, browser)
    ready(page)
    surface(page)
    out_on_the_ice(page)
    # A tap on the ice ahead walks the person there.
    page.evaluate("drawHud(); draw()")
    x, y = page.evaluate("""(() => { const r = cv.getBoundingClientRect(), V = G.view;
      return [r.left + V.ox + (walker.x - 4) * V.sc, r.top + V.oy + walker.y * V.sc]; })()""")
    page.mouse.click(x, y)
    page.evaluate("run(() => walker.to != null, 5)")
    assert abs(page.evaluate("walker.x") - (page.evaluate("hatchX()") - 4)) < 0.1
    # Out on the sea ice by the next opening: its open water stops the walk.
    page.evaluate("walker.x = 925; walker.y = ICE_TOP; walker.warm = 100")
    walk_to(page, 940)
    assert 925 < page.evaluate("walker.x") <= 932
    assert "avovettä" in toast(page)
    assert page.errors == []


def test_an_old_save_with_sisu_where_the_ice_is_now_starts_under_it(site, browser):
    save = json.dumps(save_with(sub={"x": 600, "y": 5, "dir": 1}))
    page = v4.open_game(site, browser, save=save)
    page.click("#jatka")
    page.evaluate("G.hold = true")
    assert page.evaluate("[sub.x, subHits(sub.x, sub.y), sub.y >= 8, sub.y < 12]") == [600, False, True, True]
    # The v5 save is read as it is: no new fields needed.
    assert page.evaluate("[G.s.day, G.s.inv.osat]") == [4, 2]


@pytest.mark.parametrize("w,h", [(360, 640), (740, 360)])
def test_the_ice_cards_and_controls_fit_upright_and_sideways(site, browser, w, h):
    page = v4.open_game(site, browser, w, h)
    ready(page)
    surface(page)
    v4.inside(page)
    page.evaluate("drawHud()")
    v4.act(page, "Tornista jäälle")
    assert "Jäällä" in page.inner_text("#card")
    assert page.evaluate(v4.OVERFLOW) == []
    page.click("#card button:has-text('Selvä')")
    page.evaluate("run(() => walker.climbing, 5); drawHud()")
    assert page.evaluate(v4.OVERFLOW) == []
    page.evaluate("walker.warm = 0.01; run(() => G.mode === 'ice', 1)")
    assert "Kylmä voitti" in page.inner_text("#card")
    assert page.evaluate(v4.OVERFLOW) == []


def test_sisu_holds_still_while_a_friend_is_on_the_ice_and_their_haul_is_the_hosts(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"), saves=[save_with(sub={"x": 273, "y": 20, "dir": 1}), None])
    close_cards(host, aino)
    host.evaluate("G.s.flags.pinta = false; input.y = -1")
    host.wait_for_function("surfaced()")
    host.evaluate("input.y = 0")
    aino.wait_for_function("surfaced()")
    stand(aino, "ohjaamo")
    aino.click("#pad button:visible:has-text('Tornista jäälle')")
    aino.evaluate("closeCard()")
    host.wait_for_function("Object.values(net.others).some(o => o.mode === 'ice')")
    # The host at the helm cannot drive off while Aino is out on the ice.
    x0 = host.evaluate("sub.x")
    host.evaluate("input.x = 1")
    host.wait_for_function("$('toast').textContent.includes('Aino on jäällä')")
    host.evaluate("input.x = 0")
    assert abs(host.evaluate("sub.x") - x0) < 0.5
    # Aino carries the store's crates home; they go into the host's stores.
    aino.evaluate("""walker.climbing = false; walker.x = 137; walker.y = groundAt(137); walker.warm = 100;
      input.x = -1""")
    aino.wait_for_function("G.carry.length >= 4 || G.paused")
    aino.evaluate("input.x = 0; if (G.paused) closeCard()")
    host.wait_for_function("Object.values(G.held).length >= 4")
    aino.evaluate("walker.x = hatchX(); walker.y = groundAt(walker.x); drawHud()")
    aino.click("#act")
    host.wait_for_function("G.s.inv.osat === 4 && G.s.flags.pinta === true")
    aino.wait_for_function("G.mode === 'home' && crew.room === 'ohjaamo'")
    assert aino.evaluate(f"localStorage.getItem('{SAVE}')") is None
    for p in (host, aino):
        assert p.errors == []
