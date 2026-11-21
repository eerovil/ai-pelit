'use strict';
// Pingis v1: the screen, the finger, the menus, the saves, the sounds and the main loop, and the
// rally itself (who serves, each step of the ball, a hit, a point) for one phone. Alone this phone
// judges both ends; with friends net.js decides which end it judges (`judgeHere`) and what a
// launch or a point does (`hooks`). The 3D hall is drawn by draw3d.js on the canvas #g under
// this one; this file draws the score and the texts on #c over it, and the whole table flat
// when the phone cannot draw 3D.

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

// ---- Saves (ai-pelit:pingis:*, shared by every version) ----
const KEY = 'ai-pelit:pingis:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
function drop(k) { try { localStorage.removeItem(KEY + k); } catch (e) {} }
let level = clamp(Math.floor(load('taso', 0)) || 0, 0, LEVELS.length - 1);
// Games won and lost against the computer, per level: { "0": [won, lost], ... }.
let record = load('voitot', {});
if (!record || typeof record !== 'object' || Array.isArray(record)) record = {};
const recOf = n => { const a = record[n]; return Array.isArray(a) ? [Math.max(0, Math.floor(a[0]) || 0), Math.max(0, Math.floor(a[1]) || 0)] : [0, 0]; };
let tutorial = !load('osattu', false);

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['puu', 'naksu', 'verkko', 'onnistui', 'voitto', 'tappio', 'valinta']);
let ac = null;
function beep(f, d, vol) {
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = f; g.gain.value = vol || 0.04; g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + d);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + d);
  } catch (e) {}
}
const sfx = (name, opts, f) => (S && S.play(name, opts)) || (f && beep(f, 0.06, 0.03));
function evSound(ev, b) {
  if (ev === 'bounce0' || ev === 'bounce1') sfx('naksu', { vol: 0.3, rate: 1.1 + Math.random() * 0.1 }, 1400);
  else if (ev === 'net') sfx('verkko', { vol: 0.25 }, 200);
}
const hitSound = kind => sfx('puu', { vol: kind === 'smash' ? 0.42 : 0.32, rate: kind === 'smash' ? 1.25 : 1.05 + Math.random() * 0.1 }, 900);

// ---- The game on this phone ----
let mode = 'menu', game = null, view = 0, bats = null, brains = [null, null], acc = 0, rnd = rng(Date.now() >>> 0);
let net = null;              // the game with a friend (net.js), null alone
let judgeHere = () => true;  // whether this phone decides the flights flying towards `side`
let cpuAt = side => side === 1;   // whether the computer plays `side`'s bat here
const soloHooks = { launched() {}, point: soloPoint, next: soloNext };
let hooks = soloHooks;
let names = ['Sinä', 'Kone'], banner = null, result = null;
function newBats() {
  bats = [0, 1].map(side => ({ x: 0, y: 0.15, z: sgn(side) * (HL + 0.4), vx: 0, vz: 0, swing: 0, hist: [], tx: 0, tz: sgn(side) * (HL + 0.4) }));
}
function soloGame(resume) {
  net = null; hooks = soloHooks; judgeHere = () => true; cpuAt = side => side === 1; view = 0;
  names = ['Sinä', 'Kone'];
  game = newGame(names);
  game.first = 0;
  if (resume) { game.sc = resume.sc.slice(); game.first = resume.first; game.sv = serverAt(game.sc, game.first); }
  newBats();
  brains = [null, cpuBrain(level, (Date.now() % 1e9) >>> 0)];
  acc = 0; banner = null; result = null;
  saveSolo();
  mode = 'play';
  hideAll(); wake();
}
// The game alone is saved after each point, so a reload goes on from the score (never mid-rally).
function saveSolo() { if (!net && game && !game.over) save('kesken', { lvl: level, sc: game.sc, first: game.first }); }
// A game goes on past 11 for as long as nobody leads by two, so a live score has no ceiling.
function readSolo() {
  const m = load('kesken', null);
  if (!m || !Array.isArray(m.sc) || m.sc.length !== 2 || m.sc.some(n => !(Number.isSafeInteger(n) && n >= 0)) || winnerOf(m.sc) >= 0 || !(Number.isInteger(m.lvl) && m.lvl >= 0 && m.lvl < LEVELS.length)) { drop('kesken'); return null; }
  return { lvl: m.lvl, sc: m.sc, first: m.first === 1 ? 1 : 0 };
}
function soloPoint(f, w) {
  addPoint(game, w);
  pointSound(w);
  saveSolo();
  if (game.over) soloRecord();
}
function soloNext() {
  if (game.over) { showEnd(); return; }
  game.r++; game.ph = 'serve'; game.flight = null; game.wait = 0.35;
}
function soloRecord() {
  const won = game.winner === 0, a = recOf(level);
  a[won ? 0 : 1]++; record[level] = a; save('voitot', record);
  drop('kesken');
  result = { won, sc: game.sc.slice(), names: names.slice(), rec: a, net: false };
}
function pointSound(w) {
  banner = { text: w === view ? 'Piste sinulle!' : 'Piste: ' + names[w], t: 0, good: w === view };
  if (w === view) sfx('onnistui', { vol: 0.25 }, 880);
}

