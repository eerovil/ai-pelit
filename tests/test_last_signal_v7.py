"""Last Signal v7 (#145): two diving suits. The tank gear of v5 goes down to 260 m; the hose suit breathes through a hose
from SISU's airlock: its length holds the diver back, corners it bends round wear it (metal faster than ice), hose
guides clamped to a corner stop that, fish bite it, and a cut hose leaves a small emergency air supply. The workshop
upgrades the tank and the hose apart. Otherwise v7 plays as v6 (the ice, #143): v6's tests (and through them v5's and
v4's) run here on v7 too."""

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v6 as v6
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v7/"
SAVE = v4.SAVE


@pytest.fixture(autouse=True)
def _v7(monkeypatch):
    monkeypatch.setattr(v4, "URL", URL)
    monkeypatch.setattr(v5, "URL", URL)
    monkeypatch.setattr(v6, "URL", URL)


# v6's tests (with v5's and v4's), on v7, but for the ones about the tank deep down: since v7 only the hose suit dives
# below 260 m, and Nordlys's find is a hose reel. The tests below cover those.
CHANGED = {"test_the_deep_is_cold_and_glowing_fish_bump_but_never_end_the_game_alone_v5",
           "test_reading_the_chart_room_before_the_bridge_still_moves_on_alone_v5",
           "test_the_nordlys_tank_and_lyras_lamp_upgrade_the_gear_alone_v5"}
for _name in dir(v6):
    if _name.startswith("test_") and _name not in CHANGED:
        globals()[_name + "_v6"] = getattr(v6, _name)


# v7 renamed the suit button (two suits now) and keeps the tank gear above 260 m: v5's tests put on the tank gear,
# and dive in the hose suit where SISU parks deeper than that.
_act, _dive_at = v4.act, v4.dive_at


def act(page, text):
    _act(page, "Säiliöpuku" if text == "Pue sukelluspuku" else text)


def dive_at(page, site_id):
    page.evaluate(f"""(() => {{ const s = SITES.find(s => s.id === '{site_id}') || BERG_SITE;
      crew.kit = s.spot[1] > TANK_MAX - 2 ? 'hose' : 'tank'; G.s.flags.letku = true; }})()""")
    _dive_at(page, site_id)


@pytest.fixture(autouse=True)
def _helpers(monkeypatch):
    monkeypatch.setattr(v4, "act", act)
    monkeypatch.setattr(v4, "dive_at", dive_at)


open_game, new_game, inside, walk, take = v4.open_game, v4.new_game, v4.inside, v4.walk, v4.take

