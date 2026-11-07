// Yöajo v13 (#440 "Autopeliin lisää"): things that happen on the road. Roadworks with a temporary
// light, fog lying in the dips, a broken-down car behind its warning triangle, an ambulance coming
// up from behind, a wide load coming the other way, a snowplough throwing snow, and black ice.
// At most three of these kinds on a leg (ROAD_EVENTS). Everything is top-level, as in game.js.

// The kinds on each leg, legs 1–8. Fog only on dry and rainy legs, the plough and black ice on snow.
const ROAD_EVENTS = [
  ['tietyo'],
  ['tietyo', 'rikki', 'sumu'],
  ['ambulanssi', 'rikki', 'sumu'],
  ['ambulanssi', 'erikois', 'sumu'],
  ['aura', 'jaa', 'ambulanssi'],
  ['aura', 'jaa', 'rikki'],
  ['aura', 'jaa', 'erikois'],
  ['aura', 'jaa', 'ambulanssi'],
];

// Roadworks: the player's lane is shut for WORK_LEN metres. A light at the stop line, TAPER metres
// before the shut lane begins, lets one way through at a time: WORK_GREEN s green for the player in
// every WORK_CYCLE s. The oncoming traffic, waiting at its own line FAR_STOP metres past the
// works, may go in for ONCOMING_GO s soon after the player's red begins, never while anyone of the
// player's way is in, and has the rest of the red to come through. 50 through the works.
const WORK_LEN = 80, TAPER = 34, FAR_STOP = 40, WORK_CYCLE = 26, WORK_GREEN = 6, ONCOMING_GO = 2.5, WORK_LIMIT = 50, CONES_LAT = 0.3;
// The broken-down car: half in the player's lane; its triangle TRIANGLE metres before it.
const BROKEN_LAT = 3.2, TRIANGLE = 50;
// The ambulance: catches up, and waits behind for the player to move right (to YIELD_LAT or more)
// for at most BLOCK_TIME s before it costs points.
const YIELD_LAT = 2.6, BLOCK_TIME = 5;
// The wide load: 40 km/h, half in the player's lane; meet it at YIELD_LAT or more and under
// LOAD_SLOW km/h.
const LOAD_V = 40 / KMH, LOAD_LAT = -0.9, LOAD_WID = 4.6, LOAD_SLOW = 50;
// The snowplough: 40 km/h, its snow cloud CLOUD_BACK metres behind it.
const PLOUGH_V = 40 / KMH, CLOUD_BACK = 50;
// Black ice: ICE_LEN metres where grip halves, a sign ICE_SIGN metres before.
const ICE_LEN = 50, ICE_SIGN = 150, ICE_GRIP = 0.5;
// Fog in the dips: inside it high beams reach FOG_HIGH metres, low beams at most FOG_LOW.
const FOG_HALF = 70, FOG_EDGE = 25, FOG_HIGH = 30, FOG_LOW = 45;

