'use strict';
// Pomppukeppi v1: the match with friends, 2–4 phones on one board (#482).
//
// The host phone runs the only real world (world.js): every hop, landing, cash-in and power-up,
// the computer hares' too. It sends the whole state 10 times a second. A guest sends only its
// stick's direction, when it changes and at least every half second; the host counts a guest's
// stick as let go after a second of silence. A guest decides nothing.
//
// Order (design, #482): a guest keeps only states of the round it last heard `start` for
// (rooms.js's round id, compared only for equality) and, within it, only a `seq` above the last it
// kept. The host's `seq` is one counter for the whole life of its page and never goes back.
//
// Who drives a hare: each has a take-over counter `own`, raised by the host on `continue` (the
// computer takes it), on `back` and on `hello` (the phone has it again). The host takes a phone's
// direction only with the hare's current `own`.
//
// A guest's own hare hops at once with its finger (prediction). Each hop it starts is kept in a
// list with its hop number and its from and to squares. When the host's state shows my hare in a
// hop that is in the list (same number, same squares), the older ones are dropped and my own hare
// goes on as it is: holding one way across many hops never snaps back (design review note, #482).
// A host hop that is not in the list (a block the guest could not see: another hare, a snowball,
// a hop number out of step) makes my hare take the host's hop, and the list starts again from it.
// One case is not a snap: the host bouncing in place at the first hop of a new direction, because
// my direction arrived after that landing (lateStart()).
// The list keeps at most 40 hops; a match more than that behind is no match.
//
// A flick let go before landing is sent with the hop number it is for, so the host uses it at
// that landing even when the "let go" message arrives first. A room match saves nothing lasting.
const RM = window.AiPelitRooms;
let lastEnd = null, hostSeq = 0;   // `net` is declared in ui.js: its loop may run before this file

const r2 = n => Math.round(n * 100) / 100;
function pack(h, rec) {
  return [h.id, h.name, h.col, h.kind === 'cpu' ? 1 : 0, h.own, h.x, h.y, h.fx, h.fy, r2(h.p), r2(h.hopT),
    h.pts, h.wins, h.best, r2(h.fast), r2(h.stun), h.hopN, h.bumpN, h.cashN, h.lastCash, h.got, h.gotK || '', rec && rec.helped ? 1 : 0];
}
function unpackRest(h, a) {
  h.name = a[1]; h.col = a[2]; h.own = a[4]; h.hopT = a[10];
  h.pts = a[11]; h.wins = a[12]; h.best = a[13]; h.fast = a[14]; h.stun = a[15];
  h.bumpN = a[17]; h.cashN = a[18]; h.lastCash = a[19]; h.got = a[20]; h.gotK = a[21]; h.helped = !!a[22];
}
function unpackHop(h, a) { h.x = a[5]; h.y = a[6]; h.fx = a[7]; h.fy = a[8]; h.p = a[9]; h.hopN = a[16]; }
function hostState() {
  const w = world;
  return {
    t: 's', round: net.round, seq: ++hostSeq, b: w.board, ph: w.ph, cd: r2(w.cd), era: w.era, tt: r2(w.t), pause: r2(w.pause),
    win: w.winner, ew: w.eraWin,
    cash: w.cash ? [w.cash.x, w.cash.y] : null,
    q: w.qbox ? [w.qbox.x, w.qbox.y, r2(w.qbox.life)] : null,
    tiles: w.tiles.slice(),
    hk: w.hares.map((h, i) => pack(h, net.recs[i])),
  };
}

// ---- The start ----
function netStart(s) {
  net = { round: s.round, lastSeq: -1, recs: [], res: null, sendT: 0, myOwn: -1, hist: [], sentD: -2, sentF: -2, sentT: 0 };
  hideAll();
  world = null; me = null; brains = []; result = null; stick = null; flick = -1; seen = null; pops = [];
  if (s.host && !s.over) {
    const people = s.players.slice(0, 4), used = [col];
    const players = people.map(p => {
      const mine = p.id === RM.me;
      let c = col;
      if (!mine) { c = [0, 1, 2, 3].find(k => !used.includes(k)); used.push(c); }
      return { id: p.id, name: p.name, col: c, kind: mine ? 'me' : 'net' };
    });
    for (let b = 0; players.length < 4; b++) {
      const c = [0, 1, 2, 3].find(k => !used.includes(k)); used.push(c);
      players.push({ id: 'cpu' + b, name: CPU_NAMES[(b + boardN * 2) % CPU_NAMES.length], col: c, kind: 'cpu' });
    }
    world = newWorld(boardN, players, (Date.now() % 1e9) >>> 0);
    const B = BOARDS[boardN - 1];
    net.recs = world.hares.map(h => ({ id: h.id, kind: h.kind, drive: false, helped: false, inT: performance.now(), d: -1, fd: -1, fn: -1 }));
    brains = world.hares.map((h, i) => h.kind === 'cpu' ? cpuBrain(B.cpu, world.seed + i * 31) : null);
    me = world.hares.find(h => h.id === RM.me) || null;
    mode = 'netplay';
    RM.send(hostState());
  } else mode = 'netwait';
  wake();
}

