"""Last Signal v8 (#151): the sea's sound and SISU's engines, schools of fish and a harpoon for food, the tower's inside
with the ladder up to its hatch (so going out onto the ice is one climb, no cut), a lab in the navigation room where the
samples found are studied for a lasting help, and the control room's helm button back when SISU lies surfaced.
Otherwise v8 plays as v7: v7's tests (and through them v6's, v5's and v4's) run here on v8 too."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v6 as v6
import test_last_signal_v7 as v7
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v8/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v8(monkeypatch):
    for m in (v4, v5, v6, v7):
        monkeypatch.setattr(m, "URL", URL)


# v7's tests (with v6's, v5's and v4's), on v8, but for the ones about the way out onto the ice from the control room:
# since v8 it is the tower's hatch. The tests below cover those.
CHANGED = {"test_out_through_the_tower_to_the_station_and_its_finds_come_home_v6",
           "test_the_stick_up_the_ladder_climbs_out_only_when_sisu_is_surfaced_v6",
           "test_sisu_holds_still_while_a_friend_is_on_the_ice_and_their_haul_is_the_hosts_v6"}
for _name in dir(v7):
    if _name.startswith("test_") and _name not in CHANGED:
        globals()[_name + "_v7"] = getattr(v7, _name)


def to_tower(page):
    """Inside SISU: climbs to the top of the tower, under the hatch, as a tap in the tower does."""
    page.evaluate("walkTo(LADDER, -4); run(() => crew.to, 20); step(1 / 60); drawHud()")
    assert page.evaluate("[crew.room, crew.y === TOP]") == ["torni", True]


def act(page, text):
    """v7's act; the way onto the ice is at the top of the tower since v8, so the person climbs there first."""
    if text == "Tornista jäälle":
        to_tower(page)
    v7.act(page, text)


@pytest.fixture(autouse=True)
def _helpers(monkeypatch):
    monkeypatch.setattr(v4, "act", act)
    monkeypatch.setattr(v4, "dive_at", v7.dive_at)


open_game, new_game, inside, walk = v4.open_game, v4.new_game, v4.inside, v4.walk
ready, surface, walk_to = v6.ready, v6.surface, v6.walk_to
toast = v6.toast


def dive_near_school(page, n=0):
    """A tank dive next to school n, its fish held where they are (no swimming off between steps)."""
    page.evaluate(f"""(() => {{ const [x, y] = SCHOOLS[{n}]; sub.x = x - 20; sub.y = Math.max(12, y - 4); sub.vx = sub.vy = 0;
      sub.dir = sub.face = 1; G.mode = 'home'; crew.suit = true; crew.kit = 'tank'; startDive(); if (G.paused) closeCard();
      const f = fishNow().filter(f => f.n === {n}).sort((a, b) => a.x - b.x)[0];
      diver.x = f.x - 7; diver.y = f.y; diver.vx = diver.vy = 0; diver.dir = 1; }})()""")
    assert page.evaluate("diverHits(diver.x, diver.y)") is False
    assert page.evaluate("G.mode") == "dive"


def shoot_nearest(page):
    """Faces the nearest fish, fires the harpoon and lets the spear fly; the fish speared, if any."""
    return page.evaluate("""(() => {
      const f = fishNow().sort((a, b) => Math.hypot(a.x - diver.x, a.y - diver.y) - Math.hypot(b.x - diver.x, b.y - diver.y))[0];
      diver.dir = f.x > diver.x ? 1 : -1; G.harpCd = 0; const before = G.carry.length;
      fire(); for (let i = 0; i < 60 && G.spear; i++) stepSpear(1 / 60);
      return G.carry.length > before ? G.carry[G.carry.length - 1] : null; })()""")


def test_the_control_room_keeps_its_helm_button_when_surfaced_and_back_from_the_ice(site, browser):
    page = open_game(site, browser)
    ready(page)
    surface(page)
    inside(page)
    walk(page, "ohjaamo")
    # v7 put the way onto the ice here, in place of the helm: the helm button was gone while SISU lay surfaced (#151).
    assert page.inner_text("#act") == "⛵ Ruoriin"
    assert "Radio" in page.inner_text("#act2")
    act(page, "Tornista jäälle")
    assert page.evaluate("G.mode") == "ice"
    page.evaluate("closeCard(); run(() => walker.climbing || walker.rise, 6); walker.x = hatchX(); drawHud()")
    page.click("#act")
    # Down the tower into the control room, and the helm button is there to press.
    page.evaluate("run(() => crew.to, 6); step(1 / 60); drawHud()")
    assert page.evaluate("[G.mode, crew.room, crew.y]") == ["home", "ohjaamo", 0]
    assert page.inner_text("#act") == "⛵ Ruoriin"
    page.click("#act")
    assert page.evaluate("G.mode") == "sub"
    assert page.errors == []


