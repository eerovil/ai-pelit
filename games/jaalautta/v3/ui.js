'use strict';
// Jäälautta v2: the screen, the fingers, the menus, the saves and the sounds, and the main loop.

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
  // Upright under 360 px the star row needs the whole width, so ⏸ sits under it (see drawHUD).
  document.body.classList.toggle('narrow', !LAND && W < 360);
  wake();
}
addEventListener('resize', resize);
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);

// ---- Saves (ai-pelit:jaalautta:*, shared by every version) ----
const KEY = 'ai-pelit:jaalautta:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
function drop(k) { try { localStorage.removeItem(KEY + k); } catch (e) {} }
let open = clamp(Math.floor(load('auki', 1)) || 1, 1, FLOES.length);   // floes opened
let floeN = clamp(Math.floor(load('lautta', 1)) || 1, 1, open);
let wins = Math.max(0, Math.floor(load('voitot', 0)) || 0);              // matches won alone

// The seals' hats: each player picks a colour (#478 spec), the computer takes the others.
const HATS = [
  { name: 'Punainen', c: '#e0283a' }, { name: 'Sininen', c: '#2a6fe0' }, { name: 'Keltainen', c: '#f5c518' },
  { name: 'Vihreä', c: '#24a84a' }, { name: 'Violetti', c: '#8a44d8' }, { name: 'Oranssi', c: '#f07a1a' },
  { name: 'Turkoosi', c: '#1ab8b0' }, { name: 'Pinkki', c: '#f05aa8' },
];
let hat = clamp(Math.floor(load('hattu', 0)) || 0, 0, HATS.length - 1);
function hatFor(taken, i) {
  for (let k = 0; k < HATS.length; k++) { const h = (i + k) % HATS.length; if (!taken.includes(h)) return h; }
  return i % HATS.length;
}

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['gongi', 'suhahdus', 'osuma', 'tomahdys', 'jaa', 'loiskis', 'voitto', 'tappio', 'valinta', 'nousu', 'onnistui', 'narina']);
let ac = null;
function beep(f, d, vol) {
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = f; g.gain.value = vol || 0.05; g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + d);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + d);
  } catch (e) {}
}
const sfx = (name, opts, f) => (S && S.play(name, opts)) || (f && beep(f, 0.12, 0.04));
// What changed since the last frame, on any phone (the host's world or a guest's copy of it).
let seen = null;
function soundsOf(w) {
  if (!w) { seen = null; return; }
  const now = w.seals.map(s => ({ out: !!s.out, l: s.lunges, hit: s.hit, got: s.got, stun: s.stun > 0, cr: !!s.crushed, tee: s.teeter > 0, sv: s.saved || 0 }));
  const st = { ph: w.ph, era: w.era, warn: w.warn.length, seals: now };
  if (seen && seen.era === w.era) {
    if (seen.ph === 'count' && w.ph === 'play') sfx('gongi', { vol: 0.25 }, 520);
    if (w.warn.length > seen.warn) sfx('jaa', { vol: 0.35 });
    now.forEach((s, i) => {
      const o = seen.seals[i], mine = w.seals[i] === me;
      if (!o) return;
      if (s.out && !o.out) { sfx(s.cr ? 'tomahdys' : 'loiskis', { vol: mine ? 0.55 : 0.35 }, 200); if (s.cr) sfx('loiskis', { vol: 0.3, delay: 0.1 }); }
      if (s.tee && !o.tee) sfx('narina', { vol: mine ? 0.4 : 0.2 }, 260);
      if (s.sv > o.sv) sfx('onnistui', { vol: mine ? 0.35 : 0.15 }, 660);
      if (s.l > o.l && mine && !s.tee && !o.tee) sfx('suhahdus', { vol: 0.3 });
      else if (s.l > o.l && mine) sfx('valinta', { vol: 0.2, rate: 1 + (w.seals[i].mash || 0) * 0.08 }, 500);
      if (s.hit > o.hit && (mine || i < 4)) sfx('osuma', { vol: mine ? 0.4 : 0.18, rate: 0.9 + Math.random() * 0.2 }, 300);
      if (s.got > o.got) sfx('nousu', { vol: mine ? 0.3 : 0.15 }, 880);
      if (s.stun && !o.stun && mine) sfx('tomahdys', { vol: 0.4 }, 120);
    });
  }
  seen = st;
}

