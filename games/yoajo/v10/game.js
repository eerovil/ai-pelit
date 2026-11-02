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
// v8 (#306): the lane into a rest area widens over BAY_IN metres before it and narrows back over
// as many after; a junction's solid centre line runs from NOPASS_BEFORE metres before it to
// NOPASS_AFTER after.
const BAY_IN = 40, BAY_W = 8, NOPASS_BEFORE = 110, NOPASS_AFTER = 30;

// ---- The trip: Valtatie 4 north, one leg a level ----
// len in metres of game road (the real legs are longer; a leg is a few minutes' drive).
// Each number is how many of that thing the leg has; weather 'kuiva', 'sade', 'lumi' or 'pyry'.
// tired: how fast the driver gets sleepy (0 = not at all); a leg with it has a rest area.
// junctions (v8, #306): side roads where a car waits to pull out.
const LEGS = [
  { from: 'Helsinki', to: 'Järvenpää', len: 2600, weather: 'kuiva', limit: 100, oncoming: 9, cars: 2, tractors: 2, walkers: 1, trucks: 0, cameras: 0, moose: 0, racers: 0, bad: 0, tired: 0, junctions: 2, seed: 11 },
  { from: 'Järvenpää', to: 'Lahti', len: 3000, weather: 'sade', limit: 100, oncoming: 11, cars: 2, tractors: 1, walkers: 3, trucks: 2, cameras: 1, moose: 0, racers: 0, bad: 0, tired: 0, junctions: 2, seed: 22 },
  { from: 'Lahti', to: 'Heinola', len: 3200, weather: 'sade', limit: 80, oncoming: 11, cars: 2, tractors: 1, walkers: 2, trucks: 2, cameras: 2, moose: 0, racers: 1, bad: 1, tired: 0.6, junctions: 3, seed: 33 },
  { from: 'Heinola', to: 'Jyväskylä', len: 3400, weather: 'kuiva', limit: 100, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 3, cameras: 1, moose: 2, racers: 1, bad: 1, tired: 0.8, junctions: 3, seed: 44 },
  { from: 'Jyväskylä', to: 'Äänekoski', len: 3400, weather: 'lumi', limit: 80, oncoming: 11, cars: 1, tractors: 2, walkers: 2, trucks: 2, cameras: 1, moose: 2, racers: 1, bad: 1, tired: 0.8, junctions: 3, seed: 55 },
  { from: 'Äänekoski', to: 'Pihtipudas', len: 3600, weather: 'lumi', limit: 80, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 3, cameras: 2, moose: 3, racers: 2, bad: 2, tired: 1, junctions: 3, seed: 66 },
  { from: 'Pihtipudas', to: 'Oulu', len: 3800, weather: 'pyry', limit: 80, oncoming: 12, cars: 2, tractors: 1, walkers: 2, trucks: 4, cameras: 2, moose: 3, racers: 2, bad: 2, tired: 1, junctions: 3, seed: 77 },
  { from: 'Oulu', to: 'Rovaniemi', len: 4000, weather: 'pyry', limit: 80, oncoming: 13, cars: 2, tractors: 1, walkers: 2, trucks: 4, cameras: 2, moose: 2, reindeer: 3, racers: 2, bad: 2, tired: 1.2, junctions: 3, seed: 88 },
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
let road = null;                     // { len, n, X, Y, Z, TH, K, limits, signs, holes, bays, bad, junctions, nopass }
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
  road = { len: L.len, total, n, X, Y, Z, TH, K, limits: [], signs: [], holes: [], bays: [], cams: [], bad: [], junctions: [], nopass: [] };
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
let flash = 0, whiteout = 0, shake = 0, cloudIn = 0;

function newLeg(n) {
  level = clamp(n || level, 1, maxLeg);
  leg = LEGS[level - 1];
  makeRoad(leg);
  const r = rng(leg.seed * 7 + 1);
  // Speed limits: the leg's own, now and then 60 at a village or 100 on a good stretch, and 50
  // into the town at the end. A sign stands where each one starts.
  const lim = road.limits;
  lim.push({ s: 0, v: leg.limit });
  // v4 (#181: "nopeusrajoitukset muuttuu vähän liian usein"): a stretch with another limit every
  // 1.3–2 km (v1–v3: every 0.7–1.3 km), longer, and 60 only from leg 5, now and then.
  for (let s = 900 + r() * 500; s < leg.len - 900; s += 1300 + r() * 700) {
    const slow = level >= 5 && r() < 0.35, dry = leg.weather === 'kuiva' || leg.weather === 'sade';
    const v = slow ? 60 : leg.limit === 100 ? 80 : dry ? 100 : 0;
    if (!v) continue;                     // snow on an 80 road before leg 5: no change at all
    lim.push({ s, v }); lim.push({ s: s + 400 + r() * 300, v: leg.limit });
  }
  lim.push({ s: leg.len - 260, v: 50 });
  road.signs.push({ s: leg.len - 70, kind: 'kaupunki', text: leg.to });

  // Places for the rest, spread over the leg so that two never fall on the same stretch.
  const used = [];
  const free = (a, b) => used.every(([u0, u1]) => b < u0 || a > u1);
  function spot(span, from, to, rr = r) {
    for (let k = 0; k < 60; k++) { const s = from + rr() * (to - from - span); if (free(s - 40, s + span + 40)) { used.push([s, s + span]); return s; } }
    return -1;
  }
  const evs = [];
  const end = leg.len - 320;
  // A rest area with coffee (#181 "Kuskia väsyttää") about halfway, where the driver gets sleepy.
  // v8 (#306 "P paikka pitää olla selkeämpi. Tie siihen ja merkkejä"): signs at 500 m and
  // 100 m, and an exit sign where the lane into it begins (v1–v7: one sign, 60 m before).
  if (leg.tired) {
    const s = spot(140, leg.len * 0.4, leg.len * 0.62);
    if (s > 0) {
      const b = { s0: s + 60, s1: s + 140 };
      road.bays.push(b);
      if (b.s0 - 500 > 30) road.signs.push({ s: b.s0 - 500, kind: 'levahdys', text: '500 m' });
      road.signs.push({ s: b.s0 - 100, kind: 'levahdys', text: '100 m' }, { s: b.s0 - BAY_IN - 4, kind: 'pnuoli' });
    }
  }
  for (let k = 0; k < leg.bad; k++) {
    const s = spot(280, 400, end); if (s < 0) continue;
    road.signs.push({ s, kind: 'kuoppa' });
    for (let h = s + 110; h < s + 280; h += 7 + r() * 12) road.holes.push({ s: h, lat: (r() * 2 - 1) * 3, r: 0.45 + r() * 0.35 });
    // v7 (#266 "Mitä kuopille mahtaa?"): a 50 limit over the potholes, under which they do no
    // harm, and the limit it was after them. Any other limit change inside the stretch goes.
    const after = limitAt(s + 290);
    for (let i = lim.length - 1; i >= 0; i--) if (lim[i].s >= s && lim[i].s <= s + 290) lim.splice(i, 1);
    lim.push({ s: s + 40, v: 50 }, { s: s + 290, v: after }); lim.sort((a, b) => a.s - b.s);
    road.bad.push({ s0: s, s1: s + 290, told: false });
  }
  const fixed = used.slice();   // v8: junctions keep clear of the rest area and the bad stretches only
  for (const l of lim) if (l.s > 0) road.signs.push({ s: l.s, kind: 'raja', v: l.v });
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
  // v8 (#306 "Välillä voisi olla risteyksiä mistä tulee autoja"): side roads, each with a car
  // waiting to pull out, a warning sign before it and a solid yellow centre line through it
  // ("Ohituskielto merkinnät risteyksien kohdalla"). Their own random numbers, so the rest of each
  // leg stays where v7 had it.
  const rj = rng(leg.seed * 13 + 5);
  used.length = 0; used.push(...fixed);
  for (let k = 0; k < (leg.junctions || 0); k++) {
    const x = spot(190, 400, end - 100, rj); if (x < 0) continue;
    const J = { s: Math.round((x + 150) / 4) * 4, side: rj() < 0.5 ? -1 : 1, both: rj() < 0.3 };
    road.junctions.push(J);
    road.signs.push({ s: x + 10, kind: 'risteys', side: J.both ? 0 : J.side });
    road.nopass.push({ s0: J.s - NOPASS_BEFORE, s1: J.s + NOPASS_AFTER });
    road.signs.push({ s: J.s - NOPASS_BEFORE, kind: 'ohituskielto' });
    if (rj() < 0.9) {
      const side = J.both && rj() < 0.5 ? -J.side : J.side;
      evs.push({ s: J.s - 330, kind: 'liittyja', j: J, side, dir: rj() < 0.55 ? 'same' : 'vastaan', careless: rj() < 0.35, r: rj() });
    }
  }
  road.junctions.sort((a, b) => a.s - b.s);
  events = evs.sort((a, b) => a.s - b.s);
  road.signs.sort((a, b) => a.s - b.s);

  P = { s: 6, lat: LANE, v: 60 / KMH, vl: 0, len: 4.5, wid: 1.8, high: false, brake: false, steer: 0,
    damage: 0, tired: 0, blink: 0, blinkT: 6, rest: 0, gap: [], highRun: 0, nudge: 0, overT: 0, unsafe: false };
  things = []; T = 0; points = 0; msgs = []; crashWhy = ''; result = null; flash = whiteout = shake = cloudIn = 0;
  tally = { ohitukset: 0, valot: 0, haikaisyt: 0, sakot: 0, lahelta: 0, kuopat: 0, tauko: 0, pitkat: 0, pitkatP: 0, hurjastelu: 0 };
  input.left = input.right = false; input.steer = input.gas = input.brake = 0;
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
    // v4 (#181): cars keep to the limit as drivers do, each by its own habit: some slow (the ones
    // to overtake), most about at the limit, a few a little over. Trucks at most 80.
    case 'auto': return cruiseFrom(add('auto', { s: P.s + 260, colour: Math.floor(r * 5), habit: r < 0.4 ? -22 + r * 25 : r < 0.85 ? -4 + (r - 0.4) * 17 : 6 + (r - 0.85) * 55 }));
    case 'rekka': return cruiseFrom(add('rekka', { s: P.s + 280, lat: 1.8, habit: r * 4 }));
    // A walker keeps to the left edge facing the traffic, as one should, or (now and then) the
    // right edge with their back to it. One in three has no reflector and shows only up close.
    case 'kavelija': return add('kavelija', { s: P.s + 240, lat: r < 0.6 ? -4.1 : 4.1, v: r < 0.6 ? -1.3 : 1.3, reflector: r > 0.33 && r < 0.9 });
    case 'vastaan': return cruiseFrom(add('vastaan', { s: P.s + 620, lat: -LANE, truck: e.truck, len: e.truck ? 17 : 4.4, wid: e.truck ? 2.55 : 1.8, high: true, colour: Math.floor(r * 5), habit: e.truck ? r * 4 : r < 0.25 ? -8 + r * 24 : r < 0.75 ? (r - 0.25) * 12 : 8 + (r - 0.75) * 28 }));
    // A reckless driver from behind: fast, high beams on, overtaking when the way looks clear.
    case 'takaa': return add('takaa', { s: P.s - 160, v: 44, colour: 4, high: true, plan: 'catch' });
    // Oncoming, overtaking a truck in the player's lane, high beams on.
    case 'ohittaja': {
      const truck = add('vastaan', { s: P.s + 520, lat: -LANE, v: -21, truck: true, len: 17, wid: 2.55, high: false });
      return add('ohittaja', { s: P.s + 545, lat: -LANE, v: -32, colour: 3, high: true, truck, plan: 'wait' });
    }
    // v8 (#306): a car waiting at a side road, facing the road, its lights on. It pulls out into
    // the player's lane ahead (dir 'same') or turns towards the player (dir 'vastaan'). A careless
    // one pulls out close in front.
    case 'liittyja': return add('liittyja', { s: e.j.s, lat: e.side * 9, v: 0, side: e.side, dir: e.dir, careless: e.careless,
      plan: 'wait', turn: 0, yaw: e.side * Math.PI / 2, passed: true, colour: Math.floor(r * 5), habit: r < 0.5 ? -15 + r * 20 : -5 + (r - 0.5) * 16 });
    case 'hirvi': case 'poro': {
      // It steps out of the forest so that it is on the road about four seconds of driving away.
      const lead = Math.max(55, P.v * 4.2);
      return add(e.kind, { s: P.s + lead + 25, lat: e.side * (e.kind === 'poro' ? 7 : 9), v: 0, dir: -e.side, stop: e.stop, wait: 0, walk: e.kind === 'poro' ? 2.6 : 2.0, start: true });
    }
  }
}
// The speed a car with a habit wants here, m/s: the limit where it is plus its habit (trucks at
// most 80), slower on a slippery road.
function cruise(t) {
  const lim = limitAt(clamp(t.s, 0, road.len)), heavy = t.kind === 'rekka' || t.truck;
  return (Math.min(lim, heavy ? 80 : 200) + t.habit) / KMH * Math.min(1, WEATHER[leg.weather].grip + 0.25);
}
function cruiseFrom(t) { t.base = cruise(t); t.v = t.v < 0 || t.kind === 'vastaan' ? -t.base : t.base; return t; }
function vehicle(t) { return t.kind !== 'kavelija' && t.kind !== 'hirvi' && t.kind !== 'poro'; }

