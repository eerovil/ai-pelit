"""Last Signal v12 (#300): crates carried one at a time, falling and piling up, shelved in SISU's storage (a shelved
crate's contents count in the stores); a bag of BAG small finds; the harpoon as its own gear; a hose that no longer
wears (no guides); natural iceberg caves; a two-floor weather station on the ice; thin-walled wrecks full of things;
the nomads' camp, trading what they know for food, medicine and supplies; no hull upgrades; a world 3.34 times as wide
with a short sonar, where a far place is found from a hint's search area on the chart."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v12/"
OLD = v4.SAVE
SAVE12 = v4.SAVE + "12"


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
      const x = s.x + 8 * C + 1, y = s.y + 3 * C + 1;  // a bulkhead
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
    page.evaluate(f"const o = crateById('{b}'); diver.x = o.x - diver.dir * 0.75; diver.y = o.y - 3; run(() => true, 0.2); drawHud()")
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
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE12}')).crates.some(c => c.id === '{cid}')") is False
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
      for (const [x, y] of [[s.x - 3, s.y + 2], [s.x - 3, s.y + 9], [s.x + 6, s.y + 9], [s.x + 30, s.y + 9], [s.x + 36, s.y + 13]]) {
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
    page.evaluate("for (const it of ITEMS.filter(i => i.site === 'kestrel' && i.k !== 'loki' && i.k !== 'ilma').concat(ITEMS.filter(i => i.site === 'aurora' && i.k !== 'loki'))) {"
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
    page = game(site, browser, polaris=True)
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
    walk_ice(page, "128")
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
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE12}')).sub.x") == s["x"]
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
    assert page.errors == []
