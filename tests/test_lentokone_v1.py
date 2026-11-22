"""Lentokone v1 (#533): a 3D flight from one airfield's runway to another's. Take-off by touch, every
route flown and landed by a scripted pilot, the landing judge, the stall, the approach retry, saves,
turning the phone, the menus' fit, a phone with no 3D, and lazy play that never lands."""
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/lentokone/v1/"
# A finger on the play area: [type, pointer id, x, y].
TOUCH = """([t, id, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: id, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# The test pilot: flies a route from the runway to a landing on plain numbers (world.js only).
PILOT = r"""
// A scripted pilot for the tests: flies a route from the runway to a landing on plain numbers.
function pilot(p, route, st) {
  const to = FIELDS[route.to], from = FIELDS[route.from];
  const g = guidance(p, route), agl = p.y - groundAt(p.x, p.z);
  st.phase = st.phase || 'roll';
  const steerBank = (want) => { p.sx = clamp((clamp(want, -0.5, 0.5) - p.bank) * 3, -1, 1); };
  const flyGam = (gw) => { const pw = gw + trimAoa(p); p.sy = clamp((pw - p.pit) * 5, -1, 1); };
  if (p.ground && !p.touch && !p.airborne) {
    const r = onRunway(from, p.x, p.z);
    p.thr = 1; p.flaps = 1;
    p.sx = clamp(-r.c * 0.08 - wrapAngle(p.hdg - from.hdg) * 3, -1, 1);
    p.sy = p.v > 27 ? 0.9 : 0;
    return;
  }
  if (p.ground) {   // landed: brake on the line
    const r = onRunway(to, p.x, p.z);
    p.thr = 0; p.brake = true; p.sy = 0;
    p.sx = clamp(-r.c * 0.08 - wrapAngle(p.hdg - to.hdg) * 3, -1, 1);
    return;
  }
  if (agl > 25) p.gear = false;
  if (agl > 70 && !g.lined) p.flaps = 0;
  let hw, altWant, vWant;
  if (!g.lined) {
    // Cruise: towards the approach point, high over the land ahead.
    let hi = 0;
    for (let d = 0; d <= 2500; d += 250) hi = Math.max(hi, groundAt(p.x + dirX(p.hdg) * d, p.z + dirZ(p.hdg) * d));
    altWant = Math.max(hi + 130, Math.max(from.elev, to.elev) + 220);
    hw = g.rel; vWant = 58;
    steerBank(hw * 1.2);
  } else {
    const r = onRunway(to, p.x, p.z);
    // Fly the ground track (wind included) down the line, a little towards it when off it.
    const w = windOf(route, p.t), hv = p.v * Math.cos(p.gam);
    const trk = Math.atan2(dirX(p.hdg) * hv + w.x, -(dirZ(p.hdg) * hv + w.z));
    const cdot = (st.lc === undefined ? 0 : (r.c - st.lc) / DT); st.lc = r.c;
    const err = wrapAngle(to.hdg + clamp(-r.c * 0.008 - cdot * 0.03, -0.35, 0.35) - trk);
    steerBank(clamp(err * 3, agl < 10 ? -0.08 : -0.5, agl < 10 ? 0.08 : 0.5));
    p.gear = true;
    p.flaps = g.runwayDist < 2500 ? 2 : 1;
    altWant = to.elev + Math.max(0, -(r.a - (to.len < 700 ? 110 : 220))) * Math.tan(GLIDE);
    vWant = to.len < 700 ? 29 : 32;
  }
  let gw = clamp((altWant - p.y) * 0.012, -0.11, 0.1);
  if (g.lined && agl < 10) { gw = -0.025; vWant = 0; }
  flyGam(gw);
  p.thr = clamp(0.45 + (vWant - p.v) * 0.12, 0, 1);
  if (g.lined && agl < 10) p.thr = 0;
}
function flyRoute(route, start, maxT) {
  const p = start || newPlane(route), st = {};
  for (let t = 0; t < (maxT || 900) && !(p.over && p.over.stopped); t += DT) { pilot(p, route, st); step(p, DT, route); }
  return p;
}
"""


def open_game(site, context, width=360, height=740):
    if not (site.games / "lentokone").exists():
        shutil.copytree(ROOT / "games" / "lentokone", site.games / "lentokone")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("V3 || no3d", timeout=20000)
    page.add_script_tag(content=PILOT)
    return page


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'fly'", timeout=8000)


def land_now(page):
    """Flies the rest of the live flight at once with the test pilot; the game's loop then ends it."""
    return page.evaluate("() => { const q = flyRoute(route, p, 900); return q.over; }")


