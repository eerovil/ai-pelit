'use strict';
// v12 (#300): drawing the crates, the weather station and the nomads' camp.
// ---------- crates ----------
// A crate: a wooden box with a stripe in its contents' colour and their sign; junk is plain grey wood.
function drawBox(c, x, y, flip) {
  ctx.save(); ctx.translate(x, y);
  const k = CRATE[c.k], w = BOX_W, h = BOX_H;
  ctx.fillStyle = c.k === 'romu' ? '#6d6256' : '#8a6a42'; ctx.fillRect(-w / 2, -h, w, h);
  ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.fillRect(-w / 2, -h, w, 0.06); ctx.fillRect(-w / 2, -0.06, w, 0.06);
  ctx.fillRect(-w / 2, -h, 0.06, h); ctx.fillRect(w / 2 - 0.06, -h, 0.06, h);
  ctx.strokeStyle = 'rgba(0,0,0,.22)'; ctx.lineWidth = 0.04; ctx.beginPath(); ctx.moveTo(-w / 2, -h); ctx.lineTo(w / 2, 0); ctx.stroke();
  ctx.fillStyle = k.col; ctx.fillRect(-w / 2 + 0.06, -h * 0.62, w - 0.12, h * 0.3);
  if (flip) ctx.scale(-1, 1);
  if (c.k !== 'romu') { ctx.font = '0.3px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(ICON[c.k], 0, -h * 0.47); }
  ctx.restore();
}
// Is this person (this phone's own, or a friend's as drawn) carrying a crate?
function holding(c) {
  if (!G.s) return false;
  if (c === crew || c === walker || c === diver) return !!myCrate();
  return !!(net && G.s.crates.some(k => k.w === 'held' && net.others[k.by] === c));
}
// The crates in the sea and on the ice, in world metres: seen as far as a lamp reaches (on the ice, by daylight; in a
// building, only from inside it). A crate in hands is drawn there.
function drawCrates(X0, X1, Y0, Y1) {
  const ice = G.mode === 'ice', eye = G.mode === 'dive' ? diver : ice ? walker : sub;
  const reach = G.mode === 'dive' ? 13 * LAMP[G.s.up.lamp] : 26, inB = ice && bldAt(walker.x);
  for (const c of G.s.crates) {
    let x = c.x, y = c.y, w = c.w;
    if (w === 'held') { const h = handsOf(c.by); if (!h || h[0] === 'sub') continue; [w, x, y] = h; y += BOX_H / 2; }
    if (w !== 'sea' && w !== 'ice') continue;
    if (x < X0 - 2 || x > X1 + 2 || y < Y0 - 2 || y > Y1 + 2) continue;
    let vis = 1;
    if (w === 'ice') { const b = bldAt(x); if (b && b !== inB) continue; }
    else if (c.w !== 'held') vis = Math.min(1, 1.5 - Math.hypot(x - eye.x, y - eye.y) / reach);
    if (vis <= 0) continue;
    ctx.globalAlpha = vis; drawBox(c, x, y); ctx.globalAlpha = 1;
  }
}
// Inside SISU (hull coordinates, drawn mirrored when SISU faces left): the shelf's crates, the loose ones on the decks,
// and those in someone's hands.
function drawSubCrates() {
  const flip = sub.face < 0;
  for (const c of G.s.crates) {
    if (c.w === 'shelf') drawBox(c, ...SHELF[c.slot], flip);
    else if (c.w === 'sub') drawBox(c, c.x, c.y, flip);
    else if (c.w === 'held' && G.mode === 'home') {
      const h = handsOf(c.by);
      if (h && h[0] === 'sub' && (c.by === me() || (net && net.others[c.by] && net.others[c.by].mode === 'home'))) drawBox(c, h[1], h[2] + BOX_H / 2, flip);
    }
  }
}

// ---------- the weather station ----------
// Two floors on skids east of the iceberg, a lattice mast with a spinning anemometer and a radar dome. Seen from inside
// (this phone's person in it) the wall comes off and the rooms show, the ladder between the floors.
function drawSaa() {
  const S = SAA, [f0, f1] = S.floors, r = S.roof, open = G.mode === 'ice' && bldAt(walker.x) === S;
  // the mast and its anemometer, the dome
  const mx = S.x1 - 5;
  ctx.strokeStyle = '#4b555c'; ctx.lineWidth = 0.25;
  ctx.beginPath(); ctx.moveTo(mx - 1, r); ctx.lineTo(mx, r - 14); ctx.lineTo(mx + 1, r);
  for (let y = r - 2; y > r - 13; y -= 2.2) { ctx.moveTo(mx - 0.9 + (r - y) * 0.07, y); ctx.lineTo(mx + 0.9 - (r - y) * 0.07, y - 1.1); }
  ctx.stroke();
  const a = G.t * 6;
  ctx.strokeStyle = '#2a3036'; ctx.lineWidth = 0.12; ctx.beginPath();
  for (let k = 0; k < 3; k++) { const t = a + k * 2.1; ctx.moveTo(mx, r - 14.6); ctx.lineTo(mx + Math.cos(t) * 1.1, r - 14.6 + Math.sin(t) * 0.35); }
  ctx.stroke();
  ctx.fillStyle = '#e8eef2'; ctx.beginPath(); ctx.arc(S.x0 + 9, r, 2.2, Math.PI, 0); ctx.fill();
  ctx.fillStyle = '#3a454c'; for (let x = S.x0 + 2; x < S.x1; x += 12) ctx.fillRect(x, f0, 1.4, 0.3);  // skids
  if (!open) {
    ctx.fillStyle = '#5f7486'; ctx.fillRect(S.x0, r, S.x1 - S.x0, f0 - r);
    ctx.fillStyle = '#4c5f6e'; ctx.fillRect(S.x0, f1, S.x1 - S.x0, 0.35);
    ctx.fillStyle = '#b8402e'; ctx.fillRect(S.x0, r + 0.5, S.x1 - S.x0, 0.45);
    ctx.fillStyle = '#1c2429';
    for (const fy of [f1 - 2.4, f0 - 2.4]) for (let x = S.x0 + 4; x < S.x1 - 2; x += 5.5) ctx.fillRect(x, fy, 2.2, 1.2);
    ctx.fillStyle = '#c8d6de'; ctx.fillRect(S.x0 + 0.4, f0 - 2.7, 1.6, 2.7);  // the door, facing the opening
    ctx.fillStyle = '#e8d7a8'; ctx.font = '700 1.1px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('SÄÄASEMA', (S.x0 + S.x1) / 2, r + 1.7);
  } else {
    for (const rm of S.rooms) {
      const top = rm.fl ? r : f1, bot = S.floors[rm.fl];
      ctx.fillStyle = rm.id === walker.room ? '#3f4a52' : '#333d45'; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
      const g = ctx.createRadialGradient((rm.x0 + rm.x1) / 2, top + 0.4, 0, (rm.x0 + rm.x1) / 2, top + 0.4, (rm.x1 - rm.x0) * 0.6);
      g.addColorStop(0, 'rgba(220,235,255,.2)'); g.addColorStop(1, 'rgba(220,235,255,0)');
      ctx.fillStyle = g; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
      ctx.fillStyle = '#1a2025'; if (rm.x0 > S.x0) ctx.fillRect(rm.x0 - 0.1, top, 0.2, 1.1);  // walls, open doorways below
    }
    ctx.fillStyle = '#1a2025';
    ctx.fillRect(S.x0, r, S.x1 - S.x0, 0.25); ctx.fillRect(S.x0, f1 - 0.05, S.x1 - S.x0, 0.3); ctx.fillRect(S.x0, f0 - 0.1, S.x1 - S.x0, 0.12);
    ctx.fillRect(S.x1 - 0.4, r, 0.4, f0 - r); ctx.fillRect(S.x0, r, 0.4, f1 - r + 1.2);
    ctx.fillStyle = 'rgba(200,225,240,.35)'; ctx.fillRect(S.x0, f1 + 1.2, 0.4, f0 - f1 - 1.2);  // the open door
    // the hatch in the upper floor and the ladder through it
    ctx.fillStyle = '#333d45'; ctx.fillRect(S.ladder - 0.5, f1 - 0.05, 1, 0.3);
    ctx.strokeStyle = '#c09050'; ctx.lineWidth = 0.08; ctx.beginPath();
    ctx.moveTo(S.ladder - 0.32, f1 - 1.2); ctx.lineTo(S.ladder - 0.32, f0); ctx.moveTo(S.ladder + 0.32, f1 - 1.2); ctx.lineTo(S.ladder + 0.32, f0); ctx.stroke();
    for (let y = f1 - 1; y < f0; y += 0.4) { ctx.beginPath(); ctx.moveTo(S.ladder - 0.32, y); ctx.lineTo(S.ladder + 0.32, y); ctx.stroke(); }
    // frost on the walls
    ctx.fillStyle = 'rgba(230,245,255,.18)'; for (let x = S.x0 + 1; x < S.x1; x += 3.1) ctx.fillRect(x, r + 0.25, 1.2, 0.18 + (x * 7 % 3) * 0.1);
    // downstairs: coats in the hall; store shelves; the generator with its fuel cans
    for (let n = 0; n < 2; n++) { ctx.fillStyle = ['#2f6f8f', '#c9b23a'][n]; ctx.fillRect(S.x0 + 2 + n * 1.6, f0 - 2.6, 0.9, 1.5); }
    ctx.fillStyle = '#6b5236'; for (const y of [f0 - 2.2, f0 - 1.2]) ctx.fillRect(6296, y, 5, 0.1);
    ctx.fillStyle = '#4c5458'; ctx.fillRect(6305, f0 - 1.6, 4.4, 1.6); ctx.fillStyle = '#3a4246'; ctx.fillRect(6306, f0 - 2.1, 1.4, 0.5);
    ctx.fillStyle = '#a03a2a'; for (let n = 0; n < 3; n++) ctx.fillRect(6311 + n * 0.8, f0 - 0.7, 0.6, 0.7);
    // upstairs: the instrument desk, a barograph, the radio; bunks with frozen blankets
    ctx.fillStyle = '#6b5236'; ctx.fillRect(6280, f1 - 1.1, 8, 0.18); ctx.fillRect(6280.3, f1 - 0.95, 0.15, 0.95); ctx.fillRect(6287.5, f1 - 0.95, 0.15, 0.95);
    ctx.fillStyle = '#2b3236'; ctx.fillRect(6281, f1 - 2.3, 2.6, 1.2);
    ctx.fillStyle = '#e8eef2'; ctx.fillRect(6284.4, f1 - 1.7, 1.6, 0.6);
    ctx.strokeStyle = '#c0392b'; ctx.lineWidth = 0.05; ctx.beginPath(); ctx.moveTo(6284.5, f1 - 1.4);
    for (let x = 6284.5; x < 6286; x += 0.15) ctx.lineTo(x, f1 - 1.4 - Math.sin(x * 9) * 0.12 - (x - 6284.5) * 0.08); ctx.stroke();
    ctx.fillStyle = '#5a4a3a'; for (const x of [6299, 6306]) { ctx.fillRect(x, f1 - 0.6, 4.5, 0.16); ctx.fillRect(x, f1 - 2, 4.5, 0.16); }
    ctx.fillStyle = '#8fa4b4'; for (const x of [6299, 6306]) { ctx.fillRect(x + 0.1, f1 - 0.85, 4.2, 0.25); ctx.fillRect(x + 0.1, f1 - 2.25, 4.2, 0.25); }
    // room names along each ceiling
    ctx.font = '700 0.62px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    for (const rm of S.rooms) {
      const top = rm.fl ? r : f1 + 0.25, w = ctx.measureText(rm.name).width, cx = (rm.x0 + rm.x1) / 2;
      ctx.fillStyle = 'rgba(10,14,18,.6)'; ctx.fillRect(cx - w / 2 - 0.12, top + 0.32, w + 0.24, 0.7);
      ctx.fillStyle = '#e6f2ff'; ctx.fillText(rm.name, cx, top + 0.36);
    }
  }
  ctx.fillStyle = '#eef6fb'; ctx.fillRect(S.x0 - 0.4, r - 0.45, S.x1 - S.x0 + 0.8, 0.5);  // snow on the roof
}

