"""Last Signal v15 (#329): v13's tests that still hold on v15 (crates, the shelf, the bag, the harpoon, the hose, the
weather station, friends...), then v15's own: no word of food and the container at the start; the sonar telling of
every new contact; a rebuilt sea (far more floor relief, big icebergs to pass under, rock arches with a tunnel, places in
hollows off the way, a far background layer); small openings where only the tower comes up; a dark and empty Aurora
whose power is fixed first with the fuses from its underwater module; the nomads, told of the shelter, moving in; the
pump in Saukko, the nearest wreck, shelved like a crate; and the autopilot's trip slept through once fed.

The tests of v4, v5 and v13 this file used to import are copied in below, run on v15; v15's own tests follow them."""

import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/last-signal/v16/"
SAVE = "ai-pelit:last-signal:peli"
SAVE12 = SAVE + "12"
SAVE13 = SAVE + "13"
SAVE15 = SAVE + "15"
LIT = {"sahko": 1, "pimea": 1}

RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"
OVERFLOW = """() => {
  const bad = [];
  for (const el of document.querySelectorAll('#panel:not(.hidden) .card, #menu:not(.hidden) .card'))
    if (el.scrollHeight > el.clientHeight + 1) bad.push('scrolls ' + el.className);
  for (const el of document.querySelectorAll('#panel:not(.hidden) button, #menu:not(.hidden) button, #pad:not(.hidden) button, #home'))
    if (!el.classList.contains('hidden') && getComputedStyle(el).display !== 'none') {
      const r = el.getBoundingClientRect();
      if (r.width && (r.top < 0 || r.left < 0 || r.bottom > innerHeight || r.right > innerWidth)) bad.push('out ' + el.textContent);
    }
  return bad;
}"""

_opened = []


@pytest.fixture(autouse=True)
def _close_pages():
    yield
    while _opened:
        try:
            _opened.pop().close()
        except Exception:
            pass


def open_game(site, browser, w=360, h=740, save=None):
    shutil.copytree(ROOT / "games" / "last-signal", site.games / "last-signal")
    site.build()
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    _opened.append(ctx)
    if save:
        ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                            f" localStorage.setItem('{SAVE}', JSON.stringify({save})); }}")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true")
    page.evaluate(RUN)
    return page


def new_game(page):
    page.click("#uusi")
    assert "selviä huomiseen" in page.inner_text("#card")
    page.click("#card button:has-text('Aloita')")
    page.evaluate("G.hold = true; input.x = input.y = 0; drawHud()")


def inside_from_helm(page):
    """Goes inside from the helm, past the first visit's card."""
    page.evaluate("drawHud()")
    page.click("#home")
    assert page.evaluate("G.mode") == "home"
    if page.is_visible("#panel"):
        page.click("#card button:has-text('Selvä')")


def walk(page, room):
    """Walks the person to the middle of a room, as a tap there does, and waits until they stand still."""
    page.evaluate(f"""(() => {{ const r = ROOMS.find(r => r.id === '{room}');
      walkTo((Math.max(r.x0, -11) + Math.min(r.x1, 11.8)) / 2, r.deck ? 1.2 : -1.2); run(() => crew.to, 20); step(1 / 60); drawHud(); }})()""")
    assert page.evaluate("crew.room") == room


def act(page, text):
    """Presses the room's button that says text."""
    page.click(f"#pad button:visible:has-text('{text}')")


def save_with(**over):
    s = {"v": 1, "day": 4, "t": 900, "sub": {"x": 575, "y": 100, "dir": 1}, "m": {"food": 60, "health": 80, "hull": 90},
         "inv": {"ruoka": 1, "laake": 1, "osat": 2, "vahvistin": 0, "antenni": 0, "kortti": 0},
         "up": {"hull": 1, "tank": 1, "lamp": 1}, "got": {}, "known": {"kontti": True},
         "flags": {"pinged": True, "koti": True}, "finds": [], "findN": 3}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(s.get(k), dict):
            s[k] = {**s[k], **v}
        else:
            s[k] = v
    return s


def room(site, browser, names=("Eero", "Aino", "Ville"), saves=None, w=360, h=740):
    """Phones in one room, each with its nickname (and its own save, if given); the first makes the room and
    starts. Returns the pages once every phone is in the game, the cards closed."""
    saves = saves or [save_with()] + [None] * (len(names) - 1)
    shutil.copytree(ROOT / "games" / "last-signal", site.games / "last-signal")
    site.build()
    relay = Relay()
    pages = []
    for n, name in enumerate(names):
        ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
        _opened.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        if saves and saves[n]:
            ctx.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ sessionStorage.setItem('seeded', '1');"
                                f" localStorage.setItem('{SAVE}', {json.dumps(json.dumps(saves[n]))}); }}")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("window.drawn === true")
        page.evaluate(RUN)
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for g in guests:
        g.click("#multi")
        g.fill("#aipr-codeIn", code)
        g.click("#aipr-joinBtn")
        g.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(pages)}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("G.s && G.mode !== 'wait' && G.mode !== 'menu'")
    # Every friend is seen by the host, and the host by every friend.
    host.wait_for_function(f"Object.values(net.others).filter(o => o.mode !== 'wait').length === {len(guests)}")
    for g in guests:
        g.wait_for_function("Object.values(net.others).some(o => o.mode === 'sub')")
    return pages


