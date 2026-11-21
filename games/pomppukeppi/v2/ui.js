'use strict';
// Pomppukeppi v1: the screen, the finger, the menus, the saves and the sounds, and the main loop.
// The 3D board is drawn by draw3d.js on the canvas #g underneath; this file draws the scores and
// the stick on #c over it, and the whole board flat when the phone cannot draw 3D.

const c = document.getElementById('c'), cx = c.getContext('2d');
let W = 360, H = 640, DPR = 1, SAFE_T = 0, SAFE_B = 0, SAFE_L = 0, SAFE_R = 0, LAND = false;
function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, 2);
  const r = c.getBoundingClientRect();
  W = r.width || innerWidth; H = r.height || innerHeight;
  c.width = Math.round(W * DPR); c.height = Math.round(H * DPR);
  const cs = getComputedStyle(document.getElementById('safe'));
  SAFE_T = parseFloat(cs.paddingTop) || 0; SAFE_B = parseFloat(cs.paddingBottom) || 0;
  SAFE_L = parseFloat(cs.paddingLeft) || 0; SAFE_R = parseFloat(cs.paddingRight) || 0;
  LAND = W > H;
  document.body.classList.toggle('land', LAND);
  wake();
}
addEventListener('resize', resize);
addEventListener('fullscreenchange', resize);
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);

// ---- Saves (ai-pelit:pomppukeppi:*, shared by every version) ----
const KEY = 'ai-pelit:pomppukeppi:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
function drop(k) { try { localStorage.removeItem(KEY + k); } catch (e) {} }
let open = clamp(Math.floor(load('auki', 1)) || 1, 1, BOARDS.length);   // boards opened
let boardN = clamp(Math.floor(load('kentta', 1)) || 1, 1, open);
// The best erä per board, alone: { "1": points, ... }.
let records = load('ennatys', {});
if (!records || typeof records !== 'object' || Array.isArray(records)) records = {};
const recordOf = n => Math.max(0, Math.floor(records[n]) || 0);
let col = clamp(Math.floor(load('vari', 0)) || 0, 0, COLORS.length - 1);   // my hare's colour
function setBoard(n) { if (window.AiPelitScores) AiPelitScores.board('kentta-' + n, BOARDS[n - 1].name); }

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['jousi', 'boing', 'kello', 'nousu', 'osuma', 'gongi', 'pilli', 'voitto', 'tappio', 'valinta']);
let ac = null;
function beep(f, d, vol) {
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = f; g.gain.value = vol || 0.04; g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + d);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + d);
  } catch (e) {}
}
const sfx = (name, opts, f) => (S && S.play(name, opts)) || (f && beep(f, 0.1, 0.035));
// What changed since the last frame, on any phone (the host's world or a guest's copy of it).
let seen = null, pops = [];
function soundsOf(w) {
  if (!w) { seen = null; return; }
  const now = w.hares.map(h => ({ hop: h.hopN, bump: h.bumpN, cash: h.cashN, got: h.got, stun: h.stun > 0 }));
  if (seen && seen.era === w.era) {
    if (seen.ph === 'count' && w.ph === 'play') sfx('gongi', { vol: 0.22 }, 520);
    if (seen.ph === 'play' && w.ph === 'erä') sfx('pilli', { vol: 0.2 }, 700);
    now.forEach((s, i) => {
      const o = seen.hares[i], h = w.hares[i], mine = h === me;
      if (!o) return;
      if (s.hop > o.hop && mine && w.ph === 'play') sfx('jousi', { vol: 0.1, rate: h.fast > 0 ? 1.3 : 0.95 + Math.random() * 0.1 });
      if (s.bump > o.bump && mine) sfx('boing', { vol: 0.12, rate: 0.8 });
      if (s.cash > o.cash) {
        sfx('kello', { vol: mine ? 0.3 : 0.12 }, 880);
        pops.push({ x: h.x, y: h.y, text: '+' + h.lastCash, col: COLORS[h.col], t: 0 });
      }
      if (s.got > o.got) { sfx('nousu', { vol: mine ? 0.3 : 0.12 }, 990); if (mine) pops.push({ x: h.x, y: h.y, text: POWER_NAMES[h.gotK] || '', col: '#fff', t: 0 }); }
      if (s.stun && !o.stun) sfx('osuma', { vol: mine ? 0.4 : 0.15 }, 220);
    });
  }
  seen = { ph: w.ph, era: w.era, hares: now };
}
const POWER_NAMES = { jousi: 'Pikajousi!', lumi: 'Lumipallo!' };

