"""Last Signal v13 (#300): v12's tests on v13, then v13's own (below "v13"): the research station Aurora (v12's A-3) as
three floors over the first opening, its survivors and the pump; wrecks in 1.5 m cells with rooms in order; food and
medicine only in crates; a bigger SISU; a camera that rides with SISU; steering by touch; icebergs, keels and floor
growth; quieter sounds.

Last Signal v12 (#300): crates carried one at a time, falling and piling up, shelved in SISU's storage (a shelved
crate's contents count in the stores); a bag of BAG small finds; the harpoon as its own gear; a hose that no longer
wears (no guides); natural iceberg caves; a two-floor weather station on the ice; thin-walled wrecks full of things;
the nomads' camp, trading what they know for food, medicine and supplies; no hull upgrades; a world 3.34 times as wide
with a short sonar, where a far place is found from a hint's search area on the chart."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v13/"
OLD = v4.SAVE
SAVE12 = v4.SAVE + "12"
SAVE13 = v4.SAVE + "13"


@pytest.fixture(autouse=True)
def _v12(monkeypatch):
    for m in (v4, v5):
        monkeypatch.setattr(m, "URL", URL)


toast = v5.toast


def game(site, browser, w=360, h=740, save=None, **flags):
    """A new game (or the given save) past the first cards, held still for the test to step."""
    page = v4.open_game(site, browser, w, h, save=save)
    if save:
        page.click("#jatka")
        page.evaluate("G.hold = true; input.x = input.y = 0; closeCard()")
    else:
        v4.new_game(page)
    page.evaluate(f"Object.assign(G.s.flags, {json.dumps({'pinged': True, 'kontti': True, 'asema': True, 'koti': True, 'letku': True, **flags})}); drawHud()")
    return page


def inside(page):
    page.evaluate("G.mode = 'sub'; sub.vx = sub.vy = 0; openHome(); closeCard(); drawHud()")


def stand(page, room_id, x=None):
    v5.stand(page, room_id)
    if x is not None:
        page.evaluate(f"crew.x = {x}; enterRoom(true); drawHud()")


def dive(page, site_id, kit="tank", harp=False):
    """Parks SISU at the site's spot and swims out of the airlock."""
    page.evaluate(f"""(() => {{ const s = SITES.find(s => s.id === '{site_id}') || BERG_SITE;
      sub.x = s.spot[0]; sub.y = s.spot[1]; sub.vx = sub.vy = 0; G.mode = 'home';
      crew.suit = true; crew.kit = '{kit}'; crew.harp = {str(harp).lower()}; startDive(); if (G.paused) closeCard(); drawHud(); }})()""")
    assert page.evaluate("G.mode") == "dive"


def run(page, js_cond, sec=10):
    page.evaluate(f"run(() => {js_cond}, {sec})")


# ---------- the world ----------

def test_the_world_is_wider_the_sonar_shorter_and_the_hull_takes_any_depth(site, browser):
    page = game(site, browser, pinged=False)
    assert page.evaluate("WORLD_W") > 13000
    assert page.evaluate("[pingR(), HEAR]") == [150, 300]
    assert page.evaluate("typeof RATING") == "undefined"
    page.click("#ping")
    page.evaluate("run(() => true, 0.5); drawHud()")
    # From the bay the sonar hears the container 270 m off, but a ping (150 m) does not name it yet; the wrecks far east
    # are neither heard nor known.
    assert page.evaluate("[!!G.s.heard.kontti, !!G.s.known.kontti, !!G.s.heard.polaris, !!G.s.known.polaris]") == [True, False, False, False]
    assert page.inner_text("#depth").startswith("▼ ") and "/" not in page.inner_text("#depth")
    # Deep down nothing hurts the hull any more.
    page.evaluate("sub.x = SITES.find(s => s.id === 'nordlys').spot[0]; sub.y = 860; G.s.m.hull = 80; run(() => true, 3)")
    assert page.evaluate("G.s.m.hull") == 80
    assert page.errors == []


# Flood-fills the water a diver can swim from a site's parking spot (0.5 m steps, the diver's size) and says, for every
# find and crate there, whether it can be reached and how far it is from the nearest air: the spot or an air pocket
# on the way (null when it cannot be reached).
REACH = """() => {
  const out = {}, groups = {};
  for (const it of ITEMS) (groups[it.site] = groups[it.site] || { items: [], crates: [] }).items.push(it);
  for (const c of G.s.crates) if (c.w === 'sea') { const s = c.id.split(':')[0]; (groups[s] = groups[s] || { items: [], crates: [] }).crates.push(c); }
  const k = (x, y) => Math.round(x * 2) + ',' + Math.round(y * 2);
  for (const [site, g] of Object.entries(groups)) {
    const S = SITES.find(s => s.id === site);
    const spots = S ? [S.spot] : [BERG_SITE.spot, BERG_EAST.spot];
    const box = S ? [S.x - 14, S.x + S.w * C + 14, S.y - 14, S.y + S.h * C + 14] : [BERG_X[0] - 50, BERG_X[1] + 40, 0, 210];
    const flood = from => {
      const seen = new Map(), q = [];
      for (const [sx, sy] of from) { const p = [Math.round(sx * 2) / 2, Math.round(sy * 2) / 2]; seen.set(k(...p), 0); q.push(p); }
      for (let h = 0; h < q.length; h++) {
        const [x, y] = q[h], d = seen.get(k(x, y));
        for (const [dx, dy] of [[0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) {
          const nx = x + dx, ny = y + dy;
          if (ny < 1 || seen.has(k(nx, ny)) || diverHits(nx, ny)) continue;
          if (!spots.some(([sx, sy]) => Math.hypot(nx - sx, ny - sy) < 25) && !(nx > box[0] && nx < box[1] && ny > box[2] && ny < box[3])) continue;
          seen.set(k(nx, ny), d + 0.5); q.push([nx, ny]);
        }
      }
      return seen;
    };
    const near = (m, x, y, r) => { let best = null;
      for (let dx = -r; dx <= r; dx += 0.5) for (let dy = -r; dy <= r; dy += 0.5) {
        const v = m.get(k(x + dx, y + dy));
        if (v != null && Math.hypot(dx, dy) <= r && (best == null || v < best)) best = v;
      } return best; };
    const swim = flood(spots);
    const air = flood(spots.concat(g.items.filter(it => it.k === 'ilma' && near(swim, it.x, it.y, 1.5) != null).map(it => [it.x, it.y])));
    out[site] = { parks: spots.every(([x, y]) => !subHits(x, y)),
      items: g.items.map(it => [it.id, it.k, near(swim, it.x, it.y, 1.5) == null ? null : near(air, it.x, it.y, 1.5)]),
      crates: g.crates.map(c => [c.id, near(swim, c.x, c.y - BOX_H / 2 - 0.6, 1.4)]) };
  }
  return out;
}"""


