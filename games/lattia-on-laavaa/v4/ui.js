'use strict';
// Lattia on laavaa v4: the fingers, the menus, the saves, the sounds, the 2D layer over the 3D
// picture (time, buttons, stick, names) and the main loop. Alone the phone runs the whole round;
// with friends net.js does.

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
  if (window.L3D && L3D.resize) L3D.resize();
}
addEventListener('resize', resize);
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);
document.addEventListener('fullscreenchange', resize);

// ---- Saves (ai-pelit:lattia-on-laavaa:*, shared by every version) ----
const KEY = 'ai-pelit:lattia-on-laavaa:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
let open = clamp(Math.floor(load('auki', 1)) || 1, 1, ROOMS.length);      // rooms opened
let roomN = clamp(Math.floor(load('huone', 1)) || 1, 1, open);
const best = ROOMS.map((_, i) => Math.max(0, +load('paras-' + (i + 1), 0) || 0));   // seconds survived
let tutorial = !load('osattu', false);

// ---- The outfit (v4, #572): one choice for every 3D game (lib/asut3d-1, ai-pelit:_asut:3d) ----
// The phone's own kid wears it; in a room the id goes with the kid to every phone (net.js). A pick
// made here, or in another 3D game while this page was out of view, dresses the kid at once.
let outfit = null;
if (window.AiPelitAsut3d && window.AiPelitOutfits) {
  outfit = AiPelitAsut3d.setup({
    default: 'haalari', button: 'asu',
    change(o) { outfit = o; if (me) me.o = o.id; if (typeof sendOutfit === 'function') sendOutfit(); },
  });
} else { const b = document.getElementById('asu'); if (b) b.hidden = true; }
const outfitId = () => outfit ? outfit.id : '';

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['puu', 'hyppy', 'kupla', 'suhahdus', 'osuma', 'gongi', 'valinta', 'onnistui', 'voitto', 'tappio']);
let ac = null;
function beep(f, d, vol) {
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = f; g.gain.value = vol || 0.04; g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + d);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + d);
  } catch (e) {}
}
const sfx = (name, opts, f) => (S && S.play(name, opts)) || (f && beep(f, 0.12, 0.035));
// What changed since the last frame, on any phone: a jump, a landing, a shove, a fall.
let seen = null;
function soundsOf(w) {
  if (!w) { seen = null; return; }
  const now = w.kids.map(k => ({ out: k.out, g: k.ground, j: k.jumps || 0, sh: k.shoves, st: k.stun > 0 }));
  if (seen && seen.n === w.kids.length && seen.seed === w.seed) {
    if (seen.ph === 'count' && w.ph === 'play') sfx('gongi', { vol: 0.25 }, 520);
    now.forEach((s, i) => {
      const o = seen.k[i], mine = w.kids[i] === me, v = mine ? 1 : 0.4;
      if (s.out && !o.out) sfx('kupla', { vol: 0.4 * v, rate: 0.7 }, 180);
      if (!s.out && s.j > o.j && mine) sfx('hyppy', { vol: 0.25 }, 600);
      if (!s.out && s.g && !o.g && mine) sfx('puu', { vol: 0.2 }, 240);
      if (s.sh > o.sh && mine) sfx('suhahdus', { vol: 0.3 });
      if (s.st && !o.st) sfx('osuma', { vol: 0.35 * v, rate: 0.9 + Math.random() * 0.2 }, 300);
    });
  }
  seen = { n: w.kids.length, seed: w.seed, ph: w.ph, k: now };
}