// ---- The match ----
let mode = 'menu', world = null, me = null, brains = [], result = null, endT = 0, savedEra = 0;
let net = null;   // the match with friends (net.js), null alone
function colsFor(mine) { return [mine].concat([0, 1, 2, 3].filter(k => k !== mine)); }
function soloMatch(resume) {
  const cols = colsFor(col);
  const players = [{ id: 'me', name: 'Sinä', kind: 'me', col: cols[0] }];
  for (let i = 1; i < 4; i++) players.push({ id: 'cpu' + i, name: CPU_NAMES[(i + boardN * 2) % CPU_NAMES.length], kind: 'cpu', col: cols[i] });
  world = newWorld(boardN, players, (Date.now() % 1e9) >>> 0);
  if (resume) {
    // A reload replays the erä it was in, keeping the match's wins and best erät (design, #482).
    resume.wins.forEach((n, i) => { if (world.hares[i]) world.hares[i].wins = clamp(Math.floor(n) || 0, 0, WINS_TO - 1); });
    resume.best.forEach((n, i) => { if (world.hares[i]) world.hares[i].best = Math.max(0, Math.floor(n) || 0); });
    world.era = Math.max(1, Math.floor(resume.era) || 1);
  }
  me = world.hares[0]; savedEra = 0;
  const B = BOARDS[boardN - 1];
  brains = world.hares.map((h, i) => h.kind === 'cpu' ? cpuBrain(B.cpu, world.seed + i * 31) : null);
  setBoard(boardN);
  saveMatch();
  startPlay();
}
// Saved when a match starts and after each erä that does not end it, never mid-erä.
function saveMatch() {
  if (!world || net) return;
  save('kesken1', { b: world.board, era: world.ph === 'erä' ? world.era + 1 : world.era, wins: world.hares.map(h => h.wins), best: world.hares.map(h => h.best) });
}
// A match to go on with, or null. One that does not read, or whose wins already decide it, is
// finished: dropped, and the menu shows (design review, #482).
function readMatch() {
  const m = load('kesken1', null);
  const bad = !m || typeof m !== 'object' || !Array.isArray(m.wins) || m.wins.length !== 4 || !Array.isArray(m.best) || m.best.length !== 4;
  const b = bad ? 0 : Math.floor(m.b);
  if (bad || !(b >= 1 && b <= open) || m.wins.some(n => !(Number.isFinite(n) && n >= 0)) || m.wins.some(n => n >= WINS_TO)) { drop('kesken1'); return null; }
  return { b, era: m.era, wins: m.wins, best: m.best };
}
function startPlay() {
  mode = 'play'; result = null; endT = 0; seen = null; pops = [];
  stick = null; flick = -1;
  hideAll();
  wake();
}
// Alone: the match is over. One step: the board opened, the record, the save dropped, the score
// sent (scores.js keeps an unsent score on the phone). Done the moment the deciding erä ends.
function soloRecord() {
  const won = world.winner === me.id, best = me.best, n = world.board;
  let opened = 0, newRec = false;
  if (won && n === open && open < BOARDS.length) { open++; save('auki', open); opened = open; }
  if (best > recordOf(n)) { records[n] = best; save('ennatys', records); newRec = true; }
  drop('kesken1');
  if (window.AiPelitScores && best > 0) { setBoard(n); AiPelitScores.submit(best); }
  result = { won, opened, best, newRec, rec: recordOf(n), rows: rowsOf(world) };
}
function soloEnd() { if (!result) soloRecord(); showEnd(); }
function rowsOf(w) {
  return w.hares.slice().sort((a, b) => (b.id === w.winner) - (a.id === w.winner) || b.wins - a.wins || b.best - a.best)
    .map(h => ({ id: h.id, name: h === me ? 'Sinä' : h.name, wins: h.wins, best: h.best, col: h.col, me: h === me, cpu: h.kind === 'cpu', helped: !!h.helped }));
}