// ---- Placing them on the leg (from newLeg, after the police) ----
function roadLeg(evs) {
  const r = rng(leg.seed * 19 + 7), kinds = ROAD_EVENTS[level - 1] || [];
  const near = (a, b, x0, x1) => b > x0 && a < x1;
  // A stretch with nothing else on it: no rest area, police check or other road event; a fixed
  // one also no sign but a speed limit's (none inside [quiet0, quiet1]), potholes, junction,
  // camera or moose.
  function clear(a, b, fixed, quiet0, quiet1) {
    const base = !road.bays.some(x => near(a, b, x.s0 - BAY_IN - 40, x.s1 + BAY_IN + 40)) &&
      !road.checks.some(c => near(a, b, c.s - 320, c.s + 60)) &&
      !road.taken.some(([x0, x1]) => near(a, b, x0, x1));
    if (!base || !fixed) return base;
    return !road.signs.some(sg => sg.s >= a && sg.s <= b && (sg.kind !== 'raja' || (sg.s >= quiet0 && sg.s <= quiet1))) &&
      !road.bad.some(x => near(a, b, x.s0 - 40, x.s1 + 40)) &&
      !road.nopass.some(z => near(a, b, z.s0 - 20, z.s1 + 40)) &&
      !road.cams.some(c => near(a, b, c.s - 40, c.s + 40)) &&
      !evs.some(e => (e.kind === 'hirvi' || e.kind === 'poro') && near(a, b, e.s - 200, e.s + 80));
  }
  function place(before, after, fixed, quiet0 = 0, quiet1 = -1) {
    const hi = leg.len - 280 - after;
    for (let k = 0; k < 160; k++) {
      const s = Math.round(500 + r() * (hi - 500));
      if (s - before > 300 && clear(s - before, s + after, fixed, s + quiet0, s + quiet1)) { road.taken.push([s - before, s + after]); return s; }
    }
    return -1;
  }
  // Fixed places first, then the traffic that meets the player along a stretch.
  for (const kind of ['tietyo', 'rikki', 'erikois', 'aura', 'ambulanssi', 'jaa'].filter(k => kinds.includes(k))) {
    if (kind === 'tietyo') {
      const s = place(220, TAPER + WORK_LEN + FAR_STOP + 50, true, -130, TAPER + WORK_LEN + FAR_STOP + 30); if (s < 0) continue;
      const w = { stop: s, s0: s + TAPER, s1: s + TAPER + WORK_LEN, far: s + TAPER + WORK_LEN + FAR_STOP, off: r() * WORK_CYCLE, waited: false, judged: false, told: false };
      road.works.push(w);
      const after = limitAt(w.far + 20), lim = road.limits;
      lim.push({ s: s - 120, v: WORK_LIMIT }, { s: w.far + 20, v: after }); lim.sort((a, b) => a.s - b.s);
      road.signs.push({ s: s - 200, kind: 'tietyo' }, { s: s - 120, kind: 'raja', v: WORK_LIMIT }, { s: w.far + 20, kind: 'raja', v: after });
      evs.push({ s: s - 600, kind: 'tietyo', w });
    } else if (kind === 'rikki') {
      const s = place(TRIANGLE + 90, 40, true); if (s < 0) continue;
      const b = { s, judged: false };
      road.broken.push(b);
      evs.push({ s: s - 500, kind: 'rikki', b });
    } else if (kind === 'jaa') {
      for (let k = 0, got = 0; k < 4 && got < 2; k++) {
        const s = place(ICE_SIGN + 20, ICE_LEN + 20, false); if (s < 0) continue;
        road.ice.push({ s0: s, s1: s + ICE_LEN, told: false }); got++;
        road.signs.push({ s: s - ICE_SIGN, kind: 'liukas', ice: true });
      }
    } else if (kind === 'erikois') {
      // Released 620 m ahead, it meets the player about 450 m on.
      const s = place(0, 550); if (s >= 0) evs.push({ s, kind: 'erikois', told: false });
    } else if (kind === 'ambulanssi') {
      const s = place(0, 450); if (s >= 0) evs.push({ s, kind: 'ambulanssi' });
    } else if (kind === 'aura') {
      const s = place(0, 600); if (s >= 0) evs.push({ s, kind: 'aura' });
    }
  }
  road.ice.sort((a, b) => a.s0 - b.s0);
  // Fog in the deepest dips, at most two, 600 m apart.
  if (kinds.includes('sumu')) {
    const dips = [];
    for (let s = 400; s < leg.len - 400; s += 10) { const h = heightAt(s); if (h < heightAt(s - 60) - 0.4 && h < heightAt(s + 60) - 0.4 && h <= heightAt(s - 10) && h <= heightAt(s + 10)) dips.push([h, s]); }
    dips.sort((a, b) => a[0] - b[0]);
    for (const [, s] of dips) if (road.fog.length < 2 && road.fog.every(f => Math.abs(f.s - s) > 600) && !road.taken.some(([a, b]) => s > a - 150 && s < b + 150) && !road.checks.some(c => Math.abs(c.s - s) < 300)) road.fog.push({ s, told: false });
  }
  // The racers, which overtake or come at the player in their lane, keep away from these.
  for (let i = evs.length - 1; i >= 0; i--) {
    const e = evs[i];
    if ((e.kind === 'takaa' || e.kind === 'ohittaja') && road.taken.some(([a, b]) => e.s > a - 500 && e.s < b + 100)) evs.splice(i, 1);
  }
}

