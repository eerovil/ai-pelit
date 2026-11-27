'use strict';
// Seittisankari v2 (#529), v4 (#561): the fingers, the camera, the menus, the saves, the sounds, the 2D
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
  // v2 keeps its round under its own key, so a cached v1 (which writes `kierros` as {h}) can
  // never overwrite the marked roof; v1's spot is read only when v2 has saved none.
  const k = load('kierros2', null) || load('kierros', null) || {};
  if (k.h) restore(world, k.h);
  // v2's missions: the roof marked last time, its clock, and how many are done (v1 saved none).
  world.done = Math.max(0, load('tehtavat', 0) | 0);
  // v4 (#561): the mission's kind follows the count; a roof's turn keeps the marked roof, and a
  // robber mission left open starts again with new robbers, its clock going on.
  const kind = kindFor(world.done), t4 = load('tehtava4', null) || {};
  if (!isCrook(kind) && CITY[k.g] && (kind === 'katto' || CITY[k.g].tower || t4.k === kind)) {
    world.kind = kind; setGoal(world, k.g); world.gt = Math.max(0, +k.gt || 0);
  } else {
    startMission(world);
    if (t4.k === kind) world.gt = Math.max(0, +t4.gt || 0);
  }
  cam.yaw = world.hero.yaw; cam.pitch = 0.3; cam.manualT = 9;
  mode = 'play'; acc = 0; result = null; stick = null; webPtr = null; jumpQ = false; lookPtr = null; pullPtr = null; pullQ = null; catchFx = null;
  hideAll();
  saveRound();
}
function saveRound() {
  if (!world || mode !== 'play') return;
  const h = world.hero;
  save('kierros2', { h: { x: h.x, y: h.y, z: h.z, yaw: h.yaw, st: h.st === 'wall' ? 'wall' : 'air', box: h.box ? h.box.id : -1, nx: h.nx, nz: h.nz },
    g: world.goal, gt: Math.round(world.gt * 10) / 10 });
  save('tehtava4', { k: world.kind, gt: Math.round(world.gt * 10) / 10 });
}
function restore(w, q) {
  const h = w.hero;
  if (![q.x, q.y, q.z].every(Number.isFinite)) return;
  h.x = clamp(q.x, -EDGE, EDGE); h.y = clamp(q.y, 0, 400); h.z = clamp(q.z, -EDGE, EDGE); h.yaw = +q.yaw || 0; h.st = 'air';
  if (q.st === 'wall' && CITY[q.box]) { h.st = 'wall'; h.box = CITY[q.box]; h.nx = q.nx; h.nz = q.nz; }
}

// ---- The fingers ----
// Left half: a floating stick. Right half: Seitti (held), Hyppy and Veto, and a drag anywhere
// else turns the camera, and so does sliding the held Seitti (#561). Veto (#560) is held to aim: the same finger turns the camera, and lifting
// it shoots the web along the camera's centre line.
const STICK = 52;
let stick = null, webPtr = null, jumpQ = false, jumpFlash = 0, lookPtr = null, pullPtr = null, pullQ = null, missFx = null, aimTurn = null, catchFx = null, webAt = null;
function buttons() {
  const r = LAND ? 46 : 50, rj = LAND ? 34 : 38, rp = LAND ? 32 : 34;
  const web = { x: W - SAFE_R - r - (LAND ? 26 : 20), y: H - SAFE_B - r - (LAND ? 20 : 30), r };
  const jump = LAND ? { x: web.x - r - rj - 20, y: web.y + 10, r: rj } : { x: web.x - 30, y: web.y - r - rj - 26, r: rj };
  // Upright: left of Seitti, on its row; sideways: above it.
  const pull = LAND ? { x: web.x + 4, y: web.y - r - rp - 22, r: rp } : { x: web.x - r - rp - 16, y: web.y + 14, r: rp };
  return { web, jump, pull };
}
const PITCH_AIM = -1.0;   // aiming may look much higher than the camera's own drag (#560)
const gapTo = (b, e) => Math.hypot(e.clientX - b.x, e.clientY - b.y) - b.r;
const playing = () => (mode === 'play' && !!world) ||
  (mode === 'netplay' && world && typeof net !== 'undefined' && net && !net.res && !!net.me && !RM.paused);
