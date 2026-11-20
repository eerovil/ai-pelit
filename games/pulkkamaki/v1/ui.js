'use strict';
// Pulkkamäki v1: the screen, the finger, the menus, the saves and the sounds, and the main loop.

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
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);
document.addEventListener('fullscreenchange', resize);

// ---- Saves (ai-pelit:pulkkamaki:*, shared by every version) ----
const KEY = 'ai-pelit:pulkkamaki:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
let open = clamp(Math.floor(load('auki', 1)) || 1, 1, 3);   // hills opened
let hillN = clamp(Math.floor(load('maki', 1)) || 1, 1, open);
const best = n => Math.max(0, Math.floor(load('ennatys-' + n, 0)) || 0);
let tutorial = !load('osattu', false);
camView = load('kamera', 'fp') === 'back' ? 'back' : 'fp';
function viewLabel() { $('view').textContent = camView === 'fp' ? '📷 Silmistä' : '📷 Takaa'; }

// ---- Outfits (#158): our own winter wear, the Christmas costumes first in November and December ----
const OUTFITS = [
  { id: 'haalari', name: 'Toppahaalari', skin: '#f0c8a0', hair: '#5a3418', top: '#2f6fd0', bottom: '#2f6fd0', shoe: '#1a1a22', pipo: '#d42a2a', tupsu: '#ffffff', stripe: '#ffd23a', cape: null, head: null },
  { id: 'punainen', name: 'Punainen', skin: '#e8b48f', hair: '#2a1a10', top: '#d42a2a', bottom: '#2a2a33', shoe: '#2a2a33', pipo: '#ffffff', tupsu: '#d42a2a', cape: null, head: null },
  { id: 'vihrea', name: 'Vihreä', skin: '#c98a62', hair: '#111111', top: '#27a35a', bottom: '#1b3a2a', shoe: '#111', pipo: '#ffd23a', tupsu: '#27a35a', stripe: '#ffffff', cape: null, head: null },
  { id: 'liila', name: 'Liila', skin: '#f6d4bb', hair: '#d4611c', top: '#8a4ad4', bottom: '#f4f6fa', shoe: '#8a4ad4', pipo: '#f4f6fa', tupsu: '#8a4ad4', cape: null, head: null },
  { id: 'musta', name: 'Musta', skin: '#8d5a3b', hair: '#161616', top: '#1e1e22', bottom: '#1e1e22', shoe: '#c8ff2e', pipo: '#c8ff2e', tupsu: '#1e1e22', stripe: '#c8ff2e', cape: null, head: null },
];
let outfit = OUTFITS[0];
if (window.AiPelitOutfits) {
  outfit = AiPelitOutfits.setup({
    outfits: OUTFITS, halloween: false, tylypahka: false,
    draw(g, o, w, h) { drawCard(g, o, w, h); },
    change(o) { outfit = o; if (me) me.outfit = o; wake(); },
  });
}
// The picker's card: the rider in the sled, from the side.
function drawCard(g, o, w, h) {
  const s = Math.min(w, h) / 100;
  g.save(); g.translate(w / 2, h * 0.62); g.scale(s, s);
  g.fillStyle = '#d0202c'; g.beginPath(); g.moveTo(-38, 8); g.lineTo(30, 8); g.quadraticCurveTo(44, 8, 42, -8); g.lineTo(36, -6); g.quadraticCurveTo(34, 0, 26, 0); g.lineTo(-38, 0); g.closePath(); g.fill();
  g.fillStyle = o.bottom || '#333'; g.fillRect(-14, -12, 40, 12);
  g.fillStyle = o.shoe || '#222'; g.fillRect(24, -14, 9, 12);
  g.fillStyle = o.top || '#2f6fd0'; g.beginPath(); g.roundRect ? g.roundRect(-22, -48, 20, 40, 7) : g.rect(-22, -48, 20, 40); g.fill();
  if (o.stripe) { g.fillStyle = o.stripe; g.fillRect(-22, -30, 20, 4); }
  g.strokeStyle = o.top || '#2f6fd0'; g.lineWidth = 6; g.lineCap = 'round'; g.beginPath(); g.moveTo(-10, -40); g.lineTo(6, -16); g.stroke();
  if (o.head && window.AiPelitOutfits && AiPelitOutfits.head) AiPelitOutfits.head(g, o.head, -12, -60, 12, 1, 0);
  else {
    g.fillStyle = o.skin || '#f0c8a0'; g.beginPath(); g.arc(-12, -60, 11, 0, TAU); g.fill();
    g.fillStyle = o.pipo || '#d42a2a'; g.beginPath(); g.arc(-12, -62, 11.5, Math.PI, TAU); g.fill();
    g.fillStyle = o.tupsu || '#fff'; g.beginPath(); g.arc(-12, -76, 4.5, 0, TAU); g.fill();
    g.fillStyle = '#222'; g.beginPath(); g.arc(-5, -58, 1.6, 0, TAU); g.fill();
  }
  g.restore();
}

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['tuuli', 'rullaus', 'hyppy', 'lasku', 'lumi', 'onnistui', 'tomahdys', 'kello', 'valinta']);
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
let wind = null, slide = null;
function sounds(dt) {
  if (!S) return;
  const on = mode === 'run' && me;
  if (on && !wind) { wind = S.loop('tuuli', { vol: 0 }); slide = S.loop('rullaus', { vol: 0 }); }
  if (!on && wind) { wind.stop(); slide.stop(); wind = slide = null; }
  if (wind) {
    const v = clamp(me.v / 20, 0, 1);
    wind.set({ vol: 0.05 + v * 0.18, rate: 0.8 + v * 0.4 });
    slide.set({ vol: me.air || me.fin ? 0 : 0.05 + v * 0.14, rate: 0.7 + v * 0.5 });
  }
}
function onMyEvent(e, pts) {
  if (e === 'jump') sfx('hyppy', { vol: 0.25 });
  else if (e === 'land') sfx('lumi', { vol: 0.5 });
  else if (e === 'trick') { sfx('lasku', { vol: 0.45 }); sfx('onnistui', { vol: 0.3, delay: 0.05 }, 880); }
  else if (e === 'fall') sfx('tomahdys', { vol: 0.6 }, 140);
  else if (e === 'gift') sfx('kello', { vol: 0.18, rate: 1.2 }, 1320);
  else if (e === 'finish') finishLine();
}