def test_the_ladder_climbs_up_the_tower_and_its_hatch_opens_only_in_an_opening(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("sub.x = 273; sub.y = 30")
    inside(page)
    # The stick up at the ladder climbs from the upper deck into the tower, to the top under the hatch.
    page.evaluate("crew.x = LADDER; crew.y = UP; input.y = -1; run(() => crew.y > TOP, 3); input.y = 0; step(1 / 60); drawHud()")
    assert page.evaluate("[G.mode, crew.room, crew.y === TOP]") == ["home", "torni", True]
    assert page.inner_text("#roomName") == "TORNI · TIKKAAT ↕"
    # Under water the hatch stays shut, and says why.
    assert page.inner_text("#act") == "🔒 Luukku: SISU on veden alla"
    assert page.is_disabled("#act")
    page.evaluate("input.y = -1; run(() => true, 0.5); input.y = 0")
    assert page.evaluate("G.mode") == "home"
    assert "Luukku ei aukea" in toast(page)
    # Down again to the lower deck, past the upper one, by the stick.
    page.evaluate("input.y = 1; run(() => crew.y < LOW, 4); input.y = 0; step(1 / 60)")
    assert page.evaluate("crew.y") == 2
    page.evaluate("closeHome()")
    surface(page)
    inside(page)
    to_tower(page)
    x, y = page.evaluate("[sub.x + sub.face * crew.x, sub.y + crew.y]")
    page.evaluate("input.y = -1; step(1 / 60); input.y = 0")
    assert page.evaluate("G.mode") == "ice"
    # Out of the hatch from where the person stood: up through it onto the tower's top, then down its side.
    assert page.evaluate("[walker.x, walker.y, walker.rise]") == [pytest.approx(x), pytest.approx(y, abs=0.1), True]
    page.evaluate("closeCard(); run(() => walker.rise, 3)")
    assert page.evaluate("walker.y") == pytest.approx(page.evaluate("sub.y - 5.2"), abs=0.01)
    page.evaluate("run(() => walker.climbing, 3)")
    assert page.evaluate("walker.y") == pytest.approx(page.evaluate("sub.y - 2.3"), abs=0.01)
    # The inside fades out as the view widens over the ice: one smooth move, no cut.
    page.evaluate("G.hold = false")
    page.wait_for_function("G.homeT < 0.05")
    assert page.errors == []


def test_out_through_the_tower_to_the_station_and_back_down_into_the_control_room(site, browser):
    page = open_game(site, browser)
    ready(page)
    page.evaluate("G.s.inv.osat = 0")
    surface(page)
    v6.out_on_the_ice(page)
    assert page.evaluate("[walker.climbing, walker.y === sub.y - 2.3, walker.warm > 95]") == [False, True, True]
    walk_to(page, 205)
    page.evaluate("input.x = -1; run(() => !G.paused, 10); input.x = 0")
    page.click("#card button:has-text('Jatka')")
    walk_to(page, 121)
    assert sorted(page.evaluate("G.carry")) == ["pinta:l", "pinta:o1", "pinta:o2", "pinta:r1", "pinta:r2"]
    walk_to(page, page.evaluate("hatchX()"))
    assert page.inner_text("#act") == "⬇️ Alas torniin"
    page.click("#act")
    # In at the tower's top, then down the ladder by itself into the control room.
    assert page.evaluate("[G.mode, crew.room, crew.x === LADDER, crew.y === TOP]") == ["home", "torni", True, True]
    assert page.evaluate("[G.s.inv.ruoka, G.s.inv.osat, G.s.inv.laake, G.s.flags.pinta]") == [4, 2, 2, True]
    page.evaluate("run(() => crew.to, 6); step(1 / 60)")
    assert page.evaluate("[crew.room, crew.y]") == ["ohjaamo", 0]
    assert page.errors == []


def test_a_speared_fish_is_carried_home_and_two_make_a_ration_in_the_galley(site, browser):
    page = open_game(site, browser)
    ready(page)
    dive_near_school(page, 0)
    page.evaluate("drawHud()")
    assert page.is_visible("#harp") and not page.is_visible("#ping")
    # The first school says what the harpoon is for.
    page.evaluate("step(1 / 60)")
    assert "Kalaparvi" in toast(page)
    got = shoot_nearest(page)
    assert got and got.startswith("kala:1:0:")
    k = int(got.split(":")[3])
    assert page.evaluate("G.s.caught[0]") == [k]
    assert page.evaluate("fishNow().filter(f => f.n === 0).length") == 6
    page.evaluate("drawHud()")
    assert page.inner_text("#carry") == "🐟1"
    # The harpoon reloads before the next shot.
    page.evaluate("fire()")
    assert page.evaluate("G.spear") is None
    assert shoot_nearest(page)
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; drawHud()")
    page.click("#act")
    assert page.evaluate("G.s.inv.kala") == 2
    assert "🐟 2" in toast(page) and "paista keittiössä" in toast(page)
    walk(page, "keittio")
    assert page.inner_text("#act2") == "🐟 Paista kalat (2)"
    page.click("#act2")
    assert page.evaluate("[G.s.inv.kala, G.s.inv.ruoka]") == [0, 3]
    page.evaluate("drawHud()")
    assert not page.is_visible("#act2")
    # One fish alone makes no meal.
    page.evaluate("G.s.inv.kala = 1; drawHud()")
    assert page.is_disabled("#act2")
    assert page.errors == []


def test_a_spear_stops_in_a_wall_and_one_that_misses_flies_only_so_far(site, browser):
    page = open_game(site, browser)
    ready(page)
    dive_near_school(page, 0)
    # Into the floor below: it sticks there, and no fish is taken.
    page.evaluate("diver.vx = 0; diver.vy = 4; G.pending = {}; G.s.caught = {}; diver.y = floorY(diver.x) - 1.5; fire()")
    page.evaluate("for (let i = 0; i < 30 && !G.spear.stuck; i++) stepSpear(1 / 60)")
    assert page.evaluate("[!!G.spear.stuck, solid(G.spear.x, G.spear.y), G.carry.length]") == [True, True, 0]
    page.evaluate("for (let i = 0; i < 60 && G.spear; i++) stepSpear(1 / 60)")
    assert page.evaluate("G.spear") is None
    # Out into empty water: gone after its range.
    page.evaluate("diver.x = 900; diver.y = 60; diver.vx = diver.vy = 0; diver.dir = 1; G.harpCd = 0; fire();"
                  " window.far = 0; for (let i = 0; i < 90 && G.spear; i++) { stepSpear(1 / 60); if (G.spear) far = G.spear.d; }")
    assert page.evaluate("G.spear") is None
    assert page.evaluate("far") <= 11.5
    assert page.errors == []


def test_every_fish_swims_in_open_water_shies_from_the_diver_and_the_schools_come_back_each_night(site, browser):
    page = open_game(site, browser)
    ready(page)
    bad = page.evaluate("""(() => { const bad = [];
      for (let t = 0; t < 900; t += 2.5) SCHOOLS.forEach((S, n) => { for (let k = 0; k < S[4]; k++) {
        const f = schoolFish(n, k, t); if (solid(f.x, f.y) || f.y < ICE_Y + 0.5 || f.y > TANK_MAX - 5) bad.push([n, k, t]); } });
      return bad; })()""")
    assert bad == []
    # A diver close by: the fish keep their distance (but not out of reach of the harpoon).
    near = page.evaluate("""(() => { const f = schoolFish(1, 0, 10), g = schoolFish(1, 0, 10, [{ x: f.x + 1, y: f.y }]);
      return [Math.hypot(f.x + 1 - g.x, f.y - g.y), SPEAR.range]; })()""")
    assert 3 < near[0] < near[1]
    page.evaluate("G.s.caught = { 0: [1, 2], 3: [0] }; sleep(); closeCard()")
    assert page.evaluate("G.s.caught") == {}
    assert page.errors == []


def test_samples_are_studied_in_the_lab_for_a_lasting_help(site, browser):
    page = open_game(site, browser)
    ready(page)
    # The station's sample, brought home.
    v4.dive_at(page, "asema")
    v4.take(page, "it.k === 'nayte' && it.site === 'asema'")
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; drawHud()")
    page.click("#act")
    assert "🧪 1" in toast(page) and "vie labraan" in toast(page)
    walk(page, "kartta")
    assert page.inner_text("#roomName") == "LABRA JA KARTAT"
    assert page.inner_text("#act") == "🔬 Laboratorio (1)"
    assert page.inner_text("#act2") == "🗺️ Lokikirja"
    page.click("#act")
    page.click("#card button:has-text('Tutki: Merivesinäyte')")
    assert "Tästä lähtien: SISU kulkee 10 % nopeammin." in page.inner_text("#card")
    assert "1 / 5 näytettä tutkittu" in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    assert "✓ Merivesinäyte" in page.inner_text("#card")
    page.click("#card button:has-text('Lokikirja')")
    assert "Lokikirja" in page.inner_text("#card")
    page.evaluate("closeCard(); drawHud()")
    assert page.inner_text("#act") == "🔬 Laboratorio"
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE}')).lab") == {"vesi": True}
    # Every sample's help, before and after.
    helps = "[lab('vesi', 1.1), lab('jaa', 0.5), lab('bakteeri', 0.45), pingR(), lab('suomu', 0.5)]"
    assert page.evaluate(helps) == [1.1, 1, 1, 450, 1]
    page.evaluate("Object.assign(G.s.lab, { jaa: true, bakteeri: true, pullo: true, suomu: true })")
    assert page.evaluate(helps) == [1.1, 0.5, 0.45, 600, 0.5]
    page.evaluate("closeHome(); sub.x = 700; sub.y = 40; sub.vx = 0; input.x = 1; run(() => true, 8); input.x = 0")
    assert page.evaluate("sub.vx") == pytest.approx(16 * 1.1, rel=0.03)
    page.evaluate("G.mode = 'dive'; diver.x = 3600; diver.y = 800")
    assert page.evaluate("chill()") == pytest.approx(1 + 0.35 * 0.45)
    assert page.errors == []