// Each finger gets its own job. A button already held by one thumb is not offered to the other,
// so a second thumb landing near the first still does what it is near (#529: a jump tapped right
// beside the held Seitti took the web over instead).
c.addEventListener('pointerdown', e => {
  if (!playing()) return;
  e.preventDefault();
  try { c.setPointerCapture(e.pointerId); } catch (_) {}   // its lift comes here even off the canvas
  // With Seitti held, a second thumb on or beside it jumps.
  // In the stick's half only a button itself counts, not the 22 px around it (#562 review: Veto's
  // margin took a thumb meant for the floating stick).
  const left = e.clientX < W / 2, gap = bt => { const g = gapTo(bt, e); return left && g > 0 ? Infinity : g; };
  const b = buttons(), dw = webPtr === null ? gap(b.web) : Infinity, dj = Math.min(gap(b.jump), webPtr === null ? Infinity : gap(b.web));
  const dp = pullPtr === null ? gap(b.pull) : Infinity;
  if (Math.min(dw, dj, dp) < 22) {
    if (dp < dw && dp < dj) {
      pullPtr = { id: e.pointerId, x: e.clientX, y: e.clientY }; cam.manualT = 0;
      // On a wall the aim turns straight back from it, level (Eero, #560): a quick swing of the
      // camera, not a jump, so the player sees where it turned (stepCam).
      const h = world.hero;
      aimTurn = h.st === 'wall' ? { yaw: Math.atan2(h.nx, h.nz), pitch: 0 } : null;
    }
    else if (dw <= dj) { webPtr = e.pointerId; webAt = { x: e.clientX, y: e.clientY }; }
    else { jumpQ = true; jumpFlash = 0.15; }
    return;
  }
  // Left half: the stick; right half: the camera. A finger whose side is taken does the other job.
  if ((left && !stick) || (!left && lookPtr && !stick)) stick = { id: e.pointerId, x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY };
  else if (!lookPtr) lookPtr = { id: e.pointerId, x: e.clientX, y: e.clientY };
});
c.addEventListener('pointermove', e => {
  if (stick && e.pointerId === stick.id) {
    stick.x = e.clientX; stick.y = e.clientY;
    const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy);
    if (d > STICK * 1.6) { stick.x0 = stick.x - dx / d * STICK * 1.6; stick.y0 = stick.y - dy / d * STICK * 1.6; }
  } else if (pullPtr && e.pointerId === pullPtr.id) {
    const dy = -(e.clientX - pullPtr.x) * 0.008, dp = (e.clientY - pullPtr.y) * 0.006;
    cam.yaw += dy; cam.pitch = clamp(cam.pitch + dp, PITCH_AIM, 1.1);
    if (aimTurn) { aimTurn.yaw += dy; aimTurn.pitch = clamp(aimTurn.pitch + dp, PITCH_AIM, 1.1); }   // the finger aims on top of the turn
    pullPtr.x = e.clientX; pullPtr.y = e.clientY; cam.manualT = 0;
  } else if (webAt && e.pointerId === webPtr) {
    // Sliding the held Seitti turns the camera like a drag, the web still held (Eero, #561).
    cam.yaw -= (e.clientX - webAt.x) * 0.008;
    cam.pitch = clamp(cam.pitch + (e.clientY - webAt.y) * 0.006, -0.35, 1.1);
    webAt.x = e.clientX; webAt.y = e.clientY; cam.manualT = 0;
  } else if (lookPtr && e.pointerId === lookPtr.id) {
    cam.yaw -= (e.clientX - lookPtr.x) * 0.008;
    cam.pitch = clamp(cam.pitch + (e.clientY - lookPtr.y) * 0.006, -0.35, 1.1);
    lookPtr.x = e.clientX; lookPtr.y = e.clientY; cam.manualT = 0;
  }
});
function lift(e) {
  if (stick && e.pointerId === stick.id) stick = null;
  if (lookPtr && e.pointerId === lookPtr.id) lookPtr = null;
  if (e.pointerId === webPtr) { webPtr = null; webAt = null; }
  if (pullPtr && e.pointerId === pullPtr.id) {
    pullPtr = null;
    // Shoot: a robber in the aim is caught (v4, #561) and the hero stays; else a hit pulls the
    // hero there; a miss is a web flying out and nothing else.
    if (world && playing()) {
      const h = world.hero, up = e.type === 'pointerup';
      const crook = up ? aimCrook(h, cam.yaw, cam.pitch, world.crooks) : null;
      const hit = up && !crook ? aimPull(h, cam.yaw, cam.pitch) : null;
      if (crook) { catchCrook(crook); catchFx = { t: 0.45, k: crook }; sfx('tomahdys', { vol: 0.2, rate: 0.8 }); }
      else if (hit) pullQ = hit;
      else if (e.type === 'pointerup') { const r = aimRay(h, cam.yaw, cam.pitch); missFx = { t: 0.3, x: r.ox + r.dx * 15, y: r.oy + r.dy * 15, z: r.oz + r.dz * 15 }; }
      sfx('suhahdus', { vol: 0.22, rate: hit ? 1.6 : 1.9 });
    }
  }
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
  const inp = { ix, iy, jump: jumpQ, web: webPtr !== null, yaw: cam.yaw, pull: pullQ };
  jumpQ = false; pullQ = null;
  return inp;
}
// The camera turns itself behind where the hero goes, unless the player just turned it.
function angDiff(a, b) { return Math.atan2(Math.sin(b - a), Math.cos(b - a)); }
function stepCam(h, dt) {
  cam.manualT += dt;
  if (aimTurn && pullPtr) {              // Veto on a wall: swing round in about 0.3 s
    const k = Math.min(1, dt * 12), dYaw = angDiff(cam.yaw, aimTurn.yaw);
    cam.yaw += dYaw * k; cam.pitch += (aimTurn.pitch - cam.pitch) * k;
    if (Math.abs(dYaw) < 0.002 && Math.abs(aimTurn.pitch - cam.pitch) < 0.002) { cam.yaw = aimTurn.yaw; cam.pitch = aimTurn.pitch; aimTurn = null; }
  } else aimTurn = null;
  if (pullPtr) cam.manualT = 0;          // aiming: the camera stays where the finger put it
  if (cam.manualT < 1.5) return;
  let want = null, rate = 0;
  if (h.st === 'wall') { want = Math.atan2(-h.nx, -h.nz); rate = 3; }
  else {
    const sp = Math.hypot(h.vx, h.vz);
    if (sp > 3) { want = Math.atan2(h.vx, h.vz); rate = h.st === 'ground' ? 1.6 : 1.2; }
  }
  if (want !== null) cam.yaw += angDiff(cam.yaw, want) * Math.min(1, dt * rate);
  const wantP = h.st === 'wall' ? 0.05 : h.st === 'swing' || h.st === 'pull' ? 0.22 : 0.3;
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
// v3's Veto and the jump off the web, told once more to phones that saw the old hints (#560).
let hint3T = load('ohje3', 0) ? 99 : 0;
function stepHint3(dt) {
  if (hintT < 16 || hint3T >= 9) return;
  hint3T += dt; if (hint3T >= 9) save('ohje3', 1);
}
// v4's robber missions: two lines the first time each kind starts (#561).
const HINT4 = {
  rosvot: ['Rosvoja katolla!', 'Pidä Veto pohjassa, tähtää rosvoon, päästä irti'],
  auto: ['Karkuriauto pakenee kaduilla!', 'Pidä Veto pohjassa, tähtää autoon, päästä irti'],
  heli: ['Karkurihelikopteri lentää korkealla!', 'Mene ylös ja tähtää Vedolla siihen'],
};
let hint4 = load('ohje4', null) || {}, hint4T = 0;
function stepHint4(w, dt) {
  if (hintT < 16 || hint3T < 9 || !HINT4[w.kind] || hint4[w.kind] || w.got) return;
  hint4T += dt;
  if (hint4T >= 7) { hint4[w.kind] = 1; hint4T = 0; save('ohje4', hint4); }
}
function drawHUD(w) {
  const h = w.hero, top = SAFE_T + 22;
  shadowText('↑ ' + Math.round(h.y) + ' m', W - SAFE_R - 14, top, 16, '#e8f4ff', 'right', 800);
  drawGoal(w, top);
  if (hintT < 16) drawHints();
  else if (hint3T < 9) drawHints3();
  else if (HINT4[w.kind] && !hint4[w.kind] && !w.got) HINT4[w.kind].forEach((t, i) => shadowText(t, W / 2, H * 0.3 + i * 20, 15, '#fff', 'center', 700));
  drawAim(h);
  drawControls(h);
}
// The mission: where to go, how far, an arrow toward it as the camera looks, the count done.
function drawGoal(w, top) {
  const b = CITY[w.goal], h = w.hero;
  shadowText('✔ ' + w.done, LAND ? SAFE_L + 120 : W / 2 - 70, top, 16, '#9ff7c9', 'center', 900);
  shadowText(fmt(w.gt), LAND ? SAFE_L + 190 : W / 2 + 20, top, 18, '#fff', 'center', 900);
  // Where to: the marked roof, or the nearest crook not caught yet (v4, #561).
  let t = null, say = '';
  if (isCrook(w.kind)) {
    const left = w.crooks.filter(k => !k.caught);
    const k = left.reduce((p, q) => !p || Math.hypot(q.x - h.x, q.z - h.z) < Math.hypot(p.x - h.x, p.z - h.z) ? q : p, null);
    if (k) t = { x: k.x, y: k.y, z: k.z };
    say = w.kind === 'rosvot' ? 'Ota rosvot kiinni! ' + (w.crooks.length - left.length) + '/' + w.crooks.length + ' · '
      : w.kind === 'auto' ? 'Pysäytä karkuriauto! ' : 'Pysäytä karkurihelikopteri! ';
  } else if (b) { t = roofTop(b); say = b.tower ? 'Tornin huipulle! ' : 'Mene merkitylle katolle! '; }
  if (t) {
    const dx = t.x - h.x, dz = t.z - h.z, d = Math.round(Math.hypot(dx, dz));
    const y = LAND ? top + 26 : top + 66;   // upright, under ⏸ Valikko
    const up = Math.round(t.y - h.y);   // close by: how far up (or down, after a swing over it)
    shadowText(say + (d > 15 ? d + ' m' : (up < 0 ? '↓ ' + -up : '↑ ' + up) + ' m'), W / 2, y, 15, '#fff', 'center', 800);
    if (d > 15) drawArrow(W / 2, y + 32, angDiff(cam.yaw, Math.atan2(dx, dz)));
  }
  if (w.got) {
    cx.globalAlpha = Math.min(1, w.got.show * 2);
    const big = { rosvot: 'Rosvot kiinni!', auto: 'Karkuriauto pysäytetty!', heli: 'Helikopteri pysäytetty!' }[w.got.kind];
    shadowText(big || (w.got.tower ? 'Tornin huipulla!' : 'Perillä!'), W / 2, H * 0.36, big ? 26 : 30, '#ffd166', 'center', 900);
    shadowText(fmt(w.got.t) + ' · uusi tehtävä', W / 2, H * 0.36 + 30, 15, '#fff', 'center', 800);
    cx.globalAlpha = 1;
  }
}
function drawHints() {
  const lines = hintT < 8 ? ['Juokse seinää päin: tartut siihen', 'Tikku ylös: kiipeä'] : ['Pidä Seitti pohjassa: heilu', 'Päästä irti heilahduksen huipulla'];
  shadowText(lines[0], W / 2, H * 0.3, 15, '#fff', 'center', 700);
  shadowText(lines[1], W / 2, H * 0.3 + 20, 15, '#fff', 'center', 700);
}
function drawHints3() {
  const lines = ['Pidä Veto pohjassa ja tähtää liu\'uttamalla', 'Päästä irti: seitti vetää sinut seinään', 'Seitistä irti: hyppy ja voltti'];
  lines.forEach((t, i) => shadowText(t, W / 2, H * 0.3 + i * 20, 15, '#fff', 'center', 700));
}
// While Veto is held: a crosshair where the web would go, green on a wall or roof in reach,
// grey when it would miss. A missed shot draws a short web flying out.
function drawAim(h) {
  if (missFx && window.L3D && L3D.project) {
    const a = L3D.project(h.x, h.y + 1.4, h.z), b = L3D.project(missFx.x, missFx.y, missFx.z);
    if (a && b) {
      cx.globalAlpha = Math.min(1, missFx.t * 4); cx.strokeStyle = '#fff'; cx.lineWidth = 2;
      cx.beginPath(); cx.moveTo(a[0], a[1]); cx.lineTo(b[0], b[1]); cx.stroke(); cx.globalAlpha = 1;
    }
  }
  if (catchFx && window.L3D && L3D.project) {   // the web flying to a caught crook
    const k = catchFx.k, a = L3D.project(h.x, h.y + 1.4, h.z), b = L3D.project(k.x, k.y + CROOK_MID[k.type], k.z);
    if (a && b) {
      cx.globalAlpha = Math.min(1, catchFx.t * 4); cx.strokeStyle = '#fff'; cx.lineWidth = 2.5;
      cx.beginPath(); cx.moveTo(a[0], a[1]); cx.lineTo(b[0], b[1]); cx.stroke(); cx.globalAlpha = 1;
    }
  }
  if (!pullPtr || !window.L3D || !L3D.project) return;
  // A crook in the aim: the ring turns red on him (v4, #561).
  const crook = world && aimCrook(h, cam.yaw, cam.pitch, world.crooks);
  const hit = crook ? null : aimPull(h, cam.yaw, cam.pitch), r = aimRay(h, cam.yaw, cam.pitch);
  const p = crook ? L3D.project(crook.x, crook.y + CROOK_MID[crook.type], crook.z)
    : hit ? L3D.project(hit.x, hit.y, hit.z) : L3D.project(r.ox + r.dx * PULL_MAX, r.oy + r.dy * PULL_MAX, r.oz + r.dz * PULL_MAX);
  const [x, y] = p || [W / 2, H / 2];
  const col = crook ? '#ff4d4d' : hit ? '#5dff9a' : 'rgba(200,210,220,.85)';
  cx.strokeStyle = 'rgba(10,20,40,.55)'; cx.lineWidth = 6;
  cx.beginPath(); cx.arc(x, y, 16, 0, TAU); cx.stroke();
  cx.strokeStyle = col; cx.lineWidth = 3;
  cx.beginPath(); cx.arc(x, y, 16, 0, TAU); cx.stroke();
  cx.beginPath(); cx.moveTo(x - 26, y); cx.lineTo(x - 8, y); cx.moveTo(x + 8, y); cx.lineTo(x + 26, y);
  cx.moveTo(x, y - 26); cx.lineTo(x, y - 8); cx.moveTo(x, y + 8); cx.lineTo(x, y + 26); cx.stroke();
}
function drawControls(h) {
  if (stick) {
    cx.strokeStyle = 'rgba(255,255,255,.45)'; cx.lineWidth = 3;
    cx.beginPath(); cx.arc(stick.x0, stick.y0, STICK, 0, TAU); cx.stroke();
    const [ix, iy] = stickInput();
    cx.fillStyle = 'rgba(255,255,255,.6)'; cx.beginPath(); cx.arc(stick.x0 + ix * STICK, stick.y0 + iy * STICK, 20, 0, TAU); cx.fill();
  }
  const b = buttons();
  const canWeb = (!!aimNow && !(h.webCd > 0)) || h.st === 'swing';   // the sky holds a web, except high over the roofs; not in the second after a jump off it
  cx.fillStyle = webPtr !== null ? 'rgba(255,255,255,.95)' : canWeb ? 'rgba(30,170,160,.88)' : 'rgba(60,80,90,.55)';
  cx.beginPath(); cx.arc(b.web.x, b.web.y, b.web.r, 0, TAU); cx.fill();
  cx.strokeStyle = 'rgba(255,255,255,.75)'; cx.lineWidth = 3; cx.stroke();
  shadowText('Seitti', b.web.x, b.web.y, 17, webPtr !== null ? '#0b4a46' : '#fff', 'center', 900);
  cx.fillStyle = jumpFlash > 0 ? 'rgba(255,255,255,.95)' : 'rgba(255,140,60,.85)';
  cx.beginPath(); cx.arc(b.jump.x, b.jump.y, b.jump.r, 0, TAU); cx.fill(); cx.stroke();
  shadowText('Hyppy', b.jump.x, b.jump.y, 15, '#fff', 'center', 900);
  cx.fillStyle = pullPtr ? 'rgba(255,255,255,.95)' : 'rgba(150,90,230,.85)';
  cx.beginPath(); cx.arc(b.pull.x, b.pull.y, b.pull.r, 0, TAU); cx.fill(); cx.stroke();
  shadowText('Veto', b.pull.x, b.pull.y, 15, pullPtr ? '#3b1a6e' : '#fff', 'center', 900);
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
  if (net.me) { if (hintT < 16) drawHints(); else if (hint3T < 9) drawHints3(); drawAim(w.hero); drawControls(w.hero); }
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
    stepHint3(dt);
    stepHint4(world, dt);
  }
  if (missFx) { missFx.t -= dt; if (missFx.t <= 0) missFx = null; }
  if (catchFx) { catchFx.t -= dt; if (catchFx.t <= 0) catchFx = null; }
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
  if (stepRound(w, dt)) { save('tehtavat', w.done); saveRound(); sfx('valinta', { vol: 0.35, rate: 1.2 }); hint4T = 0; }
  if (h.st === 'swing' && st0 !== 'swing') sfx('suhahdus', { vol: 0.25, rate: 1.3 });
  if (st0 === 'pull' && h.st === 'wall') sfx('tomahdys', { vol: 0.12, rate: 1.3 });
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
    s = { w: world, hero: h, heroes, cam, playing: playing(), aiming: !!pullPtr };
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
