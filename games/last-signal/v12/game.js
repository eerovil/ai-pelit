'use strict';
// The sound, the HUD and cards, the round and the story, the actions everyone shares (`act`), and the inside of
// SISU walked as a person.
// ---------- sound ----------
let AC = null;
function audio() {
  if (AC) { if (AC.state === 'suspended' && !document.hidden) AC.resume(); return; }
  try { AC = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return; }
  try { soundscape(); } catch (e) { BED = null; }
}
// The sea's sound and SISU's engines: v8 (#151) made them here from noise and oscillators; v11 (#221) plays the
// shared library's recorded loops instead (lib/aanet-2): the deep sea's rumble, SISU's engine (faster with speed), the
// reactor's hum inside and the wind on the ice. Now and then, far off: a whale, the ice overhead or clicks in the deep.
// `mix()` says how loud each one is now; `soundStep` sets the loops there.
const SFX = window.AiPelitAanet;
SFX && SFX.load(['syvyys', 'sukellusvene', 'humina', 'tuuli', 'kaiku', 'metalli', 'onnistui', 'nousu', 'valinta', 'virhe',
  'kuplat', 'loiskis', 'osuma', 'narina', 'halytys', 'naksu', 'lumi', 'jaa']);
// A library sound, or this game's own beep when it did not play (not loaded yet, offline on the very first open).
function sfx(name, vol, ...beep) { if (!(SFX && SFX.play(name, { vol })) && beep.length) tone(...beep); }
let BED = null;
function soundscape() {
  if (!SFX) return;
  BED = { sea: SFX.loop('syvyys', { vol: 0 }), engine: SFX.loop('sukellusvene', { vol: 0 }), hum: SFX.loop('humina', { vol: 0 }),
    wind: SFX.loop('tuuli', { vol: 0 }), next: 4 };
}
// How loud each layer is (0–1) for where this phone's person is and how SISU moves.
function mix() {
  const m = G.mode, speed = Math.min(1, Math.hypot(sub.vx, sub.vy) / SUB_SPEED);
  const under = m === 'sub' || m === 'dive' || m === 'home', deep = Math.min(1, sub.y / 900);
  const r = { sea: 0, wind: 0, engine: 0, prop: 0, hum: 0, depth: m === 'dive' ? Math.min(1, diver.y / 900) : deep };
  if (m === 'menu' || m === 'wait' || !G.s) return r;
  if (m === 'ice') { r.wind = 1; r.hum = 0.05; return r; }
  if (!under) return r;
  r.sea = m === 'home' ? 0.35 : m === 'dive' ? 1 : 0.75;
  // The engines idle while someone drives and growl with speed; out on a dive they are far off, inside they hum.
  const run = m === 'sub' || (net && net.helm) ? 0.25 + 0.75 * speed : speed;
  r.engine = run * (m === 'dive' ? 0.3 : m === 'home' ? 0.6 : 1);
  r.prop = speed * (m === 'home' ? 0.4 : 1);
  r.hum = m === 'home' ? 0.8 : m === 'sub' ? 0.25 : 0;
  return r;
}
function soundStep(dt) {
  if (!BED || !AC || AC.state !== 'running') return;
  const r = mix();
  BED.sea.set({ vol: r.sea * 0.7, rate: 1.05 - 0.3 * r.depth });  // deeper and darker the deeper
  BED.wind.set({ vol: r.wind * (0.5 + 0.3 * Math.sin(G.t * 0.7) * Math.sin(G.t * 0.23)) });
  BED.engine.set({ vol: r.engine * 0.55, rate: 0.75 + 0.45 * r.prop });
  BED.hum.set({ vol: r.hum * 0.35 });
  // Now and then, far off: a whale near the surface, the ice overhead, clicks in the deep.
  if ((BED.next -= dt) > 0 || !(r.sea > 0.3)) return;
  BED.next = 7 + Math.random() * 12;
  const ice = underIce(G.mode === 'dive' ? diver.x : sub.x) && (G.mode === 'dive' ? diver.y : sub.y) < 120;
  if (r.depth > 0.6) for (let k = 0; k < 5; k++) tone(1800, 1600, 0.04, 'sine', 0.012, k * 0.11);
  else if (ice && Math.random() < 0.6) {
    if (!(SFX && SFX.play('jaa', { vol: 0.25, rate: 0.6 }))) { tone(140, 95, 1.1, 'sawtooth', 0.012); tone(210, 160, 0.6, 'triangle', 0.01, 0.5); }
  }
  else { tone(180, 120, 2.6, 'sine', 0.02); tone(240, 170, 1.8, 'sine', 0.012, 2.2); }
}
// A phone that turns its screen off or leaves the game goes quiet.
document.addEventListener('visibilitychange', () => {
  if (!AC) return;
  if (document.hidden) AC.suspend(); else AC.resume();
});
function tone(f1, f2, dur, type = 'sine', vol = 0.12, delay = 0) {
  if (!AC) return;
  const t = AC.currentTime + delay, o = AC.createOscillator(), g = AC.createGain();
  o.type = type; o.frequency.setValueAtTime(f1, t); o.frequency.exponentialRampToValueAtTime(f2, t + dur);
  g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.connect(g).connect(AC.destination); o.start(t); o.stop(t + dur + 0.05);
}
function clang() { if (!(SFX && SFX.play('metalli', { vol: 0.8 }))) { tone(140, 60, 0.35, 'square', 0.08); tone(90, 40, 0.5, 'sawtooth', 0.06); } }