// ---- Input (set by ui.js from the buttons) ----
// v3 (#181 feedback): steering, gas and brake are amounts, 0..1 (steer -1..1), set by the
// thumbs' slides in ui.js. left and right still steer fully (the tests' drivers use them).
const input = { left: false, right: false, steer: 0, gas: 0, brake: 0 };
function toggleLights() { if (mode === 'drive') P.high = !P.high; if (typeof clickSound === 'function') clickSound(); }

// ---- One step of the drive ----
function step(dt) {
  if (mode === 'drive') drive(dt);
  else if (mode === 'crash' || mode === 'done') { if (P) { P.v = Math.max(0, P.v - 9 * dt); P.s += P.v * dt; } }
  for (const m of msgs) m.t += dt;
  msgs = msgs.filter(m => m.t < 2.2);
  flash = Math.max(0, flash - dt * 2.5);
  // v8 (#306 "Kun rekka tulee vastaan niin ruutu välähtää ikävästi"): the snow cloud thickens over a
  // quarter of a second to a haze the road shows through, and thins over a second (v1–v7: the
  // screen went 92 % white at once).
  if (cloudIn > 0) { cloudIn -= dt; whiteout = Math.min(CLOUD, whiteout + dt * CLOUD * 4); } else whiteout = Math.max(0, whiteout - dt * 0.5); shake = Math.max(0, shake - dt * 3);
}

