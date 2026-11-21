'use strict';
// Pulkkamäki v3: sledding with friends, everyone down the same hill at once (#475).
//
// Every phone slides its own sled on its own clock and sends it to the host ten times a second.
// The host slides the computer's sledders, keeps the run's clock and end (everyone down, or LATE
// seconds after the first), and sends every sled to every phone ten times a second. v3 (#480):
// every phone draws the others from lib/sulava-1, a moment back, gliding between the spots heard
// (asDrawn()); the rules keep the newest spot heard, and nothing carries another sled on at its
// speed between messages any more (v2's coast()), so the host sends on the spot a friend sent,
// with the friend's own stamp (`f` in each row; the message's `st` for the host's own and the
// computer's sleds). The host's record
// decides who is in, who has finished and when the run ends; a guest's points come from its own
// phone. The result is the host's deliver(), saved once per round (once()).
//
// Who drives a sled: each has a take-over counter `own`, raised by the host whenever control
// changes hands (the computer takes it on `continue`, the phone gets it back on `back`, a phone
// says `hello` after a reload or a drop). A phone whose own sled comes with a higher counter takes
// the host's state for it and slides on from there; the host ignores a state with a lower counter,
// and every state from a phone while the computer drives its sled. A sled the computer drove at
// any time is marked (`cpu`) for good: that phone saves nothing from the run.
const RM = window.AiPelitRooms;
const LATE = 30, MAX_SLEDS = 4;
const LANES = [0, -4, 4, -7, 7, -2, 2, -5];
const TRICK_IDS = ['front', 'back', 'spinL', 'spinR'];
let lastEnd = null;   // `net`, the run with friends, is declared in ui.js: its loop may run before this file

const r2 = n => Math.round(n * 100) / 100;
// A sled as sent: where, how fast, which way, in the air, its trick, its points, finished.
function pack(sl) {
  return [r2(sl.s), r2(sl.x), r2(sl.y), r2(sl.v), r2(sl.yaw), r2(sl.vy), sl.air ? 1 : 0,
    sl.trick ? TRICK_IDS.indexOf(sl.trick.type) + 1 : 0, sl.trick ? r2(sl.trick.t) : 0, sl.grab ? 1 : 0,
    sl.points, sl.streak, sl.fin ? 1 : 0, r2(sl.fallT), r2(sl.steer), sl.gifts.slice(),
    sl.jump.map(j => [j.type, j.pts]), sl.queue || 0, r2(sl.grabT)];
}
function unpack(sl, a) {
  sl.s = a[0]; sl.x = a[1]; sl.y = a[2]; sl.v = a[3]; sl.yaw = a[4]; sl.vy = a[5]; sl.air = !!a[6];
  if (a[7]) { if (!sl.trick || sl.trick.type !== TRICK_IDS[a[7] - 1]) sl.trick = { type: TRICK_IDS[a[7] - 1], t: a[8] }; else sl.trick.t = a[8]; }
  else { sl.trick = null; sl.flip = 0; sl.spin = 0; }
  sl.grab = !!a[9]; sl.points = a[10]; sl.streak = a[11]; sl.fin = !!a[12]; sl.fallT = a[13]; sl.steer = a[14];
  if (Array.isArray(a[15])) sl.gifts = a[15];
  // What this jump has earned so far (tricks done, one waiting, the grab's time), scored on landing.
  if (Array.isArray(a[16])) { sl.jump = a[16].map(([type, pts]) => ({ type, pts })); sl.queue = a[17] || null; sl.grabT = a[18] || 0; }
}
function outfitOf(id) {
  return (window.AiPelitOutfits && id && AiPelitOutfits.get(id)) || OUTFITS.find(o => o.id === id) || OUTFITS[0];
}
const recOf = id => net && net.sleds.find(r => r.id === id);
const myRec = () => recOf(RM.me);

