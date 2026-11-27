'use strict';
// Seittisankari v5 (#565): the story, Tarina. Eight chapters, each a short list of missions
// (round.js runs them), a card at each chapter's start and end, and one radio line as each mission
// starts. Chapters 5–8 (`lim`) give each crook or rescue mission a time limit (LIMITS in round.js).
// Progress: `ai-pelit:seittisankari:tarina` = { done: chapters finished, best: { chapter: s },
// cur: the chapter being played { ch, step, gt, ct, g } or null }, and the hero's spot in the
// story under `tarina-kierros` = { h }. The free city's saves are never touched here.

const WHO = {
  K: { n: 'Komisario Kallio', c: '#4d9bff' },
  V: { n: 'Varjo', c: '#a46bff' },
  S: { n: 'Seittisankari', c: '#1fb5a8' },
};
// steps: { k: mission kind, say: [who, radio line], near / high: the first chapter's roofs,
//   cut: a cutscene's lines played as the mission starts (Eero: "Voisi olla chapterin sisälläkin") }
const STORY = [
  { name: 'Ensimmäinen ilta',
    intro: [['K', 'Hei, sinä siellä seinällä! Olen komisario Kallio.'], ['K', 'Kaupunki tarvitsee apua. Näytä, mitä osaat.']],
    steps: [
      { k: 'katto', near: 1, say: ['K', 'Kiipeä tuon matalan talon katolle.'] },
      { k: 'katto', say: ['K', 'Hienoa! Heilu seitillä merkitylle katolle.'] },
      { k: 'katto', high: 1, say: ['K', 'Vielä korkealle! Kokeile Vetoa.'] },
    ],
    outro: [['K', 'Sinusta on apua. Pidä radio päällä.'], ['S', 'Selvä, komisario.']] },
  { name: 'Kattovarkaat',
    intro: [['K', 'Rosvot varastavat kattojen ilmastointikoneita!'], ['K', 'Ota heidät kiinni seitillä.']],
    steps: [
      { k: 'rosvot', say: ['K', 'Kolme rosvoa katolla. Tähtää Vedolla!'] },
      { k: 'pakenevat', say: ['K', 'Nämä loikkivat katolta toiselle. Ole nopea!'],
        cut: [['K', 'Nuo rosvot ovat nopeampia.'], ['K', 'Ne loikkaavat pois, kun tulet lähelle.']] },
    ],
    outro: [['V', 'Joku sotkee suunnitelmani…'], ['V', 'Olen Varjo. Me tapaamme vielä, sankari.']] },
  { name: 'Pankkiryöstö',
    intro: [['K', 'Pankkiin murtauduttiin katon kautta!'], ['K', 'Rosvot ovat vielä katolla.']],
    steps: [
      { k: 'rosvot', say: ['K', 'Pankin katolle, nopeasti!'] },
      { k: 'auto', say: ['K', 'Yksi pääsi autoon! Pysäytä se.'],
        cut: [['K', 'Hälytys! Rosvojen auto kiihdyttää pois.'], ['S', 'Ei se minulta pääse.']] },
      { k: 'paketti', say: ['K', 'Rahasäkki jäi katolle. Vie se pankkiin.'] },
    ],
    outro: [['K', 'Rahat ovat tallessa.'], ['K', 'Rosvot puhuivat jostain Varjosta.'], ['S', 'Varjo… kuka hän on?']] },
  { name: 'Viesti tornissa',
    intro: [['V', 'Haluatko tavata minut, sankari?'], ['V', 'Jätin sinulle viestin tornin huipulle.']],
    steps: [
      { k: 'torni', say: ['K', 'Ole varovainen. Se voi olla ansa.'] },
      { k: 'putoava', say: ['V', 'Viesti oli harhautus! Joku roikkuu katolta…'],
        cut: [['V', 'Ha! Tornissa ei ollut mitään.'], ['V', 'Mutta katso tuonne. Joku roikkuu katon reunalla…']] },
      { k: 'auto', say: ['K', 'Varjon auto pakenee! Pysäytä se.'] },
    ],
    outro: [['K', 'Autossa oli lappu: "Seuraavaksi ikkunanpesijät."'], ['S', 'Mitä se tarkoittaa?']] },
  { name: 'Pelastus', lim: 1,
    intro: [['K', 'Varjon miehet katkaisivat ikkunanpesijöiden nostimen!'], ['K', 'Pesijät roikkuvat seinillä. Nyt on kiire!']],
    steps: [
      { k: 'pelasta', say: ['K', 'Mene pesijän luo, ennen kuin ote lipeää!'] },
      { k: 'putoava', say: ['K', 'Yksi roikkuu katon reunalta! Ota kiinni!'] },
      { k: 'pelasta', say: ['K', 'Vielä yksi seinällä! Ehdi ajoissa.'] },
    ],
    outro: [['K', 'Hyvää työtä. Mutta Varjo on yhä vapaana.'], ['V', 'Huomenna lähden kaupungista. Ilmateitse.']] },
  { name: 'Helikopteri', lim: 1,
    intro: [['K', 'Varjon jengi lastaa saalista helikopteriin!'], ['K', 'Pysäytä ensin katon rosvot.']],
    steps: [
      { k: 'pakenevat', say: ['K', 'Rosvot loikkivat kopteria kohti! Pysäytä!'] },
      { k: 'heli', say: ['K', 'Kopteri nousi! Mene ylös ja tähtää siihen.'],
        cut: [['K', 'Liian myöhään, kopteri nousee!'], ['S', 'Ei ole myöhään. Seitti kantaa.']] },
    ],
    outro: [['K', 'Kopterissa oli vain Varjon apureita.'], ['V', 'Sinä et saa minua koskaan kiinni.']] },
  { name: 'Jengin ilta', lim: 1,
    intro: [['K', 'Koko jengi on liikkeellä tänä iltana.'], ['V', 'Jätin katoille pieniä yllätyksiä. Tik tak!']],
    steps: [
      { k: 'pommit', say: ['K', 'Kolme pommia katoilla! Pura ne!'] },
      { k: 'auto', say: ['K', 'Pakoauto kaduilla!'] },
      { k: 'heli', say: ['K', 'Ja vielä kopteri!'],
        cut: [['V', 'Kopterini hakee jengini. Hyvästi!']] },
    ],
    outro: [['K', 'Jengi on telkien takana.'], ['K', 'Varjo on nähty tornin huipulla.'], ['S', 'Nyt loppuu Varjon peli.']] },
  { name: 'Huipulla', lim: 1,
    intro: [['V', 'Tulit siis. Olet sinnikäs.'], ['V', 'Mutta minun helikopterini odottaa jo.']],
    steps: [
      { k: 'torni', say: ['K', 'Tornin huipulle! Varjo on siellä.'] },
      { k: 'boss', say: ['V', 'Hyvästi, sankari! Ha ha!'],
        cut: [['V', 'Myöhästyit, sankari.'], ['S', 'Et pääse mihinkään, Varjo.'], ['V', 'Ota kiinni, jos osaat!']] },
    ],
    outro: [['V', 'Ei! Minun helikopterini!'], ['K', 'Varjo on kiinni. Kaupunki on turvassa!'], ['S', 'Hyvää yötä, kaupunki.']] },
];
// What Kallio says when a mission's time runs out (nobody gets hurt).
const FAIL_SAY = {
  rosvot: 'Rosvot pääsivät pakoon katolta.',
  auto: 'Auto pääsi karkuun. Yritetään uudelleen!',
  heli: 'Helikopteri ehti pois. Yritetään uudelleen!',
  pelasta: 'Miehemme saivat pesijän verkkoon. Ehdi ensi kerralla!',
  putoava: 'Miehemme saivat hänet verkkoon. Ehdi ensi kerralla!',
  pakenevat: 'Rosvot loikkivat karkuun. Yritetään uudelleen!',
  pommit: 'Pommiryhmä hoiti loput. Yritetään uudelleen!',
  boss: 'Varjo pääsi pakoon! Hänen kopterinsa palaa…',
};

