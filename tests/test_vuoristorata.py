"""Vuoristorata v1 (#180): a roller coaster ridden from the front seat, in 3D, alone or racing friends."""

import json
import shutil

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/vuoristorata/v1/"
KEY = "ai-pelit:vuoristorata:"


def build(site):
    # Only this game is built: other games' half-made versions cannot break the build.
    shutil.copytree(ROOT / "games" / "vuoristorata", site.games / "vuoristorata")
    site.build()


def open_page(site, browser, size=(360, 740), name=None, relay=None, saves=None):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    if name:
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
    for k, v in (saves or {}).items():
        ctx.add_init_script(f"localStorage.setItem({json.dumps(KEY + k)}, {json.dumps(json.dumps(v))})")
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    if relay:
        relay.attach(page)
    page.goto(site.url + URL)
    page.wait_for_function("window.drawn === true || window.noWebgl === true", timeout=20000)
    return ctx, page


@pytest.fixture
def page(site, browser):
    build(site)
    ctx, p = open_page(site, browser)
    yield p
    ctx.close()


def inside(page, selector):
    box = page.locator(selector).bounding_box()
    vw, vh = page.evaluate("[innerWidth, innerHeight]")
    assert box, selector
    assert box["x"] >= 0 and box["y"] >= 0, selector
    assert box["x"] + box["width"] <= vw + 0.5 and box["y"] + box["height"] <= vh + 0.5, selector
    return box


def close_scores(page):
    # The first score opens the high-score list's nickname box over the end screen; close it.
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('ai-pelit-tulokset')?.remove()")


def overlaps(a, b):
    return not (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])


# ---- The rules, in plain numbers ----

def test_every_level_can_be_ridden_to_the_end_without_falling(page):
    # The computer rides each level the way a careful player would: by the limits ahead.
    res = page.evaluate("""() => [...Array(15)].map((_, i) => { const t = makeLevel(i + 1);
        return [i + 1, t.ideal, t.botFalls, Math.min(...t.S.map(o => o.y))]; })""")
    for level, ideal, falls, low in res:
        assert ideal < 200, level
        assert falls == 0, level
        assert low > 1, level   # the track never goes into the ground


def test_a_level_is_the_same_track_every_time(page):
    a = page.evaluate("buildTrack(levelPlan(4)).len")
    b = page.evaluate("buildTrack(levelPlan(4)).len")
    assert a == b
    assert page.evaluate("buildTrack(levelPlan(5)).len") != a


def test_every_sign_tells_the_truth(page):
    # Passing a sign's place at its own number, the car stays on the track: under a max, rolling;
    # at a min, it makes it over the loop.
    bad = page.evaluate("""() => { const bad = []; let n = 0;
      for (let lv = 1; lv <= 12; lv++) { const t = makeLevel(lv);
        for (const z of t.zones) for (const v of [z.max, z.min]) { if (!v) continue; n++;
          const car = Object.assign(newCar(), { s: z.s0, v: v / 3.6 }); let e = null;
          while (car.s < z.s1 + 2 && car.v > 0 && !e) e = rideStep(t, car, 1 / 120);
          if ((e && e.what === 'derail') || car.v <= 0) bad.push([lv, z.kind, v]);
        } }
      return [n, bad]; }""")
    assert bad[0] > 100
    assert bad[1] == []


def test_loops_come_from_level_two_and_signs_warn_of_them(page):
    kinds = page.evaluate("[1, 2, 3, 4].map(l => [...new Set(makeLevel(l).pieces.map(p => p.kind))])")
    assert "loop" not in kinds[0]
    assert any("loop" in k for k in kinds[1:])
    assert page.evaluate("makeLevel(2).zones.some(z => z.kind === 'loop' && z.min > 0)")


def test_the_reckless_and_the_lazy_do_not_get_round(page):
    # Holding the boost all the way flies off the track again and again; doing nothing stalls.
    flat, lazy = page.evaluate("""() => [true, false].map(boost => { const t = makeLevel(1), car = newCar(); let falls = 0;
        for (let k = 0; k < 200 * 60 && car.fin === null; k++) { car.boost = boost; const e = rideStep(t, car, 1 / 60);
          if (e && e.what === 'derail') { falls++; respawn(t, car); } }
        return [car.fin, falls]; })""")
    assert flat[1] >= 3
    assert lazy[0] is None


def test_a_derail_puts_the_car_back_before_the_place_it_flew_off(page):
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    s0 = page.evaluate("(() => { const z = game.track.zones.find(z => z.max && z.s0 > 150); game.car.check = z.s0 - 60;"
                       " game.car.s = z.s0 - 1; game.car.v = (z.max + 45) / 3.6; return z.s0; })()")
    page.wait_for_function("game.mode === 'crash'", timeout=5000)
    assert page.locator("#toast").inner_text().startswith("Liian")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    assert page.evaluate("game.car.s") < s0
    assert page.errors == []