def test_every_site_parks_and_every_find_and_crate_can_be_reached(site, browser):
    page = game(site, browser)
    reach = page.evaluate(REACH)
    bad = []
    for sid, r in reach.items():
        if not r["parks"]:
            bad.append((sid, "parks"))
        bad += [(sid, i, d) for i, k, d in r["items"] if d is None or d > 130]
        bad += [(sid, c) for c, d in r["crates"] if d is None]
    assert bad == []
    # The crates rest where the world put them, on a plate or the sea floor, not in the water.
    assert page.evaluate("G.s.crates.filter(c => c.w === 'sea' && restBelow(c, 0.02) == null).map(c => c.id)") == []
    assert page.evaluate("G.s.crates.length") > 100
    assert page.errors == []


def test_the_iceberg_caves_are_big_chambers_joined_by_narrow_passages(site, browser):
    page = game(site, browser)
    caves = page.evaluate("CAVES.map(c => c[4])")
    chambers, passages = [r for r in caves if r >= 4], [r for r in caves if r < 2]
    assert len(chambers) >= 7 and len(passages) >= 18
    # Every cave find lies in open water, and the walls are rough, not round.
    assert page.evaluate("ITEMS.filter(it => it.site === 'jaavuori' && (diverHits(it.x, it.y) || caveD(it.x, it.y) > -0.3)).map(it => it.id)") == []
    assert page.evaluate("Math.abs(caveD(HALL.x + 9.5, HALL.y) - caveD(HALL.x, HALL.y - 9.5)) > 0.2")
    assert page.errors == []


def test_wreck_walls_are_thin_plates_and_rooms_have_furniture(site, browser):
    page = game(site, browser)
    # A wall cell is water but for a 0.3 m plate along its middle.
    got = page.evaluate("""(() => { const s = SITES.find(s => s.id === 'nordvik');
      const x = s.x + 8 * C + C / 2, y = s.y + 3 * C + C / 2;  // a bulkhead
      return [solid(x, y), solid(x - 0.5, y), solid(x + 0.5, y), solid(x, y - 0.9)]; })()""")
    assert got == [True, False, False, True]
    assert page.evaluate("SITES.filter(s => s.shell === 'ship').every(s => s.decor.length >= 3)")
    assert page.evaluate("['aurora', 'kestrel'].every(id => SITES.some(s => s.id === id))")
    assert page.errors == []


# ---------- crates ----------

def lift_near(page):
    page.evaluate("step(1 / 60); drawHud()")
    label = page.inner_text("#act")
    assert label.startswith("📦 Nosta"), label
    page.click("#act")
    page.evaluate("drawHud()")


def test_a_crate_is_lifted_carried_and_let_go_of_and_sinks_onto_another(site, browser):
    page = game(site, browser)
    dive(page, "polaris")
    a, b = page.evaluate("""(() => { const cs = G.s.crates.filter(c => c.id.startsWith('polaris:') && c.w === 'sea');
      return [cs[0].id, cs[1].id]; })()""")
    page.evaluate(f"const c = crateById('{a}'); diver.x = c.x; diver.y = c.y - 1; drawHud()")
    lift_near(page)
    assert page.evaluate(f"[crateById('{a}').w, crateById('{a}').by]") == ["held", "me"]
    assert "📦" in page.inner_text("#carry")
    # Carried, it goes with the diver; let go of over the other crate, it sinks slowly and lands on top of it.
    page.evaluate(f"const o = crateById('{b}'); diver.x = o.x - diver.dir * 0.75; diver.y = o.y - 1.9; run(() => true, 0.2); drawHud()")
    assert page.inner_text("#act") == "⬇️ Laske laatikko"
    page.click("#act")
    t = page.evaluate(f"(() => {{ let t = 0; while (crateById('{a}').f && t < 20) {{ step(1 / 60); t += 1 / 60; }} return t; }})()")
    assert 0.5 < t < 20
    assert page.evaluate(f"Math.abs(crateById('{a}').y - (crateById('{b}').y - BOX_H)) < 0.06")
    # Lifting the lower one lets the upper one fall to where it stood.
    page.evaluate(f"const o = crateById('{b}'); diver.x = o.x; diver.y = o.y - 0.8; act('lift', '{b}'); run(() => true, 4)")
    assert page.evaluate(f"crateById('{a}').f") in (0, None)
    assert page.evaluate(f"crateById('{a}').y > crateById('{b}').y - 0.01 || crateById('{b}').w === 'held'")
    assert page.errors == []


def carry_home(page, cid):
    """Lifts the crate, swims it to the airlock and goes in: the person stands in the airlock holding it."""
    page.evaluate(f"const c = crateById('{cid}'); sub.x = c.x - 20; sub.y = Math.min(c.y - 6, floorY(sub.x) - 10); sub.dir = sub.face = 1;"
                  f" diver.x = c.x; diver.y = c.y - 1; act('lift', '{cid}'); const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); closeCard()")
    assert page.evaluate(f"[G.mode, crateById('{cid}').w, crateById('{cid}').by]") == ["home", "held", "me"]


def test_a_food_crate_shelved_in_the_stores_counts_and_leaves_when_eaten(site, browser):
    page = game(site, browser)
    dive(page, "polaris")
    cid = page.evaluate("G.s.crates.find(c => c.id.startsWith('polaris:') && c.k === 'ruoka').id")
    n = page.evaluate(f"crateById('{cid}').n")
    carry_home(page, cid)
    before = page.evaluate("stock('ruoka')")
    v4.walk(page, "varasto")
    assert page.inner_text("#act").startswith("📦 Hyllyyn (0/8)")
    page.click("#act")
    assert page.evaluate(f"[crateById('{cid}').w, crateById('{cid}').slot]") == ["shelf", 0]
    assert page.evaluate("stock('ruoka')") == before + n
    # Eating takes from the crate first; empty, it leaves the shelf and frees its slot.
    page.evaluate(f"for (let k = 0; k < {n}; k++) {{ G.s.m.food = 10; act('eat'); }}")
    assert page.evaluate(f"crateById('{cid}') || null") is None
    assert page.evaluate("[stock('ruoka'), shelfFree()]") == [before, 0]
    page.evaluate("save()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE13}')).crates.some(c => c.id === '{cid}')") is False
    assert page.errors == []


def test_the_shelf_has_eight_places_and_the_store_card_takes_one_down(site, browser):
    page = game(site, browser)
    inside(page)
    page.evaluate("for (const c of G.s.crates.slice(0, 9)) { c.w = 'held'; c.by = 'me'; act('shelf', c.id); }")
    assert page.evaluate("[shelved().length, shelfFree()]") == [8, -1]
    page.evaluate("const c = G.s.crates[8]; c.w = 'held'; c.by = 'me'")
    stand(page, "varasto", 1.6)
    assert page.inner_text("#act") == "📦 Hylly on täynnä"
    assert page.is_disabled("#act")
    page.evaluate("act('drop', [G.s.crates[8].id, ...dropSpot()]); run(() => true, 1); drawHud()")
    page.click("#pad button:has-text('🗄️ Varasto')")
    assert "Hyllyssä 8/8" in page.inner_text("#card")
    page.click("#card button:has-text('⬇️ 📦')")
    assert page.evaluate("[shelved().length, !!myCrate()]") == [7, True]
    assert page.errors == []


