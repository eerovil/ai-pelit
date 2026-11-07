// Yöajo v12 (#440 "Autopeliin lisää"): the police. Marked police cars from leg 2, parked by a side
// road with a radar, coming the other way, or driving ahead of the player, and from leg 3 a police
// check on the road where the driver stops to blow. Everything is top-level, as in game.js.
//
// What the police do (Eero's choices): seen driving 11–19 km/h over the limit, or dazzled, they
// stop the car for a moment and fine it 150 points, and the drive goes on; seen driving 20 or more
// over, overtaking unsafely or crossing the solid line, they end the leg. Out of their sight the
// old rules stand (minus points, cameras).

// Police cars per leg, legs 1–8; a police check on every leg from the third.
const POLICE_CARS = [0, 1, 1, 2, 2, 2, 3, 3], CHECK_FROM = 3;
// How far a police car sees the player, metres: ahead of it and behind it (its mirror), less in
// rain and snow (the leg's reach), and never over a crest or round a wooded bend. A parked one
// watches the traffic coming at it with its radar, and a little past.
const SEE_AHEAD = 250, SEE_BEHIND = 120, RADAR = 200, RADAR_PAST = 60;
// Over the limit by more than FINE_OVER (11–19) for a second: a fine. RECKLESS_OVER (20, game.js)
// or more for half a second: the leg ends.
const FINE_OVER = 10, POLICE_FINE = 150, STOP_TIME = 3, STOP_LAT = 4.1;
// The police check, CHECK_IN metres into a pothole stretch (under its 50 limit): stop within the
// window beside the officer, in the right half of the road (their side; under 5 km/h for
// BLOW_STILL s), blow for BLOW_TIME s.
const CHECK_IN = 200, BLOW_STILL = 1.5, BLOW_TIME = 2;
const OFFICER_LAT = 3.3, CHECK_CAR_LAT = 7.2;

let pstop = null;      // the stop for a fine in progress: { t, why, cop, car }

// ---- Placing them on the leg (from newLeg, before the events are sorted) ----
// Their own random numbers, so everything v11 placed stays where it was.
function policeLeg(evs) {
  pstop = null;
  if (P) P.seen = false;
  const r = rng(leg.seed * 17 + 3), n = POLICE_CARS[level - 1] || 0, end = leg.len - 320;
  // Kinds in turn: a parked radar at a side road first (the easiest to see coming), then one
  // coming the other way, then one driving ahead.
  for (let k = 0; k < n; k++) {
    const kind = ['parkki', 'vastaan', 'edella'][k % 3];
    if (kind === 'parkki') {
      // At a side road's mouth, a little up it, facing the main road. The side with no car
      // waiting to pull out, when there is one.
      const J = road.junctions[Math.floor(r() * road.junctions.length)];
      if (!J) continue;
      const waiting = evs.find(e => e.kind === 'liittyja' && e.j === J);
      const side = J.both && waiting ? -waiting.side : J.side;
      evs.push({ s: J.s - 600, kind: 'poliisi', how: 'parkki', at: J.s + 2, side: waiting && waiting.side === side ? side * 1.6 : side, r: r() });
    } else if (kind === 'vastaan') evs.push({ s: 400 + r() * (end - 800), kind: 'poliisi', how: 'vastaan', r: r() });
    else evs.push({ s: 600 + r() * (end - 1100), kind: 'poliisi', how: 'edella', r: r() });
  }
  if (level >= CHECK_FROM) placeCheck(evs, r);
}
// The check stands on a pothole stretch (v7), which already has its 50 limit from 40 m in to its
// end: the officer CHECK_IN metres into it, their car just past them on a widened shoulder, a
// POLIISI sign where the 50 starts. Kept clear of cameras, junctions, signs and moose there.
function placeCheck(evs, r) {
  const near = (a, b, x) => x >= a && x <= b;
  const spots = road.bad.map(x => x.s0 + CHECK_IN).filter(s => s > 600 && s < leg.len - 400 &&
    !road.cams.some(c => near(s - 260, s + 60, c.s)) &&
    !road.junctions.some(J => near(s - 160, s + 60, J.s)) &&
    !road.signs.some(sg => sg.kind !== 'raja' && sg.kind !== 'kuoppa' && near(s - 160, s + 40, sg.s)) &&
    !evs.some(e => (e.kind === 'hirvi' || e.kind === 'poro' || e.kind === 'kavelija') && near(s - 260, s + 40, e.s)));
  if (!spots.length) return null;
  const s = spots[Math.floor(r() * spots.length)], c = { s, state: 'wait', t: 0, live: false, told: false };
  road.checks.push(c);
  road.pads.push({ s0: s - 6, s1: s + 16 });
  road.signs.push({ s: s - CHECK_IN + 50, kind: 'poliisi' });
  evs.push({ s: s - 600, kind: 'puhallus', check: c });
  return c;
}