# ---- Playing it ----

def test_a_ride_finishes_saves_and_opens_the_next_level(page):
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    page.evaluate("auto = true")
    page.wait_for_function("game.car.s > 60", timeout=20000)
    # Far enough to see it ride; then to the last stretch, so the test is quick.
    page.evaluate("game.car.s = game.track.finish - 40; game.car.check = game.car.s")
    page.wait_for_function("game.mode === 'done'", timeout=20000)
    page.wait_for_selector("#loppu:not(.hidden)")
    assert page.locator("#loppu-otsikko").inner_text() == "Maalissa!"
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}taso'))") == 2
    assert "1" in page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}ajat'))")
    assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}tahdet'))['1']") >= 1
    close_scores(page)
    page.click("#seuraava")
    page.wait_for_function("game.level === 2 && game.mode === 'count'", timeout=3000)
    assert page.errors == []


def test_the_buttons_boost_and_brake_while_held(page):
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    page.evaluate("game.car.s = 120; game.car.v = 10")
    for sel, flag in [("#vauhti", "boost"), ("#jarru", "brake")]:
        box = page.locator(sel).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.dispatch_event(sel, "pointerdown", {"pointerId": 5, "clientX": x, "clientY": y, "isPrimary": True})
        page.wait_for_function(f"game.car.{flag} === true", timeout=2000)
        page.dispatch_event(sel, "pointerup", {"pointerId": 5, "clientX": x, "clientY": y, "isPrimary": True})
        page.wait_for_function(f"game.car.{flag} === false", timeout=2000)


def test_saves_are_kept_and_the_level_can_be_picked(site, browser):
    build(site)
    ctx, page = open_page(site, browser, saves={"taso": 4, "valittu": 3, "ajat": {"3": 71.4}, "tahdet": {"3": 2}})
    try:
        assert page.locator("#taso").inner_text() == "Taso 3"
        assert "1.11.4" in page.locator("#ennatys").inner_text()
        page.click("#seur")
        assert page.locator("#taso").inner_text() == "Taso 4"
        assert page.locator("#seur").is_disabled()
        assert page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}valittu'))") == 4
    finally:
        ctx.close()


@pytest.mark.parametrize("size", [(360, 640), (390, 844), (740, 360), (640, 360)])
def test_the_menu_and_the_end_screen_fit_without_scrolling(site, browser, size):
    build(site)
    ctx, page = open_page(site, browser, size)
    try:
        assert page.evaluate("document.documentElement.scrollHeight") == size[1]
        for sel in ["#menu h1", "#menu .help", "#taso", "#aja", "#kaverit", "#ai-pelit-back"]:
            inside(page, sel)
        assert not overlaps(inside(page, "#menu h1"), inside(page, "#ai-pelit-back"))
        page.click("#aja")
        page.wait_for_function("game.mode === 'ride'", timeout=8000)
        for sel in ["#jarru", "#vauhti", "#nopeus", "#kello"]:
            inside(page, sel)
        assert not overlaps(inside(page, "#kello"), inside(page, "#ai-pelit-back"))
        page.evaluate("auto = true; game.car.s = game.track.finish - 30")
        page.wait_for_function("game.mode === 'done'", timeout=20000)
        close_scores(page)
        for sel in ["#loppu-otsikko", "#aika", "#uudestaan", "#valikkoon"]:
            inside(page, sel)
    finally:
        ctx.close()


def test_turning_the_phone_mid_ride_keeps_the_ride(page):
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    page.evaluate("auto = true")
    page.wait_for_function("game.car.s > 40", timeout=20000)
    page.evaluate("document.fullscreenElement ? document.exitFullscreen() : null")
    for w, h in [(740, 360), (360, 740)]:
        before = page.evaluate("game.car.t")
        turn(page, {"width": w, "height": h})
        page.wait_for_function(f"innerWidth === {w} && Math.abs(camera.aspect - {w / h}) < 0.01", timeout=3000)
        page.wait_for_function(f"game.car.t > {before + 0.5}", timeout=5000)
        assert page.evaluate("game.mode") in ("ride", "crash")
        inside(page, "#vauhti")
    assert page.errors == []


# ---- Racing friends ----

