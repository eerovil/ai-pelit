'use strict';
// Seittisankari v1: playing with friends, 2–8 phones in one room (#529, design and its review on
// the issue).
//
// Each phone moves its own hero (so the stick and the web answer at once) and sends where it is
// 10 times a second, stamped with its own AiPelitSulava.now(). The host's phone runs the round:
// the clock `rt`, the balloons and who took each, who reached the top, the end. 10 times a second
// it sends one snapshot `s` with the clock, the balloons taken and every hero (each with the stamp
// of the phone that moved it); every phone draws the others through lib/sulava-1.
//
// Modes, picked by the host on the room screen: Kilpa huipulle (first onto the tower's roof),
// Ilmapallojahti (most of 20 balloons in 2 min), Vapaa kaupunki (no goal, ended by the host).
//
// What decides (design review):
// - While rooms.js says `paused`, no phone moves its hero and the host's clock stands; a claim
//   that reaches the host then is refused with `nack`.
// - One clock: the host's `rt` (paused time left out) gives the winner and every time shown.
// - A balloon goes to the first claim the host grants; a claim for a taken one is answered with
//   the `got` naming its owner, any other refused claim with `nack`. A guest resends a balloon
//   claim every RESEND s until a `got` or `nack`; a `nack` for a balloon still free re-arms it, so
//   the hero still touching it (or touching it next) claims it again.
// - A guest claims the top every 0.5 s while it stands on the tower's roof, until the round ends.
// - Once the host has decided the end it ignores every later claim (answered `nack`, over), and
//   `win` carries the final counts and times; a `got` after `win` is dropped.
const RM = window.AiPelitRooms;
const SU = window.AiPelitSulava;
const NET_MODES = [
  { key: 'kilpa', name: 'Kilpa huipulle', note: 'Ensimmäinen tornin katolle voittaa', limit: 180 },
  { key: 'pallot', name: 'Ilmapallojahti', note: 'Eniten ilmapalloja 2 minuutissa', limit: 120 },
  { key: 'vapaa', name: 'Vapaa kaupunki', note: 'Ei tehtävää: heilukaa yhdessä', limit: 0 },
];
const HERO_COLS = ['#1fb5a8', '#ff6b6b', '#ffd166', '#7b8cff', '#ff9f43', '#c77dff', '#4dd2ff', '#9be15d'];
const N_BALLOONS = 20, RESEND = 1.5, TOP_EVERY = 0.5, TOP_NEAR = 15;
const r2 = n => Math.round(n * 100) / 100;
const stampNow = () => SU ? SU.now() : performance.now() / 1000;
let net = null, netMode = 'kilpa', lastEnd = null, hostSeq = 0;

// Fair starts for the race: around the tower at the same distance, snapped onto a street.
function startSpot(i, n, mode) {
  const t = roofTop(T_BOX), a = (i / Math.max(2, n)) * TAU + 0.4;
  const rad = mode === 'kilpa' ? 95 : 30;
  let x = t.x + Math.cos(a) * rad, z = t.z + Math.sin(a) * rad;
  const snap = v => Math.round((v - 20) / LOT) * LOT + 20;   // street lines sit at lotX(k) + 20
  if (Math.abs(snap(x) - x) < Math.abs(snap(z) - z)) x = snap(x); else z = snap(z);
  return { x: clamp(x, -EDGE, EDGE), z: clamp(z, -EDGE, EDGE), yaw: Math.atan2(t.x - x, t.z - z) };
}
const onTop = h => h.st === 'ground' && h.y >= T_BOX.h - 0.1 && h.x > T_BOX.x0 - 1 && h.x < T_BOX.x1 + 1 && h.z > T_BOX.z0 - 1 && h.z < T_BOX.z1 + 1;

// ---- Smooth drawing of the others ----
function trackOf(p) {
  if (!p.tr && SU) p.tr = SU.track({ keys: ['x', 'y', 'z', 'f'], angles: ['f'], jump: 30 });
  return p.tr;
}
// Another phone's hero as drawn this frame: a hero-shaped object for draw3d.js.
function drawnHero(p, dt) {
  const t = trackOf(p), s = t ? t.at() : null;
  const d = p.dh || (p.dh = newHero(p.x, p.y, p.z, p.f));
  const nx = s ? s.x : p.x, ny = s ? s.y : p.y, nz = s ? s.z : p.z;
  if (dt > 0) { d.vx = (nx - d.x) / dt; d.vy = (ny - d.y) / dt; d.vz = (nz - d.z) / dt; }
  d.x = nx; d.y = ny; d.z = nz; d.yaw = s ? s.f : p.f;
  d.st = p.st; d.anchor = p.a; d.nx = -Math.sin(d.yaw); d.nz = -Math.cos(d.yaw);
  return d;
}

