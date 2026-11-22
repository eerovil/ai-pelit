'use strict';
// Lentokone v2 (#547; v1 #533): the screen, the thumbs, the menus, the saves and the sounds, and the main loop.
// v2 adds the passenger jet (picked in the menu) with its passengers boarding and leaving (passengers.js).

const c = document.getElementById('c'), cx = c.getContext('2d');
const $ = id => document.getElementById(id);
let W = 360, H = 640, DPR = 1, SAFE_T = 0, SAFE_B = 0, SAFE_L = 0, SAFE_R = 0, LAND = false;
function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, 2);
  const r = c.getBoundingClientRect();
  W = r.width || innerWidth; H = r.height || innerHeight;
  c.width = Math.round(W * DPR); c.height = Math.round(H * DPR);
  const cs = getComputedStyle($('safe'));
  SAFE_T = parseFloat(cs.paddingTop) || 0; SAFE_B = parseFloat(cs.paddingBottom) || 0;
  SAFE_L = parseFloat(cs.paddingLeft) || 0; SAFE_R = parseFloat(cs.paddingRight) || 0;
  LAND = W > H;
  document.body.classList.toggle('land', LAND);
  layout();
  wake();
}
addEventListener('resize', resize);
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);
document.addEventListener('fullscreenchange', resize);