// ---- A guest hears the host ----
// My hare takes the host's hop, and the list of my own hops starts again from it.
function snapMine(a) {
  unpackHop(me, a);
  net.hist = [{ n: me.hopN, fx: me.fx, fy: me.fy, x: me.x, y: me.y, d: me.x === me.fx && me.y === me.fy ? -1 : DIRS.findIndex(([dx, dy]) => me.fx + dx === me.x && me.fy + dy === me.y), at: performance.now() }];
}
function guestState(m) {
  if (net.res) return;
  if (!(m.seq > net.lastSeq)) return;   // an older state of this round, overtaken
  net.lastSeq = m.seq;
  if (!world || world.board !== m.b || world.hares.length !== m.hk.length) {
    world = newWorld(m.b, m.hk.map(a => ({ id: a[0], name: a[1], col: a[2], kind: a[3] ? 'cpu' : 'net' })), 1);
    me = world.hares.find(h => h.id === RM.me) || null;
    if (me) me.kind = 'me';
    net.myOwn = -1; net.hist = [];
  }
  const w = world;
  const wasEra = w.era;
  w.ph = m.ph; w.cd = m.cd; w.era = m.era; w.t = m.tt; w.pause = m.pause; w.winner = m.win; w.eraWin = m.ew;
  w.over = m.ph === 'over';
  w.cash = m.cash ? { x: m.cash[0], y: m.cash[1] } : null;
  w.qbox = m.q ? { x: m.q[0], y: m.q[1], life: m.q[2] } : null;
  if (m.tiles.length === w.tiles.length) for (let k = 0; k < w.tiles.length; k++) w.tiles[k] = m.tiles[k];
  m.hk.forEach((a, i) => {
    const h = w.hares[i];
    if (!h) return;
    unpackRest(h, a);
    h.kind = h === me ? 'me' : a[3] ? 'cpu' : 'net';
    if (h !== me) { unpackHop(h, a); return; }
    // My own hare. Outside play, on a new erä, or when the host hands it to me (start, my hello,
    // back), the host's word on where it is.
    if (a[4] !== net.myOwn || w.ph !== 'play' || w.era !== wasEra || h.stun > 0) { net.myOwn = a[4]; snapMine(a); return; }
    let k = net.hist.findIndex(e => e.n === a[16] && e.fx === a[7] && e.fy === a[8] && e.x === a[5] && e.y === a[6]);
    if (k < 0) k = lateStart(a);
    if (k < 0) { snapMine(a); return; }
    net.hist.splice(0, k);
    // The squares I have landed on since the host's hop, painted mine already on my phone.
    for (let j = 1; j < net.hist.length; j++) { const e = net.hist[j]; if (passable(w, e.fx, e.fy)) w.tiles[e.fy * w.n + e.fx] = me.i; }
  });
  if (!me) return;   // not in this match (joined late): the room says so
  if (mode === 'netwait') { mode = 'netplay'; stick = null; }
  wake();
}
// The host bounced my hare in place at hop n where my phone made the first hop of a new
// direction: my direction reached the host after that landing (a round trip longer than a hop).
// The host makes that move one hop later, so my hops from there on are numbered one up and
// nothing moves on my screen. Once per new direction: a second bounce there is a real block.
function lateStart(a) {
  const j = net.hist.findIndex(e => e.n === a[16]);
  const e = net.hist[j];
  if (j < 0 || !e.first || e.late || a[5] !== a[7] || a[6] !== a[8] || e.fx !== a[7] || e.fy !== a[8]) return -1;
  for (let k = j; k < net.hist.length; k++) net.hist[k].n++;
  me.hopN++;
  e.late = true;
  net.hist.splice(j, 0, { n: a[16], fx: e.fx, fy: e.fy, x: e.fx, y: e.fy, d: -1, at: e.at });
  return j;
}
// A guest's own hop, started the moment its hare lands on its phone.
function guestHop(w, h) {
  if (w.ph === 'play' && passable(w, h.x, h.y)) w.tiles[h.y * w.n + h.x] = h.i;
  h.fx = h.x; h.fy = h.y; h.p = 0; h.hopN++;
  h.hopT = h.fast > 0 ? FAST_HOP_T : HOP_T;
  let d = -1;
  if (w.ph === 'play' && h.stun <= 0 && h.want >= 0 && canHop(w, h, h.want)) { d = h.want; h.x += DIRS[d][0]; h.y += DIRS[d][1]; }
  const prev = net.hist[net.hist.length - 1];
  net.hist.push({ n: h.hopN, fx: h.fx, fy: h.fy, x: h.x, y: h.y, d, first: d >= 0 && (!prev || prev.d !== d), at: performance.now() });
  if (net.hist.length > 40) net.hist.shift();
}

