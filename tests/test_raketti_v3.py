"""Raketti v3 (#548): a small Earth and Moon, six trips, a nose that holds where it points.

The flights here are flown by scripted test pilots (PILOT below) through the same things the
player's controls set: throttle, nose direction, pointing mode, translation and time warp. The
game itself has no autopilot.
"""
import shutil

import pytest

from conftest import ROOT, turn

URL = 'games/raketti/v3/'

# Test pilots only, never shipped. They set ship.throttle, ship.angle, ship.point, held.* and
# warp, exactly what the slider, the turn and point buttons, the thrusters and "Aika" set.
PILOT = r"""
// A scripted pilot that flies only through the player's controls' effects (throttle, nose, warp).
window.pilot = function (opts = {}) {
  const log = [];
  const frame = 1 / 30, thrustWarp = opts.thrustWarp || 2;
  let stage = 'ascent', guard = 0;
  const radial = (b = EARTH) => { const q = relative(b, ship); return Math.atan2(q.x, q.y); };
  const fly = (w) => { warp = Math.min(w, maxWarp()); advanceFlight(frame); };
  const aimApo = opts.aimApo || 4.88e6;
  while (ship.phase === 'flight' && guard++ < 200000) {
    const o = orbitAround(EARTH, ship), h = o.altitude;
    if (stage === 'ascent') {
      ship.throttle = 1;
      if (h > 1500) { ship.point = null; ship.angle = wrap(radial() + ascentPitch(h) * Math.PI / 180); }
      if (o.apo >= 60000) { ship.throttle = 0; stage = 'coast1'; log.push(['meco', ship.t, ship.real]); }
      fly(thrustWarp); continue;
    }
    if (stage === 'coast1') {
      ship.point = 'pro';
      if (o.toApo < 8 || o.vr < 0) { stage = 'circ'; }
      fly(o.toApo > 60 ? 1000 : 1); continue;
    }
    if (stage === 'circ') {
      ship.point = 'pro'; ship.throttle = 1;
      if (o.peri > 45000) { ship.throttle = 0; stage = 'wait'; log.push(['orbit', ship.t, ship.real, Math.round(deltaV())]); }
      fly(thrustWarp); continue;
    }
    if (opts.stop === 'orbit') break;
    if (stage === 'wait') {
      ship.point = 'pro';
      const T = opts.target || MOON, lead = transferLead(o.r, T.orbit.r, T.orbit.n), ahead = leadOf(bodyAt(T, ship.t), ship);
      const wait = ((ahead - lead) % TAU + TAU) % TAU;
      if (wait < 1 * Math.PI / 180 || wait > TAU - 0.5 * Math.PI / 180) { stage = 'tli'; log.push(['tli', ship.t, ship.real]); }
      fly(wait > 0.2 ? 1000 : wait > 0.03 ? 100 : 5); continue;
    }
    if (stage === 'tli') {
      ship.point = 'pro'; ship.throttle = o.apo + EARTH_R > aimApo - 2e5 ? 0.05 : 1;
      if (o.apo + EARTH_R >= aimApo) { ship.throttle = 0; stage = opts.stop === 'tli' ? 'end' : 'cruise'; log.push(['tliEnd', ship.t, ship.real, Math.round(deltaV())]); }
      fly(thrustWarp); continue;
    }
    if (stage === 'cruise') {
      const m = orbitAround(MOON, ship);
      if (opts.stop === 'moon' && refBody() === MOON) break;
      if (refBody() === MOON && !opts.noFix && (m.peri < 15000 || m.peri > 60000) && m.vr < 0 && m.altitude > 60000) {
        const q = relative(MOON, ship), sg = Math.sign(m.h) * (m.peri < 15000 ? 1 : -1);
        ship.point = null; ship.angle = Math.atan2(-q.y * sg, q.x * sg); ship.throttle = 0.05; fly(2);
        if (!log.fix) { log.fix = 1; log.push(['fix', ship.t, ship.real, Math.round(m.peri)]); }
        continue;
      }
      ship.throttle = 0;
      if (refBody() === MOON && m.vr >= 0) { stage = 'loi'; log.push(['peri', ship.t, ship.real, Math.round(m.altitude)]); }
      if (refBody() === MOON && m.altitude < 30000 && m.vr < 0 && m.altitude - m.peri < 2000) { stage = 'loi'; log.push(['nearperi', ship.t, ship.real, Math.round(m.altitude)]); }
      ship.point = 'retro';
      fly(1000); continue;
    }
    if (stage === 'loi') {
      ship.point = 'retro'; const m = orbitAround(MOON, ship);
      ship.throttle = m.energy < 0 && m.apo < 400000 ? 0.1 : 1;
      if (m.energy < 0 && m.apo < 250000) { ship.throttle = 0; log.push(['loiEnd', ship.t, ship.real, Math.round(deltaV()), Math.round(m.peri), Math.round(m.apo)]); stage = 'done'; }
      fly(thrustWarp); continue;
    }
    break;
  }
  return { phase: ship.phase, reason: ship.reason, t: ship.t, real: ship.real, dv: deltaV(), stars: ship.stars, log };
};
// Land on body b from wherever the ship is near it: kill sideways speed, then fall on a
// throttle that keeps the descent under a speed that shrinks with height.
window.lander = function (b, opts = {}) {
  const frame = 1 / 30, log = []; let guard = 0;
  const fly = (w) => { warp = Math.min(w, maxWarp()); advanceFlight(frame); };
  while (ship.phase === 'flight' && !ship.landedOn && guard++ < 200000) {
    const q = relative(b, ship), r = Math.hypot(q.x, q.y), h = r - b.radius - SHIP.length / 2;
    const ux = q.x / r, uy = q.y / r, down = -(q.vx * ux + q.vy * uy);
    const sx = q.vx + down * ux, sy = q.vy + down * uy, side = Math.hypot(sx, sy);
    const g = b.mu / r / r, amax = Math.min(SHIP.thrust / mass(), SHIP.accCap);
    const target = Math.max(b.id === 'rock' ? 0.3 : 1.2, Math.sqrt(2 * 0.3 * amax * Math.max(0, h - 5)) * (b.id === 'rock' ? 0.3 : 1));
    // Thrust vector wanted: cancel side speed, hold descent at target.
    let wx = -sx * 0.5, wy = -sy * 0.5;
    const vert = g + (down - target) * 2;
    wx += ux * vert; wy += uy * vert;
    const need = Math.hypot(wx, wy);
    if (need > 1e-4 && (h > 60 || side > 0.3)) { ship.point = null; ship.angle = Math.atan2(wx, wy); }
    else ship.point = 'up';
    ship.throttle = clamp(need / amax, 0, 1);
    if (Math.cos(ship.angle - Math.atan2(wx, wy)) < 0.9) ship.throttle = 0;
    fly(opts.warp || 2);
  }
  return { phase: ship.phase, landed: ship.landedOn, reason: ship.reason, real: ship.real, dv: deltaV(), touch: ship.touch, stars: ship.stars };
};
// Meet a moving body: wait at the closest point of the coasting path, match its speed,
// then drift in at a speed that shrinks with distance.
window.meet = function (b, opts = {}) {
  const frame = 1 / 30, log = []; let guard = 0, stage = 'coast';
  const fly = (w) => { warp = Math.min(w, maxWarp()); advanceFlight(frame); };
  while (ship.phase === 'flight' && guard++ < 300000) {
    const q = relative(b, ship), r = Math.hypot(q.x, q.y), h = r - b.radius;
    const closing = -(q.x * q.vx + q.y * q.vy) / r;
    if (stage === 'coast') {
      if (closing <= 0 && r < (opts.within || 400000)) { stage = 'match'; log.push(['closest', ship.t, ship.real, Math.round(h)]); }
      fly(1000); continue;
    }
    if (stage === 'match') {
      const v = Math.hypot(q.vx, q.vy);
      ship.point = null; ship.angle = Math.atan2(-q.vx, -q.vy);
      ship.throttle = clamp(v / 20, 0.02, 1);
      if (v < 1) { ship.throttle = 0; stage = 'drift'; log.push(['matched', ship.t, ship.real, Math.round(h), Math.round(deltaV())]); }
      fly(2); continue;
    }
    if (stage === 'drift') {
      const want = Math.min(opts.cruise || 200, Math.sqrt(h) * 1.2);
      const ux = -q.x / r, uy = -q.y / r;
      const ex = ux * want - q.vx, ey = uy * want - q.vy, err = Math.hypot(ex, ey);
      if (h < (opts.landFrom || 3000)) break;
      if (err > 3) { ship.point = null; ship.angle = Math.atan2(ex, ey); ship.throttle = clamp(err / 40, 0.01, 1); fly(2); }
      else { ship.throttle = 0; fly(100); }
      continue;
    }
  }
  log.push(['meetEnd', ship.t, ship.real, Math.round(deltaV())]);
  return log;
};
window.placeAround = function (b, alt, fuelDv) {
  const p = bodyAt(b, ship.t), r = b.radius + alt, v = Math.sqrt(b.mu / r), a = 1.0;
  Object.assign(ship, { x: p.x + r * Math.sin(a), y: p.y + r * Math.cos(a), vx: p.vx + v * Math.cos(a), vy: p.vy - v * Math.sin(a), landedOn: null, point: null, throttle: 0 });
  if (fuelDv) ship.fuel = fuelForDeltaV(fuelDv);
};
// From the Moon's surface home to Earth under the parachute.
window.homer = function (opts = {}) {
  const frame = 1 / 30, log = []; let guard = 0, stage = 'up';
  const fly = (w) => { warp = Math.min(w, maxWarp()); advanceFlight(frame); };
  while (ship.phase === 'flight' && guard++ < 400000) {
    const m = orbitAround(MOON, ship), q = relative(MOON, ship), up = Math.atan2(q.x, q.y);
    const dir = 1;
    if (stage === 'up') {
      ship.throttle = 1; ship.point = null;
      ship.angle = wrap(up + dir * clamp(0.35 + m.altitude / 2000, 0.35, 1.5));
      if (m.apo > 20000) { ship.throttle = 0; stage = 'coast'; log.push(['moonApo', ship.t, ship.real, Math.round(deltaV())]); }
      fly(2); continue;
    }
    if (stage === 'coast') {
      ship.point = 'pro';
      if (m.toApo < 5 || m.vr < 0) stage = 'circ';
      fly(m.toApo > 30 ? 100 : 1); continue;
    }
    if (stage === 'circ') {
      ship.point = 'pro'; ship.throttle = 1;
      if (m.peri > 12000) { ship.throttle = 0; stage = 'wait'; log.push(['moonOrbit', ship.t, ship.real, Math.round(deltaV())]); }
      fly(2); continue;
    }
    if (stage === 'wait') {
      // Burn where the ship moves against the Moon's own motion, so it falls to Earth.
      const mv = bodyAt(MOON, ship.t), along = (q.vx * mv.vx + q.vy * mv.vy) / Math.hypot(q.vx, q.vy) / Math.hypot(mv.vx, mv.vy);
      ship.point = 'pro';
      if (along < -0.995) { stage = 'tei'; log.push(['tei', ship.t, ship.real]); }
      fly(along < -0.9 ? 5 : 100); continue;
    }
    if (stage === 'tei') {
      ship.point = 'pro'; ship.throttle = 1;
      const path = predictPath(ship), c = path.closest.earth;
      if (c && c.d < 25000) { ship.throttle = 0; stage = 'cruise'; log.push(['teiEnd', ship.t, ship.real, Math.round(deltaV()), Math.round(c.d)]); }
      fly(1); continue;
    }
    if (stage === 'cruise') {
      const h = Math.hypot(ship.x, ship.y) - EARTH_R, v = Math.hypot(ship.vx, ship.vy);
      ship.point = h < 60000 ? 'retro' : null;
      if (ship.chute === 'packed' && h < CHUTE.height && v < CHUTE.speed - 20) { openChute(); log.push(['chute', ship.t, ship.real, Math.round(h), Math.round(v)]); }
      fly(1000); continue;
    }
  }
  return { phase: ship.phase, reason: ship.reason, real: ship.real, dv: deltaV(), touch: ship.touch, stars: ship.stars, log };
};
// From a low Earth orbit up to the station and into its port.
window.docker = function (opts = {}) {
  const frame = 1 / 30, log = []; let guard = 0, stage = 'wait';
  const fly = (w) => { warp = Math.min(w, maxWarp()); advanceFlight(frame); };
  while (ship.phase === 'flight' && guard++ < 400000) {
    const o = orbitAround(EARTH, ship), st = station(ship), d = approach(ship);
    if (stage === 'wait') {
      ship.point = 'pro';
      const lead = transferLead(o.r, STATION_R, STATION_N), ahead = leadOf(st, ship);
      const wait = ((ahead - lead) % TAU + TAU) % TAU;
      if (wait < 0.5 * Math.PI / 180 || wait > TAU - 0.3 * Math.PI / 180) { stage = 'raise'; log.push(['raise', ship.t, ship.real, Math.round(wait * 57.3)]); }
      fly(wait > 0.2 ? 1000 : wait > 0.03 ? 100 : 5); continue;
    }
    if (stage === 'raise') {
      ship.point = 'pro'; ship.throttle = 0.1;
      if (o.apo + EARTH_R >= STATION_R) { ship.throttle = 0; stage = 'coast'; log.push(['raised', ship.t, ship.real, Math.round(deltaV())]); }
      fly(1); continue;
    }
    if (stage === 'coast') {
      ship.point = 'pro';
      if (Math.hypot(ship.x - st.x, ship.y - st.y) < 15000 || (o.toApo < 4 && o.vr > 0)) { stage = 'circ'; log.push(['apo', ship.t, ship.real, Math.round(d.range)]); }
      fly(o.toApo > 60 ? 1000 : 1); continue;
    }
    if (stage === 'circ') {
      ship.point = 'pro'; ship.throttle = 0.1;
      if (o.peri > STATION_R - EARTH_R - 4000) { ship.throttle = 0; stage = 'close'; log.push(['close', ship.t, ship.real, Math.round(d.range), Math.round(deltaV())]); }
      fly(1); continue;
    }
    if (stage === 'close') {
      // Main engine, velocity aimed at a point 40 m behind the port.
      const ax = st.px - 40 * st.tx, ay = st.py - 40 * st.ty;
      const nx = ship.x + Math.sin(ship.angle) * SHIP.length / 2, ny = ship.y + Math.cos(ship.angle) * SHIP.length / 2;
      const dx = ax - nx, dy = ay - ny, dist = Math.hypot(dx, dy);
      const want = Math.min(80, Math.sqrt(dist) * 0.4);
      const ex = dx / dist * want - (ship.vx - st.vx), ey = dy / dist * want - (ship.vy - st.vy), err = Math.hypot(ex, ey);
      if (dist < 8 && Math.hypot(ship.vx - st.vx, ship.vy - st.vy) < 0.5) { ship.throttle = 0; stage = 'dock'; log.push(['hold', ship.t, ship.real, Math.round(deltaV())]); continue; }
      if (err > 0.4) {
        ship.point = null; ship.angle = Math.atan2(ex, ey);
        ship.throttle = clamp(err / (2 * SHIP.accCap), 0.001, 1);
      } else ship.throttle = 0;
      fly(5); continue;
    }
    if (stage === 'dock') {
      ship.point = null; ship.angle = wrap(st.angle); ship.omega = 0; ship.throttle = 0;
      const nx = ship.x + Math.sin(ship.angle) * SHIP.length / 2, ny = ship.y + Math.cos(ship.angle) * SHIP.length / 2;
      const dx = st.px - nx, dy = st.py - ny, dist = Math.hypot(dx, dy);
      const vx = dx / dist * Math.min(0.3, dist * 0.1), vy = dy / dist * Math.min(0.3, dist * 0.1);
      const ex = vx - (ship.vx - st.pvx), ey = vy - (ship.vy - st.pvy);
      const fx = Math.sin(ship.angle), fy = Math.cos(ship.angle), rx = Math.cos(ship.angle), ry = -Math.sin(ship.angle);
      held.forward = clamp((ex * fx + ey * fy) / 0.05, -1, 1); held.side = clamp((ex * rx + ey * ry) / 0.05, -1, 1);
      fly(1); continue;
    }
  }
  clearHeld();
  return { phase: ship.phase, reason: ship.reason, real: ship.real, dv: deltaV(), touch: ship.touch, stars: ship.stars, log };
};
"""