// ---------- HUD and cards ----------
const $ = id => document.getElementById(id);
function show(id, on) { $(id).classList.toggle('hidden', !on); }
function toast(t, sec = 1.8) { $('toast').textContent = t; show('toast', true); G.toastT = sec; }
function meter(id, v) {
  const el = $(id);
  el.querySelector('s').style.width = Math.max(0, Math.min(100, v)) + '%';
  el.classList.toggle('low', v < 25);
}
function drawHud() {
  const s = G.s, home = G.mode === 'home', ice = G.mode === 'ice', playing = G.mode === 'sub' || G.mode === 'dive' || ice;
  show('hud', playing || home); show('pad', playing || home); show('home', G.mode === 'sub' || home);
  $('pad').classList.toggle('inside', home || ice);
  // The corner button goes inside from the helm, and from inside straight back to the helm.
  const hb = home ? '⛵' : '🏠';
  if ($('home').textContent !== hb) { $('home').textContent = hb; $('home').setAttribute('aria-label', home ? 'Ruoriin' : 'Sisälle'); }
  if (!s) return;
  meter('mFood', s.m.food); meter('mHealth', s.m.health); meter('mHull', s.m.hull);
  show('mAir', G.mode === 'dive'); show('mWarm', ice);
  if (ice) {
    meter('mWarm', walker.warm);
    $('warmS').textContent = Math.ceil(walker.warm / 100 * WARM) + ' s';
    $('depth').textContent = inStation(walker.x) ? '🏠 suojassa' : '❄️ −30 °C';
    $('depth').className = '';
  } else if (G.mode === 'dive') {
    // v7: the metres left on the hose; the tank gear's air in seconds. v12: the hose no longer wears.
    const onHose = diver.kit === 'hose', ic = onHose ? '➰' : '🫁';
    if ($('airI').textContent !== ic) $('airI').textContent = ic;
    meter('mAir', onHose ? 100 - hose.len / HOSE[s.up.hose] * 100 : diver.air / TANK[s.up.tank] * 100);
    $('airS').textContent = onHose ? Math.max(0, Math.floor(HOSE[s.up.hose] - hose.len)) + ' m' : Math.ceil(diver.air) + ' s';
    const a = airlock();
    $('depth').textContent = '⛵ ' + Math.round(Math.hypot(diver.x - a.x, diver.y - a.y)) + ' m';
    $('depth').className = '';
  } else {
    // v12 (#300): no hull rating any more, only the depth
    $('depth').textContent = '▼ ' + Math.round(sub.y) + ' m' + (G.auto ? ' · 🧭 ' + Math.round(G.auto.left || 0) + ' m' : '');
    $('depth').className = '';
  }
  const g = goalNow().text;
  if (g !== G.lastGoal) { $('goal').textContent = g; G.lastGoal = g; }
  // v12: the crate in hand and the bag (n/BAG) beside the goal
  const counts = {}, mc = myCrate();
  for (const id of G.carry) { const it = itemById(id); if (it) counts[it.k] = (counts[it.k] || 0) + 1; }
  const bag = Object.entries(counts).map(([k, n]) => ICON[k] + n).join(' ');
  $('carry').textContent = (mc ? '📦' + (mc.k === 'romu' ? '' : ICON[mc.k]) + ' ' : '') + (bag ? bag + ' ' : '') + (G.carry.length ? '🎒' + G.carry.length + '/' + BAG : '');
  show('ping', G.mode === 'sub');
  $('ping').classList.toggle('cool', G.pingCd > 0);
  // v12: the harpoon only when it was taken along from the suit room
  show('harp', G.mode === 'dive' && diver.harp);
  $('harp').classList.toggle('cool', G.harpCd > 0);
  let acts = [];
  if (G.mode === 'sub' && Math.hypot(sub.vx, sub.vy) < 2.5) acts = [{ label: '🚶 Sisälle', fn: openHome }];
  if (G.mode === 'dive') {
    const a = airlock();
    if (Math.hypot(diver.x - a.x, diver.y - a.y) < 4.5) acts = [{ label: 'Palaa veneeseen', fn: () => endDive(false) }];
    acts = acts.concat(crateActs());
  }
  // Inside, the room's own actions, once the person stands still in it; v12: a crate in hand or within reach first.
  if (home && !crew.moving && !crew.climbing) acts = homeActs();
  if (ice && !walker.inn && !walker.climbing) {
    if (atHatch()) acts = [{ label: '⬇️ Alas torniin', fn: climbIn }];
    if (nearElder()) acts = [{ label: '🤝 Vaihtokauppa', fn: () => campCard() }];
    acts = acts.concat(crateActs());
  }
  G.acts = acts;
  actButton('act', acts[0]); actButton('act2', acts[1]);
  const room = home && ROOMS.concat(TOWER).find(r => r.id === crew.room), b = ice && bldAt(walker.x), sroom = b && stationRoom(walker.x, walker.fl);
  const rn = room ? room.name + (Math.abs(crew.x - LADDER) < 0.4 ? ' · tikkaat ↕' : '')
    : sroom ? b.name + ' · ' + sroom.name + (b.ladder && Math.abs(walker.x - b.ladder) < 0.5 ? ' · tikkaat ↕' : '')
    : ice && Math.abs(walker.x - CAMP.fire) < 30 ? 'Nomadien leiri' : '';
  if ($('roomName').textContent !== rn) $('roomName').textContent = rn;
  show('roomName', !!rn);
}
// v12 (#300): the crate buttons: let go of the one in hand, or lift the one within reach. The harpoon in hand leaves
// no hand free for a crate.
function crateActs() {
  const mc = myCrate();
  if (mc) return [{ label: '⬇️ Laske laatikko', fn: () => act('drop', [mc.id, ...dropSpot().map((v, i) => i ? r2(v) : v)]) }];
  const c = nearCrate();
  if (!c) return [];
  if (crew.harp) return [{ label: '🔱 Harppuuna kädessä', off: true, fn: () => {} }];
  return [{ label: '📦 Nosta: ' + crateLabel(c), fn: () => act('lift', c.id) }];
}
// Inside SISU: with a crate in hand, the shelf (in the stores) and putting it down; else a crate within reach, then
// the room's own actions.
function homeActs() {
  const mc = myCrate();
  if (mc) return crew.room === 'varasto' ? [shelfFree() >= 0 ? { label: `📦 Hyllyyn (${shelved().length}/${SHELF.length})`, fn: () => act('shelf', mc.id) }
    : { label: '📦 Hylly on täynnä', off: true, fn: () => {} }].concat(crateActs()) : crateActs().concat(roomActs().slice(0, 1));
  return crateActs().concat(roomActs()).slice(0, 2);
}
function actButton(id, a) {
  const el = $(id);
  show(id, !!a);
  if (!a) return;
  if (el.textContent !== a.label) el.textContent = a.label;
  el.disabled = !!a.off;
}
// A card: a title, paragraphs ({t, c}) and buttons ({label, fn, cls, off}); `grid` puts the buttons two to a row.
function card(title, paras, buttons, grid) {
  const el = $('card');
  el.innerHTML = '';
  const txt = document.createElement('div'); txt.className = 'txt';
  if (title) { const h = document.createElement('h2'); h.textContent = title; txt.appendChild(h); }
  for (const p of paras) { const e = document.createElement('p'); e.textContent = p.t; if (p.c) e.className = p.c; txt.appendChild(e); }
  const btns = document.createElement('div'); btns.className = 'btns' + (grid ? ' grid' : buttons.length <= 2 ? ' few' : '');
  for (const b of buttons) {
    const e = document.createElement('button');
    e.textContent = b.label; if (b.cls) e.className = b.cls; if (b.off) e.disabled = true;
    e.addEventListener('click', () => { audio(); b.fn(); });
    btns.appendChild(e);
  }
  el.appendChild(txt); el.appendChild(btns);
  show('panel', true);
  G.paused = true; G.card = '';
}
function closeCard() { show('panel', false); G.paused = false; G.card = ''; }
function storyCard(key, then) {
  const L = LOGS[key];
  card('📓 ' + L.title, L.paras, [{ label: 'Jatka', cls: 'go', fn: () => { closeCard(); if (then) then(); } }]);
}

