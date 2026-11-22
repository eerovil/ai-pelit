'use strict';
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
var cw = 360, ch = 300, mapWide = false;
var pathCache = { ship: null, at: -1e9, data: null };
const starField = Array.from({ length: 75 }, (_, i) => ({
  x: ((i * 73.137) % 359) / 359, y: ((i * 47.29) % 211) / 211, a: 0.2 + (i % 4) * 0.15
}));
const LOOK = {
  earth: { fill: '#1f5a56', edge: '#64a9bb', mapFill: '#163e50', mapEdge: '#497e91', label: 'MAA' },
  moon: { fill: '#6d7378', edge: '#b9c0c4', mapFill: '#5b6166', mapEdge: '#aab2b6', label: 'KUU' },
  rock: { fill: '#6b5a4c', edge: '#b59c84', mapFill: '#6b5a4c', mapEdge: '#c7ab90', label: 'PIKKUKIVI' }
};
function fitCanvas() {
  const box = canvas.getBoundingClientRect();
  cw = Math.max(1, box.width); ch = Math.max(1, box.height);
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); draw();
}
// The engine-off path ahead, recomputed a few times a second (D6).
function currentPath(s = ship) {
  if (!s) return null;
  const now = performance.now();
  if (pathCache.ship !== s || now - pathCache.at > 300 || !pathCache.data) {
    pathCache = { ship: s, at: now, data: predictPath(s) };
  }
  return pathCache.data;
}
function line(x, y, xx, yy, color = '#56798a', dash = []) {
  ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle = color; ctx.lineWidth = 1;
  ctx.moveTo(x, y); ctx.lineTo(xx, yy); ctx.stroke(); ctx.setLineDash([]);
}
function label(text, x, y, color = '#a2bbc9', align = 'left', size = 10) {
  ctx.font = `${size}px system-ui`; ctx.textAlign = align; ctx.fillStyle = color; ctx.fillText(text, x, y);
}
function dot(x, y, r, color) { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }
function rocketGlyph(x, y, angle, size, s = ship) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
  const w = size * 0.16, h = size;
  if (s.chute === 'open') {
    ctx.strokeStyle = '#d9c9a8'; ctx.lineWidth = 1;
    for (const k of [-1, 0, 1]) { ctx.beginPath(); ctx.moveTo(k * w, -h / 2); ctx.lineTo(k * size * 0.9, -h * 1.5); ctx.stroke(); }
    ctx.fillStyle = '#e9875e'; ctx.beginPath(); ctx.ellipse(0, -h * 1.55, size * 1.05, size * 0.45, 0, Math.PI, TAU); ctx.fill();
    ctx.fillStyle = '#f4ddb5'; ctx.fillRect(-size * 0.2, -h * 1.95, size * 0.4, size * 0.4);
  }
  if (s.throttle && s.phase === 'flight' && !paused) {
    const f = Math.sqrt(s.throttle);
    ctx.fillStyle = '#f5c67a'; ctx.beginPath(); ctx.moveTo(-w * 0.75, h / 2 - 1);
    ctx.lineTo(0, h / 2 + size * (0.2 + 0.35 * f)); ctx.lineTo(w * 0.75, h / 2 - 1); ctx.fill();
    ctx.fillStyle = '#e4f6fc'; ctx.beginPath(); ctx.moveTo(-w * 0.45, h / 2);
    ctx.lineTo(0, h / 2 + size * 0.18 * (0.4 + f)); ctx.lineTo(w * 0.45, h / 2); ctx.fill();
  }
  // Landing legs.
  ctx.strokeStyle = '#9fb1b6'; ctx.lineWidth = Math.max(1, size * 0.03);
  ctx.beginPath(); ctx.moveTo(-w, h * 0.3); ctx.lineTo(-w * 2.3, h / 2 + 1); ctx.moveTo(w, h * 0.3); ctx.lineTo(w * 2.3, h / 2 + 1); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, -h / 2); ctx.quadraticCurveTo(w, -h * 0.35, w, -h * 0.2);
  ctx.lineTo(w, h / 2); ctx.lineTo(-w, h / 2); ctx.lineTo(-w, -h * 0.2);
  ctx.quadraticCurveTo(-w, -h * 0.35, 0, -h / 2); ctx.fillStyle = '#e3e9e6'; ctx.fill();
  ctx.fillStyle = '#e9875e'; ctx.fillRect(-w, -h * 0.08, w * 2, h * 0.1);
  ctx.fillStyle = '#6c8996'; ctx.fillRect(-w, h * 0.33, w * 2, 2);
  ctx.fillStyle = '#142e3f'; ctx.beginPath(); ctx.arc(0, -h * 0.25, w * 0.55, 0, TAU); ctx.fill();
  if (!paused && s.rcs > 0 && (held.forward || held.side)) {
    ctx.strokeStyle = '#b9e8f3'; ctx.lineWidth = 2;
    if (held.side) { ctx.beginPath(); ctx.moveTo(-held.side * w, -h * 0.25); ctx.lineTo(-held.side * (w + 9), -h * 0.25); ctx.stroke(); }
    if (held.forward < 0) { ctx.beginPath(); ctx.moveTo(w, -h / 3); ctx.lineTo(w + 4, -h / 2 - 7); ctx.stroke(); }
    if (held.forward > 0) { ctx.beginPath(); ctx.moveTo(w, h / 3); ctx.lineTo(w + 4, h / 2 + 7); ctx.stroke(); }
  }
  ctx.restore();
}
function stationGlyph(x, y, scale = 1, rotation = 0) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rotation); ctx.scale(scale, scale);
  ctx.fillStyle = '#b8cbd1'; ctx.fillRect(-35, -8, 70, 16);
  ctx.fillStyle = '#203f66'; ctx.strokeStyle = '#608ba5'; ctx.lineWidth = 1 / scale;
  for (const xx of [-20, 10]) {
    ctx.fillRect(xx, -52, 10, 104); ctx.strokeRect(xx, -52, 10, 104);
    for (let yy = -46; yy < 52; yy += 9) { ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + 10, yy); ctx.stroke(); }
  }
  ctx.fillStyle = '#718c98'; ctx.fillRect(-45, -3, 10, 6);
  ctx.strokeStyle = '#8fe2d5'; ctx.lineWidth = 2 / scale;
  ctx.beginPath(); ctx.moveTo(-45, -5); ctx.lineTo(-45, 5); ctx.stroke();
  ctx.fillStyle = '#e0d5b6'; ctx.fillRect(-8, -12, 16, 24);
  ctx.restore();
}
// Craters seeded by angle, so a body looks the same every frame.
function craters(b, cx, cy, radius, from, to) {
  if (b.id === 'earth') return;
  ctx.fillStyle = b.id === 'moon' ? '#585e63' : '#57483c';
  const count = b.id === 'moon' ? 900 : 60;
  for (let i = 0; i < count; i++) {
    const a = i / count * TAU;
    if (wrap(a - from) < 0 || wrap(to - a) < 0) continue;
    const size = 0.0008 + ((i * 37) % 11) / 11 * 0.002, depth = ((i * 53) % 7) / 7 * 0.004;
    const r = radius * (1 - depth - size), cr = Math.max(0.6, radius * size);
    if (cr < 0.6 || (i * 29) % 3) continue;
    ctx.beginPath(); ctx.ellipse(cx + Math.sin(a) * r, cy - Math.cos(a) * r, cr * 1.6, cr, a, 0, TAU); ctx.fill();
  }
}
function drawFlight(s) {
  const near = surfaceClearance(s), b = near.body, p = bodyAt(b, s.t);
  const dx = s.x - p.x, dy = s.y - p.y, radial = Math.atan2(dx, dy);
  const altitude = Math.max(0, Math.hypot(dx, dy) - b.radius - SHIP.length / 2);
  const scale = Math.max(0.35, altitude / (ch * 0.45));
  const rx = cw * 0.48, ry = ch * 0.46, look = LOOK[b.id];
  // The local horizon follows "up" from the nearest body; physics stays in the fixed frame.
  const ground = ry + (altitude + SHIP.length / 2) / scale, bodyR = b.radius / scale;
  if (ground < ch + bodyR) {
    ctx.fillStyle = b.id === 'earth' && altitude < 25000 ? '#2b615b' : look.fill;
    ctx.beginPath(); ctx.arc(rx, ground + bodyR, bodyR, Math.PI, TAU); ctx.fill();
    if (b.id === 'earth') { ctx.strokeStyle = '#64a9bb'; ctx.lineWidth = Math.min(14, 8000 / scale + 1); ctx.stroke(); }
    ctx.strokeStyle = look.edge; ctx.lineWidth = 1; ctx.stroke();
    craters(b, rx, ground + bodyR, bodyR, -Math.PI / 2, Math.PI / 2);
  }
  if (b.id === 'earth' && altitude < 3000) {
    // The pad stays where the ship left it, at the top of the still Earth.
    const along = wrap(0 - radial) * EARTH_R / scale;
    const padX = rx + along;
    if (padX > -100 && padX < cw + 100) {
      ctx.fillStyle = '#7d8c8a'; ctx.fillRect(padX - 18 / scale, ground - 3, 36 / scale, 5);
      ctx.fillStyle = '#536f76'; ctx.fillRect(padX + 9 / scale, ground - 22 / scale, 3 / scale, 22 / scale);
    }
  }
  const ruler = scale < 3 ? 50 : scale < 30 ? 500 : scale < 300 ? 5000 : 50000;
  const rulerPx = Math.min(cw * 0.3, ruler / scale);
  line(14, ch - 50, 14 + rulerPx, ch - 50, '#688797');
  label(`${km(rulerPx * scale)}${scale > 1 ? ' · alus suurennettu' : ''}`, 14, ch - 56, '#93aebd', 'left', 8);
  const q = pointFrame(s);
  if (Math.hypot(q.vx, q.vy) > 0.3 && !s.landedOn) {
    const prograde = Math.atan2(q.vx, q.vy) - radial;
    const vpx = rx + Math.sin(prograde) * 53, vpy = ry - Math.cos(prograde) * 53;
    line(rx, ry, vpx, vpy, '#759a9e', [3, 4]); dot(vpx, vpy, 4, '#84ded0');
  }
  rocketGlyph(rx, ry, wrap(s.angle - radial), Math.max(22, Math.min(60, SHIP.length / scale, ch * 0.3)), s);
  const heading = wrap(s.angle - radial) * 180 / Math.PI;
  label(`${Math.abs(Math.round(heading))}° pystystä`, rx + 30, ry - 24, '#c4d5da', 'left', 9);
  label(b.name.toUpperCase(), cw - 12, ch - 50, '#a2bbc9', 'right', 9);
  if (near.clearance < 5000 && !s.landedOn) {
    const r = Math.hypot(dx, dy), rvx = s.vx - p.vx, rvy = s.vy - p.vy;
    const down = -(rvx * dx + rvy * dy) / r, side = Math.abs(rvx * dy - rvy * dx) / r;
    const lim = LANDING[b.id], tilt = Math.abs(heading);
    const okDown = b.id === 'rock' ? Math.hypot(rvx, rvy) <= lim.speed : down <= lim.down;
    const okSide = b.id === 'rock' ? true : side <= lim.side;
    label(`${down < 0 ? 'YLÖS' : 'ALAS'} ${Math.abs(down).toFixed(1)} m/s`, 14, 46, okDown ? '#85d6cc' : '#efa98a', 'left', 11);
    label(`SIVU ${side.toFixed(1)} m/s`, 14, 61, okSide ? '#85d6cc' : '#efa98a', 'left', 11);
    label(`KALLISTUS ${tilt.toFixed(0)}°`, 14, 76, tilt <= lim.tilt ? '#85d6cc' : '#efa98a', 'left', 11);
  }
}
function drawMap(s) {
  const path = currentPath(s), ref = refBody(s);
  const center = ref === EARTH ? EARTH : ref;
  const c0 = bodyAt(center, s.t);
  // Points are drawn relative to the centre body at their own time, so an orbit
  // around the moving Moon is a closed loop and not a smear.
  const rel = (x, y, t) => { const c = bodyAt(center, t); return { x: x - c.x, y: y - c.y }; };
  const pts = (path ? path.points : [{ x: s.x, y: s.y, t: s.t }]).map(p => rel(p.x, p.y, p.t));
  let maxR = center.radius * (center === EARTH ? 1.6 : 2.2);
  if (mapWide) maxR = center === EARTH ? MOON.orbit.r * 1.12 : center.sphere * 4;
  // Close up near the Moon or the rock, only the path inside its reach sets the zoom:
  // the part flying away again would shrink the arrival to a dot.
  else for (const p of pts) {
    const r = Math.hypot(p.x, p.y);
    if (center === EARTH || r < center.sphere) maxR = Math.max(maxR, r * 1.08);
  }
  if (center === EARTH && !mapWide) maxR = Math.min(maxR, MOON.orbit.r * 1.12);
  const scale = Math.min(cw - 30, ch - 90) / (2 * maxR), cx = cw * 0.5, cy = ch * 0.5;
  const project = (x, y) => ({ x: cx + x * scale, y: cy - y * scale });
  if (center === EARTH) {
    for (const b of [MOON, ROCK]) {
      ctx.strokeStyle = '#30485a'; ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.arc(cx, cy, b.orbit.r * scale, 0, TAU); ctx.stroke();
    }
    ctx.strokeStyle = s.trip === 'asema' ? '#6b6046' : '#30485a'; ctx.beginPath(); ctx.arc(cx, cy, STATION_R * scale, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
  }
  for (const b of BODIES) {
    const p = bodyAt(b, s.t), q = project(p.x - c0.x, p.y - c0.y), look = LOOK[b.id];
    dot(q.x, q.y, Math.max(b.id === 'rock' ? 2 : 3, b.radius * scale), look.mapFill);
    ctx.strokeStyle = look.mapEdge; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(q.x, q.y, Math.max(2, b.radius * scale), 0, TAU); ctx.stroke();
    if (q.x > -20 && q.x < cw + 20 && q.y > -20 && q.y < ch + 20) {
      const below = b === center ? 3 : -Math.max(5, b.radius * scale) - 4;
      label(look.label, q.x, q.y + below, '#9fb7c2', 'center', 9);
    }
  }
  if (s.trip === 'asema' && center === EARTH) {
    const p = station(s), q = project(p.x, p.y); dot(q.x, q.y, 3, '#f1c987'); label('ASEMA', q.x + 6, q.y + 11, '#e6cda3', 'left', 9);
  }
  // Predicted path.
  ctx.beginPath();
  pts.forEach((p, i) => { const q = project(p.x, p.y); if (i) ctx.lineTo(q.x, q.y); else ctx.moveTo(q.x, q.y); });
  ctx.strokeStyle = '#80dbcd'; ctx.lineWidth = 1.4; ctx.stroke();
  if (path && path.hit) {
    const end = project(pts[pts.length - 1].x, pts[pts.length - 1].y);
    line(end.x - 4, end.y - 4, end.x + 4, end.y + 4, '#efa98a'); line(end.x - 4, end.y + 4, end.x + 4, end.y - 4, '#efa98a');
  }
  // The trip's target body where the path passes closest, as a dashed ghost.
  const target = s.trip === 'kivi' ? ROCK : ['kuu-kierto', 'kuuhun', 'kotiin'].includes(s.trip) && !s.visited.includes('moon') ? MOON : null;
  if (target && center === EARTH && path && path.closest[target.id]) {
    const c = path.closest[target.id], b = bodyAt(target, c.t), q = project(b.x, b.y), sp = project(c.x, c.y);
    ctx.strokeStyle = '#e6bf7c'; ctx.setLineDash([2, 3]); ctx.beginPath(); ctx.arc(q.x, q.y, Math.max(4, target.radius * scale), 0, TAU); ctx.stroke(); ctx.setLineDash([]);
    dot(sp.x, sp.y, 2.5, '#e6bf7c');
    label(`lähin ${km(Math.max(0, c.d))}`, sp.x + 6, sp.y - 6, '#e6cda3', 'left', 9);
  }
  const a = project(s.x - c0.x, s.y - c0.y);
  dot(a.x, a.y, 4, '#8ce3d6'); label('SINÄ', a.x + 8, a.y - 5, '#b8eee4', 'left', 9);
  label(mapWide ? 'Napauta: lähikuva' : 'Napauta: koko kuva', cw / 2, 44, '#9eb9c7', 'center', 9);
  const o = orbitAround(center, s);
  const closed = o.energy < 0 && o.peri > (center === EARTH ? EARTH.air.top : 2000);
  label(s.landedOn ? `Pinnalla: ${body(s.landedOn).name}` : closed ? `Suljettu rata: ${center.name}` : path && path.hit ? `Rata osuu: ${path.hit.body.name}` : 'Avoin rata',
    cw / 2, ch - 50, closed ? '#85d6cc' : '#efc28a', 'center', 9);
}
function drawDock(s) {
  const d = approach(s), p = d.p;
  // Both axes follow the station: right along its motion, up away from Earth.
  const scale = Math.min(1.8, Math.max(0.25, (ch - 65) / 110), Math.max(0.00001, (cw * 0.62) / Math.max(140, d.range + 75)));
  const cx = cw * 0.75, cy = ch * 0.5;
  const project = (x, y) => ({ x: cx + ((x - p.x) * p.tx + (y - p.y) * p.ty) * scale,
    y: cy - ((x - p.x) * p.rx + (y - p.y) * p.ry) * scale });
  for (let i = 0; i < cw; i += 36) line(i, 32, i, ch - 42, '#112c3b');
  for (let i = 32; i < ch - 30; i += 36) line(0, i, cw, i, '#112c3b');
  const a = project(s.x, s.y), port = project(p.px, p.py);
  line(0, cy, port.x, cy, '#447e79', [5, 4]);
  const corridor = Math.max(3, scale * 3);
  line(0, cy - corridor, port.x, cy - corridor, '#284e4f', [2, 5]);
  line(0, cy + corridor, port.x, cy + corridor, '#284e4f', [2, 5]);
  stationGlyph(cx, cy, Math.max(0.25, scale));
  rocketGlyph(a.x, a.y, wrap(s.angle - (p.angle - Math.PI / 2)), Math.max(20, SHIP.length * scale), s);
  const dvx = s.vx - p.vx, dvy = s.vy - p.vy, vv = Math.hypot(dvx, dvy);
  if (vv > 0.005) {
    const along = (dvx * p.tx + dvy * p.ty) / vv, cross = (dvx * p.rx + dvy * p.ry) / vv;
    line(a.x, a.y, a.x + along * 32, a.y - cross * 32, '#e6bf7c');
    dot(a.x + along * 32, a.y - cross * 32, 2, '#e6bf7c');
  }
  label('PORTTI', port.x - 5, cy - 13, '#85e0d1', 'right', 9);
  label('YLÖS = POISPÄIN MAASTA', 12, 44, '#7894a6', 'left', 8);
  label(`Asemaan ${km(d.range)} · nopeusero ${d.speed.toFixed(2)} m/s`, 12, ch - 50, '#bfd5dd', 'left', 10);
  if (d.range > 1000) label('Näkymän mittakaava muuttuu etäisyyden mukana', cw / 2, 60, '#e8c287', 'center', 8);
}
function draw() {
  ctx.clearRect(0, 0, cw, ch);
  const s = ship || freshFlight();
  const near = surfaceClearance(s);
  ctx.fillStyle = view === 'flight' && near.body === EARTH && near.clearance < 30000 ? '#102d43' : '#071320';
  ctx.fillRect(0, 0, cw, ch);
  for (const star of starField) dot(star.x * cw, star.y * ch, star.a > 0.5 ? 1 : 0.6, `rgba(206,231,239,${star.a})`);
  if (view === 'map') drawMap(s); else if (view === 'dock') drawDock(s); else drawFlight(s);
}
