// Vuoristorata v1 (#180): the ride itself, in plain numbers. index.html draws it with three.js.
//
// A track is a line of samples every DS metres, built from pieces (a lift hill, drops, hills,
// curves, loops, helices) like a turtle: each piece sets the pitch, the turn and the bank along
// its length. The car moves along the track by its distance s: gravity along the slope, rolling
// friction and air, plus the player's boost and brake. The track holds the car only while the
// forces stay sane: too fast over a crest lifts it off, too fast in a curve tips it over, too slow
// at the top of a loop drops it. Each such place gets a sign before it (max or min km/h).
'use strict';

const G = 9.81;
const DS = 0.5;               // metres between track samples
const LIFT_V = 7;             // the chain pulls at least this fast
const BOOST_A = 6.5;          // m/s² while the boost is held
const BRAKE_A = 9;            // m/s² while the brake is held
const ENERGY_USE = 0.28;      // share of the boost energy used per second
const ENERGY_BACK = 0.05;     // regained per second
const LIFT_OFF = -0.4;        // felt vertical g below which the car leaves the track
const SIDE_MAX = 1.35;        // felt sideways g above which it tips over
const GRACE = 0.25;           // seconds over a limit before it goes
const SIGN_AHEAD = 45;        // metres from a sign to the place it warns of
const KEY = 'ai-pelit:vuoristorata:';
const $ = id => document.getElementById(id);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const kmh = v => Math.round(v * 3.6);