// ---- On the road (from release in game.js) ----
function roadRelease(e) {
  if (e.kind === 'tietyo') {
    // A car already waiting for its green at the far end.
    return add('vastaan', { s: e.w.far, lat: -LANE, v: -0.001, colour: Math.floor(e.r * 5), habit: e.r * 6 - 3, high: false });
  }
  if (e.kind === 'rikki') {
    // The car, half on the shoulder with its hazard lights on, and its driver beside it with a reflector.
    add('kavelija', { s: e.b.s + 3, lat: 4.9, v: 0, reflector: true, still: true, passed: true });
    return add('auto', { s: e.b.s, lat: BROKEN_LAT, v: 0, colour: Math.floor(e.r * 5), broken: true, parked: true, passed: true });
  }
  if (e.kind === 'ambulanssi') return add('ambulanssi', { s: P.s - 140, lat: LANE, v: Math.max(P.v + 12, 28), plan: 'catch', wait: 0, passed: true, blue: true });
  if (e.kind === 'erikois') {
    // An escort car with yellow lights first, the load 60 m behind it, another escort after.
    add('vastaan', { s: P.s + 620, lat: -LANE, v: -LOAD_V, escort: true, colour: 2 });
    add('vastaan', { s: P.s + 760, lat: -LANE, v: -LOAD_V, escort: true, colour: 2 });
    return add('erikois', { s: P.s + 690, lat: LOAD_LAT, v: -LOAD_V, wid: LOAD_WID, told: false });
  }
  if (e.kind === 'aura') return add('aura', { s: P.s + 260, lat: 2.0, v: PLOUGH_V, beacon: e.r * TAU });
}

// ---- The roadworks' light ----
// Green for the player: the first WORK_GREEN s of each cycle.
function worksGreen(w) { return ((T + w.off) % WORK_CYCLE) < WORK_GREEN; }
// The oncoming traffic may go in: well into the player's red, and nobody of the player's way in it.
function worksOpen(w) {
  const ph = (T + w.off) % WORK_CYCLE;
  return ph > WORK_GREEN + 1 && ph < WORK_GREEN + 1 + ONCOMING_GO && !(P.s > w.stop - 2 && P.s < w.far) &&
    !things.some(t => t.v > 0 && vehicle(t) && !t.parked && t.s > w.stop - 2 && t.s < w.far);
}
// Where in the works the cones are, across the road: from the edge line down to the centre over
// the taper.
function conesAt(w, s) { return s < w.s0 ? CONES_LAT + (EDGE - 0.2 - CONES_LAT) * clamp((w.s0 - s) / (TAPER - 4), 0, 1) : CONES_LAT; }
function worksAt(s) { return road.works.find(w => s > w.stop - 6 && s < w.far + 10) || null; }
function iceAt(s) { return road.ice.some(x => s >= x.s0 && s <= x.s1); }
function gripAt(s) { return iceAt(s) ? ICE_GRIP : 1; }
// How thick the fog is here, 0..1.
function fogAt(s) {
  let f = 0;
  for (const z of road.fog) f = Math.max(f, clamp((FOG_HALF + FOG_EDGE - Math.abs(s - z.s)) / FOG_EDGE, 0, 1));
  return f;
}
// The headlights' reach in fog (from reachOf in game.js).
function fogReach(high, reach) { const f = fogAt(P.s); return f ? lerp(reach, high ? FOG_HIGH : Math.min(reach, FOG_LOW), f) : reach; }

