"""Last Signal v15 (#329): v13's tests that still hold on v15 (crates, the shelf, the bag, the harpoon, the hose, the
weather station, friends...), then v15's own: no word of food and the container at the start; the sonar telling of
every new contact; a rebuilt sea (far more floor relief, big icebergs to pass under, rock arches with a tunnel, places in
hollows off the way, a far background layer); small openings where only the tower comes up; a dark and empty Aurora
whose power is fixed first with the fuses from its underwater module; the nomads, told of the shelter, moving in; the
pump in Saukko, the nearest wreck, shelved like a crate; and the autopilot's trip slept through once fed."""

import json

import pytest

import test_last_signal_v4 as v4
import test_last_signal_v5 as v5
import test_last_signal_v13 as v13
from test_last_signal_v4 import _close_pages, _opened  # noqa: F401  (the fixture closes this file's pages too)

URL = "games/last-signal/v15/"
SAVE13 = v13.SAVE13
SAVE15 = v4.SAVE + "15"


@pytest.fixture(autouse=True)
def _v15(monkeypatch):
    for m in (v4, v5):
        monkeypatch.setattr(m, "URL", URL)


# v13's tests of what v15 did not change. Left out: the start's goals, the station's diary and Aurora's survivors, the
# pump in Kestrel, saves read from v12's and v11's keys, the shelved food read back from v13's key, the icebergs' sizes
# and the next-area goal (v15's own versions are below).
CHANGED = {"test_the_station_s_diary_points_to_the_nomads_who_trade_what_they_know",
           "test_aurora_is_three_floors_over_the_first_opening_and_its_survivors_get_a_pump",
           "test_the_pump_lies_in_kestrel_s_hold_and_never_goes_on_the_shelf",
           "test_a_v11_save_moves_into_the_wider_world_under_its_own_key", "test_a_v12_save_comes_into_v13_under_its_own_key",
           "test_a_v12_save_keeps_the_crates_the_player_moved_and_the_wrecks_lack_what_was_taken",
           "test_a_food_crate_shelved_in_the_stores_counts_and_leaves_when_eaten",
           "test_goods_a_friend_packed_go_back_to_the_stores_when_their_phone_leaves",
           "test_icebergs_of_other_sizes_and_keels_under_the_ice_stop_sisu", "test_logs_put_the_next_place_s_area_on_the_chart",
           "test_the_world_is_wider_the_sonar_shorter_and_the_hull_takes_any_depth"}
for _name in dir(v13):
    if _name.startswith("test_") and _name not in CHANGED:
        globals()[_name] = getattr(v13, _name)

toast = v5.toast
run = v13.run
LIT = {"sahko": 1, "pimea": 1}


def game(site, browser, w=360, h=740, save=None, **flags):
    return v13.game(site, browser, w, h, save, **flags)


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
    v13.climb_to(page, x, fl)
    page.evaluate("if (G.paused) closeCard(); run(() => true, 0.05); drawHud()")


# ---------- the start ----------

def test_no_word_of_food_and_the_container_at_the_start(site, browser):
    page = v4.open_game(site, browser)
    v4.new_game(page)
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
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
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
    v13.dive(page, "asema")
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
    v13.out_on_ice(page)
    v13.walk_ice(page, "CAMP.elder")
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
    v13.dive(page, "aurora")
    v13.carry_home(page, "aurora:14,6")
    v13.stand(page, "varasto", 1.6)
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
    v4.inside(page)
    v4.walk(page, "punkka")
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
    page = v4.open_game(site, browser)
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
    s = v5.save_with(w12=1, w13=1)
    page = v4.open_game(site, browser)
    page.evaluate(f"localStorage.setItem('{SAVE13}', {json.dumps(json.dumps(s))}); menu()")
    page.click("#jatka")
    page.evaluate("G.hold = true; closeCard(); drawHud()")
    assert page.evaluate("[G.s.flags.sahko || 0, G.s.flags.suoja || 0, goalNow().target]") == [0, 0, "railo0"]
    assert page.errors == []


def test_shelved_food_counts_and_the_save_is_v15_s_own(site, browser):
    page = game(site, browser)
    v13.dive(page, "polaris")
    cid = page.evaluate("G.s.crates.find(c => c.id.startsWith('polaris:') && c.k === 'ruoka').id")
    v13.carry_home(page, cid)
    v4.walk(page, "varasto")
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
        assert page.evaluate(v4.OVERFLOW) == []
        page.evaluate("closeCard()")
    assert page.errors == []


def test_a_friend_fixes_aurora_s_power_and_tells_the_nomads_and_the_host_s_game_has_it(site, browser):
    host, aino = v5.room(site, browser, names=("Eero", "Aino"))
    v5.close_cards(host, aino)
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
