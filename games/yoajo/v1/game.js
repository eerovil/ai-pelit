// Yöajo: the rules of the drive in plain numbers (#181). The road, the traffic, the lights and the
// points live here; view.js draws them in 3D and ui.js draws the screens and reads the fingers.
// Everything is top-level, so a test can set up a moment and run step(dt) frame by frame.
//
// Road space: `s` is metres along the road from the leg's start, `lat` metres across it, to the
// right positive. Finland drives on the right: the player's lane is centred at +1.75, the
// oncoming lane at -1.75, the edge lines at ±3.5, the gravel shoulder to ±4.6 and the ditch from
// ±5.6. Speeds are metres a second, shown as km/h.

const TAU = Math.PI * 2;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const KMH = 3.6;
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const LANE = 1.75, EDGE = 3.5, SHOULDER = 4.6, DITCH = 5.6;
// How far the headlights light the road, metres: low beams, high beams. Snow and rain take some.
const LOW = 42, HIGH = 135;

// ---- The trip: Valtatie 4 north, one leg a level ----
// len in metres of game road (the real legs are longer; a leg is a few minutes' drive).
// Each number is how many of that thing the leg has; weather 'kuiva', 'sade', 'lumi' or 'pyry'.
// tired: how fast the driver gets sleepy (0 = not at all); a leg with it has a rest area.
const LEGS = [
  { from: 'Helsinki', to: 'Järvenpää', len: 2600, weather: 'kuiva', limit: 100, oncoming: 9, cars: 2, tractors: 2, walkers: 1, trucks: 0, cameras: 0, moose: 0, racers: 0, bad: 0, tired: 0, seed: 11 },
  { from: 'Järvenpää', to: 'Lahti', len: 3000, weather: 'sade', limit: 100, oncoming: 11, cars: 2, tractors: 1, walkers: 3, trucks: 2, cameras: 1, moose: 0, racers: 0, bad: 0, tired: 0, seed: 22 },
  { from: 'Lahti', to: 'Heinola', len: 3200, weather: 'sade', limit: 80, oncoming: 11, cars: 2, tractors: 1, walkers: 2, trucks: 2, cameras: 2, moose: 0, racers: 1, bad: 1, tired: 0.6, seed: 33 },
  { from: 'Heinola', to: 'Jyväskylä', len: 3400, weather: 'kuiva', limit: 100, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 3, cameras: 1, moose: 2, racers: 1, bad: 1, tired: 0.8, seed: 44 },
  { from: 'Jyväskylä', to: 'Äänekoski', len: 3400, weather: 'lumi', limit: 80, oncoming: 11, cars: 1, tractors: 2, walkers: 2, trucks: 2, cameras: 1, moose: 2, racers: 1, bad: 1, tired: 0.8, seed: 55 },
  { from: 'Äänekoski', to: 'Pihtipudas', len: 3600, weather: 'lumi', limit: 80, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 3, cameras: 2, moose: 3, racers: 2, bad: 2, tired: 1, seed: 66 },
  { from: 'Pihtipudas', to: 'Oulu', len: 3800, weather: 'pyry', limit: 80, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 4, cameras: 2, moose: 3, racers: 2, bad: 2, tired: 1, seed: 77 },
  { from: 'Oulu', to: 'Rovaniemi', len: 4000, weather: 'pyry', limit: 80, oncoming: 13, cars: 2, tractors: 1, walkers: 2, trucks: 4, cameras: 2, moose: 2, reindeer: 3, racers: 2, bad: 2, tired: 1.2, seed: 88 },
];
const WEATHER = {
  kuiva: { grip: 1, reach: 1 },
  sade: { grip: 0.85, reach: 0.85 },
  lumi: { grip: 0.62, reach: 0.75 },
  pyry: { grip: 0.55, reach: 0.6 },
};

