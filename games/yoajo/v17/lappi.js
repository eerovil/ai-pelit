// Yöajo v15 (#440 "Autopeliin lisää"): Lapland. Three legs on from Rovaniemi to Utsjoki (LEGS 9–11
// in game.js), with reindeer crossing in herds, a tank to watch and a service station on each leg
// (fuel only on the Lapland legs, Eero's choice), and "Koko matka", the whole trip's totals: the
// best points and stars of every leg, and what has been driven in all, kept on the phone.
// Everything is top-level, as in game.js.

// ---- Fuel ----
// The tank, 0..1 (full). At FUEL_V the car burns a full tank in FUEL_TANK legs' length; faster it
// burns more (with the square of the speed, a little always). A leg starts with FUEL_MARGIN times
// what driving at the limits takes to the service station, so the station is a must and speeding
// runs the tank dry before it. Stopped at the pump it fills FUEL_FILL a second. Under FUEL_LOW a
// warning; an empty tank gives no pull, and the car rolls to a stop (FUEL_ROLL m/s² more drag).
const FUEL_V = 80 / KMH, FUEL_TANK = 1.1, FUEL_MARGIN = 1.3, FUEL_FILL = 0.1, FUEL_LOW = 0.15, FUEL_ROLL = 1.5;
// How much of the tank a metre takes at speed v (m/s).
// v16: in the endless night a full tank is leg.tankM metres at FUEL_V (the stages are short).
function burnRate(v) { return (0.4 + 0.6 * (v / FUEL_V) ** 2) / (leg.tankM || leg.len * FUEL_TANK); }
// The station: the leg's rest area, which game.js marks `station` on a leg with fuel.
const stationAhead = () => road.bays.find(b => b.station && b.s1 > P.s);
// From newLeg, once P is made: the tank as the leg starts (null on a leg without fuel).
function fuelLeg() {
  P.fuel = null; P.dry = false; P.filling = false; P.lowTold = false;
  const st = road.bays.find(b => b.station);
  // v16: the endless night starts full; nextStage() carries the tank on (loputon.js).
  if (leg.endless) { P.fuel = 1; return; }
  if (!leg.fuel || !st) return;
  let need = 0;
  for (let s = 0; s < st.s0; s += 20) need += 20 * burnRate(limitAt(s) / KMH);
  P.fuel = Math.min(1, need * FUEL_MARGIN);
}
// Every step of the drive (from drive() in game.js).
function lappiTick(dt) {
  // The moose and reindeer got past, for the trip's totals.
  for (const t of things) if ((t.kind === 'hirvi' || t.kind === 'poro') && !t.got && t.s < P.s - 4) { t.got = true; tally.elaimet++; }
  if (P.fuel === null || P.fuel === undefined) return;
  // At the pump: off the road on the station's paving, stopped (the coffee is tiredness()'s).
  const st = road.bays.find(b => b.station && P.s > b.s0 && P.s < b.s1);
  P.filling = false;
  if (st && P.lat > EDGE + 0.5 && P.v < 1) {
    if (P.fuel < 1) {
      if (!st.filled) { st.filled = true; tally.tankkaus++; }
      P.fuel = Math.min(1, P.fuel + FUEL_FILL * dt); P.filling = true; P.dry = false; P.lowTold = false;
      if (P.fuel >= 1) say('Tankki täynnä', true);
    }
    return;
  }
  P.fuel = Math.max(0, P.fuel - burnRate(P.v) * P.v * dt);
  if (P.fuel < FUEL_LOW && !P.lowTold) {
    P.lowTold = true;
    const next = stationAhead();
    say(next ? `Tankki vähissä: huoltoasema ${Math.max(0.1, (next.s0 - P.s) / 1000).toFixed(1).replace('.', ',')} km` : leg.endless ? 'Tankki vähissä: huoltoasema seuraavalla etapilla' : 'Tankki vähissä!', false);
  }
  if (P.fuel <= 0) {
    if (!P.dry) say('Polttoaine loppui!', false);
    P.dry = true;
    P.v = Math.max(0, P.v - FUEL_ROLL * dt);
    if (P.v < 0.5) crash('Polttoaine loppui.');
  }
}

// ---- Reindeer herds ----
// A herd of HERD_MIN.. HERD_MAX reindeer crossing one after another, each standing on the road
// for a while (2–4.5 s, a lone one 1.6 s): slow down and wait until the road is clear.
const HERD_MIN = 3, HERD_MAX = 5;
function herdLeg(evs, spot) {
  const r = rng(leg.seed * 31 + 11), end = leg.len - 320;
  for (let k = 0; k < leg.herds; k++) {
    const s = spot(320, 600, end, r); if (s < 0) continue;
    road.signs.push({ s, kind: 'poro' });
    const n = HERD_MIN + Math.floor(r() * (HERD_MAX - HERD_MIN + 1)), side = r() < 0.5 ? -1 : 1, at = s + 230 + r() * 60;
    for (let i = 0; i < n; i++) evs.push({ s: at, kind: 'poro', side, stop: true, hold: 2 + r() * 2.5, herd: i });
  }
}