def close_cards(*pages):
    for p in pages:
        p.evaluate("closeCard()")


def stand(page, room_id, x=None):
    """Puts the person in the room, standing still, as walking there would: in its middle, or at x."""
    page.evaluate(f"""(() => {{ const r = ROOMS.find(r => r.id === '{room_id}');
      Object.assign(crew, {{ x: (Math.max(r.x0, -11) + Math.min(r.x1, 11.8)) / 2, y: r.deck ? LOW : UP, to: null, moving: false,
        climbing: false }}); enterRoom(true); drawHud(); }})()""")
    assert page.evaluate("crew.room") == room_id
    if x is not None:
        page.evaluate(f"crew.x = {x}; enterRoom(true); drawHud()")


def toast(page):
    return page.evaluate("$('toast').classList.contains('hidden') ? '' : $('toast').textContent")


def game(site, browser, w=360, h=740, save=None, **flags):
    """A new game (or the given save) past the first cards, held still for the test to step."""
    page = open_game(site, browser, w, h, save=save)
    if save:
        page.click("#jatka")
        page.evaluate("G.hold = true; input.x = input.y = 0; closeCard()")
    else:
        new_game(page)
    page.evaluate(f"Object.assign(G.s.flags, {json.dumps({'pinged': True, 'kontti': True, 'asema': True, 'koti': True, 'letku': True, **flags})}); drawHud()")
    return page


def inside(page):
    page.evaluate("G.mode = 'sub'; sub.vx = sub.vy = 0; openHome(); closeCard(); drawHud()")


def dive(page, site_id, kit="tank", harp=False):
    """Parks SISU at the site's spot and swims out of the airlock."""
    page.evaluate(f"""(() => {{ const s = SITES.find(s => s.id === '{site_id}') || BERG_SITE;
      sub.x = s.spot[0]; sub.y = s.spot[1]; sub.vx = sub.vy = 0; G.mode = 'home';
      crew.suit = true; crew.kit = '{kit}'; crew.harp = {str(harp).lower()}; startDive(); if (G.paused) closeCard(); drawHud(); }})()""")
    assert page.evaluate("G.mode") == "dive"


def climb_to(page, x, fl):
    page.evaluate(f"tapIce({x}, AUR.floors[{fl}] - 1); for (let k = 0; k < 8 && (walker.to != null || walker.ladder != null); k++) {{"
                  " run(() => (walker.to != null || walker.ladder != null) && !G.paused, 40); if (G.paused) closeCard(); } run(() => true, 0.05); drawHud()")


def surface_at(page, n):
    """Brings SISU up in opening n, the small ones too (only the tower comes up there)."""
    page.evaluate(f"sub.x = holeMid({n}); sub.y = 24; sub.vx = sub.vy = 0; G.mode = 'sub'; input.y = -1;"
                  f" run(() => !surfaced(), 15); input.y = 0; sub.vx = sub.vy = 0")
    assert page.evaluate("surfaced()")


def up_to_aurora(page):
    surface_at(page, 0)
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); goIce(); if (G.paused) closeCard();"
                  " run(() => walker.climbing || walker.rise, 8); run(() => true, 0.1); drawHud()")
    assert page.evaluate("[G.mode, bldAt(walker.x) === AUR]") == ["ice", True]


def walk_aur(page, x, fl):
    """Walks (and climbs) in Aurora to x on floor fl, closing any card on the way."""
    climb_to(page, x, fl)
    page.evaluate("if (G.paused) closeCard(); run(() => true, 0.05); drawHud()")


# ---------- v13's tests of what v15 did not change ----------
# Left out: the start's goals, the station's diary and Aurora's survivors, the pump in Kestrel, saves read from v12's
# and v11's keys, the shelved food read back from v13's key, the icebergs' sizes and the next-area goal (v15's own
# versions are below).

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
    walk(page, "puvut")
    act(page, "Säiliöpuku")
    page.evaluate("drawHud()")
    assert page.inner_text("#act") == "🔱 Ota harppuuna"
    dive(page, "polaris", harp=False)
    assert not page.is_visible("#harp")
    page.evaluate("G.harpCd = 0; fire()")
    assert page.evaluate("G.spear") is None
    page.evaluate("const a = airlock(); diver.x = a.x; diver.y = a.y; endDive(false); closeCard()")
    walk(page, "puvut")
    act(page, "Ota harppuuna")
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
    walk(page, "paja")
    act(page, "Parannukset")
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

def surface_big(page, n):
    """v13's way up, in a big opening."""
    page.evaluate(f"sub.x = holeMid({n}); sub.y = 24; sub.vx = sub.vy = 0; G.mode = 'sub'; input.y = -1; run(() => sub.y > SURF, 15); input.y = 0; sub.vx = sub.vy = 0")
    assert page.evaluate("surfaced()")