// ---- Saves (ai-pelit:yoajo:<name>, shared by every version) ----
const KEY = 'ai-pelit:yoajo:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
let maxLeg = clamp(Math.floor(load('taso', 1)) || 1, 1, LEGS.length);   // the furthest leg open, 1-based
let stars = load('tahdet', {}) || {};                                    // leg -> best stars
let bests = load('pisteet', {}) || {};                                   // leg -> best points
let level = maxLeg;
let driven = clamp(Math.floor(load('ajettu', 0)) || 0, 0, LEGS.length); // legs driven to the end at least once

// ---- The road of a leg ----
const SEG = 2;                       // the road is sampled every 2 m
let road = null;                     // { len, n, X, Y, Z, TH, K, limits, signs, holes, bays }
function makeRoad(L) {
  const r = rng(L.seed), extra = 900, total = L.len + extra, n = Math.ceil(total / SEG) + 2;
  const K = new Float32Array(n), TH = new Float32Array(n), X = new Float32Array(n), Y = new Float32Array(n), Z = new Float32Array(n);
  // Curvature: straights and bends one after another, each bend eased in and out, turning back
  // towards where the road was heading so the road never loops.
  let i = Math.round(160 / SEG), th = 0;
  while (i < n) {
    const straight = r() < 0.4, len = Math.round((straight ? 80 + r() * 260 : 140 + r() * 260) / SEG);
    let k = 0;
    if (!straight) { const rad = 170 + r() * 450; k = (r() < 0.5 ? 1 : -1) / rad; if (Math.abs(th) > 0.5) k = -Math.sign(th) / rad; }
    for (let j = 0; j < len && i < n; j++, i++) { const e = Math.min(1, j / 20, (len - j) / 20); K[i] = k * e; }
    th += k * len * SEG * 0.8;
  }
  // Hills: a few long waves; a crest hides what comes over it.
  const hill = L.weather === 'kuiva' ? 6 : 4, w1 = 260 + r() * 200, w2 = 600 + r() * 300, p1 = r() * TAU, p2 = r() * TAU;
  let x = 0, z = 0; th = 0;
  for (let j = 0; j < n; j++) {
    const s = j * SEG;
    TH[j] = th; X[j] = x; Z[j] = z;
    Y[j] = hill * (0.55 * Math.sin(s / w1 * TAU + p1) + 0.45 * Math.sin(s / w2 * TAU + p2)) - hill * (0.55 * Math.sin(p1) + 0.45 * Math.sin(p2));
    th += K[j] * SEG; x += Math.sin(th) * SEG; z -= Math.cos(th) * SEG;
  }
  road = { len: L.len, total, n, X, Y, Z, TH, K, limits: [], signs: [], holes: [], bays: [], cams: [] };
  return road;
}
function idx(s) { const f = clamp(s / SEG, 0, road.n - 1.001), i = Math.floor(f); return [i, f - i]; }
const lerp = (a, b, t) => a + (b - a) * t;
function curveAt(s) { const [i, t] = idx(s); return lerp(road.K[i], road.K[i + 1], t); }
function headingAt(s) { const [i, t] = idx(s); return lerp(road.TH[i], road.TH[i + 1], t); }
function heightAt(s) { const [i, t] = idx(s); return lerp(road.Y[i], road.Y[i + 1], t); }
// A point on (or beside) the road in the 3D world: x right, y up, z towards the start.
function worldAt(s, lat, up) {
  const [i, t] = idx(s), th = lerp(road.TH[i], road.TH[i + 1], t);
  return [lerp(road.X[i], road.X[i + 1], t) + lat * Math.cos(th), lerp(road.Y[i], road.Y[i + 1], t) + (up || 0), lerp(road.Z[i], road.Z[i + 1], t) + lat * Math.sin(th)];
}
function limitAt(s) { let v = road.limits.length ? road.limits[0].v : 80; for (const l of road.limits) if (l.s <= s) v = l.v; return v; }