// ---- The round ----
let mode = 'menu', world = null, me = null, brains = [], result = null, acc = 0, endT = 0;
let net = null;      // the round with friends (net.js), null alone
let soloWon = false; // alone: every computer kid fell before me
const FILL_TO = 6;
function soloRound() {
  const players = [{ id: 'me', name: 'Sinä', kind: 'me', col: 0, o: outfitId() }];
  for (let i = 1; i < FILL_TO; i++) players.push({ id: 'cpu' + i, name: CPU_NAMES[(i + roomN * 3) % CPU_NAMES.length], kind: 'cpu', col: i });
  world = newWorld(roomN, players, (Date.now() % 1e9) >>> 0);
  me = world.kids[0];
  brains = world.kids.map((k, i) => k.kind === 'cpu' ? cpuBrain(ROOMS[roomN - 1].cpu, world.seed + i * 31) : null);
  soloWon = false; result = null; acc = 0; endT = 0;
  startPlay();
}
function startPlay() {
  mode = 'play'; seen = null; stick = null; jumpPtr = null;
  hideAll();
  if (window.L3D && L3D.build) L3D.build(world);
}
// A shove by a kid this phone runs, alone or as the host: the dash, then the push on whoever is
// in front. A kid run by another phone is pushed by a message (net.js).
function doShove(k) {
  if (!startShove(k)) return;
  const o = shoveTarget(world, k, k.face);
  if (!o) return;
  o.pushedAt = world.rt;
  const imp = pushOf(k, o);
  if (net && typeof pushRemote === 'function' && pushRemote(o, imp)) return;
  applyPush(o, imp);
}
// One physics step alone.
function soloStep(dt) {
  const w = world;
  me.ix = stickInput()[0]; me.iz = stickInput()[1]; me.jump = !!jumpPtr;
  if (w.ph === 'play') {
    const sol = solids(w, w.rt);
    w.kids.forEach((k, i) => { if (brains[i] && !k.out && cpuThink(w, k, brains[i], dt, sol)) doShove(k); });
  }
  stepWorld(w, dt, w.kids);
  if (w.ph !== 'play') return;
  for (const k of w.kids) if (inLava(w, k)) fall(w, k);
  // Every computer kid down while I stand: the round is won, and the lava goes on for the time.
  if (!soloWon && !me.out && w.kids.every(k => k === me || k.out)) {
    soloWon = true; wonT = 0;
    if (roomN === open && open < ROOMS.length) { open++; save('auki', open); justOpened = open; }
    save('voitot', (+load('voitot', 0) || 0) + 1);
    sfx('onnistui', { vol: 0.3 }, 660);
  }
  if (me.out && !result) soloRecord();
}
let wonT = 0, justOpened = 0;
// Alone: I fell. The time I lasted is the score, saved at once.
function soloRecord() {
  const t = Math.max(0, me.outRt), n = roomN;
  const rec = t > best[n - 1];
  if (rec) { best[n - 1] = t; save('paras-' + n, Math.round(t * 10) / 10); }
  if (tutorial) { tutorial = false; save('osattu', true); }
  result = { net: false, won: soloWon, time: t, rec, opened: justOpened, rows: rowsOf(world) };
  justOpened = 0;
  if (window.AiPelitScores && t >= 1) { AiPelitScores.board('huone-' + n, ROOMS[n - 1].name); AiPelitScores.submit(Math.round(t * 10)); }
}
function rowsOf(w) {
  return standingsOf(w).map(k => ({ id: k.id, name: k === me ? 'Sinä' : k.name, col: k.col, t: k.out ? k.outRt : null, me: k === me, cpu: k.kind === 'cpu', win: k.id === w.winner }));
}
const fmt = t => { t = Math.max(0, t); const m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(1).replace('.', ','); };

// ---- The fingers ----
// Left thumb: a floating stick wherever it touches (not on a button). Right thumb: Hyppy, held
// for a higher jump, and Töni above it.
const STICK = 52;
let stick = null, jumpPtr = null, shoveFlash = 0;
function buttons() {
  const r = LAND ? 44 : 48, rs = LAND ? 33 : 36;
  const j = { x: W - SAFE_R - r - (LAND ? 26 : 22), y: H - SAFE_B - r - (LAND ? 22 : 30), r };
  const s = LAND ? { x: j.x - r - rs - 22, y: j.y + 8, r: rs } : { x: j.x - 26, y: j.y - r - rs - 26, r: rs };
  return { jump: j, shove: s };
}
const hit = (b, e) => Math.hypot(e.clientX - b.x, e.clientY - b.y) < b.r + 14;
function playing() { return (mode === 'play' || mode === 'netplay') && world && me && !me.out; }
c.addEventListener('pointerdown', e => {
  if (!playing()) return;
  e.preventDefault();
  const b = buttons();
  if (hit(b.jump, e)) { jumpPtr = e.pointerId; return; }
  if (hit(b.shove, e)) { shoveBtn(); return; }
  // The stick is the left half's (Eero's choice): a thumb that misses a button on the right runs nothing.
  if (stick || e.clientX > W / 2) return;
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
  stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
});
c.addEventListener('pointermove', e => {
  if (!stick || e.pointerId !== stick.id) return;
  stick.x = e.clientX; stick.y = e.clientY;
  const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy);
  if (d > STICK * 1.6) { stick.x0 = stick.x - dx / d * STICK * 1.6; stick.y0 = stick.y - dy / d * STICK * 1.6; }
});
function lift(e) {
  if (stick && e.pointerId === stick.id) stick = null;
  if (e.pointerId === jumpPtr) jumpPtr = null;
}
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
function shoveBtn() {
  if (!playing() || world.ph !== 'play' || me.cd > 0) return;
  shoveFlash = 0.15;
  if (net) netShove(); else doShove(me);
}