// ---- The round's state, the same shape on every phone ----
function newNet(s) {
  return { round: s.round, mode: netMode, seed: 1, rt: 0, over: false, res: null, players: [], taken: [], balloons: null,
    me: null, sendT: 0, lastSeq: -1, pend: new Map(), topT: 0, ready: false };
}
function playerOf(id) { return net.players.find(p => p.id === id); }
function setupBalloons() {
  net.balloons = net.mode === 'pallot' ? balloonsNear(0, 0, N_BALLOONS, net.seed, 210) : null;
  net.taken = net.balloons ? net.balloons.map(() => '') : [];
}
function netStart(s) {
  net = newNet(s);
  hideAll(); stick = null; webPtr = null; lookPtr = null; result = null;
  world = null;
  if (s.host && !s.over) {
    net.mode = netMode; net.seed = (Date.now() % 1e9) >>> 0;
    net.players = s.players.slice(0, 8).map((p, i) => {
      const sp = startSpot(i, Math.min(8, s.players.length), net.mode);
      return { id: p.id, name: p.name, col: HERO_COLS[i % HERO_COLS.length], x: sp.x, y: 0, z: sp.z, f: sp.yaw, st: 'ground', a: null, stamp: 0, top: false };
    });
    setupBalloons();
    beginLocal();
    RM.send(hostState());
  } else mode = 'netwait';
}
// This phone's own hero, from its spot in the round.
function beginLocal() {
  const p = playerOf(RM.me);
  world = { n: net.mode === 'vapaa' ? 0 : -1, M: { limit: 0, done: () => false }, t: 0, done: false, failed: false, ev: [], flag: null, cat: null, thief: null, drones: null, balloons: net.balloons };
  if (net.mode === 'kilpa') world.flag = roofTop(T_BOX);
  if (net.mode === 'vapaa') world.balloons = balloonsNear(0, 0, FREE_N, 7, 2 * EDGE - 20);   // each phone's own, as alone
  if (p) {
    world.hero = newHero(p.x, p.y, p.z, p.f);
    world.hero.st = p.y > 0.1 ? 'air' : 'ground';
    net.me = p;
  } else world.hero = newHero(0, 60, 0, 0);   // not in the round (joined late): only watches
  cam.yaw = world.hero.yaw; cam.pitch = 0.3; cam.manualT = 9;
  net.ready = true;
  mode = 'netplay';
}
function heroRow(p) {
  return [p.id, r2(p.stamp || 0), r2(p.x), r2(p.y), r2(p.z), r2(p.f), p.st[0], p.a ? [r2(p.a.x), r2(p.a.y), r2(p.a.z)] : 0];
}
function hostState() {
  return { t: 's', round: net.round, seq: ++hostSeq, mode: net.mode, seed: net.seed, rt: r2(net.rt), over: net.over,
    names: net.players.map(p => [p.id, p.name, p.col]), taken: net.taken, h: net.players.map(heroRow) };
}
const ST = { g: 'ground', a: 'air', w: 'wall', s: 'swing' };
function readRow(p, a) {
  p.stamp = +a[1] || 0; p.x = +a[2] || 0; p.y = +a[3] || 0; p.z = +a[4] || 0; p.f = +a[5] || 0;
  p.st = ST[a[6]] || 'air'; p.a = Array.isArray(a[7]) ? { x: +a[7][0], y: +a[7][1], z: +a[7][2] } : null;
}

// ---- A guest hears the host ----
function guestState(m) {
  if (net.res || !(m.seq > net.lastSeq)) return;
  net.lastSeq = m.seq;
  const first = !net.ready;
  if (first) {
    net.mode = m.mode; net.seed = m.seed;
    net.players = m.names.map(([id, name, col]) => ({ id, name, col, x: 0, y: 0, z: 0, f: 0, st: 'ground', a: null, stamp: 0 }));
  }
  // The clock: eased to the host's, taken when far off.
  const d = m.rt - net.rt;
  if (first || Math.abs(d) > 0.5) net.rt = m.rt; else net.rt += d * 0.2;
  m.h.forEach(a => {
    const p = playerOf(a[0]);
    if (!p) return;
    // My own hero: taken from the host only at the first snapshot (a reload: the last spot I sent).
    if (p.id === RM.me && !first) return;
    readRow(p, a);
    if (p.id !== RM.me) { const t = trackOf(p); if (t) t.push(p.stamp, { x: p.x, y: p.y, z: p.z, f: p.f }); }
  });
  if (first) { setupBalloons(); beginLocal(); }
  // Balloons as the host has them; a pending claim that the host now shows given is settled.
  if (net.balloons && Array.isArray(m.taken)) m.taken.forEach((o, i) => { if (o) { net.taken[i] = o; net.pend.delete(i); } });
}
function onGot(m) {
  if (net.res || !net.balloons) return;   // after the end: dropped (the `win` has the counts)
  const i = m.i | 0;
  if (i < 0 || i >= net.taken.length) return;
  net.taken[i] = String(m.id || '');
  net.pend.delete(i);
  if (m.id === RM.me) sfx('pop', { vol: 0.3, rate: 1.4 });
}
function onNack(m) {
  if (m.k === 'b') {
    // Refused but still free (a pause, or my spot had not arrived yet): re-armed, so touching it
    // claims it again (design review notes).
    net.pend.delete(m.i | 0);
  }
  // A refused top claim needs nothing: it repeats every 0.5 s while I stand there.
}