const PULL = 2.5;
const CLOUD = 0.5;
function drive(dt) {
  T += dt;
  const W = WEATHER[leg.weather], grip = W.grip, k = curveAt(P.s);
  // Speed: v3 has a gas pedal: as much pull as the thumb asks, up to 130 at full; off the gas
  // the engine slows the car a little. The brake by how far the thumb slides down. The
  // shoulder and gravel drag.
  const top = 130 / KMH, offRoad = Math.abs(P.lat) > EDGE + 0.2;
  const brake = clamp(+input.brake || 0, 0, 1), gas = clamp(+input.gas || 0, 0, 1);
  P.gas = gas;
  if (brake > 0) P.v = Math.max(0, P.v - (8 * grip + 1.5) * brake * dt);
  else {
    // v8 (#306 "Kiihtyvyys tehokkaammaksi"): the pull is 2.5 times v1–v7's, so full gas takes the
    // car from 0 to 100 in about 7 s (v1–v7: 17 s). Each gas still settles at the same speed, and
    // easing off slows the car as before.
    let a = gas * 3.2 * Math.max(0, 1 - P.v / top) - (1 - gas) * 0.5;
    if (a > 0) a *= PULL;
    P.v = Math.max(0, P.v + a * dt * (offRoad ? 0.4 : 1));
  }
  if (offRoad) P.v = Math.max(0, P.v - P.v * 0.25 * dt);
  // Steering moves the car across the road; a bend pushes it outwards (more the faster), and on
  // snow the car answers late and slides on.
  // v3: by how far the thumb slides, from a gentle drift to a sharper turn than v1's buttons.
  const steer = clamp((+input.steer || 0) + (input.right ? 1 : 0) - (input.left ? 1 : 0), -1, 1);
  P.steer = steer;
  const want = steer * (2.6 + Math.min(P.v, 25) * 0.15);
  P.vl += (want - P.vl) * Math.min(1, dt * 7 * grip);
  let push = -k * P.v * P.v * 0.55;
  const lim = 4.5 * grip;
  if (Math.abs(k) * P.v * P.v > lim) push *= 1.8;          // too fast for the bend: it slides wide
  P.lat += (P.vl + push) * dt;
  P.s += P.v * dt;
  if (Math.abs(P.lat) > EDGE && P.v > 8) shake = Math.max(shake, 0.25);

  if (Math.abs(P.lat) > DITCH && !inBay(P.s, P.lat)) return crash('Ajoit ojaan.');
  // v8: the rest area's kerb keeps the car on its paving, and its narrowing lane leads it back.
  if (inBay(P.s, P.lat)) P.lat = Math.min(P.lat, Math.max(DITCH - 0.1, EDGE + bayWidth(P.s) - 0.6));

  // Things come on the road as the player reaches their place.
  while (events.length && events[0].s <= P.s) release(events.shift());
  for (const t of things) move(t, dt);
  things = things.filter(t => t.s > P.s - 260 && t.s < P.s + 900);
  // An overtake is judged unsafe before it is scored, so a pass in the same moment as an oncoming
  // car comes within 180 m earns nothing.
  unsafeOvertake();
  for (const t of things) if (meet(t, dt)) return;
  lights(dt);
  highBeams(dt);
  reckless(dt);
  holes();
  cameras();
  tiredness(dt);
  if (mode !== 'drive') return;
  if (P.s >= leg.len) finish();
}