// ---- The leg: its road, signs and the things that happen on it ----
let leg = null;        // the LEGS entry being driven
let P = null;          // the player's car
let things = [];       // everything else on the road: vehicles, walkers, moose
let events = [];       // what has yet to happen, by place: { s, kind, ... }, sorted
let mode = 'menu';     // 'menu', 'drive', 'pause', 'crash', 'done'
let T = 0;             // seconds driven this leg
let points = 0, tally = null, msgs = [], crashWhy = '', result = null;
let flash = 0, whiteout = 0, shake = 0;

function newLeg(n) {
  level = clamp(n || level, 1, maxLeg);
  leg = LEGS[level - 1];
  makeRoad(leg);
  const r = rng(leg.seed * 7 + 1);
  // Speed limits: the leg's own, now and then 60 at a village or 100 on a good stretch, and 50
  // into the town at the end. A sign stands where each one starts.
  const lim = road.limits;
  lim.push({ s: 0, v: leg.limit });
  for (let s = 600 + r() * 400; s < leg.len - 700; s += 700 + r() * 600) {
    const v = r() < 0.5 ? 60 : leg.limit === 100 ? 80 : (leg.weather === 'kuiva' || leg.weather === 'sade') ? 100 : 60;
    lim.push({ s, v }); lim.push({ s: s + 300 + r() * 200, v: leg.limit });
  }
  lim.push({ s: leg.len - 260, v: 50 });
  for (const l of lim) if (l.s > 0) road.signs.push({ s: l.s, kind: 'raja', v: l.v });
  road.signs.push({ s: leg.len - 70, kind: 'kaupunki', text: leg.to });

  // Places for the rest, spread over the leg so that two never fall on the same stretch.
  const used = [];
  const free = (a, b) => used.every(([u0, u1]) => b < u0 || a > u1);
  function spot(span, from, to) {
    for (let k = 0; k < 60; k++) { const s = from + r() * (to - from - span); if (free(s - 40, s + span + 40)) { used.push([s, s + span]); return s; } }
    return -1;
  }
  const evs = [];
  const end = leg.len - 320;
  // A rest area with coffee (#181 "Kuskia väsyttää") about halfway, where the driver gets sleepy.
  if (leg.tired) { const s = spot(140, leg.len * 0.4, leg.len * 0.62); if (s > 0) { road.bays.push({ s0: s + 60, s1: s + 140 }); road.signs.push({ s, kind: 'levahdys' }); } }
  for (let k = 0; k < leg.bad; k++) {
    const s = spot(280, 400, end); if (s < 0) continue;
    road.signs.push({ s, kind: 'kuoppa' });
    for (let h = s + 110; h < s + 280; h += 7 + r() * 12) road.holes.push({ s: h, lat: (r() * 2 - 1) * 3, r: 0.45 + r() * 0.35 });
  }
  for (let k = 0; k < leg.cameras; k++) {
    const s = spot(360, 500, end); if (s < 0) continue;
    road.signs.push({ s, kind: 'kamera' }); road.cams.push({ s: s + 340, done: false });
  }
  for (let k = 0; k < (leg.moose || 0) + (leg.reindeer || 0); k++) {
    const s = spot(320, 500, end); if (s < 0) continue;
    const poro = k >= (leg.moose || 0);
    road.signs.push({ s, kind: poro ? 'poro' : 'hirvi' }); evs.push({ s: s + 230 + r() * 60, kind: poro ? 'poro' : 'hirvi', side: r() < 0.5 ? -1 : 1, stop: r() < 0.6 });
  }
  if (leg.weather === 'lumi' || leg.weather === 'pyry') road.signs.push({ s: 120, kind: 'liukas' });
  // Traffic: where each one is met. Slow ones ahead are placed so the player reaches them there.
  const ahead = (kind, n) => { for (let k = 0; k < n; k++) { const s = spot(160, 250, end - 150); if (s > 0) evs.push({ s, kind }); } };
  ahead('traktori', leg.tractors); ahead('auto', leg.cars); ahead('rekka', leg.trucks); ahead('kavelija', leg.walkers);
  for (let k = 0; k < leg.racers; k++) { const s = 500 + r() * (end - 700); evs.push({ s, kind: k % 2 ? 'ohittaja' : 'takaa' }); }
  // Oncoming cars come anywhere, also over the slow ones; a few are trucks.
  for (let k = 0; k < leg.oncoming; k++) evs.push({ s: 150 + (k + r() * 0.8) * (end - 150) / leg.oncoming, kind: 'vastaan', truck: r() < 0.25 + 0.1 * leg.trucks });
  for (const e of evs) e.r = r();
  events = evs.sort((a, b) => a.s - b.s);
  road.signs.sort((a, b) => a.s - b.s);

  P = { s: 6, lat: LANE, v: 60 / KMH, vl: 0, len: 4.5, wid: 1.8, high: false, brake: false, steer: 0,
    damage: 0, tired: 0, blink: 0, blinkT: 6, rest: 0, gap: [] };
  things = []; T = 0; points = 0; msgs = []; crashWhy = ''; result = null; flash = whiteout = shake = 0;
  tally = { ohitukset: 0, valot: 0, haikaisyt: 0, sakot: 0, lahelta: 0, kuopat: 0, tauko: 0 };
  input.left = input.right = input.brake = false;
  mode = 'drive';
  if (window.AiPelitScores) AiPelitScores.board(`osa-${level}`, `${leg.from} – ${leg.to}`);
  if (typeof onLeg === 'function') onLeg();
}
// The target time: the leg driven at the speed limits (at most 90 on snow), plus a little for
// overtaking and slowing down, plus the coffee break.
function parTime() {
  let t = 0;
  const snowy = leg.weather === 'lumi' || leg.weather === 'pyry';
  for (let s = 0; s < leg.len; s += 20) t += 20 / (Math.min(limitAt(s), snowy ? 90 : 120) / KMH);
  return Math.round(t * 1.2 + (leg.tired ? 15 : 0));
}
const reachOf = high => (high ? HIGH : LOW) * WEATHER[leg.weather].reach;
function say(text, good) { msgs.push({ text, good, t: 0 }); if (msgs.length > 3) msgs.shift(); }
function score(n, text) { points += n; if (text) say(`${text} ${n > 0 ? '+' : ''}${n}`, n > 0); }