def test_a_loose_crate_in_sisu_is_in_the_way_until_lifted(site, browser):
    page = game(site, browser)
    inside(page)
    stand(page, "puvut", 6)
    page.evaluate("const c = G.s.crates[0]; c.w = 'sub'; c.x = 3.2; c.y = LOW; c.f = 0")
    page.evaluate("walkTo(-4, 1.2); run(() => crew.to, 6)")
    assert 3.2 + 0.45 < page.evaluate("crew.x") < 4.0
    assert "tiellä" in toast(page)
    page.evaluate("drawHud()")
    lift_near(page)
    page.evaluate("walkTo(-4, 1.2); run(() => crew.to, 6)")
    assert page.evaluate("Math.abs(crew.x + 4) < 0.05")
    # Let go of over the ladder's hatch on the upper deck, a crate falls through to the lower deck.
    page.evaluate("walkTo(LADDER - 0.8, -1.2); run(() => crew.to, 8); crew.dir = 1; act('drop', [myCrate() ? myCrate().id : '', 'sub', LADDER, -0.9]); run(() => true, 2)")
    assert page.evaluate("Math.abs(G.s.crates[0].y - LOW) < 0.01")
    assert page.errors == []


def test_the_harpoon_is_its_own_gear_and_leaves_no_hand_for_a_crate(site, browser):
    page = game(site, browser)
    inside(page)
    v4.walk(page, "puvut")
    v4.act(page, "Säiliöpuku")
    page.evaluate("drawHud()")
    assert page.inner_text("#act") == "🔱 Ota harppuuna"
    dive(page, "polaris", harp=False)
    assert not page.is_visible("#harp")
    page.evaluate("G.harpCd = 0; fire()")
    assert page.evaluate("G.spear") is None
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); closeCard()")
    v4.walk(page, "puvut")
    v4.act(page, "Ota harppuuna")
    assert page.evaluate("crew.harp") is True
    dive(page, "polaris", harp=True)
    assert page.is_visible("#harp")
    page.evaluate("const c = G.s.crates.find(c => c.id.startsWith('polaris:')); diver.x = c.x; diver.y = c.y - 1; drawHud()")
    assert page.inner_text("#act") == "🔱 Harppuuna kädessä"
    assert page.is_disabled("#act")
    assert page.errors == []


def test_the_hose_never_wears_and_the_workshop_has_no_hull_or_guides(site, browser):
    page = game(site, browser)
    dive(page, "nordvik", kit="hose")
    # Round the wreck's corners to its far end: the hose catches on corners but never wears.
    page.evaluate("""(() => { const s = SITES.find(s => s.id === 'nordvik');
      for (const [x, y] of [[s.x - 3, s.y + 2], [s.x - 3, s.y + 4.5 * C], [s.x + 5, s.y + 4.5 * C], [s.x + 25, s.y + 4.5 * C], [s.x + 40, s.y + 4.5 * C]]) {
        for (let k = 0; k < 400 && Math.hypot(x - diver.x, y - diver.y) > 0.6; k++) {
          const l = Math.hypot(x - diver.x, y - diver.y); input.x = (x - diver.x) / l; input.y = (y - diver.y) / l; step(1 / 60); if (G.paused) closeCard(); } }
      input.x = input.y = 0; })()""")
    assert page.evaluate("hose.pts.length") >= 1
    assert page.evaluate("'wear' in hose || 'cut' in hose") is False
    page.evaluate("drawHud()")
    assert page.inner_text("#airS").endswith(" m")
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); closeCard()")
    v4.walk(page, "paja")
    v4.act(page, "Parannukset")
    text = page.inner_text("#card")
    assert "Paineenkesto" not in text and "ohjain" not in text and "Happisäiliö" in text
    assert page.errors == []


def test_the_bag_holds_eight_small_finds(site, browser):
    page = game(site, browser)
    dive(page, "kestrel")
    page.evaluate("for (const it of ITEMS.filter(i => i.k !== 'loki' && i.k !== 'ilma' && i.site !== 'jaavuori')) {"
                  " diver.x = it.x; diver.y = it.y; step(1 / 60); if (G.paused) closeCard(); }")
    assert page.evaluate("G.carry.length") == 8
    assert "8/8" in page.inner_text("#carry")
    assert "Reppu on täynnä" in toast(page)
    assert page.errors == []


# ---------- hints, the nomads, the chart ----------

def surface_at(page, n):
    page.evaluate(f"sub.x = holeMid({n}); sub.y = 24; sub.vx = sub.vy = 0; G.mode = 'sub'; input.y = -1; run(() => sub.y > SURF, 15); input.y = 0; sub.vx = sub.vy = 0")
    assert page.evaluate("surfaced()")


def out_on_ice(page):
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); goIce(); closeCard(); run(() => walker.climbing || walker.rise, 6)")
    assert page.evaluate("G.mode") == "ice"


def walk_ice(page, x):
    """Walks the person on the ice to x, reading every note on the way."""
    page.evaluate(f"walker.to = {x}; walker.toFl = 0; for (let k = 0; k < 20 && walker.to != null; k++) {{ run(() => walker.to != null && !G.paused, 40);"
                  f" if (G.paused) {{ closeCard(); walker.to = {x}; }} }}")


def test_the_station_s_diary_points_to_the_nomads_who_trade_what_they_know(site, browser):
    page = game(site, browser)
    page.evaluate("act('take', 'pinta:loki'); closeCard()")
    assert page.evaluate("[!!G.s.known.railo1, goalNow().target]") == [True, "railo1"]
    # Food and medicine from the stores into the bag, then up at the nomads' opening and over to their elder.
    inside(page)
    stand(page, "varasto", 1.6)
    page.click("#pad button:has-text('🗄️ Varasto')")
    page.click("#card button:has-text('Reppuun 🥫')")
    page.click("#card button:has-text('Reppuun 💊')")
    assert page.evaluate("[G.carry.length, G.s.pack.ruoka, G.s.pack.laake, stock('ruoka')]") == [2, 1, 1, 1]
    page.evaluate("closeCard(); closeHome()")
    surface_at(page, 1)
    out_on_ice(page)
    assert page.evaluate("G.carry.length") == 2
    walk_ice(page, "CAMP.elder")
    page.evaluate("drawHud()")
    assert page.inner_text("#act") == "🤝 Vaihtokauppa"
    page.click("#act")
    assert "💊 1" in page.inner_text("#card") and "🥫 1" in page.inner_text("#card")
    assert page.evaluate(v4.OVERFLOW) == []
    page.click("#card button:has-text('🤝 Anna')")
    assert "hylkykenttä" in page.inner_text("#card").lower()
    assert page.evaluate("[G.s.trade, G.carry.length, !!G.s.areas.polaris, !!G.s.areas.nordvik, G.s.pack.ruoka]") == [1, 0, True, True, 0]
    assert page.evaluate("goalNow().target") == "area:polaris"
    # By the fire the cold stays away.
    page.evaluate("closeCard(); walker.warm = 50; run(() => true, 2)")
    assert page.evaluate("walker.warm") > 50
    assert page.errors == []