// v8 (#306): the rest area is a lane of its own: it widens from the edge over BAY_IN metres, runs
// BAY_W wide past the parking places, and narrows back (v1–v7: a square bay, 15 m either way).
function bayWidth(s) {
  let w = 0;
  for (const b of road.bays) w = Math.max(w, BAY_W * clamp(Math.min((s - b.s0 + BAY_IN) / BAY_IN, (b.s1 + BAY_IN - s) / BAY_IN), 0, 1));
  return w;
}
function inBay(s, lat) { return lat > 0 && bayWidth(s) > 0; }
function noPass(s) { return road.nopass.some(z => s > z.s0 && s < z.s1); }

function move(t, dt) {
  if (t.kind === 'hirvi' || t.kind === 'poro') {
    // Across the road at a walk; some stop on it, as moose do, and then go on.
    if (t.stop && Math.abs(t.lat) < 2.2 && t.wait < 1.6) { t.wait += dt; return; }
    t.lat += t.dir * t.walk * dt;
    return;
  }
  if (t.kind === 'liittyja') return joiner(t, dt);
  if (t.kind === 'takaa') {
    // Catch up, overtake in the oncoming lane when nobody is coming, cut back in ahead.
    const clear = !things.some(o => o.v < 0 && o.s > t.s && o.s < t.s + 320);
    // v4: never into the player's back: it waits while the player is out overtaking, and slows
    // behind them if they pull out in front of it (v1–v3 could drive into them there).
    const out = P.lat < LANE - 0.6;
    // Waiting behind: never faster than the player, and slower still when closer than 15 m.
    if (t.plan === 'catch' && t.s > P.s - 30) {
      if (clear && !out) t.plan = 'pass';
      else t.v = P.s - t.s < 15 ? P.v * 0.85 : P.v;
    }
    if (t.plan === 'pass') {
      t.v = 44; t.lat += (-LANE - t.lat) * Math.min(1, dt * 2); if (t.s > P.s + 16) t.plan = 'back';
      if (P.s > t.s && P.s - t.s < 40 && Math.abs(P.lat - t.lat) < 2.3) t.v = Math.min(t.v, P.v);
    }
    if (t.plan === 'back') t.lat += (LANE - t.lat) * Math.min(1, dt * 1.5);
  } else if (t.kind === 'ohittaja') {
    // Pulls out from behind the truck into the player's lane, and back once past it.
    if (t.plan === 'wait' && t.s - P.s < 330) t.plan = 'out';
    if (t.plan === 'out') { t.lat += (LANE - t.lat) * Math.min(1, dt * 1.6); if (t.s < t.truck.s - 22) t.plan = 'in'; }
    if (t.plan === 'in') t.lat += (-LANE - t.lat) * Math.min(1, dt * 1.8);
  } else if (t.v > 0 && t.kind !== 'kavelija') {
    if (t.habit !== undefined) t.base = cruise(t);
    // A slow car or truck ahead keeps behind a slower one.
    // v8: it brakes for it from 70 m, as hard as it needs (v1–v7: matched its speed at once from
    // 30 m, which a car close behind could not brake for, now that cars pull out of side roads).
    // Only a car on the road counts: not one still at or coming out of a side road (out of the lane).
    const front = things.find(o => o !== t && o.v > 0 && o.lat > 0 && o.lat < EDGE && o.kind !== 'liittyja' && o.s > t.s && o.s - t.s < 70 && vehicle(o));
    if (front && t.lat > 0 && t.v > front.v) {
      const gap = front.s - t.s - (front.len + t.len) / 2;
      if (gap < 8) t.v = front.v;
      else t.v = Math.max(front.v, t.v - Math.min(9, (t.v - front.v) ** 2 / (2 * (gap - 7))) * dt);
    }
    // and behind the player: nobody drives into the player's back.
    if (t.lat > 0 && P.lat > 0 && P.s > t.s && P.s - t.s < 30) t.v = Math.min(t.v, P.v);
    else if (t.base && t.v < t.base) t.v = Math.min(t.base, t.v + 2 * dt);
    else if (t.base && t.v > t.base) t.v = Math.max(t.base, t.v - 3 * dt);   // slowing for a lower limit
  }
  if (t.v < 0 && vehicle(t) && t.habit !== undefined) {
    // Oncoming cars keep to the limit by their habit too.
    t.base = cruise(t); t.v += clamp(-t.base - t.v, -2 * dt, 3 * dt);
  }
  if (t.v < 0 && vehicle(t)) {
    // Oncoming: high beams until a car comes near, then low, as a good driver does. A reckless
    // one keeps them on; a dazzled one flashes them at the player.
    if (t.kind !== 'ohittaja') t.high = t.s - P.s > 330 && !t.truck;
    if (t.flashT > 0) { t.flashT -= dt; t.high = Math.floor(t.flashT * 6) % 2 === 0; }
  }
  t.s += t.v * dt;
}