// ---- What is on the road ----
const SIZE = { auto: [4.4, 1.8], vastaan: [4.4, 1.8], rekka: [17, 2.55], traktori: [7.5, 2.4], kavelija: [0.5, 0.5], hirvi: [2.4, 0.9], poro: [1.6, 0.6], ohittaja: [4.4, 1.8], takaa: [4.4, 1.8] };
function add(kind, o) {
  const [len, wid] = SIZE[kind] || [4.4, 1.8];
  const t = Object.assign({ kind, s: 0, lat: LANE, v: 0, vl: 0, len, wid, high: false, flashT: 0, passed: false, id: add.n = (add.n || 0) + 1 }, o);
  t.base = t.v;
  things.push(t); return t;
}
function release(e) {
  const r = e.r, W = WEATHER[leg.weather];
  switch (e.kind) {
    case 'traktori': return add('traktori', { s: P.s + 260, lat: 2.4, v: 7 + r * 2, beacon: r * TAU });
    case 'auto': return add('auto', { s: P.s + 260, v: (62 + r * 10) / KMH, colour: Math.floor(r * 5) });
    case 'rekka': return add('rekka', { s: P.s + 280, lat: 1.8, v: (72 + r * 8) / KMH * Math.min(1, W.grip + 0.2) });
    // A walker keeps to the left edge facing the traffic, as one should, or (now and then) the
    // right edge with their back to it. One in three has no reflector and shows only up close.
    case 'kavelija': return add('kavelija', { s: P.s + 240, lat: r < 0.6 ? -4.1 : 4.1, v: r < 0.6 ? -1.3 : 1.3, reflector: r > 0.33 && r < 0.9 });
    case 'vastaan': return add('vastaan', { s: P.s + 620, lat: -LANE, v: -(e.truck ? 22 : 23 + r * 5) * Math.min(1, W.grip + 0.25), truck: e.truck, len: e.truck ? 17 : 4.4, wid: e.truck ? 2.55 : 1.8, high: true, colour: Math.floor(r * 5) });
    // A reckless driver from behind: fast, high beams on, overtaking when the way looks clear.
    case 'takaa': return add('takaa', { s: P.s - 160, v: 44, colour: 4, high: true, plan: 'catch' });
    // Oncoming, overtaking a truck in the player's lane, high beams on.
    case 'ohittaja': {
      const truck = add('vastaan', { s: P.s + 520, lat: -LANE, v: -21, truck: true, len: 17, wid: 2.55, high: false });
      return add('ohittaja', { s: P.s + 545, lat: -LANE, v: -32, colour: 3, high: true, truck, plan: 'wait' });
    }
    case 'hirvi': case 'poro': {
      // It steps out of the forest so that it is on the road about four seconds of driving away.
      const lead = Math.max(55, P.v * 4.2);
      return add(e.kind, { s: P.s + lead + 25, lat: e.side * (e.kind === 'poro' ? 7 : 9), v: 0, dir: -e.side, stop: e.stop, wait: 0, walk: e.kind === 'poro' ? 2.6 : 2.0, start: true });
    }
  }
}
function vehicle(t) { return t.kind !== 'kavelija' && t.kind !== 'hirvi' && t.kind !== 'poro'; }