# A diver that swims to (x, y) by the stick, along the shortest way through the water (0.5 m steps), frame by frame.
SWIM = """() => {
  window.route = (tx, ty, box) => {
    const k = (x, y) => Math.round(x * 2) + ',' + Math.round(y * 2);
    const sx = Math.round(diver.x * 2) / 2, sy = Math.round(diver.y * 2) / 2;
    const dist = new Map([[k(sx, sy), 0]]), prev = new Map(), q = [[0, sx, sy]];
    let end = null;
    while (q.length) {
      let bi = 0; for (let i = 1; i < q.length; i++) if (q[i][0] < q[bi][0]) bi = i;
      const [d, x, y] = q[bi]; q[bi] = q[q.length - 1]; q.pop();
      if (d > dist.get(k(x, y))) continue;
      if (Math.hypot(x - tx, y - ty) < 1.2) { end = [x, y]; break; }
      for (const [dx, dy] of [[0.5,0],[-0.5,0],[0,0.5],[0,-0.5],[0.5,0.5],[0.5,-0.5],[-0.5,0.5],[-0.5,-0.5]]) {
        const nx = x + dx, ny = y + dy, nd = d + Math.hypot(dx, dy);
        if (ny < 1 || nx < box[0] || nx > box[1] || ny < box[2] || ny > box[3] || diverHits(nx, ny)) continue;
        if (dx && dy && (diverHits(x + dx, y) || diverHits(x, y + dy))) continue;
        const kk = k(nx, ny);
        if (dist.has(kk) && dist.get(kk) <= nd) continue;
        dist.set(kk, nd); prev.set(kk, [x, y]); q.push([nd, nx, ny]);
      }
    }
    if (!end) return null;
    const path = [end];
    while (prev.has(k(...path[0]))) path.unshift(prev.get(k(...path[0])));
    return path;
  };
  window.swim = (path, maxT = 120) => {
    let i = 0, t = 0;
    while (i < path.length - 1 && t < maxT && G.mode === 'dive') {
      while (i < path.length - 1 && Math.hypot(path[i][0] - diver.x, path[i][1] - diver.y) < 1.0) i++;
      const j = Math.min(path.length - 1, i + 2), dx = path[j][0] - diver.x, dy = path[j][1] - diver.y, l = Math.hypot(dx, dy) || 1;
      input.x = dx / l; input.y = dy / l;
      if (G.paused) closeCard();
      step(1 / 60); t += 1 / 60;
    }
    input.x = input.y = 0;
    return { at: i >= path.length - 1, len: hose.len, wear: hose.wear, cut: hose.cut, mode: G.mode };
  };
  // Parks SISU at a site, puts on the suit and swims to the find with the given id; the hose starts fresh.
  window.reach = (siteId, spot, dir, itemId, kit) => {
    const it = ITEMS.find(i => i.id === itemId), S = SITES.find(s => s.id === siteId);
    G.mode = 'sub'; G.paused = false; G.s.got = {}; G.held = {}; G.carry = [];
    sub.x = spot[0]; sub.y = spot[1]; sub.dir = sub.face = dir; sub.vx = sub.vy = 0;
    G.mode = 'home'; crew.suit = true; crew.kit = kit; startDive(); if (G.paused) closeCard();
    const box = S ? [S.x - 14, S.x + S.w * C + 14, S.y - 14, S.y + S.h * C + 14] : [2040, 2470, 0, 210];
    box[0] = Math.min(box[0], diver.x - 3); box[1] = Math.max(box[1], diver.x + 3);
    box[2] = Math.min(box[2], diver.y - 3); box[3] = Math.max(box[3], diver.y + 3);
    const path = route(it.x, it.y, box);
    return path ? swim(path) : null;
  };
}"""


def hose_game(site, browser, w=360, h=740, **up):
    page = open_game(site, browser, w, h)
    new_game(page)
    page.evaluate(SWIM)
    page.evaluate("G.s.flags.pinged = G.s.flags.letku = true; G.s.m.hull = 1e9; G.s.up.hull = 6; drawHud()")
    for k, v in up.items():
        page.evaluate(f"G.s.up.{k} = {v}")
    return page


def suit(page, kit):
    """Inside SISU: walks to the suit room and puts on the suit (🤿 Säiliöpuku or ➰ Letkupuku)."""
    inside(page)
    walk(page, "puvut")
    _act(page, kit)