// v8 (#306): the car at a side road. It waits until the way looks clear to it, then turns onto
// the road over TURN seconds and drives on as any car does. A careful one leaves the player five
// to seven seconds; a careless one two and a half to three, at least 60 m: room to brake.
const TURN = 1.8;
function joiner(t, dt) {
  const same = t.dir === 'same', lane = same ? LANE : -LANE, d = t.s - P.s;
  if (t.plan === 'wait') {
    const busy = things.some(o => o !== t && vehicle(o) && Math.abs(o.s - t.s) < (same ? 45 : 70) && (same ? o.lat > 0 : o.lat < 0)
      || o !== t && vehicle(o) && o.v < 0 && o.s > t.s && o.s - t.s < 120 && t.side < 0 && same);
    // Its moment: when the player is in its window ahead. One that missed it (a car came) stays.
    const near = t.careless ? Math.max(60, P.v * 2.4) : Math.max(120, P.v * 5), far = t.careless ? Math.max(70, P.v * 3) : Math.max(150, P.v * 7);
    const go = same ? d > near && d < far : d > 70 && d < 260 && P.lat > 0;
    if (!go || busy) return;
    t.plan = 'turn';
    if (same && t.careless) say('Auto risteyksestä!', false);
  }
  // Turning: sideways onto its lane, gathering speed, the nose coming round.
  t.turn = Math.min(1, t.turn + dt / TURN);
  const u = t.turn, ease = u * u * (3 - 2 * u);
  t.lat = t.side * 9 + (lane - t.side * 9) * ease;
  t.yaw = t.side * Math.PI / 2 * (1 - ease) * (same ? 1 : -1);
  t.v = (same ? 1 : -1) * (1.5 + 5 * u);
  if (u >= 1) {
    // On the road: from here an ordinary car, keeping to the limit by its habit.
    t.kind = same ? 'auto' : 'vastaan'; t.yaw = 0; t.lat = lane; t.passed = P.s > t.s;
    t.base = cruise(t); t.high = false;
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
    } else if (P.unsafe) {
      // v4 (#181): an overtake made unsafely (an oncoming car within 180 m while out) earns nothing.
    } else { tally.ohitukset++; score(t.kind === 'rekka' ? 60 : t.kind === 'traktori' ? 40 : 50, 'Ohitus'); }
  }
  if (!t.passed && t.v < 0 && t.kind === 'kavelija' && P.s > t.s) {
    t.passed = true;
    const room = dl - (t.wid + P.wid) / 2;
    if (P.v > 11 && room < 1) { tally.lahelta++; score(-40, 'Liian läheltä jalankulkijaa'); }
    else if (room >= 1.5) score(20, 'Väljä ohitus');
  }
  // v6 (#235): a truck going by whooshes, oncoming or overtaken, when it is beside the car.
  if (!t.whoosh && (t.kind === 'rekka' || t.truck) && Math.abs(t.s - P.s) < (t.len + P.len) / 2 && Math.abs(t.lat - P.lat) < 5) {
    t.whoosh = true; if (typeof truckSound === 'function') truckSound(Math.abs(t.v - P.v));
  }
  // An oncoming truck in snow blows a cloud over the windscreen as it passes.
  if (t.v < 0 && t.truck && !t.cloud && t.s < P.s + 6 && (leg.weather === 'lumi' || leg.weather === 'pyry')) { t.cloud = true; cloudIn = 0.25; }
  if (t.kind === 'takaa' && !t.honk && t.plan !== 'catch' && Math.abs(t.s - P.s) < 6) { t.honk = true; say('Hurjastelija ohitti!', false); }
  return false;
}