def test_there_are_five_samples_one_a_place_each_reachable(site, browser):
    page = open_game(site, browser)
    ready(page)
    found = page.evaluate("ITEMS.concat(ICE_ITEMS).filter(it => it.k === 'nayte').map(it => [it.site, it.sample])")
    assert sorted(found) == sorted([["asema", "vesi"], ["jaavuori", "jaa"], ["majakka", "bakteeri"], ["nordlys", "pullo"],
                                    ["majakka", "suomu"]])
    reach = page.evaluate(v4.REACH)
    for site_id, r in reach.items():
        for k, x, y, d in r["items"]:
            if k == "nayte":
                assert d is not None, f"the sample at {site_id} cannot be reached"
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 740), (390, 844), (740, 360)])
def test_the_harpoon_lab_and_galley_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h)
    ready(page)
    page.evaluate("G.s.inv.kala = 3; for (const it of ITEMS.concat(ICE_ITEMS)) if (it.k === 'nayte') G.s.got[it.id] = true")
    inside(page)
    walk(page, "keittio")
    assert page.evaluate(v4.OVERFLOW) == []
    walk(page, "kartta")
    page.click("#act")
    assert page.evaluate(v4.OVERFLOW) == []
    page.click("#card button:has-text('Tutki: Lähteiden bakteerimatto')")
    assert page.evaluate(v4.OVERFLOW) == []
    page.evaluate("closeCard(); closeHome()")
    dive_near_school(page, 3)
    page.evaluate("drawHud()")
    assert page.is_visible("#harp")
    assert page.evaluate(v4.OVERFLOW) == []
    page.click("#harp")
    assert page.evaluate("!!G.spear") is True
    assert page.errors == []