// ---- Input (set by ui.js from the buttons) ----
const input = { left: false, right: false, brake: false };
function toggleLights() { if (mode === 'drive') P.high = !P.high; if (typeof clickSound === 'function') clickSound(); }

// ---- One step of the drive ----
function step(dt) {
  if (mode === 'drive') drive(dt);
  else if (mode === 'crash' || mode === 'done') { if (P) { P.v = Math.max(0, P.v - 9 * dt); P.s += P.v * dt; } }
  for (const m of msgs) m.t += dt;
  msgs = msgs.filter(m => m.t < 2.2);
  flash = Math.max(0, flash - dt * 2.5); whiteout = Math.max(0, whiteout - dt * 0.9); shake = Math.max(0, shake - dt * 3);
}

function drive(dt) {
  T += dt;
  const W = WEATHER[leg.weather], grip = W.grip, k = curveAt(P.s);
  // Speed: the car keeps pulling up to 130 unless braking; the shoulder and gravel drag.
  const top = 130 / KMH, offRoad = Math.abs(P.lat) > EDGE + 0.2;
  if (input.brake) P.v = Math.max(0, P.v - (8 * grip + 1.5) * dt);
  else P.v += Math.max(0, 2.6 * (1 - P.v / top)) * dt * (offRoad ? 0.4 : 1);
  if (offRoad) P.v = Math.max(0, P.v - P.v * 0.25 * dt);
  // Steering moves the car across the road; a bend pushes it outwards (more the faster), and on
  // snow the car answers late and slides on.
  const steer = (input.right ? 1 : 0) - (input.left ? 1 : 0);
  P.steer = steer;
  const want = steer * (2.2 + Math.min(P.v, 25) * 0.1);
  P.vl += (want - P.vl) * Math.min(1, dt * 7 * grip);
  let push = -k * P.v * P.v * 0.55;
  const lim = 4.5 * grip;
  if (Math.abs(k) * P.v * P.v > lim) push *= 1.8;          // too fast for the bend: it slides wide
  P.lat += (P.vl + push) * dt;
  P.s += P.v * dt;
  if (Math.abs(P.lat) > EDGE && P.v > 8) shake = Math.max(shake, 0.25);

  if (Math.abs(P.lat) > DITCH && !inBay(P.s, P.lat)) return crash('Ajoit ojaan.');
  if (inBay(P.s, P.lat) && P.lat > 11) P.lat = 11;

  // Things come on the road as the player reaches their place.
  while (events.length && events[0].s <= P.s) release(events.shift());
  for (const t of things) move(t, dt);
  things = things.filter(t => t.s > P.s - 260 && t.s < P.s + 900);
  for (const t of things) if (meet(t, dt)) return;
  lights(dt);
  holes();
  cameras();
  tiredness(dt);
  if (mode !== 'drive') return;
  if (P.s >= leg.len) finish();
}