// ---- The match ----
let mode = 'menu', world = null, me = null, brains = [], result = null, endT = 0;
let net = null;   // the match with friends (net.js), null alone
function soloMatch(resume) {
  const taken = [hat];
  const players = [{ id: 'me', name: 'Sinä', hat, kind: 'me' }];
  for (let i = 0; i < 3; i++) {
    const h = hatFor(taken, hat + 1 + i * 2); taken.push(h);
    players.push({ id: 'cpu' + i, name: CPU_NAMES[(i + floeN * 2) % CPU_NAMES.length], hat: h, kind: 'cpu' });
  }
  world = newWorld(floeN, players, (Date.now() % 1e9) >>> 0);
  if (resume) {
    // A reload restarts the erä it was in, keeping the match's stars (design, #478).
    resume.stars.forEach((n, i) => { if (world.seals[i]) world.seals[i].stars = clamp(Math.floor(n) || 0, 0, STARS_TO_WIN - 1); });
    world.era = Math.max(1, Math.floor(resume.era) || 1);
    resetEra(world);
  }
  me = world.seals[0];
  const F = FLOES[floeN - 1];
  brains = world.seals.map((s, i) => s.kind === 'cpu' ? cpuBrain(F.cpu, world.seed + i * 31) : null);
  saveMatch();
  startPlay();
}
function saveMatch() {
  if (!world || net) return;
  // Between erät the next one is the one a reload plays.
  save('kesken1', { f: world.floe, era: world.ph === 'erä' ? world.era + 1 : world.era, stars: world.seals.map(s => s.stars) });
}
function readMatch() {
  const m = load('kesken1', null);
  if (!m || typeof m !== 'object' || !Array.isArray(m.stars) || m.stars.length !== 4) return null;
  const f = Math.floor(m.f);
  if (!(f >= 1 && f <= open)) return null;
  return { f, era: m.era, stars: m.stars };
}
function startPlay() {
  mode = 'play'; result = null; endT = 0; seen = null;
  stick = null;
  hideAll();
  wake();
}
// Alone: the match is over. A win counts, opens the next floe and goes on the high-score list.
// Counted the moment the deciding erä is won, so a reload before the end screen cannot lose it.
function soloRecord() {
  const won = world.winner === me.id;
  drop('kesken1');
  let opened = 0;
  if (won) {
    wins++; save('voitot', wins);
    if (floeN === open && open < FLOES.length) { open++; save('auki', open); opened = open; }
    if (window.AiPelitScores) AiPelitScores.submit(wins);
  }
  result = { won, opened, rows: rowsOf(world), wins };
}
function soloEnd() { if (!result) soloRecord(); showEnd(); }
function rowsOf(w) {
  return w.seals.slice().sort((a, b) => (b.id === w.winner) - (a.id === w.winner) || b.stars - a.stars)
    .map(s => ({ id: s.id, name: s === me ? 'Sinä' : s.name, stars: s.stars, hat: s.hat, me: s === me, cpu: s.kind === 'cpu', helped: !!s.helped }));
}

// ---- The fingers ----
// A finger anywhere but the button is a floating stick: where it touched down is the middle, and
// how far it has moved from there (up to STICK px) pushes the seal that way. The "Töni" button
// lunges on touch-down, because timing is the game (spec).
const STICK = 56;
let stick = null, lungeFlash = 0;
function button() {
  const r = LAND ? 46 : 48;
  return { x: W - SAFE_R - r - (LAND ? 24 : 22), y: H - SAFE_B - r - (LAND ? 18 : 26), r };
}
c.addEventListener('pointerdown', e => {
  if (mode !== 'play' && mode !== 'netplay') return;
  e.preventDefault();
  const b = button();
  if (Math.hypot(e.clientX - b.x, e.clientY - b.y) < b.r + 16) { lunge(); return; }
  // A second finger that just misses the button does not take the stick from the first (#479 review).
  if (stick) return;
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
  stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
});
c.addEventListener('pointermove', e => {
  if (!stick || e.pointerId !== stick.id) return;
  stick.x = e.clientX; stick.y = e.clientY;
  // A finger far past the stick's reach drags the middle along, so it never needs to come back.
  const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy);
  if (d > STICK * 1.6) { stick.x0 = stick.x - dx / d * STICK * 1.6; stick.y0 = stick.y - dy / d * STICK * 1.6; }
});
function lift(e) { if (stick && e.pointerId === stick.id) stick = null; }
c.addEventListener('pointerup', lift);
c.addEventListener('pointercancel', lift);
function stickInput() {
  if (!stick) return [0, 0];
  let dx = (stick.x - stick.x0) / STICK, dy = (stick.y - stick.y0) / STICK;
  const m = Math.hypot(dx, dy);
  if (m < 0.12) return [0, 0];
  if (m > 1) { dx /= m; dy /= m; }
  return [dx, dy];
}
function lunge() {
  if (!me || me.out || !world || world.ph !== 'play') return;   // the button is only there in play
  lungeFlash = 0.15;
  if (net) netLunge();
  else me.want = me.lunges + 1;
}