// ---- One rally step by step ----
// The ball a serve waits on: over the server's bat.
function heldBall() {
  const b = bats[game.sv];
  return { x: b.x, y: 0.3 + Math.sin(performance.now() / 160) * 0.015, z: b.z };
}
function tryServe(side, aim) {
  const g = game;
  if (!g || g.ph !== 'serve' || g.sv !== side || g.wait > 0 || g.flight) return false;
  const f = newFlight(0, side, true, serveLaunch(bats[side], side, aim, rnd));
  g.flight = f; g.ph = 'play';
  hitSound('drive');
  hooks.launched(f);
  return true;
}
// A hit by `side` on flight f: from the computer's plan or from my bat's swing.
function hitBy(side, f) {
  const b = bats[side], ball = f.ball, brain = cpuAt(side) ? brains[side] : null;
  let kind, aim;
  if (brain) { kind = brain.kind; aim = brain.aim; }
  else {
    const fwd = -b.vz * sgn(side);
    kind = fwd > 3.0 ? 'smash' : fwd > 0.8 ? 'drive' : 'block';
    // In world x: a sideways swing, and where on the bat it met, send it that way.
    aim = clamp(b.vx / 2.2 + (ball.x - b.x) / REACH * 0.4, -1, 1);
    if (tutorial && side === view) { tutorial = false; save('osattu', true); }
  }
  const off = clamp(Math.abs(ball.x - b.x) / REACH, 0, 1);
  const nf = newFlight(f.n + 1, side, false, shotLaunch(ball, side, kind, aim, off, rnd));
  f.over = { hit: true };
  game.flight = nf;
  b.swing = 1;
  hitSound(kind);
  hooks.launched(nf);
}
function stepOnce(f) {
  const R = 1 - f.by, pz = f.ball.z, ev = ballStep(f.ball);
  evSound(ev, f.ball);
  if (!judgeHere(R)) {
    // Not ours to judge: it flies on to the other end and waits there for its word.
    if (f.ball.z * sgn(R) > HL + 0.55) f.held = true;
    return;
  }
  const res = judge(f, ev);
  if (res) { hooks.point(f, res.w); return; }
  if (hittable(f) && meets(f, pz, bats[R])) hitBy(R, f);
}
function advance(dtg) {
  const g = game;
  if (!g) return;
  if (g.ph === 'serve' || g.ph === 'point' || g.ph === 'over') g.wait -= dtg;
  if ((g.ph === 'point' || g.ph === 'over') && g.wait <= 0) hooks.next();
  if (game !== g) return;
  for (const side of [0, 1]) {
    if (!cpuAt(side) || !brains[side]) continue;
    cpuThink(g, side, bats[side], brains[side], bats[1 - side], dtg);
    if (cpuServes(g, side, brains[side], dtg)) tryServe(side, (brains[side].r() - 0.5) * 1.6);
  }
  const f = g.flight;
  if (!f || f.over || f.held || g.ph !== 'play') { acc = 0; return; }
  acc += dtg;
  while (acc >= STEP) {
    acc -= STEP;
    const cur = g.flight;
    stepOnce(cur);
    if (cur.over || cur.held || cur.ball.dead) { if (cur.over || cur.held) acc = 0; if (g.flight === cur) break; }
  }
}