def test_the_autopilot_takes_sisu_to_a_hint_s_area_where_the_sonar_finds_the_wreck(site, browser):
    page = game(site, browser, paivakirja=True)
    page.evaluate("G.s.trade = 1; learn('hylyt'); sub.x = 400; sub.y = 60")
    area = page.evaluate("areas().find(a => a.site === 'polaris')")
    assert 50 < page.evaluate(f"Math.hypot({area['x']} - contacts().find(c => c.id === 'polaris').x, {area['y']} - contacts().find(c => c.id === 'polaris').y)") < 150
    inside(page)
    stand(page, "kartta")
    page.click("#pad button:has-text('Merikartta')")
    page.evaluate("closeCard(); G.paused = true; G.card = 'chart'")
    page.evaluate("CV.sel = 'area:polaris'; drawChart()")
    assert "Tutkittava alue" in page.inner_text("#pickName")
    page.click("#pickGo")
    assert page.evaluate("G.auto && G.auto.id") == "area:polaris"
    page.evaluate("closeChart(); run(() => G.auto, 240)")
    assert page.evaluate("G.auto") is None
    assert "Perillä alueella" in toast(page)
    assert page.evaluate(f"Math.hypot(sub.x - {area['x']}, sub.y - {area['y']})") < 30
    # Within the area the sonar hears the wreck; a ping close enough names it, and its area leaves the chart.
    page.evaluate("mapStep()")
    assert page.evaluate("!!G.s.heard.polaris")
    page.evaluate("const c = contacts().find(c => c.id === 'polaris'); sub.x = c.x - 60; G.pingCd = 0; G.mode = 'sub'; doPing(); drawHud()")
    assert page.evaluate("[!!G.s.known.polaris, areas().some(a => a.site === 'polaris')]") == [True, False]
    assert page.errors == []


def test_every_hint_s_area_lies_in_open_water_near_its_place_and_the_autopilot_finds_a_way(site, browser):
    page = game(site, browser)
    got = page.evaluate("""(() => { for (const key of Object.keys(HINTS)) learn(key);
      return areas().map(a => { const sp = areaSpot(a), c = contacts().find(k => k.id === a.site);
        sub.x = 400; sub.y = 60;
        return [a.site, Math.hypot(a.x - c.x, a.y - c.y), subFits(...sp), !!autoRoute(sp[0], sp[1])]; }); })()""")
    assert len(got) == 12
    assert [g[0] for g in got if not (20 < g[1] < 150 and g[2] and g[3])] == []
    assert page.errors == []


def test_logs_put_the_next_place_s_area_on_the_chart(site, browser):
    page = game(site, browser, polaris=True, ingrid=True, pumppu=1)
    page.evaluate("act('take', ITEMS.find(i => i.log === 'nordvik').id); closeCard()")
    assert page.evaluate("[!!G.s.areas.itarailo, goalNow().target]") == [True, "area:itarailo"]
    page.evaluate("act('take', ITEMS.find(i => i.log === 'k7').id); closeCard()")
    assert page.evaluate("!!G.s.areas.saga")
    assert page.errors == []


def test_the_weather_station_has_two_floors_joined_by_a_ladder(site, browser):
    page = game(site, browser)
    page.evaluate("learn('saa')")
    surface_at(page, 4)
    out_on_ice(page)
    walk_ice(page, "SAA.ladder + 3")
    assert page.evaluate("[walker.fl, bldAt(walker.x) && bldAt(walker.x).id]") == [0, "saa"]
    page.evaluate("drawHud()")
    assert page.evaluate("$('roomName').textContent") == "Sääasema · Varasto"
    # A tap upstairs walks to the ladder and climbs it; the diary there points to the cargo ship.
    page.evaluate("tapIce(6284, SAA.floors[1] - 1); run(() => walker.to != null || walker.ladder != null, 30); if (G.paused) closeCard()")
    assert page.evaluate("[walker.fl, Math.abs(walker.y - SAA.floors[1]) < 0.01]") == [1, True]
    assert page.evaluate("!!G.s.got['saa:loki'] && !!G.s.areas.kestrel")
    page.evaluate("drawHud()")
    assert "Sääkoppi" in page.evaluate("$('roomName').textContent")
    # The stick down at the ladder climbs back down.
    page.evaluate("walker.to = SAA.ladder; walker.toFl = 1; run(() => walker.to != null, 10); input.y = 1; run(() => walker.fl === 1 || walker.ladder != null, 5); input.y = 0")
    assert page.evaluate("walker.fl") == 0
    assert page.errors == []


def test_a_crate_from_the_ice_station_comes_into_sisu_through_the_tower(site, browser):
    page = game(site, browser)
    surface_at(page, 0)
    out_on_ice(page)
    walk_ice(page, "293")
    page.evaluate("drawHud()")
    lift_near(page)
    cid = page.evaluate("myCrate().id")
    walk_ice(page, "hatchX()")
    page.evaluate("climbIn(); run(() => G.mode === 'ice', 20)")
    assert page.evaluate(f"[G.mode, crateById('{cid}').w, crateById('{cid}').hw]") == ["home", "held", "sub"]
    assert page.errors == []


# ---------- saves ----------

V11 = {"v": 1, "day": 7, "t": 3000, "sub": {"x": 1500, "y": 200, "dir": 1}, "m": {"food": 60, "health": 80, "hull": 90},
       "inv": {"ruoka": 3, "laake": 1, "osat": 2, "vahvistin": 0, "antenni": 0, "kortti": 0, "ohjain": 3, "kala": 0},
       "up": {"hull": 3, "tank": 2, "hose": 1, "lamp": 1}, "got": {"polaris:4,6": True}, "known": {"kontti": True, "polaris": True},
       "flags": {"pinged": True, "koti": True, "kontti": True, "asema": True, "polaris": True, "nordvik": True},
       "finds": [{"id": "f4", "k": "ohjain", "x": 1000, "y": 200}], "findN": 5, "guides": [[1200, 230]], "lab": {}, "caught": {},
       "heard": {"polaris": 1}, "seen": {"polaris": 1}, "chart": "AAAA", "cave": ""}