// ---- The run ----
let mode = 'menu', hill = buildHill(hillN), me = null, sleds = [], countT = 0, endT = 0, runT = 0;
let result = null;
function soloRun() {
  hill = buildHill(hillN);
  me = newSled('me', 'Sinä', { outfit, onEvent: onMyEvent });
  placeSled(hill, me, 0);
  sleds = [me];
  const lanes = [-4, 4, -7];
  for (let i = 0; i < 3; i++) {
    const o = OUTFITS[(i + 1) % OUTFITS.length];
    const cpu = newSled('cpu' + i, CPU_NAMES[(i + hillN) % CPU_NAMES.length], { outfit: o, cpu: cpuBrain(CPU_SKILL[clamp(hillN - 1 + (i === 2 ? 1 : 0) - (i === 0 ? 1 : 0), 0, 2)], hillN * 100 + i * 17 + Date.now() % 1000) });
    placeSled(hill, cpu, lanes[i]);
    sleds.push(cpu);
  }
  me.x = 0;
  startCount();
}
function startCount() {
  mode = 'count'; countT = 3; endT = 0; runT = 0; result = null;
  for (const p of pointers.values()) p.used = true;
  hideAll();
  wake();
}
function finishLine() {
  endT = 2.4;
}
// Alone, the computer's sledders still on the hill finish their runs at once, on their own numbers.
function soloEnd() {
  for (const sl of sleds) {
    if (sl === me) continue;
    for (let t = 0; !sl.fin && t < 240; t += DT) { cpuDrive(hill, sl, DT); step(hill, sl, DT); }
  }
  const rows = sleds.map(sl => ({ id: sl.id, name: sl.name, points: sl.points, me: sl === me })).sort((a, b) => b.points - a.points);
  const pts = me.points, n = hillN, was = best(n);
  // Saved at once, alone (design, #475).
  if (pts > was) save('ennatys-' + n, pts);
  let opened = 0;
  if (n < 3 && n === open && pts >= HILLS[n].open) { open = n + 1; save('auki', open); opened = n + 1; }
  if (pts > 0 && window.AiPelitScores) { setBoard(); AiPelitScores.submit(pts); }
  if (tutorial && pts >= 300) { tutorial = false; save('osattu', true); }
  result = { rows, pts, record: pts > was, was, opened };
  showEnd();
}
function setBoard() { if (window.AiPelitScores) AiPelitScores.board('maki-' + hillN, HILLS[hillN - 1].name); }