// ---- Progress ----
function storyLoad() {
  const t = load('tarina', null) || {};
  return { done: clamp(t.done | 0, 0, STORY.length), best: t.best && typeof t.best === 'object' ? t.best : {}, cur: t.cur && STORY[t.cur.ch] ? t.cur : null };
}
let story = storyLoad();
function storySave() { save('tarina', story); }
// The chapter now being played, and the hero's spot, as the round goes (every 2 s and on leaving).
function saveStoryRound() {
  const w = world, h = w.hero;
  if (!w.chDone) story.cur = { ch: w.story.ch, step: w.story.step, gt: w.fail ? 0 : Math.round(w.gt * 10) / 10, ct: Math.round(w.ct * 10) / 10, g: w.goal };
  storySave();
  save('tarina-kierros', { h: { x: h.x, y: h.y, z: h.z, yaw: h.yaw, st: h.st === 'wall' ? 'wall' : 'air', box: h.box ? h.box.id : -1, nx: h.nx, nz: h.nz } });
}

// ---- The chapter list ----
function showChapters() {
  mode = 'menu'; world = null;
  hideAll(); $('chapters').hidden = false;
  story = storyLoad();
  const list = $('chList'); list.textContent = '';
  STORY.forEach((c, i) => {
    const b = document.createElement('button'), open = i <= story.done, now = story.cur && story.cur.ch === i;
    b.className = 'ch' + (open && i === Math.min(story.done, STORY.length - 1) || now ? ' next' : '');
    b.disabled = !open;
    const best = story.best[i];
    b.textContent = (open ? '' : '🔒 ') + (i + 1) + '. ' + c.name + (now ? ' · jatka' : best ? ' ✔ ' + fmt(best) : '');
    b.addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); playChapter(i); });
    list.appendChild(b);
  });
  $('chSub').textContent = story.done >= STORY.length ? 'Kaupunki on turvassa! Pelaa lukuja uudelleen.' : 'Luku ' + (story.done + 1) + '/' + STORY.length;
}
function storyLabel() {
  const t = storyLoad();
  return '📖 Tarina · ' + (t.done >= STORY.length ? 'läpi ✔' : 'Luku ' + (t.done + 1) + '/' + STORY.length);
}