def test_a_v11_save_moves_into_the_wider_world_under_its_own_key(site, browser):
    page = v4.open_game(site, browser, save=json.dumps(V11))
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    s = page.evaluate("({ x: sub.x, day: G.s.day, osat: G.s.inv.osat, ohjain: 'ohjain' in G.s.inv, guides: 'guides' in G.s, up: G.s.up,"
                      " find: G.s.finds[0], crates: G.s.crates.length, k7: !!G.s.areas.itarailo, w12: G.s.w12 })")
    assert s["x"] == page.evaluate("WX(1500)") and s["day"] == 7
    assert s["osat"] == 4 and not s["ohjain"] and not s["guides"] and "hull" not in s["up"]
    assert s["find"]["k"] == "osa" and s["find"]["x"] == page.evaluate("WX(1000)")
    assert s["crates"] > 100 and s["w12"] == 1
    page.evaluate("save()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{OLD}')).sub.x") == 1500
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE13}')).sub.x") == s["x"]
    # The next open reads v12's own save, not v11's again.
    page.evaluate("G.s.day = 9; save()")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    assert page.evaluate("G.s.day") == 9
    assert page.errors == []


def test_a_reload_with_a_crate_in_hand_leaves_it_on_the_deck_and_packed_goods_back_in_the_stores(site, browser):
    page = game(site, browser)
    inside(page)
    stand(page, "puvut", 6)
    page.evaluate("const c = G.s.crates[0]; c.w = 'sub'; c.x = 5; c.y = LOW; c.f = 0; act('lift', c.id); run(() => true, 0.3)")
    stand(page, "varasto", 1.6)
    page.evaluate("act('pack', 'ruoka'); run(() => true, 0.2); save()")
    assert page.evaluate("[G.s.inv.ruoka, G.s.pack.ruoka]") == [1, 1]
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; run(() => true, 2)")
    assert page.evaluate("[G.s.crates[0].w, Math.abs(G.s.crates[0].y - LOW) < 0.01, G.s.inv.ruoka, G.s.pack.ruoka || 0]") == ["sub", True, 2, 0]
    assert page.errors == []


# ---------- with friends ----------