def test_the_menu_opens_the_first_route_only(site, context):
    page = open_game(site, context)
    assert page.evaluate("!!V3")
    routes = page.locator("#routes button")
    assert routes.count() == 5
    assert [routes.nth(i).is_disabled() for i in range(5)] == [False, True, True, True, True]
    assert "🔒 Laskeudu ensin: Ensilento" in routes.nth(1).inner_text()
    assert page.errors == []


def test_take_off_by_touch_lifts_near_the_rotate_speed(site, context):
    page = open_game(site, context)
    go(page)
    # Record the speed at the moment the wheels leave the ground.
    page.evaluate("""() => { const s = step; window.liftV = 0;
      window.step = (q, dt, r) => { const g = q.ground; s(q, dt, r); if (g && !q.ground && !liftV) liftV = q.v * 3.6; }; }""")
    t = page.evaluate("L.thr")
    x, y = t["x"] + t["w"] / 2, t["y"] + t["h"] - 10
    page.evaluate(TOUCH, ["pointerdown", 2, x, y])
    page.evaluate(TOUCH, ["pointermove", 2, x, y - t["h"]])
    page.evaluate(TOUCH, ["pointerup", 2, x, y - t["h"]])
    assert page.evaluate("p.thr") == 1
    page.wait_for_function("p.v * 3.6 > 95", timeout=30000)
    assert page.evaluate("p.ground")
    # Finger down on the left and pulled down: nose up (the default stick).
    page.evaluate(TOUCH, ["pointerdown", 3, 100, 500])
    page.evaluate(TOUCH, ["pointermove", 3, 100, 535])
    page.wait_for_function("!p.ground", timeout=10000)
    page.evaluate(TOUCH, ["pointerup", 3, 100, 535])
    v = page.evaluate("liftV")
    assert 85 < v < 125, v
    page.wait_for_function("p.y - groundAt(p.x, p.z) > 20", timeout=10000)
    assert page.evaluate("p.over") is None
    assert page.errors == []


def test_the_plane_stays_on_the_runway_without_the_stick(site, context):
    """Below the rotate speed the stick's nose-up does not lift it: the plane rolls until pulled."""
    page = open_game(site, context)
    res = page.evaluate("""() => { const q = newPlane(ROUTES[0]); q.thr = 1; q.sy = 1;
      while (q.v < 20) step(q, DT, ROUTES[0]); return { ground: q.ground, v: q.v }; }""")
    assert res["ground"]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_every_route_can_be_flown_and_landed(site, context, n):
    page = open_game(site, context)
    res = page.evaluate(f"""() => {{ const r = ROUTES[{n - 1}], q = flyRoute(r);
      return {{ over: q.over, t: q.t, onTo: runwayAt(q.x, q.z, 0) === r.to }}; }}""")
    o = res["over"]
    assert o and o["ok"], o
    assert o["stars"] >= 1 and o["points"] > 0
    assert res["onTo"]
    assert res["t"] < 400
    # From the approach too ("Harjoittele laskeutumista").
    o2 = page.evaluate(f"() => {{ const r = ROUTES[{n - 1}], q = approachPlane(r); return flyRoute(r, q).over; }}")
    assert o2 and o2["ok"], o2
    assert page.errors == []