def room_of(site, browser, names):
    build(site)
    relay = Relay()
    pages, ctxs = [], []
    for name in names:
        ctx, page = open_page(site, browser, name=name, relay=relay)
        pages.append(page)
        ctxs.append(ctx)
    host, guests = pages[0], pages[1:]
    host.click("#kaverit")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for g in guests:
        g.click("#kaverit")
        g.fill("#aipr-codeIn", code)
        g.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    for g in guests:
        g.wait_for_function("document.getElementById('vr-room').textContent.includes('Eero')")
    return relay, host, guests, ctxs


def test_three_phones_race_the_same_track_and_the_first_in_wins(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino", "Ville"])
    try:
        host.click("#aipr-start")
        for p in [host, *guests]:
            p.wait_for_function("net && net.cfg && game.mode === 'ride'", timeout=10000)
        assert {p.evaluate("game.track.len") for p in [host, *guests]} == {host.evaluate("game.track.len")}
        # Each friend's train is drawn on the others' tracks.
        host.wait_for_function("net.cars.filter(k => k.kind === 'net' && k.s > 0).length === 2", timeout=5000)
        # Aino comes in first, then Eero, then Ville.
        for p, back in [(guests[0], 25), (host, 25), (guests[1], 25)]:
            p.evaluate(f"auto = true; game.car.s = game.track.finish - {back}; game.car.check = game.car.s")
            p.wait_for_function("game.car.fin !== null", timeout=15000)
        for p in [host, *guests]:
            p.wait_for_selector("#loppu:not(.hidden)", timeout=15000)
        assert guests[0].locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert host.locator("#loppu-otsikko").inner_text() == "2. sija"
        assert guests[1].locator("#loppu-otsikko").inner_text() == "3. sija"
        assert host.locator("#tulokset li").count() == 3
        for p in [host, *guests]:
            p.click("#huoneeseen")
            p.wait_for_function("net === null && AiPelitRooms.inRoom", timeout=5000)
        for p in [host, *guests]:
            assert p.errors == []
    finally:
        for c in ctxs:
            c.close()


def test_the_computer_rides_for_a_friend_who_drops_off(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino"])
    guest = guests[0]
    try:
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && game.mode === 'ride'", timeout=10000)
        relay.drop(guest)
        host.wait_for_function("AiPelitRooms.paused", timeout=8000)
        # The host carries on without Aino: the computer takes her car to the finish.
        host.click("#aipr-goOn")
        host.wait_for_function("net.cars.some(k => k.kind === 'cpu')", timeout=5000)
        host.evaluate("net.cars.find(k => k.kind === 'cpu').car.s = game.track.finish - 20")
        host.evaluate("auto = true; game.car.s = game.track.finish - 20")
        host.wait_for_selector("#loppu:not(.hidden)", timeout=20000)
        assert host.locator("#tulokset li").count() == 2
        assert host.errors == []
    finally:
        for c in ctxs:
            c.close()


def test_a_phone_reloaded_mid_race_carries_on_from_where_it_was(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino"])
    guest = guests[0]
    try:
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && game.mode === 'ride'", timeout=10000)
        guest.evaluate("auto = true; game.car.s = 200; game.car.check = 200")
        host.wait_for_function("net.cars.find(k => k.kind === 'net').s > 200 && net.clock > 3", timeout=15000)
        guest.reload()
        guest.wait_for_function("net && game.mode === 'ride' && game.car.s > 195", timeout=15000)
        assert guest.evaluate("game.car.t") > 2.5   # the race clock, not a fresh start
        guest.evaluate("auto = true; game.car.s = game.track.finish - 20")
        host.evaluate("auto = true; game.car.s = game.track.finish - 60")
        for p in [host, guest]:
            p.wait_for_selector("#loppu:not(.hidden)", timeout=20000)
        assert guest.locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert host.locator("#loppu-otsikko").inner_text() == "2. sija"
        assert guest.errors == [] and host.errors == []
    finally:
        for c in ctxs:
            c.close()


def test_a_guest_rides_the_hosts_level_even_if_it_has_not_unlocked_it(site, browser):
    build(site)
    relay = Relay()
    ctxs = []
    try:
        hctx, host = open_page(site, browser, name="Eero", relay=relay, saves={"taso": 4, "valittu": 4})
        gctx, guest = open_page(site, browser, name="Aino", relay=relay)
        ctxs = [hctx, gctx]
        host.click("#kaverit")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost")
        guest.click("#kaverit")
        guest.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
        guest.click("#aipr-joinBtn")
        host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && net.cfg && game.mode === 'ride'", timeout=10000)
        assert guest.evaluate("game.level") == 4
        assert guest.evaluate("game.track.len") == host.evaluate("game.track.len")
        # Alone again, the guest's own progress is as it was: level 4 is still locked.
        guest.evaluate("toSolo()")
        assert guest.evaluate("[game.level, maxLevel]") == [1, 1]
    finally:
        for c in ctxs:
            c.close()


def test_the_faster_ride_wins_even_when_its_finish_is_heard_later(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino"])
    guest = guests[0]
    try:
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && game.mode === 'ride'", timeout=10000)
        # Aino's ride is 5 s faster, but the host finishes first and hears her finish after its own.
        guest.evaluate("game.car.t -= 5")
        host.evaluate("auto = true; game.car.s = game.track.finish - 5")
        host.wait_for_function("game.car.fin !== null", timeout=10000)
        guest.evaluate("auto = true; game.car.s = game.track.finish - 5")
        for p in [host, guest]:
            p.wait_for_selector("#loppu:not(.hidden)", timeout=20000)
        assert guest.locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert host.locator("#loppu-otsikko").inner_text() == "2. sija"
    finally:
        for c in ctxs:
            c.close()


def test_a_finished_phone_reloaded_while_others_ride_keeps_its_time_and_place(site, browser):
    relay, host, guests, ctxs = room_of(site, browser, ["Eero", "Aino"])
    guest = guests[0]
    try:
        host.click("#aipr-start")
        for p in [host, guest]:
            p.wait_for_function("net && game.mode === 'ride'", timeout=10000)
        guest.evaluate("auto = true; game.car.s = game.track.finish - 5")
        guest.wait_for_function("game.car.fin !== null", timeout=10000)
        fin = guest.evaluate("game.car.fin")
        host.wait_for_function("net.cars.find(k => k.kind === 'net').fin !== null", timeout=8000)
        guest.reload()
        guest.wait_for_function("net && game.car.fin !== null", timeout=15000)
        assert abs(guest.evaluate("game.car.fin") - fin) < 0.02
        host.wait_for_timeout(800)   # the reloaded phone's messages reach the host
        assert abs(host.evaluate("net.cars.find(k => k.kind === 'net').fin") - fin) < 0.02
        host.evaluate("auto = true; game.car.s = game.track.finish - 5")
        for p in [host, guest]:
            p.wait_for_selector("#loppu:not(.hidden)", timeout=20000)
        assert guest.locator("#loppu-otsikko").inner_text() == "Voitit kisan!"
        assert host.locator("#loppu-otsikko").inner_text() == "2. sija"
        assert guest.errors == []
    finally:
        for c in ctxs:
            c.close()


def test_changing_the_track_frees_the_old_tracks_materials_and_textures(page):
    # Each level change frees the old track's own geometry, materials and textures (the signs'
    # pictures, the finish banner...), and keeps the rail materials every track shares.
    res = page.evaluate("""() => {
      const freed = new Set(), seen = [];
      for (const lv of [2, 3, 2, 3]) {
        const old = scene.getObjectByName('rata'), own = new Set();
        old.traverse(o => { for (const x of [o.geometry, o.material, o.material && o.material.map]) if (x) own.add(x); });
        for (const x of own) x.addEventListener('dispose', () => freed.add(x));
        seen.push(own);
        maxLevel = 3; setLevel(lv);
      }
      const all = seen.flatMap(s => [...s]);
      const kept = all.filter(x => !freed.has(x));
      const signs = all.filter(x => x.isTexture).length;
      return { signs, keptTextures: kept.filter(x => x.isTexture).length, keptGeometries: kept.filter(x => x.isBufferGeometry).length,
               keptMaterials: new Set(kept.filter(x => x.isMaterial)).size, scenes: scene.children.filter(o => o.name === 'rata').length };
    }""")
    assert res["signs"] > 10
    assert res["keptTextures"] == 0
    assert res["keptGeometries"] == 0
    assert res["keptMaterials"] == 4   # rails, spine, ties, posts: shared by every track
    assert res["scenes"] == 1
    assert page.errors == []


def test_a_slow_phones_clock_keeps_real_time(page):
    # Every frame takes about 150 ms (under 7 a second): the ride's clock still follows the wall clock.
    page.click("#aja")
    page.wait_for_function("game.mode === 'ride'", timeout=8000)
    page.evaluate("game.car.s = 120; game.car.v = 10; auto = true")
    page.evaluate("""() => { const raf = window.requestAnimationFrame;
      window.requestAnimationFrame = f => raf(t => { const end = performance.now() + 150; while (performance.now() < end); f(t); }); }""")
    page.wait_for_timeout(600)
    t0, w0 = page.evaluate("[game.car.t, performance.now()]")
    page.wait_for_timeout(3000)
    t1, w1 = page.evaluate("[game.car.t, performance.now()]")
    assert (t1 - t0) == pytest.approx((w1 - w0) / 1000, rel=0.15)