// ---- The finger ----
// On the snow: how far the finger has moved sideways from where it touched down steers the sled.
// In the air: a swipe starts a trick (up a front flip, down a back flip, sideways a spin), a finger
// held still is the grab (Teräsmies) until it lifts. A touch that began on the snow does no trick:
// lift and swipe again in the air. One that began just before the lip counts as in the air.
const pointers = new Map();
const SWIPE = 26, HOLD = 0.2;
function steerOf(p) { return clamp((p.x - p.x0) / (Math.min(W, H) * 0.26), -1, 1); }
c.addEventListener('pointerdown', e => {
  if (mode !== 'run' && mode !== 'count') return;
  e.preventDefault();
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
  const p = { x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, t0: e.timeStamp, air: !!(me && me.air), used: false, grab: false };
  pointers.set(e.pointerId, p);
  if (!p.air) steerFinger = e.pointerId;
});
c.addEventListener('pointermove', e => {
  const p = pointers.get(e.pointerId);
  if (!p) return;
  p.x = e.clientX; p.y = e.clientY;
  airGesture(p, e.timeStamp, false);
});
function lift(e) {
  const p = pointers.get(e.pointerId);
  if (!p) return;
  p.x = e.clientX; p.y = e.clientY;
  airGesture(p, e.timeStamp, true);
  if (p.grab && me) setGrab(me, false);
  pointers.delete(e.pointerId);
  if (steerFinger === e.pointerId) steerFinger = null;
}
c.addEventListener('pointerup', lift);
c.addEventListener('pointercancel', lift);
let steerFinger = null;
function airGesture(p, now, up) {
  if (!me || p.used || mode !== 'run') return;
  // A touch that began on the snow becomes an air touch only if it began just before take-off.
  if (!p.air) { if (me.air && me.airT < 0.25 && now - p.t0 < 250) p.air = true; else return; }
  if (!me.air) return;
  const dx = p.x - p.x0, dy = p.y - p.y0, d = Math.hypot(dx, dy);
  if (d >= SWIPE) {
    const type = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'spinL' : 'spinR') : (dy < 0 ? 'front' : 'back');
    if (startTrick(me, type)) { p.used = true; teach.swiped = true; }
  }
}
function checkHolds(now) {
  for (const p of pointers.values()) {
    if (p.used || p.grab || !p.air || !me || !me.air) continue;
    if (Math.hypot(p.x - p.x0, p.y - p.y0) < SWIPE && now - p.t0 >= HOLD * 1000) {
      if (setGrab(me, true)) { p.grab = true; p.used = true; }
    }
  }
}
function steerInput() {
  if (!me) return;
  const p = steerFinger !== null ? pointers.get(steerFinger) : null;
  me.steer = p && !p.air ? steerOf(p) : 0;
  if (p && Math.abs(me.steer) > 0.3) teach.steered = true;
}
const teach = { steered: false, swiped: false };