// ---- Each frame, in a room ----
function netTick(dt) {
  if (!net || net.res || !world) return;
  if (RM.paused) return;   // a phone in the match is away: everyone waits, the host's world too
  const w = world;
  if (RM.isHost) {
    const now = performance.now();
    if (me) me.want = myWant();
    w.hares.forEach((h, i) => {
      const rec = net.recs[i];
      if (brains[i] && (rec.kind === 'cpu' || rec.drive)) cpuThink(w, h, brains[i]);
      else if (rec.kind === 'net') {
        // A phone silent for a second: its stick counts as let go until it talks again.
        if (now - rec.inT > 1000) rec.d = -1;
        h.want = rec.d >= 0 ? rec.d : rec.fn === h.hopN ? rec.fd : -1;
      }
    });
    const hop = me ? me.hopN : 0;
    step(w, dt);
    if (me && me.hopN !== hop) flick = -1;
    if (w.over) return hostEnd();
    net.sendT -= dt;
    if (net.sendT <= 0) { net.sendT = 0.1; RM.send(hostState()); }
    return;
  }
  // A guest: the countdown and the clock run on, the others finish the hop they are in, my own
  // hare hops with my finger.
  if (w.ph === 'count') w.cd = Math.max(0, w.cd - dt);
  if (w.ph === 'play') w.t = Math.min(ERA_T, w.t + dt);
  for (const h of w.hares) if (h !== me) h.p = Math.min(1, h.p + dt / h.hopT);
  if (me && net.myOwn >= 0) {
    me.want = myWant();
    me.p += dt / me.hopT;
    if (me.p >= 1) { me.p = 1; if (w.ph === 'play') { guestHop(w, me); flick = -1; } }
  }
  // My direction: sent when it changes, and at least every half second. A flick kept for the
  // next landing goes with that landing's hop number.
  net.sentT -= dt;
  if (me && net.myOwn >= 0) {
    const d = stickDir(), f = d < 0 ? flick : -1;
    if (d !== net.sentD || f !== net.sentF || net.sentT <= 0) {
      net.sentD = d; net.sentF = f; net.sentT = 0.5;
      RM.send({ t: 'i', round: net.round, w: net.myOwn, d, f, n: me.hopN, c: col });
    }
  }
}

// ---- The host hears a guest ----
function hostInput(m, from) {
  const i = net.recs.findIndex(r => r.id === from);
  if (i < 0 || !world) return;
  const rec = net.recs[i], h = world.hares[i];
  if (rec.kind !== 'net' || rec.drive || m.w !== h.own) return;   // not driving it now, or an old take-over
  rec.inT = performance.now();
  const d = Math.floor(m.d), f = Math.floor(m.f);
  rec.d = d >= 0 && d <= 3 ? d : -1;
  // A flick is for the landing that ends hop `n`; a later "nothing" does not cancel it.
  if (f >= 0 && f <= 3 && Number.isFinite(m.n)) { rec.fd = f; rec.fn = Math.floor(m.n); }
  else if (rec.d >= 0) rec.fn = -1;
  // The phone's own colour, when no other phone has it (a computer hare swaps with it).
  const c = Math.floor(m.c);
  if (c >= 0 && c < COLORS.length && c !== h.col) {
    const other = world.hares.find(o => o !== h && o.col === c);
    if (!other) h.col = c;
    else if (other.kind === 'cpu') { other.col = h.col; h.col = c; }
  }
}