def open_game(site, context):
    shutil.copytree(ROOT / 'games/raketti', site.games / 'raketti')
    site.build()
    page = context.new_page()
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof ship !== 'undefined' && !!document.querySelector('#trips .trip')")
    return page


def fly(page, body):
    """Runs body (JS statements ending in a return) with the frame loop stopped and the pilots loaded."""
    if not page.evaluate('typeof window.pilot === "function"'):
        page.add_script_tag(content=PILOT)
    return page.evaluate('() => { cancelAnimationFrame(frameId); frameId = 0; paused = false; ' + body + ' }')


def test_pad_to_moon_orbit_takes_under_five_minutes(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('kuu-kierto', 'pad'); return pilot();")
    assert r['phase'] == 'done', r
    assert r['real'] < 300, r
    assert r['stars'] >= 2 and r['dv'] >= 3300, r
    assert page.evaluate('JSON.parse(localStorage.getItem("ai-pelit:raketti:tahdet"))["kuu-kierto"]') == r['stars']
    assert page.errors == []


def test_first_trip_reaches_orbit_with_three_stars(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('kiertorata', 'pad'); return pilot({stop: 'orbit'});")
    assert r['phase'] == 'done', r
    assert r['real'] < 180 and r['stars'] == 3, r
    page.evaluate('showResult()')
    assert page.locator('#result-title').inner_text() == 'Matka onnistui!'
    assert page.locator('#result-next').inner_text() == 'Seuraava: Avaruusasemalle'
    assert page.locator('#result-list li.lit').count() == 3
    assert page.errors == []


def test_moon_landing_from_the_pad(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('kuuhun', 'pad'); const a = pilot(); const l = lander(MOON); return {a, l};")
    assert r['l']['phase'] == 'done', r
    assert r['l']['landed'] == 'moon' and r['l']['touch']['soft'], r
    assert r['l']['real'] < 7 * 60, r
    assert page.errors == []


def test_home_from_the_moon_under_the_parachute(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('kotiin', 'pad'); pilot(); lander(MOON); "
                  "if (ship.landedOn !== 'moon') return {phase: ship.phase, reason: ship.reason}; "
                  "const h = homer(); return {...h, visited: ship.visited};")
    assert r['phase'] == 'done', r
    assert set(r['visited']) == {'moon', 'earth'}, r
    assert r['touch']['body'] == 'earth' and r['touch']['speed'] <= 10, r
    assert r['real'] < 10 * 60, r
    assert page.errors == []


def test_rock_landing(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('kivi', 'pad'); pilot({target: ROCK, aimApo: 2.0e6 + 1500, stop: 'tli'}); "
                  "meet(ROCK, {within: 400000}); return lander(ROCK);")
    assert r['phase'] == 'done' and r['landed'] == 'rock', r
    assert r['touch']['speed'] <= 1, r
    assert r['real'] < 7 * 60, r
    assert page.errors == []


def test_docking_at_the_station(site, context):
    page = open_game(site, context)
    r = fly(page, "ship = freshFlight('asema', 'pad'); pilot({stop: 'orbit'}); return docker();")
    assert r['phase'] == 'done', r
    assert r['reason'].startswith('Telakointi onnistui'), r
    assert r['touch']['body'] == 'station' and r['touch']['speed'] <= 0.5, r
    assert r['real'] < 12 * 60, r
    assert page.errors == []


# Drops the ship onto a body from just above it with a chosen down speed, sideways speed and tilt.
DROP = """([trip, id, down, side, tilt]) => {
  cancelAnimationFrame(frameId); frameId = 0; paused = false;
  ship = freshFlight(trip, 'orbit'); const b = body(id), p = bodyAt(b, 0), a = 0.5;
  const r = b.radius + SHIP.length / 2 + 0.01, ux = Math.sin(a), uy = Math.cos(a);
  Object.assign(ship, { x: p.x + r * ux, y: p.y + r * uy, vx: p.vx - down * ux + side * uy,
    vy: p.vy - down * uy - side * ux, angle: wrap(a + tilt * Math.PI / 180), landedOn: null, point: null });
  step(0.05);
  return { phase: ship.phase, reason: ship.reason, touch: ship.touch, landed: ship.landedOn };
}"""


@pytest.mark.parametrize('trip,where,down,side,tilt,phase,why', [
    ('kuuhun', 'moon', 1, 0.5, 5, 'done', ''),
    ('kuuhun', 'moon', 4, 0, 0, 'crashed', 'Liian kova vauhti alas'),
    ('kuuhun', 'moon', 1, 3, 0, 'crashed', 'Liian kova sivuvauhti'),
    ('kuuhun', 'moon', 1, 0, 20, 'crashed', 'Alus kallistui 20°'),
    ('kivi', 'rock', 0.4, 0.2, 20, 'done', ''),
    ('kivi', 'rock', 1.2, 0, 0, 'crashed', 'Liian kova vauhti'),
    ('kotiin', 'earth', 1, 0, 0, 'crashed', 'Matkan tavoite jäi kesken'),
])
def test_landing_limits(site, context, trip, where, down, side, tilt, phase, why):
    page = open_game(site, context)
    r = page.evaluate(DROP, [trip, where, down, side, tilt])
    assert r['phase'] == phase, r
    assert why in r['reason'], r
    if phase == 'done':
        assert r['landed'] == where and r['touch']['soft'], r
    assert page.errors == []


def test_parachute_opens_only_low_and_slow_and_lands_softly(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      cancelAnimationFrame(frameId); frameId = 0; paused = false;
      const at = (h, v, vy = -50) => { ship = freshFlight('kotiin', 'pad');
        Object.assign(ship, { x: 0, y: EARTH_R + h, vx: v, vy, landedOn: null, visited: ['moon'],
          fuel: fuelForDeltaV(1500) }); };
      at(15000, 300, 50); const rising = openChute(), risingState = ship.chute;
      at(25000, 300); const high = openChute(), highState = ship.chute;
      at(15000, 450); const fast = openChute(), fastState = ship.chute;
      at(15000, 300); const ok = openChute(), okState = ship.chute;
      const warps = [];
      for (let i = 0; i < 20000 && ship.phase === 'flight'; i++) {
        if (i % 500 === 0) warps.push([Math.round(surfaceClearance().clearance), maxWarp()]);
        step(0.1);
      }
      return { rising, risingState, high, highState, fast, fastState, ok, okState, warps, phase: ship.phase, touch: ship.touch, reason: ship.reason };
    }""")
    assert r['rising'] == 'Laskuvarjo aukeaa vasta, kun alus putoaa.' and r['risingState'] == 'packed'
    assert r['high'] == 'Laskuvarjo aukeaa vasta alle 20 km korkeudessa.' and r['highState'] == 'packed'
    assert r['fast'].startswith('Laskuvarjo repesi') and r['fastState'] == 'torn'
    assert r['ok'] == 'Laskuvarjo auki.' and r['okState'] == 'open'
    assert r['phase'] == 'done', r
    assert r['touch']['body'] == 'earth' and r['touch']['speed'] <= 10, r
    assert all(w == 100 for h, w in r['warps'] if h > 600), r['warps']
    assert page.errors == []


def start_from_orbit(page, trip='kuu-kierto'):
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 1, asema: 1}))")
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    page.locator(f'.trip[data-trip="{trip}"]').click()
    page.locator('#start-orbit').click()
    page.evaluate('cancelAnimationFrame(frameId); frameId = 0')


def test_nose_holds_after_a_turn_and_point_buttons_aim_without_fuel(site, context):
    page = open_game(site, context)
    start_from_orbit(page)
    turn_button = page.locator('[data-hold="turn:1"]')
    turn_button.dispatch_event('pointerdown', {'pointerId': 7})
    page.evaluate('step(1)')
    turn_button.dispatch_event('pointerup', {'pointerId': 7})
    r = page.evaluate("""() => {
      const fuel = ship.fuel, a0 = ship.angle; step(10); const held = Math.abs(wrap(ship.angle - a0));
      document.querySelector('[data-point="pro"]').click(); step(3);
      const q = pointFrame(), pro = Math.abs(wrap(Math.atan2(q.vx, q.vy) - ship.angle)) * 180 / Math.PI;
      step(200);
      const q2 = pointFrame(), pro2 = Math.abs(wrap(Math.atan2(q2.vx, q2.vy) - ship.angle)) * 180 / Math.PI;
      document.querySelector('[data-point="up"]').click(); step(3);
      const up = Math.abs(wrap(Math.atan2(ship.x, ship.y) - ship.angle)) * 180 / Math.PI;
      return { held, pro, pro2, up, point: ship.point, fuelUsed: fuel - ship.fuel };
    }""")
    assert r['held'] < 1e-9, r
    assert r['pro'] < 2 and r['pro2'] < 2 and r['up'] < 2, r
    assert r['point'] == 'up' and r['fuelUsed'] == 0, r
    page.locator('[data-point="up"]').click()
    assert page.evaluate('ship.point') is None
    assert page.errors == []


def test_a_turn_tap_turns_as_far_at_any_warp(site, context):
    page = open_game(site, context)
    start_from_orbit(page)
    r = page.evaluate("""() => {
      const turned = rate => { warp = rate; held.turn = 1; held.turnFor = 0; ship.point = null;
        const a0 = ship.angle; for (let i = 0; i < 10; i++) steer(ship, 0.02 * rate);
        held.turn = 0; return Math.abs(wrap(ship.angle - a0)) * 180 / Math.PI; };
      return [turned(1), turned(5)];
    }""")
    assert abs(r[0] - 3) < 0.01 and abs(r[1] - r[0]) < 1e-9, r
    assert page.errors == []


def test_hints_do_not_call_an_unfinished_orbit_done(site, context):
    page = open_game(site, context)
    start_from_orbit(page)
    r = page.evaluate("""() => {
      const earth = guidance(Object.assign({}, ship, { trip: 'kiertorata', vx: ship.vx * 1.25 }))[1];
      const m = bodyAt(MOON, ship.t), v = Math.sqrt(MOON.mu / (MOON.radius + 1000));
      const moon = guidance(Object.assign({}, ship, { trip: 'kuu-kierto', x: m.x, y: m.y + MOON.radius + 1000,
        vx: m.vx + v * 0.9, vy: m.vy }))[1];
      return { earth, moon };
    }""")
    assert 'liian korkealla' in r['earth'], r
    assert r['moon'].startswith('Rata osuu Kuuhun'), r
    assert page.errors == []


def test_quadratic_throttle_slider(site, context):
    page = open_game(site, context)
    page.locator('.trip[data-trip="kiertorata"]').click()
    page.locator('#start-pad').click()
    page.locator('#throttle').fill('50')
    assert page.evaluate('ship.throttle') == pytest.approx(0.25)
    assert page.locator('#power').inner_text() == '25 %'
    page.locator('#cut').click()
    assert page.evaluate('ship.throttle') == 0
    assert page.errors == []


def test_time_warp_limits_and_same_flight_at_any_speed(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      cancelAnimationFrame(frameId); frameId = 0; paused = false;
      ship = freshFlight('kuu-kierto', 'pad'); const pad = maxWarp();
      ship.throttle = 1; const padBurn = maxWarp(); ship.throttle = 0;
      ship = freshFlight('kuu-kierto', 'orbit'); const low = maxWarp();
      ship.throttle = 0.1; const burn = maxWarp(); ship.throttle = 0;
      const start = JSON.parse(JSON.stringify(ship)), e0 = orbitAround(EARTH, ship).energy;
      warp = 1000; for (let i = 0; i < 1500 && ship.t < 3000; i++) advanceFlight(1 / 30);
      const fast = { x: ship.x, y: ship.y, t: ship.t, e: orbitAround(EARTH, ship).energy };
      ship = JSON.parse(JSON.stringify(start)); warp = 1;
      while (ship.t < fast.t - 1e-9) step(Math.min(1 / 30, fast.t - ship.t));
      const slow = { x: ship.x, y: ship.y, t: ship.t, e: orbitAround(EARTH, ship).energy };
      return { pad, padBurn, low, burn, fast, slow, e0, gap: Math.hypot(fast.x - slow.x, fast.y - slow.y) };
    }""")
    assert r['pad'] == 5 and r['padBurn'] == 1, r
    assert r['low'] == 100 and r['burn'] == 5, r
    assert r['fast']['t'] > 1500, r
    assert r['gap'] < 1000, r
    assert abs(r['fast']['e'] / r['slow']['e'] - 1) < 1e-5, r
    assert abs(r['fast']['e'] / r['e0'] - 1) < 1e-3, r
    assert page.errors == []


def test_warp_button_steps_through_allowed_rates(site, context):
    page = open_game(site, context)
    start_from_orbit(page)
    page.evaluate("ship.x *= 3; ship.y *= 3; ship.vx /= Math.sqrt(3); ship.vy /= Math.sqrt(3); updateUi()")
    seen = []
    for _ in range(7):
        page.locator('#warp').click()
        seen.append(page.locator('#warp').inner_text())
    assert seen == ['Aika ×2', 'Aika ×5', 'Aika ×10', 'Aika ×100', 'Aika ×1000', 'Aika ×1', 'Aika ×2']
    page.locator('#throttle').fill('20')
    assert page.locator('#warp').inner_text() == 'Aika ×2'
    page.locator('#warp').click()
    page.locator('#warp').click()
    assert page.locator('#warp').inner_text() == 'Aika ×1'
    assert page.errors == []


def test_trips_unlock_in_order_and_old_saves_are_left_alone(site, context):
    page = open_game(site, context)
    page.evaluate("""() => { localStorage.setItem('ai-pelit:raketti:lento', 'old flight');
      localStorage.setItem('ai-pelit:raketti:saavutukset', 'old marks'); }""")
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    assert page.locator('.trip:not([disabled])').count() == 1
    assert page.locator('#star-total').inner_text() == 'Tähtiä 0 / 18'
    assert page.locator('#resume').is_hidden()
    page.locator('.trip[data-trip="kiertorata"]').click()
    assert page.locator('#start-orbit').is_hidden()
    page.evaluate("""() => { stars = {}; ship = freshFlight('kiertorata', 'orbit'); paused = false;
      step(0.1); mainMenu(); }""")
    assert page.evaluate('ship.phase') == 'done'
    assert page.locator('.trip:not([disabled])').count() == 2
    page.locator('.trip[data-trip="asema"]').click()
    assert page.locator('#start-orbit').is_visible()
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 9, asema: 'x'}))")
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    assert page.locator('.trip:not([disabled])').count() == 1
    assert page.evaluate("[localStorage.getItem('ai-pelit:raketti:lento'), "
                         "localStorage.getItem('ai-pelit:raketti:saavutukset')]") == ['old flight', 'old marks']
    assert page.errors == []