def test_a_friend_lifts_a_crate_and_shelves_it_in_the_host_s_sisu(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.evaluate("const c = G.s.crates[0]; c.w = 'sub'; c.x = 2.4; c.y = LOW; c.f = 0; save()")
    aino.wait_for_function("G.s.crates[0].w === 'sub'")
    v5.stand(aino, "varasto")
    aino.evaluate("crew.x = 2.4; drawHud()")
    aino.wait_for_function("document.querySelector('#act').textContent.startsWith('📦 Nosta')")
    aino.click("#act")
    host.wait_for_function("G.s.crates[0].w === 'held' && G.s.crates[0].by !== 'me'")
    aino.wait_for_function("!!myCrate()")
    aino.evaluate("drawHud()")
    aino.click("#act")
    host.wait_for_function("G.s.crates[0].w === 'shelf'")
    aino.wait_for_function("G.s.crates[0].w === 'shelf'")
    assert host.errors == [] and aino.errors == []


@pytest.mark.parametrize("how", ["reload", "continue"])
def test_goods_a_friend_packed_go_back_to_the_stores_when_their_phone_leaves(site, browser, how):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    before = host.evaluate("stock('ruoka')")
    v5.stand(aino, "varasto")
    aino.evaluate("act('pack', 'ruoka')")
    host.wait_for_function(f"stock('ruoka') === {before - 1} && G.s.pack.ruoka === 1")
    aino.wait_for_function("G.carry.length === 1")
    if how == "reload":
        aino.reload()  # back in the room: the host's R.on('hello') lets go of what they held
        host.wait_for_function(f"stock('ruoka') === {before} && !G.s.pack.ruoka", timeout=15000)
    else:
        host.evaluate("const id = Object.keys(net.others)[0]; letGo(id); delete net.others[id]")  # what R.on('continue') does
        assert host.evaluate(f"[stock('ruoka') === {before}, G.s.pack.ruoka]") == [True, 0]
    assert host.evaluate("Object.keys(G.held).length") == 0
    assert host.evaluate(f"JSON.parse(localStorage.getItem('{SAVE13}')).pack.ruoka") == 0
    assert host.errors == []


def test_two_people_reaching_for_one_crate_the_first_gets_it(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.evaluate("const c = G.s.crates[0]; c.w = 'sub'; c.x = 2.4; c.y = LOW; c.f = 0; save()")
    aino.wait_for_function("G.s.crates[0].w === 'sub'")
    # Aino's ask reaches the host after the host's own lift: the crate stays in the host's hands, Aino's hands stay empty.
    host.evaluate("act('lift', G.s.crates[0].id)")
    aino.evaluate("act('lift', G.s.crates[0].id)")
    host.wait_for_timeout(400)
    assert host.evaluate("[G.s.crates[0].w, G.s.crates[0].by === R.me]") == ["held", True]
    aino.wait_for_function("G.s.crates[0].w === 'held' && !myCrate()")
    # and the host lets go of it on the deck: both phones see it there
    host.evaluate("act('drop', [G.s.crates[0].id, 'sub', 3, 0.5]); run(() => true, 1)")
    aino.wait_for_function("G.s.crates[0].w === 'sub' && Math.abs(G.s.crates[0].y - LOW) < 0.05")
    assert host.errors == [] and aino.errors == []


def test_a_crate_let_go_of_over_an_opening_sinks_into_the_sea(site, browser):
    page = game(site, browser)
    page.evaluate("const c = G.s.crates.find(c => c.id === 'pinta:c1'); c.w = 'held'; c.by = 'me';"
                  " act('drop', [c.id, 'ice', holeMid(0) - 10, -2]); run(() => true, 4)")
    c = page.evaluate("(() => { const c = crateById('pinta:c1'); return [c.w, c.y > 1]; })()")
    assert c == ["sea", True]
    page.evaluate("run(() => crateById('pinta:c1').f, 200)")
    assert page.evaluate("Math.abs(crateById('pinta:c1').y - floorY(crateById('pinta:c1').x)) < 0.5")
    assert page.errors == []


# ---------- layout ----------

@pytest.mark.parametrize("w,h", [(360, 740), (390, 844), (740, 360)])
def test_the_store_camp_and_workshop_cards_fit(site, browser, w, h):
    page = game(site, browser, w, h)
    page.evaluate("for (const c of G.s.crates.slice(0, 8)) { c.w = 'held'; c.by = 'me'; act('shelf', c.id); }")
    inside(page)
    stand(page, "varasto", 1.6)
    page.evaluate("storeCard()")
    assert page.evaluate(v4.OVERFLOW) == []
    page.evaluate("closeCard(); upgradeCard()")
    assert page.evaluate(v4.OVERFLOW) == []
    page.evaluate("closeCard(); G.mode = 'ice'; walker.x = CAMP.elder; campCard()")
    assert page.evaluate(v4.OVERFLOW) == []
    # v13: Ingrid's card, before and after the pump
    page.evaluate("closeCard(); G.s.flags.ingrid = true; const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'; auroraCard('talk')")
    assert page.evaluate(v4.OVERFLOW) == []
    page.evaluate("closeCard(); act('pump')")
    assert page.evaluate(v4.OVERFLOW) == []
    assert page.errors == []


# ---------- v13 ----------

def climb_to(page, x, fl):
    page.evaluate(f"tapIce({x}, AUR.floors[{fl}] - 1); for (let k = 0; k < 8 && (walker.to != null || walker.ladder != null); k++) {{"
                  " run(() => (walker.to != null || walker.ladder != null) && !G.paused, 40); if (G.paused) closeCard(); } run(() => true, 0.05); drawHud()")


def test_aurora_is_three_floors_over_the_first_opening_and_its_survivors_get_a_pump(site, browser):
    page = game(site, browser)
    surface_at(page, 0)
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); run(() => true, 0.1); drawHud()")
    assert page.inner_text("#act") == "🚪 Aurora-asemalle"
    page.click("#act")
    page.evaluate("closeCard(); run(() => walker.climbing || walker.rise, 8); drawHud()")
    assert page.evaluate("[G.mode, bldAt(walker.x) === AUR, walker.fl, walker.warm]") == ["ice", True, 0, 100]
    assert page.evaluate("$('roomName').textContent") == "Aurora · Telakka"
    # Up one ladder to the hydroponics, where Ingrid points to Kestrel; up the next to the radio room and its diary.
    climb_to(page, 268, 1)
    assert page.evaluate("walker.fl") == 1 and page.inner_text("#act") == "💬 Puhu Ingridille"
    page.click("#act")
    assert "Kestrel" in page.inner_text("#card")
    assert page.evaluate("[!!G.s.flags.ingrid, !!G.s.areas.kestrel]") == [True, True]
    page.evaluate("closeCard()")
    climb_to(page, 258, 2)
    assert page.evaluate("[walker.fl, !!G.s.got['pinta:loki'], !!G.s.known.railo1]") == [2, True, True]
    # The pump from Kestrel's hold, carried up: the hydroponics turn green, two rations of greens a day.
    page.evaluate("const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'")
    climb_to(page, 268, 1)
    page.click("#act")
    page.click("#card button:has-text('🔧 Anna pumppu')")
    assert "lehdet" in page.inner_text("#card")
    assert page.evaluate("[!!G.s.flags.pumppu, G.s.crates.some(c => c.k === 'pumppu'), !!G.s.areas.kontit]") == [True, False, True]
    page.click("#card button:has-text('Ota tuoretta')")
    assert page.evaluate("G.carry.filter(id => id.startsWith('tuore:')).length") == 2
    page.evaluate("act('greens')")
    assert "Huomenna" in toast(page)
    # Down both ladders to the dock and in through the hatch: the greens go into the stores.
    before = page.evaluate("G.s.inv.ruoka")
    climb_to(page, "hatchX()", 0)
    assert page.inner_text("#act") == "⬇️ Alas torniin"
    page.click("#act")
    page.evaluate("run(() => G.mode === 'ice', 20)")
    assert page.evaluate("G.mode") == "home" and page.evaluate("G.s.inv.ruoka") == before + 2
    assert page.errors == []


def test_the_pump_lies_in_kestrel_s_hold_and_never_goes_on_the_shelf(site, browser):
    page = game(site, browser)
    assert page.evaluate("G.s.crates.filter(c => c.k === 'pumppu').map(c => c.id)") == ["kestrel:18,7"]
    inside(page)
    stand(page, "varasto", 1.6)
    page.evaluate("const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'; act('shelf', c.id)")
    assert page.evaluate("G.s.crates.find(c => c.k === 'pumppu').w") == "held"
    assert "Auroran" in toast(page)
    assert page.errors == []


def test_food_and_medicine_lie_only_in_crates(site, browser):
    page = game(site, browser)
    assert page.evaluate("allItems().filter(i => i.k === 'ruoka' || i.k === 'laake').map(i => i.id)") == []
    page.evaluate("G.s.finds = []; for (let n = 0; n < 6; n++) { G.s.finds = []; newFinds(); }")
    assert page.evaluate("G.s.finds.every(f => f.k === 'osa' || f.k === 'tarvike')")
    assert page.evaluate("G.s.crates.filter(c => c.k === 'ruoka').length") > 20
    assert page.errors == []


def test_every_wreck_has_its_rooms_in_order(site, browser):
    page = game(site, browser)
    assert page.evaluate("C") == 1.5
    got = page.evaluate("SITES.filter(s => s.shell === 'ship' || s.shell === 'rv').map(s => [s.id, ['w', 'h', 'e', 'g'].filter(ch => !s.decor.some(d => d[0] === ch))])")
    assert [g for g in got if g[1]] == []
    # A room is 2.7 m clear: a person (about 2 m) fits with room to spare, a diver passes a doorway.
    assert page.evaluate("2 * C - WALL") == pytest.approx(2.7)
    assert page.errors == []


def test_sisu_is_bigger_so_the_person_s_head_clears_the_lower_deck(site, browser):
    page = game(site, browser)
    person = 1.78 * 1.1
    assert page.evaluate("(LOW - 0.15) * SS") > person + 0.1
    assert page.evaluate("[subHits(sub.x, sub.y), airlock().x - sub.x > 12]") == [False, True]
    assert page.errors == []


def test_inside_on_the_autopilot_s_cruise_the_view_stays_on_the_person(site, browser):
    page = game(site, browser, paivakirja=True)
    page.evaluate("G.s.trade = 1; learn('hylyt'); sub.x = 400; sub.y = 60")
    inside(page)
    stand(page, "keittio")
    page.evaluate("act('auto', 'area:polaris'); closeCard()")
    worst = page.evaluate("""(() => { let worst = 0;
      for (let k = 0; k < 90; k++) step(1 / 60);  // the view settles inside first
      for (let k = 0; k < 600; k++) { step(1 / 60); const px = sub.x + sub.face * crew.x * SS; worst = Math.max(worst, Math.abs(px - G.cx) * G.sc); }
      return [worst, Math.hypot(sub.vx, sub.vy)]; })()""")
    assert worst[1] > 20  # cruising
    assert worst[0] < page.evaluate("W / 2 - 20")
    assert page.errors == []


def test_a_finger_on_the_sea_steers_sisu_there_and_the_stick_takes_over(site, browser):
    page = game(site, browser)
    page.evaluate("sub.x = 400; sub.y = 60; G.cx = sub.x; G.cy = sub.y; draw()")
    box = page.evaluate("(() => { const r = cv.getBoundingClientRect(); return [r.left, r.top]; })()")
    tx, ty = page.evaluate("[G.view.ox + 440 * G.view.sc, G.view.oy + 70 * G.view.sc]")
    page.mouse.move(box[0] + tx, box[1] + ty)
    page.mouse.down()
    page.evaluate("run(() => true, 2)")
    assert page.evaluate("G.subTo && G.subTo.hold") is True
    page.mouse.up()
    page.evaluate("run(() => G.subTo, 30)")
    assert page.evaluate("Math.hypot(sub.x - 440, sub.y - 70)") < 4
    page.evaluate("G.subTo = { x: 900, y: 60, hold: false, t: G.t }; input.x = -1; step(1 / 60); input.x = 0")
    assert page.evaluate("G.subTo") is None
    assert page.errors == []


def test_a_crate_in_the_arms_swings_round_with_the_turning_diver(site, browser):
    page = game(site, browser)
    dive(page, "polaris")
    page.evaluate("const c = G.s.crates.find(c => c.id.startsWith('polaris:')); diver.x = c.x; diver.y = c.y - 1; act('lift', c.id); run(() => true, 0.3)")
    jumps = page.evaluate("""(() => { const c = myCrate(); let px = c.x, worst = 0, far = 0;
      for (const ix of [-1, 1, -1]) for (let k = 0; k < 40; k++) { input.x = ix; step(1 / 60); worst = Math.max(worst, Math.abs(c.x - px - diver.vx / 60)); far = Math.max(far, Math.hypot(c.x - diver.x, c.y - diver.y)); px = c.x; }
      input.x = 0; return [worst, far]; })()""")
    assert jumps[0] < 0.25 and jumps[1] < 1.3
    assert page.errors == []


def test_icebergs_of_other_sizes_and_keels_under_the_ice_stop_sisu(site, browser):
    page = game(site, browser)
    got = page.evaluate("""BERGS.map(b => { const m = (b.x0 + b.x1) / 2; return [b.x1 - b.x0, solid(m, b.d * 0.5), solid(m, b.d + 4), underIce(m)]; })""")
    assert len(got) >= 4 and len({g[0] for g in got}) == len(got)
    assert all(g[1] and not g[2] and not g[3] for g in got)
    assert page.evaluate("(() => { for (let x = 300; x < 13000; x += 3) if (keel(x) > 2 && underIce(x)) return solid(x, ICE_Y + 1); return false; })()")
    # The autopilot goes under them: a route past the biggest exists and keeps clear of it.
    ok = page.evaluate("""(() => { const b = BERGS[2]; sub.x = b.x0 - 120; sub.y = 40; const r = autoRoute(b.x1 + 120, 40);
      if (!r) return false;
      for (let k = 1; k < r.length; k++) { const [ax, ay] = r[k - 1], [bx, by] = r[k], n = Math.ceil(Math.hypot(bx - ax, by - ay) / 2);
        for (let m = 0; m <= n; m++) if (subHits(ax + (bx - ax) * m / n, ay + (by - ay) * m / n)) return false; }
      return r.some(([x]) => x > b.x0 && x < b.x1); })()""")
    assert ok
    assert page.errors == []


def test_the_sea_s_hiss_the_engine_and_steps_in_the_snow_are_quieter(site, browser):
    page = game(site, browser)
    page.evaluate("""(() => { const vols = {}; window.heard13 = vols;
      BED = { next: 99 }; for (const k of ['sea', 'engine', 'hum', 'wind']) BED[k] = { set: o => { vols[k] = o.vol; }, playing: () => true };
      AC = { state: 'running' }; soundStep(0.01); })()""")
    v = page.evaluate("heard13")
    assert v["sea"] <= 0.75 * 0.35 + 1e-9 and v["engine"] <= 0.32 + 1e-9
    assert "sfx('lumi', 0.18)" in page.evaluate("stepIce.toString()")
    assert page.errors == []


V12 = {"v": 1, "w12": 1, "day": 3, "t": 500, "sub": {"x": 600, "y": 60, "dir": 1}, "m": {"food": 60, "health": 80, "hull": 90},
       "inv": {"ruoka": 1, "laake": 1, "osat": 0, "kala": 0, "tarvike": 0}, "up": {"tank": 1, "hose": 1, "lamp": 1},
       "got": {}, "known": {}, "flags": {"pinged": True}, "finds": [{"id": "f1", "k": "ruoka", "x": 900, "y": 120}], "findN": 2,
       "lab": {}, "caught": {}, "heard": {}, "seen": {}, "chart": "", "cave": "", "areas": {}, "trade": 0, "pack": {},
       "crates": [{"id": "polaris:5,4", "k": "ruoka", "n": 3, "w": "sea", "x": 2180, "y": 300},
                  {"id": "pinta:c1", "k": "osa", "n": 2, "w": "ice", "x": 126, "y": -2.8},
                  {"id": "nordvik:5,6", "k": "laake", "n": 2, "w": "shelf", "slot": 0, "x": 0, "y": 0}]}


def test_a_v12_save_comes_into_v13_under_its_own_key(site, browser):
    page = v4.open_game(site, browser)
    page.evaluate(f"localStorage.setItem('{SAVE12}', {json.dumps(json.dumps(V12))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    s = page.evaluate("({ day: G.s.day, shelf: G.s.crates.filter(c => c.w === 'shelf').map(c => c.id), old: G.s.crates.some(c => c.id === 'pinta:c1' && c.x < 240),"
                      " pump: G.s.crates.some(c => c.k === 'pumppu'), find: G.s.finds[0].k, w13: G.s.w13 })")
    assert s == {"day": 3, "shelf": ["nordvik:5,6"], "old": False, "pump": True, "find": "osa", "w13": 1}
    page.evaluate("save()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE12}')).w13") is None
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE13}')).w13") == 1
    assert page.errors == []


def test_a_reload_in_aurora_with_the_pump_in_hand_leaves_it_on_that_floor(site, browser):
    page = game(site, browser)
    surface_at(page, 0)
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); goIce(); closeCard(); run(() => walker.climbing || walker.rise, 8)")
    climb_to(page, 268, 1)
    page.evaluate("const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'; run(() => true, 0.3); save()")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); run(() => true, 3)")
    c = page.evaluate("(() => { const c = G.s.crates.find(c => c.k === 'pumppu'); return [c.w, Math.abs(c.y - AUR.floors[1]) < 0.05, c.x > AUR.x0 && c.x < AUR.x1]; })()")
    assert c == ["ice", True, True]
    assert page.errors == []


