'use strict';
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
var cw = 360, ch = 300;
const stars = Array.from({ length: 75 }, (_, i) => ({
  x: ((i * 73.137) % 359) / 359, y: ((i * 47.29) % 211) / 211, a: 0.2 + (i % 4) * 0.15
}));
function fitCanvas() {
  const box = canvas.getBoundingClientRect();
  cw = Math.max(1, box.width); ch = Math.max(1, box.height);
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); draw();
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
  const w = size * 0.12, h = size;
  if (s.throttle && s.phase === 'flight' && !paused) {
    ctx.fillStyle = '#f5c67a'; ctx.beginPath(); ctx.moveTo(-w * 0.75, h / 2 - 1);
    ctx.lineTo(0, h / 2 + size * (0.25 + 0.17 * s.throttle)); ctx.lineTo(w * 0.75, h / 2 - 1); ctx.fill();
    ctx.fillStyle = '#e4f6fc'; ctx.beginPath(); ctx.moveTo(-w * 0.45, h / 2);
    ctx.lineTo(0, h / 2 + size * 0.2); ctx.lineTo(w * 0.45, h / 2); ctx.fill();
  }
  ctx.beginPath(); ctx.moveTo(0, -h / 2); ctx.quadraticCurveTo(w, -h * 0.35, w, -h * 0.22);
  ctx.lineTo(w, h / 2); ctx.lineTo(-w, h / 2); ctx.lineTo(-w, -h * 0.22);
  ctx.quadraticCurveTo(-w, -h * 0.35, 0, -h / 2); ctx.fillStyle = '#e3e9e6'; ctx.fill();
  ctx.fillStyle = '#83d8ce'; ctx.fillRect(-w, -h * 0.12, w * 2, h * 0.14);
  ctx.fillStyle = '#6c8996'; ctx.fillRect(-w, h * 0.33, w * 2, 2);
  if (s.stage === 0) {
    ctx.fillStyle = '#52717d'; ctx.fillRect(-w, h * 0.15, w * 2, 2);
    ctx.beginPath(); ctx.moveTo(-w, h * 0.25); ctx.lineTo(-w * 2, h / 2); ctx.lineTo(w * 2, h / 2); ctx.lineTo(w, h * 0.25); ctx.fill();
  }
  ctx.fillStyle = '#142e3f'; ctx.beginPath(); ctx.arc(0, -h * 0.26, w * 0.55, 0, TAU); ctx.fill();
  if (!paused && s.rcs > 0 && (held.forward || held.side || held.turn)) {
    ctx.strokeStyle = '#b9e8f3'; ctx.lineWidth = 2;
    const turn = held.turn || held.side;
    if (turn) { ctx.beginPath(); ctx.moveTo(-turn * w, -h * 0.25); ctx.lineTo(-turn * (w + 9), -h * 0.25); ctx.stroke(); }
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
function drawFlight(s) {
  const o = orbit(s), radial = Math.atan2(s.x, s.y);
  const altitude = Math.max(0, o.altitude), scale = Math.max(1.3, altitude / (ch * 0.55));
  const rx = cw * 0.48, ry = ch * 0.44;
  // Local horizon follows the radial direction; the physics stays inertial.
  const ground = ry + altitude / scale, earthR = EARTH / scale;
  if (ground < ch + earthR) {
    ctx.fillStyle = altitude < 60000 ? '#2b615b' : '#173f52';
    ctx.beginPath(); ctx.arc(rx, ground + earthR, earthR, Math.PI, TAU); ctx.fill();
    ctx.strokeStyle = '#64a9bb'; ctx.lineWidth = Math.min(14, 30000 / scale + 1); ctx.stroke();
    ctx.strokeStyle = '#a2cfca'; ctx.lineWidth = 1; ctx.stroke();
  }
  if (altitude < 1600) {
    const launchDrift = (s.x * Math.cos(radial) - s.y * Math.sin(radial));
    const padX = rx - (s.x - SPIN * EARTH * s.t) / scale;
    if (Math.abs(launchDrift) < 1e6 && padX > -100 && padX < cw + 100) {
      ctx.fillStyle = '#7d8c8a'; ctx.fillRect(padX - 38 / scale, ground - 3, 76 / scale, 5);
      ctx.fillStyle = '#536f76'; ctx.fillRect(padX + 12 / scale, ground - 48 / scale, 5 / scale, 48 / scale);
    }
  }
  // A local ruler makes clear that the rocket is enlarged for visibility.
  const ruler = scale < 10 ? 50 : scale < 1000 ? 10000 : 100000;
  const rulerPx = Math.min(cw * 0.3, ruler / scale);
  line(14, ch - 19, 14 + rulerPx, ch - 19, '#688797');
  label(`${distance(rulerPx * scale)} · alus suurennettu`, 14, ch - 26, '#93aebd', 'left', 8);
  const prograde = Math.atan2(s.vx, s.vy) - radial;
  const vpx = rx + Math.sin(prograde) * 53, vpy = ry - Math.cos(prograde) * 53;
  line(rx, ry, vpx, vpy, '#759a9e', [3, 4]); dot(vpx, vpy, 4, '#84ded0');
  rocketGlyph(rx, ry, wrap(s.angle - radial), Math.min(68, ch * 0.38), s);
  const heading = wrap(s.angle - radial) * 180 / Math.PI;
  label(`${heading.toFixed(1)}° pystystä`, rx + 30, ry - 28, '#c4d5da', 'left', 9);
  label(`VAIHE ${s.stage + 1} / 2`, cw - 12, ch - 20, '#a2bbc9', 'right', 9);
  if (o.altitude > 150000) label('Vihreä piste = liikesuunta', cw / 2, 43, '#7da9ae', 'center', 9);
}
function orbitalPath(s, project) {
  const o = orbit(s), h = o.h;
  if (Math.abs(h) < 1) return;
  const r = o.r, v2 = s.vx ** 2 + s.vy ** 2, rv = s.x * s.vx + s.y * s.vy;
  const ex = ((v2 - MU / r) * s.x - rv * s.vx) / MU;
  const ey = ((v2 - MU / r) * s.y - rv * s.vy) / MU;
  const e = Math.hypot(ex, ey), pe = Math.atan2(ex, ey), l = h * h / MU;
  ctx.beginPath(); let pen = false;
  for (let i = 0; i <= 240; i++) {
    const a = i / 240 * TAU, denom = 1 + e * Math.cos(a - pe);
    const rad = l / denom;
    if (denom <= 0 || rad < EARTH || rad > 1e9) { pen = false; continue; }
    const p = project(rad * Math.sin(a), rad * Math.cos(a));
    if (pen) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y);
    pen = true;
  }
  ctx.strokeStyle = '#80dbcd'; ctx.lineWidth = 1.4; ctx.stroke();
}
function drawMap(s) {
  const o = orbit(s), p = station(s);
  const maxR = Math.max(STATION_R * 1.14, o.r * 1.12, Math.min(EARTH * 3, Number.isFinite(o.apo) ? EARTH + o.apo : EARTH * 2));
  const scale = Math.min(cw - 35, ch - 80) / (2 * maxR);
  const cx = cw * 0.5, cy = ch * 0.5;
  const project = (x, y) => ({ x: cx + x * scale, y: cy - y * scale });
  ctx.strokeStyle = '#436679'; ctx.setLineDash([3, 4]); ctx.beginPath(); ctx.arc(cx, cy, STATION_R * scale, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
  dot(cx, cy, EARTH * scale, '#163e50');
  ctx.strokeStyle = '#497e91'; ctx.beginPath(); ctx.arc(cx, cy, EARTH * scale, 0, TAU); ctx.stroke();
  // Quiet latitude/longitude suggestions, all local vector art.
  ctx.save(); ctx.beginPath(); ctx.arc(cx, cy, EARTH * scale, 0, TAU); ctx.clip();
  ctx.strokeStyle = '#245064';
  for (const k of [-0.55, 0, 0.55]) { ctx.beginPath(); ctx.ellipse(cx, cy, EARTH * scale * Math.max(0.1, 1 - Math.abs(k)), EARTH * scale, 0, 0, TAU); ctx.stroke(); }
  ctx.restore(); label('MAA', cx, cy + 3, '#789da9', 'center', 10);
  orbitalPath(s, project);
  const a = project(s.x, s.y), b = project(p.x, p.y);
  dot(a.x, a.y, 4, '#8ce3d6'); label('SINÄ', a.x + 8, a.y - 5, '#b8eee4', 'left', 9);
  dot(b.x, b.y, 3, '#f1c987'); label('ASEMA', b.x + 7, b.y + 12, '#e6cda3', 'left', 9);
  label('Vihreä: oma rata   ·   Katkoviiva: aseman rata', cw / 2, 44, '#9eb9c7', 'center', 9);
  label(o.peri > 150000 ? 'Suljettu rata ilmakehän yläpuolella' : 'Rata leikkaa ilmakehän tai maan', cw / 2, ch - 47, o.peri > 150000 ? '#85d6cc' : '#efc28a', 'center', 9);
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
  const corridor = Math.max(3, scale * 2);
  line(0, cy - corridor, port.x, cy - corridor, '#284e4f', [2, 5]);
  line(0, cy + corridor, port.x, cy + corridor, '#284e4f', [2, 5]);
  stationGlyph(cx, cy, Math.max(0.25, scale));
  rocketGlyph(a.x, a.y, wrap(s.angle - (p.angle - Math.PI / 2)), Math.max(20, STAGES[s.stage].length * scale), s);
  const dvx = s.vx - p.vx, dvy = s.vy - p.vy;
  const vv = Math.hypot(dvx, dvy);
  if (vv > 0.005) {
    const along = (dvx * p.tx + dvy * p.ty) / vv, cross = (dvx * p.rx + dvy * p.ry) / vv;
    line(a.x, a.y, a.x + along * 32, a.y - cross * 32, '#e6bf7c');
    dot(a.x + along * 32, a.y - cross * 32, 2, '#e6bf7c');
  }
  label('PORTTI', port.x - 5, cy - 13, '#85e0d1', 'right', 9);
  label('YLÖS = POISPÄIN MAASTA', 12, 44, '#7894a6', 'left', 8);
  label(`Asemaan ${distance(d.range)} · suhteellinen ${d.speed.toFixed(2)} m/s`, 12, ch - 47, '#bfd5dd', 'left', 10);
  if (d.range > 1000) label('Näkymän mittakaava muuttuu etäisyyden mukana', cw / 2, 60, '#e8c287', 'center', 8);
}
function draw() {
  ctx.clearRect(0, 0, cw, ch);
  const s = ship || freshFlight();
  const alt = Math.hypot(s.x, s.y) - EARTH;
  ctx.fillStyle = view === 'flight' && alt < 80000 ? '#102d43' : '#071320'; ctx.fillRect(0, 0, cw, ch);
  for (const star of stars) dot(star.x * cw, star.y * ch, star.a > 0.5 ? 1 : 0.6, `rgba(206,231,239,${star.a})`);
  if (view === 'map') drawMap(s); else if (view === 'dock') drawDock(s); else drawFlight(s);
  if (s.practice) label('HARJOITUS', cw - 12, 31, '#e5c28d', 'right', 8);
}
