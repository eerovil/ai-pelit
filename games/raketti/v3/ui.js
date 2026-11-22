'use strict';
const $ = id => document.getElementById(id);
var panelName = 'menu', helpPage = 0, helpReturn = 'menu', pendingKind = 'launch';
var lastKind = 'launch', frameId = 0, lastFrame = 0, lastUi = 0, saveElapsed = 0;
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
    !paused && ship && ship.phase === 'flight' ? ship.throttle * 0.035 : 0, audio.currentTime, 0.08);
}
function distance(m) {
  if (!Number.isFinite(m)) return 'avoin rata';
  if (Math.abs(m) < 1000) return `${Math.round(m)} m`;
  return `${(m / 1000).toFixed(Math.abs(m) < 10000 ? 1 : 0)} km`;
}
function duration(t) { return `${Math.floor(t / 60).toString().padStart(2, '0')}:${Math.floor(t % 60).toString().padStart(2, '0')}`; }
function text(id, value) { const n = $(id); if (n.textContent !== value) n.textContent = value; }
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
function activeSaved() { const s = loadFlight(); return s && ['flight', 'pad'].includes(s.phase); }
function startFlight(kind) {
  ship = freshFlight(kind); lastKind = kind;
  ship.phase = 'flight'; ship.throttle = kind === 'launch' ? 1 : 0;
  view = kind === 'orbit' ? 'map' : kind === 'dock' ? 'dock' : 'flight';
  warp = 1; saveElapsed = 0; releaseInputs(); paused = false; saveFlight(); play();
}
function requestFlight(kind) {
  pendingKind = kind;
  if (activeSaved()) showPanel('replace-panel'); else startFlight(kind);
}
function mainMenu() {
  if (ship) saveFlight();
  readRecords();
  $('resume').hidden = !activeSaved();
  text('achievements', achieved.dock ? 'SAAVUTETTU · Kiertorata ja telakointi' : achieved.orbit ? 'SAAVUTETTU · Kiertorata' : 'Oma lento. Omat päätökset.');
  showPanel('menu');
}
function showResult() {
  const success = ship.phase === 'docked';
  text('result-label', ship.practice ? 'HARJOITUS PÄÄTTYI' : 'LENTO PÄÄTTYI');
  text('result-title', success ? 'Tervetuloa asemalle.' : 'Lento keskeytyi.');
  text('result-reason', ship.reason);
  text('result-stats', `Lentoaika ${duration(ship.t)} · Korkeus ${distance(orbit().altitude)}${ship.practice ? ' · Harjoitus ei kirjaa saavutuksia.' : ''}`);
  showPanel('result');
}
function guidance() {
  if (!ship) return ['01', 'Laukaisu → kiertorata → telakointi'];
  const o = orbit(), d = approach(), h = o.altitude;
  if (d.range < 2000) {
    if (d.speed > 1) return ['03', `Jarruta siirtosuuttimilla. Nopeusero ${d.speed.toFixed(2)} m/s. Keltainen viiva näyttää liikkeen asemaan nähden.`];
    if (Math.abs(d.cross) > 1) return ['03', `Kohdista portin vihreälle linjalle: sivuero ${d.cross.toFixed(1)} m. Suuttimien nuolet ovat aluksen suuntia.`];
    return ['03', `Lähesty porttia alle 0,25 m/s. Nokan suuntaero ${(d.alignment * 180 / Math.PI).toFixed(1)}°. Vastapainallus pysäyttää kierron.`];
  }
  if (ship.stage === 0 && ship.fuel[0] < 1) return ['01', '1. vaihe tyhjä. Irrota vaihe, nosta sitten 2. vaiheen teho. Irrotus katkaisee moottorin.'];
  if (h < 3000) return ['01', 'Teho 100 %. Nokka lähes pystyssä. Käännä maltillisesti oikealle; vastapainallus pysäyttää kierron.'];
  if (h < 45000 && !ship.orbited) return ['01', `Käänny vähitellen kohti horisonttia. Kuormitus ${(atmosphere(ship.x, ship.y, ship.vx, ship.vy).q / 1000).toFixed(0)} kPa; vähennä tehoa tarvittaessa.`];
  if (o.apo < 380000 && !ship.orbited) return ['02', `Nosta radan ylin noin 400 km:iin. Vaakasuora vauhti ${Math.round(o.vt)} m/s. Avaa Kartta.`];
  if (o.peri < 150000) return ['02', `Katkaise nousupoltto. Radan ylimpään ${Number.isFinite(o.toApo) ? duration(o.toApo) : '—'}. Kiihdytä siellä liikesuuntaan: nosta radan alin yli 150 km.`];
  if (ship.fuel[1] < 1 && ship.rcs < 1) return ['02', 'Polttoaine loppui. Vapaa lento jatkuu. Voit aloittaa uuden lennon valikosta.'];
  const lead = wrap(Math.atan2(d.p.x, d.p.y) - Math.atan2(ship.x, ship.y)) * 180 / Math.PI;
  return ['02', `Asema ${Math.abs(lead).toFixed(1)}° ${lead >= 0 ? 'edellä' : 'jäljessä'}, ${distance(d.range)}. ${lead >= 0 ? 'Alempi rata saavuttaa asemaa.' : 'Ylempi rata antaa aseman saavuttaa sinut.'} Kohtaaminen: Ohje → 4.`];
}
function updateUi() {
  limitWarp();
  const s = ship || freshFlight(), o = orbit(s), d = approach(s);
  text('alt', distance(o.altitude));
  text('speed', `${Math.round(o.speed).toLocaleString('fi-FI')} m/s`);
  text('fuel', `${Math.round(s.fuel[s.stage] / STAGES[s.stage].fuel * 100)} % · ${s.stage + 1}. vaihe`);
  const docking = view === 'dock';
  text('metric-a-label', docking ? 'ETÄISYYS PORTTIIN' : 'RADAN ALIN');
  text('metric-b-label', docking ? 'NOPEUSERO' : 'RADAN YLIN');
  text('metric-c-label', docking ? 'SUUNTAERO / KIERTO' : 'NOKKA / KIERTO');
  text('metric-a', docking ? distance(d.range) : distance(o.peri));
  text('metric-b', docking ? `${d.speed.toFixed(2)} m/s` : distance(o.apo));
  const angle = docking ? d.alignment : wrap(s.angle - Math.atan2(s.x, s.y));
  const spin = docking ? d.spin : s.omega - (s.y * s.vx - s.x * s.vy) / o.r ** 2;
  text('metric-c', `${(angle * 180 / Math.PI).toFixed(1)}° / ${(spin * 180 / Math.PI).toFixed(1)}°/s`);
  text('clock', `T+ ${duration(s.t)}`);
  text('phase-name', s.phase === 'docked' ? 'TELAKOITU' : s.orbited ? 'KIERTORADALLA' : s.phase === 'pad' ? 'VALMIS LAUKAISUUN' : 'KÄSIN OHJATTU LENTO');
  text('flight-tag', s.practice ? 'HARJOITUS / KÄSIOHJAUS' : 'LENNONJOHTO / 01');
  text('power', `${s.throttle > 0 && s.throttle < .1 ? (s.throttle * 100).toFixed(1) : Math.round(s.throttle * 100)} %`);
  $('throttle').value = s.throttle * 100;
  text('rcs', `Suuttimien polttoaine ${Math.round(s.rcs / RCS_FULL * 100)} %`);
  text('warp', `Aika ×${warp}`);
  text('warp-note', d.range <= DOCK_REALTIME_RANGE ? 'Porttiin enintään 20 m: ×1' : maxWarp() === 100 ? 'Vapaa lento: ×2/×5/×10/×100' : 'Myös ohjaten ja moottorilla: ×2/×5');
  const live = ship && ship.phase === 'flight' && !paused;
  $('stage').disabled = !live || s.stage !== 0 || o.altitude < 1000;
  text('stage', s.stage === 0 ? 'Irrota 1. vaihe' : '2. vaihe käytössä');
  $('throttle').disabled = !live || s.fuel[s.stage] === 0;
  $('cut').disabled = !live;
  $('warp').disabled = !live || maxWarp() === 1;
  for (const b of document.querySelectorAll('[data-hold]')) {
    const rotational = b.dataset.hold.startsWith('turn:');
    b.disabled = !live || (s.rcs === 0 && (!rotational || s.throttle === 0));
  }
  for (const b of document.querySelectorAll('[data-view]')) b.classList.toggle('selected', b.dataset.view === view);
  const [n, g] = guidance(); text('guide-step', n); text('guide', g);
}
const HELP = [
  ['Sinä lennät koko matkan', `<p>Tavoite: laukaisu Maasta, vakaa kiertorata ja telakointi 400 km:n korkeudella lentävään asemaan. Yläilmakehään nouseminen ei vielä ole kiertorata.</p><ul><li>TEHO säätää päämoottoria. SEIS katkaisee sen.</li><li>↶ ↷ antavat kääntävää voimaa. Vapautus ei pysäytä kiertoa: paina vastakkaiseen suuntaan.</li><li>↑ ↓ ← → käyttävät pieniä siirtosuuttimia aluksen omissa suunnissa. Ne kuluttavat erillistä polttoainetta.</li><li>Ⅱ pysäyttää ajan. Puhelimen lukitus ja ohjeen avaaminen pysäyttävät myös lennon.</li></ul>`],
  ['01 / Laukaisu', `<p>Pidä aluksi teho täysillä. Nouse lähes pystysuoraan 1–3 km, kallista sitten hitaasti oikealle. Tavoittele noin 20° pystystä 10 km:ssä, 40° 40 km:ssä, 65° 100 km:ssä ja 80° 200 km:ssä. Tämä on lähtöohje, ei automaattinen lentorata.</p><p>Liian nopea kallistus vie raketin tiheään ilmaan. Liian pitkä pystynousu kuluttaa polttoaineen ilman tarvittavaa vaakavauhtia. Kun 1. vaihe tyhjenee, irrota se ja nosta 2. vaiheen teho. Se ei käynnisty itsestään.</p>`],
  ['02 / Rakenna kiertorata', `<p>400 km:n ympyräradalla tarvitaan noin 7 670 m/s vaakavauhtia. Mittarit näyttävät inertiaalisen nopeuden sekä radan alimman ja ylimmän korkeuden.</p><p>Nosta radan ylin noin 400 km:iin ja katkaise moottori. Lähellä radan ylintä kiihdytä vaakasuoraan liikesuuntaan, kunnes myös radan alin on yli 150 km. Negatiivinen alin tarkoittaa, että rata leikkaa maan. Kartta näyttää lentoradan ilman tulevia moottoripolttoja.</p>`],
  ['02 / Kohtaa liikkuva asema', `<p>Pelkkä sama korkeus ei riitä: aseman on oltava samassa paikassa samaan aikaan. Alempi rata kiertää nopeammin ja saavuttaa edellä olevan aseman. Jos asema on jäljessä, ylemmällä radalla se saavuttaa sinut. Älä yritä lentää suoraan asemaa kohti: suora oikaisu voi viedä ilmakehään.</p><p>Esimerkki 250 km:n ympyräradalta: kun asema on noin 3° edellä, kiihdytä liikesuuntaan noin 43 m/s. Siirtoradan ylin nousee 400 km:iin. Noin 45 minuutin kuluttua, ylimmässä pisteessä, kiihdytä vielä noin 43 m/s tasataksesi radat. Tarkista todellinen kohtaaminen kartalta. Tämä arvio ei korjaa lentoa puolestasi.</p>`],
  ['03 / Telakoi hitaasti', `<p>Asema-näkymässä oikea on aseman liikesuunta ja ylös poispäin Maasta. Lähesty vasemmalta portin vihreää linjaa pitkin, nokka oikealle. Aluksen suunnat voivat erota näytön suunnista.</p><ul><li>Keltainen viiva näyttää liikkeen asemaan nähden. Jarruta vastakkaisella suuttimella.</li><li>Renkaan etäisyys alle 1,2 m, nopeusero enintään 0,25 m/s.</li><li>Nokan suuntaero enintään 5° ja kiertoero enintään 0,6°/s.</li><li>Portti lukittuu kosketuksesta. Aseman runko ja aurinkopaneelit ovat törmäysesteitä.</li></ul>`],
  ['Lentomalli ja tallennus', `<p>Fysiikka käyttää metrejä, sekunteja ja kiloja: pallomainen pyörivä Maa, etäisyyden neliössä heikkenevä painovoima, ilmanvastus, muuttuva massa sekä päämoottorin ja siirtosuuttimien liikemäärä. Raketti on kuvitteellinen kaksivaiheinen kantoraketti.</p><p>Rajaukset: yksi ratataso, yksinkertaistettu ilmakehä ja aerodynamiikka; ei Kuuta, nostetta, polttoaineen loiskumista eikä lämpökilpeä. Alukset ovat kuvassa suurennettuja. Tallennus säilyttää lennon; jatkaminen alkaa tauolta. Harjoitukset eivät kirjaa koko lennon saavutuksia.</p>`],
  ['Ajan nopeutus', `<p>Aika-painike kiertää nopeudet ×1, ×2 ja ×5 myös nousussa, moottorin käydessä ja suuttimia käyttäessä. Sama fysiikka ja polttoaineenkulutus jatkuvat; reagoimiseen jää vähemmän aikaa. ×10 ja ×100 toimivat vain ilmakehän yläpuolella, moottori ja suuttimet pois, hitaalla kierrolla ja yli 5 km asemasta. Ohjaus tai näiden ehtojen päättyminen rajoittaa nopeuden ×5:een. Viimeiset 20 m porttiin lennetään aina ×1-ajalla; nopeutus ei käynnisty uudelleen itsestään.</p>`]
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
$('launch').onclick = () => requestFlight('launch');
$('practice-orbit').onclick = () => requestFlight('orbit');
$('practice-dock').onclick = () => requestFlight('dock');
$('replace-yes').onclick = () => startFlight(pendingKind);
$('replace-no').onclick = mainMenu;
$('resume').onclick = () => {
  const loaded = loadFlight(); if (!loaded) { mainMenu(); return; }
  ship = loaded; lastKind = ship.practice ? (approach().range < 2000 ? 'dock' : 'orbit') : 'launch';
  view = approach().range < 2000 ? 'dock' : ship.orbited ? 'map' : 'flight';
  showPanel('pause-panel');
};
$('pause').onclick = () => { if (ship && ship.phase === 'flight') { saveFlight(); showPanel('pause-panel'); } };
$('continue').onclick = play;
$('to-menu').onclick = mainMenu; $('result-menu').onclick = mainMenu;
$('retry').onclick = () => startFlight(lastKind);
$('throttle').oninput = () => {
  if (!paused && ship && ship.phase === 'flight') { ship.throttle = +$('throttle').value / 100; limitWarp(); updateUi(); }
};
$('cut').onclick = () => { if (ship) { ship.throttle = 0; updateUi(); updateSound(); } };
$('stage').onclick = () => { stageRocket(); updateUi(); draw(); };
$('warp').onclick = () => {
  const rates = [1, 2, 5, 10, 100].filter(rate => canWarp(rate));
  warp = rates[(rates.indexOf(warp) + 1) % rates.length];
  updateUi();
};
for (const b of document.querySelectorAll('[data-view]')) b.onclick = () => { view = b.dataset.view; updateUi(); draw(); };
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
$('help').onclick = $('menu-help').onclick = openHelp;
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
readRecords(); mainMenu(); fitCanvas();