// ---------- the nomads' camp ----------
// Three tents of hide on poles, a fire, a sled and its dogs, and the people: the elder by the fire, two others.
function drawCamp() {
  const g = ICE_TOP;
  // the sled and the dogs lying in the snow
  ctx.fillStyle = '#6b4a2a'; ctx.fillRect(CAMP.x0, g - 0.5, 3.4, 0.12); ctx.fillRect(CAMP.x0 + 0.2, g - 0.9, 0.1, 0.4); ctx.fillRect(CAMP.x0 + 3.1, g - 0.9, 0.1, 0.4);
  ctx.strokeStyle = '#4a3a2a'; ctx.lineWidth = 0.08; ctx.beginPath(); ctx.moveTo(CAMP.x0 - 0.3, g - 0.05); ctx.quadraticCurveTo(CAMP.x0 + 1.7, g + 0.15, CAMP.x0 + 3.8, g - 0.15); ctx.stroke();
  for (let n = 0; n < 3; n++) {
    const x = CAMP.x0 + 5 + n * 1.6, t = Math.sin(G.t * 2 + n) * 0.06;
    ctx.fillStyle = ['#d8d0c4', '#7a6a5a', '#3a3632'][n]; ctx.beginPath(); ctx.ellipse(x, g - 0.25, 0.55, 0.25, 0, 0, 7); ctx.fill();
    ctx.beginPath(); ctx.arc(x + 0.5, g - 0.45 + t, 0.18, 0, 7); ctx.fill();
    polyPath(ctx, [[x + 0.45, g - 0.6 + t], [x + 0.55, g - 0.8 + t], [x + 0.62, g - 0.58 + t]]); ctx.fill();
  }
  // the tents
  for (const [x, col] of [[CAMP.x0 + 14, '#8a6a4a'], [CAMP.fire + 18, '#7a5a3a'], [CAMP.x1 - 8, '#96785a']]) {
    ctx.fillStyle = col; polyPath(ctx, [[x - 3.4, g], [x, g - 6], [x + 3.4, g]]); ctx.fill();
    ctx.fillStyle = 'rgba(0,0,0,.18)'; polyPath(ctx, [[x, g - 6], [x + 3.4, g], [x + 1.2, g]]); ctx.fill();
    ctx.fillStyle = '#2a1d13'; polyPath(ctx, [[x - 0.7, g], [x, g - 1.8], [x + 0.7, g]]); ctx.fill();
    ctx.strokeStyle = '#4a3a2a'; ctx.lineWidth = 0.1; ctx.beginPath();
    ctx.moveTo(x - 0.5, g - 6.8); ctx.lineTo(x + 0.4, g - 5.6); ctx.moveTo(x + 0.5, g - 6.8); ctx.lineTo(x - 0.4, g - 5.6); ctx.stroke();
    ctx.fillStyle = '#f4f9fc'; polyPath(ctx, [[x - 3.4, g], [x - 2.6, g - 1.4], [x - 1.8, g]]); ctx.fill();
  }
  // the fire: logs, flames, sparks and its warm light on the snow
  const f = CAMP.fire, fl = 0.8 + Math.sin(G.t * 11) * 0.12 + Math.sin(G.t * 7.3) * 0.1;
  const lg = ctx.createRadialGradient(f, g - 0.5, 0, f, g - 0.5, 6);
  lg.addColorStop(0, 'rgba(255,170,80,.35)'); lg.addColorStop(1, 'rgba(255,170,80,0)');
  ctx.fillStyle = lg; ctx.beginPath(); ctx.arc(f, g - 0.5, 6, 0, 7); ctx.fill();
  ctx.fillStyle = '#4a3020'; ctx.save(); ctx.translate(f, g - 0.12); ctx.rotate(0.25); ctx.fillRect(-0.8, -0.08, 1.6, 0.16); ctx.rotate(-0.5); ctx.fillRect(-0.8, -0.08, 1.6, 0.16); ctx.restore();
  ctx.fillStyle = '#ff7a2a'; polyPath(ctx, [[f - 0.5, g - 0.15], [f - 0.1, g - 1.1 * fl], [f + 0.1, g - 0.6], [f + 0.25, g - 1.35 * fl], [f + 0.5, g - 0.15]]); ctx.fill();
  ctx.fillStyle = '#ffd65a'; polyPath(ctx, [[f - 0.25, g - 0.15], [f, g - 0.75 * fl], [f + 0.25, g - 0.15]]); ctx.fill();
  ctx.fillStyle = 'rgba(255,200,120,.8)';
  for (let k = 0; k < 4; k++) { const a = (G.t * 0.7 + k / 4) % 1; ctx.fillRect(f + Math.sin(G.t * 3 + k * 2) * 0.4, g - 1 - a * 3, 0.07, 0.07); }
  // the people in fur: the elder sitting by the fire, two standing
  nomad(CAMP.elder, g, true, '#6a4a32');
  nomad(f - 3.5, g, false, '#5a3e2a', 1);
  nomad(CAMP.fire + 11, g, false, '#7a5636', 1);
}
function nomad(x, g, sit, col, dir = -1) {
  ctx.save(); ctx.translate(x, g); ctx.scale(dir * 1.1, 1.1);
  if (sit) {
    ctx.fillStyle = '#4a3a2a'; ctx.fillRect(-0.4, -0.35, 0.8, 0.35);  // a log to sit on
    ctx.fillStyle = col; polyPath(ctx, [[-0.32, -0.35], [-0.24, -1.2], [0.24, -1.2], [0.32, -0.35]]); ctx.fill();
    ctx.fillRect(0, -0.5, 0.55, 0.16);
    ctx.fillStyle = '#e8dcc8'; ctx.beginPath(); ctx.arc(0, -1.42, 0.27, 0, 7); ctx.fill();  // the fur hood
    ctx.fillStyle = '#c89a78'; ctx.beginPath(); ctx.arc(0.06, -1.4, 0.15, 0, 7); ctx.fill();
  } else {
    ctx.fillStyle = '#3a2a1a'; ctx.fillRect(-0.16, -0.75, 0.13, 0.75); ctx.fillRect(0.04, -0.75, 0.13, 0.75);
    ctx.fillStyle = col; polyPath(ctx, [[-0.36, -0.6], [-0.24, -1.5], [0.24, -1.5], [0.36, -0.6]]); ctx.fill();
    ctx.fillStyle = '#e8dcc8'; ctx.beginPath(); ctx.arc(0, -1.72, 0.28, 0, 7); ctx.fill();
    ctx.fillStyle = '#c89a78'; ctx.beginPath(); ctx.arc(0.06, -1.7, 0.15, 0, 7); ctx.fill();
  }
  ctx.restore();
}