// ---- On the road (from release in game.js) ----
function policeRelease(e) {
  if (e.kind === 'puhallus') {
    // The check: its police car on the pad with the blue lights going, the officer at the edge
    // line with a red baton light.
    const c = e.check; c.live = true;
    add('auto', { s: c.s + 6, lat: CHECK_CAR_LAT, v: 0, police: true, parked: true, blue: true, passed: true, colour: 0 });
    add('konstaapeli', { s: c.s, lat: OFFICER_LAT, v: 0, passed: true, beacon: 0, yaw: Math.PI });
    return c;
  }
  if (e.how === 'parkki') return add('auto', { s: e.at, lat: e.side * 13, v: 0, police: true, watch: true, parked: true, passed: true, yaw: Math.sign(e.side) * Math.PI / 2 });
  // Moving ones keep a little under the limit, as police cars do.
  if (e.how === 'vastaan') return cruiseFrom(add('vastaan', { s: P.s + 620, lat: -LANE, police: true, watch: true, high: true, habit: -2 - e.r * 4 }));
  return cruiseFrom(add('auto', { s: P.s + 260, police: true, watch: true, habit: -5 - e.r * 4 }));
}

// ---- Whether a police car sees the player ----
function policeSees(t) {
  const reach = WEATHER[leg.weather].reach, d = P.s - t.s;
  if (t.parked) { if (d < -RADAR * reach || d > RADAR_PAST) return false; }
  else {
    const front = t.v < 0 ? -d : d;   // how far the player is in front of the police car
    if (front >= 0 ? front > SEE_AHEAD * reach : -front > SEE_BEHIND * reach) return false;
  }
  return clearView(t.s, P.s);
}
// Nothing between two places on the road: no crest above the line between eyes 1.3 m up, and no
// bend taking the road more than 14 m off the straight line between them (the forest hides it).
function clearView(a, b) {
  if (Math.abs(b - a) < 15) return true;
  const ha = heightAt(a) + 1.3, hb = heightAt(b) + 1.3, pa = worldAt(a, 0), pb = worldAt(b, 0);
  const dx = pb[0] - pa[0], dz = pb[2] - pa[2], L2 = dx * dx + dz * dz || 1;
  for (let k = 1; k < 20; k++) {
    const u = k / 20, s = a + (b - a) * u;
    if (heightAt(s) + 0.2 > ha + (hb - ha) * u) return false;
    const p = worldAt(s, 0), w = ((p[0] - pa[0]) * dx + (p[2] - pa[2]) * dz) / L2;
    const ox = pa[0] + dx * w - p[0], oz = pa[2] + dz * w - p[2];
    if (ox * ox + oz * oz > 14 * 14) return false;
  }
  return true;
}
function watcher() { return things.find(t => t.watch && policeSees(t)) || null; }