// ---------- the round ----------
function begin(s) {
  G.s = s; G.carry = []; G.held = {}; G.lastGoal = ''; G.auto = null; G.coast = false;
  // v12: a crate someone held when the page closed falls where they were; the hints the save has earned are on the chart
  for (const c of s.crates) if (c.w === 'held') dropCrate(c, c.hw || 'sub', c.x, c.y);
  relearn();
  sub.x = s.sub.x; sub.y = s.sub.y; sub.dir = sub.face = s.sub.dir || 1; sub.vx = sub.vy = 0;
  // A save from v5 or earlier may have left SISU near the surface where the sea is ice now (v6): down under it.
  while (subHits(sub.x, sub.y) && sub.y < 60) sub.y += 1;
  G.cx = sub.x; G.cy = sub.y; G.sc = subScale(); G.mode = 'sub';
  show('menu', false);
  if (s.flags.end && !s.flags.ch2) chapter2();
}
// Chapter 2 opens once chapter 1 has ended, also for a player coming from v1 with chapter 1 done.
function chapter2() { G.s.flags.ch2 = true; save(); story('ch2'); }
function newGame() { begin(fresh()); save(); story('intro'); }
function menu() {
  G.mode = 'menu';
  const s = load();
  show('jatka', !!s);
  $('uusi').textContent = s ? 'Uusi peli (vanha tallennus poistuu)' : 'Uusi peli';
  $('menuText').textContent = !s ? 'Maailma on hiljentynyt. Sinulla on pieni ydinsukellusvene, kylmä meri ja yksi kysymys: onko ketään muuta jäljellä?'
    : s.flags.end2 ? `Päivä ${s.day}. Luku 2 on päättynyt: Lyra kuuluu yhä syvältä.`
    : s.flags.end ? `Päivä ${s.day}. Luku 2: Nordlys odottaa mannerrinteen alla.`
    : `Päivä ${s.day}. SISU odottaa siinä, mihin jäit.`;
  show('menu', true); show('panel', false); G.paused = false;
  if (s) { sub.x = s.sub.x; sub.y = s.sub.y; G.cx = sub.x; G.cy = sub.y; }
}
$('jatka').addEventListener('click', () => { audio(); begin(load()); });
$('uusi').addEventListener('click', () => { audio(); newGame(); });

// The story's moments (v5): shown on every phone in the game, each closing its own. On the host (or alone) `story`
// shows it and sends it on; `storyFx` is what the moment does to this phone's own person.
const STORY = {
  intro: () => card('Päivä 1', [
    { t: 'Kolme viikkoa sitten radio vaikeni. Ensin hiljenivät uutiset, sitten satamat, sitten kaikki.' },
    { t: 'Sinulla on SISU – pieni ydinkäyttöinen sukellusvene. Reaktori antaa virtaa vuosiksi. Ruoka, lääkkeet ja varaosat loppuvat paljon aiemmin.' },
    { t: 'Tavoite: selviä huomiseen.', c: 'msg' },
    { t: 'Vasen ohjain ajaa. 📡 kuuntelee merta. 🏠 vie sisälle: siellä kävelet huoneesta toiseen syömään, korjaamaan ja nukkumaan, ja ilmalukosta sukellat ulos tutkimaan.', c: 'small' },
    { t: 'Pienet löydöt menevät reppuun. 📦 Laatikoita kannetaan yksi kerrallaan varaston hyllyyn.', c: 'small' }],
  [{ label: 'Aloita', cls: 'go', fn: closeCard }]),
  ch2: () => card('Luku 2: Mannerrinne', [
    { t: 'Nordlys on yhdeksänsadassa metrissä, mannerrinteen alla. Rinne alkaa jäävuorten takaa idässä.' },
    { t: 'Mitä syvemmälle menet, sitä pimeämpää, kylmempää ja oudompaa. K-7:n loki kertoi, mistä Nordlysin jälkiä etsitään: alue on merikartalla.', c: 'msg' },
    { t: 'Rinteelle tarvitset ➰ letkupuvun: säiliöpuku kestää vain ' + TANK_MAX + ' metriä. Pimeässä uivat valokalat tönivät. Mikään ei silti lopeta peliä.', c: 'small' }],
  [{ label: 'Kohti syvyyttä', cls: 'go', fn: closeCard }]),
  end1: () => { tone(200, 2000, 1.5, 'sawtooth', 0.03); card('Viimeinen signaali', [
    { t: 'Vahvistin paikalleen, antenni tornin läpi, viritin 4,2 megahertsiin. Kohinaa... ja sitten ääni.' },
    { t: '»...tässä tutkimusalus Nordlys. Meitä on yhdeksän, mannerrinteen alla. Jos joku kuulee tämän – vastatkaa...»', c: 'log' },
    { t: 'Et olekaan yksin.', c: 'msg' },
    { t: 'Jos vanha maailma on poissa, mitä varten kannattaa jatkaa? Ehkä juuri heitä varten. Luku 1 päättyy.' }],
  [{ label: 'Luku 2', cls: 'go', fn: STORY_ch2 }]); },
  end2: () => { tone(300, 1200, 1.8, 'sine', 0.05); card('Ääniä syvyydestä', [
    { t: 'Muistikortti radioon. Rätinää – ja sitten monta ääntä, yksi kerrallaan.' },
    { t: '»Tässä Lyra. Meitä on yhä yhdeksän. Lähteiden takana on syvänne, ja syvänteessä valoa. Emme tiedä, mitä se on.»', c: 'log' },
    { t: '»Jos kuulet tämän: et ole yksin. Kukaan meistä ei ole.»', c: 'log' },
    { t: 'Jos vanha maailma on poissa, mitä varten kannattaa jatkaa? Toisiamme varten. Luku 2 päättyy.', c: 'msg' }],
  [{ label: 'Takaisin', cls: 'go', fn: closeCard }]); },
  day: () => card(`Päivä ${G.s.day}`, [{ t: DAY_LINES[G.s.day % DAY_LINES.length] },
    { t: G.s.finds.length ? 'Sonar kuulee yöllä uusia pieniä kaikuja – virta on tuonut jotain pohjaan.' : 'Meri on hiljaa.', c: 'msg' }],
  [{ label: 'Nouse', cls: 'go', fn: closeCard }]),
  faint: () => card(`Päivä ${G.s.day}`, [{ t: 'Pyörryt. Heräät punkasta tunteja myöhemmin – kaapin pohjalta löytyy viimeinen näkkileipä.' },
    { t: 'Syö ja hae ruokaa ja lääkkeitä ennen kuin voimat loppuvat.', c: 'msg' }], [{ label: 'Jatka', cls: 'go', fn: closeCard }]),
  breach: () => card('Runko pettää!', [{ t: 'Hälytys ulvoo. Hätäpainolasti nostaa SISUa, ja saumat pitävät juuri ja juuri.' },
    { t: 'Korjaa runko työpajassa varaosilla, ja aja varovammin.', c: 'msg' }], [{ label: 'Jatka', cls: 'go', fn: closeCard }]),
};
function STORY_ch2() { STORY.ch2(); }
function story(k, extra) {
  const m = Object.assign({ t: 'card', k }, extra);
  if (net && net.host) { sendState(); R.send(m); }
  showStory(m);
}
function showStory(m) {
  if (!G.s || !STORY[m.k]) return;
  if (m.k === 'faint') {
    G.carry = [];
    G.mode = 'home'; sub.vx = sub.vy = 0;
    Object.assign(crew, { x: 8, y: UP, dir: -1, suit: false, to: null, moving: false, climbing: false });
    enterRoom(true);
  }
  if (m.k === 'breach') {
    if (m.sub) { sub.x = m.sub[0]; sub.y = m.sub[1]; if (net) net.subT = null; }
    sub.vx = sub.vy = 0;
    // Alone the player is back at the helm (v4); with friends a diver comes in by the airlock, the others stay.
    if (!net && G.mode !== 'sub') { G.carry = []; G.mode = 'sub'; crew.to = null; }
    if (net && (G.mode === 'dive' || G.mode === 'ice')) {
      G.carry = []; G.mode = 'home';
      Object.assign(crew, { x: 11, y: LOW, dir: -1, suit: true, to: null, moving: false, climbing: false });
      enterRoom(true);
    }
    clang();
  }
  STORY[m.k]();
}