def test_flight_resumes_after_reload_and_turning(site, context):
    page = open_game(site, context)
    page.locator('.trip[data-trip="kiertorata"]').click()
    page.locator('#start-pad').click()
    page.evaluate("cancelAnimationFrame(frameId); frameId = 0; ship.throttle = 1; step(20); ship.throttle = 0; saveFlight()")
    before = page.evaluate('[ship.t, ship.y]')
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    assert page.locator('#resume').inner_text() == 'Jatka: Kiertoradalle'
    page.locator('#resume').click()
    assert page.locator('#pause-panel').is_visible()
    turn(page, {'width': 740, 'height': 360})
    page.locator('#continue').click()
    assert page.evaluate('[ship.t, ship.y]') == pytest.approx(before, rel=1e-3)
    assert page.evaluate('paused') is False
    page.locator('#pause').click()
    page.locator('#to-menu').click()
    page.locator('.trip[data-trip="kiertorata"]').click()
    page.locator('#start-pad').click()
    assert page.locator('#replace-panel').is_visible()
    page.locator('#replace-yes').click()
    assert page.evaluate('ship.t') < 1
    assert page.errors == []


@pytest.mark.parametrize('mutation', [
    "s.x = null", "s.trip = 'mars'", "s.point = 'side'", "s.fuel = 1e9", "s.visited = ['sun']",
])
def test_corrupt_save_is_not_resumed(site, context, mutation):
    page = open_game(site, context)
    page.evaluate(f"""() => {{ const s = freshFlight('kiertorata', 'pad'); {mutation};
      localStorage.setItem('ai-pelit:raketti:matka', JSON.stringify(s)); }}""")
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    assert page.locator('#resume').is_hidden()
    assert page.errors == []