// ---- Menus (DOM, over the canvas) ----
const $ = id => document.getElementById(id);
function hideAll() { for (const id of ['menu', 'end', 'pause']) $(id).hidden = true; }
// ⏸ pauses a game alone; from there "Lopeta peli" ends the match and goes to the menu.
// In a room the "‹ Pelit" chip's menu already ends a round (#392), so the button is only for solo.
function pauseGame() {
  if (mode !== 'play' || !world) return;
  mode = 'pause'; stick = null; if (me) { me.ix = 0; me.iy = 0; }
  sfx('valinta', { vol: 0.3 }); $('pause').hidden = false; wake();
}
$('pauseBtn').addEventListener('click', pauseGame);
$('resume').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); $('pause').hidden = true; mode = 'play'; last = 0; wake(); });
$('quit').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); drop('kesken1'); showMenu(); });
// Leaving the app mid-erä pauses too, so the seal is not pushed in while the phone is away.
document.addEventListener('visibilitychange', () => { if (document.hidden) pauseGame(); });
function showMenu() {
  mode = 'menu'; world = null; me = null; seen = null;
  hideAll(); $('menu').hidden = false;
  const box = $('floes'); box.innerHTML = '';
  FLOES.forEach((F, i) => {
    const n = i + 1, b = document.createElement('button');
    b.className = 'floe' + (n === floeN ? ' on' : '');
    b.disabled = n > open;
    b.innerHTML = '<b>' + n + '. ' + F.name + '</b><small>' + (n > open ? '🔒 Voita edellinen' : FLOE_NOTES[i]) + '</small>';
    b.addEventListener('click', () => { floeN = n; save('lautta', n); sfx('valinta', { vol: 0.3 }); showMenu(); });
    box.appendChild(b);
  });
  $('wins').textContent = wins ? 'Voitettuja otteluita: ' + wins : '';
  hatLabel();
  wake();
}
const FLOE_NOTES = ['Iso ja pyöreä', 'Pienempi ja kuoppaisempi', 'Lumipalloja vierii yli', 'Jäähän aukeaa railoja', 'Kaksi lauttaa, välissä vettä'];
function hatLabel() { const b = $('hat'); b.innerHTML = '🎩 Hattu: <span style="color:' + HATS[hat].c + '">●</span> ' + HATS[hat].name; }
function showEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result;
  $('endTitle').textContent = r.net ? (r.won ? 'Voitit ottelun!' : (r.winnerName || 'Joku') + ' voitti ottelun') : r.won ? 'Voitit ottelun!' : 'Hävisit ottelun';
  $('endNote').textContent = r.helped ? 'Tietokone pelasi puolestasi' : r.net ? '' : r.won ? 'Voitettuja otteluita: ' + r.wins : 'Yritä uudestaan!';
  $('endOpen').hidden = !r.opened;
  if (r.opened) $('endOpen').textContent = '🔓 ' + FLOES[r.opened - 1].name + ' aukesi!';
  $('again').textContent = r.net ? 'Takaisin huoneeseen' : 'Uusi ottelu';
  $('toMenu').hidden = !!r.net;
  const list = $('endList'); list.innerHTML = '';
  r.rows.forEach(row => {
    const li = document.createElement('li');
    if (row.me) li.className = 'me';
    li.innerHTML = '<span><i style="background:' + HATS[row.hat % HATS.length].c + '"></i>' + esc(row.name) + (row.cpu || row.helped ? ' 🤖' : '') + '</span><b>' + '★'.repeat(row.stars) + '<span class="dim">' + '★'.repeat(Math.max(0, STARS_TO_WIN - row.stars)) + '</span></b>';
    list.appendChild(li);
  });
  sfx(r.won ? 'voitto' : 'tappio', { vol: 0.3 });
  wake();
}
function esc(s) { return String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }
$('go').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloMatch(null); });
$('hat').addEventListener('click', () => { hat = (hat + 1) % HATS.length; save('hattu', hat); sfx('valinta', { vol: 0.3 }); hatLabel(); });
$('again').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (result && result.net) backRoom(); else soloMatch(null); });
$('friends').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (window.AiPelitRooms) AiPelitRooms.open(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });

// ---- Drawing ----
// The play area: portrait leaves the lower part for the thumbs; sideways the floe sits in the middle.
function playBox() {
  let x0 = SAFE_L + 8, x1 = W - SAFE_R - 8, y0 = SAFE_T + 58, y1 = H - SAFE_B - 128;
  if (LAND) { y0 = SAFE_T + 44; y1 = H - SAFE_B - 8; x0 = SAFE_L + 120; x1 = W - SAFE_R - 120; }
  return { x0, x1, y0, y1 };
}
function view(w) {
  const { x0, x1, y0, y1 } = playBox();
  let bx0 = Infinity, bx1 = -Infinity, by0 = Infinity, by1 = -Infinity;
  for (const p of w.parts) { bx0 = Math.min(bx0, p.x - p.r0); bx1 = Math.max(bx1, p.x + p.r0); by0 = Math.min(by0, p.y - p.r0); by1 = Math.max(by1, p.y + p.r0); }
  const m = 1.2, s = Math.min((x1 - x0) / (bx1 - bx0 + 2 * m), (y1 - y0) / (by1 - by0 + 2 * m));
  return { s, ox: (x0 + x1) / 2 - (bx0 + bx1) / 2 * s, oy: (y0 + y1) / 2 - (by0 + by1) / 2 * s };
}
let V = { s: 20, ox: 180, oy: 300 }, clock = 0;
const X = x => V.ox + x * V.s, Y = y => V.oy + y * V.s;
function drawSea() {
  const g = cx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#0d3a66'); g.addColorStop(1, '#0a2a4c');
  cx.fillStyle = g; cx.fillRect(0, 0, W, H);
  cx.strokeStyle = 'rgba(160,210,255,.13)'; cx.lineWidth = 2;
  for (let i = 0; i < 14; i++) {
    const y = ((i * 61 + clock * 9) % (H + 40)) - 20, x = (i * 97) % W;
    cx.beginPath(); cx.moveTo(x - 30, y); cx.quadraticCurveTo(x, y - 6, x + 30, y); cx.stroke();
  }
}
function floePath(p, dy) {
  cx.beginPath();
  for (let k = 0; k <= 72; k++) {
    const a = k / 72 * TAU, r = edgeAt(p, a);
    const x = X(p.x + Math.cos(a) * r), y = Y(p.y + Math.sin(a) * r) + dy;
    k ? cx.lineTo(x, y) : cx.moveTo(x, y);
  }
  cx.closePath();
}
function drawFloe(w) {
  for (const p of w.parts) {
    floePath(p, Math.max(4, V.s * 0.3)); cx.fillStyle = '#7fb4d8'; cx.fill();   // the ice's side
    floePath(p, 0);
    const g = cx.createRadialGradient(X(p.x), Y(p.y), 0, X(p.x), Y(p.y), p.r0 * V.s);
    g.addColorStop(0, '#f4fbff'); g.addColorStop(1, '#d4ebfa');
    cx.fillStyle = g; cx.fill();
    cx.strokeStyle = 'rgba(255,255,255,.9)'; cx.lineWidth = 2; cx.stroke();
  }
  // A piece about to break off: a crack across it, flashing.
  for (const b of w.warn) {
    const p = w.parts[b.p], a0 = (b.i - 1) / WEDGES * TAU, a1 = (b.i + 2) / WEDGES * TAU;
    const rIn = edgeAt(p, (a0 + a1) / 2) - 1.6 * w.scale;
    cx.strokeStyle = Math.floor(clock * 8) % 2 ? '#2a6fa8' : '#5fa0d0'; cx.lineWidth = 2.5;
    cx.beginPath();
    for (let k = 0; k <= 8; k++) {
      const a = a0 + (a1 - a0) * k / 8, r = rIn + (k % 2 ? 0.25 : -0.2);
      const x = X(p.x + Math.cos(a) * r), y = Y(p.y + Math.sin(a) * r);
      k ? cx.lineTo(x, y) : cx.moveTo(x, y);
    }
    cx.stroke();
  }
  for (const o of w.holes) {
    if (o.open > 0) {
      cx.fillStyle = '#0d3a66'; cx.beginPath(); cx.arc(X(o.x), Y(o.y), o.r * V.s, 0, TAU); cx.fill();
      cx.strokeStyle = '#7fb4d8'; cx.lineWidth = 3; cx.stroke();
    } else {
      cx.strokeStyle = Math.floor(clock * 8) % 2 ? '#2a6fa8' : '#8ab8dc'; cx.lineWidth = 2;
      for (let k = 0; k < 5; k++) {
        const a = k * 1.3; cx.beginPath(); cx.moveTo(X(o.x), Y(o.y));
        cx.lineTo(X(o.x + Math.cos(a) * o.r), Y(o.y + Math.sin(a) * o.r)); cx.stroke();
      }
    }
  }
}
function drawRing(w) {
  const r = w.ring;
  if (!r) return;
  // The gull flies in with its lantern, then the ring glows on the ice.
  const k = r.come > 0 ? r.come / RING_COME : 0;
  const gx = X(r.x) - k * 160, gy = Y(r.y) - 60 - k * 80;
  if (r.come <= 0) {
    const pulse = 0.75 + Math.sin(clock * 6) * 0.25;
    const g = cx.createRadialGradient(X(r.x), Y(r.y), 0, X(r.x), Y(r.y), RING_R * V.s * 1.4);
    g.addColorStop(0, 'rgba(255,240,140,' + 0.55 * pulse + ')'); g.addColorStop(1, 'rgba(255,220,80,0)');
    cx.fillStyle = g; cx.beginPath(); cx.arc(X(r.x), Y(r.y), RING_R * V.s * 1.4, 0, TAU); cx.fill();
    cx.strokeStyle = 'rgba(255,200,40,' + pulse + ')'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(X(r.x), Y(r.y), RING_R * V.s, 0, TAU); cx.stroke();
    cx.font = '700 ' + Math.round(V.s * 1.1) + 'px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'middle';
    cx.fillStyle = '#c88a00'; cx.fillText('?', X(r.x), Y(r.y));
  }
  cx.strokeStyle = '#fff'; cx.lineWidth = 3; cx.lineCap = 'round';
  const fl = Math.sin(clock * 10) * 5;
  cx.beginPath(); cx.moveTo(gx - 14, gy - 4 + fl); cx.quadraticCurveTo(gx - 6, gy - 8, gx, gy); cx.quadraticCurveTo(gx + 6, gy - 8, gx + 14, gy - 4 + fl); cx.stroke();
  cx.strokeStyle = 'rgba(255,255,255,.5)'; cx.lineWidth = 1;
  cx.beginPath(); cx.moveTo(gx, gy); cx.lineTo(gx, gy + 10); cx.stroke();
  cx.fillStyle = '#ffd84a'; cx.beginPath(); cx.arc(gx, gy + 12, 3.5, 0, TAU); cx.fill();
}
function drawSnow(w) {
  for (const s of w.snow) {
    const x = X(s.x), y = Y(s.y), r = s.r * V.s;
    cx.fillStyle = 'rgba(0,30,60,.25)'; cx.beginPath(); cx.ellipse(x + 3, y + 4, r, r * 0.8, 0, 0, TAU); cx.fill();
    const g = cx.createRadialGradient(x - r * 0.3, y - r * 0.3, 0, x, y, r);
    g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#c8dcec');
    cx.fillStyle = g; cx.beginPath(); cx.arc(x, y, r, 0, TAU); cx.fill();
    cx.strokeStyle = 'rgba(120,160,200,.5)'; cx.lineWidth = 1.5;
    const a = s.roll * 1.5;
    cx.beginPath(); cx.arc(x, y, r * 0.6, a, a + 1.6); cx.stroke();
  }
}
function drawSeal(w, sl) {
  const R = radiusOf(sl) * V.s;
  if (sl.out) {
    // In the water: a head bobbing where it went in, with rings. Lohkare's end comes first: the block
    // drops onto the seal, which squashes flat, shards fly, and both sink through the ice.
    const t = sl.out, x = X(sl.outX), y = Y(sl.outY);
    if (sl.crushed && t < CRUSH_T) {
      const s = R * 2.2;
      if (t < CRUSH_DROP) {
        const k = t / CRUSH_DROP;
        cx.fillStyle = '#8a93a3'; cx.beginPath(); cx.ellipse(x, y, R, R * (1 - 0.3 * k * k), 0, 0, TAU); cx.fill();
        cx.fillStyle = '#bfe6ff'; cx.fillRect(x - s / 2, y - s / 2 - (1 - k * k) * 70, s, s);
        cx.strokeStyle = '#7fb4d8'; cx.lineWidth = 2; cx.strokeRect(x - s / 2, y - s / 2 - (1 - k * k) * 70, s, s);
        return;
      }
      const k = Math.min(1, (t - CRUSH_DROP) / (CRUSH_T - CRUSH_DROP - 0.2)), d = t - CRUSH_DROP;
      cx.fillStyle = '#0d3a66'; cx.beginPath(); cx.arc(x, y, R * 1.25, 0, TAU); cx.fill();
      cx.fillStyle = '#8a93a3'; cx.beginPath(); cx.ellipse(x, y, R * 1.2 * (1 - k * 0.6), R * 0.4 * (1 - k), 0, 0, TAU); cx.fill();
      const b = s * (1 - k * 0.7), sh = (1 - k) * Math.sin(t * 60) * 2;
      cx.globalAlpha = 1 - k; cx.fillStyle = '#bfe6ff'; cx.fillRect(x - b / 2 + sh, y - b / 2, b, b);
      for (let i = 0; i < 8; i++) {
        const a = i * TAU / 8 + sl.i, r = R + d * (40 + (i % 3) * 12);
        cx.fillRect(x + Math.cos(a) * r - 3, y + Math.sin(a) * r - 3, 6, 6);
      }
      cx.globalAlpha = 1;
      return;
    }
    const tw = sl.crushed ? t - CRUSH_T : t;
    cx.strokeStyle = 'rgba(220,240,255,' + Math.max(0, 0.7 - tw * 0.3) + ')'; cx.lineWidth = 2;
    for (let k = 0; k < 3; k++) { const rr = (tw * 30 + k * 12) % 50; cx.beginPath(); cx.ellipse(x, y, rr, rr * 0.6, 0, 0, TAU); cx.stroke(); }
    cx.fillStyle = '#7a7f8a'; cx.beginPath(); cx.arc(x, y + Math.sin(clock * 3 + sl.i) * 2, V.s * 0.45, 0, TAU); cx.fill();
    cx.fillStyle = HATS[sl.hat % HATS.length].c; cx.beginPath(); cx.arc(x, y - V.s * 0.2 + Math.sin(clock * 3 + sl.i) * 2, V.s * 0.28, Math.PI, TAU); cx.fill();
    return;
  }
  // Wobbling on the edge: rocking over the water, flippers flailing.
  const tee = sl.teeter > 0, rock = tee ? Math.sin(clock * 9 + sl.i) : 0;
  const x = X(sl.x + Math.cos(sl.ta) * rock * 0.12), y = Y(sl.y + Math.sin(sl.ta) * rock * 0.12), a = sl.face + rock * 0.4;
  if (sl === me) { cx.strokeStyle = '#ffd84a'; cx.lineWidth = 3; cx.beginPath(); cx.arc(x, y, R + 5, 0, TAU); cx.stroke(); }
  cx.fillStyle = 'rgba(0,40,80,.22)'; cx.beginPath(); cx.ellipse(x + 3, y + 4, R * 1.05, R * 0.85, 0, 0, TAU); cx.fill();
  cx.save(); cx.translate(x, y); cx.rotate(a);
  // The lunge's streak behind it.
  if (sl.lungeT > 0) {
    cx.fillStyle = 'rgba(255,255,255,.6)';
    for (let k = 1; k <= 3; k++) { cx.beginPath(); cx.ellipse(-R * (0.6 + k * 0.5), 0, R * 0.5 / k, R * 0.9 / k, 0, 0, TAU); cx.fill(); }
  }
  // Body: a fat teardrop, back flippers behind, front flippers at the sides.
  const body = sl.stun > 0 ? '#9aa0b0' : '#6d7482';
  cx.fillStyle = '#4f5562';
  cx.beginPath(); cx.ellipse(-R * 1.15, -R * 0.32, R * 0.36, R * 0.18, -0.5, 0, TAU); cx.fill();
  cx.beginPath(); cx.ellipse(-R * 1.15, R * 0.32, R * 0.36, R * 0.18, 0.5, 0, TAU); cx.fill();
  const fl = Math.sin(clock * 12 + sl.i) * (tee ? 0.9 : Math.hypot(sl.vx, sl.vy) > 0.5 ? 0.3 : 0.05);
  cx.beginPath(); cx.ellipse(R * 0.1, -R * 0.85, R * 0.38, R * 0.16, -0.6 + fl, 0, TAU); cx.fill();
  cx.beginPath(); cx.ellipse(R * 0.1, R * 0.85, R * 0.38, R * 0.16, 0.6 - fl, 0, TAU); cx.fill();
  cx.fillStyle = body; cx.beginPath(); cx.ellipse(-R * 0.15, 0, R * 1.05, R * 0.82, 0, 0, TAU); cx.fill();
  cx.fillStyle = 'rgba(255,255,255,.18)'; cx.beginPath(); cx.ellipse(-R * 0.3, -R * 0.25, R * 0.6, R * 0.3, 0, 0, TAU); cx.fill();
  // Head, face forwards, with the hat on top.
  cx.fillStyle = body; cx.beginPath(); cx.arc(R * 0.7, 0, R * 0.55, 0, TAU); cx.fill();
  cx.fillStyle = '#222'; cx.beginPath(); cx.arc(R * 1.05, -R * 0.22, R * 0.09, 0, TAU); cx.arc(R * 1.05, R * 0.22, R * 0.09, 0, TAU); cx.fill();
  cx.fillStyle = '#2a2a2a'; cx.beginPath(); cx.arc(R * 1.22, 0, R * 0.08, 0, TAU); cx.fill();
  cx.fillStyle = HATS[sl.hat % HATS.length].c; cx.beginPath(); cx.arc(R * 0.6, 0, R * 0.38, 0, TAU); cx.fill();
  cx.fillStyle = '#fff'; cx.beginPath(); cx.arc(R * 0.6, 0, R * 0.14, 0, TAU); cx.fill();
  cx.restore();
  drawMarks(w, sl, x, y, R, false);
}
// What floats over a seal: stun stars, the wobble's press dots, the fuse, the name. In 3D the fuse
// itself is a model, so only its seconds are written here.
function drawMarks(w, sl, x, y, R, d3) {
  const tee = sl.teeter > 0;
  if (sl.stun > 0) {
    cx.fillStyle = '#ffe14a'; cx.font = '700 ' + Math.round(R) + 'px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'middle';
    for (let k = 0; k < 3; k++) { const b = clock * 5 + k * 2.1; cx.fillText('✦', x + Math.cos(b) * R, y - R * 1.1 + Math.sin(b) * R * 0.3); }
  }
  // The presses it still needs, as dots over it.
  if (tee) for (let k = 0; k < TEETER_N; k++) {
    cx.fillStyle = k < sl.mash ? '#ffb000' : 'rgba(255,255,255,.85)';
    cx.beginPath(); cx.arc(x + (k - (TEETER_N - 1) / 2) * 12, y - R - 10, 4.5, 0, TAU); cx.fill();
    cx.strokeStyle = 'rgba(20,50,90,.6)'; cx.lineWidth = 1; cx.stroke();
  }
  // The fuse over it: a thunder cloud or a hanging ice block, with its seconds left.
  if (sl.fuse && d3) {
    const f = sl.fuse;
    shadowText((f.k === 'ukko' ? '⚡' : '') + Math.ceil(f.t), x, y - R - 30, 15, f.k === 'ukko' ? '#ffe14a' : '#dff4ff', 'center', 900);
  } else if (sl.fuse) {
    const fy = y - R - 22, f = sl.fuse;
    if (f.k === 'ukko') {
      cx.fillStyle = '#5a6070'; for (const [dx, rr] of [[-9, 8], [0, 11], [9, 8]]) { cx.beginPath(); cx.arc(x + dx, fy, rr, 0, TAU); cx.fill(); }
      cx.fillStyle = '#ffe14a'; cx.font = '800 14px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText('⚡' + Math.ceil(f.t), x, fy + 1);
    } else {
      const s2 = 13 + (LOHK_T - f.t) * 1.2;
      cx.fillStyle = 'rgba(0,40,80,.25)'; cx.beginPath(); cx.ellipse(x, y, s2 * 0.8, s2 * 0.55, 0, 0, TAU); cx.fill();
      cx.fillStyle = '#bfe6ff'; cx.fillRect(x - s2 / 2, fy - s2 / 2 - 4, s2, s2);
      cx.strokeStyle = '#7fb4d8'; cx.lineWidth = 2; cx.strokeRect(x - s2 / 2, fy - s2 / 2 - 4, s2, s2);
      cx.fillStyle = '#1a4a7a'; cx.font = '800 13px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText(Math.ceil(f.t), x, fy - 4);
    }
  }
  // Names only with friends; alone the hats tell the seals apart and the ring marks mine.
  if (net && sl !== me) {
    cx.font = '600 11px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'top';
    cx.fillStyle = 'rgba(0,20,50,.55)'; cx.fillText(sl.name, x + 1, y + R + 5);
    cx.fillStyle = '#fff'; cx.fillText(sl.name, x, y + R + 4);
  }
}
function shadowText(t, x, y, size, col, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(0,10,30,.6)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = col; cx.fillText(t, x, y);
}
// The stars of every seal along the top, the countdown, the erä's winner, the button and the stick.
function drawHUD(w) {
  // Upright: rows of four along the top, right of the "‹ Pelit" chip. Sideways: one column in the
  // left margin under it, so the top bar stays free for the room's 🎤 chip.
  const n = w.seals.length, top = SAFE_T + 14;
  const x0 = SAFE_L + 92, x1 = W - SAFE_R - (LAND || W < 360 || net ? 12 : 52), cw = Math.min(78, (x1 - x0) / Math.min(n, 4));
  w.seals.forEach((s, i) => {
    const x = LAND ? SAFE_L + 14 : x0 + (i % 4) * cw, y = LAND ? SAFE_T + 50 + i * 22 : top + Math.floor(i / 4) * 20;
    cx.globalAlpha = s.out ? 0.5 : 1;
    cx.fillStyle = HATS[s.hat % HATS.length].c; cx.beginPath(); cx.arc(x + 6, y + 6, 6, 0, TAU); cx.fill();
    if (s === me) { cx.strokeStyle = '#ffd84a'; cx.lineWidth = 2; cx.stroke(); }
    // Won stars gold, the rest faint (an outline star reads as a full one in some fonts).
    for (let k = 0; k < STARS_TO_WIN; k++) {
      if (k < s.stars) shadowText('★', x + 16 + k * 12, y + 6, 12, '#ffd84a', 'left', 700);
      else { cx.font = '700 12px system-ui,sans-serif'; cx.textAlign = 'left'; cx.fillStyle = 'rgba(255,255,255,.28)'; cx.fillText('★', x + 16 + k * 12, y + 6); }
    }
    cx.globalAlpha = 1;
  });
  const midY = LAND ? H * 0.45 : (SAFE_T + 58 + H - SAFE_B - 128) / 2;
  if (w.ph === 'count') {
    const k = Math.ceil(w.cd);
    shadowText('Erä ' + w.era, W / 2, midY - 60, 20, '#cfe6ff', 'center', 800);
    shadowText(k > 0 ? String(k) : 'TÖNI!', W / 2, midY, 60, '#fff', 'center', 900);
  } else if (w.ph === 'play' && w.t < 0.8) shadowText('TÖNI!', W / 2, midY, 52, '#fff', 'center', 900);
  if (w.ph === 'erä' || w.ph === 'over') {
    const win = w.seals.find(s => s.id === w.eraWin);
    shadowText(win ? (win === me ? 'Voitit erän!' : win.name + ' voitti erän!') : 'Tasapeli – erä uusiksi', W / 2, midY, 24, '#fff', 'center', 900);
  }
  // In the water above the floe upright, under the star rows; sideways the floe fills the height, so
  // over its top part. Warm, so it reads on white ice as on the sea.
  if (w.ph === 'play' && w.t >= SUDDEN_AT && w.t < SUDDEN_AT + 2.5)
    shadowText('Lautta sulaa!', W / 2, LAND ? midY - 80 : top + (n > 4 ? 66 : 46), 26, '#ff9d42', 'center', 900);
  // Wobbling: in the water just above the button it means, never over the floe.
  if (me && me.teeter > 0 && w.ph === 'play') {
    const b = button();
    shadowText('Hakkaa Töniä!', LAND ? Math.min(b.x, W - SAFE_R - 92) : W / 2, b.y - b.r - 26, LAND ? 19 : 26, '#ffd84a', 'center', 900);
  }
  if (me && me.out && w.ph === 'play') shadowText('Molskis!', W / 2, midY - 40, 30, '#9fd8ff', 'center', 900);
  if (me && me.got && me.gotK && me.gotT < 1.6) shadowText(POWER_NAMES[me.gotK] + '!', W / 2, midY + 50, 22, '#ffd84a', 'center', 900);
  // The pull: its base and its knob.
  if (stick && me && !me.out) {
    cx.strokeStyle = 'rgba(255,255,255,.35)'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(stick.x0, stick.y0, STICK, 0, TAU); cx.stroke();
    const [ix, iy] = stickInput();
    cx.fillStyle = 'rgba(255,255,255,.5)'; cx.beginPath(); cx.arc(stick.x0 + ix * STICK, stick.y0 + iy * STICK, 20, 0, TAU); cx.fill();
  }
  // The button, its ring filling back over the cooldown.
  if (me && (w.ph === 'play' || w.ph === 'count')) {
    const b = button(), tee = me.teeter > 0, ready = (me.cd <= 0 || tee) && !me.out;
    cx.fillStyle = lungeFlash > 0 ? '#ffd84a' : ready ? 'rgba(224,40,58,.9)' : 'rgba(120,60,70,.7)';
    // Wobbling, the button throbs: press it again and again.
    cx.beginPath(); cx.arc(b.x, b.y, b.r * (tee ? 1 + Math.abs(Math.sin(clock * 10)) * 0.12 : 1), 0, TAU); cx.fill();
    if (me.cd > 0 && !tee) {
      cx.strokeStyle = '#fff'; cx.lineWidth = 4;
      cx.beginPath(); cx.arc(b.x, b.y, b.r - 4, -Math.PI / 2, -Math.PI / 2 + TAU * (1 - me.cd / LUNGE_CD)); cx.stroke();
    }
    shadowText('Töni', b.x, b.y, 20, '#fff', 'center', 900);
  }
  if (tutorial && me && w.ph === 'play' && w.t < 8 && w.era === 1) {
    // Above the floe upright, in the top bar sideways: never under a thumb or the button.
    const ty = LAND ? SAFE_T + 14 : SAFE_T + 46;
    shadowText('Vedä sormella: hylje liukuu', W / 2, ty, 15, '#fff', 'center', 700);
    shadowText('Töni: syöksy toista päin!', W / 2, ty + 20, 15, '#fff', 'center', 700);
  }
  if (net && window.AiPelitRooms && AiPelitRooms.paused) shadowText('Odotetaan kaveria…', W / 2, midY + 90, 18, '#fff', 'center', 800);
}
let tutorial = !load('osattu', false);
function draw(dt) {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  // In the menus an empty floe floats behind.
  const w = world || menuWorld();
  V = view(w);
  if (window.J3D && J3D.ready) {
    // The scene in 3D underneath; this canvas keeps only what floats over it.
    J3D.show(true);
    cx.clearRect(0, 0, W, H);
    J3D.render(w, clock, playBox(), me);
    if (w.ring && w.ring.come <= 0) { const [rx, ry] = J3D.project(w.ring.x, 0.9, w.ring.y); shadowText('?', rx, ry, 22, '#ffd84a', 'center', 900); }
    for (const sl of w.seals) if (!sl.out) {
      const R = radiusOf(sl), [sx, sy] = J3D.project(sl.x, R * 1.4, sl.y), [ex] = J3D.project(sl.x + R, R * 1.4, sl.y);
      drawMarks(w, sl, sx, sy, Math.abs(ex - sx), true);
    }
  } else {
    if (window.J3D && J3D.show) J3D.show(false);
    drawSea();
    drawFloe(w);
    drawRing(w);
    drawSnow(w);
    for (const sl of w.seals) if (sl.out) drawSeal(w, sl);
    for (const sl of w.seals) if (!sl.out) drawSeal(w, sl);
  }
  if (mode === 'netwait') shadowText('Odotetaan muita…', W / 2, H * 0.4, 20, '#fff', 'center', 800);
  if (world && (mode === 'play' || mode === 'netplay')) drawHUD(world);
}
let mw = null;
function menuWorld() { if (!mw || mw.floe !== floeN) mw = newWorld(floeN, [], 1); return mw; }