def test_the_approach_start_is_on_the_glide_path(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => { const r = ROUTES[0], f = FIELDS[r.to], q = approachPlane(r), g = guidance(q, r);
      return { lined: g.lined, dist: g.runwayDist, h: q.y - f.elev, gear: q.gear, ground: q.ground }; }""")
    assert res["lined"] and not res["ground"]
    assert 4000 < res["dist"] < 6000
    assert 200 < res["h"] < 400


# The plane put just over the target runway, falling as asked; the judge's verdict.
JUDGE = """([sink, c, bank, gear, a]) => { const r = ROUTES[0], f = FIELDS[r.to], q = approachPlane(r);
  const ax = Math.sin(f.hdg), az = -Math.cos(f.hdg);
  q.x = f.x + ax * a + Math.cos(f.hdg) * c; q.z = f.z + az * a + Math.sin(f.hdg) * c;
  q.hdg = f.hdg; q.y = f.elev + 0.3; q.v = 30; q.gam = -Math.asin(sink / 30); q.pit = 0.05; q.bank = bank;
  q.gear = gear; q.flaps = 2; q.thr = 0;
  for (let i = 0; i < 120 * 60 && !(q.over && q.over.stopped); i++) { q.brake = q.ground; q.sx = q.sy = 0; step(q, DT, r); }
  return q.over; }"""


def test_the_landing_judge(site, context):
    page = open_game(site, context)
    soft = page.evaluate(JUDGE, [1.0, 0, 0, True, 220])
    assert soft["ok"] and soft["stars"] >= 2, soft
    assert page.evaluate(JUDGE, [4.5, 0, 0, True, 220])["why"] == "Liian kova lasku"
    assert page.evaluate(JUDGE, [1.0, 0, 0, False, 220])["why"] == "Telineet ylhäällä"
    assert page.evaluate(JUDGE, [1.0, 0, 0.4, True, 220])["why"] == "Siipi maahan"
    assert page.evaluate(JUDGE, [1.0, 60, 0, True, 220])["ok"] is False
    # A softer, straighter touchdown scores more.
    hard = page.evaluate(JUDGE, [2.6, 10, 0, True, 220])
    assert hard["ok"] and hard["points"] < soft["points"]


def test_a_slow_nose_up_plane_stalls_and_drops_its_nose(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => { const r = ROUTES[0], q = approachPlane(r); q.y += 500; q.thr = 0.2; let stalled = false, pit = 0;
      for (let i = 0; i < 120 * 12; i++) { q.sx = 0; q.sy = 1; step(q, DT, r); if (q.stall && !stalled) { stalled = true; pit = q.pit; } }
      const low = q.pit; return { stalled, pit, low, v: q.v }; }""")
    assert res["stalled"]
    assert res["low"] < res["pit"]


def test_lazy_play_never_lands(site, context):
    """Full throttle and no stick, on every route: the plane never lands for points."""
    page = open_game(site, context)
    res = page.evaluate("""() => ROUTES.map(r => { const q = newPlane(r); let t = 0;
      for (; t < 900 && !(q.over && q.over.stopped) && !guidance(q, r).lost; t += DT) { q.thr = 1; q.sx = q.sy = 0; step(q, DT, r); }
      return q.over && q.over.ok; })""")
    assert not any(res), res


def test_a_landing_opens_the_next_route_and_scores(site, context):
    page = open_game(site, context)
    go(page)
    assert land_now(page)["ok"]
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.locator("#endTitle").inner_text() == "Laskeutuminen onnistui!"
    assert page.locator("#endParts li").count() == 5
    assert page.locator("#next").is_visible()
    assert page.evaluate("localStorage.getItem('ai-pelit:lentokone:auki')") == "2"
    assert int(page.evaluate("localStorage.getItem('ai-pelit:lentokone:ennatys-1')")) > 0
    assert page.evaluate("localStorage.getItem('ai-pelit:lentokone:lento')") is None
    # scores.js opens the route's list over the end screen after a new score.
    page.locator("#ai-pelit-tulokset button", has_text="Sulje").click()
    page.click("#toMenu")
    assert not page.locator("#routes button").nth(1).is_disabled()
    assert page.errors == []