// ---- Claims: the host decides, by its own clock and its own view of every hero ----
function claim(k, i) {
  if (RM.isHost) { hostClaim(RM.me, k, i); return; }
  RM.send({ t: 'claim', round: net.round, k, i });
}
function nack(to, k, i) {
  const m = { t: 'nack', round: net.round, k, i, over: net.over };
  if (to === RM.me) onNack(m); else RM.send(m, to);
}
function hostClaim(from, k, i) {
  const p = playerOf(from);
  if (!p) return;
  if (net.over || net.res || RM.paused) return nack(from, k, i);
  if (k === 'b') {
    i = i | 0;
    if (!net.balloons || i < 0 || i >= net.balloons.length) return;
    if (net.taken[i]) {             // already someone's: say whose
      const m = { t: 'got', round: net.round, i, id: net.taken[i] };
      if (from === RM.me) onGot(m); else RM.send(m, from);
      return;
    }
    const b = net.balloons[i];
    if (Math.hypot(p.x - b.x, p.y + 0.8 - b.y, p.z - b.z) > 10) return nack(from, k, i);
    net.taken[i] = from;
    const m = { t: 'got', round: net.round, i, id: from };
    onGot(m); RM.send(m);
    if (net.taken.every(Boolean)) hostEnd();
  } else if (k === 'top') {
    if (net.mode !== 'kilpa') return;
    const t = roofTop(T_BOX);
    if (Math.hypot(p.x - t.x, p.z - t.z) > TOP_NEAR || p.y < T_BOX.h - 1) return nack(from, k, 0);
    p.top = true; p.time = net.rt;
    hostEnd(from);
  }
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || !net.ready || net.res || !world) return;
  if (RM.paused) { acc = 0; return; }   // every hero stands, the clock too
  acc += dt;
  let steps = 0;
  const me = net.me, h = world.hero;
  while (acc >= STEP && steps++ < 24) {
    acc -= STEP;
    if (me) {
      const lands0 = h.lands || 0, st0 = h.st;
      stepHero(h, input(), STEP);
      stepCam(h, STEP);
      if (h.st === 'swing' && st0 !== 'swing') sfx('suhahdus', { vol: 0.25, rate: 1.3 });
      if ((h.lands || 0) > lands0) sfx('tomahdys', { vol: 0.15 });
      if (h.jumped) { h.jumped = false; sfx('pop', { vol: 0.2 }); }
      me.x = h.x; me.y = h.y; me.z = h.z; me.f = h.yaw; me.st = h.st; me.a = h.anchor; me.stamp = stampNow();
    }
    if (net.mode !== 'vapaa') world.t += STEP;
    if (RM.isHost) {
      net.rt += STEP;
      const M = NET_MODES.find(o => o.key === net.mode);
      if (M.limit && net.rt >= M.limit) { hostEnd(); return; }
    } else net.rt += STEP;
    if (me) localClaims(STEP);
    if (net.mode === 'vapaa') stepMission(world, STEP);
  }
  if (acc > STEP) acc = 0;
  for (const [i, t] of net.pend) {        // resend a balloon claim not yet answered
    if (performance.now() - t > RESEND * 1000) { net.pend.set(i, performance.now()); claim('b', i); }
  }
  net.sendT -= dt;
  if (net.sendT > 0) return;
  net.sendT = 0.1;
  if (RM.isHost) RM.send(hostState());
  else if (me) RM.send({ t: 'p', round: net.round, h: heroRow(me) });
}
function localClaims(dt) {
  const h = world.hero;
  if (net.balloons) net.balloons.forEach((b, i) => {
    if (net.taken[i] || net.pend.has(i)) return;
    if (Math.hypot(h.x - b.x, h.y + 0.8 - b.y, h.z - b.z) < 2.4) { net.pend.set(i, performance.now()); claim('b', i); }
  });
  if (net.mode === 'kilpa' && onTop(h)) {
    net.topT -= dt;
    if (net.topT <= 0) { net.topT = TOP_EVERY; claim('top', 0); }
  } else net.topT = 0;
}
// Balloons this phone shows as gone: taken by anyone, or claimed and waiting for the answer.
function netBalloons() {
  if (!net || !net.balloons) return world ? world.balloons : null;
  net.balloons.forEach((b, i) => { b.got = !!net.taken[i] || net.pend.has(i); });
  return net.balloons;
}

