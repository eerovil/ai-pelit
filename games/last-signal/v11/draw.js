'use strict';
// Drawing the sea, the iceberg, the sites, the dark and the lamps, SISU inside and out, the sonar; the stick and
// the main loop, which starts the game.
// ---------- drawing ----------
const cv = $('c'), ctx = cv.getContext('2d');
const dark = document.createElement('canvas'), dctx = dark.getContext('2d');
let W = 360, H = 740, DPR = 1;
function resize() {
  const r = cv.getBoundingClientRect();
  W = r.width || innerWidth; H = r.height || innerHeight;
  DPR = Math.min(devicePixelRatio || 1, 2);
  cv.width = dark.width = Math.round(W * DPR);
  cv.height = dark.height = Math.round(H * DPR);
}
addEventListener('resize', resize);
resize();

function polyPath(c, pts) { c.beginPath(); pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y)); c.closePath(); }
function hullPath(c) {
  c.beginPath();
  c.moveTo(-12, -2.3); c.lineTo(10, -2.3);
  c.quadraticCurveTo(14.4, -2.2, 14.4, 0); c.quadraticCurveTo(14.4, 2.2, 10, 2.3);
  c.lineTo(-11, 2.3); c.quadraticCurveTo(-14, 1.6, -14, 0); c.quadraticCurveTo(-14, -1.8, -12, -2.3);
  c.closePath();
}
function draw() {
  syncMaps();
  const sc = G.sc, ox = W / 2 - G.cx * sc, oy = H / 2 - G.cy * sc;
  G.view = { ox, oy, sc };
  const X0 = -ox / sc, X1 = (W - ox) / sc, Y0 = -oy / sc, Y1 = (H - oy) / sc;
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  // sky and water
  const sy = oy;
  if (sy > 0) {
    const g = ctx.createLinearGradient(0, sy - 120 * sc, 0, sy);
    g.addColorStop(0, '#0d1b33'); g.addColorStop(0.7, '#3a5378'); g.addColorStop(1, '#c79a8a');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, Math.min(H, sy));
  }
  const wg = ctx.createLinearGradient(0, sy, 0, sy + 320 * sc);
  wg.addColorStop(0, '#2a6f95'); wg.addColorStop(0.25, '#0f3d5e'); wg.addColorStop(1, '#020a14');
  ctx.fillStyle = wg; ctx.fillRect(0, Math.max(0, sy), W, H);

  ctx.save(); ctx.translate(ox, oy); ctx.scale(sc, sc);
  // light shafts: under the ice (v6) daylight comes down only through the openings
  ctx.globalAlpha = 0.09; ctx.fillStyle = '#bfe8ff';
  for (const [a, b] of HOLES) {
    if (b < X0 - 40 || a > X1 + 10) continue;
    for (let x = a + 4; x < b - 4; x += 9) {
      const s = Math.sin(x * 7.3 + G.t * 0.2) * 2;
      ctx.beginPath(); ctx.moveTo(x + s, ICE_Y); ctx.lineTo(x + s + 4, ICE_Y); ctx.lineTo(x + s + 20, 90); ctx.lineTo(x + s + 10, 90); ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
  drawGlacier();
  drawBerg(X0, X1);
  drawFloor(X0, X1, Y1);
  if (X1 > 3900) drawDeep(X0, X1);
  for (const s of SITES) if (s.x < X1 && s.x + s.w * C > X0 && s.y < Y1 && s.y + s.h * C > Y0) drawSite(s);
  drawIce(X0, X1);
  // the sea surface, open only in the openings (v6)
  ctx.strokeStyle = 'rgba(200,235,255,.6)'; ctx.lineWidth = 0.4;
  for (const [a, b] of HOLES) {
    if (b < X0 || a > X1) continue;
    ctx.beginPath();
    for (let x = a; x <= b; x += 1) { const y = Math.sin(x * 0.2 + G.t * 1.5) * 0.18; x === a ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
    ctx.stroke();
  }
  ctx.restore();

  drawDark(ox, oy, sc);

  ctx.save(); ctx.translate(ox, oy); ctx.scale(sc, sc);
  drawBeams();
  drawLayout();
  drawCaveLines(ctx, X0, X1, Y0, Y1, Math.max(0.12, 1.1 / sc), bergView() ? 'rgba(150,215,245,.55)' : 'rgba(20,60,90,.5)');
  // v9 (#160): inside the dark iceberg everything drawn over the dark — finds, SISU, guides, hoses, divers, the spear,
  // bubbles — shows only outside the berg or where a lamp lights it; the mapped wall outlines above stay.
  if (G.lit) {
    ctx.save(); ctx.beginPath(); ctx.rect(X0 - 50, Y0 - 50, X1 - X0 + 100, Y1 - Y0 + 100);
    BERG.poly.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); ctx.clip('evenodd');
    drawOverlays(X0, X1, Y0, Y1); ctx.restore();
    ctx.save(); polyPath(ctx, BERG.poly); ctx.clip(); ctx.beginPath();
    for (const p of G.lit) { for (let k = 0; k < p.length; k += 2) k ? ctx.lineTo(p[k], p[k + 1]) : ctx.moveTo(p[k], p[k + 1]); ctx.closePath(); }
    ctx.clip(); drawOverlays(X0, X1, Y0, Y1); ctx.restore();
  } else drawOverlays(X0, X1, Y0, Y1);
  ctx.restore();
  // marine snow
  ctx.fillStyle = 'rgba(210,235,255,.35)';
  if (!G.lit) for (const p of snow) {
    const x = ((p.x * W - G.cx * sc * 0.3 * p.z) % W + W) % W, y = ((p.y * H - G.cy * sc * 0.3 * p.z + G.t * 8 * p.z) % H + H) % H;
    if (y > sy) ctx.fillRect(x, y, 1.4 * p.z, 1.4 * p.z);
  }
  if (G.mode === 'ice') drawWeather(oy);
  if (G.s && G.mode !== 'menu') drawSonar(ox, oy, sc);
  if (net) drawNames(ox, oy, sc);
  window.drawn = true;
}
// Everything drawn over the dark: finds, fish, SISU, guides, hoses, divers, walkers, bubbles and sparkles.
function drawOverlays(X0, X1, Y0, Y1) {
  drawItems(X0, X1, Y0, Y1);
  if (G.s && X0 < 1700) drawSchools(X0, X1, Y0, Y1);
  if (X1 > 3200) drawFish();
  drawSub();
  if (G.s) drawGuides(X0, X1, Y0, Y1);
  if (net) for (const o of Object.values(net.others)) if (o.mode === 'dive' && o.hose) {
    const pts = []; for (let k = 2; k + 1 < o.hose.length; k += 2) pts.push([o.hose[k], o.hose[k + 1], 0]);
    drawHose(pts, o, !!o.hose[0], +o.hose[1] || 0);
  }
  if (G.mode === 'dive' && diver.kit === 'hose') drawHose(hose.pts, diver, hose.cut, hose.wear);
  if (net) for (const [id, o] of Object.entries(net.others)) if (o.mode === 'dive') drawDiver(o, net.cols[id]);
  if (G.mode === 'dive') drawDiver(diver, net && net.cols[R.me]);
  if (G.mode === 'dive' && G.spear) drawSpear(G.spear);
  // On the ice (v6): a friend inside the station shows only while this phone's person is inside too.
  const seeIn = G.mode === 'ice' && inStation(walker.x);
  if (net) for (const [id, o] of Object.entries(net.others)) if (o.mode === 'ice' && (seeIn || !inStation(o.x))) drawCrew(o, net.cols[id]);
  if (G.mode === 'ice') drawCrew(walker, net && net.cols[R.me]);
  ctx.fillStyle = 'rgba(220,240,255,.5)';
  for (const b of bubbles) { ctx.beginPath(); ctx.arc(b.x, b.y, 0.12 + b.t * 0.05, 0, 7); ctx.fill(); }
  if (G.s && G.mode === 'dive') sparkles();
}
function drawGlacier() {
  const top = [[0, -64], [12, -66], [22, -58], [30, -61], [40, -44], [44, -28], [38, -14], [42, -6], [34, 0], [0, 0]];
  ctx.fillStyle = '#dcebf5'; polyPath(ctx, top); ctx.fill();
  ctx.fillStyle = '#a9c6dc'; polyPath(ctx, [[22, -58], [30, -61], [40, -44], [44, -28], [38, -14], [32, -30]]); ctx.fill();
  const under = [[0, 0]];
  for (let y = 0; y <= 120; y += 10) under.push([glacierX(y) + Math.sin(y * 0.5) * 1.5, y]);
  under.push([0, 120]);
  const g = ctx.createLinearGradient(0, 0, 0, 120); g.addColorStop(0, '#6fb0d6'); g.addColorStop(1, '#1d4a6b');
  ctx.fillStyle = g; polyPath(ctx, under); ctx.fill();
  // the ice shelf and the abandoned station on it
  ctx.fillStyle = '#d3e6f2'; ctx.fillRect(30, -2.5, SHELF_X - 30, 2.5);
  ctx.fillStyle = '#8fbcd8'; polyPath(ctx, [[30, 0], [SHELF_X, 0], [SHELF_X - 4, SHELF_Y], [34, SHELF_Y]]); ctx.fill();
  ctx.fillStyle = '#5d6970';
  for (const x of [156, 176, 196, 206]) ctx.fillRect(x, SHELF_Y, 1.2, 22 - SHELF_Y);
  // v6: a snow drift from the shelf down to the sea ice
  ctx.fillStyle = '#e6f0f6'; polyPath(ctx, [[SHELF_X - 2, STATION.floor], [SHELF_X + 6, ICE_TOP - 0.25], [SHELF_X + 6, ICE_TOP + 0.6], [SHELF_X - 2, 0.6]]); ctx.fill();
  drawStation();
}
// The station on the ice (v6): a long hut of five rooms on the shelf, a radio mast with a red light, a dish. Seen
// from inside (this phone's person in it) the wall comes off and the rooms show, like SISU's inside.
function drawStation() {
  const { x0, x1, floor: f, roof: r } = STATION, open = G.mode === 'ice' && inStation(walker.x);
  ctx.strokeStyle = '#4b555c'; ctx.lineWidth = 0.35;
  ctx.beginPath(); ctx.moveTo(140, r); ctx.lineTo(143, -30); ctx.lineTo(146, r); ctx.moveTo(141, -14); ctx.lineTo(145, -14);
  ctx.moveTo(141.6, -22); ctx.lineTo(144.4, -22); ctx.stroke();
  ctx.fillStyle = (G.t % 2 < 1) ? '#ff4030' : '#601810'; ctx.beginPath(); ctx.arc(143, -30.6, 0.7, 0, 7); ctx.fill();
  ctx.fillStyle = '#2a3a52'; ctx.fillRect(202, r - 5, 0.3, 5);
  ctx.beginPath(); ctx.ellipse(203.4, r - 5.4, 1.6, 0.7, -0.5, 0, 7); ctx.fill();
  ctx.fillStyle = '#3a454c'; for (let x = x0 + 2; x < x1; x += 15) ctx.fillRect(x, f - 0.3, 1.4, 0.3);  // skids
  if (!open) {
    ctx.fillStyle = '#5a666e'; ctx.fillRect(x0, r, x1 - x0, f - 0.3 - r);
    ctx.fillStyle = '#8a2e22'; ctx.fillRect(x0, r + 0.6, x1 - x0, 0.5);
    ctx.fillStyle = '#1c2429';
    for (const s of SROOMS) if (s.id !== 'seteinen') for (let x = s.x0 + 4; x < s.x1 - 3; x += 7) ctx.fillRect(x, r + 1.6, 2.4, 1.2);
    ctx.fillStyle = '#c8d6de'; ctx.fillRect(x1 - 3.2, r + 1.4, 1.8, f - 0.3 - r - 1.4);  // the door
    ctx.fillStyle = '#e8d7a8'; ctx.font = '700 1.2px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('A-3', x1 - 8, r + 2.2);
  } else drawStationInside();
  ctx.fillStyle = '#eef6fb'; ctx.fillRect(x0 - 0.4, r - 0.45, x1 - x0 + 0.8, 0.5);  // snow on the roof
}
function drawStationInside() {
  const { x0, x1, floor: f, roof: r } = STATION, fl = f - 0.3;
  for (const s of SROOMS) {
    ctx.fillStyle = s.id === walker.room ? '#3f4a50' : '#333d43'; ctx.fillRect(s.x0, r, s.x1 - s.x0, fl - r);
    const g = ctx.createRadialGradient((s.x0 + s.x1) / 2, r + 0.4, 0, (s.x0 + s.x1) / 2, r + 0.4, (s.x1 - s.x0) * 0.6);
    g.addColorStop(0, 'rgba(220,235,255,.22)'); g.addColorStop(1, 'rgba(220,235,255,0)');
    ctx.fillStyle = g; ctx.fillRect(s.x0, r, s.x1 - s.x0, fl - r);
    ctx.fillStyle = '#1a2025'; if (s.x0 > x0) ctx.fillRect(s.x0 - 0.1, r, 0.2, 1.2);  // the walls, open doorways below
  }
  ctx.fillStyle = '#1a2025'; ctx.fillRect(x0, r, 0.4, fl - r); ctx.fillRect(x0, r, x1 - x0, 0.25); ctx.fillRect(x0, fl - 0.12, x1 - x0, 0.12);
  ctx.fillRect(x1 - 0.4, r, 0.4, 1.2);
  // frost on the walls
  ctx.fillStyle = 'rgba(230,245,255,.18)'; for (let x = x0 + 1; x < x1; x += 3.3) ctx.fillRect(x, r + 0.25, 1.2, 0.18 + (x * 7 % 3) * 0.1);
  // the store: shelves and the crew's crates
  ctx.fillStyle = '#6b5236';
  for (const y of [-5.2, -4.0]) ctx.fillRect(121.5, y, 16, 0.12);
  ctx.fillStyle = '#7a5a3a'; ctx.fillRect(129, -3.6, 2.6, 1.3); ctx.fillStyle = '#5a4128'; ctx.fillRect(129, -3.1, 2.6, 0.12);
  for (let x = 122; x < 137; x += 2.4) { ctx.fillStyle = (x * 3 % 2 < 1) ? '#8b8f6a' : '#6f7c86'; ctx.fillRect(x, -4.8, 1.4, 0.8); }
  // bunks with frozen blankets
  ctx.fillStyle = '#5a4a3a'; for (const x of [142, 154]) { ctx.fillRect(x, -3.4, 4.5, 0.18); ctx.fillRect(x, -4.9, 4.5, 0.18); ctx.fillRect(x + 4.4, -5.6, 0.18, 2.8); }
  ctx.fillStyle = '#8fa4b4'; for (const x of [142, 154]) { ctx.fillRect(x + 0.1, -3.7, 4.2, 0.3); ctx.fillRect(x + 0.1, -5.2, 4.2, 0.3); }
  // the lab: benches, a microscope, the whiteboard with its warning
  ctx.fillStyle = '#7d8a90'; ctx.fillRect(161, -3.8, 7, 0.2); ctx.fillRect(173, -3.8, 6, 0.2); ctx.fillRect(161.4, -3.6, 0.2, 1.3); ctx.fillRect(178.4, -3.6, 0.2, 1.3);
  ctx.fillStyle = '#e8eef2'; ctx.fillRect(166.5, -5.8, 7, 1.6);
  ctx.strokeStyle = '#c0392b'; ctx.lineWidth = 0.1; ctx.beginPath(); ctx.moveTo(167, -5.3); ctx.lineTo(172.8, -5.3); ctx.moveTo(167, -4.8); ctx.lineTo(171, -4.8); ctx.stroke();
  ctx.fillStyle = '#3a4248'; ctx.fillRect(175, -4.5, 0.4, 0.7); ctx.fillRect(174.6, -3.9, 1.2, 0.12);
  // the radio room: desk, the dead radio set, a chair, the logbook on the desk
  ctx.fillStyle = '#6b5236'; ctx.fillRect(184, -3.7, 9, 0.2); ctx.fillRect(184.3, -3.5, 0.2, 1.2); ctx.fillRect(192.5, -3.5, 0.2, 1.2);
  ctx.fillStyle = '#2b3236'; ctx.fillRect(185, -5.1, 4.2, 1.4);
  ctx.fillStyle = '#56606a'; for (let n = 0; n < 4; n++) ctx.fillRect(185.4 + n * 0.9, -4.7, 0.5, 0.5);
  ctx.fillStyle = '#4a3a2a'; ctx.fillRect(191, -4.3, 0.9, 0.12); ctx.fillRect(191.8, -5.2, 0.12, 2.9);
  // the hall: coats on hooks, boots, the door out
  for (let n = 0; n < 3; n++) { ctx.fillStyle = ['#c0392b', '#2f6f8f', '#c9b23a'][n]; ctx.fillRect(200 + n * 1.6, -5.4, 0.9, 1.6); }
  ctx.fillStyle = '#222'; for (let n = 0; n < 3; n++) ctx.fillRect(200.1 + n * 1.6, fl - 0.35, 0.8, 0.35);
  ctx.fillStyle = 'rgba(200,225,240,.35)'; ctx.fillRect(x1 - 0.4, r + 1.2, 0.4, fl - r - 1.2);
  // room names along the ceiling
  ctx.font = '700 0.62px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (const s of SROOMS) {
    const w = ctx.measureText(s.name).width, cx = (s.x0 + s.x1) / 2;
    ctx.fillStyle = 'rgba(10,14,18,.6)'; ctx.fillRect(cx - w / 2 - 0.12, r + 0.32, w + 0.24, 0.7);
    ctx.fillStyle = '#e6f2ff'; ctx.fillText(s.name, cx, r + 0.36);
  }
}
// The sea ice (v6): white on top, blue below, a ragged underside; none in the openings or around the iceberg.
function drawIce(X0, X1) {
  const cuts = HOLES.concat([BERG_X]).sort((p, q) => p[0] - q[0]);
  let a = Math.max(SHELF_X, X0 - 4);
  const segs = [];
  for (const [h0, h1] of cuts) {
    if (h1 <= a) continue;
    if (h0 > a) segs.push([a, Math.min(h0, X1 + 4)]);
    a = Math.max(a, h1);
    if (a > X1) break;
  }
  if (a < X1 + 4) segs.push([a, X1 + 4]);
  for (const [s0, s1] of segs) {
    if (s1 <= s0) continue;
    const g = ctx.createLinearGradient(0, ICE_TOP, 0, ICE_Y);
    g.addColorStop(0, '#d8ecf7'); g.addColorStop(1, '#7fb4d2');
    ctx.fillStyle = g; ctx.fillRect(s0, ICE_TOP, s1 - s0, ICE_Y - ICE_TOP);
    ctx.fillStyle = '#7fb4d2';
    ctx.beginPath(); ctx.moveTo(s0, ICE_Y);
    for (let x = Math.ceil(s0 / 3) * 3; x < s1; x += 3) ctx.lineTo(x, ICE_Y + 0.25 + Math.abs(Math.sin(x * 1.7)) * 0.5);
    ctx.lineTo(s1, ICE_Y); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#f4f9fc'; ctx.fillRect(s0, ICE_TOP - 0.2, s1 - s0, 0.45);  // snow
  }
  // Planks from SISU's back to the edges of its opening, while it lies surfaced there.
  if (surfaced()) {
    const n = holeAt(sub.x), y = sub.y - 2.3;
    ctx.fillStyle = '#8a6a40';
    ctx.fillRect(HOLES[n][0] - 0.6, y - 0.12, sub.x - 12 - HOLES[n][0] + 0.6, 0.24);
    ctx.fillRect(sub.x + 10, y - 0.12, HOLES[n][1] + 0.6 - sub.x - 10, 0.24);
  }
}
// Snow blowing over the ice, and frost at the screen's edges as the warmth runs out (v6).
function drawWeather(oy) {
  ctx.fillStyle = 'rgba(245,250,255,.7)';
  for (const p of snow) {
    const x = ((p.x * W - G.cx * G.sc * p.z + G.t * 90 * p.z) % W + W) % W, y = ((p.y * H + G.t * 30 * p.z) % H + H) % H;
    if (y < oy + 4) ctx.fillRect(x, y, 2 * p.z, 2 * p.z);
  }
  if (walker.warm < 50) {
    const k = (50 - walker.warm) / 50, g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.25, W / 2, H / 2, Math.hypot(W, H) / 2);
    g.addColorStop(0, 'rgba(225,245,255,0)'); g.addColorStop(1, `rgba(225,245,255,${0.9 * k})`);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
}
function drawBerg(X0, X1) {
  if (X1 < 2040 || X0 > 2440) return;
  ctx.fillStyle = '#e8f3fa'; polyPath(ctx, BERG.top); ctx.fill();
  ctx.fillStyle = '#b6d3e6'; polyPath(ctx, [[2318, -38], [2336, -70], [2350, -66], [2340, -30]]); ctx.fill();
  const g = ctx.createLinearGradient(0, 0, 0, 205); g.addColorStop(0, '#d2f0fb'); g.addColorStop(0.45, '#6fb8dc'); g.addColorStop(1, '#2a6890');
  ctx.fillStyle = g; polyPath(ctx, BERG.poly); ctx.fill();
  ctx.strokeStyle = 'rgba(235,250,255,.7)'; ctx.lineWidth = 0.8; ctx.stroke();
  // v9 (#160): from outside only the two ways in show; inside, the dark hides every passage the lamp does not reach.
  const inside = bergView();
  ctx.save();
  if (!inside) { ctx.beginPath(); ctx.arc(2084, 50, 5, 0, 7); ctx.arc(2419, 105, 5, 0, 7); ctx.clip(); }
  ctx.lineCap = 'round';
  // under a lamp the cave's water shows blue-green against the white ice; from outside the mouths are dark
  ctx.strokeStyle = inside ? '#1f5f80' : '#0c2f4a';
  for (const [ax, ay, bx, by, r] of BERG.caves) { ctx.lineWidth = r * 2; ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx + 0.01, by); ctx.stroke(); }
  ctx.strokeStyle = inside ? '#2a7194' : '#123f60';
  for (const [ax, ay, bx, by, r] of BERG.caves) { ctx.lineWidth = r * 1.4; ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx + 0.01, by); ctx.stroke(); }
  ctx.restore();
  if (!inside) return;
  // the hall's icicles, ice rubble on its floor and a frozen-in anchor chain; the old lifeboat in the lower cave
  const top = HALL.y - 5.5, bot = HALL.y + 5.5;
  ctx.fillStyle = '#7cc4e4';
  for (let x = HALL.x - 7; x < HALL.x + 8; x += 2.6) { const l = 1.5 + (x * 13 % 3); ctx.beginPath(); ctx.moveTo(x - 0.6, top + 0.8); ctx.lineTo(x + 0.6, top + 0.8); ctx.lineTo(x, top + 0.8 + l); ctx.fill(); }
  ctx.fillStyle = 'rgba(120,190,220,.8)';
  for (let x = HALL.x - 6; x < HALL.x + 7; x += 3.2) { const r = 0.6 + (x * 7 % 3) * 0.3; ctx.beginPath(); ctx.ellipse(x, bot - 0.7, r * 1.4, r, 0, Math.PI, 0); ctx.fill(); }
  ctx.strokeStyle = 'rgba(150,130,110,.85)'; ctx.lineWidth = 0.25;
  for (let k = 0; k < 7; k++) { ctx.beginPath(); ctx.ellipse(HALL.x + 4 + k * 0.3, top + 1.5 + k * 1.1, 0.3, 0.55, 0.3, 0, 7); ctx.stroke(); }
  ctx.fillStyle = '#5a3a26'; polyPath(ctx, [[2133, 89], [2145, 89], [2143, 91.4], [2135, 91.4]]); ctx.fill();
  ctx.fillStyle = '#7a5236'; ctx.fillRect(2137, 87.4, 4, 1.8);
}
// v9: is this phone's diver inside the iceberg? Then the berg is dark but for the lamps.
function bergView() { return G.mode === 'dive' && diver.x > 2078 && diver.x < 2424 && diver.y < 206 && pip(diver.x, diver.y, BERG.poly); }
// The light of a lamp in the iceberg (v9): rays that stop at the ice, so no light shines through a wall. `mid` and
// `half` give the beam, `len` its reach, `near` the glow round the diver. With `mark` the rays map what they light.
function lampPoly(x, y, mid, half, len, near, mark) {
  const pts = [];
  const ray = (a, L) => {
    const cx = Math.cos(a), cy = Math.sin(a);
    let t = 0.3;
    for (; t < L; t += 0.35) {
      const px = x + cx * t, py = y + cy * t;
      if (mark) markSeen(px, py);
      if (solid(px, py)) { t += 0.7; break; }  // the light reaches just into the ice, so the wall's face shows
    }
    t = Math.min(t, L);
    pts.push(x + cx * t, y + cy * t);
  };
  for (let k = 0; k <= 36; k++) ray(mid - half + 2 * half * k / 36, len);
  for (let k = 1; k < 28; k++) ray(mid + half + (2 * Math.PI - 2 * half) * k / 28, near);
  return pts;
}
// A diver's lamp: [x, y, beam direction, reach, glow] for this phone's diver or a friend's (o).
function lampOf(d) { const l = G.s ? LAMP[G.s.up.lamp] : 1; return [d.x, d.y, d.dir > 0 ? d.ang : Math.PI - d.ang, 22 * l, 8 * l]; }
// The squares of the cave outline a lamp has lit (v9), kept in the save as `cave`; `chartSeen` likewise for the chart.
const caveSeen = new Uint8Array(RV.w * RV.h);
function markSeen(x, y) {
  const n = rvAt(x, y);
  if (n >= 0 && !caveSeen[n]) { caveSeen[n] = 1; G.mapNew = true; }
}
// The cave outline mapped so far, drawn over the dark: the "kartoittuu" lines.
function drawCaveLines(c, X0, X1, Y0, Y1, w, col) {
  const i0 = Math.max(0, Math.floor((X0 - RV.x0) / RV.s)), i1 = Math.min(RV.w - 1, Math.floor((X1 - RV.x0) / RV.s));
  const j0 = Math.max(0, Math.floor((Y0 - RV.y0) / RV.s)), j1 = Math.min(RV.h - 1, Math.floor((Y1 - RV.y0) / RV.s));
  if (i0 > i1 || j0 > j1) return;
  c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'round'; c.beginPath();
  for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
    const n = i + j * RV.w, l = caveSeen[n] && CAVE_LINES.get(n);
    if (l) for (let k = 0; k < l.length; k += 4) { c.moveTo(l[k], l[k + 1]); c.lineTo(l[k + 2], l[k + 3]); }
  }
  c.stroke(); c.lineCap = 'butt';
}
// Can the eye see the point: no ice or wall between them (0.35 m steps)?
function sightTo(ax, ay, bx, by) {
  const L = Math.hypot(bx - ax, by - ay), n = Math.ceil(L / 0.35);
  for (let k = 1; k < n; k++) if (solid(ax + (bx - ax) * k / n, ay + (by - ay) * k / n)) return false;
  return true;
}
function drawFloor(X0, X1, Y1) {
  const pts = [];
  for (const [x, y] of FLOOR) if (x > X0 - 120 && x < X1 + 120) pts.push([x, y]);
  if (!pts.length) return;
  const bottom = Math.max(Y1, 400) + 10;
  const g = ctx.createLinearGradient(0, 100, 0, 380); g.addColorStop(0, '#2b3b40'); g.addColorStop(1, '#0d1519');
  ctx.fillStyle = g;
  polyPath(ctx, [[pts[0][0], bottom], ...pts, [pts[pts.length - 1][0], bottom]]); ctx.fill();
  ctx.strokeStyle = '#4c6168'; ctx.lineWidth = 0.6; ctx.beginPath();
  pts.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
  // stones and kelp on the floor
  for (let x = Math.floor(X0 / 9) * 9; x < X1; x += 9) {
    const r = (Math.sin(x * 12.9898) * 43758.5453) % 1, y = floorY(x);
    if (Math.abs(r) < 0.35) { ctx.fillStyle = '#3a4a50'; ctx.beginPath(); ctx.ellipse(x, y, 1.6, 0.8, 0, Math.PI, 0); ctx.fill(); }
    else if (Math.abs(r) > 0.8 && y < 200) {
      ctx.strokeStyle = '#2f5a3a'; ctx.lineWidth = 0.35; ctx.beginPath(); ctx.moveTo(x, y);
      for (let k = 1; k < 6; k++) ctx.lineTo(x + Math.sin(G.t + k + x) * 0.6, y - k * 1.3);
      ctx.stroke();
    }
  }
}
// The deep plain: hot vents with shimmering plumes, and the bones of a whale that sank long ago.
function drawDeep(X0, X1) {
  ctx.strokeStyle = '#c9c2a8'; ctx.lineWidth = 0.5; ctx.lineCap = 'round';
  const by = floorY(3990);
  ctx.beginPath(); ctx.moveTo(3968, by - 1); ctx.quadraticCurveTo(3990, by - 4, 4014, by - 1.2); ctx.stroke();
  for (let x = 3974; x < 4010; x += 3) { ctx.beginPath(); ctx.moveTo(x, by - 2.4); ctx.quadraticCurveTo(x + 1.5, by - 6, x + 3, by - 0.6); ctx.stroke(); }
  ctx.fillStyle = '#c9c2a8'; ctx.beginPath(); ctx.ellipse(4016, by - 1.4, 3, 1.4, -0.1, 0, 7); ctx.fill();
  ctx.lineCap = 'butt';
  for (const [vx, h] of VENTS) {
    if (vx < X0 - 20 || vx > X1 + 20) continue;
    const fy = floorY(vx), top = fy - h, w = 1.6 + h * 0.08;
    ctx.fillStyle = '#2b2522'; polyPath(ctx, [[vx - w, fy + 1], [vx - 1.6, top], [vx + 1.6, top], [vx + w, fy + 1]]); ctx.fill();
    ctx.fillStyle = '#ff7a2a'; ctx.fillRect(vx - 1, top - 0.3, 2, 0.5);
    ctx.fillStyle = 'rgba(40,36,34,.35)';
    for (let k = 0; k < 6; k++) {
      const a = (G.t * 0.6 + k / 6) % 1;
      ctx.beginPath(); ctx.arc(vx + Math.sin(G.t + k * 2) * a * 2, top - a * 16, 0.8 + a * 2.4, 0, 7); ctx.fill();
    }
  }
}
function drawSite(s) {
  const inside = G.mode === 'dive' && diver.x > s.x - 1 && diver.x < s.x + s.w * C + 1 && diver.y > s.y - 1 && diver.y < s.y + s.h * C + 1;
  s.open = (s.open || 0) + ((inside ? 1 : 0) - (s.open || 0)) * 0.12;
  const shell = s.shell === 'station' ? '#79838a' : s.shell === 'ship' ? '#4d3b2f' : s.shell === 'beacon' ? '#c0582a' : s.color;
  if (s.shell === 'rv') return drawNordlys(s);
  if (s.shell === 'ship') { // masts and rails before the hull
    ctx.strokeStyle = '#3d2f26'; ctx.lineWidth = 0.4;
    ctx.beginPath(); ctx.moveTo(s.x + 6, s.y + 4); ctx.lineTo(s.x + 6, s.y - 8); ctx.moveTo(s.x + 3, s.y - 5); ctx.lineTo(s.x + 9, s.y - 5); ctx.stroke();
  }
  for (let j = 0; j < s.h; j++) for (let i = 0; i < s.w; i++) {
    const ch = s.cells[j][i] || ' ';
    if (ch === ' ') continue;
    const x = s.x + i * C, y = s.y + j * C;
    if (ch === '#') ctx.fillStyle = s.open > 0.5 ? '#6a5446' : shell;
    else ctx.fillStyle = s.open > 0.5 ? (s.shell === 'station' ? '#2c3a40' : '#2a241f') : shell;
    ctx.fillRect(x - 0.02, y - 0.02, C + 0.04, C + 0.04);
  }
  if (s.open < 0.5) {
    ctx.strokeStyle = 'rgba(0,0,0,.35)'; ctx.lineWidth = 0.15;
    for (let j = 1; j < s.h; j += 2) { ctx.beginPath(); ctx.moveTo(s.x, s.y + j * C); ctx.lineTo(s.x + s.w * C, s.y + j * C); ctx.stroke(); }
    if (s.shell === 'station') { ctx.fillStyle = '#8a2e22'; ctx.fillRect(s.x, s.y + 1.2, s.w * C, 0.8); }
    if (s.shell === 'box') { ctx.fillStyle = 'rgba(0,0,0,.25)'; for (let x = s.x + 0.6; x < s.x + s.w * C; x += 1.2) ctx.fillRect(x, s.y + 0.3, 0.4, s.h * C - 0.6); }
    ctx.fillStyle = '#e8d7a8'; ctx.font = '1.4px system-ui'; ctx.textAlign = 'center';
    if (s.shell === 'ship') ctx.fillText(s.name.toUpperCase(), s.x + s.w * C - 12, s.y + 9);
    if (s.id === 'asema') ctx.fillText('A-3', s.x + s.w * C - 4, s.y + 9.6);
    if (s.shell === 'beacon') { // a mast with a slow red light
      ctx.fillStyle = '#5a5a5a'; ctx.fillRect(s.x + 7.6, s.y - 6, 0.6, 6);
      ctx.fillStyle = (G.t % 1.6 < 0.4) ? '#ff5030' : '#5a1a10'; ctx.beginPath(); ctx.arc(s.x + 7.9, s.y - 6.4, 0.7, 0, 7); ctx.fill();
    }
  } else {
    ctx.fillStyle = 'rgba(255,220,150,.08)'; // furniture hints inside
    for (let j = 0; j < s.h; j++) for (let i = 0; i < s.w; i++) if ((s.cells[j][i] === '.') && s.cells[j + 1] && s.cells[j + 1][i] === '#' && (i * 7 + j) % 3 === 0)
      ctx.fillRect(s.x + i * C + 0.3, s.y + j * C + 1.1, 1.4, 0.9);
  }
}
// RV Nordlys: white superstructure, a dark blue hull with a red stripe and her name; inside, rooms as in the picture.
function drawNordlys(s) {
  const inside = s.open > 0.5;
  for (let j = 0; j < s.h; j++) for (let i = 0; i < s.w; i++) {
    const ch = s.cells[j][i] || ' ';
    if (ch === ' ') continue;
    if (inside) ctx.fillStyle = ch === '#' ? '#56606a' : j < s.deck ? '#26343e' : '#1d2a33';
    else ctx.fillStyle = j <= s.deck ? '#d7dee2' : j === s.deck + 2 ? '#a83226' : '#1f3a5a';
    ctx.fillRect(s.x + i * C - 0.02, s.y + j * C - 0.02, C + 0.04, C + 0.04);
  }
  const x1 = s.x + s.w * C;
  if (!inside) {
    ctx.fillStyle = '#1b2a33';
    for (let x = s.x + 71; x < s.x + 101; x += 3.2) ctx.fillRect(x, s.y + 2.4, 2, 1.2);
    ctx.fillStyle = 'rgba(0,0,0,.35)';
    for (let x = s.x + 4; x < x1 - 10; x += 4) { ctx.beginPath(); ctx.arc(x, s.y + 11.6, 0.45, 0, 7); ctx.fill(); }
    ctx.fillStyle = '#e8eef2'; ctx.font = '700 2.4px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('NORDLYS', s.x + 64, s.y + 17);
  }
  // masts, the radar and the A-frame crane at the stern
  ctx.strokeStyle = '#9aa6ac'; ctx.lineWidth = 0.45;
  ctx.beginPath(); ctx.moveTo(s.x + 88, s.y); ctx.lineTo(s.x + 88, s.y - 12); ctx.moveTo(s.x + 85, s.y - 9); ctx.lineTo(s.x + 91, s.y - 9);
  ctx.moveTo(s.x + 4, s.y + 8); ctx.lineTo(s.x + 1, s.y - 2); ctx.lineTo(s.x + 9, s.y - 2); ctx.lineTo(s.x + 8, s.y + 8); ctx.stroke();
  ctx.fillStyle = '#9aa6ac'; ctx.fillRect(s.x + 86, s.y - 12.5, 4, 0.6);
}
function drawItems(X0, X1, Y0, Y1) {
  if (!G.s) return;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = '1.5px system-ui';
  // Finds are drawn over the dark, but only as far as a lamp reaches.
  const ice = G.mode === 'ice', eye = G.mode === 'dive' ? diver : ice ? walker : sub;
  const reach = G.mode === 'dive' ? 13 * LAMP[G.s.up.lamp] : ice ? 40 : 26, seeIn = ice && inStation(walker.x);
  for (const it of allItems()) {
    if (it.x < X0 - 2 || it.x > X1 + 2 || it.y < Y0 - 2 || it.y > Y1 + 2 || !itemHere(it)) continue;
    if ((it.site === 'pinta') !== seeIn) continue;
    // v9: in the dark iceberg a find shows only to a lamp that sees it, not through the ice
    if (caveHidden(it, eye)) continue;
    const vis = Math.min(1, 1.5 - Math.hypot(it.x - eye.x, it.y - eye.y) / reach);
    if (vis <= 0) continue;
    ctx.globalAlpha = vis;
    if (it.k === 'ilma') {
      ctx.strokeStyle = 'rgba(220,245,255,.8)'; ctx.lineWidth = 0.12;
      for (let k = 0; k < 4; k++) { ctx.beginPath(); ctx.arc(it.x + Math.sin(G.t * 2 + k) * 0.5, it.y - ((G.t * 0.8 + k * 0.4) % 1.6) + 0.6, 0.25 + k * 0.05, 0, 7); ctx.stroke(); }
      ctx.fillStyle = 'rgba(200,240,255,.25)'; ctx.beginPath(); ctx.ellipse(it.x, it.y - 0.8, 1.8, 0.6, 0, 0, 7); ctx.fill();
      continue;
    }
    if (it.site === 'find') { ctx.fillStyle = '#a8792e'; ctx.fillRect(it.x - 0.8, it.y - 0.5, 1.6, 1.4); }
    ctx.fillText(ICON[it.k], it.x, it.y + Math.sin(G.t * 2 + it.x) * 0.15);
  }
  ctx.globalAlpha = 1;
}
// A diver's hose (v7): from SISU's airlock round its corners to the suit, yellow turning red as it wears. A cut hose
// ends in a frayed end at its last corner, and a short stub trails from the suit.
function drawHose(pts, d, cut, wear) {
  const a = airlock(), path = [[a.x, a.y], ...pts.map(p => [p[0], p[1]])];
  if (!cut) path.push([d.x - d.dir * 0.5, d.y - 0.2]);
  const w = Math.min(1, wear / 100);
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  for (const [col, lw] of [['rgba(20,14,4,.7)', 0.42], [`rgb(${235},${Math.round(200 - 140 * w)},${Math.round(70 - 30 * w)})`, 0.24]]) {
    ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.beginPath();
    path.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    if (cut) { const [ex, ey] = path[path.length - 1]; ctx.lineTo(ex + 0.6, ey + 1.6); }
    ctx.stroke();
    if (cut) { ctx.beginPath(); ctx.moveTo(d.x - d.dir * 0.5, d.y - 0.2); ctx.lineTo(d.x - d.dir * 1.6, d.y + 0.9); ctx.stroke(); }
  }
  // the corners it rubs on show as small red marks; a guided one is drawn by drawGuides
  ctx.fillStyle = 'rgba(255,90,60,.85)';
  if (!cut) for (const p of pts) if (G.s && !guided(p)) { ctx.beginPath(); ctx.arc(p[0], p[1], 0.22, 0, 7); ctx.fill(); }
  ctx.lineCap = 'butt'; ctx.lineJoin = 'miter';
}
// The guides clamped to corners (v7): orange rings, seen as far as a lamp reaches (from SISU, a little further).
function drawGuides(X0, X1, Y0, Y1) {
  const eye = G.mode === 'dive' ? diver : sub, reach = G.mode === 'dive' ? 13 * LAMP[G.s.up.lamp] : 26;
  ctx.lineWidth = 0.18;
  for (const [x, y] of G.s.guides) {
    if (x < X0 - 2 || x > X1 + 2 || y < Y0 - 2 || y > Y1 + 2) continue;
    const vis = Math.min(1, 1.5 - Math.hypot(x - eye.x, y - eye.y) / reach);
    if (vis <= 0) continue;
    ctx.globalAlpha = vis;
    ctx.fillStyle = '#ff9a2e'; ctx.beginPath(); ctx.arc(x, y, 0.45, 0, 7); ctx.fill();
    ctx.strokeStyle = '#ffe2b0'; ctx.beginPath(); ctx.arc(x, y, 0.45, 0, 7); ctx.stroke();
    ctx.fillStyle = '#3a2408'; ctx.beginPath(); ctx.arc(x, y, 0.16, 0, 7); ctx.fill();
  }
  ctx.globalAlpha = 1;
}
// The schools (v8): small silver fish, seen as far as a lamp reaches; near an opening's daylight a little further.
function drawSchools(X0, X1, Y0, Y1) {
  const eye = G.mode === 'dive' ? diver : sub, reach = G.mode === 'dive' ? 13 * LAMP[G.s.up.lamp] : 26;
  for (const f of fishNow()) {
    if (f.x < X0 - 2 || f.x > X1 + 2 || f.y < Y0 - 2 || f.y > Y1 + 2) continue;
    const day = holeAt(f.x) >= 0 || !underIce(f.x) ? Math.max(0, 0.6 - f.y / 120) : 0;
    const vis = Math.max(day, Math.min(1, 1.5 - Math.hypot(f.x - eye.x, f.y - eye.y) / reach));
    if (vis <= 0) continue;
    const w = Math.sin(G.t * 9 + f.k * 1.3) * 0.18;
    ctx.globalAlpha = vis;
    ctx.save(); ctx.translate(f.x, f.y); ctx.scale(f.dir, 1);
    ctx.fillStyle = '#b9cfd8'; ctx.beginPath(); ctx.ellipse(0, 0, 0.55, 0.2, 0, 0, 7); ctx.fill();
    ctx.fillStyle = '#7f98a6'; polyPath(ctx, [[-0.45, 0], [-0.85, -0.22 + w], [-0.85, 0.22 + w]]); ctx.fill();
    ctx.fillStyle = '#e8f4f8'; ctx.fillRect(-0.3, 0.02, 0.65, 0.07);
    ctx.fillStyle = '#123'; ctx.beginPath(); ctx.arc(0.32, -0.04, 0.05, 0, 7); ctx.fill();
    ctx.restore();
  }
  ctx.globalAlpha = 1;
}
// The spear in flight, its line back to the gun.
function drawSpear(p) {
  ctx.strokeStyle = 'rgba(230,230,220,.5)'; ctx.lineWidth = 0.05;
  ctx.beginPath(); ctx.moveTo(diver.x + diver.dir * 0.6, diver.y); ctx.lineTo(p.x, p.y); ctx.stroke();
  const dx = Math.cos(p.a), dy = Math.sin(p.a);
  ctx.strokeStyle = '#d8dde0'; ctx.lineWidth = 0.1;
  ctx.beginPath(); ctx.moveTo(p.x - dx * 1.5, p.y - dy * 1.5); ctx.lineTo(p.x, p.y); ctx.stroke();
  ctx.fillStyle = '#f2f2f2'; polyPath(ctx, [[p.x + dx * 0.3, p.y + dy * 0.3], [p.x - dy * 0.14, p.y + dx * 0.14], [p.x + dy * 0.14, p.y - dx * 0.14]]); ctx.fill();
}
// Glowing fish: a dark body, a fin, and a lit lure on a stalk ahead of the mouth.
function drawFish() {
  for (let n = 0; n < FISH.length; n++) {
    const f = fishAt(n, G.t);
    ctx.save(); ctx.translate(f.x, f.y); ctx.scale(f.dir * 1.6, 1.6);
    ctx.fillStyle = '#3b2f3f'; ctx.beginPath(); ctx.ellipse(0, 0, 1.8, 1.1, 0, 0, 7); ctx.fill();
    polyPath(ctx, [[-1.5, 0], [-2.8, -0.9 + Math.sin(G.t * 5 + n) * 0.3], [-2.8, 0.9 + Math.sin(G.t * 5 + n) * 0.3]]); ctx.fill();
    ctx.fillStyle = '#e8e0c0'; for (let k = 0; k < 4; k++) ctx.fillRect(0.9 + k * 0.2, 0.15, 0.08, 0.3);
    ctx.fillStyle = '#9fffe0'; ctx.beginPath(); ctx.arc(0.6, -0.4, 0.18, 0, 7); ctx.fill();
    ctx.strokeStyle = '#5a4a5a'; ctx.lineWidth = 0.12; ctx.beginPath(); ctx.moveTo(0.4, -1); ctx.quadraticCurveTo(1.6, -2.2, 2.2, -1); ctx.stroke();
    ctx.fillStyle = `rgba(150,255,220,${0.7 + 0.3 * Math.sin(G.t * 3 + n)})`; ctx.beginPath(); ctx.arc(2.2, -1, 0.35, 0, 7); ctx.fill();
    ctx.restore();
  }
}
function sparkles() {
  for (const it of allItems()) {
    if (!itemHere(it)) continue;
    const d = Math.hypot(it.x - diver.x, it.y - diver.y);
    if (d > 14 || caveHidden(it, diver)) continue;
    const a = (1 - d / 14) * (0.5 + 0.5 * Math.sin(G.t * 4 + it.x));
    ctx.fillStyle = it.k === 'ilma' ? `rgba(200,240,255,${a * 0.6})` : `rgba(255,230,140,${a})`;
    ctx.beginPath(); ctx.arc(it.x, it.y, 0.25, 0, 7); ctx.fill();
  }
}
// v9: what the lamps light inside the iceberg this frame (`G.lit`, set by drawDark); null outside it.
function litAt(x, y) {
  if (!G.lit) return true;
  return G.lit.some(p => {
    let c = false;
    for (let i = 0, j = p.length - 2; i < p.length; j = i, i += 2)
      if ((p[i + 1] > y) !== (p[j + 1] > y) && x < (p[j] - p[i]) * (y - p[i + 1]) / (p[j + 1] - p[i + 1]) + p[i]) c = !c;
    return c;
  });
}
// A cave find shows only where a lamp lights it: inside the berg its light, from outside a clear line of sight.
function caveHidden(it, eye) {
  if (it.site !== 'jaavuori') return false;
  if (G.mode !== 'dive') return true;
  return bergView() ? !litAt(it.x, it.y) : !sightTo(eye.x, eye.y, it.x, it.y);
}
function drawDark(ox, oy, sc) {
  const d = dctx;
  G.lit = null;
  d.setTransform(DPR, 0, 0, DPR, 0, 0);
  d.globalCompositeOperation = 'source-over';
  d.clearRect(0, 0, W, H);
  // v2: darker still on the slope and in the deep sea
  const g = d.createLinearGradient(0, oy, 0, oy + 900 * sc);
  g.addColorStop(0, 'rgba(0,4,12,0.08)'); g.addColorStop(0.058, 'rgba(0,4,12,0.42)'); g.addColorStop(0.29, 'rgba(0,3,10,0.9)');
  g.addColorStop(0.75, 'rgba(0,1,6,0.97)'); g.addColorStop(1, 'rgba(0,1,5,0.98)');
  d.fillStyle = g; d.fillRect(0, Math.max(0, oy), W, H);
  d.globalCompositeOperation = 'destination-out';
  const S = (x, y) => [ox + x * sc, oy + y * sc];
  const glow = (x, y, r, a = 1) => {
    const [px, py] = S(x, y), R = r * sc, rg = d.createRadialGradient(px, py, 0, px, py, R);
    rg.addColorStop(0, `rgba(0,0,0,${a})`); rg.addColorStop(1, 'rgba(0,0,0,0)');
    d.fillStyle = rg; d.beginPath(); d.arc(px, py, R, 0, 7); d.fill();
  };
  const cone = (x, y, ang, len, half) => {
    const [px, py] = S(x, y), R = len * sc, rg = d.createRadialGradient(px, py, 0, px, py, R);
    rg.addColorStop(0, 'rgba(0,0,0,1)'); rg.addColorStop(0.6, 'rgba(0,0,0,.7)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
    d.fillStyle = rg; d.beginPath(); d.moveTo(px, py); d.arc(px, py, R, ang - half, ang + half); d.closePath(); d.fill();
  };
  const lamp = G.s ? LAMP[G.s.up.lamp] : 1;
  glow(sub.x, sub.y, 22);
  cone(sub.x + sub.face * 14, sub.y + 0.5, sub.face > 0 ? 0.12 : Math.PI - 0.12, 60 * lamp, 0.42);
  if (G.mode === 'dive') {
    glow(diver.x, diver.y, 8 * lamp);
    cone(diver.x, diver.y, diver.dir > 0 ? diver.ang : Math.PI - diver.ang, 22 * lamp, 0.55);
  }
  if (net) for (const o of Object.values(net.others)) if (o.mode === 'dive') {
    glow(o.x, o.y, 8 * lamp);
    cone(o.x, o.y, o.dir > 0 ? o.ang : Math.PI - o.ang, 22 * lamp, 0.55);
  }
  if (!bergView()) { glow(2161, 12, 6, 0.5); glow(2155, 122, 4, 0.6); }
  for (const [vx, h] of VENTS) glow(vx, floorY(vx) - h, 14, 0.55);
  for (let n = 0; n < FISH.length; n++) { const f = fishAt(n, G.t); glow(f.x + f.dir * 3.5, f.y - 1.6, 8, 0.6); }
  const mk = SITES.find(s => s.id === 'majakka');
  if (G.t % 1.6 < 0.4) glow(mk.x + 7.9, mk.y - 6.4, 9, 0.7);
  if (G.ping) {
    const age = G.t - G.ping.t, R = Math.min(pingR(), age * 260);
    if (age < 1.8) { const [px, py] = S(G.ping.x, G.ping.y); d.strokeStyle = `rgba(0,0,0,${0.35 * (1 - age / 1.8)})`; d.lineWidth = 14; d.beginPath(); d.arc(px, py, R * sc, 0, 7); d.stroke(); }
  }
  // v9 (#160): inside the iceberg it is pitch dark; only the lamps light it, and only as far as the ice lets them,
  // and a little daylight comes down the moulin's shaft.
  if (bergView()) {
    d.globalCompositeOperation = 'source-over';
    d.fillStyle = '#000308';
    d.beginPath(); BERG.poly.forEach(([x, y], i) => { const [px, py] = S(x, y); i ? d.lineTo(px, py) : d.moveTo(px, py); }); d.closePath(); d.fill();
    d.globalCompositeOperation = 'destination-out';
    const lit = [diver].concat(net ? Object.values(net.others).filter(o => o.mode === 'dive') : []);
    G.lit = [];
    for (const o of lit) {
      const [x, y, mid, len, near] = lampOf(o), pts = lampPoly(x, y, mid, 0.55, len, near);
      G.lit.push(pts);
      d.save(); d.beginPath();
      for (let k = 0; k < pts.length; k += 2) { const [px, py] = S(pts[k], pts[k + 1]); k ? d.lineTo(px, py) : d.moveTo(px, py); }
      d.closePath(); d.clip();
      glow(x, y, near); cone(x, y, mid, len, 0.55);
      d.restore();
    }
    glow(2161, 12, 6, 0.6); glow(2155, 122, 4, 0.6);
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(dark, 0, 0);
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}
// Inside a wreck the walls stay faintly visible beyond the lamp, like a cross-section drawing.
function drawLayout() {
  if (G.mode !== 'dive') return;
  for (const s of SITES) {
    if (!(s.open > 0.05)) continue;
    ctx.fillStyle = s.shell === 'rv' ? `rgba(150,180,200,${0.32 * s.open})` : `rgba(214,170,120,${0.3 * s.open})`;
    for (let j = 0; j < s.h; j++) for (let i = 0; i < s.w; i++)
      if (s.cells[j][i] === '#') ctx.fillRect(s.x + i * C - 0.02, s.y + j * C - 0.02, C + 0.04, C + 0.04);
    if (s.rooms) {
      ctx.fillStyle = `rgba(255,236,190,${0.85 * s.open})`; ctx.font = '600 1.1px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      for (const [i, j, name] of s.rooms) ctx.fillText(name, s.x + i * C, s.y + j * C + 0.25);
    }
  }
  // v9 (#160): the iceberg shows no faint walls any more: only what a lamp lit stays drawn, as an outline.
}
function drawBeams() {
  // daylight down the moulin's shaft into the iceberg; the deep crack glows faintly blue
  ctx.globalCompositeOperation = 'lighter';
  const beam = (x, y, w, len, a) => {
    const g = ctx.createLinearGradient(0, y, 0, y + len); g.addColorStop(0, `rgba(150,220,255,${a})`); g.addColorStop(1, 'rgba(150,220,255,0)');
    ctx.fillStyle = g; polyPath(ctx, [[x - w, y], [x + w, y], [x + w * 2.4, y + len], [x - w * 2.4, y + len]]); ctx.fill();
  };
  beam(2161, 8, 1, 10, 0.18);
  const p = 0.25 + 0.2 * Math.sin(G.t * 2.2);
  const g = ctx.createRadialGradient(2155, 123, 0, 2155, 123, 4); g.addColorStop(0, `rgba(90,200,255,${p})`); g.addColorStop(1, 'rgba(90,200,255,0)');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(2155, 123, 4, 0, 7); ctx.fill();
  ctx.globalCompositeOperation = 'source-over';
}
function drawSub() {
  ctx.save(); ctx.translate(sub.x, sub.y); ctx.scale(sub.face, 1);
  const inside = G.homeT;
  // tower, rudder and propeller
  ctx.fillStyle = '#c8901f';
  polyPath(ctx, [[-3, -2.2], [-2.2, -5.2], [3.6, -5.2], [4.6, -2.2]]); ctx.fill();
  // v8: the masts stand aft of the hatch, which is on the roof over the ladder; its lid stands open while anyone is out
  ctx.fillStyle = '#3b3a36'; ctx.fillRect(0.4, -7.4, 0.35, 2.3); ctx.fillRect(1.5, -6.8, 0.3, 1.7); ctx.fillRect(2.5, -7.8, 0.3, 2.7);
  ctx.fillStyle = '#8a6416'; ctx.fillRect(LADDER - 0.65, -5.42, 1.3, 0.24);
  if (G.mode === 'ice' || (net && Object.values(net.others).some(o => o.mode === 'ice'))) {
    ctx.save(); ctx.translate(LADDER + 0.65, -5.3); ctx.rotate(-1.25); ctx.fillStyle = '#a8a29a'; ctx.fillRect(-1.3, -0.1, 1.3, 0.2); ctx.restore();
  } else { ctx.fillStyle = '#a8a29a'; ctx.fillRect(LADDER - 0.6, -5.5, 1.2, 0.12); }
  ctx.fillStyle = '#b07a18'; polyPath(ctx, [[-13.2, -1], [-15.6, -3.4], [-16, -3.2], [-15.2, 0], [-16, 3.2], [-15.6, 3.4], [-13.2, 1]]); ctx.fill();
  ctx.fillStyle = '#6b6457';
  const pr = Math.sin(sub.prop * 6) * 1.6;
  ctx.fillRect(-14.8, -Math.abs(pr), 0.4, Math.abs(pr) * 2);
  // hull
  const hg = ctx.createLinearGradient(0, -2.4, 0, 2.4); hg.addColorStop(0, '#f2bd3c'); hg.addColorStop(0.6, '#c58b1c'); hg.addColorStop(1, '#7a520f');
  ctx.fillStyle = hg; hullPath(ctx); ctx.fill();
  ctx.fillStyle = 'rgba(30,20,10,.55)';
  ctx.fillRect(-9.2, -2.3, 0.5, 4.6); ctx.fillRect(7.8, -2.3, 0.5, 4.6);
  if (inside < 0.98) {
    ctx.globalAlpha = 1;
    for (const x of [-5, -2, 1, 4, 6.5]) { // warm portholes: home is lit
      ctx.fillStyle = '#ffd88a'; ctx.beginPath(); ctx.arc(x, -0.6, 0.45, 0, 7); ctx.fill();
      ctx.fillStyle = 'rgba(255,200,110,.25)'; ctx.beginPath(); ctx.arc(x, -0.6, 1.2, 0, 7); ctx.fill();
    }
    ctx.fillStyle = '#fff8d0'; ctx.beginPath(); ctx.arc(14, 0.4, 0.35, 0, 7); ctx.fill();
  }
  if (inside > 0.02) { ctx.globalAlpha = inside; drawInterior(); ctx.globalAlpha = 1; }
  ctx.restore();
}
// The cross-section of SISU from the SISU picture of #125 (v3): the reactor in the stern, the airlock in the bow, and two
// decks between them joined by the ladder under the tower. The person walks in it.
const TOWER_IN = [[-2.6, -2.3], [-1.95, -4.95], [3.35, -4.95], [4.2, -2.3]];
function drawInterior() {
  ctx.save();
  // v8 (#151): the inside reaches up into the tower: the hull and the tower are one cut-away (both drawn clockwise).
  hullPath(ctx);
  ctx.moveTo(-2.65, -2.1); ctx.lineTo(-1.95, -4.95); ctx.lineTo(3.35, -4.95); ctx.lineTo(4.25, -2.1); ctx.closePath();
  ctx.clip();
  ctx.fillStyle = '#2a1d13'; ctx.fillRect(-15, -3, 30, 6);
  const A = ctx.globalAlpha, labels = [];
  for (const r of ROOMS) {
    const y0 = r.tall || !r.deck ? -2.3 : 0.15, y1 = r.tall || r.deck ? 2.3 : 0, x0 = Math.max(r.x0, -14.2), x1 = Math.min(r.x1, 14.6);
    ctx.fillStyle = r.col; ctx.fillRect(x0 + 0.06, y0 + 0.06, x1 - x0 - 0.12, y1 - y0 - 0.12);
    const g = ctx.createRadialGradient((x0 + x1) / 2, y0 + 0.3, 0, (x0 + x1) / 2, y0 + 0.3, (x1 - x0) * 0.7);
    g.addColorStop(0, 'rgba(255,210,130,.42)'); g.addColorStop(1, 'rgba(255,210,130,0)');
    ctx.fillStyle = g; ctx.fillRect(x0 + 0.06, y0 + 0.06, x1 - x0 - 0.12, y1 - y0 - 0.12);
    if (G.mode === 'home' && crew.room === r.id) { ctx.fillStyle = 'rgba(255,230,160,.12)'; ctx.fillRect(x0 + 0.06, y0 + 0.06, x1 - x0 - 0.12, y1 - y0 - 0.12); }
    // The two tall rooms sit in the hull's curved ends: their names go a little in from the curve.
    labels.push([r.tall ? (r.x0 < 0 ? -10.9 : 11.7) : (x0 + x1) / 2, r.tall ? -1.5 : y0 + 0.22, r.tall ? 2.8 : x1 - x0 - 0.5, r.name]);
  }
  // the decks: the upper one has a hatch for the ladder; door frames between the rooms
  ctx.fillStyle = '#6b5236';
  ctx.fillRect(-8.5, UP, LADDER - 0.45 + 8.5, 0.15); ctx.fillRect(LADDER + 0.45, UP, 10 - LADDER - 0.45, 0.15);
  ctx.fillRect(-14, LOW, 29, 0.35);
  ctx.fillStyle = '#1e150d';
  for (const r of ROOMS) if (r.x0 > -14) {
    const y0 = r.tall || !r.deck ? -2.3 : 0.15;
    ctx.fillRect(r.x0 - 0.08, y0, 0.16, r.tall ? 4.3 : 2.15); // the bulkhead, with a doorway cut in it below
  }
  for (const r of ROOMS) if (r.x0 > -14 && r.id !== 'keittio') {  // the galley's back wall is the reactor's: no door
    const doors = r.tall ? [r.x0 < 0 ? null : LOW] : [r.deck ? LOW : UP];
    for (const fy of doors) if (fy != null) { ctx.fillStyle = r.col; ctx.fillRect(r.x0 - 0.1, fy - 1.75, 0.2, 1.75); }
  }
  // the reactor: two floors of steel and a blue glow
  ctx.fillStyle = '#b8c0c6'; ctx.fillRect(-12.6, -1.6, 2.8, 3.6);
  ctx.fillStyle = '#8b959c'; ctx.fillRect(-12.6, -0.2, 2.8, 0.2); ctx.fillRect(-12.9, -1.8, 3.4, 0.25);
  ctx.fillStyle = '#8fd8ff'; ctx.globalAlpha = A * (0.6 + 0.3 * Math.sin(G.t * 3)); ctx.fillRect(-11.7, -0.9, 1, 2.4); ctx.globalAlpha = A;
  ctx.strokeStyle = '#a0603a'; ctx.lineWidth = 0.12;
  ctx.beginPath(); ctx.moveTo(-9.8, -1.2); ctx.lineTo(-8.9, -1.2); ctx.lineTo(-8.9, 1.6); ctx.stroke();
  // galley: stove, kettle, counter, shelf with jars, table
  ctx.fillStyle = '#2c2c2c'; ctx.fillRect(-8.1, -0.9, 1.5, 0.9);
  ctx.fillStyle = '#ff8a3a'; ctx.fillRect(-7.95, -1.0, 1.2, 0.12);
  ctx.fillStyle = '#c9c9c9'; ctx.fillRect(-7.6, -1.35, 0.45, 0.35);
  ctx.fillStyle = 'rgba(255,255,255,.25)';
  for (let n = 0; n < 3; n++) { ctx.beginPath(); ctx.arc(-7.3 + Math.sin(G.t * 2 + n) * 0.15, -1.6 - n * 0.25 - (G.t * 0.3 % 0.25), 0.1, 0, 7); ctx.fill(); }
  ctx.fillStyle = '#9b6b3c'; ctx.fillRect(-6.2, -0.9, 2, 0.9); ctx.fillRect(-6.2, -1.9, 2.2, 0.12);
  for (let n = 0; n < 4; n++) { ctx.fillStyle = ['#d9772e', '#6aa84f', '#e8c050', '#b0473a'][n]; ctx.fillRect(-6.05 + n * 0.5, -2.2, 0.3, 0.3); }
  ctx.fillStyle = '#7a5530'; ctx.fillRect(-3.9, -0.75, 1.4, 0.12); ctx.fillRect(-3.3, -0.65, 0.15, 0.65);
  // v8: the fish from the harpoon, hung on a line over the table
  const fish = G.s ? Math.min(G.s.inv.kala || 0, 6) : 0;
  if (fish) { ctx.strokeStyle = '#8a6a40'; ctx.lineWidth = 0.04; ctx.beginPath(); ctx.moveTo(-4.0, -2.0); ctx.lineTo(-2.3, -2.0); ctx.stroke(); }
  for (let n = 0; n < fish; n++) {
    const x = -3.85 + n * 0.28;
    ctx.fillStyle = '#b9cfd8'; ctx.beginPath(); ctx.ellipse(x, -1.62, 0.09, 0.32, 0, 0, 7); ctx.fill();
    ctx.fillStyle = '#7f98a6'; polyPath(ctx, [[x, -1.33], [x - 0.12, -1.18], [x + 0.12, -1.18]]); ctx.fill();
  }
  // control room: the helm's screens and window, the chair, a plant; the ladder runs up the tower
  ctx.fillStyle = '#123'; ctx.fillRect(0.1, -1.9, 2.6, 1.1);
  ctx.fillStyle = '#5fe0a0'; ctx.fillRect(0.3, -1.7, 1, 0.65); ctx.fillStyle = '#5fb0ff'; ctx.fillRect(1.5, -1.7, 1, 0.65);
  ctx.fillStyle = '#6b4a2a'; ctx.fillRect(0.2, -0.65, 2.4, 0.65);
  ctx.fillStyle = '#3a2a1a'; ctx.fillRect(1.2, -1.0, 0.5, 0.5); ctx.fillRect(1.4, -0.5, 0.12, 0.5);
  ctx.fillStyle = '#3c7d3a'; ctx.beginPath(); ctx.arc(2.95, -0.9, 0.3, 0, 7); ctx.fill();
  ctx.fillStyle = '#6a4a2a'; ctx.fillRect(2.8, -0.6, 0.3, 0.6);
  // navigation: the chart on the wall and the chart table
  ctx.fillStyle = '#1b3550'; ctx.fillRect(3.7, -2.0, 2.2, 1.0);
  ctx.strokeStyle = '#7fd0ff'; ctx.lineWidth = 0.05;
  ctx.beginPath(); ctx.moveTo(3.8, -1.3); ctx.quadraticCurveTo(4.6, -1.9, 5.2, -1.4); ctx.lineTo(5.8, -1.15); ctx.stroke();
  ctx.fillStyle = '#ffd65a'; ctx.beginPath(); ctx.arc(5.5, -1.3, 0.08, 0, 7); ctx.fill();
  ctx.fillStyle = '#8a6a40'; ctx.fillRect(3.8, -0.7, 2.1, 0.15); ctx.fillRect(3.95, -0.55, 0.12, 0.55); ctx.fillRect(5.65, -0.55, 0.12, 0.55);
  ctx.fillStyle = '#e8dcc0'; ctx.fillRect(3.95, -0.78, 0.7, 0.08);
  // v8: the lab on the chart table: a rack of sample tubes (lit once studied) and the microscope
  const got = G.s ? ITEMS.concat(ICE_ITEMS).filter(it => it.k === 'nayte' && G.s.got[it.id]) : [];
  ctx.fillStyle = '#5a4a3a'; ctx.fillRect(4.7, -0.85, 0.95, 0.12);
  got.forEach((it, n) => {
    ctx.fillStyle = G.s.lab[it.sample] ? '#7fffd4' : '#c9d6dc'; ctx.fillRect(4.76 + n * 0.18, -1.2, 0.1, 0.38);
  });
  ctx.fillStyle = '#d7dde0'; ctx.fillRect(5.62, -0.85, 0.22, 0.14); ctx.fillRect(5.68, -1.45, 0.08, 0.6);
  ctx.fillStyle = '#3b4245'; ctx.save(); ctx.translate(5.72, -1.45); ctx.rotate(0.5); ctx.fillRect(-0.06, -0.35, 0.12, 0.4); ctx.restore();
  ctx.fillStyle = '#7fd0ff'; ctx.fillRect(5.55, -1.0, 0.3, 0.04);
  // bunks
  ctx.fillStyle = '#6e4a32'; ctx.fillRect(6.7, -0.45, 3.0, 0.15); ctx.fillRect(6.7, -1.45, 3.0, 0.15); ctx.fillRect(9.55, -2.2, 0.12, 2.2);
  ctx.fillStyle = '#9fb6c9'; ctx.fillRect(6.75, -0.68, 2.9, 0.24); ctx.fillRect(6.75, -1.68, 2.9, 0.24);
  ctx.fillStyle = '#c9a2a2'; ctx.fillRect(9.0, -0.82, 0.6, 0.2); ctx.fillStyle = '#d8c070'; ctx.fillRect(6.85, -1.85, 0.8, 0.2);
  // electrical: cabinets with blinking lights
  for (let n = 0; n < 3; n++) {
    ctx.fillStyle = '#566064'; ctx.fillRect(-8.2 + n * 0.95, 0.5, 0.8, 1.5);
    ctx.fillStyle = (Math.floor(G.t * 2 + n) % 3) ? '#5fe08a' : '#ffb04a'; ctx.fillRect(-8.0 + n * 0.95, 0.75, 0.15, 0.12);
    ctx.fillStyle = '#5fe08a'; ctx.fillRect(-7.75 + n * 0.95, 0.75, 0.15, 0.12);
  }
  ctx.strokeStyle = '#2a2f31'; ctx.lineWidth = 0.08; ctx.beginPath(); ctx.moveTo(-8.3, 0.35); ctx.lineTo(-5.5, 0.35); ctx.stroke();
  // workshop: the bench, tools on the wall, the welder
  ctx.fillStyle = '#7a5a3a'; ctx.fillRect(-5.0, 1.25, 2.6, 0.2); ctx.fillRect(-4.9, 1.45, 0.12, 0.55); ctx.fillRect(-2.6, 1.45, 0.12, 0.55);
  ctx.fillStyle = '#c0c0c0'; for (let x = -4.8; x < -2.6; x += 0.45) ctx.fillRect(x, 0.45, 0.1, 0.5);
  ctx.fillStyle = '#c04030'; ctx.fillRect(-3.9, 0.95, 0.6, 0.3);
  // stores: one tin per ration, one box per medicine, gears per spare part (the ladder passes on the left)
  const inv = G.s ? G.s.inv : { ruoka: 0, laake: 0, osat: 0 };
  ctx.fillStyle = '#8a6a40'; ctx.fillRect(-0.6, 1.1, 4.3, 0.1); ctx.fillRect(-0.6, 1.95, 4.3, 0.06); ctx.fillRect(-0.6, 0.45, 0.1, 1.55); ctx.fillRect(3.6, 0.45, 0.1, 1.55);
  for (let n = 0; n < Math.min(inv.ruoka, 7); n++) { ctx.fillStyle = '#d9772e'; ctx.fillRect(-0.4 + n * 0.55, 0.62, 0.4, 0.48); }
  for (let n = 0; n < Math.min(inv.laake, 4); n++) { ctx.fillStyle = '#f2f2f2'; ctx.fillRect(-0.4 + n * 0.6, 1.5, 0.45, 0.45); ctx.fillStyle = '#d33'; ctx.fillRect(-0.22 + n * 0.6, 1.62, 0.1, 0.22); }
  for (let n = 0; n < Math.min(inv.osat, 5); n++) { ctx.fillStyle = '#9aa'; ctx.beginPath(); ctx.arc(2.0 + n * 0.35, 1.78, 0.16, 0, 7); ctx.fill(); }
  // diving suits on their hooks: one is gone while someone wears it; with friends (v5) a hook for each
  // v7: the hooks alternate tank gear and hose suits; a worn suit leaves a hook of its own kind
  const wearers = [crew].concat(net ? Object.values(net.others).filter(o => o.mode !== 'wait') : []).filter(c => c.suit);
  const worn = [wearers.filter(c => c.kit !== 'hose').length, wearers.filter(c => c.kit === 'hose').length];
  const hooks = net && Object.keys(net.others).length > 1 ? [[0, 4.3], [1, 5.4], [2, 6.5], [3, 7.6]] : [[0, 5.2], [1, 7.4]];
  for (const [n, x] of hooks) {
    ctx.fillStyle = '#5a4a3a'; ctx.fillRect(x + 0.35, 0.3, 0.2, 0.12);
    const hs = n % 2 === 1;  // a hose suit, copper with a bigger helmet
    if (Math.floor(n / 2) < worn[n % 2]) continue;
    ctx.fillStyle = hs ? '#c96a2a' : '#e0b020'; ctx.fillRect(x, 0.85, 0.9, 1.0);
    ctx.fillStyle = hs ? '#d08a3a' : '#e0b020'; ctx.beginPath(); ctx.arc(x + 0.45, 0.6, hs ? 0.38 : 0.32, 0, 7); ctx.fill();
    ctx.fillStyle = '#7fc8e8'; ctx.beginPath(); ctx.arc(x + 0.5, 0.58, 0.16, 0, 7); ctx.fill();
  }
  ctx.fillStyle = '#c9b23a'; ctx.fillRect(8.6, 1.3, 0.35, 0.7); ctx.fillRect(9.05, 1.3, 0.35, 0.7);
  // v7: the hose reel on the wall by the airlock, its yellow hose coiled round it
  ctx.strokeStyle = '#e8c547'; ctx.lineWidth = 0.12;
  for (let r = 0.18; r < 0.5; r += 0.1) { ctx.beginPath(); ctx.arc(9.05, 0.75, r, 0, 7); ctx.stroke(); }
  ctx.fillStyle = '#5a4a3a'; ctx.beginPath(); ctx.arc(9.05, 0.75, 0.12, 0, 7); ctx.fill();
  // the airlock: the round outer hatch in the bow, the light over it green when the suit is on
  ctx.strokeStyle = '#9aa4aa'; ctx.lineWidth = 0.22; ctx.beginPath(); ctx.ellipse(13.0, 0.8, 0.55, 1.05, 0, 0, 7); ctx.stroke();
  ctx.fillStyle = '#1d2a33'; ctx.beginPath(); ctx.ellipse(13.0, 0.8, 0.42, 0.9, 0, 0, 7); ctx.fill();
  ctx.fillStyle = '#7fd0ff'; ctx.fillRect(12.85, 0.5, 0.3, 0.5);
  ctx.fillStyle = crew.suit ? '#5fe08a' : '#ff6b5a'; ctx.beginPath(); ctx.arc(12.0, -0.6, 0.14, 0, 7); ctx.fill();
  // the ladder from the lower deck up into the tower
  ctx.strokeStyle = '#c09050'; ctx.lineWidth = 0.08;
  ctx.beginPath(); ctx.moveTo(LADDER - 0.32, -2.3); ctx.lineTo(LADDER - 0.32, LOW); ctx.moveTo(LADDER + 0.32, -2.3); ctx.lineTo(LADDER + 0.32, LOW); ctx.stroke();
  for (let y = -2.2; y < LOW; y += 0.4) { ctx.beginPath(); ctx.moveTo(LADDER - 0.32, y); ctx.lineTo(LADDER + 0.32, y); ctx.stroke(); }
  drawTower(labels);
  // where a tap sent the person
  if (G.mode === 'home' && crew.mark && G.t - crew.mark.t < 0.7) {
    const k = (G.t - crew.mark.t) / 0.7;
    ctx.strokeStyle = `rgba(255,230,150,${1 - k})`; ctx.lineWidth = 0.08;
    ctx.beginPath(); ctx.ellipse(crew.mark.x, crew.mark.y - 0.05, 0.3 + k * 0.5, 0.1 + k * 0.12, 0, 0, 7); ctx.stroke();
  }
  if (G.mode === 'home') {
    if (net) for (const [id, o] of Object.entries(net.others)) if (o.mode === 'home') drawCrew(o, net.cols[id]);
    drawCrew(crew, net && net.cols[R.me]);
  }
  // Room names over everything, on a dark strip, as large as the room allows.
  ctx.save(); ctx.scale(sub.face < 0 ? -1 : 1, 1);
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (const [cx, ty, maxw, label] of labels) {
    ctx.font = '700 1px system-ui';
    const f = Math.min(0.62, maxw / ctx.measureText(label).width), w = ctx.measureText(label).width * f, x = (sub.face < 0 ? -1 : 1) * cx;
    ctx.fillStyle = 'rgba(20,12,4,.6)'; ctx.fillRect(x - w / 2 - 0.12, ty - 0.04, w + 0.24, f * 1.05);
    ctx.font = `700 ${f}px system-ui`; ctx.fillStyle = '#ffe6b8'; ctx.fillText(label, x, ty);
  }
  ctx.restore();
  ctx.restore();
  ctx.strokeStyle = '#e0a526'; ctx.lineWidth = 0.35; hullPath(ctx); ctx.stroke();
}
// The tower's inside (v8): the ladder on up to the hatch, the periscope, a porthole that shows the sky when SISU lies
// surfaced, and the hatch, open while someone is out on the ice.
function drawTower(labels) {
  const A = ctx.globalAlpha;
  ctx.fillStyle = '#2f2a22'; polyPath(ctx, TOWER_IN); ctx.fill();
  ctx.fillRect(LADDER - 0.55, -2.4, 1.1, 0.4);  // the shaft down into the control room
  const g = ctx.createRadialGradient(0.6, -4.6, 0, 0.6, -4.6, 3);
  g.addColorStop(0, 'rgba(255,210,130,.35)'); g.addColorStop(1, 'rgba(255,210,130,0)');
  ctx.fillStyle = g; polyPath(ctx, TOWER_IN); ctx.fill();
  if (G.mode === 'home' && crew.room === 'torni') { ctx.fillStyle = 'rgba(255,230,160,.12)'; polyPath(ctx, TOWER_IN); ctx.fill(); }
  // porthole
  const up = surfaced();
  ctx.fillStyle = up ? '#9cc4e0' : '#0c2a40'; ctx.beginPath(); ctx.arc(2.6, -3.6, 0.38, 0, 7); ctx.fill();
  if (up) { ctx.fillStyle = '#e8f2f8'; ctx.fillRect(2.25, -3.5, 0.7, 0.2); }
  ctx.strokeStyle = '#9aa4aa'; ctx.lineWidth = 0.1; ctx.beginPath(); ctx.arc(2.6, -3.6, 0.42, 0, 7); ctx.stroke();
  // periscope
  ctx.fillStyle = '#6d757a'; ctx.fillRect(0.75, -4.95, 0.28, 2.9);
  ctx.fillStyle = '#3b4245'; ctx.fillRect(0.55, -3.0, 0.68, 0.3); ctx.fillRect(1.03, -2.95, 0.3, 0.12);
  // the ladder to the hatch, and the hatch: a wheel under it, swung open while anyone is on the ice
  ctx.strokeStyle = '#c09050'; ctx.lineWidth = 0.08;
  ctx.beginPath(); ctx.moveTo(LADDER - 0.32, -4.9); ctx.lineTo(LADDER - 0.32, -2.0); ctx.moveTo(LADDER + 0.32, -4.9); ctx.lineTo(LADDER + 0.32, -2.0); ctx.stroke();
  for (let y = -4.7; y < -2; y += 0.4) { ctx.beginPath(); ctx.moveTo(LADDER - 0.32, y); ctx.lineTo(LADDER + 0.32, y); ctx.stroke(); }
  const out = G.mode === 'ice' || (net && Object.values(net.others).some(o => o.mode === 'ice'));
  ctx.fillStyle = '#9aa4aa';
  if (out) { ctx.save(); ctx.translate(LADDER + 0.6, -4.95); ctx.rotate(-1.2); ctx.fillRect(-1.2, -0.08, 1.2, 0.16); ctx.restore();
    ctx.fillStyle = up ? '#9cc4e0' : '#0c2a40'; ctx.fillRect(LADDER - 0.6, -5.15, 1.2, 0.2); }
  else { ctx.fillRect(LADDER - 0.6, -5.05, 1.2, 0.16); ctx.strokeStyle = '#c04030'; ctx.lineWidth = 0.07;
    ctx.beginPath(); ctx.arc(LADDER, -4.72, 0.22, 0, 7); ctx.moveTo(LADDER - 0.22, -4.72); ctx.lineTo(LADDER + 0.22, -4.72); ctx.stroke(); }
  ctx.globalAlpha = A;
  labels.push([1.9, -4.85, 1.9, TOWER.name]);
}
// The person: blue overalls, or the yellow diving suit and helmet; legs swing as they walk, arms reach on the ladder.
function drawCrew(c = crew, col) {
  const swing = c.moving && !c.climbing ? Math.sin(c.walkT * 4.5) * 0.28 : 0;
  ctx.save(); ctx.translate(c.x, c.y); ctx.scale((c.climbing ? 1 : c.dir) * 1.1, 1.1);
  const hs = c.suit && c.kit === 'hose';
  const body = hs ? '#c96a2a' : c.suit ? '#f2c230' : col || '#4fa3ff', dark = hs ? '#7a3a10' : c.suit ? '#a07a10' : col ? 'rgba(0,0,0,.45)' : '#2a5c94';
  ctx.lineCap = 'round';
  ctx.strokeStyle = dark; ctx.lineWidth = 0.2;
  ctx.beginPath(); ctx.moveTo(0, -0.78); ctx.lineTo(swing, -0.02); ctx.moveTo(0, -0.78); ctx.lineTo(-swing, -0.02); ctx.stroke();
  ctx.fillStyle = '#222'; ctx.fillRect(swing - 0.05, -0.08, 0.24, 0.08); ctx.fillRect(-swing - 0.05, -0.08, 0.24, 0.08);
  ctx.fillStyle = body; ctx.fillRect(-0.2, -1.38, 0.4, 0.66);
  ctx.strokeStyle = body; ctx.lineWidth = 0.15;
  const reach = c.climbing ? Math.sin(c.walkT * 4) * 0.25 : 0;
  ctx.beginPath();
  if (c.climbing) { ctx.moveTo(-0.15, -1.3); ctx.lineTo(-0.3, -1.75 + reach); ctx.moveTo(0.15, -1.3); ctx.lineTo(0.3, -1.75 - reach); }
  else { ctx.moveTo(0, -1.3); ctx.lineTo(-swing * 0.8, -0.85); ctx.moveTo(0, -1.3); ctx.lineTo(swing * 0.8 + 0.05, -0.85); }
  ctx.stroke();
  if (c.suit) {
    ctx.fillStyle = hs ? '#d08a3a' : '#e0b020'; ctx.beginPath(); ctx.arc(0, -1.58, hs ? 0.32 : 0.27, 0, 7); ctx.fill();
    ctx.fillStyle = '#9fe2ff'; ctx.beginPath(); ctx.arc(0.08, -1.6, 0.15, 0, 7); ctx.fill();
  } else {
    ctx.fillStyle = '#f0c8a0'; ctx.beginPath(); ctx.arc(0, -1.55, 0.19, 0, 7); ctx.fill();
    ctx.fillStyle = '#c0392b'; ctx.fillRect(-0.2, -1.78, 0.4, 0.12); // a red knit cap
  }
  ctx.restore(); ctx.lineCap = 'butt';
}
function drawDiver(d = diver, col) {
  ctx.save(); ctx.translate(d.x, d.y); ctx.scale(d.dir, 1); ctx.rotate(d.ang);
  const k = Math.sin(G.t * 9) * ((d === diver ? Math.hypot(d.vx, d.vy) > 0.4 : d.moving) ? 0.35 : 0.1);
  ctx.strokeStyle = '#d9a514'; ctx.lineWidth = 0.32; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-0.5, 0.05); ctx.lineTo(-1.25, 0.1 + k); ctx.moveTo(-0.5, 0.1); ctx.lineTo(-1.25, 0.15 - k); ctx.stroke();
  ctx.fillStyle = '#222'; ctx.beginPath();
  ctx.ellipse(-1.5, 0.12 + k * 1.2, 0.4, 0.12, k, 0, 7); ctx.ellipse(-1.5, 0.15 - k * 1.2, 0.4, 0.12, -k, 0, 7); ctx.fill();
  // v7: the tank gear carries its tank; the hose suit is darker, with a round copper helmet.
  const hs = d.kit === 'hose';
  if (!hs) { ctx.fillStyle = '#9aa7ad'; ctx.fillRect(-0.55, -0.48, 0.9, 0.3); }
  ctx.fillStyle = hs ? '#c96a2a' : '#e8b21a'; ctx.beginPath(); ctx.ellipse(0, 0, 0.62, 0.28, 0, 0, 7); ctx.fill();
  ctx.fillStyle = hs ? '#d08a3a' : '#e8b21a'; ctx.beginPath(); ctx.arc(0.8, -0.08, hs ? 0.34 : 0.27, 0, 7); ctx.fill();
  ctx.fillStyle = '#9fe2ff'; ctx.fillRect(0.88, -0.2, 0.18, 0.16);
  ctx.strokeStyle = '#e8b21a'; ctx.lineWidth = 0.16; ctx.beginPath(); ctx.moveTo(0.3, 0.05); ctx.lineTo(0.95, 0.25); ctx.stroke();
  ctx.fillStyle = '#fffbd8'; ctx.beginPath(); ctx.arc(1.0, 0.25, 0.1, 0, 7); ctx.fill();
  // v8: the speargun under the arm
  ctx.fillStyle = '#4a4f52'; ctx.fillRect(0.2, 0.22, 1.1, 0.1);
  if (d !== diver || !G.spear) { ctx.fillStyle = '#d8dde0'; ctx.fillRect(0.5, 0.17, 1.2, 0.05); }
  if (col) { ctx.fillStyle = col; ctx.fillRect(-0.35, -0.27, 0.42, 0.55); }  // the friend's colour on the suit (v5)
  ctx.restore(); ctx.lineCap = 'butt';
}
// Friends' names (v5) over their divers, and inside SISU over the people in it.
function drawNames(ox, oy, sc) {
  ctx.font = '700 12px system-ui, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  for (const [id, o] of Object.entries(net.others)) {
    let wx, wy;
    // v9: a friend in the dark iceberg goes unnamed until a lamp lights them
    if (o.mode === 'dive' && G.lit && pip(o.x, o.y, BERG.poly) && !litAt(o.x, o.y)) continue;
    if (o.mode === 'dive') { wx = o.x; wy = o.y - 1.3; }
    // Inside, clear of the room names: over the hull for the upper deck, on the deck between them for the lower.
    else if (o.mode === 'home' && G.mode === 'home' && G.homeT > 0.5) { wx = sub.x + sub.face * o.x; wy = sub.y + (o.y > 1 ? 0.35 : o.y < -1 ? o.y - 2.1 : -2.75); }
    else if (o.mode === 'ice' && (!inStation(o.x) || (G.mode === 'ice' && inStation(walker.x)))) { wx = o.x; wy = o.y - 2.3; }
    else continue;
    const x = ox + wx * sc, y = Math.max(10, oy + wy * sc - 8), w = ctx.measureText(o.name).width + 10;
    if (x < -w || x > W + w || y > H) continue;
    ctx.fillStyle = 'rgba(2,12,22,.72)'; ctx.fillRect(x - w / 2, y - 8, w, 16);
    ctx.fillStyle = net.cols[id]; ctx.fillText(o.name, x, y + 0.5);
  }
}
// Sonar: the ping ring, the outlines it lights for a moment, and the contacts at the screen's edge.
function drawSonar(ox, oy, sc) {
  const S = (x, y) => [ox + x * sc, oy + y * sc];
  if (G.ping) {
    const age = G.t - G.ping.t, R = Math.min(pingR(), age * 260), a = Math.max(0, 1 - age / 5);
    if (a <= 0) G.ping = null;
    else {
      const [px, py] = S(G.ping.x, G.ping.y);
      ctx.save();
      ctx.beginPath(); ctx.arc(px, py, R * sc, 0, 7); ctx.clip();
      ctx.translate(ox, oy); ctx.scale(sc, sc);
      ctx.strokeStyle = `rgba(110,255,180,${0.8 * a})`; ctx.lineWidth = 2 / sc;
      ctx.beginPath(); FLOOR.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.stroke();
      polyPath(ctx, BERG.poly); ctx.stroke();
      // v9: the echo shows the iceberg's outline but not its maze: that is mapped by lamp
      ctx.beginPath(); for (let y = 0; y <= 120; y += 10) y ? ctx.lineTo(glacierX(y), y) : ctx.moveTo(glacierX(y), y); ctx.stroke();
      // v6: the ice overhead, broken by the openings
      ctx.beginPath();
      for (let x = SHELF_X; x < WORLD_W; x += 4) {
        if (underIce(x) && underIce(x + 4)) { ctx.moveTo(x, ICE_Y); ctx.lineTo(x + 4, ICE_Y); }
      }
      ctx.stroke();
      ctx.strokeStyle = `rgba(255,230,120,${0.9 * a})`;
      for (const s of SITES) ctx.strokeRect(s.x, s.y, s.w * C, s.h * C);
      ctx.restore();
      if (age < 1.8) { ctx.strokeStyle = `rgba(110,255,180,${0.7 * (1 - age / 1.8)})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(px, py, R * sc, 0, 7); ctx.stroke(); }
    }
  }
  if (G.mode !== 'sub') return;
  const target = goalNow().target;
  const top = W > H ? 64 : 112, bottom = H - (W > H ? 110 : 180);
  const list = contacts().map(c => ({ ...c, d: Math.hypot(c.x - sub.x, c.y - sub.y) }))
    .filter(c => c.d < 1000 && c.d > 30).sort((a, b) => a.d - b.d);
  const shown = list.slice(0, 3);
  const tgt = list.find(c => c.id === target);
  if (tgt && !shown.includes(tgt)) shown.push(tgt);
  ctx.font = '700 11px ui-monospace, monospace'; ctx.textBaseline = 'middle';
  const placed = [];
  for (const c of shown) {
    const known = G.s.known[c.id] || (G.s.seen && G.s.seen[c.id]), hot = c.id === target && known;
    const col = hot ? '255,214,90' : '120,255,190';
    const label = known ? c.kind : 'TUNTEMATON KONTAKTI';
    let [x, y] = S(c.x, c.y);
    const on = x > 14 && x < W - 14 && y > top && y < bottom;
    if (!on) {
      const cx = W / 2, cy = (top + bottom) / 2, dx = x - cx, dy = y - cy;
      const k = Math.min((W / 2 - 18) / Math.abs(dx || 1e-6), ((bottom - top) / 2 - 10) / Math.abs(dy || 1e-6));
      x = cx + dx * k; y = cy + dy * k;
      const ang = Math.atan2(dy, dx);
      ctx.fillStyle = `rgba(${col},.95)`;
      ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
      ctx.beginPath(); ctx.moveTo(9, 0); ctx.lineTo(-5, -6); ctx.lineTo(-5, 6); ctx.fill(); ctx.restore();
    } else {
      ctx.strokeStyle = `rgba(${col},${0.6 + 0.3 * Math.sin(G.t * 4)})`; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(x, y, 12, 0, 7); ctx.stroke();
    }
    const t1 = label, t2 = Math.round(c.d) + ' m';
    const tw = Math.max(ctx.measureText(t1).width, ctx.measureText(t2).width) + 10;
    let lx = Math.min(W - tw - 6, Math.max(6, x - tw / 2)), ly = on ? y - 38 : (y > (top + bottom) / 2 ? y - 40 : y + 12);
    ly = Math.max(top - 6, Math.min(bottom - 28, ly));
    for (let n = 0; n < 6 && placed.some(r => lx < r[0] + r[2] && r[0] < lx + tw && ly < r[1] + 30 && r[1] < ly + 30); n++)
      ly = ly + 32 > bottom ? ly - 32 * (n + 1) : ly + 32;
    placed.push([lx, ly, tw]);
    ctx.fillStyle = 'rgba(0,12,10,.7)'; ctx.fillRect(lx, ly, tw, 28);
    ctx.fillStyle = `rgb(${col})`; ctx.textAlign = 'left';
    ctx.fillText(t1, lx + 5, ly + 8); ctx.fillText(t2, lx + 5, ly + 20);
  }
}

// ---------- the stick ----------
(() => {
  const st = $('stick'), kn = $('knob');
  let id = null;
  const move = e => {
    const r = st.getBoundingClientRect(), R = r.width / 2;
    let dx = e.clientX - r.left - R, dy = e.clientY - r.top - R;
    const l = Math.hypot(dx, dy), m = R * 0.75;
    if (l > m) { dx *= m / l; dy *= m / l; }
    kn.style.transform = `translate(${dx}px, ${dy}px)`;
    input.x = Math.abs(dx / m) < 0.12 ? 0 : dx / m; input.y = Math.abs(dy / m) < 0.12 ? 0 : dy / m;
  };
  const end = () => { id = null; input.x = input.y = 0; kn.style.transform = ''; };
  st.addEventListener('pointerdown', e => { audio(); id = e.pointerId; st.setPointerCapture(id); move(e); });
  st.addEventListener('pointermove', e => { if (e.pointerId === id) move(e); });
  st.addEventListener('pointerup', end); st.addEventListener('pointercancel', end);
})();

// Inside SISU a tap on a room walks the person there; on the ice (v6) a tap walks them along it.
cv.addEventListener('pointerup', e => {
  if (G.mode === 'ice' && !G.paused && G.view && !walker.climbing && !walker.inn) {
    walker.to = (e.clientX - cv.getBoundingClientRect().left - G.view.ox) / G.view.sc;
    return;
  }
  if (G.mode !== 'home' || G.paused || !G.view) return;
  audio();
  const r = cv.getBoundingClientRect(), V = G.view, f = Math.abs(sub.face) > 0.2 ? sub.face : sub.dir;
  walkTo(((e.clientX - r.left - V.ox) / V.sc - sub.x) / f, (e.clientY - r.top - V.oy) / V.sc - sub.y);
});

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (!G.hold) step(dt);
  draw();
  requestAnimationFrame(frame);
}
menu();
requestAnimationFrame(frame);
