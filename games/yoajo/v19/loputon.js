// Yöajo v16 (#440 "Autopeliin lisää"): the endless night, "🌌 Loputon yö". Once leg 1 has been
// driven, the menu offers a run of stages of about 3–4 km, each a little harder than the one before
// (more traffic, worse weather, more moose, reindeer and police, more turns). Between stages the
// screen fades for a second and the car drives on: its speed, tank and alertness carry over. A
// service station only every other stage. The run ends at a crash, falling asleep, the police, a
// missed turn or an empty tank; its points (+20 a km driven) go to the high-score list "loputon".
// Everything is top-level, as in game.js; `endless` itself is declared there.

const ENDLESS_KM = 20;        // points for each whole km driven in the run
const ENDLESS_TANK = 12000;   // metres a full tank lasts at FUEL_V (lappi.js): a station every other stage
const ENDLESS_AWAKE = 10000;  // metres from rested to asleep: a coffee at every station keeps it
// The villages the stages run between, north of the Arctic Circle. 23 of them (a prime), stepped
// by 7, so a run names none twice in 23 stages.
const VILLAGES = ['Vikajärvi', 'Tanhua', 'Pelkosenniemi', 'Savukoski', 'Vuotso', 'Saariselkä', 'Kaamanen',
  'Karigasniemi', 'Nuorgam', 'Kittilä', 'Levi', 'Muonio', 'Enontekiö', 'Hetta', 'Kilpisjärvi', 'Salla',
  'Kemijärvi', 'Posio', 'Pello', 'Kolari', 'Äkäslompolo', 'Raattama', 'Inari'];
const ENDLESS_WEATHER = ['kuiva', 'sade', 'kuiva', 'lumi', 'pakkanen', 'pyry'];
const villageAt = i => VILLAGES[(endless.seed + i * 7) % VILLAGES.length];

// Stage k (1, 2, ...) of the run, a LEGS-like entry. `tpl` is the leg whose road events and
// crossroad names it takes (ROAD_EVENTS, STRAIGHT_ON); `police` and `turns` are its own.
function endlessStage(k) {
  const seed = (endless.seed * 31 + k * 7919) % 99991 + 1, r = rng(seed * 3 + 1);
  const turns = Math.min(3, 1 + Math.floor(k / 3));
  const weather = k <= ENDLESS_WEATHER.length ? ENDLESS_WEATHER[k - 1] : ['sade', 'lumi', 'pyry', 'pakkanen', 'pyry'][Math.floor(r() * 5)];
  return {
    endless: true, k, tpl: k <= 10 ? k + 1 : 7 + (k % 5),
    from: villageAt(k - 1), to: villageAt(k), len: 2600 + 400 * turns, weather,
    limit: weather === 'kuiva' ? 100 : 80,
    oncoming: Math.min(16, 8 + k), cars: k > 3 ? 2 : 1, tractors: k < 6 ? 1 : 0, walkers: 1 + (k % 2),
    trucks: Math.min(5, 1 + Math.floor(k / 2)), cameras: Math.min(3, Math.floor((k + 1) / 3)),
    moose: Math.min(4, Math.floor(k / 2)), reindeer: k >= 5 ? Math.min(3, Math.floor((k - 3) / 2)) : 0,
    herds: k >= 4 ? Math.min(3, Math.floor((k - 2) / 2)) : 0, racers: Math.min(3, Math.floor(k / 3)),
    bad: Math.min(3, Math.floor(k / 3)), tired: 1, junctions: 2, fuel: true,
    aurora: weather === 'pakkanen', straights: k >= 5, fell: k >= 8 && r() < 0.4,
    police: Math.min(4, 1 + Math.floor(k / 3)), turns,
    noBay: k % 2 === 1, tankM: ENDLESS_TANK, awake: ENDLESS_AWAKE, seed,
  };
}
// The best run, saved as ai-pelit:yoajo:loputon: { p (points), km, k (stages reached) }.
function endlessBest() { const b = load('loputon', null); return b && typeof b.p === 'number' ? b : null; }
// "Loputon yö" opens once leg 1 has been driven to the end.
const endlessOpen = () => driven >= 1;

