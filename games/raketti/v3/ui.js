'use strict';
// Menus, the one-finger stick, saves and the frame loop.
const $ = id => document.getElementById(id);
// A drag this many px long burns at full power; shorter is gentler (power grows as the square
// of the drag past a small dead zone, so a short drag is fine control).
const STICK_RANGE = 80, STICK_DEAD = 8;
// warp: a skipped wait runs the flight faster until the next thing to do.
var warp = false, frameId = 0, lastFrame = 0, acc = 0, frames = 0, saveTimer = 0, currentHint = null, endShownAt = 0, sound = null;

function setStick(dx, dy) {
  const len = Math.hypot(dx, dy), k = len > STICK_RANGE ? STICK_RANGE / len : 1;
  stick.dx = dx * k; stick.dy = dy * k;
  stick.angle = Math.atan2(dx, -dy);
  stick.power = len < STICK_DEAD ? 0 : clamp((Math.min(len, STICK_RANGE) - STICK_DEAD) / (STICK_RANGE - STICK_DEAD), 0, 1) ** 2;
}
function releaseStick() { warp = false; stick.on = false; stick.power = 0; stick.dx = stick.dy = 0; }
canvas.addEventListener('pointerdown', e => {
  if (!ship || ship.phase !== 'flight' || paused) return;
  warp = false;
  canvas.setPointerCapture(e.pointerId);
  stick.on = true; stick.id = e.pointerId; stick.ox = e.clientX; stick.oy = e.clientY; setStick(0, 0);
  startSound();
  e.preventDefault();
});
canvas.addEventListener('pointermove', e => {
  if (!stick.on || e.pointerId !== stick.id) return;
  setStick(e.clientX - stick.ox, e.clientY - stick.oy);
});
for (const ev of ['pointerup', 'pointercancel', 'lostpointercapture']) {
  canvas.addEventListener(ev, e => { if (e.pointerId === stick.id) releaseStick(); });
}

// A soft engine hum through Web Audio, made on the first touch.
function startSound() {
  if (sound) return;
  try {
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const buf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
    const lp = ac.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 320;
    const gain = ac.createGain(); gain.gain.value = 0;
    src.connect(lp); lp.connect(gain); gain.connect(ac.destination); src.start();
    sound = { ac, gain };
  } catch (_) { sound = { gain: null }; }
}
function updateSound() {
  if (!sound || !sound.gain) return;
  const v = ship && ship.phase === 'flight' && !paused && !document.hidden ? 0.12 * ship.thrust / SHIP.acc : 0;
  sound.gain.gain.setTargetAtTime(v, sound.ac.currentTime, 0.05);
}

function starText(n) { return '★'.repeat(n) + '☆'.repeat(3 - n); }
function showPanel(id) {
  $('overlay').hidden = !id;
  for (const p of document.querySelectorAll('.panel')) p.hidden = p.id !== id;
}
function renderMenu() {
  const list = $('trips'); list.textContent = '';
  for (const t of TRIPS) {
    const open = tripOpen(t.id), b = document.createElement('button');
    b.className = 'trip'; b.dataset.trip = t.id; b.disabled = !open;
    b.innerHTML = `<span><b></b><small></small></span><i></i>`;
    b.querySelector('b').textContent = open ? t.name : `🔒 ${t.name}`;
    b.querySelector('small').textContent = t.goal;
    b.querySelector('i').textContent = open ? starText(stars[t.id] || 0) : '';
    b.onclick = () => startFlight(t.id);
    list.appendChild(b);
  }
  const saved = readFlight();
  $('resume').hidden = !saved;
  if (saved) $('resume').textContent = `Jatka: ${TRIP[saved.trip].name}`;
  const total = Object.values(stars).reduce((a, b) => a + b, 0);
  $('star-total').textContent = `★ ${total} / ${TRIPS.length * 3}`;
}
function openMenu() {
  if (ship && ship.phase === 'flight') saveFlight();
  paused = true; releaseStick(); updateSound();
  renderMenu(); showPanel('menu');
}
function begin(s) {
  ship = s; paused = false; warp = false; camReady = false; path = null; endShownAt = 0; acc = 0;
  releaseStick(); showPanel(null); updateHud(); saveFlight(); play();
}
function startFlight(trip) { begin(freshFlight(trip)); }