// How far a ping reaches: 150 m (v12, #300; 450 m before), a third more once Nordlys's sample bottle is studied (v8).
function pingR() { return PING * lab('pullo', 4 / 3); }
function doPing() {
  if (G.mode !== 'sub' || G.pingCd > 0) return;
  G.ping = { x: sub.x, y: sub.y, t: G.t };
  G.pingCd = 3;
  sfx('kaiku', 0.9, 1250, 900, 0.5, 'sine', 0.14);
  for (const c of contacts()) {
    const d = Math.hypot(c.x - sub.x, c.y - sub.y);
    if (d < pingR()) tone(900, 880, 0.25, 'sine', 0.05, 0.25 + d / 260);
  }
  act('ping');
}
$('ping').addEventListener('click', () => { audio(); doPing(); });

function startDive() {
  // With friends (v5) SISU may be on the move under someone else at the helm: the airlock opens only when it is still.
  if (net && Math.hypot(sub.vx, sub.vy) > 2.5) { toast('SISU liikkuu – odota, että se pysähtyy'); return; }
  // The tank gear goes no deeper than TANK_MAX (v7): below it only the hose suit opens the airlock.
  if (crew.kit !== 'hose' && sub.y > TANK_MAX - 2) {
    toast('Säiliöpuku kestää vain ' + TANK_MAX + ' m. Pue ➰ letkupuku.', 2.4); snd('no'); return;
  }
  const a = airlock();
  const spots = [[a.x, a.y], [sub.x, sub.y + 3.6], [sub.x - sub.dir * 6, sub.y + 3.6], [sub.x, sub.y - 3.4]];
  const p = spots.find(([x, y]) => !diverHits(x, y));
  if (!p) { toast('Ei tilaa ilmalukolle'); return; }
  diver.x = p[0]; diver.y = p[1]; diver.vx = diver.vy = 0; diver.dir = sub.dir;
  diver.kit = crew.kit === 'hose' ? 'hose' : 'tank'; diver.harp = crew.harp;
  diver.air = TANK[G.s.up.tank];
  Object.assign(hose, { pts: [], len: 0 });
  if (!net) sub.vx = sub.vy = 0;
  crew.suit = true; crew.to = null;
  // v12: the bag goes out as it is (goods packed for the nomads stay in it)
  G.asked = {}; G.mode = 'dive'; G.spear = null; G.pending = {};
  sfx('loiskis', 0.7, 300, 120, 0.6, 'sine', 0.06); sfx('kuplat', 0.5);
  save();
  // The first dive with the hose (v7): how the hose works.
  if (diver.kit === 'hose' && !G.s.flags.letku && !G.hoseSaid) {
    G.hoseSaid = true;
    if (!net || net.host) { G.s.flags.letku = true; save(); }
    card('➰ Letku', [
      { t: 'Puku saa letkulla SISUsta ilman, lämmön, sähkön ja radion. Happi ei lopu, eikä syvyys haittaa, mutta letku riittää vain ' + HOSE[G.s.up.hose] + ' metriä.' },
      { t: 'Letku kiertää kulmien takaa, ja kulmat syövät sen pituutta. Pidempi letku tehdään työpajassa.', c: 'msg' }],
    [{ label: 'Selvä', cls: 'go', fn: closeCard }]);
  }
}
// Back through the airlock (v3): the person stands in it, still in the suit. The host counts the haul (v5).
function endDive(blackout) {
  G.mode = 'home';
  Object.assign(crew, { x: 11, y: LOW, dir: -1, suit: true, to: null, moving: false, climbing: false });
  enterRoom(true);
  G.carry = [];
  if (blackout) {
    act('lost', ['sea', r2(diver.x), r2(diver.y)]);
    card('Happi loppui', [{ t: 'Näkökenttä kapenee. Viimeisillä voimilla vedät itsesi ilmalukkoon.' },
      { t: 'Kaikki mukana ollut jäi mereen. Löydöt odottavat yhä paikoillaan.', c: 'msg' }],
    [{ label: 'Jatka', cls: 'go', fn: closeCard }]);
    return;
  }
  act('home');
}
// The haul `who` holds goes into the stores (on the host, or alone): the text to show them.
function bank(who) {
  const s = G.s, counts = {};
  let extra = '';
  for (const id of Object.keys(G.held)) {
    if (G.held[id] !== who) continue;
    delete G.held[id];
    const it = itemById(id);
    if (it && it.k === 'kala') { s.inv.kala = (s.inv.kala || 0) + 1; counts.kala = (counts.kala || 0) + 1; continue; }
    // v12: goods taken from the stores to trade and brought back go back where they were
    if (id.startsWith('pack:')) { unpackGood(id); continue; }
    if (!it || s.got[id]) continue;
    s.got[id] = true;
    counts[it.k] = (counts[it.k] || 0) + 1;
    if (it.site !== 'find') s.flags[it.site] = true;
    // The Nordlys hose reel and Lyra's lamp are upgrades as found; one already bought pays two spare parts instead.
    // v7: the Nordlys find is a hose reel, a hose level.
    const up = { saili: 'hose', valo: 'lamp' }[it.k];
    if (up) {
      if (COST[up][s.up[up] + 1] !== undefined) { s.up[up]++; extra = up === 'hose' ? ` · letku ${HOSE[s.up.hose]} m` : ' · valo kirkkaampi'; }
      else s.inv.osat += 2;
      continue;
    }
    const k = it.k === 'osa' ? 'osat' : it.k;
    s.inv[k] = (s.inv[k] || 0) + 1;
  }
  s.finds = s.finds.filter(f => !s.got[f.id]);
  save();
  const got = Object.entries(counts).map(([k, n]) => ICON[k] + ' ' + n).join('  ');
  // v8: where the new things go
  if (counts.nayte) extra += ' · vie labraan';
  else if (counts.kala && s.inv.kala >= 2) extra += ' · paista keittiössä';
  return got ? 'Kotona: ' + got + extra : 'Takaisin kotona';
}
// Everything that changes the shared game goes through act (v5): alone or on the host it is done at once (`doAct`);
// a friend's phone asks the host, which does it in the order the asks arrive (the first one wins) and answers.
// v11 (#221): each answer's sound from the library, with the old beep for when it did not play.
const SND = { eat: ['onnistui', 500, 650, 0.2, 'triangle', 0.07], med: ['onnistui', 600, 800, 0.2, 'triangle', 0.07],
  up: ['nousu', 400, 800, 0.3, 'triangle', 0.08], got: ['valinta', 700, 1100, 0.15, 'triangle', 0.08],
  log: ['valinta', 500, 500, 0.4, 'triangle', 0.06], home: ['valinta', 500, 700, 0.2, 'triangle', 0.08],
  no: ['virhe', 300, 220, 0.15, 'square', 0.04] };
