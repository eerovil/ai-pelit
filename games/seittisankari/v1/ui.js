'use strict';
// Seittisankari v1 (#529): the fingers, the camera, the menus, the saves, the sounds, the 2D
// layer over the 3D picture (goal, time, stick, buttons) and the main loop.

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

// ---- Saves (ai-pelit:seittisankari:*) ----
const KEY = 'ai-pelit:seittisankari:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { if (v === null) localStorage.removeItem(KEY + k); else localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
// ---- Sounds (aanet-5, quiet: #337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['suhahdus', 'tomahdys', 'pop', 'valinta', 'voitto', 'tappio']);
const sfx = (name, opts) => S && S.play(name, opts);

// ---- The round ----
let mode = 'menu', world = null, acc = 0, result = null, saveT = 0;
const cam = { yaw: 0, pitch: 0.3, manualT: 9 };
// Into the city: where the hero was last time, if a spot is saved (a reload or a turn of the
// phone goes on, rule 5).
function startFree() {
  world = newWorld();
  const q = (load('kierros', null) || {}).h;
  if (q) restore(world, q);
  cam.yaw = world.hero.yaw; cam.pitch = 0.3; cam.manualT = 9;
  mode = 'play'; acc = 0; result = null; stick = null; webPtr = null; jumpQ = false; lookPtr = null;
  hideAll();
  saveRound();
}
function saveRound() {
  if (!world || mode !== 'play') return;
  const h = world.hero;
  save('kierros', { h: { x: h.x, y: h.y, z: h.z, yaw: h.yaw, st: h.st === 'wall' ? 'wall' : 'air', box: h.box ? h.box.id : -1, nx: h.nx, nz: h.nz } });
}
function restore(w, q) {
  const h = w.hero;
  if (![q.x, q.y, q.z].every(Number.isFinite)) return;
  h.x = clamp(q.x, -EDGE, EDGE); h.y = clamp(q.y, 0, 400); h.z = clamp(q.z, -EDGE, EDGE); h.yaw = +q.yaw || 0; h.st = 'air';
  if (q.st === 'wall' && CITY[q.box]) { h.st = 'wall'; h.box = CITY[q.box]; h.nx = q.nx; h.nz = q.nz; }
}

// ---- The fingers ----
// Left half: a floating stick. Right half: Seitti (held) and Hyppy, and a drag anywhere else
// turns the camera.
const STICK = 52;
let stick = null, webPtr = null, jumpQ = false, jumpFlash = 0, lookPtr = null;
function buttons() {
  const r = LAND ? 46 : 50, rj = LAND ? 34 : 38;
  const web = { x: W - SAFE_R - r - (LAND ? 26 : 20), y: H - SAFE_B - r - (LAND ? 20 : 30), r };
  const jump = LAND ? { x: web.x - r - rj - 20, y: web.y + 10, r: rj } : { x: web.x - 30, y: web.y - r - rj - 26, r: rj };
  return { web, jump };
}
const gapTo = (b, e) => Math.hypot(e.clientX - b.x, e.clientY - b.y) - b.r;
const playing = () => (mode === 'play' && !!world) ||
  (mode === 'netplay' && world && typeof net !== 'undefined' && net && !net.res && !!net.me);