// ---- Every step of the drive (from drive in game.js) ----
function police(dt) {
  if (pstop) return;
  const cop = watcher();
  P.seen = !!cop;
  const lim = limitAt(P.s), kmh = Math.round(P.v * KMH), over = kmh - lim;
  if (!cop || over <= FINE_OVER) { P.copT = 0; return; }
  P.copT = (P.copT || 0) + dt;
  if (over >= RECKLESS_OVER && P.copT > 0.5) return caught(`Poliisi pysäytti: ${kmh} km/h, rajoitus ${lim}.`, cop);
  if (over < RECKLESS_OVER && P.copT > 1 && !cop.fined) fine(cop, `ylinopeus ${over} km/h`);
}
// The police check: slow down, stop beside the officer, blow. Driving past ends the leg.
function policeCheck(dt) {
  for (const c of road.checks) {
    if (!c.live || c.state === 'done') continue;
    const d = c.s - P.s;
    if (!c.told && d < 300) { c.told = true; say('Puhalluskoe: pysähdy poliisin kohdalle', false); }
    if (c.state === 'wait') {
      if (d < -6) return caught('Poliisi pysäytti: ajoit puhalluskokeen ohi.', null);
      if (d <= 10 && d >= -3 && P.lat > 0 && P.v * KMH < 5) { c.t += dt; if (c.t >= BLOW_STILL) { c.state = 'blow'; c.t = 0; say('Puhalla…', true); } }
      else c.t = 0;
    } else if (c.state === 'blow') {
      // Held still while blowing.
      input.gas = 0; input.brake = 1; c.t += dt;
      if (c.t >= BLOW_TIME) { c.state = 'done'; tally.puhallus = (tally.puhallus || 0) + 1; input.brake = 0; score(20, '0,00 ‰ – hyvää matkaa!'); }
    }
  }
}
// Whether a police car sees the player now, for the rules that end the leg (unsafe overtaking,
// the solid line): from unsafeOvertake in game.js.
function policeSaw(why) { const cop = watcher(); if (cop) caught(why, cop); return !!cop; }
function policeDazzled(t) { if (t.watch) fine(t, 'häikäisit poliisiautoa'); }

// A fine: blue lights behind, the car pulls over onto the shoulder and stops, and STOP_TIME s later
// the fine is written and the drive goes on.
function fine(cop, why) {
  if (pstop || cop.fined || mode !== 'drive') return;
  cop.fined = true;
  const car = add('partio', { s: P.s - 70, lat: P.lat, v: P.v + 3, police: true, blue: true, passed: true });
  pstop = { t: 0, why, cop, car };
  say('Siniset vilkut: pysähdy tien sivuun', false);
  if (typeof sirenSound === 'function') sirenSound();
}
// While stopped for a fine the police drive: off the gas, onto the shoulder, the brake.
function policeHold(dt) {
  input.gas = 0; input.left = input.right = false;
  if (P.v > 0.3) { input.brake = 0.8; input.steer = clamp((STOP_LAT - P.lat) * 0.5, -0.4, 0.4); return; }
  input.brake = 1; input.steer = 0; P.vl = 0;
  pstop.t += dt;
  if (pstop.t >= STOP_TIME) {
    tally.sakot++; tally.poliisi = (tally.poliisi || 0) + 1;
    score(-POLICE_FINE, `Poliisi: ${pstop.why}, sakko`);
    pstop.car.done = true; pstop = null;
    input.brake = 0;
  }
}
// The police car that stops the player: up behind them, a car's length back.
function patrol(t, dt) {
  if (t.done || mode !== 'drive') { t.v = 0; return; }
  t.v = clamp(P.v + (P.s - 12 - t.s) * 2, 0, P.v + 12);
  t.lat += (P.lat - t.lat) * Math.min(1, dt * 2);
  if (t.s + t.v * dt > P.s - 7) t.v = Math.max(0, (P.s - 7 - t.s) / dt);
}
// Caught: the blue lights come on, a police car pulls in behind, and the leg ends.
function caught(why, cop) {
  if (mode !== 'drive') return true;
  if (cop) cop.blue = true;
  add('partio', { s: P.s - 14, lat: P.lat, v: 0, police: true, blue: true, passed: true, done: true });
  tally.poliisi = (tally.poliisi || 0) + 1;
  return crash(why);
}
// Blue lights on the screen's edges: while stopped, and when caught.
function blueLights() { return (mode === 'drive' && !!pstop) || (mode === 'crash' && crashWhy.startsWith('Poliisi')); }