function snd(k) { const [name, ...beep] = SND[k]; sfx(name, 0.7, ...beep); }
function me() { return net ? R.me : 'me'; }
function act(a, arg) {
  // Where this person stands goes with the ask, so the host judges it from where they are now.
  if (net && !net.host) { R.send({ t: 'do', a, arg, p: mine() }); return; }
  answer(doAct(me(), a, arg));
}
// What the host's answer means on the phone that asked.
function answer(r) {
  if (!r) return;
  if (r.got && G.mode !== 'sub') {
    G.carry.push(r.got); const it = itemById(r.got);
    if (it && !r.quiet) toast('+ ' + ICON[it.k] + ' ' + (it.sample ? SAMPLES[it.sample].name : NAME[it.k]), 1.2);
  }
  if (r.gone) G.carry = G.carry.filter(id => !r.gone.includes(id));
  if (r.say) toast(r.say, r.sec || 1.8);
  if (r.snd === 'clang') clang(); else if (SND[r.snd]) snd(r.snd);
  if (r.helm && G.mode === 'home') closeHome();
  if (r.log) storyCard(r.log, r.hint ? () => toast('🗺️ Uusi alue merikartalla', 2.2) : null);
  if (r.radio) radioCard();
  if ('up' in r && G.card === 'up') upgradeCard(r.up);
  if (r.studied) studiedCard(r.studied);
  if (r.traded != null) toldCard(r.traded);
  if (r.store && G.card === 'store') storeCard(r.store);
}
function doAct(who, a, arg) {
  const s = G.s, i = s.inv, m = s.m;
  switch (a) {
    // v12 (#300): food, medicine and spare parts come from the loose stores and the shelved crates (`use`)
    case 'eat':
      if (!stock('ruoka')) return { say: 'Ruoka loppui juuri.', snd: 'no' };
      if (m.food > 95) return { say: 'Vatsa on jo täynnä.', snd: 'no' };
      use('ruoka'); m.food = Math.min(100, m.food + 35); m.health = Math.min(100, m.health + 5); save();
      return { say: 'Lämmin ateria. Olo paranee.', snd: 'eat' };
    // v8 (#151): the fish from the harpoon, two to a ration.
    case 'cook': {
      const n = Math.floor((i.kala || 0) / 2);
      if (!n) return { say: 'Yhdestä kalasta ei tule ateriaa.', snd: 'no' };
      i.kala -= n * 2; i.ruoka += n; save();
      return { say: `Paistoit kalat: +${n} 🥫 annos${n > 1 ? 'ta' : ''}`, snd: 'eat' };
    }
    // A fish the harpoon hit (arg [school, fish]): the first one to ask gets it, and it is carried home like a find.
    case 'fish': {
      const [n, k] = Array.isArray(arg) ? arg.map(Number) : [];
      if (!SCHOOLS[n] || !(k >= 0 && k < SCHOOLS[n][4])) return null;
      const c = s.caught[n] = s.caught[n] || [];
      if (c.includes(k)) return null;
      if (heldCount(who) >= BAG) return { say: '🎒 Reppu on täynnä', snd: 'no' };
      c.push(k); save();
      const id = 'kala:' + s.day + ':' + n + ':' + k;
      G.held[id] = who;
      return { got: id, snd: 'got' };
    }
    // A sample studied in the lab (v8): its note, and its help from now on.
    case 'study': {
      if (!SAMPLES[arg] || !unstudied().includes(arg)) return null;
      s.lab[arg] = true; save();
      return { studied: arg, snd: 'up' };
    }
    case 'med':
      if (!stock('laake')) return { say: 'Lääkkeet loppuivat juuri.', snd: 'no' };
      if (m.health > 95) return { say: 'Kunto on jo hyvä.', snd: 'no' };
      use('laake'); m.health = Math.min(100, m.health + 40); save();
      return { say: 'Lääke auttaa.', snd: 'med' };
    case 'fix':
      if (!stock('osa')) return { say: 'Varaosat loppuivat juuri.', snd: 'no' };
      if (m.hull > 95) return { say: 'Runko on jo kunnossa.', snd: 'no' };
      use('osa'); m.hull = Math.min(100, m.hull + 35); save();
      return { say: 'Hitsaat vuotavan sauman umpeen.', snd: 'clang' };
    case 'up': {
      const u = s.up, cost = COST[arg] && COST[arg][u[arg] + 1];
      if (!cost || !use('osa', cost)) return { up: null, say: 'Varaosat eivät riitä.', snd: 'no' };
      u[arg]++; save();
      return { snd: 'up', up: arg === 'tank' ? `Happea riittää nyt ${TANK[u.tank]} sekuntia.`
        : arg === 'hose' ? `Letku yltää nyt ${HOSE[u.hose]} metriin.` : 'Valonheitin näkee nyt kauemmas.' };
    }
    // v12 (#300): crates. Lifted only with both hands free; let go of where the holder's phone says.
    case 'lift': {
      const c = crateById(String(arg));
      if (!c || !['sea', 'sub', 'ice'].includes(c.w)) return null;
      if (heldBy(who)) return { say: 'Kädet ovat jo täynnä', snd: 'no' };
      const w = c.w;
      c.w = 'held'; c.by = who; c.hw = w; c.f = 0;
      wake(w, c.x); save();
      return { say: crateText(c), snd: 'got', sec: 1.4 };
    }
    case 'drop': {
      const [id, w, x, y] = Array.isArray(arg) ? arg : [];
      const c = crateById(String(id));
      if (!c || c.w !== 'held' || c.by !== who || !['sea', 'sub', 'ice'].includes(w) || !isFinite(+x) || !isFinite(+y)) return null;
      dropCrate(c, w, +x, +y); save();
      return { snd: 'home' };
    }
    case 'shelf': {
      const c = crateById(String(arg)), at = net && people().find(p => p.id === who);
      if (!c || c.w !== 'held' || c.by !== who) return null;
      if (at && at.room !== 'varasto') return { say: 'Hylly on varastossa', snd: 'no' };
      const n = shelfFree();
      if (n < 0) return { say: 'Hylly on täynnä', snd: 'no' };
      delete c.by; c.w = 'shelf'; c.slot = n; c.f = 0; save();
      return { say: 'Hyllyyn: ' + crateText(c), snd: 'up', sec: 1.6 };
    }
    case 'unshelf': {
      const c = crateById(String(arg));
      if (!c || c.w !== 'shelf') return null;
      if (heldBy(who)) return { say: 'Kädet ovat jo täynnä', snd: 'no' };
      c.w = 'held'; c.by = who; c.hw = 'sub'; delete c.slot; save();
      return { say: crateText(c), snd: 'got', sec: 1.4 };
    }
    // Goods from the stores into the bag, for the nomads.
    case 'pack': {
      if (!GOODS.includes(arg)) return null;
      if (heldCount(who) >= BAG) return { say: '🎒 Reppu on täynnä', snd: 'no', store: 'Reppu on täynnä.' };
      if (!use(arg)) return { say: 'Varasto on tyhjä', snd: 'no' };
      const id = 'pack:' + arg + ':' + (G.packN = (G.packN || 0) + 1);
      G.held[id] = who; s.pack[arg] = (s.pack[arg] || 0) + 1; save();
      return { got: id, quiet: 1, snd: 'got', store: '🎒 Reppuun ' + ICON[arg] };
    }
    case 'trade': return trade(who);
    case 'radio':
      if (i.kortti && !s.flags.end2) { i.kortti = 0; s.flags.end2 = true; save(); story('end2'); return null; }
      if (!s.flags.end && i.vahvistin && i.antenni) { s.flags.end = s.flags.ch2 = true; save(); story('end1'); return null; }
      return { radio: 1 };
    case 'sleep': {
      // With friends everyone sleeps at once: the night comes when all of them are in the bunk room.
      const away = people().filter(p => !(p.mode === 'home' && p.room === 'punkka')).map(p => p.name);
      if (away.length) return { say: 'Kaikki punkkaan: odotetaan ' + away.join(', '), sec: 2.6 };
      sleep(); return null;
    }
    case 'helm': {
      // With friends the helm is taken in the control room (alone the ⛵ corner button goes straight there, as in v4).
      const at = net && people().find(p => p.id === who);
      if (at && at.room !== 'ohjaamo') return { say: 'Ruoriin pääsee ohjaamosta', snd: 'no' };
      if (net && net.helm && net.helm !== who && present(net.helm)) return { say: nameOf(net.helm) + ' on ruorissa', snd: 'no' };
      if (net) { net.helm = who; net.subT = null; }
      // the one at the helm now drives; SISU glides on under them to a stop unless they steer
      if (G.auto) { stopAuto(); return { helm: 1, say: '🧭 Autopilotti pois: ruori on käsissäsi', sec: 2 }; }
      return { helm: 1 };
    }
    case 'unhelm': if (net && net.helm === who) { net.helm = null; stopSub(); } return null;
    // v9: the autopilot, set and stopped from the chart; taking the helm stops it too.
    case 'auto': {
      const at = net && people().find(p => p.id === who);
      if (at && at.room !== 'kartta') return { say: 'Autopilotti asetetaan navigointihuoneesta', snd: 'no' };
      if (net && net.helm && net.helm !== who && present(net.helm) && people().some(p => p.id === net.helm && p.mode === 'sub'))
        return { say: nameOf(net.helm) + ' on ruorissa', snd: 'no' };
      return startAuto(String(arg));
    }
    case 'autostop': if (G.auto) { stopAuto(); stopSub(); } return { say: '🧭 Autopilotti pois', snd: 'home' };
    case 'take': {
      const it = allItems().find(t => t.id === arg);
      if (!it || s.got[it.id]) return null;
      if (G.held[it.id]) return G.held[it.id] === who ? null : { say: nameOf(G.held[it.id]) + ' ehti ensin', sec: 1.2 };
      if (it.k === 'loki') {
        s.got[it.id] = true; s.flags[it.log] = true;
        // v12 (#300): a log that points somewhere puts its search area on the chart
        const hint = LOG_HINT[it.log];
        if (hint) learn(hint);
        save(); return { log: it.log, snd: 'log', hint: hint ? 1 : 0 };
      }
      if (heldCount(who) >= BAG) return { say: '🎒 Reppu on täynnä', snd: 'no' };
      G.held[it.id] = who;
      return { got: it.id, snd: 'got' };
    }
    case 'home': return { say: bank(who), snd: 'home' };
    case 'lost': {
      for (const id of Object.keys(G.held)) if (G.held[id] === who) {
        // v12: goods packed from the stores are lost with the rest
        if (id.startsWith('pack:')) { const k = id.split(':')[1]; s.pack[k] = Math.max(0, (s.pack[k] || 0) - 1); }
        delete G.held[id];
      }
      const c = heldBy(who), [w, x, y] = Array.isArray(arg) ? arg : [];
      if (c) dropCrate(c, ['sea', 'ice'].includes(w) ? w : c.hw || 'sub', isFinite(+x) ? +x : c.x, isFinite(+y) ? +y : c.y);
      m.health = Math.max(5, m.health - 25); save();
      return null;
    }
    case 'ping':
      for (const c of contacts()) if (Math.hypot(c.x - sub.x, c.y - sub.y) < pingR()) s.known[c.id] = s.heard[c.id] = true;
      chartSee(sub.x, sub.y, pingR());  // v9: the echo draws the sea floor round SISU on the chart
      s.flags.pinged = true; save();
      return null;
    case 'dmg': m.hull -= Math.max(0, Math.min(30, +arg || 0)); return null;
  }
  return null;
}
for (const [id, n] of [['act', 0], ['act2', 1]]) $(id).addEventListener('click', () => {
  audio();
  const a = G.acts && G.acts[n];
  if (a && !a.off && !G.paused) a.fn();
  drawHud();
});