// ---- Playing a chapter ----
function storyWorld(ch, spot) {
  const w = newWorld();
  if (spot && spot.h) restore(w, spot.h);
  w.story = { ch, step: 0 };
  return w;
}
function goPlay() {
  cam.yaw = world.hero.yaw; cam.pitch = 0.3; cam.manualT = 9;
  mode = 'play'; acc = 0; result = null; stick = null; webPtr = null; jumpQ = false; lookPtr = null; pullPtr = null; pullQ = null; catchFx = null;
  hideAll();
  saveRound();
}
function playChapter(i) {
  const cur = story.cur;
  if (cur && cur.ch === i) {
    // Going on where the player left: the same step and clocks; a marked roof is kept, crooks start fresh.
    world = storyWorld(i, load('tarina-kierros', null));
    world.story.step = clamp(cur.step | 0, 0, STORY[i].steps.length - 1); world.ct = Math.max(0, +cur.ct || 0);
    const m = missionFor(world);
    if (!isCrook(m.k) && CITY[cur.g]) { world.kind = m.k; world.lim = m.lim; setGoal(world, cur.g); }
    else startMission(world);
    world.gt = Math.max(0, +cur.gt || 0);
    goPlay();
    return;
  }
  // A new start: the first chapter on the street by the tower, the others where the hero was.
  world = storyWorld(i, i ? load('tarina-kierros', null) : null);
  story.cur = { ch: i, step: 0, gt: 0, ct: 0, g: -1 }; storySave();
  startMission(world);
  playCut('Luku ' + (i + 1) + ' · ' + STORY[i].name, STORY[i].intro, goPlay, { wide: true, go: 'Aloita ▶' });
}
// A card over the paused game: a title, a few lines of talk, and its buttons.
function showCard(title, lines, go, then, alt, altThen) {
  mode = 'card';
  hideAll(); $('card').hidden = false;
  $('cardTitle').textContent = title;
  const box = $('cardLines'); box.textContent = '';
  for (const [who, text] of lines) {
    const p = WHO[who] || WHO.K, row = document.createElement('div'), av = document.createElement('span'), t = document.createElement('div'), n = document.createElement('b');
    row.className = 'ln'; av.className = 'av'; av.style.background = p.c; av.textContent = who;
    n.textContent = p.n; n.style.color = p.c; t.appendChild(n); t.appendChild(document.createTextNode(text));
    row.appendChild(av); row.appendChild(t); box.appendChild(row);
  }
  $('cardGo').textContent = go; cardThen = then;
  $('cardAlt').hidden = !alt; $('cardAlt').textContent = alt || ''; cardAltThen = altThen || null;
}
let cardThen = null, cardAltThen = null;
$('cardGo').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); const f = cardThen; cardThen = null; if (f) f(); });
$('cardAlt').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); const f = cardAltThen; cardAltThen = null; if (f) f(); });
$('story').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showChapters(); });
$('chBack').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); showMenu(); });
$('next').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (STORY[lastCh + 1]) playChapter(lastCh + 1); else showChapters(); });

