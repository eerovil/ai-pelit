'use strict';
// The six trips (D7). Each opens the next; stars come from fuel left (as Δv, so a start
// from orbit is scored the same way) and from a soft finish (D12).
const TRIPS = [
  { id: 'kiertorata', name: 'Kiertoradalle', minutes: 3, dvStar: 4300,
    goal: 'Nouse Maan kiertoradalle: radan alin yli 40 km. Katkaise lopuksi teho.',
    done: 'Kiertoradalla! Maa kiertää allasi.', soft: 'pyöreä rata' },
  { id: 'asema', name: 'Avaruusasemalle', minutes: 7, dvStar: 3900,
    goal: 'Kohtaa avaruusasema 100 km korkeudessa ja telakoidu porttiin alle 0,5 m/s.',
    done: 'Telakointi onnistui. Tervetuloa asemalle!', soft: 'pehmeä telakointi' },
  { id: 'kuu-kierto', name: 'Kuun kiertoradalle', minutes: 5, dvStar: 3300,
    goal: 'Lennä Kuuhun ja jää sen kiertoradalle: radan ylin alle 370 km. Katkaise lopuksi teho.',
    done: 'Kuun kiertoradalla! Kuu kiertää allasi.', soft: 'pyöreä rata' },
  { id: 'kuuhun', name: 'Kuuhun', minutes: 7, dvStar: 1700,
    goal: 'Laskeudu Kuuhun: alas alle 3 m/s, sivulle alle 2 m/s, nokka pystyssä.',
    done: 'Kuussa! Ensimmäinen askel harmaalle pölylle.', soft: 'pehmeä laskeutuminen' },
  { id: 'kotiin', name: 'Kuusta kotiin', minutes: 10, dvStar: 1000,
    goal: 'Laskeudu Kuuhun, nouse takaisin ja laskeudu Maahan laskuvarjolla.',
    done: 'Kotona! Kävit Kuussa ja palasit.', soft: 'pehmeä laskeutuminen Maahan' },
  { id: 'kivi', name: 'Pikkukivelle', minutes: 7, dvStar: 3100,
    goal: 'Laskeudu pienelle asteroidille 1500 km korkeudessa alle 1 m/s.',
    done: 'Pikkukivellä! Täällä yksi hyppy veisi avaruuteen.', soft: 'pehmeä laskeutuminen' }
];
const TRIP = Object.fromEntries(TRIPS.map(t => [t.id, t]));
function tripOpen(id) {
  const i = TRIPS.findIndex(t => t.id === id);
  return i === 0 || (stars[TRIPS[i - 1].id] || 0) > 0;
}
function engineQuiet(s) { return s.throttle === 0 && !held.forward && !held.side; }
function earthOrbitReady(s) {
  const o = orbitAround(EARTH, s);
  return refBody(s) === EARTH && o.peri > EARTH.air.top && o.apo < 1000000;
}
function moonOrbitReady(s) {
  const o = orbitAround(MOON, s);
  return refBody(s) === MOON && o.energy < 0 && o.peri > 2000 && o.apo < 370000;
}
function tripFinished(s) {
  if (s.landedOn === null && !engineQuiet(s)) return false;
  switch (s.trip) {
    case 'kiertorata': return !s.landedOn && earthOrbitReady(s);
    case 'kuu-kierto': return !s.landedOn && moonOrbitReady(s);
    case 'kuuhun': return s.landedOn === 'moon';
    case 'kotiin': return s.landedOn === 'earth' && s.visited.includes('moon');
    case 'kivi': return s.landedOn === 'rock';
    default: return false;
  }
}
function tripSoft(s) {
  if (s.trip === 'kiertorata') return orbitAround(EARTH, s).ecc <= 0.1;
  if (s.trip === 'kuu-kierto') return orbitAround(MOON, s).ecc <= 0.1;
  return !!(s.touch && s.touch.soft);
}
function tripStars(s) {
  return 1 + (deltaV(s) >= TRIP[s.trip].dvStar ? 1 : 0) + (tripSoft(s) ? 1 : 0);
}
function km(m) {
  if (!Number.isFinite(m)) return '—';
  return Math.abs(m) < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(Math.abs(m) < 10000 ? 1 : 0)} km`;
}
function deg(a) { return Math.round(a * 180 / Math.PI); }
// Angle the target leads the ship by, along the direction of motion (0..360°).
function leadOf(target, s) { return (Math.atan2(target.x, target.y) - Math.atan2(s.x, s.y) + 2 * TAU) % TAU; }
// Lead angle for a Hohmann transfer from the ship's orbit out to a circular target orbit.
function transferLead(r1, r2, n2) {
  const t = Math.PI * Math.sqrt(((r1 + r2) / 2) ** 3 / EARTH.mu);
  return ((Math.PI - n2 * t) % TAU + TAU) % TAU;
}
function ascentGuide(s) {
  const o = orbitAround(EARTH, s), h = o.altitude;
  if (s.landedOn === 'earth') return ['1', 'Nosta teho täysille ja laukaise.'];
  if (h < 1500 && o.vr > 0) return ['1', 'Teho täysillä. Nouse ensin suoraan ylös.'];
  if (o.apo < 55000 && s.throttle > 0) {
    return ['1', `Kallista ↷ noin ${Math.round(ascentPitch(h))}° pystystä. Radan ylin ${km(o.apo)} → tavoite 60 km.`];
  }
  if (o.toApo > 15 && o.vr > 0) return ['1', `Katkaise teho. Radan ylimpään ${Math.ceil(o.toApo)} s. Paina silloin Menosuuntaan ja kiihdytä.`];
  return ['1', `Nyt: Menosuuntaan ja teho täysille, kunnes radan alin on yli 40 km (nyt ${km(o.peri)}).`];
}
// The handbook's ascent: 20° from vertical at 1.5 km, leaning to 80° by 30 km. A hint only.
function ascentPitch(h) { return clamp(20 + (h - 1500) / 28500 * 60, 20, 80); }
function transferGuide(s, target, r2, n2, name, aim) {
  const o = orbitAround(EARTH, s), lead = transferLead(o.r, r2, n2), ahead = leadOf(target, s);
  if (o.apo + EARTH_R < r2 * 0.9) {
    const wait = ((ahead - lead) % TAU + TAU) % TAU;
    if (wait < 4 * Math.PI / 180) return ['2', `Nyt: Menosuuntaan ja teho täysille, kunnes radan ylin on ${aim}.`];
    return ['2', `${name} on ${deg(ahead)}° edellä. Kun se on noin ${deg(lead)}° edellä, kiihdytä menosuuntaan. Nopeuta aikaa odottaessa.`];
  }
  return null;
}
function landingGuide(s, b) {
  const q = relative(b, s), r = Math.hypot(q.x, q.y), h = r - b.radius;
  const down = -(q.x * q.vx + q.y * q.vy) / r, side = Math.abs(q.vx * q.y - q.vy * q.x) / r;
  const lim = LANDING[b.id];
  if (b.id === 'rock') return ['3', `Pikkukivi ${km(h)}. Nopeus ${Math.hypot(q.vx, q.vy).toFixed(1)} m/s → alle 1 m/s. Vastasuuntaan jarruttaa, siirtosuuttimet hienosäätävät.`];
  if (h > 15000) return ['3', `Laske korkeutta (${km(h)}): Vastasuuntaan ja jarruta. Sivuvauhti ${Math.round(side)} m/s pitää saada nollaan.`];
  return ['3', `Alas ${down.toFixed(1)} m/s (raja ${lim.down}), sivulle ${side.toFixed(1)} m/s (raja ${lim.side}). Pystyyn ennen kosketusta; noin 7 % teho kannattelee.`];
}
function guidance(s = ship, path = null) {
  if (!s) return ['1', 'Valitse matka.'];
  if (s.phase === 'done') return ['✓', TRIP[s.trip].done];
  if (s.phase === 'crashed') return ['!', s.reason];
  if (s.chute === 'open') return ['4', `Laskuvarjo auki. Vauhti ${Math.hypot(s.vx, s.vy).toFixed(1)} m/s; kosketus alle 10 m/s. Pehmeään laskuun jarruta moottorilla viime metreillä.`];
  const ref = refBody(s), o = orbitAround(EARTH, s);
  if (ref === EARTH && !s.visited.includes('moon') && (s.landedOn === 'earth' || o.peri < EARTH.air.top) && o.apo < 1500000) {
    return ascentGuide(s);
  }
  const trip = s.trip, closest = path && path.closest;
  if (trip === 'kiertorata') return ['1', 'Katkaise teho, niin kiertorata on valmis.'];
  if (trip === 'asema') {
    const d = approach(s);
    if (d.range < 2000) {
      if (d.speed > 1) return ['3', `Jarruta siirtosuuttimilla: nopeusero ${d.speed.toFixed(2)} m/s. Keltainen viiva näyttää liikkeen asemaan nähden.`];
      if (Math.abs(d.cross) > 1.5) return ['3', `Kohdista portin vihreälle linjalle: sivuero ${d.cross.toFixed(1)} m. Menosuuntaan kääntää nokan porttia kohti.`];
      return ['3', `Lähesty porttia alle 0,5 m/s. Nokan suuntaero ${(d.alignment * 180 / Math.PI).toFixed(0)}° (raja 10°).`];
    }
    if (d.range < 20000) return ['3', `Asema ${km(d.range)}, nopeusero ${d.speed.toFixed(1)} m/s. Vastasuuntaan jarruttaa asemaan nähden; käännä sitten nokka asemaan ja lähesty hitaasti.`];
    const tr = transferGuide(s, station(s), STATION_R, STATION_N, 'Asema', '100 km');
    if (tr) return tr;
    if (o.peri < 90000) return ['2', `Radan ylimmässä (${Math.ceil(o.toApo)} s) Menosuuntaan ja kiihdytä, kunnes radan alin on noin 100 km. Asema ${km(d.range)}.`];
    return ['2', `Asema ${km(d.range)}. Hieman alempi rata saavuttaa sen, ylempi päästää sen edelle.`];
  }
  if (trip === 'kivi') {
    if (ref === ROCK) return landingGuide(s, ROCK);
    const rock = bodyAt(ROCK, s.t);
    const tr = transferGuide(s, rock, ROCK.orbit.r, ROCK.orbit.n, 'Pikkukivi', '1500 km');
    if (tr) return tr;
    const c = closest && closest.rock;
    return ['2', `Matkalla Pikkukivelle. Kartan radan lähin kohta: ${c ? km(c.d) : '—'}. Pienellä poltolla saat sen alle 30 km.`];
  }
  // The Moon trips.
  const homeward = trip === 'kotiin' && s.visited.includes('moon');
  if (homeward) {
    if (s.landedOn === 'moon') return ['4', 'Kuussa! Teho ylös ja kallista menosuuntaan: nouse Kuun kiertoradalle.'];
    if (ref === MOON) {
      const m = orbitAround(MOON, s);
      if (m.peri < 5000) return ['4', `Nouse: kallista ↷ kohti vaakaa. Radan alin Kuun ympäri ${km(m.peri)} → yli 5 km.`];
      const c = closest && closest.earth;
      return ['4', `Kiihdytä menosuuntaan, kunnes kartan rata vie Maahan: lähin kohta ${c ? km(c.d) : '—'}, tavoite alle 30 km.`];
    }
    if (Math.hypot(s.x, s.y) - EARTH_R > EARTH.air.top) return ['4', `Matkalla kotiin. Radan alin ${km(o.peri)}: pidä se alle 30 km, niin ilma jarruttaa.`];
    return ['4', `Ilma jarruttaa (${Math.round(Math.hypot(s.vx, s.vy))} m/s). Avaa laskuvarjo alle 20 km korkeudessa ja alle 400 m/s.`];
  }
  if (ref === MOON) {
    const m = orbitAround(MOON, s);
    if (s.landedOn === 'moon') return ['3', 'Olet Kuussa. Tämä matka jatkuu kiertoradalta: nouse ja kierrä Kuuta.'];
    if (trip === 'kuu-kierto' || m.energy >= 0 || m.apo > 370000) {
      if (m.energy < 0 && m.apo < 370000) return ['3', 'Katkaise teho, niin kiertorata on valmis.'];
      if (m.peri < 2000) return ['3', `Rata osuu Kuuhun! Kiihdytä sivulle, kunnes radan alin on yli 2 km (nyt ${km(m.peri)}).`];
      if (m.vr < 0 && m.altitude - m.peri > 15000) return ['3', `Kuu lähestyy. Lähimmillään ${km(m.peri)} korkeudella. Jarruta siellä Vastasuuntaan.`];
      return ['3', `Nyt: Vastasuuntaan ja teho täysille, kunnes radan ylin on alle 370 km (nyt ${km(m.apo)}).`];
    }
    return landingGuide(s, MOON);
  }
  const tr = transferGuide(s, bodyAt(MOON, s.t), MOON.orbit.r, MOON.orbit.n, 'Kuu', 'noin 4900 km');
  if (tr) return tr;
  const c = closest && closest.moon;
  if (c && c.d > 300000) return ['2', `Rata ohittaa Kuun ${km(c.d)} päästä. Pieni poltto menosuuntaan tai vastaan siirtää sitä.`];
  return ['2', `Matkalla Kuuhun: lähin kohta ${c ? km(c.d) : '—'} pinnasta. Nopeuta aikaa ×1000.`];
}