def test_the_sea_and_the_engines_sound_by_where_the_person_is(site, browser):
    page = open_game(site, browser)
    ready(page)
    # The first tap made the sound: the soundscape is running, without an error.
    assert page.evaluate("!!AC && !!BED") is True
    still = page.evaluate("mix()")
    assert still["sea"] > 0.5 and still["engine"] == pytest.approx(0.25) and still["wind"] == 0
    page.evaluate("sub.vx = SUB_SPEED")
    assert page.evaluate("mix().engine") == pytest.approx(1)
    assert page.evaluate("mix().prop") == pytest.approx(1)
    page.evaluate("sub.vx = 0; sub.y = 900")
    assert page.evaluate("mix().depth") == 1
    page.evaluate("sub.y = 30")
    inside(page)
    home = page.evaluate("mix()")
    assert home["hum"] > 0.5 and home["sea"] < still["sea"]
    page.evaluate("closeHome()")
    surface(page)
    v6.out_on_the_ice(page)
    ice = page.evaluate("mix()")
    assert ice["wind"] == 1 and ice["sea"] == 0 and ice["engine"] == 0
    page.evaluate("G.hold = false")
    page.wait_for_timeout(300)
    assert page.errors == []


def test_an_older_save_gets_no_fish_an_empty_lab_and_whole_schools(site, browser):
    s = v5.save_with(inv={"ohjain": 3}, up={"hose": 2})
    page = open_game(site, browser, save=json.dumps(s))
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    assert page.evaluate("[G.s.inv.kala, G.s.lab, G.s.caught, G.s.inv.ohjain, G.s.up.hose]") == [0, {}, {}, 3, 2]
    assert page.errors == []