// ---------- the research station Aurora (v13, #300) ----------
// On the ice over its moon pool: a long three-floor building with a dome, an antenna and the greenhouse's lit windows
// (dark brown until the pump is in). Seen from inside, the wall comes off: the dock round the pool, the pump room, the
// hydroponics and the mess, the control room and the living quarters, the ladders, and the three survivors.
function drawAurora() {
  const A = AUR, [f0, f1, f2] = A.floors, r = A.roof, open = G.mode === 'ice' && bldAt(walker.x) === A, green = !!(G.s && G.s.flags.pumppu);
  const [p0, p1] = HOLES[A.pool];
  // the antenna mast and the dome
  ctx.strokeStyle = '#4b555c'; ctx.lineWidth = 0.25;
  ctx.beginPath(); ctx.moveTo(A.x1 - 6, r); ctx.lineTo(A.x1 - 6, r - 12); ctx.moveTo(A.x1 - 8, r - 9); ctx.lineTo(A.x1 - 4, r - 9); ctx.stroke();
  ctx.fillStyle = (G.t % 2 < 1) ? '#ff4030' : '#601810'; ctx.beginPath(); ctx.arc(A.x1 - 6, r - 12.4, 0.5, 0, 7); ctx.fill();
  ctx.fillStyle = '#e8eef2'; ctx.beginPath(); ctx.arc(A.x0 + 10, r, 3, Math.PI, 0); ctx.fill();
  if (!open) {
    ctx.fillStyle = '#d9dee2'; ctx.fillRect(A.x0, r, A.x1 - A.x0, f0 - r);
    ctx.fillStyle = '#c2484a'; ctx.fillRect(A.x0, r + 0.6, A.x1 - A.x0, 0.5); ctx.fillRect(A.x0, f1 - 0.2, A.x1 - A.x0, 0.25); ctx.fillRect(A.x0, f2 - 0.2, A.x1 - A.x0, 0.25);
    for (const [fy, lit] of [[f2, '#ffe8a8'], [f1, null], [f0, '#ffe8a8']]) for (let x = A.x0 + 3; x < A.x1 - 2; x += 6) {
      const gh = !lit && x < 1150;  // the greenhouse windows on the middle floor
      ctx.fillStyle = gh ? (green ? '#8fe07a' : '#5a4630') : lit || '#ffe8a8';
      ctx.fillRect(x, fy - 2.4, gh ? 4.4 : 2.2, 1.2);
    }
    ctx.fillStyle = '#2a3a4a'; ctx.font = '700 1.3px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('AURORA', (A.x0 + A.x1) / 2, r + 2.4);
    ctx.fillStyle = '#eef6fb'; ctx.fillRect(A.x0 - 0.4, r - 0.45, A.x1 - A.x0 + 0.8, 0.5);
    return;
  }
  // inside: the rooms, floor by floor
  for (const rm of A.rooms) {
    const top = rm.fl === 2 ? r : A.floors[rm.fl + 1], bot = A.floors[rm.fl];
    ctx.fillStyle = rm.id === walker.room ? '#3e4a52' : '#343f47'; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
    const g = ctx.createRadialGradient((rm.x0 + rm.x1) / 2, top + 0.4, 0, (rm.x0 + rm.x1) / 2, top + 0.4, (rm.x1 - rm.x0) * 0.6);
    g.addColorStop(0, 'rgba(255,235,190,.22)'); g.addColorStop(1, 'rgba(255,235,190,0)');
    ctx.fillStyle = g; ctx.fillRect(rm.x0, top, rm.x1 - rm.x0, bot - top);
    ctx.fillStyle = '#1a2025'; if (rm.x0 > A.x0) ctx.fillRect(rm.x0 - 0.1, top, 0.2, 1.2);
  }
  // the floors' slabs (the dock's has the pool cut out), the outer walls, the ladders through their hatches
  ctx.fillStyle = '#1a2025';
  ctx.fillRect(A.x0, r, A.x1 - A.x0, 0.25); ctx.fillRect(A.x0, f2 - 0.05, A.x1 - A.x0, 0.3); ctx.fillRect(A.x0, f1 - 0.05, A.x1 - A.x0, 0.3);
  ctx.fillRect(A.x0, f0 - 0.1, p0 - A.x0, 0.3); ctx.fillRect(p1, f0 - 0.1, A.x1 - p1, 0.3);
  ctx.fillRect(A.x0, r, 0.4, f0 - r); ctx.fillRect(A.x1 - 0.4, r, 0.4, f0 - r);
  ctx.fillStyle = 'rgba(40,110,150,.55)'; ctx.fillRect(p0, f0 + 0.2, p1 - p0, 0.6);  // the moon pool's water
  ctx.strokeStyle = '#9aa4aa'; ctx.lineWidth = 0.12; ctx.beginPath(); ctx.moveTo(p0, f0 - 1); ctx.lineTo(p1, f0 - 1); ctx.stroke();  // its rail
  for (const [fl, x] of A.ladders) {
    const lo = A.floors[fl], hi = A.floors[fl + 1] - 0.6;
    ctx.fillStyle = '#343f47'; ctx.fillRect(x - 0.5, A.floors[fl + 1] - 0.05, 1, 0.3);
    ctx.strokeStyle = '#c09050'; ctx.lineWidth = 0.08; ctx.beginPath();
    ctx.moveTo(x - 0.32, hi); ctx.lineTo(x - 0.32, lo); ctx.moveTo(x + 0.32, hi); ctx.lineTo(x + 0.32, lo); ctx.stroke();
    for (let y = hi + 0.2; y < lo; y += 0.4) { ctx.beginPath(); ctx.moveTo(x - 0.32, y); ctx.lineTo(x + 0.32, y); ctx.stroke(); }
  }
  // the dock: a winch over the pool, diving gear on the wall; the pump room's broken pipes (whole once fixed)
  ctx.fillStyle = '#56606a'; ctx.fillRect((p0 + p1) / 2 - 0.2, f1 + 0.25, 0.4, 1.4);
  ctx.strokeStyle = '#3a4248'; ctx.lineWidth = 0.06; ctx.beginPath(); ctx.moveTo((p0 + p1) / 2, f1 + 1.6); ctx.lineTo((p0 + p1) / 2, f0 - 1.8); ctx.stroke();
  for (let n = 0; n < 3; n++) { ctx.fillStyle = ['#e0b020', '#c96a2a', '#e0b020'][n]; ctx.fillRect(A.x0 + 2 + n * 1.5, f0 - 2.6, 0.9, 1.4); }
  ctx.strokeStyle = '#6a7a84'; ctx.lineWidth = 0.25; ctx.beginPath();
  ctx.moveTo(1169, f0 - 0.5); ctx.lineTo(1169, f1 + 0.4); ctx.moveTo(1171, f0 - 0.5); ctx.lineTo(1171, f0 - 2.4); ctx.stroke();
  ctx.fillStyle = green ? '#3a7ab8' : '#5a4a3a'; ctx.fillRect(1170, f0 - 1.6, 1.4, 1.2);
  // hydroponics: racks of plants under grow lights
  for (let rack = 0; rack < 3; rack++) {
    const x = 1119 + rack * 9;
    ctx.fillStyle = '#6b7a84'; for (const y of [f1 - 1.1, f1 - 2.5]) ctx.fillRect(x, y, 7, 0.15);
    ctx.fillStyle = green ? 'rgba(255,120,220,.35)' : 'rgba(255,120,220,.08)'; ctx.fillRect(x, f2 + 0.3, 7, 0.25);
    for (const y of [f1 - 1.1, f1 - 2.5]) for (let k = 0; k < 7; k++) {
      ctx.fillStyle = green ? (k % 2 ? '#5fc04a' : '#3f9a3a') : (k % 2 ? '#7a6040' : '#5a4630');
      ctx.beginPath(); ctx.ellipse(x + 0.5 + k, y - (green ? 0.35 : 0.15), 0.4, green ? 0.35 : 0.15, 0, 0, 7); ctx.fill();
    }
  }
  // the mess: a table, a stove; the control room: screens and the radio; the quarters: bunks
  ctx.fillStyle = '#6b5236'; ctx.fillRect(1158, f1 - 0.85, 4, 0.12); ctx.fillRect(1158.3, f1 - 0.75, 0.12, 0.75); ctx.fillRect(1161.6, f1 - 0.75, 0.12, 0.75);
  ctx.fillStyle = '#3a3a3a'; ctx.fillRect(1170, f1 - 0.9, 1, 0.9);
  ctx.fillStyle = '#123'; ctx.fillRect(1119, f2 - 2.2, 6, 1.2); ctx.fillStyle = '#5fe0a0'; ctx.fillRect(1119.3, f2 - 2, 2.4, 0.8); ctx.fillStyle = '#5fb0ff'; ctx.fillRect(1122.2, f2 - 2, 2.4, 0.8);
  ctx.fillStyle = '#6b4a2a'; ctx.fillRect(1119, f2 - 0.9, 6, 0.15);
  ctx.fillStyle = '#5a4a3a'; for (const x of [1148, 1156, 1164]) { ctx.fillRect(x, f2 - 0.55, 4.5, 0.15); ctx.fillRect(x, f2 - 1.95, 4.5, 0.15); }
  ctx.fillStyle = '#9fb6c9'; for (const x of [1148, 1156, 1164]) { ctx.fillRect(x + 0.1, f2 - 0.78, 4.2, 0.24); ctx.fillRect(x + 0.1, f2 - 2.18, 4.2, 0.24); }
  // the survivors
  for (const p of CREW13) survivor(p.x, A.floors[p.fl], p.col, p.lead && Math.abs(walker.x - p.x) < 8 && walker.fl === p.fl);
  // room names
  ctx.font = '700 0.62px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (const rm of A.rooms) {
    const top = (rm.fl === 2 ? r : A.floors[rm.fl + 1]) + 0.3, w = ctx.measureText(rm.name).width, cx = (rm.x0 + rm.x1) / 2;
    ctx.fillStyle = 'rgba(10,14,18,.6)'; ctx.fillRect(cx - w / 2 - 0.12, top + 0.02, w + 0.24, 0.7);
    ctx.fillStyle = '#e6f2ff'; ctx.fillText(rm.name, cx, top + 0.06);
  }
}
// A survivor in a thick sweater and a knit cap; the one who talks waves.
function survivor(x, y, col, wave) {
  ctx.save(); ctx.translate(x, y); ctx.scale(-1.1, 1.1);
  ctx.fillStyle = '#2a2a30'; ctx.fillRect(-0.16, -0.75, 0.13, 0.75); ctx.fillRect(0.04, -0.75, 0.13, 0.75);
  ctx.fillStyle = col; ctx.fillRect(-0.22, -1.4, 0.44, 0.7);
  ctx.strokeStyle = col; ctx.lineWidth = 0.15; ctx.beginPath(); ctx.moveTo(0.1, -1.3);
  if (wave) ctx.lineTo(0.35, -1.75 - Math.abs(Math.sin(G.t * 4)) * 0.15); else ctx.lineTo(0.2, -0.85);
  ctx.stroke();
  ctx.fillStyle = '#e8c4a0'; ctx.beginPath(); ctx.arc(0, -1.58, 0.19, 0, 7); ctx.fill();
  ctx.fillStyle = '#d9d0c0'; ctx.fillRect(-0.21, -1.8, 0.42, 0.14);
  ctx.restore();
}