// ---- Saves (ai-pelit:lentokone:*, shared by every version) ----
const KEY = 'ai-pelit:lentokone:';
function load(k, d) { try { const v = localStorage.getItem(KEY + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v) { try { localStorage.setItem(KEY + k, JSON.stringify(v)); } catch (e) {} }
function drop(k) { try { localStorage.removeItem(KEY + k); } catch (e) {} }
let open = clamp(Math.floor(load('auki', 1)) || 1, 1, ROUTES.length);   // routes opened
let rN = clamp(Math.floor(load('reitti', 1)) || 1, 1, open);              // the route picked, 1-based
let stars = load('tahdet', []); if (!Array.isArray(stars)) stars = [];
const best = n => Math.max(0, Math.floor(load('ennatys-' + n, 0)) || 0);
let tutorial = !load('osattu', false);
camView = load('kamera', 'chase') === 'cockpit' ? 'cockpit' : 'chase';
let plane = load('kone', 'iso') === 'pieni' ? 'pieni' : 'iso';   // 'iso' the passenger jet (new in v2), 'pieni' v1's plane
let stickStyle = load('sauva', 'lentaja') === 'suora' ? 'suora' : 'lentaja';   // 'lentaja': finger down lifts the nose

// ---- Sounds (#205, aanet-5): only after the first tap, quiet (#337, #355) ----
const S = window.AiPelitAanet;
if (S) S.load(['moottori', 'tuuli', 'rullaus', 'halytys', 'lasku', 'kolari', 'onnistui', 'valinta', 'naksu', 'metalli', 'virhe', 'askel', 'askel2']);
let ac = null;
function beep(f, d, vol) {
  try {
    ac = ac || new (window.AudioContext || window.webkitAudioContext)();
    const o = ac.createOscillator(), g = ac.createGain();
    o.frequency.value = f; g.gain.value = vol || 0.04; g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + d);
    o.connect(g); g.connect(ac.destination); o.start(); o.stop(ac.currentTime + d);
  } catch (e) {}
}
const sfx = (name, opts, f) => (S && S.play(name, opts)) || (f && beep(f, 0.12, 0.04));
let engine = null, windL = null, wheels = null, stallT = 0;
function sounds(dt) {
  if (!S) return;
  const on = mode === 'fly' && p && !(p.over && !p.over.ok);
  if (on && !engine) { engine = S.loop('moottori', { vol: 0 }); windL = S.loop('tuuli', { vol: 0 }); wheels = S.loop('rullaus', { vol: 0 }); }
  if (!on && engine) { engine.stop(); windL.stop(); wheels.stop(); engine = windL = wheels = null; }
  if (!engine) return;
  // The jet: a deeper engine and more rushing air.
  const big = p.kind === 'iso';
  engine.set(big ? { vol: 0.07 + p.thr * 0.12, rate: 0.35 + p.thr * 0.4 } : { vol: 0.08 + p.thr * 0.14, rate: 0.55 + p.thr * 0.7 });
  const v = clamp(p.v / (big ? 90 : 60), 0, 1);
  windL.set({ vol: (p.ground ? v * 0.05 : 0.03 + v * 0.12) + (big ? p.thr * 0.06 : 0), rate: 0.8 + v * 0.4 });
  wheels.set({ vol: p.ground && p.v > 1 ? 0.04 + v * 0.16 : 0, rate: 0.7 + v * 0.6 });
  stallT -= dt;
  if (p.stall && stallT <= 0) { sfx('halytys', { vol: 0.12 }, 900); stallT = 1.1; }
}
function events() {
  for (const e of p.events) {
    if (e === 'touch') sfx('lasku', { vol: 0.35, rate: 0.7 }, 160);
    else if (e === 'crash') sfx('kolari', { vol: 0.35 }, 120);
    else if (e === 'landed') sfx('onnistui', { vol: 0.3 }, 880);
    else if (e === 'wrong') sfx('virhe', { vol: 0.2 }, 200);
  }
  p.events.length = 0;
}

// ---- The flight ----
// Modes: 'menu', 'board' (the jet's passengers walk in), 'fly', 'pause', 'deplane' (they walk out), 'end'.
let mode = 'menu', p = null, route = ROUTES[rN - 1], endT = 0, saveT = 0, result = null;
let paxT = 0, pax = null, stepT = 0, stepN = 0;   // the passengers' scene and its clock (#547)
// The menu's picture: the plane on the first route's runway.
p = newPlane(route, plane);
function startFlight(fromApproach) {
  // Flying the same route again in the jet after a crash or a restart: the passengers are still aboard.
  const aboard = mode !== 'menu' && p && p.kind === 'iso' && plane === 'iso' && route === ROUTES[rN - 1] && !(p.over && p.over.ok);
  route = ROUTES[rN - 1];
  p = fromApproach ? approachPlane(route, plane) : newPlane(route, plane);
  // A practice landing is scored on screen only: no list, record or new route without a take-off.
  p.practice = !!fromApproach;
  if (p.kind === 'iso' && !fromApproach && !aboard) beginBoarding();
  else beginFlight();
}
// The passengers walk from the bus up the stairs; a tap skips it. Nothing is saved until the flight.
function beginBoarding() {
  mode = 'board'; paxT = 0; pax = paxScene('board', 0); result = null; endT = 0;
  hideAll(); chip(false);
  wake();
}
function beginDeplaning() {
  mode = 'deplane'; paxT = 0; pax = paxScene('deplane', 0);
  p.pit = 0; p.bank = 0;   // level on its wheels, so the door meets the stairs
  wake();
}
function beginFlight(fromBoarding) {
  mode = 'fly'; endT = 0; saveT = 0; result = null; acc = 0; pax = null;
  stick.id = thrHold.id = null; for (const b of BTNS) b.down = null;
  // From the passengers' scene the chase camera glides from where it was.
  if (V3 && !fromBoarding) V3.cam = null;
  hideAll();
  chip(false);
  wake();
}
function resumeFlight() {
  const s = load('lento', null);
  if (!s || !s.p || !ROUTES[s.r - 1]) { drop('lento'); showMenu(); return; }
  rN = s.r; route = ROUTES[rN - 1];
  p = Object.assign(newPlane(route, s.p.kind || 'pieni'), s.p, { events: [], sx: 0, sy: 0, brake: false });
  beginFlight();
}
function keepFlight() {
  const q = Object.assign({}, p); delete q.events;
  save('lento', { r: rN, p: q });
}
// The flight is over: the score, the stars, the next route, saved the moment it is earned (the end
// screen waits a moment after it, and a reload or a hidden page then must not lose the landing).
// Once per flight: `result` is set here and cleared only when a new flight begins.
function settleFlight() {
  if (result) return;
  drop('lento');
  const o = p.over;
  result = { ok: o.ok, why: o.why };
  if (o.ok && p.practice) result = Object.assign(result, o, { practice: true, was: best(rN) });
  else if (o.ok) {
    const was = best(rN);
    result = Object.assign(result, o, { record: o.points > was, was });
    if (o.points > was) save('ennatys-' + rN, o.points);
    stars[rN - 1] = Math.max(stars[rN - 1] || 0, o.stars); save('tahdet', stars);
    if (rN === open && open < ROUTES.length) { open++; save('auki', open); result.opened = ROUTES[open - 1].name; }
    if (tutorial) { tutorial = false; save('osattu', true); }
    // The first score's nickname question waits for the end screen, not over the passengers.
    if (window.AiPelitScores) { setBoard(rN); result.ask = AiPelitScores.submit(o.points, true) === true; }
  }
}
function endFlight() {
  settleFlight();
  mode = 'end'; pax = null;
  showEnd();
  if (result.ask && window.AiPelitScores) { result.ask = false; AiPelitScores.prompt(); }
}
function setBoard(n) { n = n || rN; if (window.AiPelitScores) AiPelitScores.board('reitti-' + n, ROUTES[n - 1].name); }

// ---- The thumbs ----
// The stick: a finger down on the left side; how far it is from where it touched down is the stick.
// The throttle: a slider on the right; dragging moves it from where it was. Buttons act on the lift.
const stick = { id: null, x0: 0, y0: 0, x: 0, y: 0, R: 60 };
const thrHold = { id: null, y: 0, t0: 0 };
const BTNS = [
  { id: 'gear', label: () => p.gear ? 'Telineet ⬇' : 'Telineet ⬆', act: () => { if (!p.ground) { p.gear = !p.gear; sfx('metalli', { vol: 0.15, rate: 1.4 }, 300); } } },
  { id: 'flaps', label: () => 'Laipat ' + p.flaps, act: () => { p.flaps = (p.flaps + 1) % 3; sfx('naksu', { vol: 0.3 }, 600); } },
  { id: 'brake', label: () => 'Jarru', hold: true, show: () => p.ground },
  { id: 'pause', label: () => '⏸', act: () => pause() },
];
let L = {};   // where each control sits, from layout()
function layout() {
  const b = H - SAFE_B, r = W - SAFE_R;
  const thrH = LAND ? Math.min(190, H * 0.5) : 190;
  L.thr = { x: r - 70, y: b - 30 - thrH, w: 52, h: thrH };
  L.zoneThr = { x: L.thr.x - 26, y: L.thr.y - 30, w: r - L.thr.x + 26, h: thrH + 60 };
  const bw = 104, bh = 44;
  L.gear = { x: L.thr.x - bw - 16, y: b - 30 - bh, w: bw, h: bh };
  L.flaps = { x: L.gear.x, y: L.gear.y - bh - 10, w: bw, h: bh };
  L.brake = LAND ? { x: SAFE_L + 170, y: b - 30 - bh, w: 90, h: bh } : { x: SAFE_L + 16, y: b - 30 - bh - 150, w: 90, h: bh };
  L.pause = { x: r - 52, y: SAFE_T + 10, w: 42, h: 38 };
  L.stickHome = { x: SAFE_L + 92, y: b - 104 };
  L.hudY = SAFE_T + 8;
}
const inBox = (bx, x, y) => bx && x >= bx.x && x <= bx.x + bx.w && y >= bx.y && y <= bx.y + bx.h;
function btnAt(x, y) { return BTNS.find(bt => (!bt.show || bt.show()) && inBox(L[bt.id], x, y)); }
function point(e) { const r = c.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
c.addEventListener('pointerdown', e => {
  e.preventDefault();
  if (mode === 'board' || mode === 'deplane') { skipPax(); return; }
  if (mode !== 'fly') return;
  const [x, y] = point(e);
  const bt = btnAt(x, y);
  if (p.over) return;
  if (bt) { bt.down = e.pointerId; wake(); return; }
  if (inBox(L.zoneThr, x, y) && thrHold.id === null) { thrHold.id = e.pointerId; thrHold.y = y; thrHold.t0 = p.thr; return; }
  if (x < W * 0.6 && y > SAFE_T + 60 && stick.id === null) { stick.id = e.pointerId; stick.x0 = stick.x = x; stick.y0 = stick.y = y; readStick(); }
});
c.addEventListener('pointermove', e => {
  if (mode !== 'fly') return;
  const [x, y] = point(e);
  if (e.pointerId === stick.id) { stick.x = x; stick.y = y; readStick(); }
  else if (e.pointerId === thrHold.id) p.thr = clamp(thrHold.t0 + (thrHold.y - y) / L.thr.h, 0, 1);
});
function lift(e) {
  const [x, y] = point(e);
  if (e.pointerId === stick.id) { stick.id = null; p.sx = p.sy = 0; }
  if (e.pointerId === thrHold.id) thrHold.id = null;
  for (const bt of BTNS) if (bt.down === e.pointerId) {
    bt.down = null;
    if (e.type === 'pointerup' && !bt.hold && inBox(L[bt.id], x, y) && mode === 'fly') bt.act();
  }
}
c.addEventListener('pointerup', lift);
c.addEventListener('pointercancel', lift);
function readStick() {
  const dx = stick.x - stick.x0, dy = stick.y - stick.y0, d = Math.hypot(dx, dy), k = d > stick.R ? stick.R / d : 1;
  p.sx = clamp(dx * k / stick.R, -1, 1);
  const vy = clamp(dy * k / stick.R, -1, 1);
  p.sy = stickStyle === 'lentaja' ? vy : -vy;
  // A small dead zone, so a resting thumb flies straight.
  if (Math.abs(p.sx) < 0.08) p.sx = 0;
  if (Math.abs(p.sy) < 0.08) p.sy = 0;
}
// A tap during the passengers' scene skips to its end.
function skipPax() {
  if (mode === 'board') beginFlight(true);
  else if (mode === 'deplane') endFlight();
}
function brakeHeld() { return BTNS[2].down !== null && BTNS[2].down !== undefined && p.ground; }

// ---- Pause and the page going away ----
function pause() {
  if (mode !== 'fly' || p.over) return;
  mode = 'pause'; keepFlight();
  stick.id = thrHold.id = null; p.sx = p.sy = 0;
  $('pause').hidden = false; chip(true);
  wake();
}
document.addEventListener('visibilitychange', () => { if (document.hidden && mode === 'fly' && !p.over) pause(); });

// ---- Menus ----
function hideAll() { for (const id of ['menu', 'end', 'pause']) $(id).hidden = true; }
// The 🏆 chip: shown in the menus, not over the flight's controls.
function chip(on) { const ch = document.getElementById('ai-pelit-tulokset-nappi'); if (ch) ch.style.display = on ? '' : 'none'; }
function showMenu() {
  mode = 'menu'; hideAll();
  route = ROUTES[rN - 1]; p = newPlane(route, plane);
  // The jet waits with its stairs and bus by the door.
  pax = plane === 'iso' ? paxScene('board', 0) : null;
  const box = $('routes'); box.textContent = '';
  ROUTES.forEach((r, i) => {
    const b = document.createElement('button'), n = i + 1, locked = n > open;
    b.className = 'route' + (n === rN ? ' on' : '');
    b.disabled = locked;
    const st = stars[i] || 0;
    b.innerHTML = '<span><b></b><small></small></span><em></em>';
    b.querySelector('b').textContent = n + '. ' + r.name;
    b.querySelector('small').textContent = locked ? '🔒 Laskeudu ensin: ' + ROUTES[i - 1].name : FIELDS[r.from].name + ' → ' + FIELDS[r.to].name;
    b.querySelector('em').innerHTML = locked ? '' : '★'.repeat(st) + '<i>' + '★'.repeat(3 - st) + '</i>';
    b.onclick = () => { rN = n; save('reitti', rN); setBoard(rN); sfx('valinta', { vol: 0.25 }); showMenu(); };
    box.appendChild(b);
  });
  $('routeNote').textContent = route.note;
  const s = load('lento', null);
  $('resume').hidden = !(s && s.p && ROUTES[s.r - 1]);
  if (!$('resume').hidden) $('resume').textContent = '▶ Jatka lentoa: ' + ROUTES[s.r - 1].name;
  $('plane').textContent = plane === 'iso' ? '✈ Iso kone' : '🛩 Pieni kone';
  $('view').textContent = camView === 'chase' ? '📷 Takaa' : '📷 Ohjaamosta';
  $('stickBtn').textContent = stickStyle === 'lentaja' ? '🕹 Sauva: alas = nokka ylös' : '🕹 Sauva: ylös = nokka ylös';
  $('menu').hidden = false; chip(true);
  wake();
}
function showEnd() {
  hideAll();
  const r = result;
  $('endTitle').textContent = r.ok ? 'Laskeutuminen onnistui!' : 'Lento päättyi';
  $('endStars').innerHTML = r.ok ? '★'.repeat(r.stars) + '<i>' + '★'.repeat(3 - r.stars) + '</i>' : '';
  $('endStars').hidden = !r.ok;
  const list = $('endParts'); list.textContent = '';
  const row = (a, b) => { const li = document.createElement('li'); li.innerHTML = '<span></span><b></b>'; li.firstChild.textContent = a; li.lastChild.textContent = b; list.appendChild(li); };
  if (r.ok) {
    row('Pehmeys (' + r.sink.toFixed(1).replace('.', ',') + ' m/s)', r.soft);
    row('Keskiviiva', r.line);
    row('Kosketuskohta', r.spot);
    row('Pysähtyi radalle', r.stop);
    row('Yhteensä', r.points + ' p');
  } else row(r.why, '');
  $('endNote').textContent = r.practice ? 'Harjoituslasku: ei tuloslistalle eikä avaa uutta lentoa.' : r.ok ? (r.record ? (r.was ? 'Uusi ennätys!' : 'Ensimmäinen laskeutuminen!') : 'Ennätys ' + r.was + ' p') : 'Yritä uudelleen alusta tai harjoittele pelkkä laskeutuminen.';
  $('endOpen').hidden = !r.opened; if (r.opened) $('endOpen').textContent = 'Uusi lento auki: ' + r.opened;
  $('next').hidden = !(r.ok && rN < open);
  $('again').textContent = r.ok ? 'Lennä uudelleen' : 'Alusta';
  $('approach').hidden = r.ok && !r.practice;
  $('end').hidden = false; chip(true);
  wake();
}
$('go').onclick = () => { sfx('valinta', { vol: 0.25 }); drop('lento'); startFlight(false); };
$('resume').onclick = () => resumeFlight();
$('plane').onclick = () => { plane = plane === 'iso' ? 'pieni' : 'iso'; save('kone', plane); sfx('valinta', { vol: 0.25 }); showMenu(); };
$('view').onclick = () => { camView = camView === 'chase' ? 'cockpit' : 'chase'; save('kamera', camView); showMenu(); };
$('stickBtn').onclick = () => { stickStyle = stickStyle === 'lentaja' ? 'suora' : 'lentaja'; save('sauva', stickStyle); showMenu(); };
$('next').onclick = () => { rN = Math.min(open, rN + 1); save('reitti', rN); setBoard(rN); startFlight(false); };
$('again').onclick = () => startFlight(false);
$('approach').onclick = () => startFlight(true);
$('toMenu').onclick = () => showMenu();
$('scores').onclick = () => { setBoard(rN); if (window.AiPelitScores) AiPelitScores.open(); };
$('goOn').onclick = () => { $('pause').hidden = true; beginFlight(); };
$('pRestart').onclick = () => startFlight(false);
$('pApproach').onclick = () => startFlight(true);
$('pMenu').onclick = () => { drop('lento'); showMenu(); };

// ---- The HUD, drawn on the 2D canvas over the 3D one ----
function shadowText(t, x, y, size, col, align, weight) {
  cx.font = (weight || 700) + ' ' + size + 'px system-ui,sans-serif';
  cx.textAlign = align || 'left'; cx.textBaseline = 'middle';
  cx.fillStyle = 'rgba(0,0,0,.55)'; cx.fillText(t, x + 1.5, y + 1.5);
  cx.fillStyle = col || '#fff'; cx.fillText(t, x, y);
}
function rrect(x, y, w, h, r) { cx.beginPath(); cx.roundRect ? cx.roundRect(x, y, w, h, r) : cx.rect(x, y, w, h); }
const num = (v, d) => v.toFixed(d || 0).replace('.', ',');
function drawHUD() {
  cx.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx.clearRect(0, 0, W, H);
  if (no3d) { cx.fillStyle = '#4f8fd8'; cx.fillRect(0, 0, W, H); shadowText('Tämä puhelin ei osaa piirtää 3D-kuvaa.', W / 2, H * 0.2, 15, '#fff', 'center'); }
  if (mode === 'board' || mode === 'deplane') { drawPaxHUD(); return; }
  if (mode !== 'fly' && mode !== 'pause') return;
  const g = guidance(p, route), gnd = groundAt(p.x, p.z), agl = Math.max(0, p.y - gnd);
  // Top strip: speed, height, climb; the way to go under it.
  const y0 = L.hudY, cw = Math.min(88, (W - 150) / 3), x0 = W / 2 - cw * 1.5;
  const cells = [['Nopeus', num(p.v * 3.6) + ' km/h'], ['Korkeus', num(agl) + ' m'], ['Nousu', (p.ground ? '0' : (p.v * Math.sin(p.gam) >= 0 ? '+' : '') + num(p.v * Math.sin(p.gam), 1)) + ' m/s']];
  cx.fillStyle = 'rgba(10,20,40,.45)'; rrect(x0 - 6, y0, cw * 3 + 12, 44, 12); cx.fill();
  cells.forEach(([a, b], i) => { shadowText(a, x0 + cw * (i + 0.5), y0 + 12, 11, '#cfe0ff', 'center', 600); shadowText(b, x0 + cw * (i + 0.5), y0 + 30, 16, '#fff', 'center', 800); });
  // The arrow to the approach point, or along the runway's line.
  const ay = y0 + 76, ax = W / 2;
  cx.save(); cx.translate(ax - 70, ay); cx.rotate(g.rel);
  cx.fillStyle = g.out ? '#ff6a5a' : '#ffd23a'; cx.beginPath(); cx.moveTo(0, -16); cx.lineTo(11, 10); cx.lineTo(0, 4); cx.lineTo(-11, 10); cx.closePath(); cx.fill();
  cx.restore();
  const f = FIELDS[route.to];
  const where = g.out ? 'Käänny takaisin!' : g.lined ? f.name + ' ' + num(g.runwayDist / 1000, 1) + ' km' : 'Lähestymispiste ' + num(g.dist / 1000, 1) + ' km';
  shadowText(where, ax - 50, ay, 14, g.out ? '#ff9a8a' : '#fff', 'left', 800);
  // The glide path when lined up: four dots as the lights beside the runway show it.
  const lit = g.lined ? papi(p, f) : null;
  if (lit && g.runwayDist < 4500) {
    shadowText('Liukupolku', ax - 50, ay + 24, 11, '#cfe0ff', 'left', 600);
    lit.forEach((on, i) => { cx.fillStyle = on ? '#ffffff' : '#ff3a3a'; cx.beginPath(); cx.arc(ax + 30 + i * 16, ay + 24, 6, 0, TAU); cx.fill(); });
  }
  // Warnings.
  let warn = '';
  if (p.stall) warn = 'SAKKAUS – nokka alas!';
  else if (!p.ground && g.lined && !p.gear && g.runwayDist < 2500) warn = 'Telineet alas!';
  if (warn) shadowText(warn, W / 2, H * 0.32, 22, '#ff5a4a', 'center', 900);
  if (tutorial && !warn && !p.over) { const t = hint(g, agl); if (t) shadowText(t, W / 2, H * (LAND ? 0.38 : 0.36), 15, '#fff', 'center', 700); }
  if (p.over && p.over.ok) shadowText('Laskeutunut!', W / 2, H * 0.3, 28, '#ffd84a', 'center', 900);
  else if (p.over) shadowText(p.over.why, W / 2, H * 0.3, 26, '#ff7a6a', 'center', 900);
  drawControls();
}
// The passengers' scene: who is aboard, and that a tap skips it.
function drawPaxHUD() {
  if (!pax) return;
  // On a narrow phone the banner would run under the "‹ Pelit" chip: put it below the chip.
  const on = mode === 'board', y = L.hudY + 22 + (W < 420 ? 40 : 0);
  cx.fillStyle = 'rgba(10,20,40,.45)'; rrect(W / 2 - 130, y - 18, 260, 58, 14); cx.fill();
  shadowText(on ? 'Matkustajat nousevat kyytiin' : 'Matkustajat poistuvat', W / 2, y - 2, 16, '#fff', 'center', 800);
  shadowText('🧳 ' + pax.aboard + ' / ' + PAX.n + ' koneessa', W / 2, y + 22, 15, '#ffd84a', 'center', 800);
  shadowText('Napauta: ohita', W / 2, H - SAFE_B - 34, 14, '#cfe0ff', 'center', 700);
}
// First flights: what to do next.
function hint(g, agl) {
  const up = stickStyle === 'lentaja' ? 'vedä sauvaa alas' : 'työnnä sauvaa ylös';
  const vr = kindOf(p).vr;
  if (p.ground && !p.airborne) return p.thr < 0.9 ? 'Kaasu täysille: oikea peukalo ylös' : p.v * 3.6 < vr - 5 ? 'Vauhti kasvaa… nokka ylös ' + vr + ' km/h' : vr + ' km/h: ' + up + '!';
  if (p.ground && p.touch) return 'Pidä Jarru pohjassa';
  if (agl < 80 && p.gear && !g.lined) return 'Nosta telineet';
  if (!g.lined) return 'Lennä keltaisen nuolen suuntaan';
  if (g.runwayDist > 1500) return 'Telineet alas, laipat 2, kaasu pienelle';
  if (agl < 12) return 'Loivenna juuri ennen maata';
  return 'Pidä valot: kaksi valkoista, kaksi punaista';
}
function drawControls() {
  if (mode !== 'fly') return;
  // Throttle.
  const t = L.thr;
  cx.fillStyle = 'rgba(10,20,40,.45)'; rrect(t.x, t.y, t.w, t.h, 14); cx.fill();
  cx.fillStyle = 'rgba(255,210,58,.55)'; rrect(t.x + 6, t.y + 6 + (t.h - 12) * (1 - p.thr), t.w - 12, (t.h - 12) * p.thr, 9); cx.fill();
  shadowText(Math.round(p.thr * 100) + ' %', t.x + t.w / 2, t.y - 14, 14, '#fff', 'center', 800);
  shadowText('KAASU', t.x + t.w / 2, t.y + t.h + 14, 10, '#cfe0ff', 'center', 700);
  // Buttons.
  for (const bt of BTNS) {
    if (bt.show && !bt.show()) continue;
    const b = L[bt.id], on = bt.down !== null && bt.down !== undefined;
    cx.fillStyle = on ? 'rgba(255,210,58,.6)' : 'rgba(10,20,40,.5)'; rrect(b.x, b.y, b.w, b.h, 12); cx.fill();
    shadowText(bt.label(), b.x + b.w / 2, b.y + b.h / 2, bt.id === 'pause' ? 18 : 15, '#fff', 'center', 800);
  }
  // Stick: where the thumb is, or at rest in its corner.
  const held = stick.id !== null, sx0 = held ? stick.x0 : L.stickHome.x, sy0 = held ? stick.y0 : L.stickHome.y;
  cx.strokeStyle = 'rgba(255,255,255,.4)'; cx.lineWidth = 3; cx.beginPath(); cx.arc(sx0, sy0, stick.R, 0, TAU); cx.stroke();
  const kx = sx0 + p.sx * stick.R, ky = sy0 + (stickStyle === 'lentaja' ? p.sy : -p.sy) * stick.R;
  cx.fillStyle = held ? 'rgba(255,210,58,.8)' : 'rgba(255,255,255,.35)'; cx.beginPath(); cx.arc(kx, ky, 24, 0, TAU); cx.fill();
  if (!held) shadowText('SAUVA', sx0, sy0 + stick.R + 14, 10, '#cfe0ff', 'center', 700);
}

// ---- The main loop ----
// The physics runs in fixed steps (DT), whatever the frame rate. In the menus the picture rests
// (docs/making-games.md, "A still game must not draw every frame").
let raf = 0, last = 0, still = 0, acc = 0;
function wake() { still = 0; if (!raf) { last = 0; raf = requestAnimationFrame(frame); } }
function frame(now) {
  raf = 0;
  const dt = last ? Math.min(0.1, (now - last) / 1000) : 1 / 60; last = now;
  if (mode === 'fly') {
    p.brake = brakeHeld();
    acc += dt;
    while (acc >= DT) { step(p, DT, route); acc -= DT; }
    events();
    if (g0Lost()) { p.over = { ok: false, why: 'Eksyit liian kauas', stopped: true }; }
    if (p.over) {
      settleFlight(); endT += dt;
      // The jet's passengers walk out after a landing, before the end screen.
      if (endT > (p.over.ok ? 1.8 : 2.4)) { if (p.over.ok && p.over.stop === 100 && p.kind === 'iso') beginDeplaning(); else endFlight(); }
    }
    else { saveT += dt; if (saveT > 1) { saveT = 0; keepFlight(); } }
    tune(dt * 1000);
  }
  if (mode === 'board' || mode === 'deplane') paxStep(dt);
  sounds(dt);
  const moving = mode === 'fly' || mode === 'board' || mode === 'deplane';
  render3d(p, route, dt, !moving, pax);
  drawHUD();
  if (moving || still++ < 2 || (!V3 && !no3d)) raf = requestAnimationFrame(frame);
}
function paxStep(dt) {
  paxT += dt;
  pax = paxScene(mode, paxT);
  // Quiet steps while someone walks.
  stepT -= dt;
  if (stepT <= 0 && pax.pax.some(q => q && q.leg < 2)) { stepT = 0.32; sfx(stepN++ % 2 ? 'askel2' : 'askel', { vol: 0.05, rate: 1.2 }); }
  if (pax.done) { if (mode === 'board') beginFlight(true); else endFlight(); }
}
function g0Lost() { return !p.over && guidance(p, route).lost; }
resize();
showMenu();
// scores.js loads after this file: name the list once it is there, so its 🏆 chip opens this route's.
addEventListener('DOMContentLoaded', () => { setBoard(rN); chip(mode !== 'fly'); });