def test_a_friend_s_speared_fish_goes_into_the_host_s_stores(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    x, y = host.evaluate("SCHOOLS[0].slice(0, 2)")
    host.evaluate(f"sub.x = {x} - 20; sub.y = {y} - 4; sub.vx = sub.vy = 0; net.subT = null")
    aino.wait_for_function(f"Math.abs(sub.x - ({x} - 20)) < 1")
    v5.stand(aino, "puvut")
    aino.click("#act")
    v5.stand(aino, "ilmalukko")
    aino.click("#act")
    aino.wait_for_function("G.mode === 'dive'")
    aino.evaluate(f"closeCard(); G.hold = true; diver.x = {x} - 8; diver.y = {y}; diver.vx = diver.vy = 0")
    got = shoot_nearest(aino)
    assert got is None  # the host decides: the fish is hers once its answer comes
    aino.wait_for_function("G.carry.some(id => id.startsWith('kala:'))")
    host.wait_for_function("Object.keys(G.held).some(id => id.startsWith('kala:')) && (G.s.caught[0] || []).length === 1")
    aino.wait_for_function("(G.s.caught[0] || []).length === 1 && fishNow().filter(f => f.n === 0).length === 6")
    aino.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false)")
    host.wait_for_function("G.s.inv.kala === 1")
    for p in (host, aino):
        assert p.errors == []


def test_a_friend_goes_onto_the_ice_by_the_tower_while_sisu_holds_still_and_their_haul_is_the_hosts(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"), saves=[v5.save_with(sub={"x": 273, "y": 20, "dir": 1}), None])
    v5.close_cards(host, aino)
    host.evaluate("G.s.flags.pinta = false; input.y = -1")
    host.wait_for_function("surfaced()")
    host.evaluate("input.y = 0")
    aino.wait_for_function("surfaced()")
    v5.stand(aino, "ohjaamo")
    aino.evaluate("walkTo(LADDER, -4)")
    aino.wait_for_function("crew.room === 'torni' && !crew.to")
    aino.click("#pad button:visible:has-text('Tornista jäälle')")
    aino.evaluate("closeCard()")
    host.wait_for_function("Object.values(net.others).some(o => o.mode === 'ice')")
    # The host at the helm cannot drive off while Aino is out on the ice, and the hatch shows open.
    x0 = host.evaluate("sub.x")
    host.evaluate("input.x = 1")
    host.wait_for_function("$('toast').textContent.includes('Aino on jäällä')")
    host.evaluate("input.x = 0")
    assert abs(host.evaluate("sub.x") - x0) < 0.5
    aino.evaluate("walker.climbing = walker.rise = false; walker.x = 137; walker.y = groundAt(137); walker.warm = 100; input.x = -1")
    aino.wait_for_function("G.carry.length >= 4 || G.paused")
    aino.evaluate("input.x = 0; if (G.paused) closeCard()")
    host.wait_for_function("Object.values(G.held).length >= 4")
    aino.evaluate("walker.x = hatchX(); walker.y = groundAt(walker.x); drawHud()")
    aino.click("#act")
    host.wait_for_function("G.s.inv.osat === 4 && G.s.flags.pinta === true")
    # Aino comes in at the tower's top and climbs down; the host sees her inside.
    aino.wait_for_function("G.mode === 'home' && crew.room === 'ohjaamo'")
    host.wait_for_function("Object.values(net.others).some(o => o.mode === 'home')")
    host.evaluate("draw()")
    assert aino.evaluate(f"localStorage.getItem('{SAVE}')") is None
    for p in (host, aino):
        assert p.errors == []