// ---- Saves (rule 5: ai-pelit:vuoristorata:*) ----
function load(name, d) { try { const v = localStorage.getItem(KEY + name); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(name, v) { try { localStorage.setItem(KEY + name, JSON.stringify(v)); } catch (e) {} }

// ---- Smooth shapes over u in [0, 1] ----
const ease = u => { u = clamp(u, 0, 1); return u * u * u * (u * (u * 6 - 15) + 10); };
// 0 → 1 over the first `a` of the piece, 1 until the last `a`, then back to 0.
const plateau = (u, a) => ease(u / a) - ease((u - 1 + a) / a);

// ---- Random numbers from a seed, so a level is the same track on every phone ----
function rng(seed) {
  let s = (seed >>> 0) % 2147483647 || 1;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

// ---- Pieces: functions of u giving pitch (absolute), turn (added to the heading), bank, side shift ----
const deg = Math.PI / 180;
function piece(kind, len, f) { return Object.assign({ kind, len, pitch: () => 0, turn: () => 0, bank: () => 0, side: () => 0 }, f); }
const straight = len => piece('straight', len);
// A pitched piece is a chain of parts: a bend from one pitch to another, tightest (radius R) in
// its middle, or a stretch held at one pitch.
const bend = (a, b, R) => ({ len: Math.max(1, Math.abs(b - a) * R * 1.875), pitch: u => a + (b - a) * ease(u) });
const hold = (a, len) => ({ len: Math.max(0, len), pitch: () => a });
function chain(kind, parts) {
  const len = parts.reduce((t, p) => t + p.len, 0);
  return piece(kind, len, {
    pitch: u => {
      let s = u * len;
      for (const p of parts) { if (s <= p.len || p === parts[parts.length - 1]) return p.pitch(p.len ? clamp(s / p.len, 0, 1) : 0); s -= p.len; }
      return 0;
    },
  });
}
const partRise = p => { let t = 0; for (let i = 0; i < 40; i++) t += Math.sin(p.pitch((i + 0.5) / 40)) * p.len / 40; return t; };
// Rise (or fall) h metres: the two bends, and the steady slope between them takes the rest.
// A short one gets a gentler slope, so its two bends fit in it.
function slope(kind, h, a, R1, R2) {
  let th, b1, b2;
  for (; ; a -= 2) {
    th = Math.sign(h) * a * deg; b1 = bend(0, th, R1); b2 = bend(th, 0, R2);
    if (Math.abs(partRise(b1) + partRise(b2)) <= Math.abs(h) * 0.9 || a <= 8) break;
  }
  const rest = h - partRise(b1) - partRise(b2);
  return chain(kind, [b1, hold(th, rest / Math.sin(th)), b2]);
}
const lift = (h, a = 30) => slope('lift', h, a, 10, 14);
const drop = (h, a = 50) => slope('drop', -h, a, 15, 13);
const climb = (h, a = 30) => slope('climb', h, a, 13, 18);
// Up h, over a crest of radius Rc, down h. A tight crest throws the riders up: it has a max sign.
function hill(h, a, Rc) {
  const th = a * deg, b1 = bend(0, th, 12), top = bend(th, -th, Rc), b2 = bend(-th, 0, 12);
  const rest = Math.max(1, (h - partRise(b1) - partRise(top) / 2 - 0) / Math.sin(th));
  return chain('hill', [b1, hold(th, rest), top, hold(-th, rest), b2]);
}
// Turn `angle` degrees (+ right, - left) on radius r (tightest r in the middle), banked up to `bank`.
function curve(angle, r, bank) {
  const len = Math.abs(angle) * deg * r * 1.875, sg = Math.sign(angle);
  return piece('curve', len, {
    turn: u => angle * deg * ease(u),
    bank: u => sg * bank * deg * Math.pow(Math.sin(Math.PI * clamp(u, 0, 1)), 1.4),
  });
}
// A loop: pitch goes round once, tightest (radius r) at the top; it moves 3 m sideways so the way
// out passes beside the way in.
function loop(r) {
  const len = 2 * Math.PI * r * 1.875;
  return piece('loop', len, { pitch: u => 2 * Math.PI * ease(u), side: u => 3.2 * ease(u) });
}
// A banked spiral down h metres, turning a whole round.
function helix(h, r, dir) {
  const len = 2 * Math.PI * r * 1.25, th = Math.asin(clamp(h / (len * 0.85), 0, 0.5));
  return piece('helix', len, {
    turn: u => dir * 2 * Math.PI * ease(u),
    pitch: u => -th * plateau(u, 0.12),
    bank: u => dir * 40 * deg * plateau(u, 0.15),
  });
}
// How much a piece climbs (negative: falls).
function rise(pc) { let t = 0; for (let i = 0; i < 400; i++) t += Math.sin(pc.pitch((i + 0.5) / 400)) * pc.len / 400; return t; }

// ---- Levels ----
// Level 1 teaches: gentle hills and wide curves. Loops come from level 2, sharp airtime hills from
// 3, helices from 4, S-bends from 5; the courses get longer and the limits tighter up to level 10.
function levelPlan(level) {
  const rnd = rng(level * 7919 + 13), pick = a => a[Math.floor(rnd() * a.length)];
  const hard = clamp((level - 1) / 9, 0, 1);
  const top = 20 + Math.min(level, 8) * 1.5;
  const plan = [];
  let y = 3, heading = 0, last = '';
  const add = (...pcs) => { for (const pc of pcs) { plan.push(pc); y += rise(pc); } };
  add(straight(14), lift(top - 3), straight(3), drop(top - 5, 45 + hard * 12));
  const n = 5 + Math.min(level, 6);
  for (let i = 0; i < n; i++) {
    const kinds = ['hill', 'curve', 'curve', 'hill'];
    if (level >= 2) kinds.push('loop');
    if (level >= 3) kinds.push('air');
    if (level >= 4) kinds.push('helix');
    if (level >= 5) kinds.push('scurve');
    let k = pick(kinds);
    if (k === last) k = pick(kinds);
    last = k;
    // Keep off the ground and out of the sky.
    if (y > 16) add(drop(y - 4, 40 + hard * 15), straight(4));
    switch (k) {
      case 'hill': add(hill(5 + rnd() * (4 + hard * 5), 28 + rnd() * 10, 26 - hard * 6)); break;
      case 'air': add(hill(5 + rnd() * 4, 30 + rnd() * 10, 14 - hard * 3)); break;
      case 'curve': case 'scurve': {
        // Turn back towards the main direction when far off it, so the track never crosses itself.
        const dir = Math.abs(heading) > 50 ? -Math.sign(heading) : rnd() < 0.5 ? -1 : 1;
        const ang = dir * (60 + Math.floor(rnd() * 4) * 15), r = 26 - hard * 8 + rnd() * 8, bank = 20 + rnd() * 20;
        add(curve(ang, r, bank)); heading += ang;
        if (k === 'scurve') { add(straight(4), curve(-ang, r, bank)); heading -= ang; }
        break;
      }
      case 'loop': add(loop(8 - hard * 1.5 + rnd() * 1.5)); break;
      case 'helix': {
        if (y < 14) add(climb(16 - y, 28), straight(4));
        add(helix(9, 13 + rnd() * 4, heading > 0 ? -1 : 1));
        break;
      }
    }
    add(straight(6 + rnd() * 10));
    // A climb now and then, so a low track has somewhere to drop from again.
    if (y < 6 && rnd() < 0.3 + hard * 0.2) { const h = 8 + rnd() * 6; add(climb(h, 26 + rnd() * 8), straight(5), drop(h, 45 + hard * 10)); }
  }
  if (y > 4) add(drop(y - 3, 35));
  add(straight(12), piece('brake', 34));
  return plan;
}

// Builds the samples: position, frame (forward f, right r, up u, all banked), the felt-force
// coefficients, and which piece each belongs to.
function buildTrack(plan) {
  const S = [];
  let x = 0, y = 3, z = 0, psi = 0, side = 0;
  const pieces = [];
  for (const pc of plan) {
    const n = Math.max(2, Math.round(pc.len / DS)), s0 = S.length ? S[S.length - 1].s + DS : 0, i0 = S.length;
    const psi0 = psi;
    for (let k = 0; k < n; k++) {
      const u = k / n, phi = pc.pitch(u), ps = psi0 + pc.turn(u), bank = pc.bank(u), sd = pc.side(u);
      const hx = Math.sin(ps), hz = -Math.cos(ps);
      const c = Math.cos(phi), sn = Math.sin(phi);
      const f = [hx * c, sn, hz * c];
      let r = [Math.cos(ps), 0, Math.sin(ps)], up = [-hx * sn, c, -hz * sn];
      const cb = Math.cos(bank), sb = Math.sin(bank);
      const up2 = [up[0] * cb + r[0] * sb, up[1] * cb + r[1] * sb, up[2] * cb + r[2] * sb];
      const r2 = [r[0] * cb - up[0] * sb, r[1] * cb - up[1] * sb, r[2] * cb - up[2] * sb];
      S.push({ s: s0 + k * DS, x, y, z, f, r: r2, u: up2, piece: pieces.length, kind: pc.kind, bank });
      x += f[0] * DS + r[0] * (pc.side((k + 1) / n) - sd);
      y += f[1] * DS;
      z += f[2] * DS + r[2] * (pc.side((k + 1) / n) - sd);
      psi = ps;
    }
    psi = psi0 + pc.turn(1);
    side += pc.side(1);
    pieces.push({ kind: pc.kind, i0, i1: S.length - 1 });
  }
  // Curvature from the positions: the felt force per mass is v²·k + g·up(world) seen in the
  // car's frame, so each sample keeps a + b·v² for its vertical and sideways g.
  for (let i = 0; i < S.length; i++) {
    const a = S[Math.max(0, i - 2)], b = S[i], c = S[Math.min(S.length - 1, i + 2)];
    const h = DS * 2, k = [(a.x - 2 * b.x + c.x) / (h * h), (a.y - 2 * b.y + c.y) / (h * h), (a.z - 2 * b.z + c.z) / (h * h)];
    if (i < 2 || i > S.length - 3) k[0] = k[1] = k[2] = 0;
    b.va = b.u[1]; b.vb = (k[0] * b.u[0] + k[1] * b.u[1] + k[2] * b.u[2]) / G;
    b.sa = b.r[1]; b.sb = (k[0] * b.r[0] + k[1] * b.r[1] + k[2] * b.r[2]) / G;
  }
  // Smooth the coefficients a little: the sampled curvature is noisy where pieces join.
  for (const key of ['vb', 'sb']) {
    const v = S.map(o => o[key]);
    for (let i = 0; i < S.length; i++) {
      let t = 0, n = 0;
      for (let j = Math.max(0, i - 3); j <= Math.min(S.length - 1, i + 3); j++) { t += v[j]; n++; }
      S[i][key] = t / n;
    }
  }
  // Each sample's allowed speed²: vertical g = va + vb·w ≥ LIFT_OFF, |sa + sb·w| ≤ SIDE_MAX.
  for (const o of S) {
    let lo = 0, hi = Infinity;
    const lim = (a, b, min) => {   // a + b·w ≥ min
      if (Math.abs(b) < 1e-6) { if (a < min) hi = -1; return; }
      const w = (min - a) / b;   // w in (m/s)²
      if (b > 0) lo = Math.max(lo, w); else hi = Math.min(hi, w);
    };
    lim(o.va, o.vb, LIFT_OFF + 0.08);
    lim(o.sa, o.sb, -(SIDE_MAX - 0.08));
    lim(-o.sa, -o.sb, -(SIDE_MAX - 0.08));
    o.wlo = lo; o.whi = hi;
  }
  const track = { S, pieces, len: S[S.length - 1].s, finish: S[pieces[pieces.length - 1].i0].s };
  track.zones = zones(track);
  return track;
}

// The places worth a sign: a run of samples whose speed limit bites (max under 110 km/h, or a
// minimum above 0). The sign's number is the speed at the zone's start that keeps every sample of
// it inside its limits, if the car only rolls (gravity in, a little friction out).
function zones(track) {
  const S = track.S, out = [];
  const tight = o => o.whi < 30 * 30 || o.wlo > 1;
  for (let i = 0; i < S.length; i++) {
    if (!tight(S[i]) || S[i].kind === 'lift' || S[i].kind === 'brake') continue;
    let j = i;
    while (j + 1 < S.length && (tight(S[j + 1]) || (j + 8 < S.length && tight(S[j + 8]) && S[j + 1].piece === S[i].piece))) j++;
    const y0 = S[i].y;
    let wmax = Infinity, wmin = 0;
    for (let k = i; k <= j; k++) {
      const drop = 2 * G * (S[k].y - y0), loss = 1.4 * (S[k].s - S[i].s);
      if (S[k].whi < 30 * 30) wmax = Math.min(wmax, S[k].whi + drop + loss * 0.6);
      if (S[k].wlo > 1) wmin = Math.max(wmin, S[k].wlo + drop + loss);
    }
    const z = { i0: i, i1: j, s0: S[i].s, s1: S[j].s, kind: S[i].kind };
    if (wmin > 1) z.min = Math.ceil(Math.sqrt(wmin) * 3.6 / 5) * 5 + 5;
    if (wmax < 30 * 30) z.max = Math.floor(Math.sqrt(Math.max(0, wmax)) * 3.6 / 5) * 5;
    if (z.min && z.max && z.max < z.min) z.max = undefined;
    if (z.min || z.max) {
      const prev = out[out.length - 1];
      // Two zones close together read as one sign: keep the stricter numbers.
      if (prev && z.s0 - prev.s1 < 20) {
        prev.i1 = z.i1; prev.s1 = z.s1;
        if (z.max) prev.max = prev.max ? Math.min(prev.max, z.max) : z.max;
        if (z.min) prev.min = Math.max(prev.min || 0, z.min);
      } else out.push(z);
    }
    i = j;
  }
  return out;
}

// The sample at distance s, and a point between samples.
function at(track, s) {
  const S = track.S, i = clamp(Math.floor(s / DS), 0, S.length - 2), t = clamp(s / DS - i, 0, 1);
  return { a: S[i], b: S[i + 1], t, i };
}
function lerpS(track, s, key) { const p = at(track, s); return p.a[key] + (p.b[key] - p.a[key]) * p.t; }

// ---- One car on the track ----
function newCar() {
  return { s: 4, v: 0, energy: 1, boost: false, brake: false, t: 0, over: 0, gv: 1, gs: 0, fin: null,
    derail: null, check: 4, took: new Set(), warn: 0 };
}

// Rolls the car dt seconds. Returns what happened: 'derail' (and why), 'finish', 'pickup' or null.
function rideStep(track, car, dt) {
  if (car.fin !== null) {
    // Past the line: the brakes stop it in the station.
    car.v = Math.max(0, car.v - 6 * dt);
    car.s = Math.min(track.len - 1, car.s + car.v * dt);
    return null;
  }
  car.t += dt;
  const p = at(track, car.s), o = p.a, kind = o.kind;
  // Along the slope: f·(0, -g, 0).
  let a = -G * o.f[1] - 0.12 - 0.0012 * car.v * car.v * Math.sign(car.v);
  let used = false;
  if (kind === 'lift' || (kind === 'straight' && car.s < 16)) {
    // The station and the chain: pulled up at an even pace.
    if (car.v < LIFT_V) { car.v = LIFT_V; a = Math.max(a, 0); }
  } else {
    if (car.boost && car.energy > 0) { a += BOOST_A; car.energy = Math.max(0, car.energy - ENERGY_USE * dt); used = true; }
    if (car.brake && car.v > 0) a -= BRAKE_A;
  }
  if (!used) car.energy = Math.min(1, car.energy + (Math.abs(car.v) < 2.5 ? 0.45 : ENERGY_BACK) * dt);
  const v0 = car.v;
  car.v += a * dt;
  if (car.brake && v0 > 0 && car.v < 0 && kind !== 'lift') car.v = 0;
  car.s = clamp(car.s + car.v * dt, 0, track.len - 1);
  // The forces the riders feel.
  const w = car.v * car.v;
  car.gv = o.va + o.vb * w;
  car.gs = o.sa + o.sb * w;
  const bad = car.gv < LIFT_OFF ? 'air' : Math.abs(car.gs) > SIDE_MAX ? 'side' : null;
  // How close to a limit, 0..1, for the shaking and the warning sound.
  car.warn = Math.max(clamp((LIFT_OFF + 0.6 - car.gv) / 0.6, 0, 1), clamp((Math.abs(car.gs) - SIDE_MAX + 0.45) / 0.45, 0, 1));
  car.over = bad ? car.over + dt : 0;
  if (bad && car.over > GRACE) return { what: 'derail', why: o.kind === 'loop' && o.u[1] < 0 ? 'loop' : bad };
  // A safe place to come back to: the start of the piece before a zone, never inside one.
  const z = track.zones.find(q => car.s >= q.s0 - SIGN_AHEAD - 5 && car.s <= q.s1);
  if (!z && car.v > 0) car.check = car.s;
  for (const pk of track.pickups) {
    if (!car.took.has(pk.id) && Math.abs(pk.s - car.s) < 1.2) { car.took.add(pk.id); car.energy = Math.min(1, car.energy + 0.4); return { what: 'pickup' }; }
  }
  if (car.s >= track.finish) { car.fin = car.t; return { what: 'finish' }; }
  return null;
}

// Back on the track after a derail: at the last safe place, rolling.
function respawn(track, car) {
  car.s = car.check;
  car.v = 7;
  car.over = 0;
  car.energy = Math.max(car.energy, 0.5);
}

// The computer's driving: looks 60 m ahead and brakes when, rolling on, it would pass a place too
// fast, boosts when it would reach a loop too slow, and otherwise boosts while it has energy.
// `skill` under 1 keeps a wider margin (a slower, safer rider).
function botStep(track, car, dt, skill = 1) {
  const S = track.S, i0 = Math.floor(car.s / DS), y = lerpS(track, car.s, 'y'), w = car.v * car.v;
  let fast = false, slow = false;
  for (let i = i0 + 1; i < Math.min(S.length, i0 + 120); i += 2) {
    const o = S[i], roll = w + 2 * G * (y - o.y) - (0.24 + 0.0024 * w) * (o.s - car.s);
    if (o.whi < Infinity && roll > o.whi * 0.86 * skill) fast = true;
    if (o.wlo > 1 && roll < o.wlo * 1.2 + 20) slow = true;
  }
  car.brake = fast && !slow && car.v > 3;
  car.boost = !car.brake && (!fast || car.v < 3) && (slow || car.energy > 0.15 || car.v < 3);
  return rideStep(track, car, dt);
}

// ---- The level as a whole: track, pickups, the computer's time for the stars ----
const levels = {};
function makeLevel(level) {
  if (levels[level]) return levels[level];
  const track = buildTrack(levelPlan(level));
  // Energy pickups: on low, gentle stretches every 110 m or so.
  const rnd = rng(level * 31 + 7);
  track.pickups = [];
  let next = 90;
  for (const o of track.S) {
    if (o.s < next || o.kind === 'lift' || o.kind === 'brake' || o.s > track.finish - 20) continue;
    if (track.zones.some(z => o.s > z.s0 - SIGN_AHEAD && o.s < z.s1 + 5)) continue;
    track.pickups.push({ id: track.pickups.length, s: o.s });
    next = o.s + 90 + rnd() * 60;
  }
  // The computer rides it once: its time sets the stars.
  const car = newCar();
  let falls = 0;
  for (let k = 0; k < 400 * 60 && car.fin === null; k++) {
    const e = botStep(track, car, 1 / 60);
    if (e && e.what === 'derail') { falls++; respawn(track, car); }
  }
  track.ideal = car.fin ?? 999;
  track.botFalls = falls;
  return (levels[level] = track);
}

function starsFor(track, t) { return t <= track.ideal * 1.08 ? 3 : t <= track.ideal * 1.3 ? 2 : 1; }

function fmtTime(t) {
  if (t === null || t === undefined) return '–';
  const m = Math.floor(t / 60), s = t - m * 60;
  return m + '.' + (s < 10 ? '0' : '') + s.toFixed(1);
}

// ---- The game: menu, ride, end ----
const game = {
  mode: 'menu',          // menu | count | ride | crash | done | netwait
  level: 1, track: null, car: null, count: 0, crashT: 0, crashWhy: '', result: null, demo: 0,
};
let maxLevel = Math.max(1, +load('taso', 1) || 1);
game.level = clamp(+load('valittu', maxLevel) || 1, 1, maxLevel);

function bests() { return load('ajat', {}); }
function starsOf() { return load('tahdet', {}); }

function setLevel(n) {
  game.level = clamp(n, 1, maxLevel);
  if (!net) save('valittu', game.level);
  game.track = makeLevel(game.level);
  game.car = newCar();
  game.demo = 0;
  if (window.AiPelitScores) AiPelitScores.board('taso-' + game.level, 'Taso ' + game.level);
  window.dispatchEvent(new Event('rata'));
  menuText();
}

function startRide() {
  unlockAudio();
  game.car = newCar();
  game.mode = 'count'; game.count = 3; game.result = null;
  document.body.classList.add('riding');
  show(null);
  beep(440, 0.15, 'triangle', 0.08);
}

function finishRide() {
  game.mode = 'done';
  const t = game.car.fin, tr = game.track, st = starsFor(tr, t);
  const B = bests(), S = starsOf(), lv = game.level, prev = B[lv], record = prev === undefined || t < prev;
  // A race with friends is saved once, however often its end is heard.
  if (!net || RM.once(net.round)) {
    if (record) { B[lv] = Math.round(t * 100) / 100; save('ajat', B); }
    if (st > (S[lv] || 0)) { S[lv] = st; save('tahdet', S); }
    if (lv === maxLevel) { maxLevel++; save('taso', maxLevel); }
    if (window.AiPelitScores) AiPelitScores.submit(Math.round(t * 10) / 10);
  }
  game.result = { t, stars: st, record, prev };
  beep(784, 0.18, 'triangle', 0.1); setTimeout(() => beep(1047, 0.3, 'triangle', 0.1), 160);
  if (net) { const k = meK(); k.fin = Math.round(t * 100) / 100; k.s = game.car.s; if (RM.isHost) arrive(k); net.sendT = 0; toast('Maalissa! Odotetaan muita…'); return; }
  endScreen();
}

function step(dt) {
  if (net && RM.paused) return;   // a phone in the race is away: everyone waits for it
  const car = game.car;
  if (game.mode === 'menu' || game.mode === 'netwait') {
    // Behind the menu the car rides the track slowly, so the player sees what is coming.
    game.demo = (game.demo + dt * 9) % Math.max(1, game.track.finish - 20);
    car.s = 20 + game.demo; car.v = 9;
  } else if (game.mode === 'count') {
    game.count -= dt;
    const was = Math.ceil(game.count + dt);
    if (Math.ceil(game.count) !== was && game.count > 0) beep(440, 0.12, 'triangle', 0.08);
    if (game.count <= 0 && (!net || RM.isHost)) go();
  } else if (game.mode === 'ride') {
    readInput(car);
    const n = Math.max(1, Math.ceil(dt / (1 / 120))), h = dt / n;
    for (let i = 0; i < n && game.mode === 'ride'; i++) {
      const e = auto ? botStep(game.track, car, h) : rideStep(game.track, car, h);
      if (!e) continue;
      if (e.what === 'derail') crash(e.why);
      else if (e.what === 'finish') finishRide();
      else if (e.what === 'pickup') { beep(988, 0.08, 'square', 0.06); setTimeout(() => beep(1319, 0.12, 'square', 0.06), 70); }
    }
    sound(car);
  } else if (game.mode === 'crash') {
    game.crashT += dt;
    car.t += dt;   // the clock runs on while the car is put back
    if (game.crashT > 1.6) { respawn(game.track, car); game.mode = 'ride'; }
  } else if (game.mode === 'done') {
    rideStep(game.track, car, dt);
  }
  if (net) netTick(dt);
  hud();
}

function go() {
  game.mode = 'ride';
  beep(880, 0.25, 'triangle', 0.1);
  if (net) { net.phase = 'run'; net.clock = 0; }
}

function crash(why) {
  game.mode = 'crash'; game.crashT = 0; game.crashWhy = why;
  game.crashFrom = { s: game.car.s, v: game.car.v };
  toast(why === 'loop' ? 'Liian hiljaa silmukkaan!' : why === 'air' ? 'Liian kovaa mäen harjalle!' : 'Liian kovaa mutkaan!');
  noise(0.5);
}

// ---- Input: two held buttons, any number of fingers ----
const held = { boost: new Set(), brake: new Set() };
let auto = false;   // tests and the demo: the computer drives
function readInput(car) {
  if (auto) return;
  car.boost = held.boost.size > 0;
  car.brake = held.brake.size > 0;
}
function bindHold(el, which) {
  const on = e => { e.preventDefault(); unlockAudio(); held[which].add(e.pointerId); el.classList.add('down'); el.setPointerCapture?.(e.pointerId); };
  const off = e => { held[which].delete(e.pointerId); if (!held[which].size) el.classList.remove('down'); };
  el.addEventListener('pointerdown', on);
  el.addEventListener('pointerup', off);
  el.addEventListener('pointercancel', off);
  el.addEventListener('lostpointercapture', off);
  el.addEventListener('contextmenu', e => e.preventDefault());
}

// ---- Screens and HUD ----
function show(id) {
  for (const s of document.querySelectorAll('.screen')) s.classList.toggle('hidden', s.id !== id);
  const riding = id === null;
  $('hud').classList.toggle('hidden', !riding);
  $('ohjaimet').classList.toggle('hidden', !riding);
  document.body.classList.toggle('riding', riding);
}
function starText(n) { return '★'.repeat(n) + '☆'.repeat(3 - n); }
function menuText() {
  const lv = game.level, b = bests()[lv], st = starsOf()[lv] || 0;
  $('taso').textContent = 'Taso ' + lv;
  $('edel').disabled = lv <= 1 || !!net;
  $('seur').disabled = lv >= maxLevel || !!net;
  $('ennatys').textContent = b !== undefined ? `${starText(st)}  Paras aika ${fmtTime(b)}` : lv === 1 ? 'Aja rata maaliin, niin seuraava taso aukeaa.' : 'Uusi rata!';
}
function endScreen() {
  const r = game.result;
  $('loppu-otsikko').textContent = 'Maalissa!';
  $('aika').textContent = fmtTime(r.t);
  $('tahdet').textContent = starText(r.stars);
  $('loppu-teksti').textContent = r.record ? (r.prev === undefined ? 'Ensimmäinen aikasi tällä radalla!' : 'Uusi ennätys!') : `Ennätys ${fmtTime(r.prev)}`;
  $('seuraava').classList.toggle('hidden', game.level >= maxLevel);
  $('uudestaan').classList.remove('hidden');
  $('huoneeseen').classList.add('hidden');
  $('tulokset').innerHTML = '';
  show('loppu');
}

let lastHud = '';
function hud() {
  if (game.mode !== 'ride' && game.mode !== 'crash' && game.mode !== 'count' && game.mode !== 'done') return;
  const car = game.car, tr = game.track;
  const z = tr.zones.find(q => q.s1 >= car.s && q.s0 - car.s < 120);
  let sign = '';
  if (z) {
    const d = Math.max(0, Math.round(z.s0 - car.s));
    sign = (z.min ? `<b class="min">${z.min}</b>` : '') + (z.max ? `<b class="max">${z.max}</b>` : '') + (d > 0 ? `<span>${d} m</span>` : '');
  }
  const v = Math.max(0, kmh(car.v));
  // Red while the speed is wrong for the sign just ahead (the sign's number is for its start).
  const near = z && car.s >= z.s0 - 25 && car.s <= z.s0 + 3;
  const slow = near && z.min && v < z.min, fast = near && z.max && v > z.max;
  const key = [v, sign, slow, fast, Math.floor(car.t * 10), Math.round(car.energy * 50), game.mode, net && net.order].join('|');
  if (key === lastHud) return;
  lastHud = key;
  $('nopeus').innerHTML = `${v}<small> km/h</small>`;
  $('nopeus').className = slow || fast ? 'huono' : '';
  $('merkki').innerHTML = sign;
  $('kello').textContent = fmtTime(car.fin ?? car.t);
  $('vauhti').style.setProperty('--e', car.energy.toFixed(3));
  $('vauhti').classList.toggle('tyhja', car.energy < 0.03);
  $('lahto').textContent = game.mode === 'count' ? Math.max(1, Math.ceil(game.count)) : '';
  $('kisa').innerHTML = net && net.order ? net.order : '';
}

let toastT = null;
function toast(text) {
  const t = $('toast');
  t.textContent = text;
  t.classList.remove('hidden');
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.add('hidden'), 1600);
}

// ---- Sound: Web Audio only after the first tap ----
let ac = null, hum = null;
function unlockAudio() {
  if (!ac) { try { ac = new AudioContext(); } catch (e) { ac = null; } }
  ac?.resume?.();
}
function beep(f, len, type = 'sine', vol = 0.08) {
  if (!ac) return;
  const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
  o.type = type; o.frequency.value = f;
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + len);
  o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + len + 0.02);
}
function noise(len) {
  if (!ac) return;
  const n = ac.sampleRate * len, buf = ac.createBuffer(1, n, ac.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const src = ac.createBufferSource(), g = ac.createGain();
  src.buffer = buf; g.gain.value = 0.25; src.connect(g); g.connect(ac.destination); src.start();
}
// The wheels' rumble rises with the speed; the chain clacks on the lift; a whine warns of a limit.
let clackT = 0;
function sound(car) {
  if (!ac) return;
  if (!hum) {
    const o = ac.createOscillator(), g = ac.createGain(), w = ac.createOscillator(), wg = ac.createGain();
    o.type = 'sawtooth'; g.gain.value = 0; o.connect(g); g.connect(ac.destination); o.start();
    w.type = 'square'; wg.gain.value = 0; w.frequency.value = 1400; w.connect(wg); wg.connect(ac.destination); w.start();
    hum = { o, g, wg };
  }
  const t = ac.currentTime, v = Math.abs(car.v);
  hum.o.frequency.setTargetAtTime(40 + v * 4, t, 0.1);
  hum.g.gain.setTargetAtTime(game.mode === 'ride' ? Math.min(0.05, v * 0.002) : 0, t, 0.1);
  hum.wg.gain.setTargetAtTime(game.mode === 'ride' && car.warn > 0.3 ? 0.015 * car.warn : 0, t, 0.05);
  const o = at(game.track, car.s).a;
  if (o.kind === 'lift' && (clackT -= 1 / 60) <= 0) { clackT = 0.18; beep(180, 0.03, 'square', 0.05); }
}
function quiet() { if (hum && ac) { hum.g.gain.setTargetAtTime(0, ac.currentTime, 0.05); hum.wg.gain.setTargetAtTime(0, ac.currentTime, 0.05); } }

// ---- Racing friends ----
// Everyone in the room rides the host's level at once, each phone its own car; the others show as
// trains in their own colours on the same track (they ride through each other). The host runs the
// start, the end (everyone in, or 40 s after the first) and the computer's car for a friend who is
// away, and sends the race ten times a second. The first to the finish wins.
const RM = window.AiPelitRooms;
const COLORS = ['#e2574c', '#3f8ad8', '#3fa65a', '#e0a526', '#9a5cc6', '#e07ab0'];
const LATE = 40;
let net = null, lastEnd = null;
const meK = () => net.cars.find(k => k.kind === 'me');
const r2 = n => Math.round(n * 100) / 100;

function netStart(s) {
  net = { round: s.round, cfg: null, phase: 'cd', sendT: 0, clock: 0, firstFin: null, res: null, order: '',
    soloLevel: net ? net.soloLevel : game.level, heard: false,
    cars: s.players.map((p, i) => ({ id: p.id, name: p.name, color: COLORS[i % COLORS.length], kind: p.id === RM.me ? 'me' : 'net',
      s: 4, v: 0, fin: null, at: null })) };
  show(null);
  if (s.host && !s.over) { net.cfg = { level: game.level }; netLevel(); startRide(); }
  else { game.mode = 'netwait'; $('odota').classList.remove('hidden'); document.body.classList.add('riding'); }
  window.dispatchEvent(new Event('rata'));
}
function netLevel() { setLevel(net.cfg.level); }
const pack = k => [r2(k.s), r2(k.v), k.fin, k.at, k.kind === 'cpu' || k.handback ? 1 : 0, k.cpuFin ? 1 : 0];
function synced(k) {
  if (k.kind === 'me') { k.s = game.car.s; k.v = game.car.v; }
  return k;
}
function hostState() {
  return { t: 's', round: net.round, cfg: net.cfg, ph: net.phase, cd: r2(game.count || 0), clock: r2(net.clock), c: net.cars.map(k => pack(synced(k))) };
}
function arrive(k) {
  if (k.fin === null || k.at !== null) return;
  k.at = r2(net.clock);
  if (net.firstFin === null) net.firstFin = net.clock;
}
function netTick(dt) {
  if (net.phase === 'run') net.clock += dt;
  for (const k of net.cars) {
    if (k.kind === 'me') continue;
    if (k.kind === 'cpu' && RM.isHost) {
      if (net.phase === 'run' && k.fin === null) {
        const e = botStep(game.track, k.car, dt, 0.97);
        if (e && e.what === 'derail') respawn(game.track, k.car);
        k.s = k.car.s; k.v = k.car.v;
        if (k.car.fin !== null) { k.fin = r2(k.car.fin); k.cpuFin = true; arrive(k); }
      }
    } else if (net.phase === 'run' && k.fin === null) k.s = Math.min(game.track.len - 1, k.s + k.v * dt);
  }
  // The places, for the HUD: finished by arrival, the rest by how far they are.
  const list = net.cars.map(synced).slice().sort((a, b) => (a.fin === null) - (b.fin === null) || (a.fin !== null ? (a.at ?? a.fin) - (b.at ?? b.fin) : b.s - a.s));
  net.order = list.map((k, i) => `<span style="color:${k.color}">${i + 1}. ${k.kind === 'me' ? 'Sinä' : esc(k.name)}</span>`).join('');
  net.sendT -= dt;
  if (RM.isHost) {
    if (net.phase === 'run' && (net.cars.every(k => k.fin !== null) || (net.firstFin !== null && net.clock > net.firstFin + LATE))) {
      const m = { t: 'end', round: net.round, res: standings() };
      RM.send(hostState());
      RM.deliver(m);
      RM.endRound();
      netEnd(m.res);
      return;
    }
    if (net.sendT <= 0) { net.sendT = 0.1; RM.send(hostState()); }
    return;
  }
  if ((game.mode === 'ride' || game.mode === 'crash' || game.mode === 'done') && net.sendT <= 0 && !net.res) {
    net.sendT = 0.1; RM.send({ t: 'p', round: net.round, c: pack(synced(meK())) });
  }
}
function guestState(m) {
  const first = !net.heard;
  net.heard = true;
  if (!net.cfg) { net.cfg = m.cfg; netLevel(); }
  net.phase = m.ph; net.clock = m.clock;
  m.c.forEach((a, i) => {
    const k = net.cars[i];
    if (!k) return;
    if (k.kind !== 'me') { k.s = a[0]; k.v = a[1]; k.fin = a[2]; k.at = a[3]; return; }
    k.at = a[3] ?? k.at;
    // Back after a reload, or the computer rode for me while I was away: carry on from there.
    if ((first && m.ph === 'run' && a[0] > game.car.s + 5) || (a[4] && game.mode === 'ride')) {
      game.car.s = a[0]; game.car.v = Math.max(5, a[1]); game.car.t = m.clock; game.car.check = a[0];
    }
    if (a[2] !== null && a[5] && game.car.fin === null) {
      // The computer took me to the finish: my place stands, but it is not my time.
      game.car.fin = a[2]; game.mode = 'done'; game.result = { t: a[2], stars: 0, cpu: true };
    }
  });
  $('odota').classList.add('hidden');
  if (game.mode === 'netwait') {
    if (m.ph === 'cd') { startRide(); game.count = m.cd; }
    else if (m.ph === 'run') { startRide(); game.mode = 'ride'; game.car.t = Math.max(game.car.t, m.clock); }
  }
  if (game.mode === 'count') game.count = m.cd;
  if (m.ph === 'run' && game.mode === 'count') { go(); game.car.t = m.clock; }
}
function cpuTakes(k) {
  k.kind = 'cpu';
  k.car = Object.assign(newCar(), { s: k.s, v: Math.max(5, k.v), t: net.clock, check: k.s });
}
function standings() {
  return net.cars.map(synced).slice().sort((a, b) => (a.fin === null) - (b.fin === null) || (a.fin !== null ? (a.at ?? a.fin) - (b.at ?? b.fin) : b.s - a.s))
    .map(k => ({ id: k.id, name: k.name, fin: k.fin, color: k.color }));
}
function netEnd(res) {
  if (!net || net.res) return;
  net.res = res; net.phase = 'done';
  if (RM.isHost) lastEnd = { t: 'end', round: net.round, res };
  if (game.mode !== 'done') { game.mode = 'done'; game.result = game.result || { t: null, stars: 0 }; }
  quiet();
  const i = res.findIndex(o => o.id === RM.me), r = res[i], mine = game.result && !game.result.cpu ? game.result : null;
  $('loppu-otsikko').textContent = i === 0 ? 'Voitit kisan!' : i > 0 ? `${i + 1}. sija` : 'Kisa päättyi';
  $('aika').textContent = r && r.fin !== null ? fmtTime(r.fin) : 'Et ehtinyt maaliin';
  $('tahdet').textContent = mine && mine.t !== null ? starText(mine.stars) : '';
  $('loppu-teksti').textContent = game.result && game.result.cpu ? 'Tietokone ajoi puolestasi maaliin.' : mine && mine.record ? 'Uusi ennätys tällä radalla!' : '';
  $('tulokset').innerHTML = res.map((o, j) => `<li style="color:${o.color}">${j + 1}. ${o.id === RM.me ? 'Sinä' : esc(o.name)} <b>${o.fin === null ? '–' : fmtTime(o.fin)}</b></li>`).join('');
  $('seuraava').classList.add('hidden');
  $('uudestaan').classList.add('hidden');
  $('huoneeseen').classList.remove('hidden');
  show('loppu');
}
function backRoom() {
  const res = net.res, i = res.findIndex(o => o.id === RM.me), r = res[i];
  RM.note(res.map((o, j) => `${j + 1}. ${o.id === RM.me ? 'Sinä' : o.name} ${o.fin === null ? '–' : fmtTime(o.fin)}`).join(' · '));
  const text = i < 0 ? 'Kisa päättyi' : r.fin === null ? 'Et ehtinyt maaliin' : `${i + 1}. sija · ${fmtTime(r.fin)}`;
  toSolo();
  RM.backToRoom(text, i === 0 ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  const lv = net.soloLevel;
  net = null;
  quiet();
  setLevel(lv);
  game.mode = 'menu';
  $('odota').classList.add('hidden');
  show('menu');
  roomControls();
}
const esc = s => String(s).replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));