// v3 (#480): what a track keeps of another sled: its place, heading and height, and the turns drawn
// (a trick's flip and spin, the roll of a fall, the lean). Angles blend the short way round.
const KEYS = ['s', 'x', 'y', 'yaw', 'flip', 'spin', 'roll', 'tilt'];
const newTrack = () => AiPelitSulava.track({ keys: KEYS, angles: ['yaw', 'flip', 'spin', 'roll'], jump: 12 });
const stampOf = m => Number.isFinite(m.st) ? m.st : null;
// A spot heard for another phone's or the computer's sled: the turns it shows now, worked out from
// the state as sent, then into its track. `src` is whose clock the stamp is on, 'f' (the friend's)
// or 'h' (the host's): when it changes (the computer takes over a friend, or gives them back) the
// track starts again there, as two clocks cannot be compared.
function heardSpot(rec, st, src) {
  const sl = rec.sl;
  if (sl.trick) trickPose(sl); else { sl.flip = 0; sl.spin = 0; }
  sl.tilt = sl.air ? 0 : -sl.steer * 0.25;
  sl.roll = sl.fallT > 0 ? (1 - sl.fallT / FALL_T) * TAU * 1.5 : 0;
  if (src !== rec.src) rec.tr.snap(st, sl); else rec.tr.push(st, sl);
  rec.src = src;
}
// The sleds drawn from their tracks: every other phone's, and on a guest the computer's too (the
// host slides those itself, and a friend's sled while its computer drives it).
const drawnHere = rec => rec.kind !== 'me' && !(RM.isHost && (rec.kind === 'cpu' || rec.drive)) && rec.tr.size();
// Swaps the drawn spot in for one frame's drawing, and putBack() the newest one after it.
function asDrawn() {
  const kept = [];
  if (!net) return kept;
  for (const rec of net.sleds) {
    if (!drawnHere(rec)) continue;
    const sl = rec.sl, old = KEYS.map(k => sl[k]), d = rec.tr.at();
    for (const k of KEYS) sl[k] = d[k];
    kept.push([sl, old]);
  }
  return kept;
}
function putBack(kept) { for (const [sl, old] of kept) KEYS.forEach((k, i) => { sl[k] = old[i]; }); }

// ---- The start ----
function netStart(s) {
  net = { round: s.round, hill: 0, ph: 'wait', cd: 3, clock: 0, firstFin: null, res: null, sendT: 0, sleds: [] };
  hideAll();
  sleds = []; me = null; result = null;
  for (const p of pointers.values()) p.used = true;
  if (s.host && !s.over) {
    net.hill = hillN;
    hill = buildHill(hillN);
    const people = s.players.slice(0, 8);
    people.forEach((p, i) => addRec({ id: p.id, name: p.name, kind: p.id === RM.me ? 'me' : 'net', o: p.id === RM.me ? outfit.id : OUTFITS[0].id }, i));
    for (let i = people.length, b = 0; i < MAX_SLEDS; i++, b++) {
      const id = 'cpu' + b, o = OUTFITS[(b + 1) % OUTFITS.length].id;
      const rec = addRec({ id, name: CPU_NAMES[(b + hillN) % CPU_NAMES.length], kind: 'cpu', o }, i);
      rec.sl.cpu = cpuBrain(CPU_SKILL[clamp(hillN - 1 + (b % 2), 0, 2)], hillN * 100 + b * 17 + (Date.now() % 1000));
    }
    net.ph = 'count'; net.cd = 3;
    mode = 'count'; countT = 3;
    me = myRec().sl;
    RM.send(hostState());
  } else mode = 'netwait';
  wake();
}
function addRec(r, i) {
  const sl = newSled(r.id, r.name, { outfit: r.kind === 'me' ? outfit : outfitOf(r.o) });
  placeSled(hill, sl, LANES[i % LANES.length]);
  if (r.kind === 'me') sl.onEvent = onMyEvent;
  const rec = { id: r.id, name: r.name, kind: r.kind, o: r.o, own: 0, cpu: false, drive: false, hostFin: false, lastT: 0, lastA: null, sl,
    tr: newTrack(), ts: null, src: '' };
  net.sleds.push(rec);
  sleds.push(sl);
  return rec;
}
function hostState() {
  // v3 (#480): `st`, the host's clock; `f`, a friend's own stamp for the spot they sent, while they drive it.
  return { t: 's', round: net.round, st: AiPelitSulava.now(), hill: net.hill, ph: net.ph, cd: r2(net.cd), clock: r2(net.clock), ff: net.firstFin,
    sk: net.sleds.map(r => ({ id: r.id, n: r.name, c: r.kind === 'cpu' ? 1 : 0, o: r.o, w: r.own, m: r.cpu ? 1 : 0, a: pack(r.sl),
      f: r.kind === 'net' && !r.drive ? r.ts : null })) };
}