// High beams: dip them for an oncoming car before it is near, and behind a car ahead.
const DAZZLE = 90;
// v4 (#181: "pitkien valojen käyttöä ei rohkaista"): every 100 m on high beams is worth 5 points,
// and a while on low beams on an empty road brings a reminder.
const HIGH_STEP = 100, HIGH_POINTS = 5, NUDGE_AFTER = 6;
function roadEmpty() {
  return !things.some(t => vehicle(t) && ((t.v < 0 && t.s > P.s - 5 && t.s - P.s < 520) || (t.v >= 0 && t.s > P.s && t.s - P.s < 60)));
}
// v4 (#181: "hurjastelusta pitää antaa miinusta"): driving 20 km/h or more over the limit for
// over a second costs 25 points, and 25 more every 5 s it goes on; being in the oncoming lane
// while an oncoming car is within 180 m costs 50, once a car. Both cost the third star.
// v8 (#306 "Vaarallinen ohitus on hieman liian herkkä"): within 130 m (v4–v7: 180 m). Crossing
// a junction's solid centre line costs 30, once until back in the lane, and counts as reckless.
const RECKLESS_OVER = 20, RECKLESS_EVERY = 5, ONCOMING_GAP = 130;
function reckless(dt) {
  const kmh = P.v * KMH, lim = limitAt(P.s);
  if (kmh >= lim + RECKLESS_OVER) {
    P.overT += dt;
    if (P.overT > 1) { P.overT -= RECKLESS_EVERY; tally.hurjastelu++; score(-25, `Hurjastelu: ${Math.round(kmh)} km/h`); }
  } else P.overT = 0;
}
function unsafeOvertake() {
  if (P.lat < 0) for (const t of things) {
    if (t.v < 0 && vehicle(t) && !t.cutIn && t.s > P.s && t.s - P.s < ONCOMING_GAP) {
      t.cutIn = true; tally.hurjastelu++; score(-50, 'Vaarallinen ohitus'); P.unsafe = true;
    }
  }
  if (P.lat < 0 && !P.crossed && noPass(P.s)) { P.crossed = true; P.unsafe = true; tally.hurjastelu++; score(-30, 'Ohitit sulkuviivan yli'); }
  // The overtake stays unsafe until the car is back in its own lane.
  if (P.lat > LANE - 0.6) P.unsafe = P.crossed = false;
}
// Street lights (#181): the town at the end and the villages, where the limit is 60. No high beams
// are needed there: driving on them earns nothing, and nobody is reminded.
function streetLit(s) { return s >= road.len - 300 || limitAt(s) === 60; }
function highBeams(dt) {
  if (streetLit(P.s)) { P.nudge = 0; return; }
  if (P.high) {
    P.highRun += P.v * dt;
    tally.pitkat += P.v * dt;
    while (P.highRun >= HIGH_STEP) {
      P.highRun -= HIGH_STEP; points += HIGH_POINTS; tally.pitkatP += HIGH_POINTS;
      // Shown every 500 m, so the reward is seen without a message every few seconds.
      if (tally.pitkatP % (HIGH_POINTS * 5) === 0) say(`Pitkillä ${(tally.pitkatP / HIGH_POINTS / 10).toFixed(1).replace('.', ',')} km +${tally.pitkatP}`, true);
    }
    P.nudge = 0;
  } else if (P.v > 12 && roadEmpty()) {
    P.nudge += dt;
    if (P.nudge > NUDGE_AFTER) { say('Tie on tyhjä: pitkät päälle!', true); P.nudge = -12; }
  } else P.nudge = Math.min(P.nudge, 0);
}
function lights(dt) {
  for (const t of things) {
    if (!vehicle(t) || t.kind === 'liittyja' || t.kind === 'takaa' && t.plan === 'catch') continue;
    const d = t.s - P.s;
    if (t.v < 0 && t.kind !== 'ohittaja') {
      if (d < 0 || t.judged) continue;
      // Judged from when its lights come into sight (it is released 620 m ahead).
      if (d < 520 && t.sawHigh === undefined) t.sawHigh = P.high;
      if (!P.high && t.sawHigh) { t.sawHigh = false; t.judged = true; tally.valot++; score(20, 'Lähivaloille ajoissa'); }
      // v4 (#181: "häikäisy tulee liian herkästi"): dazzled only when still on high beams 90 m
      // away (v1–v3: 150 m), so there is time to see the lights and dip.
      else if (d < DAZZLE && P.high) { t.judged = true; t.flashT = 1.2; tally.haikaisyt++; score(-30, 'Häikäisit vastaantulijaa'); if (typeof honkSound === 'function') honkSound(); }
      else if (d < DAZZLE) t.judged = true;
    } else if (t.v > 0 && d > 4 && d < 50 && Math.abs(t.lat - P.lat) < 2.5) {
      // A car ahead: within 50 m for 2.5 s (v1–v3: 70 m, 1.5 s).
      t.behind = P.high ? (t.behind || 0) + dt : 0;
      if (t.behind > 2.5 && !t.judgedBehind) { t.judgedBehind = true; tally.haikaisyt++; score(-20, 'Häikäiset edellä ajavaa'); if (typeof honkSound === 'function') honkSound(); }
    }
  }
}

