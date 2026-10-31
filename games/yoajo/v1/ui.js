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
function at(e) { const r = c.getBoundingClientRect(); return [(e.clientX - r.left) * W / (r.width || W), (e.clientY - r.top) * H / (r.height || H)]; }

// ---- Buttons ----
// Drawn and hit-tested from the same list, rebuilt every frame for the screen as it is now.
let btns = [];
function button(id, x0, y0, w, h, label, o) { const b = Object.assign({ id, x: x0, y: y0, w, h, label }, o); btns.push(b); return b; }
const inside = (b, px, py) => px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h;
const held = new Map();   // pointer id -> the drive button under it (held buttons act while held)
const pressed = new Map(); // pointer id -> the menu button it went down on (acts on lifting)

function driveButtons() {
  const gap = 8, b = H - SAFE_B - 14;
  if (LAND) {
    const s = Math.min(96, H * 0.27), y0 = b - s;
    button('left', SAFE_L + 14, y0, s, s, '◀', { hold: true });
    button('right', SAFE_L + 22 + s, y0, s, s, '▶', { hold: true });
    button('brake', W - SAFE_R - 14 - s * 1.15, y0, s * 1.15, s, 'JARRU', { hold: true });
    button('lights', W - SAFE_R - 22 - s * 2.05, y0 + s * 0.2, s * 0.9, s * 0.8, '');
  } else {
    const sw = Math.min(96, W * 0.25), h = Math.min(100, H * 0.14), y0 = b - h, mid = (W - 2 * 10 - 2 * sw - 4 * gap) / 2;
    button('left', 10, y0, sw, h, '◀', { hold: true });
    button('right', W - 10 - sw, y0, sw, h, '▶', { hold: true });
    button('brake', 10 + sw + 2 * gap, y0, mid, h, 'JARRU', { hold: true });
    button('lights', 10 + sw + 2 * gap + mid + 0, y0, mid, h, '');
  }
  button('pause', W - SAFE_R - 52, SAFE_T + 10, 42, 42, 'II');
}
function setHeld() {
  input.left = input.right = input.brake = false;
  for (const b of held.values()) if (b && b.hold) input[b.id] = true;
}
c.addEventListener('pointerdown', e => {
  e.preventDefault(); unlock();
  const [px, py] = at(e), b = btns.find(b => inside(b, px, py));
  if (!b) return;
  if (b.hold) { held.set(e.pointerId, b); setHeld(); try { c.setPointerCapture(e.pointerId); } catch (_) {} }
  else if (b.id === 'lights') { toggleLights(); }
  else pressed.set(e.pointerId, b);
});
c.addEventListener('pointermove', e => {
  if (!held.has(e.pointerId)) return;
  const [px, py] = at(e), b = btns.find(b => b.hold && inside(b, px, py));
  // A thumb slid from one steering button to the other steers the other way.
  if (b && b !== held.get(e.pointerId)) { held.set(e.pointerId, b); setHeld(); }
});
function lift(e, cancel) {
  if (held.has(e.pointerId)) { held.delete(e.pointerId); setHeld(); }
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
  if (b.id === 'uudelleen') { newLeg(level); return; }
  if (b.id === 'seuraava') { sel = Math.min(maxLeg, level + 1); newLeg(sel); return; }
  if (b.id === 'valikko') { sel = level; preview(sel); return; }
  if (b.id.startsWith('osa-')) { const n = +b.id.slice(4); if (n <= maxLeg) { sel = n; preview(n); } }
}
// The menu shows the picked leg's road behind it, the car waiting at the start.
function preview(n) { newLeg(n); mode = 'menu'; P.v = 0; }