function inBay(s, lat) { return lat > 0 && road.bays.some(b => s > b.s0 - 15 && s < b.s1 + 15); }

function move(t, dt) {
  if (t.kind === 'hirvi' || t.kind === 'poro') {
    // Across the road at a walk; some stop on it, as moose do, and then go on.
    if (t.stop && Math.abs(t.lat) < 2.2 && t.wait < 1.6) { t.wait += dt; return; }
    t.lat += t.dir * t.walk * dt;
    return;
  }
  if (t.kind === 'takaa') {
    // Catch up, overtake in the oncoming lane when nobody is coming, cut back in ahead.
    const clear = !things.some(o => o.v < 0 && o.s > t.s && o.s < t.s + 320);
    if (t.plan === 'catch' && t.s > P.s - 30) { if (clear) t.plan = 'pass'; else { t.v = Math.max(P.v, 10); } }
    if (t.plan === 'pass') { t.v = 44; t.lat += (-LANE - t.lat) * Math.min(1, dt * 2); if (t.s > P.s + 16) t.plan = 'back'; }
    if (t.plan === 'back') t.lat += (LANE - t.lat) * Math.min(1, dt * 1.5);
  } else if (t.kind === 'ohittaja') {
    // Pulls out from behind the truck into the player's lane, and back once past it.
    if (t.plan === 'wait' && t.s - P.s < 330) t.plan = 'out';
    if (t.plan === 'out') { t.lat += (LANE - t.lat) * Math.min(1, dt * 1.6); if (t.s < t.truck.s - 22) t.plan = 'in'; }
    if (t.plan === 'in') t.lat += (-LANE - t.lat) * Math.min(1, dt * 1.8);
  } else if (t.v > 0 && t.kind !== 'kavelija') {
    // A slow car or truck ahead keeps behind a slower one.
    const front = things.find(o => o !== t && o.v > 0 && o.lat > 0 && o.s > t.s && o.s - t.s < 30 && vehicle(o));
    if (front && t.lat > 0) t.v = Math.min(t.v, front.v);
    // and behind the player: nobody drives into the player's back.
    if (t.lat > 0 && P.lat > 0 && P.s > t.s && P.s - t.s < 30) t.v = Math.min(t.v, P.v);
    else if (t.base && t.v < t.base) t.v = Math.min(t.base, t.v + 2 * dt);
  }
  if (t.v < 0 && vehicle(t)) {
    // Oncoming: high beams until a car comes near, then low, as a good driver does. A reckless
    // one keeps them on; a dazzled one flashes them at the player.
    if (t.kind !== 'ohittaja') t.high = t.s - P.s > 330 && !t.truck;
    if (t.flashT > 0) { t.flashT -= dt; t.high = Math.floor(t.flashT * 6) % 2 === 0; }
  }
  t.s += t.v * dt;
}