// ---- The finger ----
// A finger anywhere is a floating stick: where it touched down is the middle, and the way it has
// moved from there (snapped to right, down, left or up) is the next hop. A flick that is let go
// before the hare lands is kept for that landing (spec D4).
const STICK = 46, DEAD = 13;
let stick = null, flick = -1;
c.addEventListener('pointerdown', e => {
  if (mode !== 'play' && mode !== 'netplay') return;
  e.preventDefault();
  if (stick) return;
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
  stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
});
c.addEventListener('pointermove', e => {
  if (!stick || e.pointerId !== stick.id) return;
  stick.x = e.clientX; stick.y = e.clientY;
  // A finger far past the stick's reach drags the middle along, so turning back is quick.
  const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy);
  if (d > STICK) { stick.x0 = stick.x - dx / d * STICK; stick.y0 = stick.y - dy / d * STICK; }
  const k = stickDir();
  if (k >= 0) flick = k;
});
function lift(e) { if (stick && e.pointerId === stick.id) stick = null; }
c.addEventListener('pointerup', lift);
c.addEventListener('pointercancel', lift);
function stickDir() {
  if (!stick) return -1;
  const dx = stick.x - stick.x0, dy = stick.y - stick.y0;
  if (Math.hypot(dx, dy) < DEAD) return -1;
  return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 0 : 2) : (dy > 0 ? 1 : 3);
}
// The direction my hare should hop next: the stick held, or the last flick.
function myWant() { const k = stickDir(); return k >= 0 ? k : flick; }

// ---- Menus (DOM, over the canvas) ----
const $ = id => document.getElementById(id);
function hideAll() { for (const id of ['menu', 'end']) $(id).hidden = true; }
function showMenu() {
  mode = 'menu'; world = null; me = null; seen = null;
  hideAll(); $('menu').hidden = false;
  const box = $('boards'); box.innerHTML = '';
  BOARDS.forEach((B, i) => {
    const n = i + 1, b = document.createElement('button');
    b.className = 'board' + (n === boardN ? ' on' : '');
    b.disabled = n > open;
    const rec = recordOf(n);
    b.innerHTML = '<b>' + n + '. ' + B.name + '</b><small>' + (n > open ? '🔒 Voita edellinen' : B.note + (rec ? ' · ennätys ' + rec + ' p' : '')) + '</small>';
    b.addEventListener('click', () => { boardN = n; save('kentta', n); setBoard(n); sfx('valinta', { vol: 0.3 }); showMenu(); });
    box.appendChild(b);
  });
  colLabel();
  wake();
}
function colLabel() { $('col').innerHTML = '🎨 Väri: <span style="color:' + COLORS[col] + '">●</span> ' + COLOR_NAMES[col]; }
function showEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result;
  $('endTitle').textContent = r.net ? (r.won ? 'Voitit ottelun!' : (r.winnerName || 'Joku') + ' voitti ottelun') : r.won ? 'Voitit ottelun!' : 'Hävisit ottelun';
  $('endNote').textContent = r.helped ? 'Tietokone pelasi puolestasi' : r.net ? '' :
    'Paras eräsi ' + r.best + ' p' + (r.newRec ? ' – uusi ennätys!' : ' · ennätys ' + r.rec + ' p');
  $('endOpen').hidden = !r.opened;
  if (r.opened) $('endOpen').textContent = '🔓 ' + BOARDS[r.opened - 1].name + ' aukesi!';
  $('again').textContent = r.net ? 'Takaisin huoneeseen' : 'Uusi ottelu';
  $('toMenu').hidden = !!r.net;
  const list = $('endList'); list.innerHTML = '';
  r.rows.forEach(row => {
    const li = document.createElement('li');
    if (row.me) li.className = 'me';
    li.innerHTML = '<span><i style="background:' + COLORS[row.col] + '"></i>' + esc(row.name) + (row.cpu || row.helped ? ' 🤖' : '') + '</span>' +
      '<span><b>' + '●'.repeat(row.wins) + '<span class="dim">' + '●'.repeat(Math.max(0, WINS_TO - row.wins)) + '</span></b> <small>' + row.best + ' p</small></span>';
    list.appendChild(li);
  });
  sfx(r.won ? 'voitto' : 'tappio', { vol: 0.3 });
  wake();
}
function esc(s) { return String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }
$('go').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloMatch(null); });
$('col').addEventListener('click', () => { col = (col + 1) % COLORS.length; save('vari', col); sfx('valinta', { vol: 0.3 }); colLabel(); });
$('again').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (result && result.net) backRoom(); else soloMatch(null); });
$('friends').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (window.AiPelitRooms) AiPelitRooms.open(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });

// ---- Drawing on the 2D canvas ----
function shadowText(t, x, y, size, colr, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(0,20,10,.55)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = colr; cx.fillText(t, x, y);
}
// Without 3D: the board flat from above, the hares as discs that grow in the air.
let flat = null;
function flatView(n) {
  const top = LAND ? SAFE_T + 12 : SAFE_T + 96, bottom = H - SAFE_B - (LAND ? 12 : 60);
  const left = LAND ? SAFE_L + 130 : SAFE_L + 10, right = W - SAFE_R - (LAND ? 130 : 10);
  const s = Math.min((right - left) / n, (bottom - top) / n);
  return { s, ox: (left + right) / 2 - s * n / 2, oy: (top + bottom) / 2 - s * n / 2 };
}
function draw2d(w) {
  flat = flatView(w.n);
  const { s, ox, oy } = flat, n = w.n;
  cx.fillStyle = '#6fb04a'; cx.fillRect(0, 0, W, H);
  cx.fillStyle = '#a8743a'; cx.fillRect(ox - 6, oy - 6, s * n + 12, s * n + 12);
  for (let k = 0; k < n * n; k++) {
    const x = k % n, y = (k / n) | 0, t = w.tiles[k];
    cx.fillStyle = t >= 0 ? COLORS[w.hares[t] ? w.hares[t].col : t] : t === BLANK ? ((x + y) % 2 ? '#e6ddc2' : '#f0e9d4') : '#5f9a3e';
    cx.fillRect(ox + x * s + 1, oy + y * s + 1, s - 2, s - 2);
    if (t === ROCK) { cx.fillStyle = '#8a8f96'; cx.beginPath(); cx.arc(ox + (x + 0.5) * s, oy + (y + 0.5) * s, s * 0.36, 0, TAU); cx.fill(); }
    if (t === HOLE) { cx.fillStyle = '#2a1c10'; cx.beginPath(); cx.arc(ox + (x + 0.5) * s, oy + (y + 0.5) * s, s * 0.38, 0, TAU); cx.fill(); }
  }
  for (const [b, t, colr] of [[w.cash, '💰', '#f2b632'], [w.qbox, '?', '#3d7ee8']]) {
    if (!b) continue;
    cx.fillStyle = colr; cx.fillRect(ox + (b.x + 0.2) * s, oy + (b.y + 0.2) * s, s * 0.6, s * 0.6);
    shadowText(t, ox + (b.x + 0.5) * s, oy + (b.y + 0.5) * s, s * 0.4, '#fff', 'center', 900);
  }
  for (const h of w.hares) {
    const p = harePos(h), X = ox + (p.x + 0.5) * s, Y = oy + (p.y + 0.5) * s - p.z * s * 0.5;
    cx.fillStyle = 'rgba(0,0,0,.25)'; cx.beginPath(); cx.arc(ox + (p.x + 0.5) * s, oy + (p.y + 0.5) * s, s * 0.3, 0, TAU); cx.fill();
    cx.fillStyle = COLORS[h.col]; cx.beginPath(); cx.arc(X, Y, s * (0.3 + p.z * 0.08), 0, TAU); cx.fill();
    cx.strokeStyle = h === me ? '#ffe14a' : '#fff'; cx.lineWidth = h === me ? 4 : 2; cx.stroke();
  }
}
// Screen px of a board point, in 3D or flat.
function project(x, y, z) {
  if (V3 && !no3d) return project3d(x, y, z);
  if (!flat) return { x: W / 2, y: H / 2 };
  return { x: flat.ox + (x + 0.5) * flat.s, y: flat.oy + (y + 0.5) * flat.s - z * flat.s * 0.5 };
}
// Each hare's points and squares along the top (sideways: a column on the left), the clock, the
// countdown, the erä's winner, the pop-ups and the stick.
function drawHUD(w, dt) {
  const n = w.hares.length;
  const x0 = SAFE_L + 86, x1 = W - SAFE_R - 8, cw = Math.min(84, (x1 - x0) / n);
  w.hares.forEach((h, i) => {
    const x = LAND ? SAFE_L + 10 : x0 + i * cw, y = LAND ? SAFE_T + 56 + i * 50 : SAFE_T + 10, bw = LAND ? 104 : cw - 6;
    cx.fillStyle = 'rgba(20,40,20,.45)'; roundRect(x, y, bw, 44, 10); cx.fill();
    cx.fillStyle = COLORS[h.col]; roundRect(x, y, 8, 44, 4); cx.fill();
    if (h === me) { cx.strokeStyle = '#ffe14a'; cx.lineWidth = 2.5; roundRect(x, y, bw, 44, 10); cx.stroke(); }
    shadowText(String(h.pts), x + 14, y + 15, 19, '#fff', 'left', 900);
    shadowText('▦ ' + ownCount(w, h), x + 14, y + 34, 12, '#e8f0e0', 'left', 700);
    for (let k = 0; k < WINS_TO; k++) {
      cx.fillStyle = k < h.wins ? '#ffd84a' : 'rgba(255,255,255,.25)';
      cx.beginPath(); cx.arc(x + bw - 9 - k * 11, y + 12, 4, 0, TAU); cx.fill();
    }
    if (h.stun > 0) shadowText('💫', x + bw - 12, y + 32, 13, '#fff', 'center', 700);
    else if (h.fast > 0) shadowText('⚡', x + bw - 12, y + 32, 13, '#fff', 'center', 700);
  });
  const left = Math.max(0, Math.ceil(ERA_T - w.t));
  const clockY = LAND ? SAFE_T + 22 : SAFE_T + 74;
  if (w.ph === 'play' || w.ph === 'erä') shadowText(String(left), W / 2, clockY, LAND ? 24 : 22, left <= 10 && w.ph === 'play' ? '#ffd84a' : '#fff', 'center', 900);
  const midY = H * 0.42;
  if (w.ph === 'count') {
    const k = Math.ceil(w.cd);
    shadowText('Erä ' + w.era, W / 2, midY - 56, 22, '#fff', 'center', 800);
    shadowText(k > 0 ? String(k) : 'POMPI!', W / 2, midY, 60, '#fff', 'center', 900);
  } else if (w.ph === 'play' && w.t < 0.8) shadowText('POMPI!', W / 2, midY, 52, '#fff', 'center', 900);
  if (w.ph === 'erä' || w.ph === 'over') {
    const win = w.hares.find(h => h.id === w.eraWin);
    shadowText(win ? (win === me ? 'Voitit erän!' : win.name + ' voitti erän!') : 'Tasapeli – erä uusiksi', W / 2, midY, 26, '#fff', 'center', 900);
  }
  // Cash-ins and power-ups rise from where they happened.
  pops = pops.filter(p => (p.t += dt) < 1.2);
  for (const p of pops) { const s = project(p.x, p.y, 1.4 + p.t); shadowText(p.text, s.x, s.y - p.t * 30, 22, p.col, 'center', 900); }
  // Names with friends.
  if (net) for (const h of w.hares) {
    if (h === me) continue;
    const pp = harePos(h), s = project(pp.x, pp.y, pp.z + 1.65);
    shadowText(h.name, s.x, s.y, 12, '#fff', 'center', 700);
  }
  if (tutorial && me && w.era === 1 && w.ph === 'play' && w.t < 10) {
    // Upright under the board; sideways in the free strip right of it.
    const lines = LAND ? [['Vedä sormella:', '#fff'], ['jänis pomppii', '#fff'], ['sinne.', '#fff'], ['Pompi 💰-', '#ffe14a'], ['laatikkoon:', '#ffe14a'], ['ruudut pisteiksi!', '#ffe14a']]
      : [['Vedä sormella: jänis pomppii sinne', '#fff'], ['Pompi 💰-laatikkoon: ruudut pisteiksi!', '#ffe14a']];
    const tx = LAND ? W - SAFE_R - 12 : W / 2, ty = LAND ? H / 2 - 50 : H - SAFE_B - 70;
    lines.forEach(([t, c2], k) => shadowText(t, tx, ty + k * 21, 15, c2, LAND ? 'right' : 'center', 700));
  }
  if (stick && me) {
    cx.strokeStyle = 'rgba(255,255,255,.4)'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(stick.x0, stick.y0, STICK, 0, TAU); cx.stroke();
    const k = stickDir();
    const kx = k >= 0 ? DIRS[k][0] * STICK * 0.7 : 0, ky = k >= 0 ? DIRS[k][1] * STICK * 0.7 : 0;
    cx.fillStyle = 'rgba(255,255,255,.55)'; cx.beginPath(); cx.arc(stick.x0 + kx, stick.y0 + ky, 18, 0, TAU); cx.fill();
  }
  if (net && window.AiPelitRooms && AiPelitRooms.paused) shadowText('Odotetaan kaveria…', W / 2, midY + 80, 18, '#fff', 'center', 800);
}
function roundRect(x, y, w, h, r) {
  cx.beginPath(); cx.moveTo(x + r, y); cx.arcTo(x + w, y, x + w, y + h, r); cx.arcTo(x + w, y + h, x, y + h, r);
  cx.arcTo(x, y + h, x, y, r); cx.arcTo(x, y, x + w, y, r); cx.closePath();
}
let tutorial = !load('osattu', false), showNo3d = 0;
let mw = null;
function menuWorld() { if (!mw || mw.board !== boardN) mw = newWorld(boardN, [], 1); return mw; }
function draw(dt) {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  const w = world || menuWorld();
  if (V3 && !no3d) render3d(w, me, dt);
  else draw2d(w);
  if (no3d && mode === 'menu') shadowText('Puhelimesi ei pysty piirtämään 3D-kuvaa.', W / 2, H - SAFE_B - 20, 13, '#fff', 'center', 700);
  if (mode === 'netwait') shadowText('Odotetaan muita…', W / 2, H * 0.4, 20, '#fff', 'center', 800);
  if (world && (mode === 'play' || mode === 'netplay')) drawHUD(world, dt);
}