def test_a_practice_landing_counts_on_screen_only(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("mode === 'fly'", timeout=8000)
    page.evaluate("() => { startFlight(true); }")
    assert page.evaluate("p.practice")
    assert land_now(page)["ok"]
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.locator("#endTitle").inner_text() == "Laskeutuminen onnistui!"
    assert "Harjoituslasku" in page.locator("#endNote").inner_text()
    assert page.evaluate("localStorage.getItem('ai-pelit:lentokone:auki')") in (None, "1")
    assert page.evaluate("localStorage.getItem('ai-pelit:lentokone:ennatys-1')") is None
    assert page.locator("#approach").is_visible() and not page.locator("#next").is_visible()
    assert page.errors == []


def test_the_lights_show_two_white_on_the_glide_path(site, context):
    page = open_game(site, context)
    for r in range(5):
        for d in (300, 1000, 2500, 4000):
            lit = page.evaluate(f"""() => {{ const r = ROUTES[{r}], f = FIELDS[r.to], q = approachPlane(r);
              q.x = f.x - dirX(f.hdg) * {d}; q.z = f.z - dirZ(f.hdg) * {d}; q.y = guidance(q, r).glideH;
              return papi(q, f); }}""")
            assert lit.count(True) == 2, (r, d, lit)


def test_a_landing_ends_on_the_brake_with_some_throttle_left(site, context):
    page = open_game(site, context)
    o = page.evaluate("""() => { const r = ROUTES[0], f = FIELDS[r.to], q = approachPlane(r);
      q.x = f.x + dirX(f.hdg) * 220; q.z = f.z + dirZ(f.hdg) * 220; q.hdg = f.hdg + 0.08;
      q.y = f.elev + 0.3; q.v = 31; q.gam = -Math.asin(1 / 31); q.pit = 0.05; q.gear = true; q.flaps = 2; q.thr = 0.2;
      for (let i = 0; i < 120 * 60 && !(q.over && q.over.stopped); i++) { q.brake = q.ground; q.sx = q.sy = 0; step(q, DT, r); }
      return Object.assign({ hdgOff: Math.abs(wrapAngle(q.hdg - f.hdg)) }, q.over); }""")
    assert o["ok"] and o["stop"] > 0, o
    assert o["hdgOff"] < 1e-6


def test_pause_is_not_offered_once_the_flight_has_ended(site, context):
    page = open_game(site, context)
    go(page)
    assert land_now(page)["ok"]
    page.evaluate("pause()")
    assert page.evaluate("mode") == "fly"
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.evaluate("localStorage.getItem('ai-pelit:lentokone:auki')") == "2"


def test_a_crash_offers_the_approach(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { p.x = FIELDS[0].x + 300; p.z = FIELDS[0].z - 3000; p.y = groundAt(p.x, p.z) + 40; p.v = 50; p.ground = false; p.airborne = true; p.gear = false; p.gam = -0.3; p.pit = -0.3; }")
    page.wait_for_function("mode === 'end'", timeout=15000)
    assert page.locator("#endTitle").inner_text() == "Lento päättyi"
    assert page.locator("#approach").is_visible()
    page.click("#approach")
    page.wait_for_function("mode === 'fly' && !p.ground", timeout=8000)
    assert page.evaluate("guidance(p, route).lined")
    assert page.errors == []


def test_a_reload_mid_flight_goes_on_from_the_same_spot(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { const q = approachPlane(route); Object.assign(p, q); }")
    page.wait_for_timeout(1400)
    spot = page.evaluate("({ x: p.x, z: p.z })")
    page.reload()
    page.wait_for_function("V3 || no3d", timeout=20000)
    assert page.locator("#resume").is_visible()
    page.click("#resume")
    page.wait_for_function("mode === 'fly'", timeout=8000)
    now = page.evaluate("({ x: p.x, z: p.z, ground: p.ground })")
    assert not now["ground"]
    assert abs(now["x"] - spot["x"]) + abs(now["z"] - spot["z"]) < 200
    assert page.errors == []


def test_turning_the_phone_keeps_the_flight(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { const q = approachPlane(route); Object.assign(p, q); }")
    page.wait_for_timeout(300)
    t0 = page.evaluate("p.t")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND", timeout=5000)
    page.wait_for_timeout(500)
    assert page.evaluate("mode") == "fly"
    assert page.evaluate("p.t") > t0
    assert page.evaluate("L.thr.y + L.thr.h") <= 360
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360)])
def test_the_menus_fit_without_scrolling(site, context, size):
    w, h = size
    page = open_game(site, context, w, h)
    fits = """(sel) => [...document.querySelectorAll(sel + ' button:not([hidden]), ' + sel + ' h1, ' + sel + ' h2')]
      .filter(e => e.offsetParent).every(e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight + 0.5 && r.right <= innerWidth + 0.5; })"""
    assert page.evaluate(fits, "#menu")
    go(page)
    land_now(page)
    page.wait_for_function("mode === 'end'", timeout=8000)
    assert page.evaluate(fits, "#end")
    assert page.errors == []


def test_a_phone_with_no_3d_says_so(site, context):
    if not (site.games / "lentokone").exists():
        shutil.copytree(ROOT / "games" / "lentokone", site.games / "lentokone")
        site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.add_init_script("""HTMLCanvasElement.prototype.getContext = (o => function (k, ...a) {
      return /webgl/.test(k) ? null : o.call(this, k, ...a); })(HTMLCanvasElement.prototype.getContext);
      window.__said = []; const f = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function (t, ...a) { __said.push(t); return f.call(this, t, ...a); };""")
    page.goto(site.url + URL)
    page.wait_for_function("no3d", timeout=20000)
    page.wait_for_function("__said.includes('Tämä puhelin ei osaa piirtää 3D-kuvaa.')", timeout=5000)
    assert page.locator("#go").is_visible()
    assert page.errors == []