def test_a_friend_brings_the_pump_and_the_host_s_aurora_is_green(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    host.evaluate("const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = Object.keys(net.others)[0]; G.s.flags.ingrid = true; save()")
    aino.wait_for_function("G.s.flags.ingrid && !!myCrate()")
    aino.evaluate("act('pump')")
    host.wait_for_function("G.s.flags.pumppu && !G.s.crates.some(c => c.k === 'pumppu')")
    aino.wait_for_function("G.s.flags.pumppu")
    aino.evaluate("act('greens')")
    host.wait_for_function("Object.keys(G.held).filter(id => id.startsWith('tuore:')).length === 2")
    host.evaluate("act('greens')")
    assert "Huomenna" in toast(host)
    assert host.errors == [] and aino.errors == []


def v12_save(crates, **over):
    return {**V12, "crates": crates, **over}


def test_a_v12_save_keeps_the_crates_the_player_moved_and_the_wrecks_lack_what_was_taken(site, browser):
    # In v12 Polaris had 14 crates, one of them food: the player shelved it
    # (it is on the shelf), moved a junk crate onto the sea floor beside the wreck, and used up a supply crate (gone).
    untouched = [{"id": f"polaris:u{n}", "k": k, "n": 2, "w": "sea", "x": 2180, "y": 300}
                 for n, k in enumerate(["romu"] * 4 + ["tarvike"] * 3 + ["laake"] * 2 + ["osa"] * 2)]
    crates = untouched + [{"id": "polaris:5,4", "k": "ruoka", "n": 1, "w": "shelf", "slot": 0, "x": 0, "y": 0},
                          {"id": "polaris:9,7", "k": "romu", "n": 0, "w": "sea", "x": 2240, "y": 200, "vy": 0, "f": 0}]
    page = v4.open_game(site, browser)
    page.evaluate(f"localStorage.setItem('{SAVE12}', {json.dumps(json.dumps(v12_save(crates)))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); run(() => crateById('polaris:9,7').f, 60)")
    got = page.evaluate("""(() => { const s = G.s, pol = s.crates.filter(c => c.id.startsWith('polaris:'));
      const kinds = {}; for (const c of pol.filter(c => c.w === 'sea' && !('vy' in c && c.id === 'polaris:9,7'))) kinds[c.k] = (kinds[c.k] || 0) + 1;
      const moved = s.crates.find(c => c.id === 'polaris:9,7');
      return { shelf: s.crates.filter(c => c.w === 'shelf').map(c => c.id), moved: [moved.w, moved.x, Math.abs(moved.y - floorY(moved.x)) < 0.5],
        all: pol.length, v13: CRATES0.filter(c => c.id.startsWith('polaris:')).length, food: kinds.ruoka || 0 }; })()""")
    assert got["shelf"] == ["polaris:5,4"]
    assert got["moved"] == ["sea", 2240, True]           # where the player left it, settled on the floor
    # v12's 14, less the three taken (the shelved food, the moved junk, the used-up supplies): v13's crates less three,
    # plus the shelved and the moved ones kept as they were.
    assert got["all"] == got["v13"] - 3 + 2
    assert got["food"] == page.evaluate("CRATES0.filter(c => c.id.startsWith('polaris:') && c.k === 'ruoka').length") - 1
    assert page.errors == []


def test_greens_not_yet_brought_home_go_into_the_stores_after_a_reload(site, browser):
    page = game(site, browser, ingrid=True, pumppu=1)
    page.evaluate("G.mode = 'ice'; act('greens'); G.mode = 'sub'; save()")
    assert page.evaluate("[G.s.tuore, G.s.greens === G.s.day]") == [2, True]
    food = page.evaluate("G.s.inv.ruoka")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(v4.RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    assert page.evaluate("[G.s.inv.ruoka, G.s.tuore]") == [food + 2, 0]
    # brought home the normal way, they count once
    page.evaluate("G.s.day++; G.mode = 'ice'; act('greens'); act('home')")
    assert page.evaluate("[G.s.inv.ruoka, G.s.tuore]") == [food + 4, 0]
    assert page.errors == []


# Records every rectangle and ellipse drawAurora() draws from inside, with its colour.
DRAWN = """(() => { const out = [], f = ctx.fillRect, e = ctx.ellipse;
  ctx.fillRect = function (x, y, w, h) { out.push([x, x + w, String(ctx.fillStyle)]); return f.apply(this, arguments); };
  ctx.ellipse = function (x, y) { out.push([x, x, String(ctx.fillStyle)]); return e.apply(this, arguments); };
  ctx.setTransform(1, 0, 0, 1, 0, 0); drawAurora(); ctx.fillRect = f; ctx.ellipse = e; return out; })()"""


def test_aurora_s_furniture_stands_inside_it_and_its_plants_turn_green_with_the_pump(site, browser):
    page = game(site, browser)
    page.evaluate("G.mode = 'ice'; walker.x = 270; walker.y = AUR.floors[1]; walker.fl = 1")
    before = page.evaluate(DRAWN)
    lo, hi = page.evaluate("[AUR.x0 - 0.5, AUR.x1 + 0.5]")
    assert len(before) > 80
    # (the survivors are drawn round their own spot: only world-placed shapes count)
    assert [d for d in before if d[0] > 100 and (d[0] < lo or d[1] > hi)] == []
    assert not any(c in ("#5fc04a", "#3f9a3a") for *_, c in before)
    page.evaluate("G.s.flags.pumppu = 1")
    after = page.evaluate(DRAWN)
    assert sum(c in ("#5fc04a", "#3f9a3a") for *_, c in after) >= 40
    assert page.errors == []


def test_a_crate_the_player_left_at_v12_s_shelf_station_moves_into_aurora_s_store(site, browser):
    crates = [{"id": "pinta:c1", "k": "osa", "n": 1, "w": "ice", "x": 180, "y": -2.8, "vy": 0, "f": 0},
              {"id": "pinta:c2", "k": "ruoka", "n": 3, "w": "ice", "x": 128, "y": -2.8},
              {"id": "polaris:7,4", "k": "tarvike", "n": 2, "w": "ice", "x": 600, "y": -0.8, "vy": 0, "f": 0}]
    page = v4.open_game(site, browser)
    page.evaluate(f"localStorage.setItem('{SAVE12}', {json.dumps(json.dumps(v12_save(crates)))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); run(() => G.s.crates.some(c => c.f), 10)")
    got = page.evaluate("""(() => { const c = id => G.s.crates.find(c => c.id === id);
      return [[c('pinta:c1').n, bldAt(c('pinta:c1').x) === AUR, c('pinta:c1').y <= AUR.floors[0] + 0.01 && c('pinta:c1').y > AUR.floors[1] && !c('pinta:c1').f],
        [c('pinta:c2').n, c('pinta:c2').x > 240], [c('polaris:7,4').x, c('polaris:7,4').n]]; })()""")
    assert got[0] == [1, True, True]                      # the player's half-used crate, in Aurora's store (on its pile)
    assert got[1][1] is True                              # the untouched one is Aurora's own again
    assert got[2] == [600, 2]                             # one left out on the sea ice stays where it was
    assert page.errors == []