// Each finger gets its own job. A button already held by one thumb is not offered to the other,
// so a second thumb landing near the first still does what it is near (#529: a jump tapped right
// beside the held Seitti took the web over instead).
c.addEventListener('pointerdown', e => {
  if (!playing()) return;
  e.preventDefault();
  try { c.setPointerCapture(e.pointerId); } catch (_) {}   // its lift comes here even off the canvas
  // With Seitti held, a second thumb on or beside it jumps.
  const b = buttons(), dw = webPtr === null ? gapTo(b.web, e) : Infinity, dj = Math.min(gapTo(b.jump, e), webPtr === null ? Infinity : gapTo(b.web, e));
  if (Math.min(dw, dj) < 22) {
    if (dw <= dj) webPtr = e.pointerId;
    else { jumpQ = true; jumpFlash = 0.15; }
    return;
  }
  // Left half: the stick; right half: the camera. A finger whose side is taken does the other job.
  const left = e.clientX < W / 2;
  if ((left && !stick) || (!left && lookPtr && !stick)) stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
  else if (!lookPtr) lookPtr = { id: e.pointerId, x: e.clientX, y: e.clientY };
});
c.addEventListener('pointermove', e => {
  if (stick && e.pointerId === stick.id) {
    stick.x = e.clientX; stick.y = e.clientY;
    const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy);
    if (d > STICK * 1.6) { stick.x0 = stick.x - dx / d * STICK * 1.6; stick.y0 = stick.y - dy / d * STICK * 1.6; }
  } else if (lookPtr && e.pointerId === lookPtr.id) {
    cam.yaw -= (e.clientX - lookPtr.x) * 0.008;
    cam.pitch = clamp(cam.pitch + (e.clientY - lookPtr.y) * 0.006, -0.35, 1.1);
    lookPtr.x = e.clientX; lookPtr.y = e.clientY; cam.manualT = 0;
  }
});
function lift(e) {
  if (stick && e.pointerId === stick.id) stick = null;
  if (lookPtr && e.pointerId === lookPtr.id) lookPtr = null;
  if (e.pointerId === webPtr) webPtr = null;
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
function input() {
  const [ix, iy] = stickInput();
  const inp = { ix, iy, jump: jumpQ, web: webPtr !== null, yaw: cam.yaw };
  jumpQ = false;
  return inp;
}
// The camera turns itself behind where the hero goes, unless the player just turned it.
function angDiff(a, b) { return Math.atan2(Math.sin(b - a), Math.cos(b - a)); }
function stepCam(h, dt) {
  cam.manualT += dt;
  if (cam.manualT < 1.5) return;
  let want = null, rate = 0;
  if (h.st === 'wall') { want = Math.atan2(-h.nx, -h.nz); rate = 3; }
  else {
    const sp = Math.hypot(h.vx, h.vz);
    if (sp > 3) { want = Math.atan2(h.vx, h.vz); rate = h.st === 'ground' ? 1.6 : 1.2; }
  }
  if (want !== null) cam.yaw += angDiff(cam.yaw, want) * Math.min(1, dt * rate);
  const wantP = h.st === 'wall' ? 0.05 : h.st === 'swing' ? 0.22 : 0.3;
  if (cam.manualT > 2.5) cam.pitch += (wantP - cam.pitch) * Math.min(1, dt * 1.5);
}

// ---- Menus (DOM over the canvas) ----
const $ = id => document.getElementById(id);
function hideAll() { for (const id of ['menu', 'end']) $(id).hidden = true; }
const fmt = t => { t = Math.max(0, t); const m = Math.floor(t / 60), s = t - m * 60; return m + ':' + (s < 10 ? '0' : '') + s.toFixed(1).replace('.', ','); };
function showMenu() {
  mode = 'menu'; world = null;
  hideAll(); $('menu').hidden = false;
  $('friends').hidden = !window.AiPelitRooms;
}
$('friends').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (window.AiPelitRooms) AiPelitRooms.open(); });
$('free').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); startFree(); });
$('toMenu').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (result && result.net) backRoom(); else showMenu(); });
$('quit').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); saveRound(); showMenu(); });