// From the menu ("🌌 Loputon yö"), and "Aja uudelleen" / "Aloita alusta" in a run. Each run has
// roads of its own (a random seed; the tests give one).
function startEndless(seed) {
  const back = endless ? endless.back : level;
  endless = { k: 1, seed: seed || Math.floor(Math.random() * 99000) + 1, back, m: 0, paid: 0, fade: 0, over: null };
  newLeg();
  say(`Etappi 1: ${leg.from} → ${leg.to}`, true);
}
// From finish() in game.js, when the car reaches the stage's end: the next stage, with the car as it is.
function nextStage() {
  const keep = { v: P.v, fuel: P.fuel, tired: P.tired, lat: Math.abs(P.lat) < EDGE ? P.lat : LANE, high: P.high, dry: P.dry }, pts = points;
  endless.m += leg.len;
  endless.k++;
  // newLeg() lets go of the controls; a finger held over the line keeps driving (the thumbs are
  // still down, ui.js), and so does a held key.
  const held = { left: input.left, right: input.right };
  newLeg();
  Object.assign(P, keep);
  Object.assign(input, held);
  if (typeof setThumbs === 'function') setThumbs();
  points = pts; lastPoints = pts;
  endless.fade = 1;
  say(`Etappi ${endless.k} · ${Math.floor(endless.m / 1000)} km`, true);
}
// Each step of the drive: +ENDLESS_KM points for each whole km of the run.
const endlessMetres = () => endless.m + clamp(P.s, 0, leg.len);
function endlessTick() {
  const km = Math.floor(endlessMetres() / 1000);
  while (endless.paid < km) { endless.paid++; score(ENDLESS_KM, `${endless.paid} km`); }
}
// From crash() in game.js: the run is over. The points go to the "loputon" list, the best stays.
function endlessOver() {
  if (endless.over) return;
  const km = endlessMetres() / 1000, best = endlessBest(), record = !best || points > best.p;
  endless.over = { km, k: endless.k, record, best: record ? points : best.p };
  if (record) save('loputon', { p: points, km: Math.round(km * 10) / 10, k: endless.k });
  if (window.AiPelitScores) AiPelitScores.submit(points);
}
// Back to the menu: the legs again, on the leg picked before the run.
function leaveEndless() { if (!endless) return; level = endless.back; endless = null; }

// ---- Drawing (ui.js's helpers) ----
// The black between two stages, fading out, with the stage's number and the km so far.
function endlessFade() {
  if (!endless || !(endless.fade > 0)) return;
  x.fillStyle = `rgba(0,0,0,${clamp(endless.fade * 1.4, 0, 1)})`; x.fillRect(0, 0, W, H);
  // Sideways, under the messages (which say the same with the km), not over them.
  const a = clamp(endless.fade * 2, 0, 1), y = LAND ? H * 0.62 : H * 0.4;
  text(`Etappi ${endless.k}`, W / 2, y, 30, `rgba(255,224,138,${a})`, 'center', 900);
  fitText(`${leg.from} → ${leg.to}`, W / 2, y + 34, 16, W - 40, `rgba(207,224,255,${a})`, 'center', 600);
}
// The end of a run, in place of crashScreen().
function endlessScreen(title, lines, hints) {
  const o = endless.over || { km: 0, k: endless.k, record: false, best: points };
  const w = Math.min(LAND ? 600 : 340, W - 24), h = LAND ? H - 24 : Math.min(H - 20, 330 + lines.length * 21 + hints.length * 18);
  const x0 = (W - w) / 2, y0 = LAND ? 12 : Math.max(SAFE_T + 10, Math.min(H * 0.16, H - h - 10));
  panel(x0, y0, w, h);
  const cx = LAND ? x0 + w * 0.27 : W / 2, cw = LAND ? w / 2 - 20 : w - 30;
  fitText(title, cx, y0 + 34, 26, cw, '#ff8a7a', 'center', 900);
  let ly = y0 + 66;
  lines.forEach((l, i) => fitText(l, cx, ly + i * 20, 14, cw, '#e8eefc', 'center', 600));
  ly += lines.length * 20;
  hints.forEach((l, i) => fitText(l, cx, ly + i * 17, 12, cw, '#9fb0cc', 'center', 500));
  ly += hints.length * 17 + 18;
  fitText(`Loputon yö: etappi ${o.k} · ${o.km.toFixed(1).replace('.', ',')} km`, cx, ly, 15, cw, '#cfe0ff', 'center', 700);
  text(`${points} p`, cx, ly + 36, 30, '#ffffff', 'center', 900);
  text(o.record ? 'Uusi ennätys!' : `Ennätys ${o.best} p`, cx, ly + 66, 14, o.record ? '#9ff0a8' : '#9fb0cc', 'center', 700);
  const list = [['uudelleen', 'Aja uudelleen'], ['valikko', 'Valikko']];
  if (LAND) {
    const bx = x0 + w / 2 + 10, bw = w / 2 - 26, by = y0 + h / 2 - 57;
    list.forEach(([id, label], i) => button(id, bx, by + i * 62, bw, 52, label));
    btns.forEach((b, i) => drawBtn(b, i === 0));
  } else endButtons(list, y0 + h - 124);
}
