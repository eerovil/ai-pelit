'use strict';
const $ = id => document.getElementById(id);
const WARPS = [1, 2, 5, 10, 100, 1000];
var panelName = 'menu', helpPage = 0, helpReturn = 'menu', pendingStart = null, chosenTrip = 'kiertorata';
var frameId = 0, lastFrame = 0, lastUi = 0, saveElapsed = 0, flash = '', flashUntil = 0;
const pointers = new Map();
var audio = null, engineGain = null;
function soundReady() {
  try {
    if (!audio) {
      audio = new (window.AudioContext || window.webkitAudioContext)();
      const buffer = audio.createBuffer(1, audio.sampleRate * 2, audio.sampleRate);
      const samples = buffer.getChannelData(0);
      for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
      const noise = audio.createBufferSource(); noise.buffer = buffer; noise.loop = true;
      const filter = audio.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 180;
      engineGain = audio.createGain(); engineGain.gain.value = 0;
      noise.connect(filter); filter.connect(engineGain); engineGain.connect(audio.destination); noise.start();
    }
    if (audio.state === 'suspended') audio.resume().catch(() => {});
  } catch (_) { /* Sound is optional. */ }
}
function updateSound() {
  if (audio && engineGain) engineGain.gain.setTargetAtTime(
    !paused && ship && ship.phase === 'flight' ? Math.sqrt(ship.throttle) * 0.035 : 0, audio.currentTime, 0.08);
}
function duration(t) {
  t = Math.max(0, t);
  const h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), sec = Math.floor(t % 60);
  return `${h ? h + ':' + String(m).padStart(2, '0') : String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}
function text(id, value) { const n = $(id); if (n.textContent !== value) n.textContent = value; }
function starText(n) { return '★'.repeat(n) + '☆'.repeat(3 - n); }
function showPanel(name) {
  panelName = name; $('overlay').hidden = !name;
  for (const el of document.querySelectorAll('.panel')) el.hidden = el.id !== name;
  if (name) {
    cancelAnimationFrame(frameId); frameId = 0;
    releaseInputs(); paused = true; warp = 1; updateSound();
  }
  updateUi(); draw();
}
function releaseInputs() {
  pointers.clear(); clearHeld();
  document.querySelectorAll('[data-hold]').forEach(b => b.classList.remove('held'));
}
function schedule() { if (!frameId && !paused && ship && ship.phase === 'flight') frameId = requestAnimationFrame(frame); }
function frame(now) {
  frameId = 0;
  if (paused || !ship || ship.phase !== 'flight') return;
  const dt = lastFrame ? Math.max(0, Math.min(0.2, (now - lastFrame) / 1000)) : 0;
  lastFrame = now;
  limitWarp();
  advanceFlight(dt); saveElapsed += dt;
  if (saveElapsed >= 2) { saveFlight(); saveElapsed = 0; }
  if (now - lastUi >= 80) { updateUi(); lastUi = now; }
  draw(); updateSound();
  if (ship.phase !== 'flight') { showResult(); return; }
  schedule();
}
function play() {
  if (!ship || ship.phase !== 'flight') return;
  showPanel(''); paused = false; lastFrame = 0; updateUi(); updateSound(); schedule();
}
function activeSaved() { const s = loadFlight(); return s && s.phase === 'flight' ? s : null; }
function startFlight(trip, from) {
  ship = freshFlight(trip, from); chosenTrip = trip;
  view = from === 'orbit' ? 'map' : 'flight'; mapWide = false;
  warp = 1; saveElapsed = 0; flash = ''; releaseInputs(); paused = false; saveFlight(); play();
}
function requestFlight(trip, from) {
  pendingStart = [trip, from];
  if (activeSaved()) showPanel('replace-panel'); else startFlight(trip, from);
}
function renderTrips() {
  const list = $('trips');
  list.textContent = '';
  for (const t of TRIPS) {
    const open = tripOpen(t.id), b = document.createElement('button');
    b.className = 'trip'; b.dataset.trip = t.id; b.disabled = !open;
    b.innerHTML = `<span class="trip-name"></span><span class="trip-meta"></span><span class="trip-stars"></span>`;
    b.querySelector('.trip-name').textContent = (open ? '' : '🔒 ') + t.name;
    b.querySelector('.trip-meta').textContent = `noin ${t.minutes} min`;
    b.querySelector('.trip-stars').textContent = open ? starText(stars[t.id] || 0) : '';
    b.onclick = () => openTrip(t.id);
    list.appendChild(b);
  }
}
function mainMenu() {
  if (ship) saveFlight();
  readStars(); renderTrips();
  const saved = activeSaved();
  $('resume').hidden = !saved;
  if (saved) text('resume', `Jatka: ${TRIP[saved.trip].name}`);
  const total = TRIPS.reduce((n, t) => n + (stars[t.id] || 0), 0);
  text('star-total', `Tähtiä ${total} / ${TRIPS.length * 3}`);
  showPanel('menu');
}
function openTrip(id) {
  if (!tripOpen(id)) return;
  chosenTrip = id;
  const t = TRIP[id];
  text('trip-title', t.name); text('trip-goal', t.goal);
  text('trip-stars', `${starText(stars[id] || 0)} · noin ${t.minutes} min`);
  text('trip-star-rule', `Tähdet: perillä · Δv jäljellä vähintään ${t.dvStar} m/s · ${t.soft}.`);
  $('start-orbit').hidden = id === 'kiertorata' || !(stars.kiertorata > 0);
  showPanel('trip-panel');
}
function nextTrip(id) { const i = TRIPS.findIndex(t => t.id === id); return TRIPS[i + 1] || null; }
function showResult() {
  const ok = ship.phase === 'done', t = TRIP[ship.trip];
  text('result-label', t.name.toUpperCase());
  text('result-title', ok ? 'Matka onnistui!' : 'Matka päättyi.');
  text('result-reason', ship.reason);
  $('result-stars').hidden = !ok;
  if (ok) {
    text('result-star-big', starText(ship.stars));
    const dv = Math.round(deltaV(ship)), soft = tripSoft(ship);
    const rows = [['Perillä', true],
      [`Δv jäljellä ${dv} m/s (tähti ≥ ${t.dvStar})`, dv >= t.dvStar],
      [soft ? `${t.soft[0].toUpperCase()}${t.soft.slice(1)}` : `Ei ${t.soft}`, soft]];
    const ul = $('result-list'); ul.textContent = '';
    for (const [label, lit] of rows) {
      const li = document.createElement('li'); li.className = lit ? 'lit' : 'dim';
      li.textContent = `${lit ? '★' : '☆'} ${label}`; ul.appendChild(li);
    }
  }
  text('result-stats', `Lentoaika T+ ${duration(ship.t)} · pelattu ${duration(ship.real)}`);
  const next = ok && nextTrip(ship.trip);
  $('result-next').hidden = !next;
  if (next) text('result-next', `Seuraava: ${next.name}`);
  showPanel('result');
}
function telemetry(s) {
  const ref = refBody(s), o = orbitAround(ref, s), d = approach(s);
  const docking = view === 'dock';
  const fuelPct = Math.round(s.fuel / SHIP.fuel * 100);
  return {
    alt: km(Math.max(0, o.altitude - SHIP.length / 2)),
    speed: `${Math.round(s.landedOn ? 0 : o.speed).toLocaleString('fi-FI')} m/s`,
    fuel: `${fuelPct} %`,
    aLabel: docking ? 'PORTTIIN' : 'RADAN ALIN', a: docking ? km(d.range) : s.landedOn ? '—' : o.peri < 0 ? 'pinnan alla' : km(o.peri),
    bLabel: docking ? 'NOPEUSERO' : 'RADAN YLIN', b: docking ? `${d.speed.toFixed(2)} m/s` : s.landedOn ? '—' : o.energy >= 0 ? 'karkaa' : km(o.apo),
    cLabel: docking ? 'SUUNTAERO' : 'Δv JÄLJELLÄ', c: docking ? `${Math.round(Math.abs(d.alignment) * 180 / Math.PI)}°` : `${Math.round(deltaV(s)).toLocaleString('fi-FI')} m/s`,
    ref
  };
}
function stateName(s, ref) {
  if (s.phase === 'done') return 'PERILLÄ';
  if (s.phase === 'crashed') return 'MATKA PÄÄTTYI';
  if (s.landedOn) return { earth: 'MAAN PINNALLA', moon: 'KUUN PINNALLA', rock: 'PIKKUKIVELLÄ' }[s.landedOn];
  if (s.chute === 'open') return 'LASKUVARJO AUKI';
  return { earth: 'MAAN LÄHELLÄ', moon: 'KUUN LÄHELLÄ', rock: 'PIKKUKIVEN LÄHELLÄ' }[ref.id];
}
function updateUi() {
  limitWarp();
  const s = ship || freshFlight(chosenTrip), m = telemetry(s);
  text('alt', m.alt); text('speed', m.speed); text('fuel', m.fuel);
  text('metric-a-label', m.aLabel); text('metric-b-label', m.bLabel); text('metric-c-label', m.cLabel);
  text('metric-a', m.a); text('metric-b', m.b); text('metric-c', m.c);
  text('clock', `T+ ${duration(s.t)}`);
  text('phase-name', stateName(s, m.ref));
  text('flight-tag', TRIP[s.trip].name.toUpperCase());
  const pct = Math.sqrt(s.throttle) * 100;
  text('power', `${Math.round(s.throttle * 100)} %`);
  if (Math.abs(+$('throttle').value - pct) > 0.5) $('throttle').value = pct;
  text('rcs', `Suuttimet ${Math.round(s.rcs / SHIP.rcsDv * 100)} %`);
  text('warp', `Aika ×${warp}`);
  const live = !!ship && ship.phase === 'flight' && !paused;
  $('throttle').disabled = !live || s.fuel === 0;
  $('cut').disabled = !live;
  $('warp').disabled = !live || maxWarp() === 1;
  // Only while falling: opened on the way up, it would end the climb for good.
  const air = Math.hypot(s.x, s.y) - EARTH_R < EARTH.air.top && s.x * s.vx + s.y * s.vy < 0;
  $('chute').disabled = !live || s.chute !== 'packed' || !air || !!s.landedOn;
  text('chute', s.chute === 'open' ? 'Varjo auki' : s.chute === 'torn' ? 'Varjo rikki' : 'Laskuvarjo');
  for (const b of document.querySelectorAll('[data-point]')) {
    b.disabled = !live || s.chute === 'open';
    b.classList.toggle('selected', s.point === b.dataset.point);
  }
  for (const b of document.querySelectorAll('[data-hold]')) {
    const turning = b.dataset.hold.startsWith('turn:');
    b.disabled = !live || (!turning && s.rcs === 0) || (turning && s.chute === 'open');
  }
  $('view-dock').hidden = s.trip !== 'asema';
  if (view === 'dock' && s.trip !== 'asema') view = 'flight';
  for (const b of document.querySelectorAll('[data-view]')) b.classList.toggle('selected', b.dataset.view === view);
  let [n, g] = guidance(s, ship ? currentPath(s) : null);
  if (flash && performance.now() < flashUntil) { n = '!'; g = flash; }
  else if (s.note && s.phase === 'flight') g = `${s.note} ${g}`;
  text('guide-step', n); text('guide', g);
}
const HELP = [
  ['Ohjaus', `<ul><li><b>TEHO</b> säätää moottoria. Liukusäätimen alkupää on hienosäätöä varten. <b>SEIS</b> katkaisee moottorin.</li><li><b>↶ ↷</b> kääntävät nokkaa: ensin hitaasti, sitten nopeammin. Kun päästät irti, nokka pysyy siinä suunnassa.</li><li><b>Menosuuntaan</b>, <b>Vastasuuntaan</b> ja <b>Pystyyn</b> kääntävät nokan ja pitävät sen siinä. Ne eivät käynnistä moottoria.</li><li><b>← ↑ ↓ →</b> ovat pieniä siirtosuuttimia aluksen omiin suuntiin, hienosäätöön.</li><li><b>Laskuvarjo</b> toimii vain Maan ilmakehässä.</li></ul>`],
  ['1 · Kiertoradalle', `<p>Nosta teho täysille ja nouse ensin suoraan ylös. Noin 1,5 km:n jälkeen kallista ↷ vähitellen: 20° pystystä alussa, 80° noin 30 km:n korkeudessa.</p><p>Kun <b>radan ylin</b> on noin 60 km, katkaise teho. Odota radan ylimpään kohtaan, paina <b>Menosuuntaan</b> ja kiihdytä, kunnes myös <b>radan alin</b> on yli 40 km. Katkaise lopuksi teho.</p>`],
  ['2 · Kuuhun', `<p><b>Kartta</b> näyttää, mihin rata vie moottori sammuksissa. Odota kiertoradalla, kunnes Kuu on ohjeen kertoman verran edellä. Paina <b>Menosuuntaan</b> ja kiihdytä, kunnes radan ylin on noin 4900 km. Nopeuta aikaa ×1000.</p><p>Kuun lähellä paina <b>Vastasuuntaan</b> ja jarruta: Kuun kiertoradalle riittää, että radan ylin on alle 370 km.</p>`],
  ['3 · Laskeutuminen', `<p>Jarruta <b>Vastasuuntaan</b> ja laske hiljalleen. Juuri ennen pintaa paina <b>Pystyyn</b>.</p><ul><li>Kuu: alas enintään 3 m/s, sivulle 2 m/s, kallistus 15°.</li><li>Pikkukivi: vauhti alle 1 m/s. Sen painovoima on hyvin heikko.</li><li>Maa: avaa laskuvarjo alle 20 km korkeudessa ja alle 400 m/s. Kosketus alle 10 m/s.</li></ul>`],
  ['4 · Asema', `<p>Asema kiertää 100 km korkeudessa. Alempi rata kiertää nopeammin ja saavuttaa sen, ylempi jättää sen edelle. Kun asema on lähellä, avaa <b>Asema</b>-näkymä.</p><p>Paina <b>Vastasuuntaan</b> ja jarruta nopeusero pieneksi. Käännä nokka porttia kohti ja lähesty siirtosuuttimilla: alle 3 m, alle 0,5 m/s, nokka enintään 10° vinossa.</p>`],
  ['Tähdet ja aika', `<p>Joka matkasta saa kolme tähteä: yksi perille pääsystä, yksi kun Δv:tä (polttoainetta) jää matkan rajan yli, yksi pehmeästä laskeutumisesta, telakoinnista tai pyöreästä radasta. Onnistunut matka avaa seuraavan. Kun Kiertoradalle on lennetty, muut matkat voi aloittaa myös valmiilta kiertoradalta.</p><p><b>Aika</b>-painike nopeuttaa lentoa: ×2 ja ×5 aina, ×10–×1000 kun moottori on sammuksissa ja pinnat kaukana. Nopeus hidastuu itsestään lähestyessä.</p>`]
];
function openHelp() {
  helpReturn = panelName || 'pause-panel';
  if (ship) saveFlight();
  helpPage = 0; showPanel('help-panel'); renderHelp();
}
function renderHelp() {
  text('help-title', HELP[helpPage][0]); $('help-body').innerHTML = HELP[helpPage][1];
  text('help-page', `${helpPage + 1} / ${HELP.length}`);
  $('help-prev').disabled = helpPage === 0; $('help-next').disabled = helpPage === HELP.length - 1;
}
function say(message) { if (message) { flash = message; flashUntil = performance.now() + 3000; } updateUi(); }
$('start-pad').onclick = () => requestFlight(chosenTrip, 'pad');
$('start-orbit').onclick = () => requestFlight(chosenTrip, 'orbit');
$('trip-back').onclick = mainMenu;
$('replace-yes').onclick = () => startFlight(...pendingStart);
$('replace-no').onclick = mainMenu;
$('resume').onclick = () => {
  const loaded = activeSaved(); if (!loaded) { mainMenu(); return; }
  ship = loaded; chosenTrip = ship.trip; mapWide = false;
  view = ship.trip === 'asema' && approach().range < 2000 ? 'dock' : 'flight';
  showPanel('pause-panel');
};
$('pause').onclick = () => { if (ship && ship.phase === 'flight') { saveFlight(); showPanel('pause-panel'); } };
$('continue').onclick = play;
$('to-menu').onclick = mainMenu; $('result-menu').onclick = mainMenu;
$('retry').onclick = () => startFlight(ship.trip, ship.from);
$('result-next').onclick = () => { const n = nextTrip(ship.trip); if (n) { readStars(); openTrip(n.id); } };
// The slider is quadratic: its first half covers 0–25 %, for hovering and gentle burns.
$('throttle').oninput = () => {
  if (!paused && ship && ship.phase === 'flight') {
    ship.throttle = (+$('throttle').value / 100) ** 2; limitWarp(); updateUi();
  }
};
$('cut').onclick = () => { if (ship) { ship.throttle = 0; $('throttle').value = 0; updateUi(); updateSound(); } };
$('chute').onclick = () => say(openChute());
for (const b of document.querySelectorAll('[data-point]')) b.onclick = () => {
  if (paused || !ship || ship.phase !== 'flight') return;
  ship.point = ship.point === b.dataset.point ? null : b.dataset.point;
  updateUi();
};
$('warp').onclick = () => {
  const rates = WARPS.filter(rate => rate <= maxWarp());
  warp = rates[(rates.indexOf(warp) + 1) % rates.length];
  updateUi();
};
for (const b of document.querySelectorAll('[data-view]')) b.onclick = () => { view = b.dataset.view; updateUi(); draw(); };
canvas.addEventListener('click', () => { if (view === 'map') { mapWide = !mapWide; draw(); } });
function applyPointers() {
  clearHeld();
  for (const p of pointers.values()) held[p.key] = clamp(held[p.key] + p.value, -1, 1);
  for (const b of document.querySelectorAll('[data-hold]')) b.classList.toggle('held', [...pointers.values()].some(p => p.button === b));
}
for (const b of document.querySelectorAll('[data-hold]')) {
  b.onpointerdown = e => {
    if (paused || !ship || ship.phase !== 'flight' || b.disabled) return;
    e.preventDefault(); soundReady();
    const [key, value] = b.dataset.hold.split(':');
    pointers.set(e.pointerId, { key, value: +value, button: b });
    try { b.setPointerCapture(e.pointerId); } catch (_) { /* Window handlers release the finger if capture is unavailable. */ }
    applyPointers(); limitWarp(); updateUi();
  };
  const release = e => { pointers.delete(e.pointerId); applyPointers(); };
  b.onpointerup = b.onpointercancel = b.onlostpointercapture = release;
}
for (const event of ['pointerup', 'pointercancel']) window.addEventListener(event, e => {
  if (pointers.has(e.pointerId)) { pointers.delete(e.pointerId); applyPointers(); }
});
$('help').onclick = $('menu-help').onclick = $('pause-help').onclick = openHelp;
$('help-prev').onclick = () => { helpPage = Math.max(0, helpPage - 1); renderHelp(); };
$('help-next').onclick = () => { helpPage = Math.min(HELP.length - 1, helpPage + 1); renderHelp(); };
$('help-close').onclick = () => showPanel(helpReturn);
document.addEventListener('pointerdown', soundReady, { once: true });
function suspendFlight() {
  releaseInputs();
  if (ship && ship.phase === 'flight') {
    saveFlight();
    if (!panelName) showPanel('pause-panel');
  }
  updateSound();
}
document.addEventListener('visibilitychange', () => { if (document.hidden) suspendFlight(); });
window.addEventListener('blur', suspendFlight);
window.addEventListener('pagehide', () => { suspendFlight(); if (ship) saveFlight(); });
new ResizeObserver(fitCanvas).observe(canvas);
readStars(); mainMenu(); fitCanvas();