def out_on_ice(page):
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); goIce(); closeCard(); run(() => walker.climbing || walker.rise, 6)")
    assert page.evaluate("G.mode") == "ice"


def walk_ice(page, x):
    """Walks the person on the ice to x, reading every note on the way."""
    page.evaluate(f"walker.to = {x}; walker.toFl = 0; for (let k = 0; k < 20 && walker.to != null; k++) {{ run(() => walker.to != null && !G.paused, 40);"
                  f" if (G.paused) {{ closeCard(); walker.to = {x}; }} }}")


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


def test_the_weather_station_has_two_floors_joined_by_a_ladder(site, browser):
    page = game(site, browser)
    page.evaluate("learn('saa')")
    surface_big(page, 4)
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
    surface_big(page, 0)
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
    page.evaluate(RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; run(() => true, 2)")
    assert page.evaluate("[G.s.crates[0].w, Math.abs(G.s.crates[0].y - LOW) < 0.01, G.s.inv.ruoka, G.s.pack.ruoka || 0]") == ["sub", True, 2, 0]
    assert page.errors == []


# ---------- with friends ----------

def test_a_friend_lifts_a_crate_and_shelves_it_in_the_host_s_sisu(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
    host.evaluate("const c = G.s.crates[0]; c.w = 'sub'; c.x = 2.4; c.y = LOW; c.f = 0; save()")
    aino.wait_for_function("G.s.crates[0].w === 'sub'")
    stand(aino, "varasto")
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
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
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
    assert page.evaluate(OVERFLOW) == []
    page.evaluate("closeCard(); upgradeCard()")
    assert page.evaluate(OVERFLOW) == []
    page.evaluate("closeCard(); G.mode = 'ice'; walker.x = CAMP.elder; campCard()")
    assert page.evaluate(OVERFLOW) == []
    # v13: Ingrid's card, before and after the pump
    page.evaluate("closeCard(); G.s.flags.ingrid = true; const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'; auroraCard('talk')")
    assert page.evaluate(OVERFLOW) == []
    page.evaluate("closeCard(); act('pump')")
    assert page.evaluate(OVERFLOW) == []
    assert page.errors == []


# ---------- v13 ----------

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


def test_the_sea_s_hiss_the_engine_and_steps_in_the_snow_are_quieter(site, browser):
    page = game(site, browser)
    page.evaluate("""(() => { const vols = {}; window.heard13 = vols;
      window.BED = {}; for (const k of ['sea', 'engine', 'hum', 'wind']) BED[k] = { set: o => { vols[k] = o.vol; }, playing: () => true }; BED.next = 99;
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


def test_a_reload_in_aurora_with_the_pump_in_hand_leaves_it_on_that_floor(site, browser):
    page = game(site, browser)
    surface_big(page, 0)
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); goIce(); closeCard(); run(() => walker.climbing || walker.rise, 8)")
    climb_to(page, 268, 1)
    page.evaluate("const c = G.s.crates.find(c => c.k === 'pumppu'); c.w = 'held'; c.by = 'me'; run(() => true, 0.3); save()")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(RUN)
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); run(() => true, 3)")
    c = page.evaluate("(() => { const c = G.s.crates.find(c => c.k === 'pumppu'); return [c.w, Math.abs(c.y - AUR.floors[1]) < 0.05, c.x > AUR.x0 && c.x < AUR.x1]; })()")
    assert c == ["ice", True, True]
    assert page.errors == []


def test_a_friend_brings_the_pump_and_the_host_s_aurora_is_green(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
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


def test_greens_not_yet_brought_home_go_into_the_stores_after_a_reload(site, browser):
    page = game(site, browser, ingrid=True, pumppu=1)
    page.evaluate("G.mode = 'ice'; act('greens'); G.mode = 'sub'; save()")
    assert page.evaluate("[G.s.tuore, G.s.greens === G.s.day]") == [2, True]
    food = page.evaluate("G.s.inv.ruoka")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.evaluate(RUN)
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
    page = open_game(site, browser)
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


# ---------- v15 ----------

# ---------- the start ----------

def test_no_word_of_food_and_the_container_at_the_start(site, browser):
    page = open_game(site, browser)
    new_game(page)
    assert page.inner_text("#goal").startswith("Paina 📡")
    page.click("#ping")
    page.evaluate("drawHud()")
    goal = page.inner_text("#goal")
    assert "Ruoka" not in goal and "kontti" not in goal.lower()
    assert goal.startswith("Tutkimusasema Aurora") and page.evaluate("goalNow().target") == "railo0"
    assert page.errors == []


def test_the_sonar_tells_of_every_new_contact_one_at_a_time(site, browser):
    page = game(site, browser)
    # Aurora's module and the opening over SISU are heard at once: each is said, kind, size and distance
    page.evaluate("G.sonarQ = []; G.s.heard = {}; mapStep()")
    said = page.evaluate("G.sonarQ.slice()")
    assert any(s.startswith("📡 Sonar: metallinen kohde · noin ") and " m länteen" in s for s in said)
    assert any("avovettä jään yllä" in s for s in said)
    # shown under the goal, one after another, never twice
    page.evaluate("G.sonarT = 0; step(1 / 60)")
    assert page.is_visible("#sonarMsg") and page.inner_text("#sonarMsg") == said[0]
    page.evaluate("mapStep()")
    assert page.evaluate("G.sonarQ.length") == len(said) - 1
    # a small opening, and the iceberg's caves: an onkalo
    page.evaluate("G.sonarQ = []; sub.x = holeMid(5); sub.y = 30; mapStep(); sub.x = BERG_SITE.x - 100; sub.y = 50; mapStep()")
    said = page.evaluate("G.sonarQ.slice()")
    assert any("pieni avanto jäässä · noin 18 m" in s for s in said)
    assert any(s.startswith("📡 Sonar: onkalo") for s in said)
    # it fits on a small phone and sideways
    page.evaluate("G.sonarT = 0; step(1 / 60)")
    assert page.evaluate("(() => { const r = $('sonarMsg').getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top > $('goalbar').getBoundingClientRect().bottom - 1; })()")
    assert page.errors == []


def test_a_friend_s_phone_hears_the_host_s_sonar_too(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
    host.evaluate("G.s.heard = {}; mapStep()")
    aino.wait_for_function("G.sonarQ.length > 0 || !$('sonarMsg').classList.contains('hidden')")
    assert host.errors == [] and aino.errors == []


# ---------- the world ----------

def test_the_floor_rises_and_falls_far_more_and_big_icebergs_reach_down(site, browser):
    page = game(site, browser)
    # the floor's swings: ridges and arches rising within 90 m of the ice all along the shallow sea, and a big drop and
    # climb every few hundred metres
    ridges = page.evaluate("""(() => { let n = 0, up = false; for (let x = 400; x < 7200; x += 6) {
      let t = floorY(x); for (const r of ROCKS) if (x > r.x0 && x < r.x1) for (let y = r.y0; y < t; y += 1) if (inRock(x, y)) { t = y; break; }
      const hi = t < 90; if (hi && !up) n++; up = hi; } return n; })()""")
    assert ridges >= 6
    # (v14's floor climbed and fell about 2 000 m in all, at these 50 m steps)
    swing = page.evaluate("(() => { let s = 0; for (let x = 400; x < 13000; x += 50) s += Math.abs(floorY(x + 50) - floorY(x)); return s; })()")
    assert swing > 5000
    # at least five icebergs reach 110 m or deeper, solid, with water under them
    deep = page.evaluate("BERGS.filter(b => b.d >= 110).map(b => { const m = (b.x0 + b.x1) / 2; return [solid(m, b.d * 0.6), solid(m, b.d * 0.95 + 8)]; })")
    assert len(deep) >= 5 and all(a and not b for a, b in deep)
    # the way is narrow where a ridge meets an iceberg and wide elsewhere
    gaps = page.evaluate("""BERGS.filter(b => b.d >= 110).map(b => { let g = 1e9; for (let x = b.x0 + 10; x < b.x1 - 10; x += 2) {
      let y = 0; while (y < 1400 && solid(x, y, true)) y += 0.5; const t = y; while (y < 1400 && !solid(x, y, true)) y += 0.5; g = Math.min(g, y - t); } return g; })""")
    assert min(gaps) < 40 and max(gaps) > 90
    assert page.errors == []


def test_the_autopilot_winds_under_icebergs_and_over_ridges_and_keeps_off_the_wrecks(site, browser):
    page = game(site, browser)
    route = page.evaluate("sub.x = 330; sub.y = 30; autoRoute(...contacts().find(c => c.id === 'majakka').spot)")
    assert route
    ys = [p[1] for p in route]
    under = page.evaluate(f"(() => {{ const r = {json.dumps(route)}; return BERGS.filter(b => b.d >= 110 && r.some(([x, y]) => x > b.x0 && x < b.x1 && y > b.d)).length; }})()")
    assert under >= 3 and max(ys) - min(ys) > 300
    # nowhere along it does SISU touch anything, and it passes no wreck within 12 m (they lie in hollows below)
    bad = page.evaluate(f"""(() => {{ const r = {json.dumps(route)}, out = [];
      for (let k = 1; k < r.length; k++) {{ const [ax, ay] = r[k - 1], [bx, by] = r[k], n = Math.ceil(Math.hypot(bx - ax, by - ay) / 2);
        for (let m = 0; m <= n; m++) {{ const x = ax + (bx - ax) * m / n, y = ay + (by - ay) * m / n;
          if (subHits(x, y)) out.push(['hits', Math.round(x), Math.round(y)]);
          for (const s of SITES) if (s.floor && x > s.x - 2 && x < s.x + s.w * C + 2 && y > s.y - 12) out.push(['near', s.id]); }} }}
      return out.slice(0, 5); }})()""")
    assert bad == []
    # every place lies in a hollow: the floor rises on both sides of it, higher than its roof
    hollow = page.evaluate("""HOLLOWS.map(([id]) => { const s = SITES.find(s => s.id === id), x1 = s.x + s.w * C;
      let l = 1e9, r = 1e9; for (let d = 2; d < 32; d += 1) { l = Math.min(l, floorY(s.x - d)); r = Math.min(r, floorY(x1 + d)); }
      return [id, l < s.y + 4 && r < s.y + 4]; })""")
    assert [h for h in hollow if not h[1]] == []
    assert page.errors == []


def test_rock_arches_give_two_ways_over_the_top_or_through_the_tunnel(site, browser):
    page = game(site, browser)
    got = page.evaluate("""ROCKS.map(r => { const fy = floorY(r.m), top = r.y0;
      const tunnel = !subHits(r.m, fy - r.th / 2), over = !subHits(r.m, (top + ICE_Y) / 2), rock = solid(r.m, (top + fy - r.th) / 2);
      return [tunnel, over, rock]; })""")
    assert len(got) >= 3 and all(all(g) for g in got)
    # SISU fits all the way through each tunnel, and all the way over each top
    through = page.evaluate("ROCKS.map(r => { for (let x = r.x0 + 16; x <= r.x1 - 16; x += 2) if (subHits(x, floorY(x) - r.th / 2 - 1)) return false; return true; })")
    over = page.evaluate("ROCKS.map(r => { for (let x = r.x0; x < r.x1; x += 2) { let t = floorY(x); for (let y = r.y0; y < t; y += 1) if (inRock(x, y)) { t = y; break; }"
                         " if (!Array.from({ length: Math.max(0, Math.floor(t - 18)) }, (_, k) => k + 9).some(y => !subHits(x, y))) return false; } return true; })")
    assert all(through) and all(over)
    assert page.errors == []


def test_a_far_background_layer_slides_behind_the_sea(site, browser):
    page = game(site, browser)
    # deeper than the ice everywhere, and it moves at half the speed of the near world
    assert page.evaluate("(() => { for (let F = 0; F < 7000; F += 37) if (backFloor(F) < ICE_Y + 20) return false; return true; })()")
    page.evaluate("G.cx = 600; draw(); window.bd1 = (W / 2 + (300 - G.cx * BACK_P) * G.sc); G.cx = 700; window.bd2 = (W / 2 + (300 - G.cx * BACK_P) * G.sc); draw()")
    assert page.evaluate("Math.abs(Math.abs(bd1 - bd2) - 50 * G.sc) < 0.01")
    assert page.errors == []


# ---------- small openings ----------

def test_in_a_small_opening_only_the_tower_comes_up_and_the_person_walks_out_over_planks(site, browser):
    page = game(site, browser)
    small = page.evaluate("HOLES.map((h, n) => h[2] ? n : -1).filter(n => n >= 0)")
    assert len(small) >= 3
    n = small[0]
    surface_at(page, n)
    # the hull stays under the ice, the tower's top is out of the water
    assert page.evaluate("[Math.abs(sub.y - holeSurf(holeAt(sub.x))) < 0.6, towerTop() < 0, sub.y - 2.4 * SS > 2.5]") == [True, True, True]
    assert page.evaluate(f"contacts().find(c => c.id === 'railo{n}').name") == "Pieni avanto"
    page.evaluate("openHome(); closeCard(); walkTo(LADDER, -4); run(() => crew.to, 20); run(() => true, 0.1); drawHud()")
    assert page.inner_text("#act") == "🧗 Tornista jäälle"
    page.click("#act")
    page.evaluate("closeCard(); run(() => walker.climbing || walker.rise, 8)")
    assert page.evaluate("Math.abs(walker.y - towerTop()) < 0.01")
    # over the plank onto the ice beside the opening, and back in through the tower
    page.evaluate(f"walker.to = HOLES[{n}][1] + 6; run(() => walker.to != null, 20)")
    assert page.evaluate(f"[walker.x > HOLES[{n}][1], walker.y]") == [True, -0.8]
    page.evaluate("climbIn(); run(() => G.mode === 'ice', 30)")
    assert page.evaluate("G.mode") == "home"
    assert page.errors == []


# ---------- Aurora: dark, then lit, then home to the nomads ----------

def test_aurora_starts_dark_and_empty_and_its_fuses_lie_in_its_underwater_module(site, browser):
    page = game(site, browser)
    up_to_aurora(page)
    page.evaluate("run(() => !G.paused, 1)")
    assert "pimeä" in page.inner_text("#card")
    page.evaluate("closeCard(); drawHud()")
    assert page.evaluate("[!!G.s.flags.pimea, G.s.flags.sahko || 0]") == [True, 0]
    assert page.inner_text("#goal").startswith("Auroran sähkökeskuksen sulakkeet") and page.evaluate("goalNow().target") == "asema"
    # nobody here, and in the dark nothing to read
    walk_aur(page, 268, 1)
    assert page.evaluate("[nearIngrid(), nearElder()]") == [False, False]
    walk_aur(page, 258, 2)
    assert page.evaluate("!!G.s.got['pinta:loki']") is False
    # by the fuse box: nothing to put in yet
    walk_aur(page, "FUSE.x", 0)
    assert page.inner_text("#act") == "🔌 Sulakkeet palaneet" and page.is_disabled("#act")
    # the spare fuses from the module under the station, home in the bag
    page.evaluate("climbIn(); run(() => G.mode === 'ice', 30)")
    dive(page, "asema")
    page.evaluate("const it = ITEMS.find(i => i.k === 'sulake'); diver.x = it.x; diver.y = it.y; step(1 / 60); const a = airlock(); endDive(false); closeCard()")
    assert page.evaluate("stock('sulake')") == 1
    page.evaluate("G.mode = 'sub'; drawHud()")
    assert page.inner_text("#goal").startswith("Vie varasulakkeet")
    up_to_aurora(page)
    walk_aur(page, "FUSE.x", 0)
    assert page.inner_text("#act") == "🔌 Vaihda sulakkeet"
    page.click("#act")
    assert "Valot syttyvät" in page.inner_text("#card")
    page.evaluate("closeCard(); drawHud()")
    assert page.evaluate("[!!G.s.flags.sahko, stock('sulake')]") == [True, 0]
    assert "radiopäiväkirja" in page.inner_text("#goal").lower()
    # now the diary can be read: it tells of the nomads, whom the player should tell of the shelter
    walk_aur(page, 258, 2)
    assert page.evaluate("[!!G.s.got['pinta:loki'], !!G.s.known.railo1, goalNow().target]") == [True, True, "railo1"]
    assert "Kerro heille" in page.inner_text("#goal") or "kerro heille" in page.inner_text("#goal")
    assert page.errors == []


def test_the_nomads_told_of_the_shelter_move_into_aurora_and_ingrid_asks_for_saukko_s_pump(site, browser):
    page = game(site, browser, paivakirja=True, **LIT)
    surface_at(page, 1)
    out_on_ice(page)
    walk_ice(page, "CAMP.elder")
    page.evaluate("drawHud()")
    assert page.inner_text("#act") == "💬 Puhu vanhimmalle"
    page.click("#act")
    assert "Aurorasta" in page.inner_text("#card")
    page.click("#card button:has-text('Kerro')")
    assert "Nomadit muuttavat" in page.inner_text("#card")
    page.evaluate("closeCard(); drawHud()")
    # the camp is left: no elder, no fire to warm by
    assert page.evaluate("[!!G.s.flags.suoja, nearElder(), nearFire(walker.x)]") == [True, False, False]
    assert page.evaluate("$('roomName').textContent") == "Hylätty leiri"
    assert "Ingridille" in page.inner_text("#goal")
    # in Aurora: Ingrid in the hydroponics points to Saukko, the elder trades in the mess
    page.evaluate("climbIn(); run(() => G.mode === 'ice', 30); G.mode = 'sub'")
    up_to_aurora(page)
    walk_aur(page, "CREW13[0].x", 1)
    assert page.inner_text("#act") == "💬 Puhu Ingridille"
    page.click("#act")
    assert "Saukko" in page.inner_text("#card")
    page.evaluate("closeCard(); drawHud()")
    assert page.evaluate("[!!G.s.flags.ingrid, !!G.s.areas.aurora, goalNow().site]") == [True, True, "aurora"]
    walk_aur(page, "ELDER.x", 1)
    assert page.inner_text("#act") == "🤝 Vaihtokauppa"
    page.click("#act")
    assert "Nomadien vanhin" in page.inner_text("#card")
    assert page.errors == []


def test_the_pump_lies_in_saukko_the_nearest_wreck_and_goes_on_the_shelf(site, browser):
    page = game(site, browser, paivakirja=True, suoja=1, ingrid=True, **LIT)
    assert page.evaluate("G.s.crates.filter(c => c.k === 'pumppu').map(c => c.id)") == ["aurora:14,6"]
    nearest = page.evaluate("SITES.filter(s => s.kind === 'HYLKY' || s.kind === 'SUURI HYLKY').sort((a, b) => Math.abs(a.x - 270) - Math.abs(b.x - 270))[0].id")
    assert nearest == "aurora"
    assert page.evaluate("SITES.find(s => s.id === 'aurora').x - AUR.x1") < 700
    dive(page, "aurora")
    carry_home(page, "aurora:14,6")
    stand(page, "varasto", 1.6)
    assert page.inner_text("#act").startswith("📦 Hyllyyn")
    page.click("#act")
    assert page.evaluate("crateById('aurora:14,6').w") == "shelf"
    assert page.evaluate("goalNow().text").startswith("Vie pumppu")
    page.evaluate("storeCard()")
    assert "VESIPUMPPU 🚰" in page.inner_text("#card")
    page.click("#card button:has-text('VESIPUMPPU')")
    assert page.evaluate("[crateById('aurora:14,6').w, crateById('aurora:14,6').by]") == ["held", "me"]
    # carried up into Aurora to Ingrid: the hydroponics turn green
    page.evaluate("closeCard(); G.mode = 'sub'")
    up_to_aurora(page)
    walk_aur(page, "CREW13[0].x", 1)
    page.click("#act")
    page.click("#card button:has-text('🔧 Anna pumppu')")
    assert page.evaluate("[!!G.s.flags.pumppu, G.s.crates.some(c => c.k === 'pumppu')]") == [True, False]
    page.evaluate("closeCard(); drawHud()")
    assert "vanhin" in page.inner_text("#goal")
    assert page.errors == []


def test_logs_put_the_next_place_s_area_on_the_chart(site, browser):
    page = game(site, browser, polaris=True, ingrid=True, pumppu=1, suoja=1, **LIT)
    page.evaluate("act('take', ITEMS.find(i => i.log === 'nordvik').id); closeCard()")
    assert page.evaluate("[!!G.s.areas.itarailo, goalNow().target]") == [True, "area:itarailo"]
    page.evaluate("act('take', ITEMS.find(i => i.log === 'k7').id); closeCard()")
    assert page.evaluate("!!G.s.areas.saga")
    assert page.errors == []


# ---------- the night's trip ----------

def test_sleeping_on_the_autopilot_takes_sisu_there_once_fed(site, browser):
    page = game(site, browser, **LIT)
    page.evaluate("G.s.known.kontit = G.s.heard.kontit = 1; act('auto', 'kontit'); G.s.m.food = 60")
    assert page.evaluate("!!G.auto")
    inside_from_helm(page)
    walk(page, "punkka")
    assert page.inner_text("#act") == "🧭 Syö ensin, niin yö vie perille" and page.is_disabled("#act")
    page.evaluate("act('sleepgo')")
    assert "Syö ensin" in toast(page) and page.evaluate("G.s.day") == 1
    page.evaluate("act('eat'); drawHud()")
    assert page.inner_text("#act") == "🧭 Nuku, autopilotti ajaa perille"
    end = page.evaluate("G.auto.pts[G.auto.pts.length - 1]")
    page.click("#act")
    assert page.evaluate("[G.s.day, !!G.auto]") == [2, False]
    assert page.evaluate(f"Math.hypot(sub.x - {end[0]}, sub.y - {end[1]})") < 1
    assert "autopilotti ajoi SISUn perille" in page.inner_text("#card")
    # on the way the sea went on the chart and the sonar heard what it passed
    assert page.evaluate("!!G.s.heard.polaris")
    # without the autopilot the night is the same as before
    page.evaluate("closeCard(); drawHud()")
    assert page.inner_text("#act") == "🛏️ Nuku yön yli"
    assert page.errors == []


def test_a_night_trip_to_an_opening_ends_surfaced_in_it(site, browser):
    page = game(site, browser, **LIT)
    page.evaluate("G.s.known.railo1 = G.s.heard.railo1 = 1; act('auto', 'railo1'); act('eat'); sleep(true)")
    assert page.evaluate("[surfaced(), holeAt(sub.x)]") == [True, 1]
    assert page.errors == []


# ---------- saves ----------

def test_a_v13_save_far_into_the_story_finds_aurora_lit_and_the_nomads_moved_in(site, browser):
    page = open_game(site, browser)
    s = page.evaluate("JSON.parse(JSON.stringify(fresh()))")
    s.update({"day": 6, "trade": 1, "sub": {"x": 3000, "y": 200, "dir": 1}, "chart": "AAAA"})
    s["flags"].update({"pinged": True, "kontti": True, "asema": True, "koti": True, "paivakirja": True, "ingrid": True, "polaris": True})
    s.pop("w15")
    # in v13's world the pump lay in Kestrel and Saukko held a junk crate where v15's pump is
    for c in s["crates"]:
        if c["id"] == "aurora:14,6":
            c["k"] = "romu"
        if c["id"] == "kestrel:18,7":
            c["k"] = "pumppu"
    page.evaluate(f"localStorage.setItem('{SAVE13}', {json.dumps(json.dumps(s))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    assert page.evaluate("[G.s.flags.sahko, G.s.flags.suoja, sub.x, sub.y]") == [1, 1, 330, 30]
    assert page.evaluate("!subHits(sub.x, sub.y)")
    assert page.evaluate("G.s.crates.filter(c => c.k === 'pumppu').map(c => c.id)") == ["aurora:14,6"]
    assert page.evaluate("goalNow().site") == "aurora"
    page.evaluate("save()")
    assert page.evaluate(f"[!!localStorage.getItem('{SAVE15}'), JSON.parse(localStorage.getItem('{SAVE13}')).sub.x]") == [True, 3000]
    assert page.errors == []


def test_a_v13_save_at_the_start_finds_aurora_dark(site, browser):
    s = save_with(w12=1, w13=1)
    page = open_game(site, browser)
    page.evaluate(f"localStorage.setItem('{SAVE13}', {json.dumps(json.dumps(s))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); drawHud()")
    assert page.evaluate("[G.s.flags.sahko || 0, G.s.flags.suoja || 0, goalNow().target]") == [0, 0, "railo0"]
    assert page.errors == []


def test_shelved_food_counts_and_the_save_is_v15_s_own(site, browser):
    page = game(site, browser)
    dive(page, "polaris")
    cid = page.evaluate("G.s.crates.find(c => c.id.startsWith('polaris:') && c.k === 'ruoka').id")
    carry_home(page, cid)
    walk(page, "varasto")
    page.click("#act")
    assert page.evaluate(f"crateById('{cid}').w") == "shelf"
    page.evaluate("save()")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE15}')).crates.find(c => c.id === '{cid}').w") == "shelf"
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 740), (390, 844), (740, 360)])
def test_the_new_cards_fit(site, browser, w, h):
    page = game(site, browser, w, h, paivakirja=True, **LIT)
    for js in ["auroraCard('power')", "auroraCard('moved')", "G.s.flags.suoja = 0; campCard()"]:
        page.evaluate(js)
        assert page.evaluate(OVERFLOW) == []
        page.evaluate("closeCard()")
    assert page.errors == []


def test_a_friend_fixes_aurora_s_power_and_tells_the_nomads_and_the_host_s_game_has_it(site, browser):
    host, aino = room(site, browser, names=("Eero", "Aino"))
    close_cards(host, aino)
    host.evaluate("G.s.inv.sulake = 1; G.s.flags.pimea = 1; sendState()")
    aino.wait_for_function("G.s.inv.sulake === 1")
    # both phones press at once: the first ask wins, the fuses are used once
    aino.evaluate("act('power')")
    host.evaluate("act('power')")
    host.wait_for_function("!!G.s.flags.sahko")
    assert host.evaluate("G.s.inv.sulake") == 0
    aino.wait_for_function("!!G.s.flags.sahko")
    aino.evaluate("act('suoja')")
    host.wait_for_function("!!G.s.flags.suoja")
    # the day it happened, kept in the host's own save
    assert host.evaluate("[G.s.flags.suoja === G.s.day, JSON.parse(localStorage.getItem('%s')).flags.suoja === G.s.day]" % SAVE15) == [True, True]
    assert host.errors == [] and aino.errors == []


def test_a_reload_keeps_aurora_lit_the_nomads_in_and_the_pump_on_the_shelf(site, browser):
    page = game(site, browser, paivakirja=True, suoja=1, ingrid=True, **LIT)
    page.evaluate("const c = crateById('aurora:14,6'); c.w = 'shelf'; c.slot = 0; save()")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    page.evaluate("closeCard(); drawHud()")
    assert page.evaluate("[G.s.flags.sahko, G.s.flags.suoja, crateById('aurora:14,6').w]") == [1, 1, "shelf"]
    assert page.evaluate("goalNow().text").startswith("Vie pumppu")
    assert page.errors == []


def test_with_every_trade_done_the_elder_still_hears_of_the_shelter_first(site, browser):
    # a player who traded everything at the camp before Aurora's power came back
    page = game(site, browser, paivakirja=True, **LIT)
    page.evaluate("G.s.trade = TRADES.length; campCard()")
    assert "Aurorasta" in page.inner_text("#card")
    page.click("#card button:has-text('Kerro')")
    assert page.evaluate("!!G.s.flags.suoja")
    page.evaluate("closeCard(); campCard()")
    assert "Kerroimme kaiken" in page.inner_text("#card")
    assert page.errors == []


def test_a_v13_save_with_saukko_s_junk_on_the_shelf_still_finds_the_pump(site, browser):
    page = open_game(site, browser)
    s = page.evaluate("JSON.parse(JSON.stringify(fresh()))")
    s.pop("w15")
    s["flags"].update({"pinged": True, "koti": True})
    for c in s["crates"]:
        if c["id"] == "aurora:14,6":  # in v13 this was a junk crate, which the player put on SISU's shelf
            c.update({"k": "romu", "n": 0, "junk": "KIVIÄ", "w": "shelf", "slot": 0})
        if c["id"] == "kestrel:18,7":
            c["k"] = "pumppu"
    page.evaluate(f"localStorage.setItem('{SAVE13}', {json.dumps(json.dumps(s))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard()")
    got = page.evaluate("G.s.crates.filter(c => c.id.startsWith('aurora:14,6')).map(c => [c.id, c.k, c.w]).sort()")
    assert got == [["aurora:14,6", "pumppu", "sea"], ["aurora:14,6:v13", "romu", "shelf"]]
    assert page.errors == []


def test_a_night_trip_tells_of_every_contact_it_heard(site, browser):
    page = game(site, browser, **LIT)
    page.evaluate("G.s.heard = { railo0: 1, asema: 1 }; G.s.known.majakka = G.s.heard.majakka = 1; sub.x = 330; sub.y = 30;"
                  " act('auto', 'majakka'); G.s.heard.majakka = 1; delete G.s.heard.majakka; G.s.known.majakka = 1; act('eat'); G.sonarQ = []; sleep(true)")
    n = page.evaluate("G.sonarQ.length")
    assert n > 3
    assert page.evaluate("G.sonarQ.every(t => /^📡 Sonar: .+ · (noin \\d+ m|pieni) · /.test(t))")
    card = page.inner_text("#card")
    assert "perille" in card and card.count("📡 Sonar:") == n
    assert page.errors == []
