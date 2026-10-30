"""Last Signal v2 (#129): v1 plus chapter 2 — the continental slope, the research vessel Nordlys and the deep sea."""

import shutil

import pytest

from conftest import ROOT, turn

URL = "games/last-signal/v2/"
SAVE = "ai-pelit:last-signal:peli"

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
# Flood-fills the water a diver can swim in (0.5 m steps, the diver's own size) from where the submarine parks
# at each site, and gives the walking distance to every find there; null when it cannot be reached.
REACH = """() => {
  const out = {}, groups = {};
  for (const it of ITEMS) (groups[it.site] = groups[it.site] || []).push(it);
  for (const [site, items] of Object.entries(groups)) {
    const S = SITES.find(s => s.id === site), [sx, sy] = S ? S.spot : BERG_SITE.spot;
    const box = S ? [S.x - 12, S.x + S.w * C + 12, S.y - 12, S.y + S.h * C + 12] : [2040, 2430, 0, 210];
    const k = (x, y) => Math.round(x * 2) + ',' + Math.round(y * 2), seen = new Map([[k(sx, sy), 0]]), q = [[sx, sy]];
    for (let h = 0; h < q.length; h++) {
      const [x, y] = q[h], d = seen.get(k(x, y));
      for (const [dx, dy] of [[0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) {
        const nx = x + dx, ny = y + dy;
        if (ny < 1 || seen.has(k(nx, ny)) || diverHits(nx, ny)) continue;
        if (Math.hypot(nx - sx, ny - sy) > 25 && !(nx > box[0] && nx < box[1] && ny > box[2] && ny < box[3])) continue;
        seen.set(k(nx, ny), d + 0.5); q.push([nx, ny]);
      }
    }
    out[site] = { parks: !subHits(sx, sy), depth: sy, items: items.map(it => {
      let best = null;
      for (let dx = -1.5; dx <= 1.5; dx += 0.5) for (let dy = -1.5; dy <= 1.5; dy += 0.5) {
        const v = seen.get(k(it.x + dx, it.y + dy));
        if (v != null && Math.hypot(dx, dy) <= 1.6 && (best == null || v < best)) best = v;
      }
      return [it.k, it.x, it.y, best];
    }) };
  }
  return out;
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


def dive_at(page, site_id):
    """Parks SISU where the site says and swims out."""
    page.evaluate(f"""(() => {{ const s = SITES.find(s => s.id === '{site_id}') || BERG_SITE;
      sub.x = s.spot[0]; sub.y = s.spot[1]; sub.vx = sub.vy = 0; startDive(); }})()""")
    assert page.evaluate("G.mode") == "dive"


def take(page, item_filter):
    """Swims the diver onto every find the filter picks (a JS expression over `it`)."""
    page.evaluate(f"for (const it of ITEMS.filter(it => {item_filter})) {{ diver.x = it.x; diver.y = it.y; step(1 / 60);"
                  " if (G.paused) closeCard(); }")


def test_a_new_game_starts_on_day_1_and_the_ping_names_what_it_hears(site, browser):
    page = open_game(site, browser)
    new_game(page)
    assert page.inner_text("#goal").startswith("Paina 📡")
    assert page.evaluate("[G.mode, G.s.day, G.s.inv.ruoka, Math.round(G.s.m.food)]") == ["sub", 1, 2, 70]
    assert not page.evaluate("G.s.known.kontti")
    page.click("#ping")
    page.evaluate("drawHud()")
    # The container and the station are within reach of the ping; the far wrecks stay unknown.
    assert page.evaluate("[G.s.known.kontti, G.s.known.asema, !!G.s.known.polaris]") == [True, True, False]
    assert page.inner_text("#goal").startswith("Ruoka on vähissä")
    assert page.evaluate("goalNow().target") == "kontti"
    assert page.errors == []


def test_finds_count_only_once_the_diver_is_back_in_sisu(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.flags.pinged = true")
    dive_at(page, "kontti")
    take(page, "it.site === 'kontti'")
    assert page.evaluate("G.carry.length") == 3
    assert page.evaluate("G.s.inv.ruoka") == 2
    page.evaluate("diver.x = airlock().x; diver.y = airlock().y; drawHud()")
    assert page.inner_text("#act") == "Palaa veneeseen"
    page.click("#act")
    assert page.evaluate("[G.mode, G.s.inv.ruoka, G.s.inv.osat, G.s.flags.kontti]") == ["sub", 4, 1, True]
    page.evaluate("drawHud()")
    assert page.inner_text("#goal").startswith("Sonar kuuli metallia")
    # Saved at once: a reload keeps the haul.
    page.reload()
    page.wait_for_function("window.drawn === true")
    assert page.evaluate("JSON.parse(localStorage.getItem('%s')).inv.ruoka" % SAVE) == 4


def test_running_out_of_air_loses_the_haul_but_the_finds_wait_in_place(site, browser):
    page = open_game(site, browser)
    new_game(page)
    dive_at(page, "kontti")
    take(page, "it.site === 'kontti' && it.k === 'ruoka'")
    assert page.evaluate("G.carry.length") == 2
    page.evaluate("G.hold = false; diver.air = 0.01")
    page.wait_for_function("G.mode === 'sub'")
    assert "Happi loppui" in page.inner_text("#card")
    assert page.evaluate("[G.s.inv.ruoka, G.s.m.health, ITEMS.filter(it => it.site === 'kontti').every(itemHere)]") == [2, 75, True]


def test_an_air_pocket_fills_the_tank(site, browser):
    page = open_game(site, browser)
    new_game(page)
    dive_at(page, "asema")
    page.evaluate("diver.air = 5")
    take(page, "it.site === 'asema' && it.k === 'ilma'")
    assert page.evaluate("diver.air") == 60


def test_the_logs_tell_the_story_and_set_the_next_goal(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("Object.assign(G.s.flags, { pinged: true, kontti: true })")
    dive_at(page, "asema")
    page.evaluate("const it = ITEMS.find(it => it.log === 'asema'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
    assert "Nordlys hakee meidät" in page.inner_text("#card")
    page.click("#card button:has-text('Jatka')")
    page.evaluate("drawHud()")
    assert page.evaluate("G.s.flags.asema") is True
    assert page.inner_text("#goal").startswith("Hylkykenttä on yli 160 metrissä")


def test_below_the_hull_rating_the_pressure_breaks_the_hull_and_an_upgrade_lets_you_down(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("sub.x = 1180; sub.y = 222; run(() => true, 2); drawHud()")
    assert page.evaluate("G.s.m.hull") < 95
    assert page.get_attribute("#depth", "class") == "over"
    page.evaluate("run(() => G.mode === 'sub' && !G.paused, 40)")
    assert "Runko pettää" in page.inner_text("#card")
    # v2: the emergency ballast lifts SISU 40 m above the hull's limit, not to the surface.
    assert page.evaluate("[G.s.m.hull, sub.y]") == [25, 120]
    page.click("#card button:has-text('Jatka')")
    # Three spare parts and the workshop: the hull now holds 260 m.
    page.evaluate("G.s.inv.osat = 3")
    page.click("#home")
    page.click("#card button:has-text('parannukset')")
    page.click("#card button:has-text('Paineenkesto')")
    assert "260 metriä" in page.inner_text("#card")
    page.click("#card button:has-text('Ohjaamoon')")
    page.evaluate("sub.x = 1180; sub.y = 222; run(() => true, 3)")
    assert page.evaluate("[G.s.up.hull, G.s.m.hull, G.s.inv.osat]") == [2, 100, 0]


def test_home_feeds_heals_repairs_and_sleep_brings_a_new_day(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.m.food = 30; G.s.m.health = 40; G.s.m.hull = 50; G.s.inv.osat = 1")
    page.click("#home")
    assert page.evaluate("G.mode") == "home"
    page.click("#card button:has-text('Keittiö')")
    page.click("#card button:has-text('Lääkekaappi')")
    page.click("#card button:has-text('korjaa runko')")
    assert page.evaluate("[G.s.m.food, G.s.m.health, G.s.m.hull, G.s.inv.ruoka, G.s.inv.laake, G.s.inv.osat]") == [65, 85, 85, 1, 0, 0]
    page.click("#card button:has-text('Punkka')")
    assert "Päivä 2" in page.inner_text("#card")
    assert page.evaluate("[G.s.day, G.s.finds.length >= 1, G.s.finds.every(f => f.y < 160 && !diverHits(f.x, f.y))]") == [2, True, True]
    page.click("#card button:has-text('Nouse')")
    page.click("#card button:has-text('Ohjaamoon')")
    assert page.evaluate("G.mode") == "sub"


def test_hunger_never_ends_the_game(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.m.food = 0; G.s.m.health = 0.1; run(() => !G.paused, 2)")
    assert "Pyörryt" in page.inner_text("#card")
    assert page.evaluate("[G.s.day, G.s.m.health, G.s.m.food]") == [2, 35, 25]


def test_amplifier_and_antenna_fix_the_radio_and_the_last_signal_ends_chapter_1(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.click("#home")
    page.click("#card button:has-text('Radio')")
    assert "Vahvistin ✗ · Antenni ✗" in page.inner_text("#card")
    page.click("#card button:has-text('Takaisin')")
    page.click("#card button:has-text('Ohjaamoon')")
    # The antenna waits in the iceberg's cache K-7, the amplifier in the station.
    dive_at(page, "jaavuori")
    take(page, "it.k === 'antenni'")
    page.evaluate("endDive(false)")
    dive_at(page, "asema")
    take(page, "it.k === 'vahvistin'")
    page.evaluate("endDive(false); drawHud()")
    assert page.evaluate("[G.s.inv.antenni, G.s.inv.vahvistin]") == [1, 1]
    page.click("#home")
    page.click("#card button:has-text('Radio: korjaa')")
    assert "tässä tutkimusalus Nordlys" in page.inner_text("#card")
    assert "Et olekaan yksin" in page.inner_text("#card")
    assert page.evaluate(OVERFLOW) == []
    assert page.evaluate("JSON.parse(localStorage.getItem('%s')).flags.end" % SAVE) is True


def test_every_find_can_be_reached_on_the_air_there_is(site, browser):
    page = open_game(site, browser)
    new_game(page)
    reach = page.evaluate(REACH)
    assert set(reach) == {"asema", "kontti", "polaris", "kontit", "nordvik", "syva", "jaavuori", "saga", "laskeutuja", "rinne",
                          "nordlys", "majakka"}
    for site_id, r in reach.items():
        assert r["parks"], f"SISU cannot park at {site_id}"
        unreached = [i for i in r["items"] if i[3] is None]
        assert not unreached, f"{site_id}: cannot reach {unreached}"
        # The grid walk is longer than a swim; from the nearest air (SISU or a pocket) every find is in reach on
        # the first tank, there and back.
        airs = [(i[1], i[2], i[3]) for i in r["items"] if i[0] == "ilma"] + [(0, 0, 0)]
        for k, x, y, d in r["items"]:
            nearest = min(abs(d - a[2]) for a in airs)
            # Below 600 m the cold drains air 1.35 times faster; those sites are reached with the third tank.
            tank = 120 / 1.35 if r["depth"] > 600 else 60
            assert nearest / 4.4 * 2 < tank * 1.5, f"{site_id}: {k} at {x},{y} is {nearest} m from air"
    # The station and the container are in reach of the first hull, the wrecks need the second, the trench the third.
    depth = {k: v["depth"] for k, v in reach.items()}
    assert depth["asema"] < 160 and depth["kontti"] < 160 and depth["jaavuori"] < 160
    assert 160 < depth["polaris"] < 260 and 160 < depth["nordvik"] < 260 and 260 < depth["syva"] < 380
    # Chapter 2: each step down the slope needs the next hull.
    assert 260 < depth["saga"] < 380 and 380 < depth["laskeutuja"] < 620 and 380 < depth["rinne"] < 620
    assert 620 < depth["nordlys"] < 1000 and 1000 < depth["majakka"] < 1450


def test_continue_returns_to_where_sisu_was(site, browser):
    save = ("{v: 1, day: 4, t: 900, sub: {x: 1500, y: 120, dir: -1}, m: {food: 50, health: 80, hull: 70},"
            " inv: {ruoka: 1, laake: 0, osat: 2, vahvistin: 1, antenni: 0}, up: {hull: 2, tank: 1, lamp: 1},"
            " got: {}, known: {kontti: true}, flags: {pinged: true, kontti: true, asema: true}, finds: [], findN: 3}")
    page = open_game(site, browser, save=save)
    assert "Päivä 4" in page.inner_text("#menuText")
    page.click("#jatka")
    page.evaluate("G.hold = true; drawHud()")
    assert page.evaluate("[G.mode, sub.x, sub.y, sub.dir, G.s.up.hull]") == ["sub", 1500, 120, -1, 2]
    assert page.inner_text("#goal").startswith("Tutki hylkykenttä")


@pytest.mark.parametrize("w,h", [(360, 640), (360, 740), (390, 844), (740, 360)])
def test_menus_cards_and_controls_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h)
    assert page.evaluate(OVERFLOW) == []
    new_game(page)
    assert page.evaluate(OVERFLOW) == []
    page.click("#home")
    assert page.evaluate(OVERFLOW) == []
    page.click("#card button:has-text('parannukset')")
    assert page.evaluate(OVERFLOW) == []
    page.click("#card button:has-text('Takaisin')")
    page.click("#card button:has-text('Ohjaamoon')")
    dive_at(page, "polaris")
    page.evaluate("const it = ITEMS.find(it => it.log === 'polaris'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
    assert page.evaluate(OVERFLOW) == []
    assert page.errors == []


def test_turning_the_phone_mid_dive_keeps_the_dive(site, browser):
    page = open_game(site, browser)
    new_game(page)
    dive_at(page, "kontti")
    page.evaluate("G.hold = false")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert page.evaluate("[G.mode, innerWidth]") == ["dive", 740]
    assert page.is_visible("#stick")
    assert page.errors == []


CH1_DONE = ("{v: 1, day: 9, t: 3000, sub: {x: 2460, y: 120, dir: 1}, m: {food: 80, health: 90, hull: 100},"
            " inv: {ruoka: 3, laake: 1, osat: 0, vahvistin: 1, antenni: 1}, up: {hull: 3, tank: 3, lamp: 2},"
            " got: {}, known: {}, flags: {pinged: true, kontti: true, asema: true, polaris: true, nordvik: true, k7: true,"
            " jaavuori: true, end: true}, finds: [], findN: 5}")


def test_a_v1_save_with_chapter_1_done_opens_chapter_2(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    assert "Luku 2" in page.inner_text("#menuText")
    page.click("#jatka")
    assert "Luku 2: Mannerrinne" in page.inner_text("#card")
    assert page.evaluate(OVERFLOW) == []
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; drawHud()")
    assert page.inner_text("#goal").startswith("Aja itään jäävuorten ohi")
    assert page.evaluate("[goalNow().target, G.s.inv.kortti, G.s.flags.ch2, sub.x]") == ["saga", 0, True, 2460]
    # The intro shows once.
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    assert page.is_hidden("#panel")
    assert page.errors == []


def test_ending_chapter_1_in_v2_leads_into_chapter_2(site, browser):
    page = open_game(site, browser)
    new_game(page)
    page.evaluate("G.s.inv.vahvistin = 1; G.s.inv.antenni = 1; drawHud()")
    page.click("#home")
    page.click("#card button:has-text('Radio: korjaa')")
    assert "Luku 1 päättyy" in page.inner_text("#card")
    page.click("#card button:has-text('Luku 2')")
    assert "Luku 2: Mannerrinne" in page.inner_text("#card")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("drawHud()")
    assert page.evaluate("G.mode") == "sub"
    assert page.evaluate("[G.s.flags.end, G.s.flags.ch2]") == [True, True]


def test_chapter_2_goes_down_the_slope_to_nordlys_and_the_beacon(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true")
    goal = lambda: page.evaluate("drawHud(), [goalNow().target, document.getElementById('goal').textContent]")

    def read_log(site_id, log):
        dive_at(page, site_id)
        page.evaluate(f"const it = ITEMS.find(it => it.log === '{log}'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
        text = page.inner_text("#card")
        page.click("#card button:has-text('Jatka')")
        page.evaluate("endDive(false)")
        return text

    assert "Nordlys kävi luonamme" in read_log("saga", "saga")
    assert goal()[1].startswith("Pohjalaskeutuja on yli 380 metrissä")
    page.evaluate("G.s.up.hull = 4")
    assert goal()[0] == "laskeutuja"
    assert "900 metriin" in read_log("laskeutuja", "laskeutuja")
    page.evaluate("G.s.up.hull = 5")
    assert goal() == ["nordlys", "Etsi tutkimusalus Nordlys rinteen juurelta, noin 900 metristä."]
    assert "Lähdemme Lyralla" in read_log("nordlys", "silta")
    assert goal()[1].startswith("Nordlys on tyhjä")
    assert "Lähteet, 1300 m" in read_log("nordlys", "kartta")
    page.evaluate("G.s.up.hull = 6")
    assert goal()[0] == "majakka"
    # The beacon: its log, then the memory card home to the radio ends chapter 2.
    assert "kolme lyhyttä" in read_log("majakka", "majakka")
    dive_at(page, "majakka")
    take(page, "it.k === 'kortti'")
    page.evaluate("endDive(false)")
    assert goal()[1].startswith("Soita majakan muistikortti")
    page.click("#home")
    page.click("#card button:has-text('soita muistikortti')")
    assert "Luku 2 päättyy" in page.inner_text("#card")
    assert page.evaluate(OVERFLOW) == []
    page.click("#card button:has-text('Takaisin kotiin')")
    assert "Radio: Lyra" in page.inner_text("#card")
    saved = page.evaluate("JSON.parse(localStorage.getItem('%s'))" % SAVE)
    assert saved["flags"]["end2"] is True and saved["v"] == 1
    assert page.errors == []


def test_the_nordlys_tank_and_lyras_lamp_upgrade_the_gear(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; G.s.up.hull = 5")
    dive_at(page, "nordlys")
    take(page, "it.k === 'saili' || it.k === 'valo'")
    page.evaluate("endDive(false)")
    assert page.evaluate("[G.s.up.tank, G.s.up.lamp, TANK[G.s.up.tank]]") == [4, 3, 150]
    assert "happea 150 s" in page.inner_text("#toast") or "valo" in page.inner_text("#toast")


def test_the_deep_is_cold_and_glowing_fish_bump_but_never_end_the_game(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; G.s.up.hull = 6; G.s.up.tank = 4")
    dive_at(page, "nordlys")
    page.evaluate("const a = diver.air; step(1); window.used = a - diver.air; drawHud()")
    assert abs(page.evaluate("used") - 1.35) < 0.05
    assert "❄️" in page.inner_text("#airS")
    # Warm water by a hot vent keeps the cold away.
    page.evaluate("diver.x = VENTS[0][0] + 6; diver.y = floorY(VENTS[0][0]) - 16; const b = diver.air; step(1); window.used = b - diver.air")
    assert abs(page.evaluate("used") - 1) < 0.05
    # A fish takes 8 s of air and pushes the diver away, once per 3 s.
    page.evaluate("G.fishCd = 0; const f = fishAt(3, G.t); diver.x = f.x + 0.5; diver.y = f.y; diver.air = 50; step(1 / 60)")
    assert 41 < page.evaluate("diver.air") < 42.5
    assert "Valokala" in page.inner_text("#toast")
    # Even with almost no air left a fish leaves one second: running out ends only the dive.
    page.evaluate("G.fishCd = 0; const f = fishAt(3, G.t); diver.x = f.x; diver.y = f.y + 0.5; diver.air = 3; step(1 / 60)")
    assert page.evaluate("[G.mode, diver.air >= 0.9]") == ["dive", True]
    page.evaluate("endDive(false); const f = fishAt(1, G.t); sub.x = f.x; sub.y = f.y; G.fishCd = 0; G.s.m.hull = 50; stepSub(1 / 60)")
    assert page.evaluate("G.s.m.hull") < 50


def test_fish_swim_in_open_water_and_vents_stand_on_the_floor(site, browser):
    page = open_game(site, browser)
    bad = page.evaluate("""() => {
      const bad = [];
      for (let n = 0; n < FISH.length; n++) for (let t = 0; t < 120; t += 0.25) {
        const f = fishAt(n, t);
        for (const [dx, dy] of [[-2, 0], [2, 0], [0, -1.2], [0, 1.2]]) if (solid(f.x + dx, f.y + dy, true)) { bad.push([n, t]); break; }
      }
      return bad.slice(0, 5);
    }""")
    assert bad == []
    assert page.evaluate("VENTS.every(([x, h]) => solid(x, floorY(x) - h + 0.5) && !solid(x, floorY(x) - h - 1))")


def test_the_slope_takes_sisu_down_faster_and_nightly_finds_follow_the_hull(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; sub.y = 900")
    assert page.evaluate("subBoost()") == 2.2
    # Many nights, so a find on the steepest part of the slope is drawn too: each must lie in open water.
    page.evaluate("G.s.up.hull = 6; window.all = []; for (let n = 0; n < 400; n++) { G.s.finds = []; newFinds(); all.push(...G.s.finds); }")
    assert page.evaluate("all.filter(f => f.y >= RATING[6] || diverHits(f.x, f.y)).map(f => [f.x, f.y])") == []
    assert page.evaluate("all.some(f => f.x > 3700)")


def test_inside_nordlys_the_rooms_are_named_and_the_iceberg_hall_widens_the_view(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; G.s.up.hull = 5")
    dive_at(page, "nordlys")
    names = page.evaluate("SITES.find(s => s.id === 'nordlys').rooms.map(r => r[2])")
    for room in ("Komentosilta", "Karttahuone", "Laboratorio", "Työpaja", "Sukellusvarusteet", "Lastiruuma",
                 "Tutkimussukellusveneen halli"):
        assert room in names
    # every room label sits on water inside the ship, not on a wall
    assert page.evaluate("(() => { const s = SITES.find(s => s.id === 'nordlys');"
                         " return s.rooms.every(([i, j]) => s.cells[j + 1][Math.floor(i)] !== '#'); })()")
    page.evaluate("endDive(false)")
    dive_at(page, "jaavuori")
    small = page.evaluate("diveScale()")
    page.evaluate("diver.x = 2245; diver.y = 68")
    assert page.evaluate("diveScale()") < small * 0.75


def test_reading_the_chart_room_before_the_bridge_still_moves_on(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; Object.assign(G.s.flags, { saga: true, laskeutuja: true }); G.s.up.hull = 5")
    dive_at(page, "nordlys")
    page.evaluate("const it = ITEMS.find(it => it.log === 'kartta'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
    page.click("#card button:has-text('Jatka')")
    page.evaluate("endDive(false); drawHud()")
    assert page.inner_text("#goal").startswith("Lähteet ovat 1300 metrissä")
    # A tank or lamp found when that level was already bought pays two spare parts instead.
    page.evaluate("G.s.up.tank = 4; G.s.up.lamp = 3; G.s.inv.osat = 0")
    dive_at(page, "nordlys")
    take(page, "it.k === 'saili' || it.k === 'valo'")
    page.evaluate("endDive(false)")
    assert page.evaluate("[G.s.up.tank, G.s.up.lamp, G.s.inv.osat]") == [4, 3, 4]


def test_a_reload_mid_dive_in_nordlys_comes_back_at_sisu_with_the_story_kept(site, browser):
    page = open_game(site, browser, save=CH1_DONE)
    page.click("#jatka")
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; Object.assign(G.s.flags, { saga: true, laskeutuja: true }); G.s.up.hull = 5")
    dive_at(page, "nordlys")
    page.evaluate("const it = ITEMS.find(it => it.log === 'silta'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
    page.reload()
    page.wait_for_function("window.drawn === true")
    page.click("#jatka")
    assert page.is_hidden("#panel")
    page.evaluate("G.hold = true; drawHud()")
    assert page.evaluate("[G.mode, Math.round(sub.x), Math.round(sub.y), G.s.flags.silta]") == ["sub", 3452, 879, True]
    assert page.inner_text("#goal").startswith("Nordlys on tyhjä")


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844), (360, 740), (740, 360)])
def test_chapter_2_cards_fit_upright_and_sideways(site, browser, w, h):
    page = open_game(site, browser, w, h, save=CH1_DONE)
    page.click("#jatka")
    assert page.evaluate(OVERFLOW) == []
    page.click("#card button:has-text('Kohti syvyyttä')")
    page.evaluate("G.hold = true; G.s.up.hull = 5")
    for log in ("labra", "kartta", "halli"):
        dive_at(page, "nordlys")
        page.evaluate(f"const it = ITEMS.find(it => it.log === '{log}'); diver.x = it.x; diver.y = it.y; step(1 / 60)")
        assert page.evaluate(OVERFLOW) == [], log
        page.click("#card button:has-text('Jatka')")
        page.evaluate("endDive(false)")
    page.evaluate("G.s.inv.kortti = 1; drawHud()")
    page.click("#home")
    page.click("#card button:has-text('soita muistikortti')")
    assert page.evaluate(OVERFLOW) == []
    assert page.errors == []