// The time ran out: the same mission again, or back to the menu (the step is kept).
function storyFail() {
  const w = world;
  saveRound();
  showCard('Liian myöhään!', [['K', FAIL_SAY[w.fail.kind] || 'Yritetään uudelleen!']], 'Yritä uudelleen', () => { retryMission(world); goPlay(); },
    'Valikkoon', () => showMenu());
}
// The chapter's last mission done: saved at once (storyRecord); a moment later its closing card,
// then the chapter's end screen (storyEnd).
let lastCh = -1;
function storyRecord(w) {
  const i = w.story.ch, t = Math.round(w.ct * 10) / 10;
  const best = story.best[i], rec = !best || t < best;
  if (rec) story.best[i] = t;
  story.done = Math.max(story.done, i + 1); story.cur = null; storySave();
  lastCh = i; w.endRes = { t, rec, best };
}
function storyEnd() {
  const w = world, i = w.story.ch, { t, rec, best } = w.endRes;
  sfx('voitto', { vol: 0.3 });
  playCut('Luku ' + (i + 1) + ' valmis!', STORY[i].outro, () => {
    mode = 'end'; hideAll(); $('end').hidden = false; result = null;
    const last = i === STORY.length - 1;
    $('endTitle').textContent = last ? 'Kaupunki on turvassa!' : 'Luku ' + (i + 1) + ' valmis!';
    $('endNote').textContent = 'Aika ' + fmt(t) + (rec ? ' · uusi ennätys!' : ' · ennätys ' + fmt(best));
    $('next').hidden = last; $('next').textContent = last ? '' : 'Luku ' + (i + 2) + ': ' + STORY[i + 1].name + ' ▶';
    $('toMenu').textContent = 'Valikkoon';
  }, { caught: i === STORY.length - 1, end: true });
}
// A mission inside a chapter with a cutscene of its own: played a moment after the last one was
// done (ui.js waits cutT, so its "done" text shows first), then back to play.
function storyCut(w) {
  const st = STORY[w.story.ch].steps[w.story.step];
  w.cutQ = false;
  if (st && st.cut) playCut(null, st.cut, goPlay, {});
}