// ---- Menus (DOM, over the canvas) ----
const $ = id => document.getElementById(id);
function hideAll() { for (const id of ['menu', 'end']) $(id).hidden = true; }
function showMenu() {
  mode = 'menu'; me = null; sleds = []; hill = buildHill(hillN);
  hideAll(); $('menu').hidden = false;
  const box = $('hills'); box.innerHTML = '';
  HILLS.forEach((H, i) => {
    const n = i + 1, b = document.createElement('button');
    b.className = 'hill' + (n === hillN ? ' on' : '');
    const locked = n > open;
    b.disabled = locked;
    b.innerHTML = '<b>' + H.name + '</b><small>' + (locked ? '🔒 ' + H.open + ' p ' + HILLS[i - 1].name + 'ssa' : best(n) ? 'Ennätys ' + best(n) + ' p' : 'Ei vielä laskettu') + '</small>';
    b.addEventListener('click', () => { hillN = n; save('maki', n); sfx('valinta', { vol: 0.3 }); showMenu(); });
    box.appendChild(b);
  });
  setBoard();
  wake();
}
function showEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result;
  $('endPts').textContent = r.pts + ' p';
  $('endNote').textContent = r.record ? (r.was ? 'Uusi ennätys!' : 'Ensimmäinen lasku tällä mäellä!') : 'Ennätys ' + r.was + ' p';
  $('endOpen').hidden = !r.opened;
  if (r.opened) $('endOpen').textContent = '🔓 ' + HILLS[r.opened - 1].name + ' aukesi!';
  const list = $('endList'); list.innerHTML = '';
  r.rows.forEach((row, i) => {
    const li = document.createElement('li');
    if (row.me) li.className = 'me';
    li.innerHTML = '<span>' + (i + 1) + '. ' + esc(row.name) + (row.cpu ? ' 🤖' : '') + '</span><b>' + row.points + ' p</b>';
    list.appendChild(li);
  });
  sfx(r.rows[0] && r.rows[0].me ? 'onnistui' : 'valinta', { vol: 0.3 });
}
function esc(s) { return String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]); }
$('go').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloRun(); });
$('view').addEventListener('click', () => {
  camView = camView === 'fp' ? 'back' : 'fp'; save('kamera', camView); if (V3) V3.view = camView;
  sfx('valinta', { vol: 0.3 }); viewLabel();
});
viewLabel();
$('asu').addEventListener('click', () => { if (window.AiPelitOutfits) AiPelitOutfits.open(); });
$('again').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloRun(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });

// ---- The HUD (the 2D canvas over the 3D one) ----
function shadowText(t, x, y, size, col, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(0,0,30,.55)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = col; cx.fillText(t, x, y);
}
function drawHUD() {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  if (!V3) {
    const g = cx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#0d1534'); g.addColorStop(0.6, '#5a5f9a'); g.addColorStop(1, '#dfe8ff');
    cx.fillStyle = g; cx.fillRect(0, 0, W, H);
    if (no3d) shadowText('Tämä puhelin ei osaa piirtää 3D-kuvaa.', W / 2, H * 0.3, 15, '#fff', 'center', 600);
  }
  if (mode === 'menu' || mode === 'end' || !me) return;
  const top = SAFE_T + 14, right = W - SAFE_R - 14;
  // Points and streak, top right (the "‹ Pelit" chip is top left).
  shadowText(me.points + ' p', right, top + 14, 26, '#fff', 'right', 800);
  if (me.streak > 1) shadowText('Putki ×' + Math.min(3, 1 + 0.25 * (me.streak - 1)).toFixed(2).replace(/\.?0+$/, '').replace('.', ','), right, top + 42, 15, '#ffd84a', 'right', 700);
  // Place among the sleds, under the chip.
  const order = sleds.slice().sort((a, b) => b.points - a.points), place = order.indexOf(me) + 1;
  shadowText(place + '. / ' + sleds.length, SAFE_L + 16, top + 50, 16, '#fff', 'left', 700);
  // How far down the hill.
  const bw = Math.min(W * 0.5, 260), bx = W / 2 - bw / 2, by = top + 6;
  cx.fillStyle = 'rgba(0,0,30,.35)'; cx.fillRect(bx, by, bw, 5);
  for (const sl of sleds) {
    const f = clamp(sl.s / hill.len, 0, 1);
    cx.fillStyle = sl === me ? '#ffd84a' : 'rgba(255,255,255,.8)';
    cx.beginPath(); cx.arc(bx + f * bw, by + 2.5, sl === me ? 5 : 3.5, 0, TAU); cx.fill();
  }
  // Names over the others' sleds.
  for (const sl of sleds) {
    if (sl === me) continue;
    const p = screenOf(hill, sl.s, sl.x, sl.y + 1.8);
    if (p && p.d < 60) shadowText(sl.name, p.x, p.y, 12, 'rgba(255,255,255,.9)', 'center', 600);
  }
  // The trick just landed, or the fall.
  const pop = me.pop;
  if (pop && pop.t < 1.8) {
    const a = clamp(1.8 - pop.t, 0, 1), y = H * (LAND ? 0.3 : 0.32) - pop.t * 10;
    cx.globalAlpha = a;
    shadowText(pop.text, W / 2, y, pop.bad ? 22 : 20, pop.bad ? '#ff8a8a' : '#fff', 'center', 800);
    if (!pop.bad) shadowText('+' + pop.pts + (pop.mult ? '  (×' + pop.mult + ' temppua)' : ''), W / 2, y + 28, 18, '#ffd84a', 'center', 800);
    cx.globalAlpha = 1;
  }
  // The trick going on now, while in the air.
  if (me.air && me.trick) shadowText(TRICKS[me.trick.type].name + '…', W / 2, H * 0.2, 17, '#cfe0ff', 'center', 700);
  if (me.air && me.grab) {
    const warn = timeToLand(hill, me) < 0.45;
    shadowText(warn ? 'Päästä irti!' : 'Teräsmies…', W / 2, H * 0.2, warn ? 24 : 17, warn ? '#ff6a6a' : '#cfe0ff', 'center', 800);
  }
  // The first runs teach the controls.
  if (tutorial && mode === 'run') {
    let t = '';
    if (me.air && !me.trick && !me.grab && me.jump.length === 0) t = 'Pyyhkäise: temppu! Pidä sormi paikallaan: Teräsmies';
    else if (!me.air && !teach.steered && runT < 12) t = 'Vedä sormea sivulle: pulkka kääntyy';
    else if (!me.air && runT < 30 && !teach.swiped) t = 'Osu hyppyriin, ilmassa pyyhkäise ↑ ↓ ← →';
    if (t) shadowText(t, W / 2, H - SAFE_B - 70, 15, '#fff', 'center', 700);
  }
  if (mode === 'count') {
    const n = Math.ceil(countT);
    shadowText(n > 0 ? String(n) : 'MENOKSI!', W / 2, H * 0.35, n > 0 ? 64 : 44, '#fff', 'center', 900);
  } else if (runT < 0.8) shadowText('MENOKSI!', W / 2, H * 0.35, 44, '#fff', 'center', 900);
  if (me.fin) shadowText('Maalissa!', W / 2, H * 0.42, 30, '#ffd84a', 'center', 900);
}

// ---- The main loop ----
// It runs only while something moves: in the menus the picture is drawn once and then rests
// (docs/making-games.md, "A still game must not draw every frame").
let raf = 0, last = 0, still = 0;
function wake() { still = 0; if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
function frame(now) {
  raf = 0;
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60; last = now;
  if (mode === 'count') {
    countT -= dt;
    if (countT <= 0) { mode = 'run'; runT = 0; }
  } else if (mode === 'run') {
    runT += dt;
    checkHolds(performance.now());
    steerInput();
    for (const sl of sleds) {
      if (sl.cpu) cpuDrive(hill, sl, dt);
      advance(hill, sl, dt);
    }
    if (me.fin && endT > 0) { endT -= dt; if (endT <= 0) soloEnd(); }
    tune(dt * 1000);
  }
  sounds(dt);
  const moving = mode === 'run' || mode === 'count';
  render3d(hill, sleds, me, dt, !moving);
  drawHUD();
  if (moving || still++ < 2 || !V3) raf = requestAnimationFrame(frame);
}
resize();
showMenu();