// ---- The end ----
function standings() {
  const w = world;
  return w.hares.map((h, i) => ({ id: h.id, n: h.name, wn: h.wins, bs: h.best, c: h.col, b: h.kind === 'cpu' ? 1 : 0, m: net.recs[i] && net.recs[i].helped ? 1 : 0 }))
    .sort((a, b) => (b.id === w.winner) - (a.id === w.winner) || b.wn - a.wn || b.bs - a.bs);
}
function hostEnd() {
  const m = { t: 'end', round: net.round, win: world.winner, res: standings() };
  RM.send(hostState());
  RM.deliver(m);
  RM.endRound();
  netEnd(m);
}
// The result, on every phone: shown once (`once()`), saved nowhere.
function netEnd(m) {
  if (!net || net.res) return;
  net.res = m.res; net.win = m.win;
  if (RM.isHost) lastEnd = m;
  const row = m.res.find(o => o.id === RM.me), winRow = m.res.find(o => o.id === m.win);
  result = {
    net: true, won: !!row && m.win === RM.me, winnerName: winRow ? winRow.n : '', helped: !!(row && row.m),
    rows: m.res.map(o => ({ id: o.id, name: o.id === RM.me ? 'Sinä' : o.n, wins: o.wn, best: o.bs, col: o.c, me: o.id === RM.me, cpu: !!o.b, helped: !!o.m })),
  };
  if (RM.once(net.round)) showEnd();
  else backRoom();   // seen already (a reload after the end): straight back to the room
}
// From the end screen back to the room, with everyone's erä wins under the list.
function backRoom() {
  if (!net || !net.res) return;
  const res = net.res, won = net.win === RM.me;
  RM.note(res.map(o => `${o.id === RM.me ? 'Sinä' : o.n} ${'●'.repeat(o.wn) || '0'}`).join(' · '));
  const w = res.find(o => o.id === net.win);
  const text = won ? 'Voitit ottelun!' : (w ? (w.id === RM.me ? 'Sinä' : w.n) + ' voitti ottelun' : 'Ottelu päättyi');
  toSolo();
  RM.backToRoom(text, won ? 'win' : 'lose');
}
function toSolo() {
  if (!net) return;
  net = null; world = null; me = null; brains = [];
  showMenu();
  roomControls();
}

// ---- The room screen: the host picks the board ----
let roomEl = null;
function roomControls() {
  if (!RM || !RM.extra || !RM.inRoom) return;
  if (!roomEl) {
    const css = document.createElement('style');
    css.textContent = '#ppk-room{display:flex;flex-wrap:wrap;justify-content:center;gap:6px;margin:2px 0 4px}' +
      '#aipr #ppk-room button{font-size:15px;padding:7px 12px;background:#4f8a2e;box-shadow:0 3px 0 #2f5a18}' +
      '#aipr #ppk-room button.on{background:#e8323f;box-shadow:0 3px 0 #9a1424}' +
      '#aipr #ppk-room button:disabled{opacity:.35}';
    document.head.appendChild(css);
    roomEl = document.createElement('div'); roomEl.id = 'ppk-room';
    roomEl.addEventListener('click', e => {
      const b = e.target.closest('button');
      if (!b || !RM.isHost || net) return;
      const n = +b.dataset.b;
      if (n >= 1 && n <= open) { boardN = n; save('kentta', n); wake(); }
      roomControls();
    });
    RM.extra(roomEl);
  }
  if (RM.isHost) {
    roomEl.innerHTML = BOARDS.map((B, i) => `<button data-b="${i + 1}"${i + 1 === boardN ? ' class="on"' : ''}${i + 1 > open ? ' disabled' : ''}>${i + 1 > open ? '🔒 ' : ''}${B.name}</button>`).join('');
  } else {
    const h = (RM.members || []).find(m => m.id === RM.hostId);
    roomEl.innerHTML = `<p class="small">Huoneen tekijä${h ? ' (' + esc(h.name) + ')' : ''} valitsee kentän.</p>`;
  }
}

if (RM) {
  RM.on('start', netStart);
  RM.on('message', (m, from) => {
    if (!net || !m || m.round !== net.round) return;   // another round's message: dropped, never compared by size
    if (RM.isHost) { if (m.t === 'i') hostInput(m, from); return; }
    if (m.t === 's') guestState(m);
    if (m.t === 'end') netEnd(m);
  });
  RM.on('hello', id => {
    if (net && !net.res && world) {
      // The phone is back (a reload or a drop): it takes its hare again from the next state.
      const i = net.recs.findIndex(r => r.id === id);
      if (i >= 0 && net.recs[i].kind === 'net' && !net.recs[i].drive) { world.hares[i].own++; net.recs[i].inT = performance.now(); }
      RM.send(hostState(), id);
    }
    // A phone back after an end it already confirmed: the library does not send it again.
    else if (lastEnd && lastEnd.round === RM.round) RM.send(lastEnd, id);
  });
  RM.on('continue', ids => {
    if (!net || net.res || !world) return;
    const B = BOARDS[world.board - 1];
    net.recs.forEach((rec, i) => {
      if (!ids.includes(rec.id) || rec.kind !== 'net' || rec.drive) return;
      rec.drive = true; rec.helped = true; world.hares[i].own++;
      brains[i] = cpuBrain(B.cpu, world.seed + i * 31 + 7);
    });
  });
  RM.on('back', id => {
    const i = net && world ? net.recs.findIndex(r => r.id === id) : -1;
    if (i < 0 || !net.recs[i].drive) return;
    const rec = net.recs[i];
    rec.drive = false; rec.inT = performance.now(); rec.d = -1; rec.fn = -1; world.hares[i].own++;
    world.hares[i].want = -1;
  });
  RM.on('lobby', toSolo);
  RM.on('leave', () => { toSolo(); });
  RM.on('menu', () => { if (net) toSolo(); else showMenu(); });
  RM.on('peers', roomControls);
}