// ---- Koko matka: the whole trip ----
// What has been driven in all, saved as ai-pelit:yoajo:tilasto: km, legs driven to the end, police
// stops, fines, moose and reindeer got past, fuel stops.
const TRIP_KEYS = ['km', 'osuudet', 'poliisi', 'sakot', 'elaimet', 'tankkaus'];
function tripStats() { const t = load('tilasto', {}) || {}; for (const k of TRIP_KEYS) t[k] = +t[k] || 0; return t; }
// What the leg has added since the last call: when it ends (driven to the end, crashed, or left
// from the pause), and when the page is hidden or left (the "‹ Pelit" chip, closing the app),
// where nothing else runs. Each call adds only what is new since the one before (`tally.logged`),
// so a page hidden and shown again counts nothing twice. A leg left before 30 m adds nothing.
function tripLog() {
  if (!tally || !P || !leg || P.s < 30) return;
  const was = tally.logged || { m: 0, poliisi: 0, sakot: 0, elaimet: 0, tankkaus: 0, done: false };
  const now = { m: Math.min(P.s, leg.len), poliisi: tally.poliisi || 0, sakot: tally.sakot || 0, elaimet: tally.elaimet || 0, tankkaus: tally.tankkaus || 0, done: was.done || mode === 'done' };
  tally.logged = now;
  const t = tripStats();
  t.km += Math.max(0, now.m - was.m) / 1000;   // unrounded, so many short visits add up; shown to 0.1 km
  if (now.done && !was.done) t.osuudet++;
  for (const k of ['poliisi', 'sakot', 'elaimet', 'tankkaus']) t[k] += Math.max(0, now[k] - was[k]);
  save('tilasto', t);
}
addEventListener('pagehide', tripLog);
document.addEventListener('visibilitychange', () => { if (document.hidden) tripLog(); });
// The best points and stars over every leg.
function tripTotals() {
  let pts = 0, st = 0, legs = 0;
  for (let n = 1; n <= LEGS.length; n++) { if (bests[n] != null) { pts += +bests[n] || 0; legs++; } st += +stars[n] || 0; }
  return { pts, st, legs, of: LEGS.length * 3 };
}
// The screen (mode 'matka', from the menu or the last leg's end): the route with each leg's stars,
// the totals, and what has been driven in all. "Takaisin" goes back where it came from.
let tripFrom = 'menu';
function openTrip() { tripFrom = mode; mode = 'matka'; }
function tripScreen() {
  x.fillStyle = 'rgba(4,6,12,0.78)'; x.fillRect(0, 0, W, H);
  const tot = tripTotals(), st = tripStats(), num = v => String(v).replace('.', ',');
  const w = Math.min(LAND ? 680 : 360, W - 20 - SAFE_L - SAFE_R), x0 = (W - w) / 2, y0 = LAND ? SAFE_T + 8 : SAFE_T + 46, h = LAND ? H - y0 - SAFE_B - 8 : H - y0 - SAFE_B - 10;
  panel(x0, y0, w, h);
  const colW = LAND ? w / 2 : w, cx = x0 + colW / 2;
  fitText('🏁 Koko matka', cx, y0 + 26, 22, colW - 30, '#ffe08a', 'center', 900);
  fitText(`${LEGS[0].from} → ${LEGS[LEGS.length - 1].to}`, cx, y0 + 50, 13, colW - 30, '#cfe0ff', 'center', 600);
  // The route: one row a leg, its stars, or a lock.
  const ry = y0 + 70, rh = Math.min(LAND ? 22 : 21, ((LAND ? h - 84 : h * 0.5) - 6) / LEGS.length);
  LEGS.forEach((L, i) => {
    const n = i + 1, y = ry + i * rh + rh / 2, open = n <= maxLeg;
    text(String(n), x0 + 22, y, 13, open ? '#ffe08a' : '#666', 'center', 800);
    fitText(L.to, x0 + 36, y, 13, colW - 120, open ? '#e8eefc' : '#777', 'left', 600);
    text(open ? starText(stars[n] || 0) : '🔒', x0 + colW - 16, y, 13, open ? '#ffd24a' : '#777', 'right', 700);
  });
  // The totals, and what has been driven in all.
  const tx0 = LAND ? x0 + colW + 14 : x0 + 22, tx1 = LAND ? x0 + w - 18 : x0 + w - 22;
  let ty = LAND ? y0 + 30 : ry + LEGS.length * rh + 18;
  const rows = [
    ['Tähdet', `${tot.st} / ${tot.of} ★`],
    ['Parhaat pisteet yhteensä', `${tot.pts} p`],
    ['Osuuksia perillä', String(st.osuudet)],
    ['Ajettu yhteensä', `${num(st.km.toFixed(1))} km`],
    ['Hirvet ja porot ohitettu', String(st.elaimet)],
    ['Poliisin pysäytykset', String(st.poliisi)],
    ['Sakot', String(st.sakot)],
    ['Tankkaukset', String(st.tankkaus)],
  ];
  const lh = Math.min(24, ((LAND ? h - 110 : y0 + h - ty - 74)) / rows.length);
  rows.forEach(([a, b], i) => { fitText(a, tx0, ty + i * lh, 14, (tx1 - tx0) * 0.62, '#cfd8ea', 'left', 500); text(b, tx1, ty + i * lh, 14, i < 2 ? '#ffe08a' : '#fff', 'right', 700); });
  const bw = Math.min(260, (LAND ? colW : w) - 40), bx = LAND ? x0 + colW + (colW - bw) / 2 : x0 + (w - bw) / 2;
  const b = button('takaisin', bx, y0 + h - 64, bw, 50, 'Takaisin');
  drawBtn(b, true);
}