FITS = """sel => { const r = document.querySelector(sel).getBoundingClientRect();
  return r.width > 0 && r.top >= -1 && r.left >= -1 && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1; }"""


@pytest.mark.parametrize('width,height', [(360, 640), (360, 740), (740, 360)])
def test_menus_help_and_controls_fit_the_screen(site, browser, width, height):
    context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', "
                  "JSON.stringify({kiertorata: 3, asema: 2, 'kuu-kierto': 1, kuuhun: 1, kotiin: 1}))")
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    for sel in ['#menu', '.trip[data-trip="kivi"]']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    page.locator('.trip[data-trip="kotiin"]').click()
    for sel in ['#trip-panel', '#start-pad', '#start-orbit', '#trip-back']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    page.locator('#trip-back').click()
    page.locator('#menu-help').click()
    for _ in range(6):
        assert page.evaluate(FITS, '#help-panel'), (page.locator('#help-title').inner_text(), width, height)
        if page.locator('#help-next').is_enabled():
            page.locator('#help-next').click()
    page.locator('#help-close').click()
    page.locator('.trip[data-trip="asema"]').click()
    page.locator('#start-pad').click()
    controls = ['#throttle', '#cut', '#chute', '[data-point="pro"]', '[data-point="retro"]', '[data-point="up"]',
                '[data-hold="turn:-1"]', '[data-hold="turn:1"]', '[data-hold="side:-1"]', '[data-hold="forward:1"]',
                '[data-hold="forward:-1"]', '[data-hold="side:1"]', '#warp', '#help', '#pause', '#c', '#guide',
                '[data-view="map"]', '#view-dock']
    for sel in controls:
        assert page.evaluate(FITS, sel), (sel, width, height)
    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight + 1')
    assert page.errors == []
    context.close()
