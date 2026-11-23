'use strict';
// One view (#548): the camera zooms itself. Near a surface it frames the ship and the ground
// under it; in space it frames the ship, the path ahead and the body it circles, so a whole
// orbit is on screen. World y is up; the camera never turns, so a drag on screen is a direction
// in the world.
const canvas = document.getElementById('c'), ctx = canvas.getContext('2d');
var cam = { x: 0, y: EARTH.radius, scale: 20 }, camReady = false, path = null, view = { w: 360, h: 640, top: 56, bottom: 96 };
const SKY = Array.from({ length: 90 }, (_, i) => ({ x: (i * 7919 % 997) / 997, y: (i * 104729 % 991) / 991, r: i % 7 === 0 ? 1.4 : 0.8 }));

function closeUp(s) {
  const nb = nearestSurface(s), b = nb.body;
  return (s.landedOn || nb.alt < Math.max(b.radius * 0.45, 10)) ? nb : null;
}
// The box the camera wants: { x, y, half } (half the shorter side, in metres).
function cameraTarget(s, p, h) {
  const near = closeUp(s);
  if (near) {
    const b = near.body, c = bodyAt(b, s.t), r = Math.hypot(s.x - c.x, s.y - c.y);
    const gx = c.x + (s.x - c.x) / r * b.radius, gy = c.y + (s.y - c.y) / r * b.radius;
    const half = Math.max(near.alt * 0.8 + 6, b === ROCK ? b.radius * 1.8 : 9);
    return { x: (s.x + gx) / 2, y: (s.y + gy) / 2, half };
  }
  let x0 = s.x, x1 = s.x, y0 = s.y, y1 = s.y;
  const add = (x, y, r = 0) => { x0 = Math.min(x0, x - r); x1 = Math.max(x1, x + r); y0 = Math.min(y0, y - r); y1 = Math.max(y1, y + r); };
  if (p) {
    const f = bodyAt(p.frame, s.t);
    add(f.x, f.y, p.frame.radius * 1.1);
    for (const q of p.points) add(q.x, q.y);
  }
  if (h && (h.target || h.ghost)) {
    const b = BODY[(h.target || h.ghost.id)], q = bodyAt(b, h.ghost ? h.ghost.t : s.t);
    add(q.x, q.y, b.radius * 1.5);
  }
  if (h && h.station) { const st = stationAt(s.t); add(st.x, st.y, 2); }
  const limit = MOON.orbit.r + MOON.sphere;
  x0 = Math.max(x0, -limit); x1 = Math.min(x1, limit); y0 = Math.max(y0, -limit); y1 = Math.min(y1, limit);
  const aspect = Math.max(1, view.w - 160) / Math.max(1, view.h - view.top - view.bottom - 80);
  const halfW = (x1 - x0) / 2 * 1.12, halfH = (y1 - y0) / 2 * 1.12;
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, half: Math.max(halfH, halfW / aspect, 8), aspect };
}
function moveCamera(dt, h) {
  if (!ship) return;
  // Keep room around the framed things for the hint arrow (up to 90 px from the ship).
  const t = cameraTarget(ship, path, h), usable = Math.max(1, view.h - view.top - view.bottom - 80);
  const wide = Math.max(1, view.w - 160);
  const scale = (t.aspect ? usable : Math.min(usable, wide)) / (2 * t.half);
  if (!camReady) { cam = { x: t.x, y: t.y, scale }; camReady = true; return; }
  const k = 1 - Math.exp(-dt * 4);
  cam.x += (t.x - cam.x) * k; cam.y += (t.y - cam.y) * k;
  cam.scale = Math.exp(Math.log(cam.scale) + (Math.log(scale) - Math.log(cam.scale)) * k);
}
function sx(x) { return view.w / 2 + (x - cam.x) * cam.scale; }
function sy(y) { return view.top + (view.h - view.top - view.bottom) / 2 - (y - cam.y) * cam.scale; }

function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2), w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  view.w = w; view.h = h;
  const land = w > h;
  view.top = land ? 48 : 56; view.bottom = land ? 70 : 110;
}