// The host's level, in the room under the players; the others see who picks.
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#vr-room{display:flex;gap:8px;align-items:center;justify-content:center;margin:2px 0 4px}' +
      '#aipr #vr-room button{font-size:15px;padding:7px 12px}#aipr #vr-room button:disabled{opacity:.35}#vr-room b{min-width:74px;font-size:17px}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'vr-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      setLevel(game.level + +b.dataset.d);
      roomControls();
    });
    RM.extra(roomEl);
  }
  if (RM.isHost) {
    roomEl.innerHTML = `<button data-d="-1"${game.level > 1 ? '' : ' disabled'}>‹</button><b>Taso ${game.level}</b><button data-d="1"${game.level < maxLevel ? '' : ' disabled'}>›</button>`;
  } else {
    const h = RM.members.find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Radan valitsee ${h ? '👑 ' + esc(h.name) : 'huoneen tekijä'}.</p>`;
  }
}
if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || m.round !== net.round) return;
    if (RM.isHost) {
      const k = net.cars.find(o => o.id === from);
      if (!k || k.kind !== 'net' || m.t !== 'p') return;
      // Given back by the computer: the phone's own car counts again once it has caught up.
      if (k.handback && m.c[0] < k.s - 1) return;
      k.handback = false;
      k.s = m.c[0]; k.v = m.c[1]; k.fin = m.c[2];
      arrive(k);
      return;
    }
    if (m.t === 's') guestState(m);
    if (m.t === 'end') netEnd(m.res);
  });
  RM.on('hello', id => {
    if (net && !net.res) RM.send(hostState(), id);
    else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('continue', ids => { if (net) net.cars.forEach(k => { if (ids.includes(k.id) && k.kind === 'net') cpuTakes(k); }); });
  RM.on('back', id => { if (net) net.cars.forEach(k => { if (k.id === id && k.kind === 'cpu') { k.kind = 'net'; k.handback = true; } }); });
  RM.on('lobby', toSolo);
  RM.on('leave', toSolo);
  RM.on('menu', toSolo);
  RM.on('peers', roomControls);
}

// ---- Wiring ----
function wire() {
  $('aja').addEventListener('click', startRide);
  $('edel').addEventListener('click', () => setLevel(game.level - 1));
  $('seur').addEventListener('click', () => setLevel(game.level + 1));
  $('uudestaan').addEventListener('click', startRide);
  $('seuraava').addEventListener('click', () => { setLevel(game.level + 1); startRide(); });
  $('valikkoon').addEventListener('click', () => { if (net && net.res) return backRoom(); quiet(); game.mode = 'menu'; setLevel(game.level); show('menu'); });
  $('huoneeseen').addEventListener('click', backRoom);
  $('kaverit').addEventListener('click', () => { unlockAudio(); RM && RM.open(); roomControls(); });
  if (!RM) $('kaverit').classList.add('hidden');
  bindHold($('vauhti'), 'boost');
  bindHold($('jarru'), 'brake');
  setLevel(game.level);
  show('menu');
  let last = performance.now();
  // The rules run on their own timer, so the round goes on even where 3D cannot be drawn.
  (function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    step(dt);
    requestAnimationFrame(frame);
  })(last);
}
document.addEventListener('DOMContentLoaded', wire);