// Potholes on a bad stretch: slow through them, or they jolt the car and, hit hard enough, burst
// a tyre. v7 (#266): at the stretch's sign the driver is told how, and up to 55 km/h (the 50
// limit and a little) they do nothing (v1–v6: under 50).
const HOLE_SAFE = 55;
function holes() {
  for (const b of road.bad) if (!b.told && P.s >= b.s0 - 30 && P.s < b.s1) { b.told = true; say(`Kuoppia: hidasta alle ${HOLE_SAFE - 5} km/h`, false); }
  for (const h of road.holes) {
    if (h.hit || Math.abs(h.s - P.s) > 1.2) continue;
    if (Math.abs(h.lat - (P.lat - 0.75)) < h.r + 0.15 || Math.abs(h.lat - (P.lat + 0.75)) < h.r + 0.15) {
      h.hit = true;
      if (P.v <= HOLE_SAFE / KMH) continue;
      // Hit faster than 70 km/h, it bends the rim a little more.
      if (P.v > 70 / KMH) P.damage++;
      shake = 1; P.vl += (Math.random() < 0.5 ? -1 : 1) * 1.6; P.v *= 0.9;
      tally.kuopat++;
      // v6: the thud comes first, also for the hit that bursts the tyre.
      if (typeof bumpSound === 'function') bumpSound();
      if (P.damage >= 4) return crash('Rengas puhkesi kuoppaan.');
      score(-15, 'Kuoppa!');
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
  if (typeof crashSound === 'function') crashSound(why);
  if (typeof onEnd === 'function') onEnd();
  return true;
}

function finish() {
  const par = parTime(), fast = T <= par, clean = !tally.sakot && !tally.haikaisyt && !tally.lahelta && !tally.hurjastelu;
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
  if (typeof legDoneSound === 'function') legDoneSound();
  // Every leg driven to the end goes to its list, even at zero or below after fines: it still
  // counts as a leg driven.
  if (window.AiPelitScores) AiPelitScores.submit(points);
  if (typeof onEnd === 'function') onEnd();
}