// ---- The 2D layer ----
function shadowText(t, x, y, size, col, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif'; cx.textAlign = align || 'center'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(10,20,40,.6)'; cx.fillText(t, x + 1.5, y + 2);
  cx.fillStyle = col; cx.fillText(t, x, y);
}
let aimNow = null;
let hintT = load('ohje', 0) ? 99 : 0;   // the controls, told once on the phone's first visit
function drawHUD(w) {
  const h = w.hero, top = SAFE_T + 22;
  shadowText('↑ ' + Math.round(h.y) + ' m', W - SAFE_R - 14, top, 16, '#e8f4ff', 'right', 800);
  if (hintT < 16) drawHints();
  drawControls(h);
}
function drawHints() {
  const lines = hintT < 8 ? ['Juokse seinää päin: tartut siihen', 'Tikku ylös: kiipeä'] : ['Pidä Seitti pohjassa: heilu', 'Päästä irti heilahduksen huipulla'];
  shadowText(lines[0], W / 2, H * 0.3, 15, '#fff', 'center', 700);
  shadowText(lines[1], W / 2, H * 0.3 + 20, 15, '#fff', 'center', 700);
}
function drawControls(h) {
  if (stick) {
    cx.strokeStyle = 'rgba(255,255,255,.45)'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(stick.x0, stick.y0, STICK, 0, TAU); cx.stroke();
    const [ix, iy] = stickInput();
    cx.fillStyle = 'rgba(255,255,255,.6)'; cx.beginPath(); cx.arc(stick.x0 + ix * STICK, stick.y0 + iy * STICK, 20, 0, TAU); cx.fill();
  }
  const b = buttons();
  const canWeb = !!aimNow || h.st === 'swing';   // the sky holds a web, except high over the roofs
  cx.fillStyle = webPtr !== null ? 'rgba(255,255,255,.95)' : canWeb ? 'rgba(30,170,160,.88)' : 'rgba(60,80,90,.55)';
  cx.beginPath(); cx.arc(b.web.x, b.web.y, b.web.r, 0, TAU); cx.fill();
  cx.strokeStyle = 'rgba(255,255,255,.75)'; cx.lineWidth = 3; cx.stroke();
  shadowText('Seitti', b.web.x, b.web.y, 17, webPtr !== null ? '#0b4a46' : '#fff', 'center', 900);
  cx.fillStyle = jumpFlash > 0 ? 'rgba(255,255,255,.95)' : 'rgba(255,140,60,.85)';
  cx.beginPath(); cx.arc(b.jump.x, b.jump.y, b.jump.r, 0, TAU); cx.fill(); cx.stroke();
  shadowText('Hyppy', b.jump.x, b.jump.y, 15, '#fff', 'center', 900);
}

// ---- In a room: the others' heroes, names over them, the round's clock and score ----
function netHeroes(dt) {
  const out = [];
  for (const p of net.players) {
    if (p.id === RM.me && net.me) out.push({ id: p.id, col: p.col, h: world.hero });
    else out.push({ id: p.id, col: p.col, h: drawnHero(p, dt) });
  }
  return out;
}
function drawNetHUD(w) {
  const top = SAFE_T + 22, M = NET_MODES.find(o => o.key === net.mode) || NET_MODES[0];
  if (M.limit) { const left = Math.max(0, M.limit - net.rt); shadowText(fmt(left), LAND ? SAFE_L + 150 : W / 2, top, 22, left < 15 ? '#ff8080' : '#fff', 'center', 900); }
  else shadowText(fmt(net.rt), LAND ? SAFE_L + 150 : W / 2, top, 20, '#fff', 'center', 900);
  let goal = M.note;
  const gb = goalBox();
  if (gb) {
    // The marked roof: how far, and an arrow toward it as the camera looks.
    const t = roofTop(gb), dx = t.x - w.hero.x, dz = t.z - w.hero.z, d = Math.round(Math.hypot(dx, dz));
    goal = 'Merkitylle katolle! ' + (d > 15 ? d + ' m' : '↑ ' + Math.max(0, Math.round(gb.h - w.hero.y)) + ' m');
    if (d > 15) drawArrow(W / 2, (LAND ? top + 26 : top + 30) + 32, angDiff(cam.yaw, Math.atan2(dx, dz)));
  }
  shadowText(goal, W / 2, LAND ? top + 26 : top + 30, 15, '#fff', 'center', 800);
  shadowText('↑ ' + Math.round(w.hero.y) + ' m', W - SAFE_R - 14, top, 16, '#e8f4ff', 'right', 800);
  // Names over the others' heroes.
  for (const p of net.players) {
    if (p.id === RM.me || !p.dh) continue;
    const q = L3D.project(p.dh.x, p.dh.y + 2.4, p.dh.z);
    if (!q) continue;
    shadowText(p.name, q[0], q[1], 13, p.col, 'center', 800);
  }
  if (RM.paused) shadowText('Odotetaan kaveria…', W / 2, H * 0.4, 18, '#ffd166', 'center', 900);
  if (net.me) { if (hintT < 16) drawHints(); drawControls(w.hero); }
  else shadowText('Katsot kierrosta', W / 2, H - SAFE_B - 40, 16, '#fff', 'center', 800);
}
function drawArrow(x, y, a) {
  cx.save(); cx.translate(x, y); cx.rotate(-a);
  cx.fillStyle = '#ffd166'; cx.strokeStyle = 'rgba(10,20,40,.6)'; cx.lineWidth = 3;
  cx.beginPath(); cx.moveTo(0, -16); cx.lineTo(12, 10); cx.lineTo(0, 4); cx.lineTo(-12, 10); cx.closePath();
  cx.stroke(); cx.fill(); cx.restore();
}
function showNetEnd() {
  mode = 'end';
  hideAll(); $('end').hidden = false;
  const r = result;
  $('endTitle').textContent = r.won ? 'Voitit!' : r.winRow ? r.winRow.n + ' voitti' : 'Kierros päättyi';
  $('endNote').textContent = r.rows.map((o, i) => (i + 1) + '. ' + o.n + ' ' +
    (o.t !== null ? fmt(o.t) : '↑ ' + o.y + ' m')).join('  ·  ');
  $('toMenu').textContent = 'Takaisin huoneeseen';
  sfx(r.won ? 'voitto' : 'tappio', { vol: 0.3 });
}