// ---- The main loop ----
let raf = 0, last = 0, still = 0;
function wake() { still = 0; if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
function frame(now) {
  raf = 0;
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60; last = now;
  clock += dt;
  if (lungeFlash > 0) lungeFlash -= dt;
  if (net) netTick(dt);
  else if (mode === 'play' && world) {
    const [ix, iy] = stickInput();
    me.ix = ix; me.iy = iy;
    world.seals.forEach((s, i) => { if (brains[i]) cpuThink(world, s, brains[i], dt); });
    const ph = world.ph;
    step(world, dt);
    // Saved at the start and after each erä, never mid-erä (design review, #478).
    if (ph !== 'erä' && world.ph === 'erä' && !world.winner) saveMatch();
    if (world.winner && !result) soloRecord();
    if (tutorial && me.lunges > 0 && world.ph !== 'count') { tutorial = false; save('osattu', true); }
    if (world.over) { endT += dt; if (endT > 0.3) soloEnd(); }
  }
  if (me) { if (me.got !== gotSeen) { gotSeen = me.got; me.gotT = 0; } me.gotT = (me.gotT || 0) + dt; }
  soundsOf(mode === 'play' || mode === 'netplay' ? world : null);
  // v3 (#480): on a guest the other seals are drawn where their tracks glide (net.js), then put back
  // at the newest spot heard.
  const kept = net && typeof asDrawn === 'function' ? asDrawn() : null;
  draw(dt);
  if (kept) putBack(kept);
  document.body.classList.toggle('playing', mode === 'play' || mode === 'pause' || mode === 'netplay' || mode === 'netwait');
  document.body.classList.toggle('solo', mode === 'play' && !net);
  const moving = mode === 'play' || mode === 'netplay' || mode === 'netwait' || mode === 'menu' || mode === 'end';
  if (moving || still++ < 2) raf = requestAnimationFrame(frame);
}
let gotSeen = 0;
resize();
const resumed = !(window.AiPelitRooms && AiPelitRooms.inRoom) ? readMatch() : null;
if (window.AiPelitRooms && AiPelitRooms.inRoom) hideAll();
else if (resumed) { floeN = resumed.f; soloMatch(resumed); }
else showMenu();