// Whether the player's car and a thing touch, and what passing it is worth.
function meet(t, dt) {
  const ds = Math.abs(t.s - P.s), dl = Math.abs(t.lat - P.lat);
  if (ds < (t.len + P.len) / 2 && dl < (t.wid + P.wid) / 2) {
    if (t.kind === 'kavelija') { t.lat += Math.sign(t.lat) * 2.5; return crash('Vaaratilanne: jalankulkija joutui hyppäämään ojaan.'); }
    if (t.kind === 'hirvi') return crash('Törmäsit hirveen.');
    if (t.kind === 'poro') return crash('Törmäsit poroon.');
    if (t.v < 0) return crash('Nokkakolari vastaantulijan kanssa.');
    return crash(t.kind === 'traktori' ? 'Ajoit traktorin perään.' : t.kind === 'rekka' ? 'Ajoit rekan perään.' : 'Kolari toisen auton kanssa.');
  }
  // Passing: a walker needs room, a vehicle ahead gives points once overtaken.
  if (!t.passed && P.s > t.s && t.v >= 0 && (t.kind !== 'hirvi' && t.kind !== 'poro')) {
    t.passed = true;
    if (t.kind === 'kavelija') {
      const room = dl - (t.wid + P.wid) / 2;
      if (P.v > 11 && room < 1) { tally.lahelta++; score(-40, 'Liian läheltä jalankulkijaa'); }
      else if (room >= 1.5) score(20, 'Väljä ohitus');
    } else if (t.kind === 'takaa') {
      // overtaken back by the player: nothing special
    } else { tally.ohitukset++; score(t.kind === 'rekka' ? 60 : t.kind === 'traktori' ? 40 : 50, 'Ohitus'); }
  }
  if (!t.passed && t.v < 0 && t.kind === 'kavelija' && P.s > t.s) {
    t.passed = true;
    const room = dl - (t.wid + P.wid) / 2;
    if (P.v > 11 && room < 1) { tally.lahelta++; score(-40, 'Liian läheltä jalankulkijaa'); }
    else if (room >= 1.5) score(20, 'Väljä ohitus');
  }
  // An oncoming truck in snow blows a cloud over the windscreen as it passes.
  if (t.v < 0 && t.truck && !t.cloud && t.s < P.s + 6 && (leg.weather === 'lumi' || leg.weather === 'pyry')) { t.cloud = true; whiteout = 1; }
  if (t.kind === 'takaa' && !t.honk && t.plan !== 'catch' && Math.abs(t.s - P.s) < 6) { t.honk = true; say('Hurjastelija ohitti!', false); }
  return false;
}

// High beams: dip them for an oncoming car before it is near, and behind a car ahead.
function lights(dt) {
  for (const t of things) {
    if (!vehicle(t) || t.kind === 'takaa' && t.plan === 'catch') continue;
    const d = t.s - P.s;
    if (t.v < 0 && t.kind !== 'ohittaja') {
      if (d < 0 || t.judged) continue;
      // Judged from when its lights come into sight (it is released 620 m ahead).
      if (d < 520 && t.sawHigh === undefined) t.sawHigh = P.high;
      if (!P.high && t.sawHigh) { t.sawHigh = false; t.judged = true; tally.valot++; score(20, 'Lähivaloille ajoissa'); }
      else if (d < 150 && P.high) { t.judged = true; t.flashT = 1.2; tally.haikaisyt++; score(-30, 'Häikäisit vastaantulijaa'); }
      else if (d < 150) t.judged = true;
    } else if (t.v > 0 && d > 4 && d < 70 && Math.abs(t.lat - P.lat) < 2.5) {
      t.behind = P.high ? (t.behind || 0) + dt : 0;
      if (t.behind > 1.5 && !t.judgedBehind) { t.judgedBehind = true; tally.haikaisyt++; score(-20, 'Häikäiset edellä ajavaa'); }
    }
  }
}

// Potholes on a bad stretch: slow through them, or they jolt the car and, hit hard enough, burst
// a tyre.
function holes() {
  for (const h of road.holes) {
    if (h.hit || Math.abs(h.s - P.s) > 1.2) continue;
    if (Math.abs(h.lat - (P.lat - 0.75)) < h.r + 0.15 || Math.abs(h.lat - (P.lat + 0.75)) < h.r + 0.15) {
      h.hit = true;
      if (P.v < 50 / KMH) continue;
      // Hit faster than 70 km/h, it bends the rim a little more.
      if (P.v > 70 / KMH) P.damage++;
      shake = 1; P.vl += (Math.random() < 0.5 ? -1 : 1) * 1.6; P.v *= 0.9;
      tally.kuopat++;
      if (P.damage >= 4) return crash('Rengas puhkesi kuoppaan.');
      score(-15, 'Kuoppa!');
      if (typeof bumpSound === 'function') bumpSound();
    }
  }
}