// ---- The main loop ----
// It draws every frame while a round is on; in the menus it draws a few frames and rests, so a
// phone left on the menu does not heat up (docs/making-games.md, Pasianssi v1).
let raf = 0, last = 0, still = 0;
function wake() { still = 0; if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
function frame(now) {
  raf = 0;
  const ms = last ? now - last : 16;
  const dt = last ? Math.min(0.1, ms / 1000) : 1 / 60; last = now;
  if (net) netTick(dt);
  else if (mode === 'play' && world) {
    me.want = myWant();
    world.hares.forEach((h, i) => { if (brains[i]) cpuThink(world, h, brains[i]); });
    const hop = me.hopN;
    step(world, dt);
    if (me.hopN !== hop) flick = -1;   // the landing used the flick
    // An erä that did not decide the match: saved once, as the next erä to play.
    if (world.ph === 'erä' && !world.winner && savedEra !== world.era) { savedEra = world.era; saveMatch(); }
    if (world.winner && !result) soloRecord();
    if (tutorial && me.cashN > 0) { tutorial = false; save('osattu', true); }
    if (world.over) { endT += dt; if (endT > 0.3) soloEnd(); }
  }
  soundsOf(mode === 'play' || mode === 'netplay' ? world : null);
  draw(dt);
  if (mode === 'play' || mode === 'netplay') tune(ms);
  document.body.classList.toggle('playing', mode === 'play' || mode === 'netplay' || mode === 'netwait');
  const moving = mode === 'play' || mode === 'netplay' || mode === 'netwait';
  if (moving || still++ < 3) raf = requestAnimationFrame(frame);
}
resize();
const resumed = !(window.AiPelitRooms && AiPelitRooms.inRoom) ? readMatch() : null;
setBoard(boardN);
if (window.AiPelitRooms && AiPelitRooms.inRoom) hideAll();
else if (resumed) { boardN = resumed.b; soloMatch(resumed); }
else showMenu();