// ---------- home: the lit inside of SISU, walked as a person (v3) ----------
function openHome() {
  if (G.mode !== 'sub') return;
  sub.vx = sub.vy = 0;
  G.mode = 'home';
  act('unhelm');
  Object.assign(crew, { x: 0.6, y: UP, dir: 1, to: null, moving: false, climbing: false });  // up from the helm
  enterRoom(true);
  if (!G.s.flags.koti) {
    G.s.flags.koti = true; save();
    card('SISU sisältä', [
      { t: 'Napauta huonetta, niin kävelet sinne. Voit kävellä myös ohjaimella. Tikkaat vievät kerrosten välillä.' },
      { t: 'Yläkerta: keittiö, ohjaamo (ruori ja radio), labra ja kartat, punkka ja ylhäällä torni. Alakerta: reaktori, sähkö, työpaja, varasto, sukelluspuvut ja ilmalukko.' },
      { t: 'Sukeltamaan: puku päälle ja ulos ilmalukosta. ⛵ vie takaisin ruoriin.', c: 'msg' }],
    [{ label: 'Selvä', cls: 'go', fn: closeCard }]);
  }
}
function closeHome() { closeCard(); G.mode = 'sub'; crew.to = null; save(); }
// To the helm (v5): with friends only one drives, so the host is asked first; `answer` then calls closeHome.
function toHelm() {
  if (net && crew.room !== 'ohjaamo') { toast('Kävele ohjaamoon: ruori on siellä'); snd('no'); return; }
  act('helm');
}
$('home').addEventListener('click', () => { audio(); if (G.mode === 'home') toHelm(); else openHome(); drawHud(); });
// The room the person stands in; a room with nothing to do says something once each time they come in.
function enterRoom(quiet) {
  const r = roomOf(crew.x, crew.y), id = r ? r.id : '';
  if (id === crew.room && !quiet) return;
  crew.room = id;
  if (!quiet && r && r.say) toast(r.say, 2.2);
}
// What can be done in the room the person stands in: one or two actions, the first on the big button.
function roomActs() {
  const s = G.s, i = s.inv;
  switch (crew.room) {
    // v8: two fish make a ration on the stove.
    case 'keittio': return [{ label: `🍲 Syö annos (${stock('ruoka')})`, off: !stock('ruoka') || s.m.food > 95, fn: () => act('eat') }]
      .concat(i.kala ? [{ label: `🐟 Paista kalat (${i.kala})`, off: i.kala < 2, fn: () => act('cook') }] : []);
    // v12 (#300): the stores' card (the shelf, goods into the bag) and medicine
    case 'varasto': return [{ label: '🗄️ Varasto', fn: () => storeCard() },
      { label: `💊 Ota lääke (${stock('laake')})`, off: !stock('laake') || s.m.health > 95, fn: () => act('med') }];
    case 'paja': return [{ label: '🔧 Korjaa runko (⚙️ 1)', off: !stock('osa') || s.m.hull > 95, fn: () => act('fix') },
      { label: '🛠️ Parannukset', fn: () => upgradeCard() }];
    // v8: the way out onto the ice is the tower's hatch, so the helm stays here when SISU lies surfaced (#151).
    case 'ohjaamo':
      return [net && net.helm && net.helm !== me() && present(net.helm)
      ? { label: `⛵ ${nameOf(net.helm)} ruorissa`, off: true, fn: () => {} } : { label: '⛵ Ruoriin', fn: toHelm },
      { label: s.flags.end2 ? '📻 Radio: Lyra' : i.kortti ? '📻 Soita muistikortti' : s.flags.end ? '📻 Radio: Nordlys'
        : i.vahvistin && i.antenni ? '📻 Korjaa radio' : '📻 Radio (kohinaa)', fn: radio }];
    // v9 (#160): the navigation room's chart first, the lab second; the logbook (and with friends the host's way back
    // to the room) are in the lab's card.
    case 'kartta': return [{ label: '🗺️ Merikartta', fn: openChart },
      { label: `🔬 Laboratorio${unstudied().length ? ` (${unstudied().length})` : ''}`, fn: labCard }];
    case 'torni': return Math.abs(crew.y - TOP) > 0.05 ? [] : surfaced() ? [{ label: '🧗 Tornista jäälle', fn: goIce }]
      : [{ label: '🔒 Luukku: SISU on veden alla', off: true, fn: () => {} }];
    case 'punkka': return [{ label: '🛏️ Nuku yön yli', fn: () => act('sleep') }];
    // v7: two suits, the tank gear (to TANK_MAX) and the hose suit (as deep as SISU, as far as the hose).
    case 'puvut': {
      const wear = kit => () => {
        crew.suit = true; crew.kit = kit; sfx('naksu', 0.8, 300, 450, 0.2, 'triangle', 0.06);
        toast(kit === 'hose' ? `➰ Letkupuku: ilma letkusta, letkua ${HOSE[s.up.hose]} m` : `🤿 Säiliöpuku: happea ${TANK[s.up.tank]} s, enintään ${TANK_MAX} m`, 2.2);
      };
      // v12 (#300): the harpoon is its own gear, taken along once the suit is on; with it in hand no crate can be carried
      if (crew.suit) return [crew.harp ? { label: '🔱 Jätä harppuuna', fn: () => { crew.harp = false; sfx('naksu', 0.8, 400, 250, 0.2, 'triangle', 0.06); toast('Harppuuna telineeseen.', 1.4); } }
        : { label: '🔱 Ota harppuuna', off: !!myCrate(), fn: () => { crew.harp = true; sfx('naksu', 0.8, 300, 450, 0.2, 'triangle', 0.06); toast('🔱 Harppuuna mukaan: kädet eivät riitä laatikolle', 2.2); } },
        { label: '🧥 Riisu puku', fn: () => { crew.suit = false; crew.harp = false; sfx('naksu', 0.8, 400, 250, 0.2, 'triangle', 0.06); toast('Puku naulakkoon.', 1.4); } }];
      return [{ label: '🤿 Säiliöpuku', fn: wear('tank') }, { label: '➰ Letkupuku', fn: wear('hose') }];
    }
    case 'ilmalukko': return [crew.suit ? { label: '🌊 Sukella ulos', fn: startDive }
      : { label: '🤿 Pue ensin puku', off: true, fn: () => {} }];
  }
  return [];
}
// A tap inside SISU, in hull coordinates: the person walks there, by the ladder when it is on the other deck.
// v8: a tap in the tower climbs to its top, under the hatch (deck -1).
function walkTo(lx, ly) {
  const r = roomOf(lx, ly);
  if (r === TOWER && ly > -5.4) {
    crew.to = { x: LADDER, deck: -1 }; crew.mark = { x: LADDER, y: TOP, t: G.t };
    return true;
  }
  if (lx < -14.2 || lx > 14.6 || ly < -2.6 || ly > 2.6) return false;
  const deck = r ? r.deck : ly > 0 ? 1 : 0, [a, b] = DECK_X[deck];
  crew.to = { x: Math.max(a, Math.min(b, lx)), deck };
  crew.mark = { x: crew.to.x, y: deck ? LOW : UP, t: G.t };
  return true;
}
// Where the feet stand on each level: the tower's top, the upper deck, the lower deck.
function level(deck) { return deck < 0 ? TOP : deck ? LOW : UP; }
function stepCrew(dt) {
  const c = crew, x0 = c.x, y0 = c.y;
  const at = v => Math.abs(c.y - v) < 0.01, mid = !at(TOP) && !at(UP) && !at(LOW);
  const toward = (v, goal, sp) => v + Math.sign(goal - v) * Math.min(sp * dt, Math.abs(goal - v));
  if (input.x || input.y) c.to = null;  // the stick takes over from a tap
  if (c.to) {
    const fy = level(c.to.deck);
    if (Math.abs(c.y - fy) > 0.01) {
      if (!mid && Math.abs(c.x - LADDER) > 0.01) c.x = toward(c.x, LADDER, WALK);
      else { c.x = LADDER; c.y = toward(c.y, fy, CLIMB); }
    } else if (Math.abs(c.x - c.to.x) > 0.01) c.x = toward(c.x, c.to.x, WALK);
    else c.to = null;
  } else if (at(TOP) && input.y < -0.6 && -input.y > Math.abs(input.x)) {
    // v8: at the top of the tower the stick pushed on up opens the hatch, out onto the ice (v6 did this from the deck).
    if (surfaced()) { goIce(); return; }
    if (G.iceCd <= 0) { toast('Luukku ei aukea: SISU on veden alla', 1.6); G.iceCd = 2; }
  } else if (mid || (Math.abs(c.x - LADDER) < 0.4 && Math.abs(input.y) > 0.5 && Math.abs(input.y) > Math.abs(input.x))) {
    // On the ladder the stick climbs, from the lower deck up to the tower's top; pushed sideways halfway between the
    // decks, the person climbs on to the nearer one.
    c.x = LADDER;
    const dir = Math.abs(input.y) > 0.3 ? Math.sign(input.y) : Math.abs(input.x) > 0.5 && c.y > UP ? (c.y > (UP + LOW) / 2 ? 1 : -1) : 0;
    if (dir) c.y = Math.max(TOP, Math.min(LOW, c.y + dir * CLIMB * dt));
  } else if (input.x && !at(TOP)) {
    const [a, b] = DECK_X[c.y > 1 ? 1 : 0];
    // The inside is drawn mirrored when SISU faces left: right on the stick is right on the screen either way.
    c.x = Math.max(a, Math.min(b, c.x + input.x * (sub.dir < 0 ? -1 : 1) * WALK * dt));
  }
  if (c.y < TOP + 0.01) c.y = TOP; else if (c.y > LOW - 0.01) c.y = LOW; else if (Math.abs(c.y - UP) < 0.01) c.y = UP;
  // v12 (#300): a loose crate on the deck is in the way: the person stops at it (and can lift it, or walk round by another way)
  if (c.y === UP || c.y === LOW) {
    const nx = crateBlock(x0, c.x, c.y);
    if (Math.abs(nx - c.x) > 1e-6) {
      c.x = nx; c.to = null;
      if (G.iceCd <= 0) { toast('📦 Laatikko on tiellä', 1.2); G.iceCd = 1.5; }
    }
  }
  const dx = c.x - x0, dy = c.y - y0;
  if (Math.abs(dx) > 1e-4) c.dir = Math.sign(dx);
  c.moving = Math.abs(dx) > 1e-4 || Math.abs(dy) > 1e-4 || !!c.to;
  c.climbing = !at(TOP) && !at(UP) && !at(LOW);
  c.walkT += Math.abs(dx) + Math.abs(dy);
  enterRoom();
}
function upgradeCard(msg) {
  const s = G.s, u = s.up;
  const row = (key, name, now, next) => {
    const cost = COST[key][u[key] + 1];
    return cost ? { label: `${name}: ${now} → ${next} (⚙️ ${cost})`, off: stock('osa') < cost, fn: () => act('up', key) }
      : { label: `${name}: ${now} (täysi)`, off: true, fn: () => {} };
  };
  // v12 (#300): the hull is no longer reinforced and the hose needs no guides
  const paras = [{ t: `Varaosia: ⚙️ ${stock('osa')}`, c: 'small' }];
  if (msg) paras.push({ t: msg, c: 'msg' });
  card('🛠️ Työpaja', paras, [
    row('tank', '🫁 Happisäiliö', TANK[u.tank] + ' s', TANK[u.tank + 1] + ' s'),
    row('hose', '➰ Letku', HOSE[u.hose] + ' m', HOSE[u.hose + 1] + ' m'),
    row('lamp', '🔦 Valonheitin', 'tavallinen', 'kirkas'),
    { label: 'Takaisin', cls: 'go', fn: closeCard }]);
  G.card = 'up';
}
// The navigation room's logbook: every log read so far, to read again.
function logBook() {
  const s = G.s, read = Object.keys(LOGS).filter(k => ITEMS.concat(ICE_ITEMS).some(it => it.log === k && s.got[it.id]));
  card('📓 Lokikirja', [
    { t: read.length ? 'Luetut viestit – napauta lukeaksesi uudelleen.' : 'Lokikirja on vielä tyhjä. Löytämäsi viestit kirjataan tänne.', c: 'small' }],
  read.map(k => ({ label: LOGS[k].title, fn: () => storyCard(k, logBook) })).concat([{ label: 'Takaisin', cls: 'go', fn: closeCard }]),
  read.length > 2);
}
// The lab (v8, #151): the samples brought home and not yet studied, in the order the story finds them.
function unstudied() {
  const s = G.s;
  return ITEMS.concat(ICE_ITEMS).filter(it => it.k === 'nayte' && s.got[it.id] && !s.lab[it.sample]).map(it => it.sample);
}
function labCard() {
  const s = G.s, todo = unstudied(), done = Object.keys(SAMPLES).filter(k => s.lab[k]);
  const paras = [{ t: todo.length ? 'Näytteet odottavat mikroskoopin alla. Napauta tutkiaksesi.'
    : done.length ? 'Ei uusia näytteitä. Etsi lisää 🧪 sukelluksilta ja jäältä.' : 'Laboratorio on tyhjä. Tuo 🧪 näytteitä sukelluksilta ja jäältä.', c: 'small' }];
  for (const k of done) paras.push({ t: '✓ ' + SAMPLES[k].name + ': ' + SAMPLES[k].gain, c: 'small' });
  card('🔬 Laboratorio', paras,
    todo.map(k => ({ label: '🧪 Tutki: ' + SAMPLES[k].name, fn: () => act('study', k) }))
      .concat([{ label: '📓 Lokikirja', fn: logBook }], net && net.host ? [{ label: '👥 Huoneeseen', fn: toRoom }] : [],
        [{ label: 'Takaisin', cls: 'go', fn: closeCard }]));
  G.card = 'lab';
}
function studiedCard(k) {
  const S = SAMPLES[k];
  card('🔬 ' + S.name, S.paras.concat([{ t: 'Tästä lähtien: ' + S.gain + '.', c: 'msg' },
    { t: `${Object.keys(G.s.lab).length} / ${Object.keys(SAMPLES).length} näytettä tutkittu.`, c: 'small' }]),
  [{ label: 'Jatka', cls: 'go', fn: labCard }]);
}