function updateHud() {
  if (!ship) return;
  $('trip-name').textContent = TRIP[ship.trip].name;
  $('fuel-bar').style.width = `${Math.round(fuelShare() * 100)}%`;
  $('fuel').classList.toggle('low', fuelShare() < 0.15);
  const h = currentHint, skip = canSkip(h);
  let text = h ? h.word : '';
  if (h && h.word === 'Odota' && h.wait >= 1.5) text += ` ${Math.ceil(h.wait)} s`;
  if (skip) text += warp ? ' ⏩⏩' : ' ⏩';
  if ($('hint').textContent !== text) $('hint').textContent = text;
  $('hint').classList.toggle('go', !!h && h.dir !== undefined);
  $('hint').classList.toggle('skip', skip);
}
function showResult() {
  const s = ship, ok = s.phase === 'done';
  $('result-title').textContent = ok ? 'Perillä!' : 'Rysähti!';
  $('result-stars').textContent = ok ? starText(s.stars) : '';
  $('result-reason').textContent = ok ? TRIP[s.trip].goal : s.reason;
  const list = $('result-list'); list.textContent = '';
  if (ok) {
    const soft = s.trip === 'kiertorata' || s.trip === 'kuu-kierto' ? 'Pyöreä rata' : s.trip === 'asema' ? 'Hellä telakointi' : 'Pehmeä lasku';
    const parts = starParts(s), labels = ['Perillä', `Polttoainetta jäi ${Math.round(fuelShare(s) * 100)} %`, soft];
    parts.forEach((p, i) => { const li = document.createElement('li'); li.textContent = `${p ? '★' : '☆'} ${labels[i]}`; li.className = p ? 'got' : ''; list.appendChild(li); });
  }
  const i = TRIPS.findIndex(t => t.id === s.trip), next = TRIPS[i + 1];
  $('result-next').hidden = !(ok && next && tripOpen(next.id));
  $('result-next').onclick = () => startFlight(next.id);
  showPanel('result');
}

// A wait can be skipped when it is long enough to bother, or its length is not known.
function canSkip(h) {
  return !!h && h.word === 'Odota' && !!ship && ship.phase === 'flight' && !paused && !ship.landedOn
    && (h.wait === undefined || h.wait >= 2.5);
}
function warpStep(dt) {
  // Any wait passes in about two seconds; never run past the moment the wait ends.
  const w = currentHint && currentHint.wait;
  if (w === undefined) return dt * 8;
  return Math.min(dt * clamp(w / 1.5, 4, 40), Math.max(0, w - 0.6));
}
function frame(now) {
  frameId = requestAnimationFrame(frame);
  const dt = Math.min(0.05, Math.max(0, (now - (lastFrame || now)) / 1000)); lastFrame = now;
  if (ship && !paused && ship.phase === 'flight') {
    acc += warp ? warpStep(dt) : dt;
    while (acc >= STEP && ship.phase === 'flight') {
      step(STEP); acc -= STEP;
      if (ship.phase === 'flight' && goalMet(ship)) endFlight(TRIP[ship.trip].goal, true);
    }
    saveTimer += dt;
    if (saveTimer > 2) { saveTimer = 0; saveFlight(); }
  }
  if (ship && (frames++ % 4 === 0 || !path || warp)) path = predictPath(ship);
  currentHint = ship ? hint(ship, path) : null;
  if (warp && !canSkip(currentHint)) warp = false;
  if (warp && currentHint.wait !== undefined && currentHint.wait < 1) warp = false;
  moveCamera(dt, currentHint);
  draw(currentHint, now);
  updateHud(); updateSound();
  if (ship && ship.phase !== 'flight' && !paused) {
    if (!endShownAt) endShownAt = now;
    else if (now - endShownAt > 900) { paused = true; showResult(); }
  }
}
function play() { if (!frameId) { lastFrame = 0; frameId = requestAnimationFrame(frame); } }

$('hint').onclick = () => { if (canSkip(currentHint)) { stick.power = 0; warp = !warp; updateHud(); } };
$('pause').onclick = () => { if (ship && ship.phase === 'flight') { paused = true; releaseStick(); saveFlight(); showPanel('pause-panel'); } };
$('continue').onclick = () => { paused = false; showPanel(null); };
$('to-menu').onclick = openMenu;
$('resume').onclick = () => { const s = readFlight(); if (s) begin(s); };
$('retry').onclick = () => startFlight(ship.trip);
$('result-menu').onclick = openMenu;
document.addEventListener('visibilitychange', () => {
  if (document.hidden && ship && ship.phase === 'flight' && !paused) {
    paused = true; releaseStick(); saveFlight(); showPanel('pause-panel');
  }
  updateSound();
});
addEventListener('pagehide', () => { if (ship && ship.phase === 'flight') saveFlight(); });

stars = readStars();
ship = readFlight() || freshFlight('kiertorata');
renderMenu(); showPanel('menu'); play();