// ---- The other road users around these (from move in game.js, before they move) ----
function roadMove(t, dt) {
  if (t.parked || t.kind === 'liittyja' || t.kind === 'takaa' || t.kind === 'ohittaja' || t.kind === 'partio' || t.kind === 'ambulanssi' || !vehicle(t)) return;
  if (t.v < 0) {
    // Oncoming: wait at the far end of roadworks for their turn; a wide load or an ambulance
    // coming: keep right.
    for (const w of road.works) {
      if (t.inWorks || t.s - w.far < -1 || t.s - w.far > 200) continue;
      // Queue behind the cars already waiting at the line, not on top of them.
      let line = w.far;
      for (const o of things) if (o !== t && o.v < 0 && vehicle(o) && !o.inWorks && o.s < t.s && o.s >= w.far - 1) line = Math.max(line, o.s + (o.len + t.len) / 2 + 2);
      const d = t.s - line;
      // Once its way is open within 30 m of the line it goes; otherwise it stops at the line.
      if (worksOpen(w)) { if (d < 30) t.inWorks = true; }
      else t.v = Math.min(-0.001, Math.max(t.v, -Math.sqrt(2 * 4 * Math.max(0, d))));
    }
    // Behind a wide load, at its speed.
    const ld = things.find(o => o.kind === 'erikois' && o !== t && o.s < t.s && t.s - o.s < 60);
    if (ld && t.v < ld.v) t.v = ld.v;
    const amb = things.find(o => o.kind === 'ambulanssi' && o.plan === 'pass' && Math.abs(o.s - t.s) < 120);
    if (t.home === undefined) t.home = t.lat;
    if (t.kind !== 'erikois') t.lat += ((amb ? -3.0 : t.home) - t.lat) * Math.min(1, dt * 1.5);
    return;
  }
  // The player's way: through roadworks in the left lane on its green, round a broken-down car,
  // onto the shoulder for a wide load, aside for an ambulance.
  // Back to its own line after: where it drove before (v12 left each car on its line).
  if (t.home === undefined) t.home = t.lat;
  let want = t.home;
  for (const w of road.works) {
    if (t.s > w.stop - 200 && t.s < w.stop - 1 && !t.green && !worksGreen(w)) {
      let line = w.stop - 3;
      for (const o of things) if (o !== t && o.v >= 0 && vehicle(o) && !o.green && !o.parked && o.s > t.s && o.s <= w.stop) line = Math.min(line, o.s - (o.len + t.len) / 2 - 2);
      t.v = Math.min(t.v, Math.sqrt(2 * 4 * Math.max(0, line - t.s)));
    }
    if (t.s >= w.stop - 1 && t.s < w.stop) t.green = true;
    if (t.s > w.stop - 4 && t.s < w.s1 + 6) want = -LANE;
  }
  // Round a broken-down car only with the other lane free (the player beside it, or a car
  // coming); otherwise wait behind it.
  const bk = road.broken.find(b => b.s - t.s < 40 && b.s - t.s > -8);
  if (bk) {
    const busy = t.lat > 1 && (Math.abs(P.s - t.s) < (P.len + t.len) / 2 + 6 && P.lat < 1
      || things.some(o => o.v < 0 && vehicle(o) && o.s > t.s - 10 && o.s - t.s < 150));
    if (busy && bk.s - t.s > (t.len + 4.4) / 2 + 2) t.v = Math.min(t.v, Math.sqrt(2 * 4 * Math.max(0, bk.s - (t.len + 4.4) / 2 - 4 - t.s)));
    else want = Math.min(want, 0.2);
  }
  const load = things.find(o => o.kind === 'erikois' && o.s > t.s - 10 && o.s - t.s < 160);
  if (load) { want = Math.max(want, 2.8); t.v = Math.min(t.v, 11); }
  if (things.some(o => o.kind === 'ambulanssi' && o.plan !== 'back' && o.s < t.s && t.s - o.s < 60)) want = Math.max(want, 3.0);
  t.lat += (want - t.lat) * Math.min(1, dt * 1.5);
}

// ---- The ambulance (from move in game.js) ----
function ambulance(t, dt) {
  const d = P.s - t.s, top = 120 / KMH;
  const yielded = P.lat >= YIELD_LAT;
  if (t.plan === 'catch') {
    t.v = Math.max(t.v, Math.min(top, P.v + 12));
    if (d < 40) { t.plan = 'behind'; say('Ambulanssi takana: väistä oikealle', false); if (typeof sirenSound === 'function') sirenSound(); }
  }
  if (t.plan === 'behind') {
    // Close behind, as close as is safe, until the player makes room.
    t.v = clamp(P.v + (d - 18) * 0.8, 0, top);
    t.wait += dt;
    t.sirenT = (t.sirenT || 0) - dt;
    if (t.sirenT <= 0) { t.sirenT = 2.4; if (typeof sirenSound === 'function') sirenSound(); }
    if (yielded) { t.plan = 'pass'; t.room = true; }
    else if (t.wait > BLOCK_TIME) {
      if (!t.blocked) { t.blocked = true; tally.tukit = (tally.tukit || 0) + 1; score(-50, 'Tukit ambulanssin'); }
      if (!things.some(o => o.v < 0 && vehicle(o) && o.s > t.s && o.s - t.s < 250)) t.plan = 'pass';
    }
  }
  if (t.plan === 'pass') {
    // By on the left: half over the centre line when the player made room, in the oncoming lane if not.
    t.v = Math.min(top, Math.max(P.v + 10, 25));
    t.lat += ((t.room ? -0.2 : -LANE) - t.lat) * Math.min(1, dt * 2);
    if (P.s > t.s - 2 && P.s - t.s < 30 && Math.abs(P.lat - t.lat) < (P.wid + t.wid) / 2 + 0.2) t.v = Math.min(t.v, P.v);
    if (t.s > P.s + 20) {
      t.plan = 'back';
      if (!t.blocked) { tally.ambulanssi = (tally.ambulanssi || 0) + 1; score(30, 'Päästit ambulanssin ohi'); }
    }
  }
  if (t.plan === 'back') { t.v = top; t.lat += (LANE - t.lat) * Math.min(1, dt * 1.5); }
  t.s += t.v * dt;
}