// ---- Cutscenes (#565, Eero: "Saataisko myös cutscenejä") ----
// The talk played in the city: at a chapter's start a wide look over the city, then Kallio on a
// roof beside the hero or Varjo on the tower top with his helicopter, by who speaks; at a
// mission's start it ends on the mission's target with its radio line. A tap shows the next line,
// "Ohita" skips the rest. The world stands still meanwhile (mode 'cut'). Without 3D, the card.
const CUT_COL = { K: '#2f4f9e', V: '#3a2050' };
let cut = null;
function cutSpots(w) {
  const h = w.hero; let best = null, bd = 1e9;
  for (const b of CITY) if (!b.tower && b.h >= 20 && b.h <= 80) {
    const t = roofTop(b), d = Math.hypot(t.x - h.x, t.z - h.z);
    if (d < bd) { bd = d; best = b; }
  }
  return { roof: roofTop(best || T_BOX), top: roofTop(T_BOX) };
}
function playCut(title, lines, then, o) {
  if (window.L3D && L3D.failed) { showCard(title || '', lines, o.go || 'Jatka ▶', then); return; }
  const shots = o.wide ? [{ k: 'city', lines: [] }] : [];
  for (const ln of lines) {
    const k = ln[0] === 'V' ? 'varjo' : 'roof', last = shots[shots.length - 1];
    if (last && last.k === k) last.lines.push(ln); else shots.push({ k, lines: [ln] });
  }
  const m = !o.end && world.story && STORY[world.story.ch].steps[world.story.step];
  if (m && cutAim(world)) shots.push({ k: 'target', lines: [m.say] });
  cut = { title, shots, i: 0, n: 0, t: 0, then, spots: cutSpots(world), caught: !!o.caught, go: o.go || 'Jatka ▶' };
  mode = 'cut'; hideAll(); $('cut').hidden = false;
  showCutLine();
}
// Where the mission's thing is: its first crook, or the marked roof.
function cutAim(w) {
  const k = w.crooks && w.crooks[0];
  return k ? { x: k.x, y: k.y + 1, z: k.z } : w.flag ? { x: w.flag.x, y: w.flag.y + 1, z: w.flag.z } : null;
}
function showCutLine() {
  const sh = cut.shots[cut.i], ln = sh.lines[cut.n];
  $('cut').classList.toggle('wide', sh.k === 'city');
  $('cutTitle').textContent = cut.title || ''; $('cutTitle').hidden = !cut.title || cut.i > 0;
  $('cutLine').hidden = !ln;
  if (ln) {
    const p = WHO[ln[0]] || WHO.K;
    const av = $('cutAv'); av.textContent = ln[0]; av.style.background = p.c;
    $('cutWho').textContent = p.n; $('cutWho').style.color = p.c; $('cutText').textContent = ln[1];
  }
  const last = cut.i === cut.shots.length - 1 && cut.n >= sh.lines.length - 1;
  $('cutTap').textContent = last ? cut.go : 'Napauta ▸';
}
function cutNext() {
  if (!cut) return;
  const sh = cut.shots[cut.i];
  if (cut.n + 1 < sh.lines.length) cut.n++;
  else if (cut.i + 1 < cut.shots.length) { cut.i++; cut.n = 0; cut.t = 0; }
  else return cutDone();
  showCutLine();
}
function cutDone() {
  const f = cut.then; cut = null;
  $('cut').hidden = true;
  f();
}
$('cut').addEventListener('click', e => { if (e.target.id === 'cutSkip') return; sfx('valinta', { vol: 0.2 }); cutNext(); });
$('cutSkip').addEventListener('click', () => { sfx('valinta', { vol: 0.3 }); if (cut) cutDone(); });
// The camera and the people of the shot being played, for L3D.draw (s.cut).
function cutView(dt) {
  if (!cut) return null;
  cut.t += dt;
  let sh = cut.shots[cut.i];
  if (sh.k === 'city' && cut.t > 3.5) { cutNext(); if (!cut || mode !== 'cut') return null; sh = cut.shots[cut.i]; }
  const t = cut.t, { roof, top } = cut.spots;
  const vx = top.x + 2.5, vz = top.z + 3;
  const actors = [
    { id: 'kallio', col: CUT_COL.K, x: roof.x - 0.9, y: roof.y, z: roof.z, yaw: Math.PI / 2 },
    { id: 'sankari', col: '#1fb5a8', x: roof.x + 0.9, y: roof.y, z: roof.z, yaw: -Math.PI / 2 },
    { id: 'varjo', col: CUT_COL.V, x: vx, y: top.y, z: vz, yaw: Math.PI / 2, caught: cut.caught },
  ];
  if (!cut.caught) actors.push({ id: 'kopteri', heli: true, x: top.x - 4, y: top.y + 4.5 + Math.sin(t * 1.6) * 0.4, z: top.z - 0.5, yaw: Math.PI / 2 });
  if (sh.k === 'target') actors.length = 0;   // only the mission's own things there
  let c, l;
  const dn = LAND ? 1.1 : 0;   // sideways the talk covers the lower half: the people a bit higher
  if (sh.k === 'city') {
    const a = 0.7 + t * 0.1, rr = 190 - t * 8;
    c = [top.x + Math.sin(a) * rr, 120 - t * 6, top.z + Math.cos(a) * rr]; l = [top.x, top.y * 0.55, top.z];
  } else if (sh.k === 'varjo') {
    // From a little below, Varjo in front and his helicopter waiting behind him.
    const d = Math.max(8, 12 - t * 0.5);
    c = [vx + d, top.y + 1.4, vz + d * 0.45]; l = [vx - 2.5, top.y + 2.6 - dn, vz - 0.8];
  } else if (sh.k === 'roof') {
    const a = 0.25 + t * 0.08;
    l = [roof.x, roof.y + 1.3 - dn, roof.z];
    let d = 6;
    while (d > 2 && insideCity(roof.x + Math.sin(a) * d, roof.y + 2.4, roof.z + Math.cos(a) * d, 0.3)) d -= 0.5;
    c = [roof.x + Math.sin(a) * d, roof.y + 2.4, roof.z + Math.cos(a) * d];
  } else {
    // The target, from the hero's side, the camera slowly closing in.
    const p = cutAim(world) || top, h = world.hero;
    let dx = h.x - p.x, dz = h.z - p.z; const n = Math.hypot(dx, dz) || 1; dx /= n; dz /= n;
    const d = Math.max(14, 24 - t * 1.5);
    c = [p.x + dx * d, p.y + 8, p.z + dz * d]; l = [p.x, p.y, p.z];
  }
  return { cam: c, look: l, actors };
}

// The radio line on top of the play: the speaker's name in his colour, the line under it.
function drawRadio(w, top) {
  const r = w.radio;
  if (!r || w.got) return;
  const p = WHO[r.who] || WHO.K;
  cx.font = '700 14px system-ui,sans-serif';
  const wd = Math.min(W - 40, Math.max(cx.measureText(r.text).width, 120) + 24);
  const x = W / 2, y = LAND ? H - SAFE_B - 44 : top + 150;
  cx.globalAlpha = Math.min(1, r.t * 2);
  cx.fillStyle = 'rgba(8,24,48,.72)';
  cx.beginPath(); cx.roundRect ? cx.roundRect(x - wd / 2, y - 22, wd, 44, 10) : cx.rect(x - wd / 2, y - 22, wd, 44); cx.fill();
  shadowText('📻 ' + p.n, x, y - 9, 12, p.c, 'center', 900);
  shadowText(r.text, x, y + 10, 14, '#fff', 'center', 700);
  cx.globalAlpha = 1;
}
if (mode === 'menu' && !$('menu').hidden) $('story').textContent = storyLabel();