// ---- The host hears a guest ----
function hostSpot(m, from) {
  const p = playerOf(from);
  if (!p || !Array.isArray(m.h) || m.h[0] !== from) return;
  readRow(p, m.h);
  p.x = clamp(p.x, -EDGE, EDGE); p.z = clamp(p.z, -EDGE, EDGE);
  const t = trackOf(p); if (t) t.push(p.stamp, { x: p.x, y: p.y, z: p.z, f: p.f });
}

// ---- The end ----
function standings() {
  const rows = net.players.map(p => ({ id: p.id, n: p.name, c: p.col,
    b: net.taken.filter(o => o === p.id).length, t: p.top ? r2(p.time) : null, y: Math.round(p.y) }));
  if (net.mode === 'pallot') rows.sort((a, b) => b.b - a.b);
  else rows.sort((a, b) => (a.t === null) - (b.t === null) || (a.t || 0) - (b.t || 0) || b.y - a.y);
  return rows;
}
function hostEnd(winner) {
  if (net.over) return;
  net.over = true;
  const res = standings();
  let win = winner || null;
  if (!win && net.mode === 'pallot' && res.length && res[0].b > 0 && !(res[1] && res[1].b === res[0].b)) win = res[0].id;
  const m = { t: 'win', round: net.round, mode: net.mode, win, rt: r2(net.rt), res };
  RM.send(hostState());
  RM.deliver(m);
  RM.endRound();
  netEnd(m);
}
function netEnd(m) {
  if (!net || net.res) return;
  net.res = m.res; net.win = m.win; net.over = true;
  if (RM.isHost) lastEnd = m;
  const M = NET_MODES.find(o => o.key === m.mode) || NET_MODES[0];
  result = { net: true, mode: m.mode, won: m.win === RM.me, winRow: m.res.find(o => o.id === m.win), rows: m.res, name: M.name };
  if (RM.once(net.round)) showNetEnd();
  else backRoom();
}
function backRoom() {
  if (!net || !net.res) return;
  const won = net.win === RM.me, w = net.res.find(o => o.id === net.win);
  const text = won ? 'Voitit kierroksen!' : w ? w.n + ' voitti kierroksen' : 'Kierros päättyi';
  if (w) RM.note('🏆 ' + (w.id === RM.me ? 'Sinä' : w.n));
  toSolo();
  RM.backToRoom(text, won ? 'win' : 'lose');
}
function toSolo() {
  net = null; world = null; result = null;
  showMenu();
  roomControls();
}

// ---- The room screen: the host picks the mode ----
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra || !RM.inRoom) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#ss-room{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:2px 0 4px}' +
      '#aipr #ss-room button{font-size:15px;padding:7px 12px;background:#14615b;box-shadow:0 3px 0 #0b3d39}' +
      '#aipr #ss-room button.on{background:#1fb5a8;box-shadow:0 3px 0 #0f6f68}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'ss-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      if (NET_MODES.some(o => o.key === b.dataset.m)) netMode = b.dataset.m;
      roomControls();
    });
    RM.extra(roomEl);
  }
  if (RM.isHost) roomEl.innerHTML = NET_MODES.map(o => `<button data-m="${o.key}"${o.key === netMode ? ' class="on"' : ''}>${o.name}</button>`).join('');
  else {
    const h = (RM.members || []).find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Huoneen tekijä${h ? ' (' + esc(h.name) + ')' : ''} valitsee pelin.</p>`;
  }
}
function esc(s) { return String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || !m || m.round !== net.round) return;
    if (RM.isHost) {
      if (!net.ready) return;
      if (m.t === 'p') hostSpot(m, from);
      else if (m.t === 'claim') hostClaim(from, m.k === 'top' ? 'top' : 'b', m.i);
      return;
    }
    if (m.t === 's') guestState(m);
    else if (m.t === 'got') onGot(m);
    else if (m.t === 'nack') onNack(m);
    else if (m.t === 'win') netEnd(m);
  });
  // A phone is back: the round as it is, with its hero where it last said it was.
  RM.on('hello', id => {
    if (net && net.ready && !net.res) RM.send(hostState(), id);
    else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('lobby', toSolo);
  RM.on('leave', toSolo);
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
  RM.on('peers', roomControls);
}