// ---- Menus (DOM, over the canvas) ----
const $ = id => document.getElementById(id);
// A round starting (the host's start on a guest too) closes the outfit picker over the play area.
function hideAll() {
  for (const id of ['menu', 'end']) $(id).hidden = true;
  if (window.AiPelitOutfits && AiPelitOutfits.isOpen && AiPelitOutfits.isOpen()) AiPelitOutfits.close();
}
const ROOM_NOTES = ['Sohva, nojatuoli ja kirjahylly', 'Sänky, säkkituolit ja lelulaatikot', 'Pöytä, tuolit ja jääkaappi', 'Portaita ylös katolle asti'];
function showMenu() {
  mode = 'menu'; world = null; me = null; seen = null;
  hideAll(); $('menu').hidden = false;
  const box = $('rooms'); box.innerHTML = '';
  ROOMS.forEach((R, i) => {
    const n = i + 1, b = document.createElement('button');
    b.className = 'room' + (n === roomN ? ' on' : '');
    b.disabled = n > open;
    b.innerHTML = '<b>' + n + '. ' + R.name + '</b><small>' + (n > open ? '🔒 Voita edellinen' : best[i] ? 'Paras ' + fmt(best[i]) : ROOM_NOTES[i]) + '</small>';
    b.addEventListener('click', () => { roomN = n; save('huone', n); sfx('valinta', { vol: 0.3 }); showMenu(); });
    box.appendChild(b);
  });
  if (window.AiPelitScores) AiPelitScores.board('huone-' + roomN, ROOMS[roomN - 1].name);
  if (window.L3D && L3D.build) L3D.build(menuWorld());
}
let mw = null;
function menuWorld() { if (!mw || mw.level !== roomN) { mw = newWorld(roomN, [], 1); mw.rt = -1; } return mw; }
function showEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result;
  if (r.net) {
    $('endTitle').textContent = r.draw ? 'Tasapeli!' : r.won ? 'Voitit!' : (r.winnerName || 'Joku') + ' voitti';
    $('endNote').textContent = [r.helped ? 'Tietokone pelasi välillä puolestasi' : '', r.time !== null ? 'Kestit ' + fmt(r.time) : ''].filter(Boolean).join(' · ');
  } else {
    $('endTitle').textContent = r.won ? 'Voitit kierroksen!' : 'Laavaan!';
    $('endNote').textContent = 'Kestit ' + fmt(r.time) + (r.rec ? ' – uusi ennätys!' : best[roomN - 1] ? ' · paras ' + fmt(best[roomN - 1]) : '');
  }
  $('endOpen').hidden = !r.opened;
  if (r.opened) $('endOpen').textContent = '🔓 ' + ROOMS[r.opened - 1].name + ' aukesi!';
  $('again').textContent = r.net ? 'Takaisin huoneeseen' : 'Uusi kierros';
  $('toMenu').hidden = !!r.net;
  const list = $('endList'); list.innerHTML = '';
  r.rows.forEach(row => {
    const li = document.createElement('li');
    if (row.me) li.className = 'me';
    li.innerHTML = '<span><i style="background:' + KID_COLORS[row.col % KID_COLORS.length] + '"></i>' + esc(row.name) + (row.cpu || row.helped ? ' 🤖' : '') + '</span><b>' + (row.win ? '🏆' : row.t === null ? '–' : fmt(row.t)) + '</b>';
    list.appendChild(li);
  });
  sfx(r.won ? 'voitto' : 'tappio', { vol: 0.3 });
}
function esc(s) { return String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }
$('go').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloRound(); });
$('again').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (result && result.net) backRoom(); else soloRound(); });
$('friends').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (window.AiPelitRooms) AiPelitRooms.open(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });

// ---- The 2D layer: time, kids left, the countdown, the stick, the buttons, names ----
function shadowText(t, x, y, size, col, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(30,6,0,.65)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = col; cx.fillText(t, x, y);
}
function drawHUD(w, clock) {
  const top = SAFE_T + 22, midY = LAND ? H * 0.42 : H * 0.38;
  const left = w.kids.filter(k => !k.out).length;
  // Time and kids left, right of the "‹ Pelit" chip; sideways it leaves the middle of the top bar
  // free for the room's 🎤 chip.
  shadowText(fmt(Math.max(0, w.rt)), LAND ? SAFE_L + 140 : W / 2, top, 22, '#fff', 'center', 900);
  shadowText('🧒 ' + left + '/' + w.kids.length, W - SAFE_R - 14, top, 17, '#ffe7c2', 'right', 800);
  if (w.ph === 'count') {
    const k = Math.ceil(-w.rt);
    shadowText(String(Math.max(1, k)), W / 2, midY, 72, '#fff', 'center', 900);
    shadowText('Kiipeä huonekalun päälle!', W / 2, midY + 56, 18, '#ffe7c2', 'center', 800);
  } else if (w.rt < 1.6 && w.ph === 'play') {
    const s = 1 + Math.max(0, 0.4 - w.rt);
    shadowText('LATTIA ON', W / 2, midY - 24 * s, 34 * s, '#ffd166', 'center', 900);
    shadowText('LAAVAA!', W / 2, midY + 18 * s, 44 * s, '#ff5a1f', 'center', 900);
  }
  if (!net && soloWon && wonT < 3 && me && !me.out) {
    shadowText('Voitit kierroksen!', W / 2, midY - 30, 28, '#ffd166', 'center', 900);
    shadowText('Kestä niin kauan kuin pystyt', W / 2, midY + 6, 16, '#fff', 'center', 700);
  }
  if (w.ph === 'play' && w.rt >= w.floatAt && w.rt < w.floatAt + 3) shadowText(w.house ? 'Talo jäi laavan alle – hyppää lautalle!' : 'Tavarat kelluvat – hyppää kyytiin!', W / 2, midY + 70, 17, '#ffe7c2', 'center', 800);
  // Koko talo (#526): the doors of the stairs open, then the lava climbs them.
  if (w.house && w.ph === 'play') {
    for (let n = 0; n < 2; n++) {
      if (w.rt >= HOUSE.open[n] && w.rt < HOUSE.climb[n] + 3) {
        shadowText(w.rt < HOUSE.climb[n] ? 'Ovi aukesi!' : 'Laava nousee!', W / 2, midY - 36, 30, '#ff7a1a', 'center', 900);
        shadowText(n ? 'Portaita ylös katolle!' : 'Portaita ylös yläkertaan!', W / 2, midY, 19, '#ffe7c2', 'center', 800);
      }
    }
  }
  if (me && me.out && (mode === 'netplay')) shadowText('Laavaan! Katsot muita', W / 2, midY, 24, '#ffd166', 'center', 900);
  // Names over friends' kids.
  if (net && window.L3D && L3D.project) {
    cx.font = '600 11px system-ui'; cx.textAlign = 'center'; cx.textBaseline = 'bottom';
    for (const k of w.kids) {
      if (k === me || k.out || k.dy >= (L3D.cutY || Infinity)) continue;
      const p = L3D.project(k.dx, k.dy + KID_H + 0.45, k.dz);
      if (!p) continue;
      cx.fillStyle = 'rgba(0,0,0,.55)'; cx.fillText(k.name, p[0] + 1, p[1] + 1);
      cx.fillStyle = '#fff'; cx.fillText(k.name, p[0], p[1]);
    }
  }
  if (!me || me.out || !(mode === 'play' || mode === 'netplay')) return;
  if (stick) {
    cx.strokeStyle = 'rgba(255,255,255,.4)'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(stick.x0, stick.y0, STICK, 0, TAU); cx.stroke();
    const [ix, iy] = stickInput();
    cx.fillStyle = 'rgba(255,255,255,.55)'; cx.beginPath(); cx.arc(stick.x0 + ix * STICK, stick.y0 + iy * STICK, 20, 0, TAU); cx.fill();
  }
  const b = buttons();
  cx.fillStyle = jumpPtr !== null ? 'rgba(255,209,102,.95)' : 'rgba(255,122,26,.85)';
  cx.beginPath(); cx.arc(b.jump.x, b.jump.y, b.jump.r, 0, TAU); cx.fill();
  cx.strokeStyle = 'rgba(255,255,255,.7)'; cx.lineWidth = 3; cx.stroke();
  shadowText('Hyppy', b.jump.x, b.jump.y, 18, '#fff', 'center', 900);
  const ready = me.cd <= 0 && w.ph === 'play';
  cx.fillStyle = shoveFlash > 0 ? 'rgba(255,209,102,.95)' : ready ? 'rgba(42,125,225,.85)' : 'rgba(60,70,100,.6)';
  cx.beginPath(); cx.arc(b.shove.x, b.shove.y, b.shove.r, 0, TAU); cx.fill();
  if (me.cd > 0) {
    cx.strokeStyle = '#fff'; cx.lineWidth = 4;
    cx.beginPath(); cx.arc(b.shove.x, b.shove.y, b.shove.r - 4, -Math.PI / 2, -Math.PI / 2 + TAU * (1 - me.cd / SHOVE_CD)); cx.stroke();
  }
  shadowText('Töni', b.shove.x, b.shove.y, 15, '#fff', 'center', 900);
  if (tutorial && w.rt < 7) {
    const ty = LAND ? SAFE_T + 52 : SAFE_T + 56;
    shadowText('Vedä sormella: juokse', W / 2, ty, 15, '#fff', 'center', 700);
    shadowText('Hyppy: huonekalulta toiselle · Töni: tönäise', W / 2, ty + 20, 14, '#fff', 'center', 700);
  }
  if (net && window.AiPelitRooms && AiPelitRooms.paused) shadowText('Odotetaan kaveria…', W / 2, midY + 90, 18, '#fff', 'center', 800);
}
// Where each kid is drawn: its own spot, or for another phone's kid the smoothed one (net.js).
function placeKids(w) {
  for (const k of w.kids) {
    const s = net && typeof drawnSpot === 'function' ? drawnSpot(k) : null;
    if (s) { k.dx = s.x; k.dy = s.y; k.dz = s.z; k.df = s.f; }
    else {
      // A climb (#505) is drawn as a quick pull up from where the kid grabbed the edge.
      const c = k.climbT > 0 ? k.climbT / CLIMB_T : 0;
      k.dx = k.x + (c ? k.climbX * c : 0); k.dy = k.y + (c ? k.climbY * c : 0); k.dz = k.z + (c ? k.climbZ * c : 0); k.df = k.face;
    }
  }
}
function draw(clock) {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  const w = world || menuWorld();
  if (w.kids.length) placeKids(w);
  if (window.L3D && L3D.draw) L3D.draw(w, me, clock);
  if (window.L3D && L3D.failed) {
    cx.fillStyle = '#2a0d05'; cx.fillRect(0, 0, W, H);
    shadowText('Puhelimesi ei osaa piirtää 3D-kuvaa', W / 2, H * 0.3, 17, '#ffd166', 'center', 800);
  }
  if (mode === 'netwait') shadowText('Odotetaan muita…', W / 2, H * 0.4, 20, '#fff', 'center', 800);
  if (world && (mode === 'play' || mode === 'netplay')) drawHUD(world, clock);
}

// ---- The main loop ----
let last = 0, clock = 0;
function frame(now) {
  requestAnimationFrame(frame);
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60; last = now;
  clock += dt;
  if (shoveFlash > 0) shoveFlash -= dt;
  if (net) netTick(dt);
  else if (mode === 'play' && world) {
    acc += dt;
    while (acc >= STEP) { acc -= STEP; soloStep(STEP); if (result) break; }
    if (soloWon) wonT += dt;
    if (result) { endT += dt; if (endT > 1.2) showEnd(); }
  }
  soundsOf(mode === 'play' || mode === 'netplay' ? world : null);
  draw(clock);
  document.body.classList.toggle('playing', mode === 'play' || mode === 'netplay' || mode === 'netwait');
}
resize();
if (window.AiPelitRooms && AiPelitRooms.inRoom) hideAll();
else showMenu();
requestAnimationFrame(frame);