// ---- Every step of the drive (from drive in game.js) ----
function roadTick(dt) {
  // Roadworks: the light at the stop line, the cones, the waiting rewarded.
  for (const w of road.works) {
    const d = w.stop - P.s;
    if (!w.told && d < 260 && d > 0) { w.told = true; say('Tietyö: yksi kaista, odota vihreää', false); }
    if (!w.judged) {
      if (d > 0 && d < 40 && P.v < 1 && !worksGreen(w)) w.waited = true;
      if (d <= 0) {
        w.judged = true;
        if (!worksGreen(w)) {
          tally.hurjastelu++; tally.punaiset = (tally.punaiset || 0) + 1; score(-50, 'Punaisia päin');
        } else if (w.waited) { tally.tietyo = (tally.tietyo || 0) + 1; score(20, 'Odotit vihreää'); }
      }
    }
    // Into the shut lane: the cones (unless the police are pulling the car over).
    if (!pstop && P.s > w.s0 - TAPER + 6 && P.s < w.s1 && P.lat + P.wid / 2 > conesAt(w, P.s) + 0.15) return crash('Ajoit tietyömaalle.');
  }
  // The broken-down car: round it with room.
  for (const b of road.broken) {
    if (b.judged || P.s < b.s || P.s - b.s > 20) continue;
    b.judged = true;
    const room = BROKEN_LAT - 0.9 - (P.lat + P.wid / 2);
    if (room < 0.8 && P.v > 40 / KMH) { tally.lahelta++; score(-40, 'Liian läheltä rikkinäistä autoa'); }
    else if (room >= 1) score(20, 'Väljä ohitus');
  }
  // The wide load: on the shoulder and slow as it goes by.
  for (const t of things) {
    if (t.kind !== 'erikois') continue;
    const d = t.s - P.s;
    if (!t.loadTold && d < 400) { t.loadTold = true; say('Erikoiskuljetus vastaan: oikeaan reunaan ja alle 50', false); }
    if (!t.loadDone && Math.abs(d) < (t.len + P.len) / 2) {
      t.loadDone = true;
      if (P.v * KMH > LOAD_SLOW) return crash('Vaaratilanne: ohitit erikoiskuljetuksen liian kovaa.');
      tally.erikois = (tally.erikois || 0) + 1; score(20, 'Väistit erikoiskuljetusta');
    }
  }
  // The snowplough's cloud of snow, thick close behind it.
  for (const t of things) {
    if (t.kind !== 'aura') continue;
    const d = t.s - t.len / 2 - P.s;
    if (d > 0 && d < CLOUD_BACK && Math.abs(P.lat - t.lat) < 3.2) whiteout = Math.max(whiteout, CLOUD * (1 - d / CLOUD_BACK));
  }
  for (const x of road.ice) if (!x.told && P.s > x.s0 - 20 && P.s < x.s1) { x.told = true; say('Musta jää: ei jarrua eikä äkkiohjausta', false); }
  const fog = fogAt(P.s);
  for (const z of road.fog) if (!z.told && fog > 0.2 && Math.abs(P.s - z.s) < FOG_HALF + FOG_EDGE) { z.told = true; say('Sumua: lähivaloilla näkee paremmin', false); }
  // High beams light the fog itself.
  if (fog > 0 && P.high) whiteout = Math.max(whiteout, 0.4 * fog);
}
// What to tell the driver at the bottom of the screen now (ui.js), or ''.
function roadHint() {
  const amb = things.find(t => t.kind === 'ambulanssi' && (t.plan === 'behind' || t.plan === 'catch') && P.s - t.s < 120);
  if (amb) return '🚑 Ambulanssi takana: oikealle reunaan';
  const load = things.find(t => t.kind === 'erikois' && t.s - P.s < 400 && t.s > P.s);
  if (load) return '⚠ Erikoiskuljetus: oikeaan reunaan, alle 50 km/h';
  const w = road.works.find(w => w.stop - P.s < 300 && P.s < w.s1);
  if (w) {
    if (P.s > w.stop) return 'Tietyö: aja vasenta kaistaa';
    const d = Math.round((w.stop - P.s) / 10) * 10;
    return worksGreen(w) ? `Tietyö ${d} m: vihreä, aja vasenta kaistaa` : `Tietyö ${d} m: punainen, pysähdy valoihin`;
  }
  return '';
}