def test_the_suit_room_has_two_suits_and_the_hose_suit_shows_the_hose_instead_of_air(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.flags.pinged = true")
    inside(page)
    walk(page, "puvut")
    assert page.inner_text("#act") == "🤿 Säiliöpuku" and page.inner_text("#act2") == "➰ Letkupuku"
    page.click("#act2")
    assert page.evaluate("[crew.suit, crew.kit]") == [True, "hose"]
    page.evaluate("drawHud()")
    assert page.inner_text("#act") == "🧥 Riisu puku" and not page.is_visible("#act2")
    # Out of the airlock at the container: the first hose dive explains the hose once.
    page.evaluate("const s = SITES.find(s => s.id === 'kontti'); sub.x = s.spot[0]; sub.y = s.spot[1]")
    walk(page, "ilmalukko")
    _act(page, "Sukella ulos")
    assert page.evaluate("[G.mode, diver.kit]") == ["dive", "hose"]
    assert "➰ Letku" in page.inner_text("#card") and "80 metriä" in page.inner_text("#card")
    page.click("#card button:has-text('Selvä')")
    assert page.evaluate("G.s.flags.letku") is True
    # No air runs out on the hose: the meter shows the metres of hose left.
    page.evaluate("run(() => true, 30); drawHud()")
    assert page.inner_text("#airI") == "➰"
    assert page.inner_text("#airS").endswith(" m")
    assert page.evaluate("[G.mode, hose.cut]") == ["dive", False]
    assert page.errors == []


def test_the_tank_gear_goes_no_deeper_than_260_m(site, browser):
    page = hose_game(site, browser)
    # Below 260 m the airlock opens only for the hose suit.
    page.evaluate("sub.x = 2600; sub.y = 300; sub.vx = sub.vy = 0; crew.suit = true; crew.kit = 'tank'; G.mode = 'home'; startDive()")
    assert page.evaluate("G.mode") == "home"
    assert "Säiliöpuku kestää vain 260 m" in v5.toast(page)
    page.evaluate("crew.kit = 'hose'; startDive()")
    assert page.evaluate("[G.mode, diver.kit]") == ["dive", "hose"]
    # A tank diver swimming down stops at 260 m.
    page.evaluate("G.mode = 'home'; sub.x = 2560; sub.y = 240; crew.kit = 'tank'; startDive(); diver.x = 2540; diver.y = 255;"
                  " input.y = 1; run(() => true, 4); input.y = 0")
    assert page.evaluate("[G.mode, diver.kit]") == ["dive", "tank"]
    assert 255 < page.evaluate("diver.y") <= 260.1
    assert page.errors == []


def test_the_hose_holds_the_diver_back_at_its_length_and_a_longer_hose_reaches_further(site, browser):
    page = hose_game(site, browser)
    page.evaluate("sub.x = 600; sub.y = 40; G.mode = 'home'; crew.suit = true; crew.kit = 'hose'; startDive();"
                  " input.x = 1; run(() => true, 40); input.x = 0; drawHud()")
    # Open water to the east: the diver stops where the hose ends.
    assert page.evaluate("Math.round(hoseLen(diver.x, diver.y))") == 80
    assert page.inner_text("#airS") == "0 m"
    assert "Letku on lopussa (80 m)" in v5.toast(page)
    page.evaluate("G.s.up.hose = 2; input.x = 1; run(() => true, 30); input.x = 0")
    assert page.evaluate("Math.round(hoseLen(diver.x, diver.y))") == 120
    assert page.errors == []


def test_a_corner_wears_the_hose_a_guide_stops_it_and_stays_where_it_was_clamped(site, browser):
    page = hose_game(site, browser)
    # Into the wreck Nordvik: the hose catches on the door frames.
    r = page.evaluate("reach('nordvik', SITES.find(s => s.id === 'nordvik').spot, 1, ITEMS.find(i => i.site === 'nordvik' && i.k === 'loki').id, 'hose')")
    assert r["at"] and not r["cut"]
    assert page.evaluate("hose.pts.length") >= 1
    worn = page.evaluate("hose.wear")
    assert 2 < worn < 60
    # Every corner on the way gets a guide: swimming on no longer wears the hose.
    assert page.evaluate("G.s.inv.ohjain") == 2
    page.evaluate("G.s.inv.ohjain = 9; for (const p of hose.pts.slice()) { diver.x = p[0]; diver.y = p[1]; drawHud();"
                  " if (G.acts[0] && G.acts[0].label.startsWith('📌')) G.acts[0].fn(); }")
    n = page.evaluate("G.s.guides.length")
    assert n >= 1 and page.evaluate("G.s.inv.ohjain") == 9 - n
    assert page.evaluate("rubbing()") == 0
    # The guides are saved with the game.
    assert len(page.evaluate("JSON.parse(localStorage.getItem('%s')).guides" % SAVE)) == n
    assert page.errors == []


def test_with_no_guides_left_the_button_says_so(site, browser):
    page = hose_game(site, browser)
    page.evaluate("reach('nordvik', SITES.find(s => s.id === 'nordvik').spot, 1, ITEMS.find(i => i.site === 'nordvik' && i.k === 'loki').id, 'hose')")
    page.evaluate("G.s.inv.ohjain = 0; const p = hose.pts[hose.pts.length - 1]; diver.x = p[0]; diver.y = p[1]; drawHud()")
    assert page.inner_text("#act") == "📌 Ohjaimet loppu"
    assert page.is_disabled("#act")


def test_a_cut_hose_leaves_the_emergency_air_and_the_airlock_still_brings_the_haul_home(site, browser):
    page = hose_game(site, browser)
    page.evaluate("const s = SITES.find(s => s.id === 'kontti'); sub.x = s.spot[0]; sub.y = s.spot[1]; G.mode = 'home';"
                  " crew.suit = true; crew.kit = 'hose'; startDive()")
    take(page, "it.site === 'kontti'")
    page.evaluate("wearHose(100); drawHud()")
    assert page.evaluate("[hose.cut, diver.air]") == [True, 25]
    assert "Letku katkesi" in v5.toast(page)
    assert page.inner_text("#airI") == "🫁"
    assert page.inner_text("#airS") == "25 s"
    page.evaluate("run(() => true, 5); drawHud()")
    assert page.inner_text("#airS") == "20 s"
    page.evaluate("diver.x = airlock().x; diver.y = airlock().y; drawHud()")
    page.click("#act")
    assert page.evaluate("[G.mode, G.s.inv.ruoka]") == ["home", 4]
    # The next dive has a whole hose again.
    page.evaluate("startDive()")
    assert page.evaluate("[hose.cut, hose.wear]") == [False, 0]


def test_running_out_of_emergency_air_loses_the_haul(site, browser):
    page = hose_game(site, browser)
    page.evaluate("const s = SITES.find(s => s.id === 'kontti'); sub.x = s.spot[0]; sub.y = s.spot[1]; G.mode = 'home';"
                  " crew.suit = true; crew.kit = 'hose'; startDive()")
    take(page, "it.site === 'kontti'")
    page.evaluate("wearHose(100); diver.air = 0.01; step(1 / 60)")
    assert page.evaluate("[G.mode, G.s.inv.ruoka]") == ["home", 2]
    assert "Hätähappi loppui" in page.inner_text("#card")


def test_a_glowing_fish_bites_the_hose_and_a_tougher_hose_loses_less(site, browser):
    page = hose_game(site, browser)
    page.evaluate("sub.x = FISH[3][0] - 30; sub.y = FISH[3][1] - 30; G.mode = 'home'; crew.suit = true; crew.kit = 'hose'; startDive();"
                  " G.fishCd = 0; const f = fishAt(3, G.t); diver.x = f.x + 0.5; diver.y = f.y; step(1 / 60)")
    assert page.evaluate("Math.round(hose.wear)") == 30
    page.evaluate("hose.wear = 0; G.s.up.hose = 4; G.fishCd = 0; const f = fishAt(3, G.t); diver.x = f.x + 0.5; diver.y = f.y; step(1 / 60)")
    assert page.evaluate("Math.round(hose.wear)") == 15
    # No air is lost while the hose is whole.
    assert page.evaluate("diver.air") == 25


def test_the_workshop_upgrades_the_tank_and_the_hose_apart_and_makes_guides(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.inv.osat = 10")
    inside(page)
    walk(page, "paja")
    _act(page, "Parannukset")
    text = page.inner_text("#card")
    assert "🫁 Happisäiliö: 60 s → 90 s" in text and "➰ Letku: 80 m → 120 m" in text
    page.click("#card button:has-text('Letku:')")
    assert page.evaluate("[G.s.up.hose, G.s.up.tank, G.s.inv.osat]") == [2, 1, 8]
    assert "120 metriin" in page.inner_text("#card")
    page.click("#card button:has-text('letkunohjainta')")
    assert page.evaluate("[G.s.inv.ohjain, G.s.inv.osat]") == [4, 7]
    assert page.evaluate(v4.OVERFLOW) == []
    assert page.errors == []


@pytest.mark.parametrize("w,h", [(360, 640), (740, 360)])
def test_the_workshop_card_fits(site, browser, w, h):
    page = open_game(site, browser, w, h)
    new_game(page)
    inside(page)
    walk(page, "paja")
    _act(page, "Parannukset")
    assert page.evaluate(v4.OVERFLOW) == []


def test_an_older_save_keeps_its_tank_and_gets_the_first_hose_and_two_guides(site, browser):
    save = ("{v: 1, day: 7, t: 900, sub: {x: 1500, y: 120, dir: -1}, m: {food: 50, health: 80, hull: 70},"
            " inv: {ruoka: 1, laake: 0, osat: 2, vahvistin: 1, antenni: 0, kortti: 0}, up: {hull: 3, tank: 3, lamp: 2},"
            " got: {}, known: {kontti: true}, flags: {pinged: true, koti: true}, finds: [], findN: 3}")
    page = open_game(site, browser, save=save)
    page.click("#jatka")
    assert page.evaluate("[G.s.up.tank, G.s.up.hose, G.s.inv.ohjain, G.s.guides.length]") == [3, 1, 2, 0]
    # The first hose dive explains the hose, also to a player coming from an older version.
    page.evaluate("G.mode = 'home'; crew.suit = true; crew.kit = 'hose'; sub.y = 200; startDive()")
    assert "➰ Letku" in page.inner_text("#card")


def test_the_nordlys_hose_reel_lengthens_the_hose(site, browser):
    page = hose_game(site, browser)
    page.evaluate("const s = SITES.find(s => s.id === 'nordlys'); sub.x = s.spot[0]; sub.y = s.spot[1]; G.mode = 'home';"
                  " crew.suit = true; crew.kit = 'hose'; startDive()")
    take(page, "it.k === 'saili'")
    page.evaluate("diver.x = airlock().x; diver.y = airlock().y; endDive(false)")
    assert page.evaluate("[G.s.up.hose, G.s.up.tank]") == [2, 1]
    assert "letku 120 m" in v5.toast(page)


def test_the_k7_cache_is_in_reach_of_the_first_hose_through_the_east_crack(site, browser):
    page = hose_game(site, browser, hose=1)
    for item in ("antenni", "loki"):
        r = page.evaluate(f"reach('itarailo', BERG_EAST.spot, -1, ITEMS.find(i => i.site === 'jaavuori' && i.k === '{item}'"
                          f" && (i.k !== 'loki' || i.log === 'k7')).id, 'hose')")
        assert r["at"] and not r["cut"] and r["len"] <= 80, (item, r)
    # The goal points the way there.
    page.evaluate("Object.assign(G.s.flags, {kontti: true, asema: true, polaris: true, nordvik: true}); G.s.up.hull = 2; drawHud()")
    assert page.evaluate("goalNow().target") == "itarailo"
    assert "itäkyljen railo" in page.inner_text("#goal")


DEEP = ["syva", "saga", "laskeutuja", "rinne", "nordlys", "majakka"]


@pytest.mark.parametrize("site_id", DEEP)
def test_every_find_deeper_than_the_tank_gear_goes_is_in_reach_of_the_hose(site, browser, site_id):
    """Below 260 m only the hose suit dives. Swimming the shortest way, every find is in reach of the hose, and the
    hose holds on the way there; Nordlys's far end needs the second hose (its own reel), the rest the first."""
    page = hose_game(site, browser, hose=2 if site_id == "nordlys" else 1)
    ids = page.evaluate(f"ITEMS.filter(i => i.site === '{site_id}').map(i => i.id)")
    assert page.evaluate(f"SITES.find(s => s.id === '{site_id}').spot[1]") > 260
    for item in ids:
        r = page.evaluate(f"reach('{site_id}', SITES.find(s => s.id === '{site_id}').spot, 1, '{item}', 'hose')")
        assert r and r["at"] and not r["cut"], (item, r)


def test_friends_see_each_other_s_hose(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
    aino.evaluate("const s = SITES.find(s => s.id === 'nordvik'); G.s.flags.letku = true;")
    host.evaluate("const s = SITES.find(s => s.id === 'nordvik'); sub.x = s.spot[0]; sub.y = s.spot[1]; net.subT = null")
    aino.wait_for_function("Math.abs(sub.x - SITES.find(s => s.id === 'nordvik').spot[0]) < 1")
    v5.stand(aino, "puvut")
    aino.click("#act2")
    v5.stand(aino, "ilmalukko")
    aino.click("#act")
    aino.wait_for_function("G.mode === 'dive' && diver.kit === 'hose'")
    aino.evaluate(SWIM)
    # Aino swims round the wreck's corner: the host's phone gets her hose with its corner and draws it.
    aino.evaluate("closeCard(); G.hold = true; const s = SITES.find(s => s.id === 'nordvik');"
                  " swim(route(ITEMS.find(i => i.site === 'nordvik' && i.k === 'loki').x, ITEMS.find(i => i.site === 'nordvik' && i.k === 'loki').y,"
                  " [s.x - 14, s.x + s.w * C + 14, s.y - 14, s.y + s.h * C + 14])); G.hold = false")
    assert aino.evaluate("hose.pts.length") >= 1
    host.wait_for_function("Object.values(net.others).some(o => o.mode === 'dive' && o.kit === 'hose' && o.hose && o.hose.length >= 3)")
    host.evaluate("draw()")
    assert host.errors == [] and aino.errors == []


def chapter_2(site, browser):
    page = open_game(site, browser, save=v4.CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; G.s.up.hull = 6")
    return page


def test_the_nordlys_reel_and_lyras_lamp_upgrade_the_gear_and_once_bought_pay_spare_parts(site, browser):
    page = chapter_2(site, browser)
    dive_at(page, "nordlys")
    take(page, "it.k === 'saili' || it.k === 'valo'")
    page.evaluate("endDive(false)")
    # The reel lengthens the hose; the tank (level 3 in this save) stays as it was.
    assert page.evaluate("[G.s.up.hose, G.s.up.tank, G.s.up.lamp, HOSE[G.s.up.hose]]") == [2, 3, 3, 120]
    # A reel or lamp found when that level was already bought pays two spare parts instead.
    page.evaluate("G.s.got = {}; G.s.up.hose = 4; G.s.up.lamp = 3; G.s.inv.osat = 0")
    dive_at(page, "nordlys")
    take(page, "it.k === 'saili' || it.k === 'valo'")
    page.evaluate("endDive(false)")
    assert page.evaluate("[G.s.up.hose, G.s.up.lamp, G.s.inv.osat]") == [4, 3, 4]


def test_in_the_cold_deep_a_cut_hose_s_emergency_air_drains_faster_but_not_by_a_vent(site, browser):
    page = chapter_2(site, browser)
    dive_at(page, "nordlys")
    # A whole hose: no air is used, cold or not.
    page.evaluate("const a = diver.air; step(1); window.used = a - diver.air")
    assert page.evaluate("used") == 0
    page.evaluate("cutHose('Letku katkesi!'); const a = diver.air; step(1); window.used = a - diver.air; drawHud()")
    assert abs(page.evaluate("used") - 1.35) < 0.05
    assert "❄️" in page.inner_text("#airS")
    page.evaluate("diver.x = VENTS[0][0] + 6; diver.y = floorY(VENTS[0][0]) - 16; const b = diver.air; step(1); window.used = b - diver.air")
    assert abs(page.evaluate("used") - 1) < 0.05
    # A fish then takes 5 s, never the last second.
    page.evaluate("G.fishCd = 0; const f = fishAt(3, G.t); diver.x = f.x; diver.y = f.y + 0.5; diver.air = 3; step(1 / 60)")
    assert page.evaluate("[G.mode, diver.air >= 0.9]") == ["dive", True]


def test_the_tank_gear_still_works_as_before_with_air_pockets(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.flags.pinged = true")
    dive_at(page, "asema")
    assert page.evaluate("[diver.kit, diver.air]") == ["tank", 60]
    page.evaluate("run(() => true, 10); drawHud()")
    assert page.inner_text("#airI") == "🫁" and page.inner_text("#airS") in ("50 s", "51 s")
    page.evaluate("diver.air = 5")
    take(page, "it.site === 'asema' && it.k === 'ilma'")
    assert page.evaluate("diver.air") == 60