// ---- The main loop ----
let last = 0;
const menuHero = newHero(LX(2) + 20, 0, LX(2) + 20, 0);
let menuT = 0;
function frame(now) {
  requestAnimationFrame(frame);
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60; last = now;
  if (jumpFlash > 0) jumpFlash -= dt;
  if (mode === 'play' && world) {
    acc += dt;
    while (acc >= STEP) { acc -= STEP; tick(STEP); }
    saveT += dt; if (saveT > 2) { saveT = 0; saveRound(); }
    if (hintT < 16) { hintT += dt; if (hintT >= 16) save('ohje', 1); }
  }
  if (mode === 'netplay' && typeof netTick === 'function') netTick(dt);
  draw(dt);
  document.body.classList.toggle('playing', mode === 'play' || mode === 'netplay');
  document.body.classList.toggle('net', mode === 'netplay' || mode === 'netwait');
}
// One fixed step: the hero, the camera, the sounds.
function tick(dt) {
  const w = world, h = w.hero, st0 = h.st, lands0 = h.lands || 0;
  stepHero(h, input(), dt);
  stepCam(h, dt);
  stepRound(w, dt);
  if (h.st === 'swing' && st0 !== 'swing') sfx('suhahdus', { vol: 0.25, rate: 1.3 });
  if ((h.lands || 0) > lands0) sfx('tomahdys', { vol: 0.15 });
  if (h.jumped) { h.jumped = false; sfx('pop', { vol: 0.2 }); }
}
function draw(dt) {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  let s;
  if (world) {
    const h = world.hero;
    const fx = Math.sin(cam.yaw), fz = Math.cos(cam.yaw);
    aimNow = h.st !== 'swing' && playing() ? aimAnchor(h, fx, fz) : null;
    const heroes = mode === 'netplay' && net ? netHeroes(dt) : [{ id: 'me', col: '#1fb5a8', h }];
    s = { w: world, hero: h, heroes, cam, playing: playing() };
  } else {
    // Behind the menu: the city turning slowly.
    menuT += dt; cam.yaw = menuT * 0.08; cam.pitch = 0.5;
    menuHero.y = 45;
    s = { w: null, hero: menuHero, heroes: [], cam };
  }
  if (window.L3D && L3D.draw) L3D.draw(s, dt);
  if (window.L3D && L3D.failed) {
    cx.fillStyle = '#16304a'; cx.fillRect(0, 0, W, H);
    shadowText('Puhelimesi ei osaa piirtää 3D-kuvaa', W / 2, H * 0.3, 17, '#ffd166', 'center', 800);
  }
  if (world && mode === 'play') drawHUD(world);
  else if (world && mode === 'netplay' && net) drawNetHUD(world);
  else if (mode === 'netwait') shadowText('Odotetaan kierrosta…', W / 2, H / 2, 18, '#fff', 'center', 800);
}
resize();
showMenu();
requestAnimationFrame(frame);
