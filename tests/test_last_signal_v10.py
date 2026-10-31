"""Last Signal v10 (#196): a hose guide clamped to a corner comes off again ("📌 Irrota ohjain") back into the stores,
and back from the ice the person climbs in the way they came out: up the tower's outside ladder, in through the hatch
and down the ladder inside. Otherwise v10 plays as v9: v9's tests (and through them v8's to v4's) run here on v10 too."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v6 as v6
import test_last_signal_v7 as v7
import test_last_signal_v8 as v8
import test_last_signal_v9 as v9
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v10/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v10(monkeypatch):
    for m in (v4, v5, v6, v7, v8, v9):
        monkeypatch.setattr(m, "URL", URL)


@pytest.fixture(autouse=True)
def _helpers(monkeypatch):
    monkeypatch.setattr(v4, "act", v9.act)
    monkeypatch.setattr(v4, "dive_at", v7.dive_at)


# v9's tests (with v8's to v4's), on v10, but for the ones that press "Alas torniin" and expect the person inside at
# once: now they climb the tower first. The tests below cover the way back in.
CHANGED = ("test_out_through_the_tower_to_the_station_and_back_down_into_the_control_room",
           "test_the_control_room_keeps_its_helm_button_when_surfaced_and_back_from_the_ice")
for _name in dir(v9):
    if _name.startswith("test_") and not _name.startswith(CHANGED):
        globals()[_name + "_v9"] = getattr(v9, _name)

open_game, inside, walk = v4.open_game, v4.inside, v4.walk
ready, toast = v6.ready, v6.toast


def climb_in(page):
    """At the tower's foot on the ice, presses "Alas torniin" and follows the person until they are inside: the
    heights they pass through, from SISU's back to the tower's top and down into it."""
    assert page.inner_text("#act") == "⬇️ Alas torniin"
    page.click("#act")
    return page.evaluate("""(() => { const ys = [], xs = [];
      for (let i = 0; i < 1200 && G.mode === 'ice'; i++) { step(1 / 60); ys.push(walker.y - sub.y); xs.push(walker.x - hatchX()); }
      return { ys, xs, mode: G.mode }; })()""")


# ---------- hose guides ----------

def test_a_clamped_guide_comes_off_again_into_the_stores(site, browser):
    page = v7.hose_game(site, browser)
    page.evaluate("reach('nordvik', SITES.find(s => s.id === 'nordvik').spot, 1, ITEMS.find(i => i.site === 'nordvik' && i.k === 'loki').id, 'hose')")
    page.evaluate("closeCard(); const p = hose.pts[hose.pts.length - 1]; diver.x = p[0]; diver.y = p[1]; drawHud()")
    n = page.evaluate("G.s.inv.ohjain")
    assert page.inner_text("#act").startswith("📌 Kiinnitä ohjain")
    page.click("#act")
    page.evaluate("drawHud()")
    assert page.evaluate("[G.s.guides.length, G.s.inv.ohjain]") == [1, n - 1]
    # By the guide just clamped, its button takes it off: the corner is bare again and the guide is in the stores.
    page.click("button:has-text('📌 Irrota ohjain')")
    assert page.evaluate("[G.s.guides.length, G.s.inv.ohjain]") == [0, n]
    assert "Ohjain irti" in toast(page)
    page.evaluate("drawHud()")
    assert page.inner_text("#act").startswith("📌 Kiinnitä ohjain")
    assert not page.is_visible("button:has-text('Irrota ohjain')")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).inv.ohjain") == n
    page.evaluate("G.paused = false; step(1 / 60)")
    assert page.errors == []


def test_the_tank_diver_takes_a_guide_off_too_and_only_beside_it(site, browser):
    page = v7.hose_game(site, browser)
    v7.dive_at(page, "asema")
    page.evaluate("G.s.guides.push([diver.x + 8, diver.y]); diver.x += 8.5; drawHud()")
    # the tank diver can take a guide off too: it needs no hose to unclamp it
    assert page.evaluate("diver.kit") == "tank"
    assert page.inner_text("#act") == "📌 Irrota ohjain"
    page.evaluate("diver.x += 4; drawHud()")
    assert not page.is_visible("button:has-text('Irrota ohjain')")
    assert page.errors == []


def test_a_friend_takes_a_guide_off_into_the_hosts_stores(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"),
                         saves=[v5.save_with(inv={"ohjain": 0}, guides=[[700, 120]]), None])
    v5.close_cards(host, aino)
    aino.evaluate("act('unguide', [700, 120])")
    host.wait_for_function("G.s.guides.length === 0 && G.s.inv.ohjain === 1")
    aino.wait_for_function("G.s.guides.length === 0")
    # a second ask for the same guide finds nothing there
    aino.evaluate("act('unguide', [700, 120])")
    host.wait_for_timeout(300)
    assert host.evaluate("G.s.inv.ohjain") == 1
    assert host.errors == [] and aino.errors == []


# ---------- back in from the ice ----------

def test_back_from_the_ice_up_the_outside_ladder_in_through_the_hatch_and_down_inside(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.inv.osat = 0")
    v6.surface(page)
    v6.out_on_the_ice(page)
    v6.walk_to(page, page.evaluate("hatchX() - 1.5"))
    r = climb_in(page)
    assert r["mode"] == "home"
    ys, xs = r["ys"], r["xs"]
    # first a step to the tower's foot on SISU's back, then straight up its outside ladder to the top ...
    top = ys.index(min(ys))
    assert min(ys) == pytest.approx(-5.2, abs=0.01)
    assert all(b <= a + 1e-6 for a, b in zip(ys[:top], ys[1:top + 1]))
    assert all(abs(x) < 1e-3 for x in xs[top:])
    # ... then down through the hatch into the tower, where the person stands under it, inside.
    assert ys[-1] == pytest.approx(-3.3, abs=0.05)
    assert all(b >= a - 1e-6 for a, b in zip(ys[top:], ys[top + 1:]))
    assert page.evaluate("[crew.room, crew.x === LADDER, crew.y === TOP]") == ["torni", True, True]
    # Then down the inside ladder by itself into the control room, where the helm button is.
    page.evaluate("run(() => crew.to, 6); step(1 / 60); drawHud()")
    assert page.evaluate("[crew.room, crew.y]") == ["ohjaamo", 0]
    assert page.inner_text("#act") == "⛵ Ruoriin"
    assert page.errors == []


def test_on_the_way_in_taps_and_the_stick_do_not_stop_the_climb(site, browser):
    page = open_game(site, browser)
    ready(page)
    v6.surface(page)
    v6.out_on_the_ice(page)
    v6.walk_to(page, page.evaluate("hatchX()"))
    page.click("#act")
    page.evaluate("step(1 / 60); input.x = -1; run(() => G.mode === 'ice', 6); input.x = 0")
    assert page.evaluate("[G.mode, crew.room]") == ["home", "torni"]
    assert page.errors == []


def test_the_haul_from_the_station_goes_into_the_stores_once_inside(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.inv.osat = 0")
    v6.surface(page)
    v6.out_on_the_ice(page)
    v6.walk_to(page, 205)
    page.evaluate("input.x = -1; run(() => !G.paused, 10); input.x = 0")
    page.click("#card button:has-text('Jatka')")
    v6.walk_to(page, 121)
    assert sorted(page.evaluate("G.carry")) == ["pinta:l", "pinta:o1", "pinta:o2", "pinta:r1", "pinta:r2"]
    v6.walk_to(page, page.evaluate("hatchX()"))
    climb_in(page)
    assert page.evaluate("[G.mode, crew.room, G.s.inv.ruoka, G.s.inv.osat, G.s.inv.laake]") == ["home", "torni", 4, 2, 2]
    page.evaluate("drawHud()")
    assert "nouse railosta" not in page.inner_text("#goal")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).inv.osat") == 2
    assert page.errors == []
