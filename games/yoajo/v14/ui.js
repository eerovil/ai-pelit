// Yöajo: the screens over the 3D view (menu, the dashboard while driving, the end of a leg), the
// buttons, the sounds and the main loop.

const c = document.getElementById('c'), x = c.getContext('2d');
let W = 360, H = 640, DPR = 1, SAFE_T = 0, SAFE_B = 0, SAFE_L = 0, SAFE_R = 0, LAND = false;
function resize() {
  DPR = Math.min(window.devicePixelRatio || 1, 2);
  const r = c.getBoundingClientRect();
  W = r.width || innerWidth; H = r.height || innerHeight;
  c.width = W * DPR; c.height = H * DPR;
  const cs = getComputedStyle(document.getElementById('safe'));
  SAFE_T = parseFloat(cs.paddingTop) || 0; SAFE_B = parseFloat(cs.paddingBottom) || 0;
  SAFE_L = parseFloat(cs.paddingLeft) || 0; SAFE_R = parseFloat(cs.paddingRight) || 0;
  // Sideways the road shows wider, the buttons go to the thumbs and the menu into two columns.
  // Only the drawing changes: turning the phone mid-leg keeps the leg.
  LAND = W > H;
}
addEventListener('resize', resize); resize();
if (window.visualViewport) visualViewport.addEventListener('resize', resize);
if (window.ResizeObserver) new ResizeObserver(resize).observe(c);
// v2: going full screen (back.js asks on the first tap) changes the screen without always
// telling the page; size again then, and whenever the canvas box no longer matches.
document.addEventListener('fullscreenchange', resize);
function fitCheck() { const r = c.getBoundingClientRect(); if (Math.abs(r.width - W) > 0.5 || Math.abs(r.height - H) > 0.5) resize(); }
function at(e) { const r = c.getBoundingClientRect(); return [(e.clientX - r.left) * W / (r.width || W), (e.clientY - r.top) * H / (r.height || H)]; }

// ---- Buttons ----
// Drawn and hit-tested from the same list, rebuilt every frame for the screen as it is now.
let btns = [];
function button(id, x0, y0, w, h, label, o) { const b = Object.assign({ id, x: x0, y: y0, w, h, label }, o); btns.push(b); return b; }
const inside = (b, px, py) => px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h;
const pressed = new Map(); // pointer id -> the menu button it went down on (acts on lifting)

// v3 (#181 feedback): one thumb a side. The left thumb steers by sliding sideways from where it
// landed, the right one is the gas: where it lands is a light press, up is more, down past where it
// landed brakes. They work wherever the thumb lands below the top line; only the lights button
// in the middle (and pause) are buttons.
const thumbs = new Map();   // pointer id -> { kind: 'steer' | 'gas', x0, y0, x, y }
const slide = () => Math.max(60, Math.min(110, (LAND ? H : W) * 0.26));
const STICK = 56;   // v4: the one-thumb stick's radius, as Areena's (50) give or take
// v4 (#181): one thumb does it all ('yksi', the default): sideways steers, up is gas, down
// brakes, from wherever it lands. v3's two thumbs ('kaksi') stay as a choice on the menu. Saved.
let controls = load('ohjaus', 'yksi') === 'kaksi' ? 'kaksi' : 'yksi';
function setControls(c2) { controls = c2; save('ohjaus', c2); thumbs.clear(); setThumbs(); }
function driveButtons() {
  const w = 86, h = 64;
  // With one thumb in the middle, the lights sit in the lower left corner, out of its way (v8,
  // #306 "Valonappula vasemmalle puolelle"; v4–v7: lower right). Two thumbs keep them between.
  if (controls === 'yksi') button('lights', SAFE_L + 14, H - SAFE_B - 14 - h, w, h, '');
  else button('lights', W / 2 - w / 2, H - SAFE_B - 14 - h, w, h, '');
  button('pause', W - SAFE_R - 52, SAFE_T + 10, 42, 42, 'II');
}
// The amounts the thumbs ask for, from how far each has slid.
function setThumbs() {
  let steer = 0, gas = 0, brake = 0;
  const R = slide();
  for (const t of thumbs.values()) {
    // The one-thumb stick reads its knob, kept inside the circle.
    let dx = t.x - t.x0, dy = t.y - t.y0;
    const r = t.kind === 'one' ? STICK : R;
    if (t.kind === 'one') { const n = Math.hypot(dx, dy); if (n > r) { dx *= r / n; dy *= r / n; } }
    if (t.kind === 'steer' || t.kind === 'one') {
      // A small slide is a gentle turn: the turn grows faster than the slide.
      const d = clamp(dx / r, -1, 1);
      steer = Math.sign(d) * Math.pow(Math.abs(d), 1.4);
    }
    if (t.kind === 'gas' || t.kind === 'one') {
      const u = clamp(-dy / r, -1, 1);
      if (u >= 0) gas = 0.35 + 0.65 * u;
      else if (u > -0.2) gas = 0.35 * (1 + u / 0.2);
      else brake = (-u - 0.2) / 0.8;
    }
  }
  input.steer = steer; input.gas = gas; input.brake = brake;
}
// v5: no thumb starts on the speedometer (#206).
const thumbTop = () => { const sp = speedoBox(); return sp.cy + sp.r + 8; };
c.addEventListener('pointerdown', e => {
  e.preventDefault(); unlock();
  const [px, py] = at(e), b = btns.find(b => inside(b, px, py));
  if (b) {
    if (b.id === 'lights') toggleLights();
    else pressed.set(e.pointerId, b);
    return;
  }
  if (mode !== 'drive' || py < thumbTop()) return;
  const kind = controls === 'yksi' ? 'one' : px < W / 2 ? 'steer' : 'gas';
  // One thumb a side: a second finger on the same side takes over from the first.
  for (const [id, t] of thumbs) if (t.kind === kind) thumbs.delete(id);
  thumbs.set(e.pointerId, { kind, x0: px, y0: py, x: px, y: py });
  setThumbs();
  try { c.setPointerCapture(e.pointerId); } catch (_) {}
});
c.addEventListener('pointermove', e => {
  const t = thumbs.get(e.pointerId);
  if (!t) return;
  [t.x, t.y] = at(e);
  setThumbs();
});
function lift(e, cancel) {
  if (thumbs.delete(e.pointerId)) setThumbs();
  const b = pressed.get(e.pointerId); pressed.delete(e.pointerId);
  if (!b || cancel) return;
  const [px, py] = at(e);
  if (inside(b, px, py)) act(b);
}
c.addEventListener('pointerup', e => lift(e));
c.addEventListener('pointercancel', e => lift(e, true));