// ---- The finger moves my bat ----
// The bat sits a little above the finger, so the finger never hides it. Its swing is how fast it
// moved over the last 80 ms; forward fast is a drive, faster a smash, still is a block.
const LIFT = 46;
let finger = null;
function tableAt(px, py) {
  if (V3 && !no3d) return unproject3d(px, py);
  return flatUnproject(px, py);
}
function moveBat(px, py) {
  if (!bats) return;
  const b = bats[view], s = sgn(view);
  const p = tableAt(px, py - LIFT);
  let x, z;
  if (p) { x = p.x; z = p.z; } else { x = b.tx; z = -s * 9; }
  const d = clamp(z * s - HL, -0.3, 1.05);
  b.tx = clamp(x, -1.15, 1.15); b.tz = s * (HL + d);
}
c.addEventListener('pointerdown', e => {
  if (mode !== 'play' && mode !== 'netplay') return;
  e.preventDefault();
  if (finger) return;
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
  finger = e.pointerId;
  moveBat(e.clientX, e.clientY);
  if (bats) bats[view].jump = true;   // the bat jumps to a new finger: no swing from that
});
c.addEventListener('pointermove', e => { if (finger === e.pointerId) moveBat(e.clientX, e.clientY); });
function lift(e) { if (finger === e.pointerId) finger = null; }
c.addEventListener('pointerup', lift);
c.addEventListener('pointercancel', lift);
// My bat goes to the finger's spot each frame; its speed is measured from where it has been.
function myBat(dt) {
  const b = bats[view], now = performance.now() / 1000;
  b.x = b.tx; b.z = b.tz;
  if (b.jump) { b.hist = []; b.jump = false; }
  b.hist.push([now, b.x, b.z]);
  while (b.hist.length > 2 && now - b.hist[0][0] > 0.08) b.hist.shift();
  const o = b.hist[0], span = now - o[0];
  if (span > 0.01) { b.vx = (b.x - o[1]) / span; b.vz = (b.z - o[2]) / span; } else { b.vx = 0; b.vz = 0; }
}
// Every bat's height follows the ball near it, and its swing settles.
function batHeights(ball, dt) {
  for (const side of [0, 1]) {
    const b = bats[side];
    const near = ball && Math.abs(ball.z - b.z) < 1.2 ? clamp(ball.y, 0.04, 0.6) : 0.15;
    b.y += (near - b.y) * Math.min(1, dt * 12);
    b.swing = Math.max(0, (b.swing || 0) - dt * 4);
    if (cpuAt(side) || side !== view) {
      // A bat not moved by a finger here: its speed from its last frame, for the drawing.
      if (b.px !== undefined && dt > 0) { b.vx = (b.x - b.px) / dt; b.vz = (b.z - b.pz) / dt; }
      b.px = b.x; b.pz = b.z;
    }
  }
}

// ---- Menus (DOM, over the canvas) ----
const $ = id => document.getElementById(id);
function hideAll() { for (const id of ['menu', 'end']) $(id).hidden = true; }
function showMenu() {
  mode = 'menu'; game = null;
  hideAll(); $('menu').hidden = false;
  const box = $('levels'); box.innerHTML = '';
  LEVELS.forEach((L, i) => {
    const b = document.createElement('button'), r = recOf(i);
    b.className = 'lvl' + (i === level ? ' on' : '');
    b.innerHTML = '<b>' + L.name + '</b><small>' + L.note + (r[0] + r[1] ? ' · voitot ' + r[0] + '/' + (r[0] + r[1]) : '') + '</small>';
    b.addEventListener('click', () => { level = i; save('taso', i); sfx('valinta', { vol: 0.3 }); showMenu(); });
    box.appendChild(b);
  });
  wake();
}
function showEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result, me = r.net ? r.side : 0, a = r.sc[me], b = r.sc[1 - me];
  $('endTitle').textContent = r.won ? 'Voitit!' : 'Hävisit';
  $('endScore').textContent = a + '–' + b;
  $('endNote').textContent = r.net ? (r.helped ? 'Tietokone pelasi puolestasi' : 'vastaan ' + r.foe) :
    LEVELS[level].name + ': voitot ' + r.rec[0] + ' / ' + (r.rec[0] + r.rec[1]);
  $('again').textContent = r.net ? 'Takaisin huoneeseen' : 'Uusi peli';
  $('toMenu').hidden = !!r.net;
  sfx(r.won ? 'voitto' : 'tappio', { vol: 0.3 });
  wake();
}
$('go').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); soloGame(null); });
$('again').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (result && result.net) backRoom(); else soloGame(null); });
$('friends').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (window.AiPelitRooms) AiPelitRooms.open(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });

// ---- Drawing on the 2D canvas ----
function shadowText(t, x, y, size, colr, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(0,10,30,.6)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = colr; cx.fillText(t, x, y);
}
function roundRect(x, y, w, h, r) {
  cx.beginPath(); cx.moveTo(x + r, y); cx.arcTo(x + w, y, x + w, y + h, r); cx.arcTo(x + w, y + h, x, y + h, r);
  cx.arcTo(x, y + h, x, y, r); cx.arcTo(x, y, x + w, y, r); cx.closePath();
}
// Without 3D: the table flat from above, my end at the bottom, the ball's height as its lift.
let flat = null;
function flatView() {
  const top = SAFE_T + 70, bottom = H - SAFE_B - 20;
  const k = Math.min((W - SAFE_L - SAFE_R - 40) / (HW * 2 + 1.2), (bottom - top) / (HL * 2 + 1.6));
  return { k, cx: (SAFE_L + W - SAFE_R) / 2, cy: (top + bottom) / 2 };
}
function flatProject(x, y, z) {
  const f = flat || flatView(), s = sgn(view);
  return { x: f.cx + x * f.k * s, y: f.cy + z * f.k * s - Math.max(0, y) * f.k * 0.6 };
}
function flatUnproject(px, py) {
  const f = flat || flatView(), s = sgn(view);
  return { x: (px - f.cx) / f.k * s, z: (py - f.cy) / f.k * s };
}
function draw2d(st) {
  flat = flatView();
  cx.fillStyle = '#a5683a'; cx.fillRect(0, 0, W, H);
  const p0 = flatProject(-HW, 0, -HL), p1 = flatProject(HW, 0, HL);
  const x = Math.min(p0.x, p1.x), y = Math.min(p0.y, p1.y), w = Math.abs(p1.x - p0.x), h = Math.abs(p1.y - p0.y);
  cx.fillStyle = '#1f5aa8'; cx.fillRect(x, y, w, h);
  cx.strokeStyle = '#fff'; cx.lineWidth = 2; cx.strokeRect(x, y, w, h);
  cx.beginPath(); cx.moveTo(x + w / 2, y); cx.lineTo(x + w / 2, y + h); cx.lineWidth = 1; cx.stroke();
  cx.fillStyle = '#ddd'; cx.fillRect(x - 8, y + h / 2 - 2, w + 16, 4);
  [0, 1].forEach(side => {
    const b = st.bats[side], p = flatProject(b.x, 0, b.z);
    cx.fillStyle = side === 0 ? '#d8282f' : '#2c5fd0';
    cx.beginPath(); cx.arc(p.x, p.y, 0.078 * flat.k + 3, 0, TAU); cx.fill();
  });
  if (st.ball) {
    const sh = flatProject(st.ball.x, 0, st.ball.z), p = flatProject(st.ball.x, st.ball.y, st.ball.z);
    cx.fillStyle = 'rgba(0,0,0,.35)'; cx.beginPath(); cx.arc(sh.x, sh.y, 4, 0, TAU); cx.fill();
    cx.fillStyle = '#ffa63d'; cx.beginPath(); cx.arc(p.x, p.y, 5, 0, TAU); cx.fill();
  }
}
// The score at the top, the texts in the middle, the hint at the bottom.
function drawHUD(dt) {
  const g = game, me = view, foe = 1 - view;
  const bw = Math.min(250, W - SAFE_L - SAFE_R - 150), x0 = W / 2 - bw / 2, y0 = SAFE_T + 10;
  cx.fillStyle = 'rgba(10,20,40,.6)'; roundRect(x0, y0, bw, 48, 12); cx.fill();
  const name = n => { cx.font = '700 13px system-ui,sans-serif'; let t = n; while (cx.measureText(t).width > bw / 2 - 40 && t.length > 2) t = t.slice(0, -2) + '…'; return t; };
  shadowText(String(g.sc[me]), x0 + 26, y0 + 25, 26, '#fff', 'center', 900);
  shadowText(String(g.sc[foe]), x0 + bw - 26, y0 + 25, 26, '#fff', 'center', 900);
  shadowText(name(names[me]), x0 + 48, y0 + 17, 13, '#ffd84a', 'left', 700);
  shadowText(name(names[foe]), x0 + bw - 48, y0 + 17, 13, '#cfe0ff', 'right', 700);
  // Who serves: a small ball under their name.
  cx.fillStyle = '#ffa63d';
  cx.beginPath(); cx.arc(g.sv === me ? x0 + 54 : x0 + bw - 54, y0 + 35, 5, 0, TAU); cx.fill();
  const midY = H * (LAND ? 0.42 : 0.36);
  if (banner) {
    banner.t += dt;
    if (banner.t > 1.4) banner = null;
    else shadowText(banner.text, W / 2, midY, 26, banner.good ? '#ffd84a' : '#fff', 'center', 900);
  }
  if (g.ph === 'over' && !banner) shadowText(g.winner === me ? 'Voitit pelin!' : 'Peli päättyi', W / 2, midY, 28, '#fff', 'center', 900);
  // Serve hint for me, the first rallies a tutorial.
  const hintY = H - SAFE_B - (LAND ? 26 : 40);
  if (g.ph === 'serve' && g.sv === me && g.wait <= 0 && canPlay()) shadowText('Syötä: vedä mailaa nopeasti ylös', W / 2, hintY, 15, '#fff', 'center', 800);
  else if (tutorial && g.ph === 'play' && canPlay()) shadowText('Liikuta mailaa sormella pallon eteen', W / 2, hintY, 14, '#fff', 'center', 700);
  if (g.ph === 'serve' && g.sv === foe && g.wait <= 0 && !cpuAt(foe) && net) shadowText(names[foe] + ' syöttää', W / 2, midY + 40, 16, '#cfe0ff', 'center', 700);
  if (net && net.note) shadowText(net.note, W / 2, midY + 70, 17, '#fff', 'center', 800);
}
const canPlay = () => !net || netCanPlay();
function scene() {
  let ball = null, moving = false;
  if (game) {
    const f = game.flight;
    if (game.ph === 'serve' && !f) ball = heldBall();
    else if (f) { ball = f.ball; moving = !f.held && !f.ball.dead && !f.over; }
  }
  return { view, bats: bats || [{ x: 0, y: 0.15, z: HL + 0.4 }, { x: 0, y: 0.15, z: -HL - 0.4 }], ball, moving };
}
function draw(dt) {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  const st = scene();
  if (V3 && !no3d) render3d(st, dt);
  else draw2d(st);
  if (no3d && mode === 'menu') shadowText('Puhelimesi ei pysty piirtämään 3D-kuvaa.', W / 2, H - SAFE_B - 20, 13, '#fff', 'center', 700);
  if (mode === 'netwait') shadowText('Odotetaan…', W / 2, H * 0.4, 20, '#fff', 'center', 800);
  if (game && (mode === 'play' || mode === 'netplay')) drawHUD(dt);
}