function drawBody(b, t, alpha = 1) {
  const p = bodyAt(b, t), x = sx(p.x), y = sy(p.y), r = Math.max(b.radius * cam.scale, 3);
  if (x + r < -50 || x - r > view.w + 50 || y + r < -50 || y - r > view.h + 50) return;
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU);
  if (b === EARTH) {
    const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
    g.addColorStop(0, '#5aa8f0'); g.addColorStop(1, '#1f4f9a'); ctx.fillStyle = g; ctx.fill();
    ctx.save(); ctx.clip(); ctx.fillStyle = '#3f9b55';
    for (const [a, d, s] of [[0, 0.75, 0.38], [2.1, 0.5, 0.33], [3.9, 0.65, 0.3], [5.2, 0.2, 0.25]]) {
      ctx.beginPath(); ctx.arc(x + Math.sin(a) * r * d, y - Math.cos(a) * r * d, r * s, 0, TAU); ctx.fill();
    }
    ctx.restore();
    ctx.beginPath(); ctx.arc(x, y, r + Math.max(2, r * 0.04), 0, TAU); ctx.strokeStyle = 'rgba(140,200,255,.35)'; ctx.lineWidth = Math.max(2, r * 0.05); ctx.stroke();
    // The launch pad on top.
    ctx.fillStyle = '#d7dde2'; ctx.fillRect(x - Math.max(3, cam.scale * 1.4), y - r - Math.max(1.5, cam.scale * 0.2), Math.max(6, cam.scale * 2.8), Math.max(1.5, cam.scale * 0.2));
  } else if (b === MOON) {
    ctx.fillStyle = '#bfc4cc'; ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = '#9ea4ae';
    for (const [a, d, s] of [[0.5, 0.5, 0.2], [2.5, 0.6, 0.15], [4.3, 0.3, 0.24], [5.6, 0.7, 0.12]]) {
      ctx.beginPath(); ctx.arc(x + Math.sin(a) * r * d, y - Math.cos(a) * r * d, r * s, 0, TAU); ctx.fill();
    }
    ctx.restore();
  } else { ctx.fillStyle = '#9c7f62'; ctx.fill(); }
  ctx.restore();
}
// The base's parts, drawn standing on the ground (y up from 0) in a box `u` metres to a unit.
function drawPart(id, u) {
  if (id === 'paneeli') {
    ctx.fillStyle = '#9aa3ad'; ctx.fillRect(-0.08 * u, -0.9 * u, 0.16 * u, 0.9 * u);
    ctx.fillStyle = '#3d7fd6'; ctx.fillRect(-1.1 * u, -1.25 * u, 2.2 * u, 0.42 * u);
    ctx.strokeStyle = '#a9d1ff'; ctx.lineWidth = Math.max(1, 0.05 * u); ctx.strokeRect(-1.1 * u, -1.25 * u, 2.2 * u, 0.42 * u);
  } else if (id === 'tankki') {
    ctx.fillStyle = '#eef2f5'; ctx.beginPath(); ctx.ellipse(0, -0.75 * u, 0.75 * u, 0.75 * u, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = '#e2574c'; ctx.fillRect(-0.75 * u, -0.82 * u, 1.5 * u, 0.14 * u);
  } else if (id === 'tehdas') {
    ctx.fillStyle = '#c9b27a'; ctx.fillRect(-0.9 * u, -1 * u, 1.8 * u, 1 * u);
    ctx.fillStyle = '#8b7b55'; ctx.fillRect(0.35 * u, -1.6 * u, 0.3 * u, 0.6 * u);
    ctx.fillStyle = '#ffd65a'; ctx.fillRect(-0.6 * u, -0.7 * u, 0.4 * u, 0.3 * u);
  }
}
// Where each part stands in the base, as an angle off its middle (radians round the Moon).
const PART_SPOT = { paneeli: -0.22, tankki: 0, tehdas: 0.22 };
function drawBase(s, now) {
  const m = bodyAt(MOON, s.t), r = MOON.radius * cam.scale;
  if (r < 6) return;
  const trip = TRIP[s.trip];
  // The zone to land in, glowing on a part trip.
  if (trip.part) {
    const a0 = BASE.a - BASE.zone, a1 = BASE.a + BASE.zone;
    ctx.save(); ctx.beginPath(); ctx.arc(sx(m.x), sy(m.y), r + 2, a0 - Math.PI / 2, a1 - Math.PI / 2);
    ctx.strokeStyle = `rgba(255,214,90,${0.5 + 0.4 * pulse(now)})`; ctx.lineWidth = Math.max(3, cam.scale * 0.3); ctx.stroke(); ctx.restore();
  }
  for (const id of Object.keys(PART_SPOT)) {
    if (!baseBuilt(id) && !(ship.phase === 'done' && ship.trip === id)) continue;
    const a = BASE.a + PART_SPOT[id];
    ctx.save(); ctx.translate(sx(m.x + Math.sin(a) * MOON.radius), sy(m.y + Math.cos(a) * MOON.radius)); ctx.rotate(a);
    drawPart(id, Math.max(1.2 * cam.scale, 3)); ctx.restore();
  }
}
// The rockets: Raketti white and red; Kiitäjä slim and blue; Rahtiraketti wide and grey. A part
// on its way rides on the nose.
function drawShip(s) {
  const kind = TRIP[s.trip].rocket || 'raketti', x = sx(s.x), y = sy(s.y), len = Math.max(16, SHIP.size * 2.4 * cam.scale);
  const wide = kind === 'rahti' ? 1.35 : kind === 'kiitaja' ? 0.8 : 1;
  ctx.save(); ctx.translate(x, y); ctx.rotate(s.angle);
  if (s.thrust > 0) {
    const f = len * (0.4 + 0.6 * s.thrust / SHIP.acc) * (0.85 + Math.random() * 0.3);
    ctx.fillStyle = '#ffb347'; ctx.beginPath(); ctx.moveTo(-len * 0.18 * wide, len * 0.4); ctx.lineTo(0, len * 0.4 + f); ctx.lineTo(len * 0.18 * wide, len * 0.4); ctx.fill();
  }
  ctx.fillStyle = kind === 'rahti' ? '#c3cad1' : '#f3f6f8';
  ctx.beginPath(); ctx.moveTo(0, -len * 0.55); ctx.lineTo(len * 0.22 * wide, len * 0.25); ctx.lineTo(-len * 0.22 * wide, len * 0.25); ctx.fill();
  ctx.fillStyle = kind === 'kiitaja' ? '#3d9be0' : kind === 'rahti' ? '#e89a3c' : '#e2574c';
  ctx.beginPath(); ctx.moveTo(len * 0.22 * wide, len * 0.25); ctx.lineTo(len * 0.34 * wide, len * 0.45); ctx.lineTo(-len * 0.34 * wide, len * 0.45); ctx.lineTo(-len * 0.22 * wide, len * 0.25); ctx.fill();
  if (TRIP[s.trip].part && s.phase !== 'done') { ctx.translate(0, -len * 0.42); drawPart(s.trip, len * 0.24); }
  ctx.restore();
}
function drawStation(s) {
  const st = stationAt(s.t), x = sx(st.x), y = sy(st.y), w = Math.max(10, 3 * cam.scale);
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = '#7fb6e8'; ctx.fillRect(-w, -w * 0.18, w * 0.7, w * 0.36); ctx.fillRect(w * 0.3, -w * 0.18, w * 0.7, w * 0.36);
  ctx.fillStyle = '#e8edf1'; ctx.fillRect(-w * 0.3, -w * 0.3, w * 0.6, w * 0.6);
  ctx.restore();
}
function ring(x, y, r, color, width = 2, dash = null) {
  ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.strokeStyle = color; ctx.lineWidth = width;
  if (dash) ctx.setLineDash(dash); ctx.stroke(); ctx.restore();
}
function pulse(now) { return 0.5 + 0.5 * Math.sin(now / 180); }
function drawPath(s, p, h, now) {
  if (!p || p.points.length < 2) return;
  const ready = (s.trip === 'kiertorata' && orbitReady(EARTH, s)) || (s.trip === 'kuu-kierto' && orbitReady(MOON, s));
  ctx.save(); ctx.lineWidth = 2; ctx.setLineDash([4, 6]);
  ctx.strokeStyle = ready ? '#62e88a' : 'rgba(255,255,255,.75)';
  ctx.beginPath(); ctx.moveTo(sx(s.x), sy(s.y));
  for (const q of p.points) ctx.lineTo(sx(q.x), sy(q.y));
  ctx.stroke(); ctx.restore();
  if (p.hit) {
    const x = sx(p.hit.x), y = sy(p.hit.y);
    ctx.save(); ctx.strokeStyle = '#ff6a5a'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x - 6, y - 6); ctx.lineTo(x + 6, y + 6); ctx.moveTo(x + 6, y - 6); ctx.lineTo(x - 6, y + 6); ctx.stroke(); ctx.restore();
  }
}
function drawHint(s, h, now) {
  if (!h) return;
  if (h.ghost) drawBody(BODY[h.ghost.id], h.ghost.t, 0.35);
  if (h.target) { const b = BODY[h.target], q = bodyAt(b, s.t); ring(sx(q.x), sy(q.y), Math.max(b.radius * cam.scale, 3) + 8 + 6 * pulse(now), 'rgba(255,214,90,.8)', 2); }
  if (h.station) { const st = stationAt(s.t); ring(sx(st.x), sy(st.y), 14 + 5 * pulse(now), 'rgba(255,214,90,.8)', 2); }
  if (h.mark) {
    const x = sx(h.mark.x), y = sy(h.mark.y);
    ring(x, y, 7 + 5 * pulse(now), '#ffd65a', 3);
    ctx.save(); ctx.fillStyle = '#ffd65a'; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.fill();
    if (h.word === 'Odota' && h.wait >= 1.5) {
      // The wait's seconds beside the spot, as on the button.
      ctx.font = '700 14px system-ui,sans-serif'; ctx.textBaseline = 'middle';
      const text = `${Math.ceil(h.wait)} s`, w = ctx.measureText(text).width;
      const tx = clamp(x + 16, 6, view.w - w - 6), ty = clamp(y - 14, view.top + 10, view.h - view.bottom - 10);
      ctx.fillStyle = 'rgba(8,18,28,.75)'; ctx.fillRect(tx - 4, ty - 10, w + 8, 20);
      ctx.fillStyle = '#ffd65a'; ctx.fillText(text, tx, ty + 1);
    }
    ctx.restore();
  }
  if (h.dir === undefined || s.phase !== 'flight') return;
  // The arrow: drag this way, this hard. It brightens while the finger agrees.
  const agree = stick.power > 0 && Math.abs(wrap(stick.angle - h.dir)) < 0.35;
  const x = sx(s.x), y = sy(s.y), len = 34 + 56 * (h.power ?? 1);
  ctx.save(); ctx.translate(x, y); ctx.rotate(h.dir);
  ctx.globalAlpha = agree ? 1 : 0.55 + 0.35 * pulse(now);
  ctx.strokeStyle = agree ? '#62e88a' : '#ffd65a'; ctx.lineWidth = 4; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(0, -18); ctx.lineTo(0, -len); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-9, -len + 10); ctx.lineTo(0, -len); ctx.lineTo(9, -len + 10); ctx.stroke();
  ctx.restore();
}
function drawSpeed(s) {
  if (s.phase !== 'flight' || s.landedOn) return;
  let b = null, v = 0, lim = 0;
  if (s.trip === 'asema') { const d = stationRelative(s); if (d.dist < 30) { v = d.speed; lim = STATION.speed; b = true; } }
  if (!b) {
    const nb = nearestSurface(s);
    if (nb.alt > 30) return;
    v = relative(nb.body, s).speed; lim = nb.body.land; b = nb.body;
  }
  const color = v <= lim / 2 ? '#62e88a' : v <= lim ? '#ffd65a' : '#ff6a5a';
  ctx.save(); ctx.font = '600 15px system-ui,sans-serif'; ctx.textBaseline = 'middle';
  const text = `${v.toFixed(1)} m/s`, w = ctx.measureText(text).width + 14;
  // Beside the ship, but always whole on the screen.
  const x = clamp(sx(s.x) + 22, 8, view.w - w - 8), y = clamp(sy(s.y) - 22, view.top + 14, view.h - view.bottom - 14);
  ctx.fillStyle = 'rgba(8,18,28,.8)'; ctx.fillRect(x, y - 12, w, 24);
  ctx.fillStyle = color; ctx.fillText(text, x + 7, y + 1); ctx.restore();
}
function drawStick() {
  if (!stick.on) return;
  const r = STICK_RANGE;
  ring(stick.ox, stick.oy, r, 'rgba(255,255,255,.25)', 2);
  ctx.save(); ctx.fillStyle = 'rgba(255,255,255,.35)';
  ctx.beginPath(); ctx.arc(stick.ox + stick.dx, stick.oy + stick.dy, 22, 0, TAU); ctx.fill(); ctx.restore();
}
function draw(h, now = performance.now()) {
  resize();
  const g = ctx.createLinearGradient(0, 0, 0, view.h); g.addColorStop(0, '#050b14'); g.addColorStop(1, '#0b1a2b');
  ctx.fillStyle = g; ctx.fillRect(0, 0, view.w, view.h);
  ctx.fillStyle = 'rgba(255,255,255,.55)';
  for (const st of SKY) ctx.fillRect(st.x * view.w, st.y * view.h, st.r, st.r);
  if (!ship) return;
  // Faint circles where the Moon, the rock and the station travel.
  for (const b of [MOON, ROCK]) ring(sx(0), sy(0), b.orbit.r * cam.scale, 'rgba(255,255,255,.08)', 1);
  if (ship.trip === 'asema') ring(sx(0), sy(0), STATION.r * cam.scale, 'rgba(127,182,232,.2)', 1, [3, 5]);
  for (const b of BODIES) drawBody(b, ship.t);
  drawBase(ship, now);
  if (ship.trip === 'asema') drawStation(ship);
  drawPath(ship, path, h, now);
  drawHint(ship, h, now);
  drawShip(ship);
  drawSpeed(ship);
  drawStick();
}