// ---- A guest hears the host ----
function guestState(m) {
  if (net.res) return;
  if (!net.hill) { net.hill = m.hill; hill = buildHill(m.hill); setBoard(m.hill); }
  m.sk.forEach((k, i) => {
    let rec = recOf(k.id);
    const fresh = !rec;
    if (fresh) rec = addRec({ id: k.id, name: k.n, kind: k.id === RM.me ? 'me' : k.c ? 'cpu' : 'net', o: k.o }, i);
    if (rec.kind !== 'me' && rec.o !== k.o) { rec.o = k.o; rec.sl.outfit = outfitOf(k.o); }
    if (rec.kind === 'me') {
      // The host has had my sled (the computer drove it, or I was away): carry on from its state.
      if (fresh || k.w > rec.own) { rec.own = k.w; unpack(rec.sl, k.a); handOver(rec.sl); }
      if (k.a[12]) rec.hostFin = true;
    } else {
      unpack(rec.sl, k.a);
      const own = Number.isFinite(k.f);
      heardSpot(rec, own ? k.f : stampOf(m), own ? 'f' : 'h');
    }
  });
  if (!me) me = myRec() ? myRec().sl : null;
  net.ph = m.ph; net.cd = m.cd; net.clock = m.clock; net.firstFin = m.ff === undefined ? null : m.ff;
  if (!me) return;   // not in this round's list (joined late): the room says so
  if (m.ph === 'count') { if (mode === 'netwait' || mode === 'count') { mode = 'count'; countT = m.cd; } }
  else if (m.ph === 'run' && (mode === 'netwait' || mode === 'count')) { mode = 'run'; runT = m.clock; }
  wake();
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || net.res) return;
  if (RM.paused) return;   // a phone in the run is away: everyone waits
  const host = RM.isHost;
  if (host) {
    if (net.ph === 'count') {
      net.cd -= dt; countT = net.cd;
      if (net.cd <= 0) { net.ph = 'run'; mode = 'run'; runT = 0; net.sendT = 0; }
    } else if (net.ph === 'run') net.clock += dt;
  } else if (net.ph === 'run') net.clock += dt;
  else if (mode === 'count') countT = Math.max(0, countT - dt);
  if (mode === 'run') {
    runT += dt;
    for (const rec of net.sleds) {
      const sl = rec.sl;
      if (rec.kind === 'me') advance(hill, sl, dt);
      else if (host && (rec.kind === 'cpu' || rec.drive)) { cpuDrive(hill, sl, dt); advance(hill, sl, dt); }
      // v3: a sled heard from messages stays at its newest spot; its track draws it on (v2 coasted it).
    }
  }
  net.sendT -= dt;
  if (host) {
    if (net.ph === 'run') {
      if (net.firstFin === null && net.sleds.some(r => r.sl.fin)) net.firstFin = net.clock;
      if (net.sleds.every(r => r.sl.fin) || (net.firstFin !== null && net.clock > net.firstFin + LATE)) return hostEnd();
    }
    if (net.sendT <= 0) { net.sendT = net.ph === 'run' ? 0.1 : 0.25; RM.send(hostState()); }
    return;
  }
  // A guest: its sled ten times a second; once finished, again each second until the host has it.
  const rec = myRec();
  if (!rec || mode === 'netwait') return;
  if (rec.sl.fin && rec.hostFin) return;
  if (net.sendT <= 0) {
    net.sendT = rec.sl.fin ? 1 : net.ph === 'run' ? 0.1 : 0.5;
    RM.send({ t: 'p', round: net.round, st: AiPelitSulava.now(), w: rec.own, o: outfit.id, a: pack(rec.sl) });
  }
}
// The end clock's own time left, for the HUD: null until someone has finished.
function lateLeft() { return net && net.firstFin !== null ? Math.max(0, Math.ceil(net.firstFin + LATE - net.clock)) : null; }