// ---- The main loop ----
// It draws every frame while a game is on; in the menus it draws a few frames and rests, so a
// phone left on the menu does not heat up (docs/making-games.md, Pasianssi v1).
let raf = 0, last = 0, still = 0;
function wake() { still = 0; if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
// One frame of play: my bat, the computer, the ball, a serve by my swing.
function playFrame(dt) {
  if (!game || !bats) return;
  myBat(dt);
  const g = game, b = bats[view];
  if (g.ph === 'serve' && g.sv === view && -b.vz * sgn(view) > 0.8 && canPlay() && finger !== null) {
    tryServe(view, clamp(b.vx / 2.2, -1, 1));
  }
  advance(dt * SLOW);
  const st = scene();
  batHeights(st.ball, dt);
}
function frame(now) {
  raf = 0;
  const ms = last ? now - last : 16;
  const dt = last ? Math.min(0.05, ms / 1000) : 1 / 60; last = now;
  if (net) netTick(dt);
  else if (mode === 'play') playFrame(dt);
  draw(dt);
  const moving = mode === 'play' || mode === 'netplay' || mode === 'netwait';
  if (moving) tune(ms);
  document.body.classList.toggle('playing', moving);
  if (moving || still++ < 3) raf = requestAnimationFrame(frame);
}
resize();
const resumed = !(window.AiPelitRooms && AiPelitRooms.inRoom) ? readSolo() : null;
if (window.AiPelitRooms && AiPelitRooms.inRoom) hideAll();
else if (resumed) { level = resumed.lvl; soloGame(resumed); }
else showMenu();