let sel = level;   // the leg picked on the menu
function act(b) {
  clickSound();
  if (b.id === 'pause' && mode === 'drive') { mode = 'pause'; return; }
  if (b.id === 'jatka') { mode = 'drive'; return; }
  if (b.id === 'aja') { newLeg(sel); return; }
  if (b.id === 'ohjaus') { setControls(controls === 'yksi' ? 'kaksi' : 'yksi'); return; }
  if (b.id === 'uudelleen') { newLeg(level); return; }
  if (b.id === 'seuraava') { sel = Math.min(maxLeg, level + 1); newLeg(sel); return; }
  if (b.id === 'valikko') { sel = level; preview(sel); return; }
  if (b.id.startsWith('osa-')) { const n = +b.id.slice(4); if (n <= maxLeg) { sel = n; preview(n); } }
}
// The menu shows the picked leg's road behind it, the car waiting at the start.
function preview(n) { newLeg(n); mode = 'menu'; P.v = 0; }

// ---- Sound ----
// v6 (#235): recorded sounds from the shared library (lib/aanet-2/, #205): the engine and the
// rain as loops, a click for the lights and the menu, a thud for a pothole, the shutter and a buzz
// for a fine, the horn of a dazzled driver, a whoosh as a truck goes by, screeching tyres, a crash
// and glass, and the tune at the end of a leg. Each falls back to v5's beep while its file is not
// there (the first open offline). Sound starts with the first tap (aanet.js listens for it).
const S = AiPelitAanet;
S.load(['moottori', 'sade', 'naksu', 'tomahdys', 'kamera', 'virhe', 'torvi', 'suhahdus', 'kitka', 'kolari', 'lasi', 'voitto', 'kello']);
let ac = null, engine = null, rain = null;
function unlock() {
  if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} }
  if (ac && ac.state === 'suspended') ac.resume();
  // The engine and the rain run from the first tap on, silent while not driving.
  if (!engine) engine = S.loop('moottori', { vol: 0 });
  if (!rain) rain = S.loop('sade', { vol: 0 });
}
function tone(freq, dur, type, vol, slide) {
  if (!ac) return;
  const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
  o.type = type || 'square'; o.frequency.setValueAtTime(freq, t); if (slide) o.frequency.exponentialRampToValueAtTime(slide, t + dur);
  g.gain.setValueAtTime(vol || 0.08, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + dur + 0.02);
}
function noise(dur, vol, freq) {
  if (!ac) return;
  const n = Math.floor(ac.sampleRate * dur), buf = ac.createBuffer(1, n, ac.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
  const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
  s.buffer = buf; f.type = 'lowpass'; f.frequency.value = freq || 900; g.gain.value = vol || 0.3;
  s.connect(f); f.connect(g); g.connect(ac.destination); s.start();
}
function clickSound() { S.play('naksu', { vol: 0.6 }) || tone(900, 0.05, 'square', 0.04); }
// A fine at a speed camera: the shutter with the flash, then the buzz of the fine.
function flashSound() {
  if (!S.play('kamera', { vol: 0.9 })) tone(2400, 0.12, 'sine', 0.07, 1200);
  S.play('virhe', { vol: 0.5, delay: 0.35 });
}
function bumpSound() { S.play('tomahdys', { vol: 0.9, rate: 0.9 + Math.random() * 0.2 }) || noise(0.18, 0.5, 220); }
// The tyres screech first, then the crash and the glass. Falling asleep ends in the ditch the
// same way; a walker who had to jump aside and a burst tyre are no crash, only the screech.
function crashSound(why) {
  // v12: stopped by the police: only the siren.
  if (/^Poliisi/.test(why || '')) return sirenSound();
  const hit = !/^(Vaaratilanne|Rengas)/.test(why || '');
  const screech = S.play('kitka', { vol: 0.7 });
  if (!hit) { if (!screech) noise(0.4, 0.4, 1600); return; }
  const d = screech ? 0.35 : 0;
  if (!S.play('kolari', { vol: 1, delay: d })) noise(0.7, 0.6, 700);
  S.play('lasi', { vol: 0.7, delay: d + 0.12 });
}
// v12 (#440): a police siren, quiet and short (the sound library has none): two tones in turn.
function sirenSound() { for (let i = 0; i < 6; i++) setTimeout(() => tone(i % 2 ? 880 : 660, 0.32, 'triangle', 0.035), i * 340); }
// A dazzled driver honks back (v5 only flashed the lights).
// v14 (#440): the level crossing's bell, quiet.
function bellSound() { S.play('kello', { vol: 0.25 }) || tone(1250, 0.1, 'triangle', 0.03); }
function honkSound() { S.play('torvi', { vol: 0.45, delay: 0.15 }) || tone(420, 0.35, 'square', 0.04); }
// A truck going by, close to the car: louder the faster they pass each other. No beep without it.
function truckSound(rel) { S.play('suhahdus', { vol: clamp(0.35 + rel / 50, 0.35, 0.9), rate: 0.7 }); }
function legDoneSound() { S.play('voitto', { vol: 0.8 }) || [523, 659, 784].forEach((f, i) => setTimeout(() => tone(f, 0.18, 'sine', 0.06), i * 120)); }
// The engine follows the speed and the gas; the rain (also the snow legs, as the issue asked) is
// on while the leg goes on, paused too, and stops when it ends.
function engineSound() {
  const drive = mode === 'drive' && P;
  if (engine) engine.set(drive ? { vol: 0.25 + 0.15 * input.gas, rate: 0.6 + P.v / 30 } : { vol: 0 });
  if (rain) {
    const wet = P && leg && leg.weather !== 'kuiva', snow = wet && leg.weather !== 'sade';
    rain.set(wet && (mode === 'drive' || mode === 'pause') ? { vol: snow ? 0.25 : 0.45, rate: snow ? 0.8 : 1 } : { vol: 0 });
  }
}
let lastPoints = 0;

// ---- Drawing helpers ----
function rr(x0, y0, w, h, r) { x.beginPath(); x.roundRect ? x.roundRect(x0, y0, w, h, r) : x.rect(x0, y0, w, h); }
function text(t, x0, y0, size, colour, align, weight) {
  x.font = `${weight || 700} ${size}px system-ui,sans-serif`; x.fillStyle = colour || '#fff'; x.textAlign = align || 'center'; x.textBaseline = 'middle';
  x.fillText(t, x0, y0);
}
function fitText(t, x0, y0, size, maxW, colour, align, weight) {
  let s = size; x.font = `${weight || 700} ${s}px system-ui,sans-serif`;
  while (s > 9 && x.measureText(t).width > maxW) { s--; x.font = `${weight || 700} ${s}px system-ui,sans-serif`; }
  text(t, x0, y0, s, colour, align, weight);
}
const mmss = t => { const m = Math.floor(t / 60), s = Math.floor(t % 60); return `${m}:${s < 10 ? '0' : ''}${s}`; };
const starText = n => '★'.repeat(n) + '☆'.repeat(3 - n);
function panel(x0, y0, w, h) { rr(x0, y0, w, h, 16); x.fillStyle = 'rgba(8,12,22,0.88)'; x.fill(); x.strokeStyle = 'rgba(160,190,255,0.25)'; x.lineWidth = 1.5; x.stroke(); }
function drawBtn(b, primary) {
  const on = b.id === 'lights' && P && P.high;
  rr(b.x, b.y, b.w, b.h, 14);
  x.fillStyle = b.locked ? 'rgba(60,66,80,0.6)' : on ? 'rgba(110,170,255,0.75)' : primary ? '#f2b630' : b.sel ? 'rgba(70,110,190,0.9)' : 'rgba(30,38,58,0.82)';
  x.fill(); x.strokeStyle = 'rgba(255,255,255,0.22)'; x.lineWidth = 1.5; x.stroke();
  if (b.draw) return b.draw(b);
  fitText(b.label, b.x + b.w / 2, b.y + b.h / 2, b.size || 18, b.w - 12, primary ? '#1a1406' : '#fff');
}

// ---- The screens ----
function draw() {
  x.setTransform(DPR, 0, 0, DPR, 0, 0);
  x.clearRect(0, 0, W, H);
  btns = [];
  if (no3d) { x.fillStyle = '#05070c'; x.fillRect(0, 0, W, H); }
  if (!P) return;
  if (mode === 'drive' || mode === 'pause' || mode === 'crash' || mode === 'done') dashboard();
  if (mode === 'menu') menu();
  else if (mode === 'pause') pauseScreen();
  else if (mode === 'crash') crashScreen();
  else if (mode === 'done') doneScreen();
  if (no3d && mode !== 'menu') text('Tämä puhelin ei osaa piirtää 3D-kuvaa.', W / 2, H * 0.45, 15, '#fff');
  const chip = document.getElementById('ai-pelit-tulokset-nappi');
  if (chip) chip.style.display = mode === 'menu' || mode === 'done' ? '' : 'none';
}

function dashboard() {
  // Oncoming high beams dazzle: a glare where their lights are.
  for (const t of things) {
    if (!(t.v < 0 && t.high && !t.arm && t.s > P.s + 5 && t.s - P.s < 260)) continue;
    const p = screenOf(t.s - t.len / 2, t.lat, 0.8); if (!p) continue;
    const k = 1 - (t.s - P.s) / 260, r = 24 + k * k * 220, g = x.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
    g.addColorStop(0, `rgba(255,250,235,${0.15 + k * 0.55})`); g.addColorStop(1, 'rgba(255,250,235,0)');
    x.fillStyle = g; x.fillRect(p.x - r, p.y - r, r * 2, r * 2);
  }
  if (whiteout > 0) { x.fillStyle = `rgba(225,232,240,${Math.min(0.92, whiteout)})`; x.fillRect(0, 0, W, H); }
  if (flash > 0) { x.fillStyle = `rgba(255,255,255,${flash * 0.75})`; x.fillRect(0, 0, W, H); }
  // v12: blue lights flashing at the screen's edges while the police stop the car.
  if (blueLights()) {
    const on = Math.sin(performance.now() / 1000 * 13) > 0, ew = Math.min(70, W * 0.16);
    // Each edge's gradient runs from the screen's edge inwards, ew wide.
    for (const [x0, edge, inner, lit] of [[0, 0, ew, on], [W - ew, W, W - ew, !on]]) {
      const g = x.createLinearGradient(edge, 0, inner, 0);
      g.addColorStop(0, `rgba(47,98,255,${lit ? 0.55 : 0.12})`); g.addColorStop(1, 'rgba(47,98,255,0)');
      x.fillStyle = g; x.fillRect(x0, 0, ew, H);
    }
  }
  // v13 (#440): an ambulance behind: its blue lights flash in the mirror, a strip along the top.
  if (mode === 'drive' && things.some(t => t.kind === 'ambulanssi' && t.plan !== 'back' && t.s < P.s && P.s - t.s < 120)) {
    const on = Math.sin(performance.now() / 1000 * 15) > 0, g = x.createLinearGradient(0, 0, 0, 46);
    g.addColorStop(0, `rgba(47,98,255,${on ? 0.6 : 0.15})`); g.addColorStop(1, 'rgba(47,98,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, W, 46);
  }
  // Eyelids closing.
  const e = eyes();
  if (e > 0) { x.fillStyle = '#000'; x.fillRect(0, 0, W, H * 0.5 * e); x.fillRect(0, H - H * 0.5 * e, W, H * 0.5 * e); }

  // The end screens cover the rest; only the road shows under them.
  if (mode === 'crash' || mode === 'done') return;
  // Top: where to and how far along, then v5's speedometer in the middle (#206) with the time,
  // the distance and alertness on its left and the points and the limit on its right.
  const top = SAFE_T + 10, left = Math.max(SAFE_L + 92, LAND ? 100 : 92), right = W - SAFE_R - 62;
  fitText(`${leg.from} → ${leg.to}`, (left + right) / 2, top + 10, 15, right - left, '#e8eefc');
  rr(left, top + 24, right - left, 7, 4); x.fillStyle = 'rgba(255,255,255,0.18)'; x.fill();
  rr(left, top + 24, (right - left) * clamp(P.s / leg.len, 0, 1), 7, 4); x.fillStyle = '#f2b630'; x.fill();
  const lim = limitAt(P.s), kmh = Math.round(P.v * KMH), over = kmh > lim + 5;
  const sp = speedoBox();
  speedometer(sp, P.v * KMH, kmh, lim, over);
  const lx = sp.cx - sp.r - 14, rx = sp.cx + sp.r + 14, par = parTime();
  text(`${mmss(T)} / ${mmss(par)}`, lx, sp.cy - sp.r * 0.45, 14, T > par ? '#ff9a8a' : '#cfe0ff', 'right', 600);
  text(`${Math.max(0, (leg.len - P.s) / 1000).toFixed(1).replace('.', ',')} km`, lx, sp.cy - sp.r * 0.45 + 20, 13, '#9fb0cc', 'right', 600);
  if (leg.tired) {
    // Alertness: full when rested, empty when the driver falls asleep.
    const bw = 58, by = sp.cy - sp.r * 0.45 + 36;
    text('Vireys', lx - bw - 6, by + 5, 11, '#9fb0cc', 'right', 600);
    rr(lx - bw, by, bw, 9, 5); x.fillStyle = 'rgba(255,255,255,0.15)'; x.fill();
    rr(lx - bw, by, bw * (1 - P.tired), 9, 5); x.fillStyle = P.tired > 0.62 ? '#ff6a5a' : P.tired > 0.4 ? '#f2b630' : '#7fd38a'; x.fill();
  }
  text(`${points} p`, rx, sp.cy - sp.r * 0.45, 15, '#ffe08a', 'left', 800);
  const ly = sp.cy + sp.r * 0.25;
  x.beginPath(); x.arc(rx + 19, ly, 19, 0, TAU); x.fillStyle = '#d42a1e'; x.fill();
  x.beginPath(); x.arc(rx + 19, ly, 14, 0, TAU); x.fillStyle = '#fff'; x.fill();
  text(String(lim), rx + 19, ly + 1, 14, '#111', 'center', 800);
  if (mode === 'drive') driveButtons();
  // A hint at the rest area, with how far it is (v8, #306; v1–v7: only while sleepy, no distance).
  // v14: on the wrong road only "Väärä tie!" shows; the hints ahead belong to the right road.
  const bay = !P.wrong && road.bays.find(b => b.s1 > P.s && b.s0 - P.s < 300);
  if (bay && mode === 'drive') {
    const d = Math.round((bay.s0 - BAY_IN - P.s) / 10) * 10;
    fitText(P.rest > 0 ? 'Kahvitauko…' : d > 0 ? `P Levähdysalue ${d} m: oikealle ja pysähdy` : 'P Levähdysalue: oikealle ja pysähdy', W / 2, H - SAFE_B - (LAND ? 160 : 180), 15, W - 40, '#ffe08a');
  }
  // v12 (#440): the police check ahead, with how far it is, and what to do there.
  const ck = !P.wrong && road.checks.find(c => c.live && c.state !== 'done' && c.s - P.s < 320 && c.s - P.s > -8);
  if (ck && mode === 'drive' && !bay) {
    const d = Math.round((ck.s - P.s) / 10) * 10;
    fitText(ck.state === 'blow' ? 'Puhalla…' : d > 10 ? `Puhalluskoe ${d} m: pysähdy poliisin kohdalle` : 'Pysähdy poliisin kohdalle', W / 2, H - SAFE_B - (LAND ? 160 : 180), 15, W - 40, '#bcd0ff');
  }
  // v13: what to do at the road events ahead (roadHint() in tie.js).
  const rhint = mode === 'drive' && !P.wrong && !bay && !ck ? roadHint() : '';
  if (rhint) fitText(rhint, W / 2, H - SAFE_B - (LAND ? 160 : 180), 15, W - 40, '#ffd27a');
  // v14 (#440): the next turn: a blue sign with its arrow and how far; the blinker by the speedometer.
  turnPill(H - SAFE_B - (LAND ? 160 : 180) - 34);
  if (P.signal && mode === 'drive' && (performance.now() / 1000 % (BLINK_T * 2)) < BLINK_T) {
    const bx = sp.cx + P.signal * (sp.r + 2), by = sp.cy + sp.r * 0.85, d = P.signal;
    x.beginPath(); x.moveTo(bx + d * 14, by); x.lineTo(bx, by - 10); x.lineTo(bx, by + 10); x.closePath(); x.fillStyle = '#4cd964'; x.fill();
  }
  // While a police car sees the car: a small sign under the speedometer.
  if (P.seen && mode === 'drive') text('🚓 Poliisi näkee', W / 2, sp.cy + sp.r + 14, 12, '#a9c2ff', 'center', 700);
  // Messages: overtakes, fines, the lights.
  msgs.forEach((m, i) => {
    const a = clamp(2.2 - m.t, 0, 1), y0 = Math.max(H * 0.3, sp.cy + sp.r + 30) + i * 30 - m.t * 10;
    x.globalAlpha = a; fitText(m.text, W / 2, y0, 18, W - 30, m.good ? '#9ff0a8' : '#ffb0a0'); x.globalAlpha = 1;
  });
  for (const b of btns) if (mode === 'drive') {
    if (b.id === 'lights') drawBtn(b, false), lightsIcon(b);
    else if (b.id === 'pause') { rr(b.x, b.y, b.w, b.h, 12); x.fillStyle = 'rgba(30,38,58,0.7)'; x.fill(); text('II', b.x + b.w / 2, b.y + b.h / 2 + 1, 16, '#fff'); }
    else drawBtn(b, false);
  }
  if (mode === 'drive') thumbGuides();
}
// v14 (#440): the turn ahead, from SIGN_FAR metres before (turnHint() in risteys.js): a blue pill with
// an arrow, "Käänny vasemmalle 450 m"; on the wrong road a red one.
function turnPill(y) {
  if (mode !== 'drive' || typeof turnHint !== 'function') return;
  const h = turnHint(); if (!h) return;
  const label = h.wrong ? 'Väärä tie!' : h.d > 0 ? `Käänny ${h.dir > 0 ? 'oikealle' : 'vasemmalle'} ${h.d} m` : `Käänny ${h.dir > 0 ? 'oikealle' : 'vasemmalle'}: ${h.to}`;
  x.font = '700 15px system-ui,sans-serif';
  const tw = Math.min(W - 80, x.measureText(label).width), pw = tw + 58, px = (W - pw) / 2;
  rr(px, y - 15, pw, 30, 15); x.fillStyle = h.wrong ? 'rgba(170,30,24,0.92)' : 'rgba(29,85,168,0.92)'; x.fill();
  x.strokeStyle = 'rgba(255,255,255,0.85)'; x.lineWidth = 2; x.stroke();
  if (!h.wrong) {
    // The arrow: up, then bent to the turn's side.
    const ax = px + 20, d = h.dir;
    x.strokeStyle = '#fff'; x.lineWidth = 3; x.lineCap = 'round'; x.beginPath(); x.moveTo(ax, y + 9); x.lineTo(ax, y - 1); x.lineTo(ax + d * 8, y - 1); x.stroke();
    x.fillStyle = '#fff'; x.beginPath(); x.moveTo(ax + d * 14, y - 1); x.lineTo(ax + d * 7, y - 7); x.lineTo(ax + d * 7, y + 5); x.closePath(); x.fill();
  }
  fitText(label, px + (h.wrong ? pw / 2 : 36 + tw / 2), y, 15, tw, '#fff', 'center', 700);
}
// v5 (#206: "nopeusmittari yläreunaan, samannäköinen kuin auton nopeusmittari"): a round dial
// at the top middle, 0–200 km/h, ticks every 10 and numbers every 20, a red needle, the speed in
// digits in the gap at the bottom, and the band above the limit tinted red.
const SPEEDO_MAX = 200, SPEEDO_A0 = Math.PI * 0.75, SPEEDO_SWEEP = Math.PI * 1.5;
function speedoBox() {
  const r = LAND ? 44 : 52;
  return { cx: W / 2 + (SAFE_L - SAFE_R) / 2, cy: SAFE_T + 42 + r, r };
}
const needleAngle = v => SPEEDO_A0 + SPEEDO_SWEEP * clamp(v / SPEEDO_MAX, 0, 1);
function speedometer(sp, v, kmh, lim, over) {
  const { cx, cy, r } = sp;
  x.save();
  // The bezel and the face.
  const bz = x.createLinearGradient(cx, cy - r, cx, cy + r);
  bz.addColorStop(0, '#9aa3b5'); bz.addColorStop(0.5, '#3a404c'); bz.addColorStop(1, '#7c8596');
  x.beginPath(); x.arc(cx, cy, r + 3, 0, TAU); x.fillStyle = bz; x.fill();
  const face = x.createRadialGradient(cx, cy - r * 0.3, r * 0.1, cx, cy, r);
  face.addColorStop(0, '#1d2330'); face.addColorStop(1, '#06080d');
  x.beginPath(); x.arc(cx, cy, r, 0, TAU); x.fillStyle = face; x.fill();
  // Above the limit: a red band on the rim.
  x.lineWidth = r * 0.08; x.lineCap = 'butt';
  x.beginPath(); x.arc(cx, cy, r * 0.9, needleAngle(lim), needleAngle(SPEEDO_MAX)); x.strokeStyle = 'rgba(230,50,35,0.85)'; x.stroke();
  // Ticks and numbers, lit warm white as a car's at night.
  x.strokeStyle = '#f4eee0'; x.fillStyle = '#f4eee0';
  for (let k = 0; k <= SPEEDO_MAX; k += 10) {
    const a = needleAngle(k), big = k % 20 === 0, c = Math.cos(a), s = Math.sin(a);
    x.lineWidth = big ? 2 : 1;
    x.beginPath(); x.moveTo(cx + c * r * 0.94, cy + s * r * 0.94); x.lineTo(cx + c * r * (big ? 0.78 : 0.85), cy + s * r * (big ? 0.78 : 0.85)); x.stroke();
    if (big) {
      x.font = `700 ${Math.round(r * 0.155)}px system-ui,sans-serif`; x.textAlign = 'center'; x.textBaseline = 'middle';
      x.fillText(String(k), cx + c * r * 0.6, cy + s * r * 0.6);
    }
  }
  // The speed in digits in the gap at the bottom, red when over the limit.
  text(String(kmh), cx, cy + r * 0.52, Math.round(r * 0.34), over ? '#ff6a5a' : '#ffffff', 'center', 800);
  text('km/h', cx, cy + r * 0.8, Math.round(r * 0.15), '#9fb0cc', 'center', 600);
  // The needle, with a soft glow, and its cap.
  const a = needleAngle(v), c = Math.cos(a), s = Math.sin(a);
  x.shadowColor = 'rgba(255,80,40,0.8)'; x.shadowBlur = 6;
  x.beginPath();
  x.moveTo(cx + c * r * 0.86, cy + s * r * 0.86);
  x.lineTo(cx - s * r * 0.045 - c * r * 0.16, cy + c * r * 0.045 - s * r * 0.16);
  x.lineTo(cx + s * r * 0.045 - c * r * 0.16, cy - c * r * 0.045 - s * r * 0.16);
  x.closePath(); x.fillStyle = '#ff4a26'; x.fill();
  x.shadowBlur = 0;
  x.beginPath(); x.arc(cx, cy, r * 0.11, 0, TAU); x.fillStyle = '#2a303c'; x.fill();
  x.lineWidth = 1.5; x.strokeStyle = '#8c95a6'; x.stroke();
  x.restore();
}
// v3: where each thumb is and what it asks for; while a side is free, a faint hint in its corner.
function thumbGuides() {
  const R = slide(), by = H - SAFE_B - 60;
  if (controls === 'yksi') return oneThumbGuide();
  const st = [...thumbs.values()].find(t => t.kind === 'steer'), gs = [...thumbs.values()].find(t => t.kind === 'gas');
  x.lineCap = 'round';
  if (st) {
    x.strokeStyle = 'rgba(255,255,255,0.25)'; x.lineWidth = 10;
    x.beginPath(); x.moveTo(st.x0 - R, st.y0); x.lineTo(st.x0 + R, st.y0); x.stroke();
    x.strokeStyle = 'rgba(242,182,48,0.9)'; x.lineWidth = 10;
    x.beginPath(); x.moveTo(st.x0, st.y0); x.lineTo(st.x0 + input.steer * R, st.y0); x.stroke();
    x.beginPath(); x.arc(clamp(st.x, st.x0 - R, st.x0 + R), st.y0, 22, 0, TAU); x.fillStyle = 'rgba(255,255,255,0.35)'; x.fill();
  } else {
    const cx = SAFE_L + Math.min(90, W * 0.22);
    text('◀  ▶', cx, by, 24, 'rgba(255,255,255,0.4)');
    text('liu\'uta: ohjaa', cx, by + 26, 12, 'rgba(255,255,255,0.4)', 'center', 600);
  }
  if (gs) {
    x.strokeStyle = 'rgba(255,255,255,0.25)'; x.lineWidth = 10;
    x.beginPath(); x.moveTo(gs.x0, gs.y0 - R); x.lineTo(gs.x0, gs.y0 + R); x.stroke();
    x.lineWidth = 10;
    if (input.brake > 0) { x.strokeStyle = 'rgba(255,90,70,0.95)'; x.beginPath(); x.moveTo(gs.x0, gs.y0 + 0.2 * R); x.lineTo(gs.x0, gs.y0 + (0.2 + 0.8 * input.brake) * R); x.stroke(); }
    else if (input.gas > 0) { x.strokeStyle = 'rgba(120,220,130,0.95)'; x.beginPath(); x.moveTo(gs.x0, gs.y0 + 0.2 * R); x.lineTo(gs.x0, gs.y0 + 0.2 * R - input.gas * 1.2 * R); x.stroke(); }
    x.beginPath(); x.arc(gs.x0, clamp(gs.y, gs.y0 - R, gs.y0 + R), 22, 0, TAU); x.fillStyle = 'rgba(255,255,255,0.35)'; x.fill();
  } else {
    const cx = W - SAFE_R - Math.min(90, W * 0.22);
    text('▲ kaasu', cx, by - 4, 15, 'rgba(255,255,255,0.4)', 'center', 700);
    text('▼ jarru', cx, by + 22, 15, 'rgba(255,255,255,0.4)', 'center', 700);
  }
}
// v4: one thumb: a round stick as in the other games (Areena): a faint circle where the thumb
// landed and a knob that follows it, kept inside the circle. While the thumb is lifted the circle
// waits in the lower middle with a word under it. v8: right of the middle, mirrored, now that the
// lights are on the left (v5–v7: left of it).
function stickHome() { return LAND ? { x: W - SAFE_R - 110, y: H - SAFE_B - 84 } : { x: W * 0.64, y: H - SAFE_B - 92 }; }
function oneThumbGuide() {
  const R = STICK;
  const t = [...thumbs.values()].find(t => t.kind === 'one'), home = stickHome();
  const bx = t ? t.x0 : home.x, by = t ? t.y0 : home.y;
  x.fillStyle = 'rgba(255,255,255,.08)'; x.strokeStyle = 'rgba(255,255,255,.25)'; x.lineWidth = 2;
  x.beginPath(); x.arc(bx, by, R, 0, TAU); x.fill(); x.stroke();
  let kx = bx, ky = by;
  if (t) { const dx = t.x - t.x0, dy = t.y - t.y0, d = Math.hypot(dx, dy), m = Math.min(d, R); if (d > 0) { kx += dx / d * m; ky += dy / d * m; } }
  x.fillStyle = t ? 'rgba(255,255,255,.55)' : 'rgba(255,255,255,.3)'; x.beginPath(); x.arc(kx, ky, 24, 0, TAU); x.fill();
  if (!t) text('Ohjaa · kaasu ylös · jarru alas', bx, by + R + 16, 12, 'rgba(255,255,255,.5)', 'center', 600);
}
// The high-beam symbol, blue and lit while they are on (as on a real dashboard).
function lightsIcon(b) {
  const on = P.high, cx = b.x + b.w / 2, cy = b.y + b.h / 2 - 8;
  x.fillStyle = b.locked ? '#888' : on ? '#3d8bff' : 'rgba(30,38,58,1)';
  rr(b.x + 3, b.y + 3, b.w - 6, b.h - 6, 12); x.fillStyle = on ? 'rgba(40,110,255,0.85)' : 'rgba(30,38,58,0.82)'; x.fill();
  x.strokeStyle = on ? '#ffffff' : '#9fb0cc'; x.lineWidth = 2.5;
  x.beginPath(); x.moveTo(cx - 4, cy - 11); x.quadraticCurveTo(cx - 20, cy, cx - 4, cy + 11); x.closePath(); x.stroke();
  for (let i = -1; i <= 1; i++) { x.beginPath(); x.moveTo(cx + 1, cy + i * 7); x.lineTo(cx + 16, cy + i * 7); x.stroke(); }
  fitText(on ? 'PITKÄT' : 'LÄHI', cx, b.y + b.h - 14, 12, b.w - 8, on ? '#fff' : '#cfd8ea');
}

function menu() {
  x.fillStyle = 'rgba(4,6,12,0.55)'; x.fillRect(0, 0, W, H);
  const pad = 14, colW = LAND ? (W - SAFE_L - SAFE_R - 3 * pad) / 2 : W - 2 * pad, lx = SAFE_L + pad;
  const titleY = SAFE_T + (LAND ? 34 : 56);
  text('Yöajo', lx + colW / 2, titleY, LAND ? 34 : 40, '#ffe08a', 'center', 900);
  fitText('Valtatie 4 pohjoiseen, yöllä', lx + colW / 2, titleY + 32, 15, colW, '#cfe0ff', 'center', 600);
  const listX = LAND ? lx + colW + pad : lx, listY = LAND ? SAFE_T + 50 : titleY + 58, listH = LAND ? H - listY - SAFE_B - 10 : H - listY - SAFE_B - 178;
  const gapR = LAND ? 4 : 6, rowH = Math.min(48, (listH - 7 * gapR) / 8);
  LEGS.forEach((L, i) => {
    const n = i + 1, y0 = listY + i * (rowH + gapR), locked = n > maxLeg;
    const b = button(`osa-${n}`, listX, y0, colW, rowH, '', { locked, sel: n === sel });
    b.draw = () => {
      text(String(n), b.x + 18, b.y + b.h / 2, 16, locked ? '#777' : '#ffe08a', 'center', 800);
      fitText(`${L.from} → ${L.to}`, b.x + 36, b.y + b.h / 2, 15, b.w - 140, locked ? '#888' : '#fff', 'left', 650);
      text(locked ? '🔒' : starText(stars[n] || 0), b.x + b.w - 12, b.y + b.h / 2 - (bests[n] != null && !locked ? 7 : 0), 15, locked ? '#888' : '#ffd24a', 'right', 700);
      if (bests[n] != null && !locked) text(`${bests[n]} p`, b.x + b.w - 12, b.y + b.h / 2 + 10, 11, '#9fb0cc', 'right', 600);
    };
  });
  const L = LEGS[sel - 1], W0 = { kuiva: 'kuiva keli', sade: 'vesisade', lumi: 'lumisade', pyry: 'lumipyry' }[L.weather];
  const infoY = LAND ? titleY + 70 : listY + 8 * (rowH + gapR) + 10;
  // v7 (#266): a leg with bad stretches tells how to get over the potholes.
  const tips = [L.bad ? 'Kuoppamerkin jälkeen hidasta alle 50 km/h.' : 'Pitkät pois, kun joku tulee vastaan.'];
  fitText(`Osa ${sel}: ${W0}, ${(L.len / 1000).toFixed(1).replace('.', ',')} km`, lx + colW / 2, infoY, 14, colW, '#cfe0ff', 'center', 600);
  tips.forEach((t, i) => fitText(t, lx + colW / 2, infoY + 22 + i * 19, 13, colW, '#9fb0cc', 'center', 500));
  // v4: one thumb or two, saved.
  const sw = button('ohjaus', lx + colW * 0.1, infoY + 40, colW * 0.8, 36, '', { size: 14 });
  sw.draw = () => fitText(controls === 'yksi' ? 'Ohjaus: yksi peukalo  ⇄' : 'Ohjaus: kaksi peukaloa  ⇄', sw.x + sw.w / 2, sw.y + sw.h / 2, 14, sw.w - 16, '#fff', 'center', 650);
  const by = LAND ? H - SAFE_B - 84 : H - SAFE_B - 82;
  const go = button('aja', lx + colW * 0.15, by, colW * 0.7, 62, 'Aja ▶', { size: 24 });
  for (const b of btns) drawBtn(b, b === go);
}
function endButtons(list, y0) {
  const w = Math.min(300, W - 40), h = 52;
  list.forEach(([id, label], i) => button(id, (W - w) / 2, y0 + i * (h + 10), w, h, label));
  btns.forEach((b, i) => drawBtn(b, i === 0));
}
function pauseScreen() {
  x.fillStyle = 'rgba(4,6,12,0.6)'; x.fillRect(0, 0, W, H);
  text('Tauko', W / 2, H * 0.3, 30, '#fff');
  endButtons([['jatka', 'Jatka'], ['uudelleen', 'Aloita alusta'], ['valikko', 'Valikko']], H * 0.38);
}
function crashScreen() {
  const asleep = crashWhy.startsWith('Nukahdit');
  const cop = crashWhy.startsWith('Poliisi');
  const words = crashWhy.split(' '), lines = []; let line = '';
  for (const wd of words) { if ((line + ' ' + wd).length > 32) { lines.push(line.trim()); line = ''; } line += ' ' + wd; }
  lines.push(line.trim());
  const hints = asleep ? ['Pysähdy levähdysalueelle kahville.']
    : cop && crashWhy.includes('puhallus') ? ['Pysähdy puhalluskokeessa poliisin kohdalle.']
    : cop && crashWhy.includes('käännös') ? ['Vasemmalle kääntyessä anna tietä', 'vastaantulijalle.']
    : cop ? ['Poliisin nähden enintään 10 km/h yli', 'ja vain turvallisia ohituksia.']
    // v14 (#440): the turns and the level crossing.
    : crashWhy.startsWith('Väärä tie') ? ['Käänny opasteen nuolen suuntaan:', 'hidasta ja ohjaa ajoissa.']
    : crashWhy.includes('liian lujaa') ? ['Hidasta risteykseen alle 40 km/h', 'ja rampille alle 60 km/h.']
    : crashWhy.includes('puomi') ? ['Tasoristeyksessä odota,', 'kunnes puomit nousevat.']
    : crashWhy.startsWith('Rengas') ? ['Kuoppien kohdalla hidasta alle 50 km/h.']
    : crashWhy.includes('tietyö') ? ['Tietyössä aja vasenta kaistaa vihreällä.']
    : crashWhy.includes('erikoiskuljetu') ? ['Erikoiskuljetusta väistä reunaan,', 'alle 50 km/h.']
    : [];
  // v13: tall enough for the reason and the hint above the buttons (v12: a fixed 270 px, where a
  // two-line reason and a two-line hint ran under "Yritä uudelleen").
  const textH = 74 + (lines.length - 1) * 21 + (hints.length ? 8 + hints.length * 18 : 0);
  const w = Math.min(340, W - 24), h = LAND ? H - 30 : Math.max(270, textH + 150), x0 = (W - w) / 2, y0 = LAND ? 15 : Math.min(H * 0.22, H - h - 10);
  panel(x0, y0, w, h);
  text(asleep ? 'Nukahdit!' : cop ? 'Poliisi pysäytti!' : crashWhy.startsWith('Vaara') ? 'Vaaratilanne!' : crashWhy.startsWith('Väärä tie') ? 'Väärä tie!' : crashWhy.startsWith('Rengas') ? 'Rengas rikki!' : 'Kolari!', W / 2, y0 + 36, 28, '#ff8a7a', 'center', 900);
  let ly = y0 + 74;
  lines.forEach((l, i) => text(l, W / 2, ly + i * 21, 15, '#e8eefc', 'center', 600));
  ly += (lines.length - 1) * 21;
  hints.forEach((l, i) => text(l, W / 2, ly + 26 + i * 18, 13, '#9fb0cc', 'center', 500));
  endButtons([['uudelleen', 'Yritä uudelleen'], ['valikko', 'Valikko']], y0 + h - 130);
}
function doneScreen() {
  const r = result, w = Math.min(LAND ? 640 : 340, W - 24), x0 = (W - w) / 2, y0 = LAND ? 10 : Math.max(SAFE_T + 50, H * 0.08), h = LAND ? H - 20 : Math.min(H - y0 - 6, 600);
  panel(x0, y0, w, h);
  const cx = LAND ? x0 + w * 0.27 : W / 2;
  fitText(`Perillä: ${leg.to}!`, cx, y0 + 30, 24, (LAND ? w / 2 : w) - 30, '#ffe08a', 'center', 900);
  text(starText(r.stars), cx, y0 + 66, 32, '#ffd24a', 'center', 700);
  const rows = [
    ['Aika', `${mmss(r.time)} (tavoite ${mmss(r.par)})`],
    ['Ohitukset', String(tally.ohitukset)],
    ['Lähivaloille ajoissa', String(tally.valot)],
    ['Häikäisyt', String(tally.haikaisyt)],
    ['Sakot', String(tally.sakot)],
    ['Hurjastelu', String(tally.hurjastelu)],
    ['Pitkillä ajettu', `${(tally.pitkat / 1000).toFixed(1).replace('.', ',')} km (+${tally.pitkatP})`],
    ['Aikabonus', `+${r.bonus}`],
  ];
  if (leg.tired) rows.splice(6, 0, ['Kahvitauot', String(tally.tauko)]);
  const tx0 = LAND ? x0 + 16 : x0 + 22, tx1 = LAND ? x0 + w / 2 - 10 : x0 + w - 22, ty = LAND ? y0 + 96 : y0 + 104;
  const rh = LAND ? Math.min(24, (H - 120 - (ty - y0)) / rows.length) : Math.min(24, (H - ty - 266) / rows.length);
  rows.forEach(([a, b], i) => { text(a, tx0, ty + i * rh, 14, '#cfd8ea', 'left', 500); text(b, tx1, ty + i * rh, 14, '#fff', 'right', 700); });
  const py = ty + rows.length * rh + 14;
  text(`${points} p`, cx, py, 28, '#ffffff', 'center', 900);
  text(r.record ? 'Uusi ennätys!' : `Ennätys ${r.best} p`, cx, py + 28, 14, r.record ? '#9ff0a8' : '#9fb0cc', 'center', 700);
  const hint = r.stars < 2 ? 'Aja tavoiteajassa saadaksesi toisen tähden.' : r.stars < 3 && tally.tukit ? 'Kolmas tähti: päästä ambulanssi heti ohi.' : r.stars < 3 ? 'Kolmas tähti: ei sakkoja, hurjastelua, häikäisyjä eikä liian läheisiä ohituksia.' : 'Täydellinen yöajo!';
  const list = [];
  if (level < LEGS.length) list.push(['seuraava', `Seuraava: ${LEGS[level].from} → ${LEGS[level].to}`]);
  else list.push(['valikko', 'Perillä Rovaniemellä! Valikkoon']);
  list.push(['uudelleen', 'Aja uudelleen']);
  if (level < LEGS.length) list.push(['valikko', 'Valikko']);
  if (LAND) {
    const bx = x0 + w / 2 + 10, bw = w / 2 - 26;
    fitText(hint, bx + bw / 2, y0 + 40, 13, bw, '#cfe0ff', 'center', 500);
    list.forEach(([id, label], i) => button(id, bx, y0 + 70 + i * 62, bw, 52, label));
    btns.forEach((b, i) => drawBtn(b, i === 0));
  } else {
    fitText(hint, W / 2, py + 54, 12, w - 24, '#cfe0ff', 'center', 500);
    endButtons(list, py + 76);
  }
}

// ---- The main loop ----
let HOLD = false, last = 0, acc = 0;
function frame(now) {
  fitCheck();
  const ms = last ? now - last : 16; last = now;
  if (!HOLD) {
    acc = Math.min(acc + ms / 1000, 0.1);
    while (acc >= 1 / 60) { step(1 / 60); acc -= 1 / 60; }
  }
  if (mode === 'drive' && points !== lastPoints) lastPoints = points;
  try { draw3d(now); } catch (e) { if (!no3d) console.error(e); }
  draw();
  engineSound();
  tune(ms);
  requestAnimationFrame(frame);
}
document.addEventListener('visibilitychange', () => { if (document.hidden && mode === 'drive') mode = 'pause'; });
preview(level);
requestAnimationFrame(frame);