// ---- Sound: Web Audio, only after the first tap ----
let ac = null, engine = null;
function unlock() {
  if (!ac) { try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} }
  if (ac && ac.state === 'suspended') ac.resume();
  if (ac && !engine) {
    const o = ac.createOscillator(), f = ac.createBiquadFilter(), g = ac.createGain();
    o.type = 'sawtooth'; o.frequency.value = 40; f.type = 'lowpass'; f.frequency.value = 260; g.gain.value = 0;
    o.connect(f); f.connect(g); g.connect(ac.destination); o.start();
    engine = { o, g };
  }
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
function clickSound() { tone(900, 0.05, 'square', 0.04); }
function flashSound() { tone(2400, 0.12, 'sine', 0.07, 1200); }
function bumpSound() { noise(0.18, 0.5, 220); }
function crashSound() { noise(0.7, 0.6, 700); }
function engineSound() {
  if (!engine) return;
  const on = mode === 'drive' && P, t = ac.currentTime;
  engine.o.frequency.setTargetAtTime(on ? 38 + P.v * 3.2 : 30, t, 0.15);
  engine.g.gain.setTargetAtTime(on ? 0.035 : 0, t, 0.2);
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
  const on = b.hold ? [...held.values()].includes(b) : b.id === 'lights' && P && P.high;
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
    if (!(t.v < 0 && t.high && t.s > P.s + 5 && t.s - P.s < 260)) continue;
    const p = screenOf(t.s - t.len / 2, t.lat, 0.8); if (!p) continue;
    const k = 1 - (t.s - P.s) / 260, r = 24 + k * k * 220, g = x.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
    g.addColorStop(0, `rgba(255,250,235,${0.15 + k * 0.55})`); g.addColorStop(1, 'rgba(255,250,235,0)');
    x.fillStyle = g; x.fillRect(p.x - r, p.y - r, r * 2, r * 2);
  }
  if (whiteout > 0) { x.fillStyle = `rgba(225,232,240,${Math.min(0.92, whiteout)})`; x.fillRect(0, 0, W, H); }
  if (flash > 0) { x.fillStyle = `rgba(255,255,255,${flash * 0.75})`; x.fillRect(0, 0, W, H); }
  // Eyelids closing.
  const e = eyes();
  if (e > 0) { x.fillStyle = '#000'; x.fillRect(0, 0, W, H * 0.5 * e); x.fillRect(0, H - H * 0.5 * e, W, H * 0.5 * e); }

  // The end screens cover the rest; only the road shows under them.
  if (mode === 'crash' || mode === 'done') return;
  // Top: where to, how far, the time against the target, the points.
  const top = SAFE_T + 10, left = Math.max(SAFE_L + 92, LAND ? 100 : 92), right = W - SAFE_R - 62;
  fitText(`${leg.from} → ${leg.to}`, (left + right) / 2, top + 10, 15, right - left, '#e8eefc');
  rr(left, top + 24, right - left, 7, 4); x.fillStyle = 'rgba(255,255,255,0.18)'; x.fill();
  rr(left, top + 24, (right - left) * clamp(P.s / leg.len, 0, 1), 7, 4); x.fillStyle = '#f2b630'; x.fill();
  const par = parTime();
  text(`${mmss(T)} / ${mmss(par)}`, left, top + 46, 14, T > par ? '#ff9a8a' : '#cfe0ff', 'left', 600);
  text(`${points} p`, right, top + 46, 15, '#ffe08a', 'right', 800);
  text(`${Math.max(0, (leg.len - P.s) / 1000).toFixed(1).replace('.', ',')} km`, (left + right) / 2, top + 46, 13, '#9fb0cc', 'center', 600);
  if (leg.tired) {
    // Alertness: full when rested, empty when the driver falls asleep.
    const bx = left, by = top + 62, bw = Math.min(120, right - left);
    text('Vireys', bx, by + 5, 11, '#9fb0cc', 'left', 600);
    rr(bx + 44, by, bw - 44, 9, 5); x.fillStyle = 'rgba(255,255,255,0.15)'; x.fill();
    rr(bx + 44, by, (bw - 44) * (1 - P.tired), 9, 5); x.fillStyle = P.tired > 0.62 ? '#ff6a5a' : P.tired > 0.4 ? '#f2b630' : '#7fd38a'; x.fill();
  }
  if (mode === 'drive') driveButtons();
  // Speed and the limit, above the buttons.
  const lim = limitAt(P.s), kmh = Math.round(P.v * KMH), over = kmh > lim + 5;
  const sy = LAND ? H - SAFE_B - 40 : (btns.find(b => b.id === 'brake') || { y: H - 120 }).y - 34, sx = W / 2 - 22;
  text(String(kmh), sx, sy, 34, over ? '#ff7a6a' : '#ffffff', 'right', 800);
  text('km/h', sx + 4, sy + 8, 12, '#9fb0cc', 'left', 600);
  x.beginPath(); x.arc(sx + 62, sy, 19, 0, TAU); x.fillStyle = '#d42a1e'; x.fill();
  x.beginPath(); x.arc(sx + 62, sy, 14, 0, TAU); x.fillStyle = '#fff'; x.fill();
  text(String(lim), sx + 62, sy + 1, 14, '#111', 'center', 800);
  // A hint at the rest area while sleepy.
  const bay = road.bays.find(b => b.s1 > P.s && b.s0 - P.s < 260);
  if (bay && P.tired > 0.25 && mode === 'drive') fitText(P.rest > 0 ? 'Kahvitauko…' : 'Levähdysalue: oikealle ja pysähdy', W / 2, sy - 44, 15, W - 40, '#ffe08a');
  // Messages: overtakes, fines, the lights.
  msgs.forEach((m, i) => {
    const a = clamp(2.2 - m.t, 0, 1), y0 = H * 0.3 + i * 30 - m.t * 10;
    x.globalAlpha = a; fitText(m.text, W / 2, y0, 18, W - 30, m.good ? '#9ff0a8' : '#ffb0a0'); x.globalAlpha = 1;
  });
  for (const b of btns) if (mode === 'drive') {
    if (b.id === 'lights') drawBtn(b, false), lightsIcon(b);
    else if (b.id === 'pause') { rr(b.x, b.y, b.w, b.h, 12); x.fillStyle = 'rgba(30,38,58,0.7)'; x.fill(); text('II', b.x + b.w / 2, b.y + b.h / 2 + 1, 16, '#fff'); }
    else drawBtn(b, false);
  }
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
  const tips = ['Pitkät valot päälle, kun tie on tyhjä,', 'pois, kun joku tulee vastaan.', 'Varo hirviä, kuoppia ja kameroita.'];
  const listX = LAND ? lx + colW + pad : lx, listY = LAND ? SAFE_T + 50 : titleY + 58, listH = LAND ? H - listY - SAFE_B - 10 : H - listY - SAFE_B - 170;
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
  fitText(`Osa ${sel}: ${W0}, ${(L.len / 1000).toFixed(1).replace('.', ',')} km`, lx + colW / 2, infoY, 14, colW, '#cfe0ff', 'center', 600);
  tips.forEach((t, i) => fitText(t, lx + colW / 2, infoY + 24 + i * 19, 13, colW, '#9fb0cc', 'center', 500));
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
  const w = Math.min(340, W - 24), h = LAND ? H - 30 : 270, x0 = (W - w) / 2, y0 = LAND ? 15 : H * 0.22;
  panel(x0, y0, w, h);
  const asleep = crashWhy.startsWith('Nukahdit');
  text(asleep ? 'Nukahdit!' : crashWhy.startsWith('Vaara') ? 'Vaaratilanne!' : crashWhy.startsWith('Rengas') ? 'Rengas rikki!' : 'Kolari!', W / 2, y0 + 36, 28, '#ff8a7a', 'center', 900);
  const words = crashWhy.split(' '); let line = '', ly = y0 + 74;
  for (const wd of words) { if ((line + ' ' + wd).length > 32) { text(line.trim(), W / 2, ly, 15, '#e8eefc', 'center', 600); ly += 21; line = ''; } line += ' ' + wd; }
  text(line.trim(), W / 2, ly, 15, '#e8eefc', 'center', 600);
  if (asleep) text('Pysähdy levähdysalueelle kahville.', W / 2, ly + 26, 13, '#9fb0cc', 'center', 500);
  endButtons([['uudelleen', 'Yritä uudelleen'], ['valikko', 'Valikko']], y0 + h - 130);
}
function doneScreen() {
  const r = result, w = Math.min(LAND ? 640 : 340, W - 24), x0 = (W - w) / 2, y0 = LAND ? 10 : Math.max(SAFE_T + 50, H * 0.08), h = LAND ? H - 20 : Math.min(H - y0 - 20, 560);
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
    ['Aikabonus', `+${r.bonus}`],
  ];
  if (leg.tired) rows.splice(5, 0, ['Kahvitauot', String(tally.tauko)]);
  const tx0 = LAND ? x0 + 16 : x0 + 22, tx1 = LAND ? x0 + w / 2 - 10 : x0 + w - 22, ty = LAND ? y0 + 96 : y0 + 104;
  rows.forEach(([a, b], i) => { text(a, tx0, ty + i * 24, 14, '#cfd8ea', 'left', 500); text(b, tx1, ty + i * 24, 14, '#fff', 'right', 700); });
  const py = ty + rows.length * 24 + 14;
  text(`${points} p`, cx, py, 28, '#ffffff', 'center', 900);
  text(r.record ? 'Uusi ennätys!' : `Ennätys ${r.best} p`, cx, py + 28, 14, r.record ? '#9ff0a8' : '#9fb0cc', 'center', 700);
  const hint = r.stars < 2 ? 'Aja tavoiteajassa saadaksesi toisen tähden.' : r.stars < 3 ? 'Kolmas tähti: ei sakkoja, häikäisyjä eikä liian läheisiä ohituksia.' : 'Täydellinen yöajo!';
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