// ---- The end ----
// Finished sleds by points, then those the clock caught on the hill, by points.
function standings() {
  return net.sleds.slice().sort((a, b) => (b.sl.fin - a.sl.fin) || (b.sl.points - a.sl.points))
    .map(r => ({ id: r.id, n: r.name, p: r.sl.points, f: r.sl.fin ? 1 : 0, m: r.cpu ? 1 : 0, b: r.kind === 'cpu' ? 1 : 0 }));
}
function hostEnd() {
  const m = { t: 'end', round: net.round, hill: net.hill, res: standings() };
  RM.send(hostState());
  RM.deliver(m);
  RM.endRound();
  netEnd(m.res, m.hill);
}
// The result, on every phone: shown, and saved once for a sled the computer never drove. It
// overrides the phone's own idea of its run (a finish the clock beat counts as not finished).
function netEnd(res, hillOf) {
  if (!net || net.res) return;
  net.res = res; net.ph = 'done';
  // A phone back only after the end has not heard the hill yet: the result names it.
  if (hillOf && !net.hill) { net.hill = hillOf; setBoard(hillOf); }
  if (RM.isHost) lastEnd = { t: 'end', round: net.round, hill: net.hill, res };
  const i = res.findIndex(o => o.id === RM.me), row = res[i];
  let saved = { record: false, was: best(net.hill || hillN), opened: 0 };
  if (row && !row.m && RM.once(net.round)) saved = saveRun(net.hill || hillN, row.p);
  result = {
    net: true, rows: res.map(o => ({ id: o.id, name: o.id === RM.me ? 'Sinä' : o.n, points: o.p, me: o.id === RM.me, cpu: !!o.b, helped: !!o.m, fin: !!o.f })),
    pts: row ? row.p : 0, fin: row ? !!row.f : false, helped: row ? !!row.m : false, ...saved,
  };
  showEnd();
}
// From the end screen back to the room, with my place there and everyone's points under the list.
function backRoom() {
  if (!net || !net.res) return;
  const res = net.res, i = res.findIndex(o => o.id === RM.me), r = res[i];
  RM.note(res.map((o, j) => `${j + 1}. ${o.id === RM.me ? 'Sinä' : o.n} ${o.p} p`).join(' · '));
  const text = i < 0 ? 'Lasku päättyi' : `${i + 1}. sija · ${r.p} p`;
  toSolo();
  RM.backToRoom(text, i === 0 ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  net = null;
  showMenu();
  roomControls();
}

// ---- The room screen: the host picks the hill ----
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra || !RM.inRoom) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#pulkka-room{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:2px 0 4px}' +
      '#aipr #pulkka-room button{font-size:15px;padding:7px 12px;background:#5a6aa8;box-shadow:0 3px 0 #3b4778}' +
      '#aipr #pulkka-room button.on{background:#c8202f;box-shadow:0 3px 0 #8a1420}' +
      '#aipr #pulkka-room button:disabled{opacity:.35}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'pulkka-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      const n = +b.dataset.h;
      if (n >= 1 && n <= open) { hillN = n; save('maki', n); hill = buildHill(n); wake(); }
      roomControls();
    });
    RM.extra(roomEl);
  }
  if (RM.isHost) {
    roomEl.innerHTML = HILLS.map((H, i) => `<button data-h="${i + 1}"${i + 1 === hillN ? ' class="on"' : ''}${i + 1 > open ? ' disabled' : ''}>${i + 1 > open ? '🔒 ' : ''}${H.name}</button>`).join('');
  } else {
    const h = RM.members.find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Huoneen tekijä${h ? ' (' + esc(h.name) + ')' : ''} valitsee mäen.</p>`;
  }
}

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || m.round !== net.round) return;
    if (RM.isHost) {
      if (m.t !== 'p') return;
      const rec = recOf(from);
      // Only the phone's own sled, only while it drives it, and never an older state than the
      // host's last take-over.
      if (!rec || rec.kind !== 'net' || rec.drive || net.res || !(m.w >= rec.own)) return;
      unpack(rec.sl, m.a);
      rec.lastT = performance.now(); rec.lastA = m.a;
      rec.ts = stampOf(m); heardSpot(rec, rec.ts, 'f');
      if (m.o && m.o !== rec.o) { rec.o = m.o; rec.sl.outfit = outfitOf(m.o); }
      return;
    }
    if (m.t === 's') guestState(m);
    if (m.t === 'end') netEnd(m.res, m.hill);
  });
  RM.on('hello', id => {
    if (net && !net.res) {
      const rec = recOf(id);
      // The phone carries on from its last state the host heard (or the computer's, if it drove).
      if (rec && rec.kind === 'net') { if (rec.lastA && !rec.drive) unpack(rec.sl, rec.lastA); handOver(rec.sl); rec.own++; }
      RM.send(hostState(), id);
    }
    // A phone back after the end it already confirmed (a reload): the library does not send it
    // again, so the host does.
    else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('continue', ids => {
    if (!net || net.res) return;
    for (const rec of net.sleds) if (ids.includes(rec.id) && rec.kind === 'net' && !rec.drive && !rec.sl.fin) {
      rec.drive = true; rec.cpu = true; rec.own++; rec.lastA = null;   // the phone's last state is past
      handOver(rec.sl);
      rec.sl.cpu = cpuBrain(CPU_SKILL[1], rec.sl.s * 7 + 3);
    }
  });
  RM.on('back', id => {
    const rec = recOf(id);
    if (!rec || !rec.drive) return;
    rec.drive = false; rec.own++; rec.sl.cpu = null; handOver(rec.sl);
    rec.tr.reset(); rec.ts = null; rec.src = '';   // v3: drawn where the host has it until the phone's own spots come
  });
  RM.on('lobby', toSolo);
  RM.on('leave', () => { toSolo(); });
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
  RM.on('peers', roomControls);
}