// Speed cameras: over the limit by more than 5 km/h at the camera is a fine.
function cameras() {
  for (const c of road.cams) {
    if (c.done || P.s < c.s) continue;
    c.done = true;
    const v = Math.round(P.v * KMH), lim = limitAt(c.s);
    if (v > lim + 5) { flash = 1; tally.sakot++; score(-150, `Kamera välähti: ${v} km/h, sakko`); if (typeof flashSound === 'function') flashSound(); }
    else score(25, 'Kameran ohi rajoituksissa');
  }
}

// The driver gets sleepy (#181 "Kuskia väsyttää"): the eyes close now and then, longer and more
// often as it grows, and at the end they stay shut. Coffee at the rest area wakes them up.
function tiredness(dt) {
  if (!leg.tired) return;
  const bay = road.bays.find(b => P.s > b.s0 && P.s < b.s1);
  if (bay && P.lat > EDGE + 0.5 && P.v < 15 / KMH) {
    P.rest += dt; P.v = Math.max(0, P.v - 6 * dt);
    if (P.rest > 1.4 && P.tired > 0) { P.tired = 0; tally.tauko++; T += 10; score(30, 'Kahvitauko'); P.blink = 0; }
    return;
  }
  P.rest = 0;
  // It grows with the road driven: the eyes start closing before the rest area, and without
  // the break the driver falls asleep after it, before the town.
  const b = road.bays[0], full = b ? b.s1 + leg.len * 0.16 : leg.len * 1.5;
  P.tired = Math.min(1, P.tired + P.v * dt / full / (tally.tauko ? 2.5 : 1));
  if (P.blink > 0) { P.blink -= dt; return; }
  P.blinkT -= dt;
  if (P.tired > 0.4 && P.blinkT <= 0) {
    P.blink = 0.2 + (P.tired - 0.4) * 1.6;
    P.blinkT = 9 - P.tired * 6;
    if (P.tired > 0.62) say('Silmät painuvat kiinni…', false);
  }
  if (P.tired >= 1) crash('Nukahdit rattiin.');
}
// How shut the eyes are, 0..1, for the drawing.
function eyes() { if (!P || !P.blink || P.blink <= 0) return 0; return clamp(P.blink * 4, 0, 1); }

function crash(why) {
  if (mode !== 'drive') return true;
  mode = 'crash'; crashWhy = why; shake = 1.2;
  P.v = Math.min(P.v, 6);
  if (typeof crashSound === 'function') crashSound();
  if (typeof onEnd === 'function') onEnd();
  return true;
}

function finish() {
  const par = parTime(), fast = T <= par, clean = !tally.sakot && !tally.haikaisyt && !tally.lahelta;
  const bonus = Math.max(0, Math.round((par - T) * 10));
  points += bonus;
  const st = fast ? (clean ? 3 : 2) : 1;
  const prevBest = bests[level];
  result = { stars: st, bonus, par, time: T, record: !(prevBest >= points), best: Math.max(points, prevBest || -1e9) };
  stars[level] = Math.max(stars[level] || 0, st); save('tahdet', stars);
  if (result.record) { bests[level] = points; save('pisteet', bests); }
  if (level === maxLeg && maxLeg < LEGS.length) { maxLeg++; save('taso', maxLeg); }
  // 'taso' stops at the last leg, so the legs driven are kept apart for the high-score lists.
  if (level > driven) { driven = level; save('ajettu', driven); }
  mode = 'done';
  if (points > 0 && window.AiPelitScores) AiPelitScores.submit(points);
  if (typeof onEnd === 'function') onEnd();
}
