'use strict';
// The world (v9 split it out of index.html, #161): the sea floor, the ice, the places to dive, the iceberg's maze,
// the finds, the logs, SISU's rooms, the game's state and its save, the chart's maps, the geometry and the goals.
const KEY = 'ai-pelit:last-signal:';
const C = 2;                       // a site's grid cell, in metres
const WORLD_W = 4500;
const SHELF_X = 240, SHELF_Y = 5;  // the ice shelf at the head of the bay
const RATING = [0, 160, 260, 380, 620, 1000, 1450]; // hull level → safe depth (m)
const TANK = [0, 60, 90, 120, 150];  // tank level → seconds of air
// v7 (#145): two suits. The tank gear goes no deeper than TANK_MAX. The hose suit is joined to SISU by a hose that
// brings air, heat, power and the radio; its level gives its length (m) and how little it wears on a corner
// (TOUGH). A cut hose leaves the suit's own emergency air (EMERG s). WEAR: % of the hose lost per metre it slides
// over an unguided corner.
const TANK_MAX = 260;
const HOSE = [0, 80, 120, 180, 260], TOUGH = [0, 1, 0.8, 0.65, 0.5], EMERG = 25;
const WEAR = { metal: 0.2, ice: 0.1 }, FISH_BITE = 30, GUIDE_R = 2.2;
const LAMP = [0, 1, 1.45, 1.9];
const COST = { hull: [0, 0, 3, 5, 5, 6, 7], tank: [0, 0, 2, 3, 4], hose: [0, 0, 2, 3, 4], lamp: [0, 0, 2, 4] };
const COLD = 600, CHILL = 1.35;     // below this depth the cold water drains a diver's air faster
const DIVER_SPEED = 4.4, SUB_SPEED = 16;
const WALK = 4.2, CLIMB = 2.6;      // the person inside SISU (v3), in m/s

// The ice (v6, #143): the sea is frozen over from the ice shelf to the far end, the top of the ice at ICE_TOP and its
// underside at ICE_Y. SISU comes up only in the openings (HOLES, [x0, x1]); at SURF its tower and back are out of the
// water. The first opening is in front of the station on the ice shelf. The iceberg stands in the ice on its own.
const ICE_TOP = -0.8, ICE_Y = 3, SURF = 1.2;
const HOLES = [[256, 290], [932, 966], [1994, 2028], [3004, 3038]];
const BERG_X = [2084, 2420];
function holeAt(x) { return HOLES.findIndex(([a, b]) => x > a && x < b); }
function holeMid(n) { return (HOLES[n][0] + HOLES[n][1]) / 2; }
function underIce(x) { return x >= SHELF_X && holeAt(x) < 0 && !(x > BERG_X[0] && x < BERG_X[1]); }
// The station on the ice (the top half of A-3, whose lower module stands on the floor below): one floor of rooms on
// the shelf, walked from its door at the seaward end. Outside, the cold runs the warmth meter down in WARM seconds.
const STATION = { x0: 120, x1: 212, floor: -2.5, roof: -6.4 };
const SROOMS = [
  { id: 'svarasto', name: 'Varasto', x0: 120, x1: 140 },
  { id: 'smakuu', name: 'Makuuhuone', x0: 140, x1: 160 },
  { id: 'slabra', name: 'Laboratorio', x0: 160, x1: 180 },
  { id: 'sradio', name: 'Radiohuone', x0: 180, x1: 198 },
  { id: 'seteinen', name: 'Eteinen', x0: 198, x1: 212 },
];
const WARM = 60, WARMUP = 35;
function inStation(x) { return x > STATION.x0 && x < STATION.x1; }
function stationRoom(x) { return SROOMS.find(r => x >= r.x0 && x < r.x1) || null; }

// The sea floor, left to right: glacier bay, a ridge, the wreck field, a deep trench, the iceberg field, and
// in v2 the continental slope down in ledges, the Nordlys ledge at ~900 m and the deep sea beyond 1300 m.
const FLOOR = [[0, 105], [60, 112], [140, 118], [230, 122], [330, 126], [450, 132], [560, 136], [640, 136], [720, 130],
  [800, 138], [860, 104], [905, 110], [960, 180], [1040, 238], [1090, 246], [1180, 246], [1260, 242], [1340, 248],
  [1400, 248], [1470, 252], [1580, 252], [1660, 240], [1730, 300], [1765, 362], [1815, 362], [1850, 310], [1920, 250],
  [2000, 230], [2080, 270], [2200, 300], [2350, 290], [2480, 300], [2560, 330], [2700, 345], [2760, 400], [2830, 440],
  [2900, 445], [2950, 500], [3020, 580], [3120, 590], [3180, 650], [3260, 760], [3330, 860], [3400, 902], [3560, 906],
  [3640, 900], [3700, 960], [3780, 1090], [3850, 1210], [3920, 1320], [4000, 1345], [4160, 1350], [4260, 1330],
  [4380, 1352], [4460, 1300], [4500, 1250]];
function floorY(x) {
  if (x <= FLOOR[0][0]) return FLOOR[0][1];
  for (let i = 1; i < FLOOR.length; i++) {
    const [x1, y1] = FLOOR[i];
    if (x <= x1) { const [x0, y0] = FLOOR[i - 1]; return y0 + (y1 - y0) * (x - x0) / (x1 - x0); }
  }
  return FLOOR[FLOOR.length - 1][1];
}
function glacierX(y) { return 34 + Math.max(0, y) * 0.12; }

// Places the diver can swim into. '#' wall, '.' water inside, ' ' outside; letters are finds:
// r food, l medicine, o spare part, A radio amplifier, a air pocket, L the site's log.
const SITES = [
  { id: 'asema', kind: 'METALLIRAKENNE', name: 'Tutkimusasema A-3', shell: 'station', x: 150, y: 22, log: 'asema', sample: 'vesi',
    spot: [180, 46], cells: [
      '##############################',
      '#....#........#.....#........#',
      '#.L..#...r....#..o..#...a....#',
      '#............................#',
      '#....#........#.....#........#',
      '#.l..#..o.....#..A..#...r....#',
      '#....#..S.....#.....#........#',
      '#######...####################'] },
  { id: 'kontti', kind: 'KONTTI', name: 'Kontti', shell: 'box', x: 596, floor: true, color: '#b5532c',
    spot: [575, 122], cells: [
      '#######',
      '..r..o#',
      '....r.#',
      '#######'] },
  { id: 'polaris', kind: 'HYLKY', name: 'Polaris', shell: 'ship', x: 1104, floor: true, log: 'polaris',
    spot: [1180, 222], cells: [
      '         ######      #      ',
      '         #.L..#      #      ',
      '#########.....#############.',
      '#...r..#......#....o......#.',
      '#......D......D...........D.',
      '#..#####......#####.#######.',
      '#..#..o.......#.....#..r..#.',
      '##.#....l.....D.....D.....#.',
      ' ###########################'] },
  { id: 'kontit', kind: 'KONTTEJA', name: 'Konttipino', shell: 'box', x: 1362, floor: true, color: '#2f6f8f',
    spot: [1350, 228], cells: [
      '######  ',
      '..o.l#  ',
      '######  ',
      '  ######',
      '  ..r..#',
      '  ######'] },
  { id: 'nordvik', kind: 'HYLKY', name: 'Nordvik', shell: 'ship', x: 1490, floor: true, log: 'nordvik',
    spot: [1478, 232], cells: [
      '  ####                          ',
      '  #..#                          ',
      '###..##########################',
      '#.......#.......#.......#.....##',
      'D...o...D...r...D...L...D..o...#',
      '#.......#.......#.......#.....##',
      '#..r....#...l...#.......#..a..# ',
      '############################### '] },
  { id: 'syva', kind: 'KONTTI', name: 'Avustuskontti', shell: 'box', x: 1780, floor: true, color: '#c9b23a', log: 'avustus',
    spot: [1770, 345], cells: [
      '########',
      '...o.o.#',
      '..L.o.l#',
      '########'] },
  // Chapter 2 (v2): the cable ship on the slope's edge, the Nordlys lander and containers on the ledges, the
  // research vessel Nordlys at the foot of the slope, and the Lyra beacon on the deep plain. A digit is a log,
  // named in the site's `logs`; T, V and K are the Nordlys diving tank, Lyra's lamp and the beacon's memory card.
  { id: 'saga', kind: 'HYLKY', name: 'Kaapelilaiva Saga', shell: 'ship', x: 2588, floor: true, log: 'saga',
    spot: [2570, 300], cells: [
      '   ####                   ',
      '   #L.#                   ',
      '###..#####################',
      '#..o...#.....o..#....o...#',
      'D..........r....D........D',
      '#..#####.#######.#####...#',
      '#..o...#..o.a...#..o.....#',
      '##########################'] },
  { id: 'laskeutuja', kind: 'METALLIRAKENNE', name: 'Nordlysin pohjalaskeutuja', shell: 'station', x: 2842, floor: true,
    log: 'laskeutuja', spot: [2812, 414], cells: [
      '  ######  ',
      '  #.L..#  ',
      '###....###',
      '#o..##..o#',
      '...r..a.o#',
      '##########'] },
  { id: 'rinne', kind: 'KONTTEJA', name: 'Rinteen kontit', shell: 'box', x: 3052, floor: true, color: '#7a3f8f',
    spot: [3034, 566], cells: [
      '######  ',
      '..o.r#  ',
      '######  ',
      '  ######',
      '  ..l.o#',
      '  ######'] },
  { id: 'nordlys', kind: 'SUURI HYLKY', name: 'Tutkimusalus Nordlys', shell: 'rv', x: 3420, floor: true, deck: 4, sample: 'pullo',
    logs: { 1: 'silta', 2: 'labra', 3: 'kartta', 4: 'halli' }, spot: [3452, 879],
    rooms: [[38, 1, 'Karttahuone'], [46.5, 1, 'Komentosilta'], [5, 5, 'Työpaja'], [15.5, 5, 'Laboratorio'],
      [26.5, 5, 'Messi'], [37.5, 5, 'Sukellusvarusteet'], [50, 5, 'Keulavarasto'], [9, 9, 'Tutkimussukellusveneen halli'],
      [31, 9, 'Lastiruuma'], [51, 9, 'Konehuone']], cells: [
      '                                  ##################          ',
      '                                  #......#.........#          ',
      '                                  #..3...D....1....D          ',
      '                                  #......#.........#          ',
      '############D###############################D#################',
      '#......o.#...........#........a.#.........#.........r....#####',
      '#..o.....D....2......D......r...D....T....D.....o........#####',
      '#.....o..#..S.....l..#...r......#.......a.#...........l..#### ',
      '####D####################D####################D############## ',
      'D................#.................a........#.........a..###  ',
      'D.......4........D......o...................D.....o......###  ',
      'D............V...#............r.........o...#............##   ',
      '##########################################################    '] },
  { id: 'majakka', kind: 'HEIKKO SIGNAALI', name: 'Lyran majakka', shell: 'beacon', x: 4172, floor: true, sample: 'suomu',
    logs: { 4: 'majakka' }, spot: [4150, 1320], cells: [
      '  ####  ',
      '###..###',
      '..K.4..#',
      '#..a.S.#',
      '########'] },
];

// The iceberg: an outline that is solid ice, hollowed by caves (segments with a radius). v9 (#160): the caves are a
// maze — short, narrow, winding passages close together, with dead ends — in the berg's west half: the way in on
// the left, a small hall in the middle, a shaft up to daylight, and below a lower cave with a crack down into the
// deep. The cache K-7 lies apart in the east, through the east crack (v7). The maze comes from a fixed seed, so every
// phone and every visit has the same one.
const BERG = {
  poly: [[2088, -1], [2082, 30], [2090, 75], [2110, 130], [2150, 178], [2215, 203], [2295, 200], [2360, 172], [2400, 120],
    [2418, 60], [2420, -1]],
  top: [[2084, 0], [2096, -14], [2110, -18], [2124, -34], [2140, -36], [2158, -52], [2178, -48], [2196, -60], [2214, -54],
    [2236, -40], [2262, -44], [2286, -30], [2318, -38], [2336, -70], [2350, -66], [2366, -40], [2392, -26], [2412, -10], [2422, 0]],
  caves: [],
};
// The maze's crossings: `cols` × `rows` of them, `d` metres apart; the hall takes the ones in HALL.
const MAZE = { x: 2104, y: 18, d: 7, cols: 11, rows: 9, edges: [], ends: [] };
const HALL = { i0: 4, i1: 6, j0: 3, j1: 4, x: 2139, y: 42.5 };
const MAZE_P = [];
(() => {
  let a = 160;
  const rnd = () => (a = (Math.imul(a, 1664525) + 1013904223) >>> 0) / 4294967296;
  const { cols, rows, d } = MAZE, id = (i, j) => i + j * cols;
  const hall = (i, j) => i >= HALL.i0 && i <= HALL.i1 && j >= HALL.j0 && j <= HALL.j1;
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++)
    MAZE_P.push(hall(i, j) ? null : [MAZE.x + i * d + (rnd() - 0.5) * 2, MAZE.y + j * d + (rnd() - 0.5) * 2]);
  const near = n => {
    const i = n % cols, j = (n - i) / cols;
    return [[i - 1, j], [i + 1, j], [i, j - 1], [i, j + 1]].filter(([p, q]) => p >= 0 && q >= 0 && p < cols && q < rows && !hall(p, q))
      .map(([p, q]) => id(p, q));
  };
  // Grown from the way in, joining a random neighbour at a time: many short side passages and dead ends.
  const start = id(0, 4), inn = new Set([start]), walls = near(start).map(m => [start, m]), E = MAZE.edges;
  while (walls.length) {
    const [n, m] = walls.splice(Math.floor(rnd() * walls.length), 1)[0];
    if (inn.has(m)) continue;
    inn.add(m); E.push([n, m]);
    for (const k of near(m)) if (!inn.has(k)) walls.push([m, k]);
  }
  // A few loops, so a wrong turn is not always the whole way back.
  for (let k = 0, tries = 0; k < 6 && tries < 400; tries++) {
    const n = Math.floor(rnd() * MAZE_P.length), ms = MAZE_P[n] ? near(n) : [], m = ms[Math.floor(rnd() * ms.length)];
    if (m == null || E.some(([p, q]) => (p === n && q === m) || (p === m && q === n))) continue;
    E.push([n, m]); k++;
  }
  const P = n => MAZE_P[n], C2 = BERG.caves;
  for (const [n, m] of E) C2.push([...P(n), ...P(m), 1.25 + rnd() * 0.45]);
  // The way in, the hall and its three doors, the shaft up to the air gap under the moulin, the lower cave and the crack.
  C2.push([2058, 50, ...P(start), 1.7], [HALL.x - 4, HALL.y, HALL.x + 4, HALL.y, 5.5],
    [...P(id(3, 3)), HALL.x, HALL.y, 1.5], [...P(id(7, 4)), HALL.x, HALL.y, 1.5], [...P(id(5, 5)), HALL.x, HALL.y, 1.5],
    [...P(id(8, 0)), 2161, 9, 1.6], [2157, 9, 2165, 9, 2.4],
    [...P(id(5, 8)), 2140, 84, 1.5], [2128, 87, 2152, 88, 3.2], [2150, 89, 2157, 108, 1.3], [2157, 108, 2155, 121, 1.0],
    // v7 (#145): the cache K-7, and a crack in the east side, so a short hose reaches it from outside
    [2335, 99, 2368, 102, 5], [2366, 103, 2420, 105, 1.8]);
  // The dead ends, farthest from the way in first, and each at least two crossings from the ones before it: the maze's
  // own finds wait there.
  const deg = new Map(), adj = new Map(), far = new Map([[start, 0]]), q = [start];
  for (const n of [start, id(3, 3), id(7, 4), id(5, 5), id(8, 0), id(5, 8)]) deg.set(n, 1);
  for (const [n, m] of E) {
    for (const [p, r] of [[n, m], [m, n]]) { deg.set(p, (deg.get(p) || 0) + 1); adj.set(p, (adj.get(p) || []).concat(r)); }
  }
  for (let h = 0; h < q.length; h++) for (const m of adj.get(q[h]) || []) if (!far.has(m)) { far.set(m, far.get(q[h]) + 1); q.push(m); }
  for (const n of [...far.keys()].filter(n => deg.get(n) === 1).sort((n, m) => far.get(m) - far.get(n)))
    if (MAZE.ends.every(e => Math.hypot(e[0] - P(n)[0], e[1] - P(n)[1]) > d * 2.5)) MAZE.ends.push(P(n));
})();
const BERG_SITE = { id: 'jaavuori', kind: 'AUKKO JÄÄSSÄ', name: 'Jäävuoren luolasto', x: 2072, y: 52, spot: [2050, 52] };
const BERG_EAST = { id: 'itarailo', kind: 'RAILO JÄÄSSÄ', name: 'Jäävuoren itärailo', x: 2416, y: 105, spot: [2424, 105] };
// v9: the caves as a grid of distances to their walls, 0.5 m apart and negative in the water, so the maze's many
// passages cost nothing to test; and the outline of the walls, cut into the 2 m squares (RV) that a lamp maps.
const CF = { x0: 2040, y0: -4, s: 0.5, w: 800, h: 432 };
const CFD = new Float32Array(CF.w * CF.h).fill(9);
for (const [ax, ay, bx, by, r] of BERG.caves) {
  const i0 = Math.max(0, Math.floor((Math.min(ax, bx) - r - 2 - CF.x0) / CF.s)), i1 = Math.min(CF.w - 1, Math.ceil((Math.max(ax, bx) + r + 2 - CF.x0) / CF.s));
  const j0 = Math.max(0, Math.floor((Math.min(ay, by) - r - 2 - CF.y0) / CF.s)), j1 = Math.min(CF.h - 1, Math.ceil((Math.max(ay, by) + r + 2 - CF.y0) / CF.s));
  for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
    const k = i + j * CF.w, v = segDist(CF.x0 + i * CF.s, CF.y0 + j * CF.s, ax, ay, bx, by) - r;
    if (v < CFD[k]) CFD[k] = v;
  }
}
function caveD(x, y) {
  const fx = (x - CF.x0) / CF.s, fy = (y - CF.y0) / CF.s, i = Math.floor(fx), j = Math.floor(fy);
  if (!(i >= 0 && j >= 0 && i < CF.w - 1 && j < CF.h - 1)) return 9;
  const u = fx - i, v = fy - j, k = i + j * CF.w;
  return (CFD[k] * (1 - u) + CFD[k + 1] * u) * (1 - v) + (CFD[k + CF.w] * (1 - u) + CFD[k + CF.w + 1] * u) * v;
}
const RV = { x0: 2040, y0: -4, s: 2, w: 200, h: 108 };
function rvAt(x, y) {
  const i = Math.floor((x - RV.x0) / RV.s), j = Math.floor((y - RV.y0) / RV.s);
  return i >= 0 && j >= 0 && i < RV.w && j < RV.h ? i + j * RV.w : -1;
}
// The walls' outline by marching squares, as [x1, y1, x2, y2, ...] for each 2 m square it runs through.
const CAVE_LINES = new Map();
for (let j = 0; j < CF.h - 1; j++) for (let i = 0; i < CF.w - 1; i++) {
  const k = i + j * CF.w, a = CFD[k], b = CFD[k + 1], c = CFD[k + CF.w + 1], d = CFD[k + CF.w];
  if ((a < 0) === (b < 0) && (b < 0) === (c < 0) && (c < 0) === (d < 0)) continue;
  const v = [a, b, c, d];
  const x = CF.x0 + i * CF.s, y = CF.y0 + j * CF.s, s = CF.s, pts = [];
  const cut = (a, b, ax, ay, bx, by) => { if ((a < 0) !== (b < 0)) { const t = a / (a - b); pts.push(ax + (bx - ax) * t, ay + (by - ay) * t); } };
  cut(v[0], v[1], x, y, x + s, y); cut(v[1], v[2], x + s, y, x + s, y + s); cut(v[3], v[2], x, y + s, x + s, y + s); cut(v[0], v[3], x, y, x, y + s);
  if (!pip(x + s / 2, y + s / 2, BERG.poly)) continue;  // only walls of ice, not the way in out in the open sea
  const n = rvAt(x + s / 2, y + s / 2), l = CAVE_LINES.get(n) || [];
  for (let p = 0; p + 3 < pts.length; p += 4) l.push(pts[p], pts[p + 1], pts[p + 2], pts[p + 3]);
  CAVE_LINES.set(n, l);
}

// v8: S is a sample for the lab (`SAMPLES`, named by the site's `sample`); a harpooned fish is 'kala'.
const KINDS = { r: 'ruoka', l: 'laake', o: 'osa', A: 'vahvistin', N: 'antenni', a: 'ilma', L: 'loki', T: 'saili', V: 'valo',
  K: 'kortti', S: 'nayte' };
const ICON = { ruoka: '🥫', laake: '💊', osa: '⚙️', vahvistin: '📟', antenni: '📡', loki: '📓', saili: '➰', valo: '🔦', kortti: '💾',
  ohjain: '📌', nayte: '🧪', kala: '🐟' };
const NAME = { ruoka: 'Ruoka-annos', laake: 'Lääkkeet', osa: 'Varaosa', vahvistin: 'Radion vahvistin', antenni: 'Radioantenni',
  saili: 'Nordlysin letkukela', valo: 'Lyran valonheitin', kortti: 'Majakan muistikortti', ohjain: 'Letkunohjain',
  nayte: 'Näyte', kala: 'Kala' };
const ITEMS = [];
for (const s of SITES) {
  s.h = s.cells.length;
  s.w = Math.max(...s.cells.map(r => r.length));
  if (s.floor) s.y = Math.min(...[0, 0.5, 1].map(f => floorY(s.x + f * s.w * C))) - s.h * C + 0.6;
  s.cells.forEach((row, j) => [...row].forEach((ch, i) => {
    const log = ch === 'L' ? s.log : s.logs && s.logs[ch];
    if (KINDS[ch] || log) ITEMS.push({ id: s.id + ':' + i + ',' + j, k: log ? 'loki' : KINDS[ch], x: s.x + i * C + 1,
      y: s.y + j * C + 1, site: s.id, log: log || null, sample: ch === 'S' ? s.sample : undefined });
  }));
}
// v9: the cave's finds keep their numbers (a save remembers them by it), in the new maze: four of them at its farthest
// dead ends, an air pocket each in the hall, the lower cave and the cache.
const END = MAZE.ends;
[['a', ...END[3]], ['a', HALL.x + 2, HALL.y - 4], ['a', 2131, 85.5], ['a', 2161, 10], ['a', 2352, 97.5], ['r', ...END[0]],
  ['o', ...END[1]], ['r', ...END[2]],
  ['L', 2337, 100, 'k7'], ['N', 2366, 102], ['o', 2345, 104], ['o', 2356, 97], ['r', 2350, 101], ['l', 2361, 105],
  ['o', 2147, 89.5], ['L', 2155, 120, 'syvyys'], ['S', HALL.x - 2, HALL.y + 3.5, 'jaa']].forEach(([ch, x, y, log], n) =>
  ITEMS.push(ch === 'S' ? { id: 'jaavuori:' + n, k: 'nayte', x, y, site: 'jaavuori', log: null, sample: log }
    : { id: 'jaavuori:' + n, k: KINDS[ch], x, y, site: 'jaavuori', log: log || null }));

// The station on the ice (v6): two notes, and the stores the crew left behind.
const ICE_ITEMS = [
  { id: 'pinta:loki', k: 'loki', x: 190, y: -3.3, site: 'pinta', log: 'paivakirja' },
  { id: 'pinta:taulu', k: 'loki', x: 170, y: -3.3, site: 'pinta', log: 'taulu' },
  { id: 'pinta:l', k: 'laake', x: 151, y: -3.1, site: 'pinta' },
  { id: 'pinta:r1', k: 'ruoka', x: 136, y: -3.1, site: 'pinta' },
  { id: 'pinta:r2', k: 'ruoka', x: 133, y: -3.1, site: 'pinta' },
  { id: 'pinta:o1', k: 'osa', x: 127, y: -3.1, site: 'pinta' },
  { id: 'pinta:o2', k: 'osa', x: 124, y: -3.1, site: 'pinta' },
];
// The lab (v8, #151): each sample, once studied in SISU's lab, tells a little of what happened and helps for good.
const SAMPLES = {
  vesi: { name: 'Merivesinäyte', where: 'aseman alamoduulista', paras: [
    { t: 'Vesi on puhdasta, eikä säteilymittari värähdäkään. Planktonia on enemmän kuin koskaan.', c: 'log' },
    { t: 'Virtausmittari näyttää, miten vesi kulkee lahdelta itään. Ajat nyt virran mukana.' }],
    gain: 'SISU kulkee 10 % nopeammin' },
  jaa: { name: 'Jääydin', where: 'jäävuoren suuresta salista', paras: [
    { t: 'Jään kerrokset ovat kuin vuosirenkaat. Ylimpien joukossa on ohut punainen juova: rautapölyä taivaalta, samana keväänä.', c: 'log' },
    { t: 'Nyt tiedät, missä jää on pehmeää ja missä terävää.' }],
    gain: 'letku hankautuu jäähän puolet vähemmän' },
  pullo: { name: 'Nordlysin näytepullo', where: 'Nordlysin laboratoriosta', paras: [
    { t: 'Pullon etiketissä lukee »Päivä 0, pinta». Vedessä on rautaa ja varautuneita hiukkasia, jotka satoivat taivaalta samana päivänä kuin revontulet.', c: 'log' },
    { t: 'Pullon alla on Nordlysin kaikuluotaimen säätötaulukko. Säädät SISUn sonarin samoin.' }],
    gain: 'sonarin ping kuuluu 600 metriin' },
  bakteeri: { name: 'Lähteiden bakteerimatto', where: 'lämpimien lähteiden luota', paras: [
    { t: 'Bakteerit elävät lähteiden lämmöstä ja kemiasta, eivät auringosta – ja voivat hyvin. Täällä alhaalla mikään ei muuttunut.', c: 'log' },
    { t: 'Opit niiltä saman kuin Nordlysin tutkijat: kylmässä hengitetään hitaasti.' }],
    gain: 'kylmä vesi kuluttaa happea hitaammin' },
  suomu: { name: 'Valokalan suomu', where: 'Lyran majakalta', paras: [
    { t: 'Suomu hehkuu vielä mikroskoopin alla. Kalat ovat sokeita: ne seuraavat valoa ja tärinää.', c: 'log' },
    { t: 'Himmennät valot, kun ne lähestyvät. Ne eivät enää ryntää päin yhtä kovaa.' }],
    gain: 'valokalat tönivät ja purevat puolet vähemmän' },
};
// v8: the bacterial mat by the hot vents, beside Lyra's beacon.
ITEMS.push({ id: 'lahteet:bakteeri', k: 'nayte', x: 4164, y: Math.round((floorY(4164) - 0.9) * 10) / 10, site: 'majakka', log: null, sample: 'bakteeri' });
// A studied sample's help (v8): 1 while not studied.
function lab(key, k) { return G.s && G.s.lab && G.s.lab[key] ? k : 1; }
const LOGS = {
  asema: { title: 'Aseman päiväkirja', paras: [
    { t: '2.3. Revontulet eivät sammu, vaikka on päivä. Kompassit pyörivät ympyrää.', c: 'log' },
    { t: '4.3. Mantereelta ei vastata millään taajuudella. Satelliittipuhelin näyttää vain viivaa.', c: 'log' },
    { t: '6.3. Nordlys hakee meidät huomenna. Jätin radion varavahvistimen tutkimusmoduuliin – jos joku joskus tarvitsee sitä.', c: 'log' },
    { t: 'Joku muukin on siis ollut täällä. Minne he lähtivät?' }] },
  paivakirja: { title: 'A-3:n radiopäiväkirja', paras: [
    { t: '»1.3. Aurinko ei noussut, vaikka kalenterin mukaan pitäisi. Revontulet loistavat keskipäivällä.»', c: 'log' },
    { t: '»5.3. Meri jäätyy umpeen. Vain railot pysyvät auki. Nordlys lupasi lähettää veneen alakautta, jään alta.»', c: 'log' },
    { t: 'He odottivat täällä apua. Apu tuli meren alta – niin kuin sinäkin.' }] },
  taulu: { title: 'Laboratorion valkotaulu', paras: [
    { t: 'Taululle on kirjoitettu isoin kirjaimin: »JÄÄ PAKSUNEE 4 CM / VRK. PINTA EI OLE TURVALLINEN. ALAS MODUULIIN.»', c: 'log' },
    { t: 'Alla pienemmällä: »Kaikki varaosat ja ruoka varastoon. Jos joku tulee perässä, ottakoon.»', c: 'log' },
    { t: 'Varasto on aseman perällä, jäätikön puolella.', c: 'msg' }] },
  polaris: { title: 'Polariksen radioloki', paras: [
    { t: '»...kaikille aluksille: älkää palatko satamiin. Toistan: älkää palatko satamiin...»', c: 'log' },
    { t: 'Alla käsin kirjoitettuna: »Hilma, odota minua. Tulen kotiin keväällä.»', c: 'log' },
    { t: 'Kevät tuli. Polaris ei koskaan lähtenyt.' }] },
  nordvik: { title: 'Nordvikin rahtikirja', paras: [
    { t: 'Rahtikirjan kääntöpuolelle on piirretty kartta: »Nordlysin huoltovarasto K-7 – jäävuoren luolassa itäisellä kentällä. Varaosia, ruokaa, radioantenni.»', c: 'log' },
    { t: 'Nordlys – sama alus, joka haki aseman väen. Itään siis.', c: 'msg' }] },
  avustus: { title: 'Avustuskontti', paras: [
    { t: 'Kontin kyljessä lukee: HUMANITARIAN AID. Sisällä on lääkkeitä ja varaosia, siististi pakattuina.', c: 'log' },
    { t: 'Joku yritti auttaa. Se tuntuu oudon lohdulliselta.' }] },
  k7: { title: 'Huoltovarasto K-7', paras: [
    { t: '»K-7. Otimme mitä tarvitsimme. Nordlys lähtee syvemmälle, mannerrinteelle – siellä vesi on lämpimämpää ja hiljaista.»', c: 'log' },
    { t: '»Jätimme varaantennin. Jos löydät tämän, kuuntele 4,2 megahertsiä.»', c: 'log' },
    { t: 'Ota antenni mukaan ja vie se kotiin radioon.', c: 'msg' }] },
  syvyys: { title: 'Syvä railo', paras: [
    { t: 'Railo kapenee liian ahtaaksi. Jostain syvältä kuuluu tasaista naputusta: kolme lyhyttä, kolme pitkää, kolme lyhyttä.', c: 'log' },
    { t: 'Ehkä se on vain jää. Ehkä ei.' }] },
  saga: { title: 'Sagan kaapeliloki', paras: [
    { t: '»14.3. Laskimme kaapelia mannerrinteen reunalle, kun kaikki yhteydet katkesivat yhtä aikaa. Vika ei ollut kaapelissa.»', c: 'log' },
    { t: '»Nordlys kävi luonamme. He laskivat rinteelle pohjalaskeutujan mittaamaan jotain ja jatkoivat alas, syvemmälle.»', c: 'log' },
    { t: 'Rinne jatkuu jyrkkänä pimeyteen. Laskeutuja on yli 380 metrissä.', c: 'msg' }] },
  laskeutuja: { title: 'Pohjalaskeutujan muisti', paras: [
    { t: '»NORDLYS / LASKEUTUJA 2. Veden lämpötila nousee syvemmällä. Pohjasta kuuluu ääniä, joita emme tunnista.»', c: 'log' },
    { t: '»Viimeinen merkintä: Nordlys ankkuroi rinteen juurelle, 900 metriin.»', c: 'log' },
    { t: 'Yhdeksänsataa metriä – sama luku kuin radiossa.', c: 'msg' }] },
  silta: { title: 'Kapteenin loki', paras: [
    { t: '»Päivä 41. Ankkuroimme rinteen juurelle. Täällä on hiljaista. Liian hiljaista nukkua.»', c: 'log' },
    { t: '»Päivä 58. Runko vuotaa, eikä Nordlys enää nouse. Lähdemme Lyralla. Emme anna periksi.»', c: 'log' },
    { t: 'Komentosilta on tyhjä. Nordlys on hylätty – mutta miehistö lähti itse.', c: 'msg' }] },
  labra: { title: 'Tutkijan muistiinpanot', paras: [
    { t: '»Revontulet näkyivät päivälläkin, kaikkialla maailmassa yhtä aikaa. Sähköverkot paloivat. Sen jälkeen tuli hiljaisuus.»', c: 'log' },
    { t: '»Pinnalla on kylmää ja autiota. Syvällä, lämpimien lähteiden luona, elämä jatkuu kuin mitään ei olisi tapahtunut.»', c: 'log' },
    { t: 'Ehkä vastaus on syvemmällä.' }] },
  kartta: { title: 'Karttahuone', paras: [
    { t: 'Pöydällä on kartta. Lyijykynäviiva kulkee rinnettä alas syvälle tasangolle ja päättyy ympyrään: »Lähteet, 1300 m. Majakka.»', c: 'log' },
    { t: '»Jos joku tulee perässä: seuraa majakan naputusta.»', c: 'log' },
    { t: 'Naputusta – samaa, jonka kuulit jäävuoren railossa?', c: 'msg' }] },
  halli: { title: 'Lyran halli', paras: [
    { t: 'Halli on tyhjä. Lattiassa on Lyran kiinnityspultit, irrotettuina. Seinään on raapustettu: »9 + Lyra. Alas.»', c: 'log' },
    { t: 'Yhdeksän ihmistä pienessä sukellusveneessä, matkalla syvemmälle. Lyran varavalonheitin on jäänyt hyllylle.', c: 'msg' }] },
  majakka: { title: 'Lyran majakka', paras: [
    { t: 'Majakka naputtaa tasaisesti: kolme lyhyttä, kolme pitkää, kolme lyhyttä. Sama ääni kuului jäävuoren railossa.', c: 'log' },
    { t: 'Sen kyljessä on muistikortti ja teksti: »Soita tämä radiolla.»', c: 'log' },
    { t: 'Vie muistikortti kotiin radioon.', c: 'msg' }] },
};
// The deep sea (v2): glowing fish swim slow loops (x, y, reach across, reach up and down, speed) and bump into the
// diver or SISU; hot vents stand on the deep plain, solid chimneys whose warm water keeps the cold away.
const FISH = [[3300, 742, 22, 6, 0.3], [3600, 860, 28, 8, 0.25], [3810, 1075, 16, 8, 0.35], [4080, 1300, 36, 10, 0.22],
  [4300, 1288, 30, 10, 0.28], [4425, 1262, 18, 8, 0.32]];
const VENTS = [[4062, 12], [4112, 8], [4232, 14], [4318, 10]];
function fishAt(n, t) {
  const [x, y, rx, ry, sp] = FISH[n];
  return { x: x + Math.sin(t * sp + n * 2) * rx, y: y + Math.sin(t * sp * 1.7 + n) * ry, dir: Math.cos(t * sp + n * 2) >= 0 ? 1 : -1 };
}
function nearVent(x, y, r) { return VENTS.some(([vx, h]) => Math.hypot(x - vx, y - (floorY(vx) - h)) < r); }
// Schools of small fish (v8, #151) in the shallow bay and the wreck field: (x, y, reach across, reach up and down,
// how many). They come back each night; a speared one is a fish carried home and cooked in the galley.
const SCHOOLS = [[372, 40, 22, 6, 7], [530, 78, 26, 8, 6], [760, 96, 20, 6, 7], [1230, 205, 22, 8, 7], [1640, 214, 18, 6, 6]];
const SPEAR = { speed: 22, range: 11, reload: 1, hit: 1.1 };
// Where fish k of school n is at time t: the school wanders, each fish circles in it, and they all shy away from a
// diver within 6 m (`from`).
function schoolFish(n, k, t, from) {
  const [x, y, rx, ry] = SCHOOLS[n], sp = 0.07 + n * 0.01;
  let fx = x + Math.sin(t * sp + n * 1.7) * rx + Math.cos(k * 2.4 + t * (0.8 + k * 0.05)) * 2.4;
  let fy = y + Math.sin(t * sp * 1.6 + n) * ry + Math.sin(k * 1.7 + t * (1.1 + k * 0.04)) * 1.2;
  for (const d of from || []) {
    const dx = fx - d.x, dy = fy - d.y, l = Math.hypot(dx, dy);
    if (l < 6 && l > 0.01) { fx += dx / l * (6 - l) * 0.9; fy += dy / l * (6 - l) * 0.5; }
  }
  return { x: fx, y: fy, dir: Math.cos(t * sp + n * 1.7) >= 0 ? 1 : -1 };
}
// The fish of every school still swimming today, where they are now.
function fishNow() {
  const out = [], from = G.mode === 'dive' ? [diver] : [];
  if (net) for (const o of Object.values(net.others)) if (o.mode === 'dive') from.push(o);
  const caught = (G.s && G.s.caught) || {};
  SCHOOLS.forEach((S, n) => {
    for (let k = 0; k < S[4]; k++) if (!(caught[n] || []).includes(k) && !G.pending[n + ':' + k]) out.push({ n, k, ...schoolFish(n, k, G.t, from) });
  });
  return out;
}
const DAY_LINES = ['Unessa kuulit lokkien huudon. Herätessä oli taas vain reaktorin humina.',
  'Keität teetä viimeisistä lehdistä. Ikkunan takana on pimeää ja hiljaista.',
  'Kirjoitat päiväkirjaan yhden rivin: vielä täällä.',
  'Radio rätisee hetken. Sitten taas kohinaa.',
  'Näit unta kaupungista, jossa kaikki valot paloivat.'];

// SISU inside (v3, #132), from the SISU picture of #125: the reactor in the stern and the airlock in the bow are full
// height; between them two decks joined by the ladder under the tower. x runs stern → bow in metres from the middle of
// the hull, y down; a person stands on the upper deck at y = UP and on the lower deck at y = LOW.
const UP = 0, LOW = 2, LADDER = -1.4;
// v8 (#151): the ladder goes on up the tower to its hatch; at the top (TOP) the person stands under the hatch.
const TOP = -3.3;
const TOWER = { id: 'torni', name: 'Torni' };
const DECK_X = [[-8.2, 9.3], [-11.2, 11.8]];
const ROOMS = [
  { id: 'reaktori', name: 'Reaktori', x0: -14, x1: -8.5, deck: 1, tall: true, col: '#3a3f44',
    say: 'Reaktori hurisee tasaisesti. Virtaa riittää vuosiksi.' },
  { id: 'keittio', name: 'Keittiö', x0: -8.5, x1: -2, deck: 0, col: '#5a3b22' },
  { id: 'ohjaamo', name: 'Ohjaamo', x0: -2, x1: 3.3, deck: 0, col: '#3b3422' },
  { id: 'kartta', name: 'Labra ja kartat', x0: 3.3, x1: 6.3, deck: 0, col: '#2c3836' },
  { id: 'punkka', name: 'Punkka', x0: 6.3, x1: 10, deck: 0, col: '#55372a' },
  { id: 'sahko', name: 'Sähkö', x0: -8.5, x1: -5.3, deck: 1, col: '#33393a',
    say: 'Sähkötaulu napsuu. Kaikki valot palavat vihreinä.' },
  { id: 'paja', name: 'Työpaja', x0: -5.3, x1: -2, deck: 1, col: '#43372c' },
  { id: 'varasto', name: 'Varasto', x0: -2, x1: 4, deck: 1, col: '#4a3926' },
  { id: 'puvut', name: 'Sukelluspuvut', x0: 4, x1: 10, deck: 1, col: '#3d3527' },
  { id: 'ilmalukko', name: 'Ilmalukko', x0: 10, x1: 15, deck: 1, tall: true, col: '#33393d' },
];
// The room at (x, y) in hull coordinates; the tall rooms reach from the ceiling to the lower deck.
function roomOf(x, y) {
  if (y < -2.35 && Math.abs(x - LADDER) < 1.6) return TOWER;
  const deck = y > 0 ? 1 : 0;
  return ROOMS.find(r => x >= r.x0 && x < r.x1 && (r.tall || r.deck === deck)) || null;
}

// ---------- state ----------
// `held` (v5): every find a diver has picked up and not yet brought home, by who holds it ('me' when playing alone);
// `carry` is this phone's own share of it. `asked`: finds this phone has asked the host for on this dive.
const G = { mode: 'menu', s: null, t: 0, hold: false, paused: false, sc: 4, cx: 380, cy: 30, ping: null, pingCd: 0,
  carry: [], held: {}, asked: {}, homeT: 0, toastT: 0, hitCd: 0, warnCd: 0, saveCd: 0, lastGoal: '', fishCd: 0,
  coldSaid: false, card: '', iceCd: 0, hoseSaid: false, ropeCd: 0, harpCd: 0, spear: null, pending: {}, parviSaid: false };
const sub = { x: 330, y: 30, vx: 0, vy: 0, dir: 1, face: 1, prop: 0 };
// `kit` (v7): the suit, 'tank' or 'hose'.
const diver = { x: 0, y: 0, vx: 0, vy: 0, dir: 1, air: 60, ang: 0, kit: 'tank' };
// This phone's hose-suit diver's hose (v7): the corners it bends round on its way from the airlock ([x, y, 1 on
// metal]), how worn it is (%), and whether it is cut; then `air` is the suit's emergency air.
const hose = { pts: [], wear: 0, cut: false, len: 0 };
// The person inside SISU: where they stand, whether the diving suit is on, and where a tap sent them (`to`).
const crew = { x: 0.6, y: UP, dir: 1, suit: false, kit: 'tank', to: null, room: 'ohjaamo', said: '', walkT: 0, moving: false, climbing: false,
  mark: null };
// The person out on the ice (v6), in world metres (y down, the feet at y): `warm` runs down outside, `to` is a tap.
const walker = { x: 0, y: 0, dir: 1, to: null, warm: 100, walkT: 0, moving: false, climbing: false, suit: false, room: '' };
const input = { x: 0, y: 0 };
// Playing with friends (v5, #138): null when playing alone. See "playing with friends" below.
let net = null;
const snow = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), z: 0.4 + Math.random() * 0.8 }));
const bubbles = [];

function fresh() {
  return { v: 1, day: 1, t: 0, sub: { x: 330, y: 30, dir: 1 }, m: { food: 70, health: 100, hull: 100 },
    inv: { ruoka: 2, laake: 1, osat: 0, vahvistin: 0, antenni: 0, kortti: 0, ohjain: 2, kala: 0 }, up: { hull: 1, tank: 1, hose: 1, lamp: 1 },
    got: {}, known: {}, flags: {}, finds: [{ id: 'f0', k: 'ruoka', x: 700, y: floorY(700) - 0.9 }], findN: 1, guides: [],
    lab: {}, caught: {}, heard: {}, seen: {}, chart: '', cave: '' };
}
function load() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY + 'peli'));
    // A v1 save loads as it is (AGENTS.md rule 5); the parts v2 added start empty, v7's hose at its first level with two guides,
    // v8's fish, lab and schools empty.
    // v9's chart starts from what the save already knows (`seedMaps`), and a hose guide left in an old cave wall goes
    // back into the stores.
    if (s && s.v === 1) { const f = fresh(), o = Object.assign(f, s); o.inv = Object.assign({ kortti: 0, ohjain: 2, kala: 0 }, s.inv);
      o.up = Object.assign({ hose: 1 }, s.up);
      if (!('chart' in s)) o.seed = true;
      const keep = o.guides.filter(g => !(pip(g[0], g[1], BERG.poly) && caveD(g[0], g[1]) > 0.8));
      o.inv.ohjain += o.guides.length - keep.length; o.guides = keep;
      return o; }
  } catch (e) {}
  return null;
}
function save() {
  // A friend in the host's game (v5) never saves it, so their own Last Signal save stays as it was.
  if (!G.s || (net && !net.host)) return;
  if (net) net.dirty = true;
  G.s.sub = { x: Math.round(sub.x * 10) / 10, y: Math.round(sub.y * 10) / 10, dir: sub.dir };
  if (G.mapNew) { G.s.cave = pack(caveSeen); G.s.chart = pack(chartSeen); G.mapNew = false; }
  try { localStorage.setItem(KEY + 'peli', JSON.stringify(G.s)); } catch (e) {}
}

// ---------- the chart (v9, #160) ----------
// The chart in the navigation room shows only what has been explored: 20 m squares of the sea that SISU's lamp, a
// ping, a diver or a walker has reached (`chartSeen`), and the iceberg's outline as far as a lamp has lit it
// (`caveSeen`). A contact is first heard (❓), then known once a ping names its kind, then seen up close (its name).
// Both maps are kept in the save as bits.
const CH = { x0: 0, y0: -60, s: 20, w: 225, h: 74 };
const chartSeen = new Uint8Array(CH.w * CH.h);
function chartSee(x, y, r) {
  const i0 = Math.max(0, Math.floor((x - r - CH.x0) / CH.s)), i1 = Math.min(CH.w - 1, Math.floor((x + r - CH.x0) / CH.s));
  const j0 = Math.max(0, Math.floor((y - r - CH.y0) / CH.s)), j1 = Math.min(CH.h - 1, Math.floor((y + r - CH.y0) / CH.s));
  for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
    const n = i + j * CH.w;
    if (chartSeen[n]) continue;
    const cx = CH.x0 + (i + 0.5) * CH.s, cy = CH.y0 + (j + 0.5) * CH.s;
    // the sea and the floor's face, not the rock deep under it
    if (cy < floorY(cx) + 30 && Math.hypot(cx - x, cy - y) < r + CH.s * 0.5) { chartSeen[n] = 1; G.mapNew = true; }
  }
}
function pack(a) {
  let bin = '';
  for (let i = 0; i < a.length; i += 8) { let b = 0; for (let k = 0; k < 8; k++) if (a[i + k]) b |= 1 << k; bin += String.fromCharCode(b); }
  return btoa(bin);
}
function unpack(str, a) {
  a.fill(0);
  let bin = '';
  try { bin = atob(str || ''); } catch (e) { return; }
  for (let i = 0; i < bin.length; i++) { const b = bin.charCodeAt(i); for (let k = 0; k < 8; k++) if (b >> k & 1 && i * 8 + k < a.length) a[i * 8 + k] = 1; }
}
// The maps follow the game this phone shows: the host's own, or (a friend's phone) the latest the host sent.
let mapsOf = null;
function syncMaps() {
  if (!G.s || G.s === mapsOf) return;
  mapsOf = G.s; unpack(G.s.cave, caveSeen); unpack(G.s.chart, chartSeen);
  if (G.s.seed) seedMaps();
}
// A save from v8 or earlier: what it already knows goes on the chart — the contacts pinged, the places dived, and
// the sea round them and round SISU.
function seedMaps() {
  const s = G.s;
  delete s.seed;
  for (const c of contacts()) {
    if (s.known[c.id]) s.heard[c.id] = 1;
    if (s.flags[c.id]) { s.heard[c.id] = s.seen[c.id] = 1; chartSee(c.x, c.y, 80); }
  }
  chartSee(sub.x, sub.y, 22);
  G.mapNew = true;
}
// Every 0.1 s on the host (or alone): what the lamps light goes on the chart — SISU's glow and beam, each diver's —
// and walkers on the ice see round them in the daylight; every lamp in the iceberg maps the walls it lights. Contacts
// within the sonar's hearing are heard; one is seen only when a lamp actually lights it with nothing in between.
function mapStep() {
  const s = G.s, f = sub.face >= 0 ? 1 : -1, L = LAMP[s.up.lamp];
  // [x, y, beam direction, beam reach, glow, beam half-width]
  const lamps = [[sub.x, sub.y, 0, 0, 22, 0], [sub.x + f * 14, sub.y + 0.5, f > 0 ? 0.12 : Math.PI - 0.12, 60 * L, 0, 0.42]];
  const walkers = [];
  const mark = d => {
    const l = lampOf(d);
    lamps.push([...l, 0.55]);
    if (d.x > 2078 && d.x < 2424 && d.y < 206 && pip(d.x, d.y, BERG.poly)) lampPoly(l[0], l[1], l[2], 0.55, l[3], l[4], true);
  };
  if (G.mode === 'dive') mark(diver);
  if (G.mode === 'ice') walkers.push(walker);
  if (net) for (const o of Object.values(net.others)) {
    if (o.mode === 'dive') mark(o);
    else if (o.mode === 'ice') walkers.push(o);
  }
  for (const l of lamps) chartLamp(l);
  for (const w of walkers) chartSee(w.x, w.y, 40);
  for (const c of contacts()) {
    if (!s.heard[c.id] && Math.hypot(c.x - sub.x, c.y - sub.y) < 1000) { s.heard[c.id] = 1; G.mapNew = true; }
    if (s.seen[c.id]) continue;
    const near = (x, y) => c.box ? [Math.max(c.box[0], Math.min(c.box[2], x)), Math.max(c.box[1], Math.min(c.box[3], y))] : [c.x, c.y];
    if (lamps.some(l => lampSees(l, ...near(l[0], l[1]))) || walkers.some(w => Math.hypot(c.x - w.x, c.y - w.y) < 30 + c.r)) {
      s.seen[c.id] = s.heard[c.id] = 1; G.mapNew = true;
    }
  }
}
// A lamp's lit footprint on the chart: its glow, and squares along its beam as wide as the beam is there.
function chartLamp([x, y, mid, len, near, half]) {
  if (near) chartSee(x, y, near);
  for (let d = 10; d <= len; d += 10) chartSee(x + Math.cos(mid) * d, y + Math.sin(mid) * d, Math.max(3, d * Math.tan(half) * 0.8));
}
// Does the lamp light the point, with nothing solid between them? (The last 1.5 m is the thing itself.)
function lampSees([x, y, mid, len, near, half], px, py) {
  const d = Math.hypot(px - x, py - y);
  let a = Math.atan2(py - y, px - x) - mid;
  a = Math.atan2(Math.sin(a), Math.cos(a));
  if (!(d <= near || (d <= len && Math.abs(a) <= half))) return false;
  const k = d > 1.5 ? 1 - 1.5 / d : 0;
  return sightTo(x, y, x + (px - x) * k, y + (py - y) * k);
}

// ---------- geometry ----------
function pip(x, y, p) {
  let c = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const [xi, yi] = p[i], [xj, yj] = p[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
  }
  return c;
}
function segDist(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy;
  const t = l ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l)) : 0;
  return Math.hypot(px - ax - t * dx, py - ay - t * dy);
}
function inCave(x, y) { return caveD(x, y) < 0; }
function inBerg(x, y) { return x > 2078 && x < 2424 && y < 206 && pip(x, y, BERG.poly) && !inCave(x, y); }
function siteAt(x, y) {
  for (const s of SITES) {
    const i = Math.floor((x - s.x) / C), j = Math.floor((y - s.y) / C);
    if (i >= 0 && j >= 0 && i < s.w && j < s.h) return s;
  }
  return null;
}
function cellAt(s, x, y) { return s.cells[Math.floor((y - s.y) / C)][Math.floor((x - s.x) / C)] || ' '; }
// Is (x, y) rock, ice or wall? A big body (the submarine) cannot enter a site's rooms either.
function solid(x, y, big) {
  if (y > floorY(x)) return true;
  if (x < glacierX(y) || x > WORLD_W - 8) return true;
  if (y < SHELF_Y && x < SHELF_X) return true;
  if (iceOn && y < ICE_Y && underIce(x)) return true;
  if (inBerg(x, y)) return true;
  if (x > 4040) for (const [vx, h] of VENTS) if (Math.abs(x - vx) < 1.6 + (y - floorY(vx) + h) * 0.08 && y > floorY(vx) - h) return true;
  const s = siteAt(x, y);
  if (!s) return false;
  const ch = cellAt(s, x, y);
  return ch === '#' || (big && ch !== ' ');
}
// Does SISU at (x, y) touch only the sea ice (v6)? Then it stops softly, without a bump; anything else still bumps.
let iceOn = true;
function onlyIce(x, y) { iceOn = false; const hit = subHits(x, y); iceOn = true; return !hit; }
function subHits(x, y) {
  for (let a = 0; a < 12; a++) {
    const t = a / 12 * Math.PI * 2;
    if (solid(x + Math.cos(t) * 13.6, y + Math.sin(t) * 2.4, true)) return true;
  }
  return solid(x, y - 5, true);
}
function diverHits(x, y) {
  for (let a = 0; a < 8; a++) {
    const t = a / 8 * Math.PI * 2;
    if (solid(x + Math.cos(t) * 0.5, y + Math.sin(t) * 0.5)) return true;
  }
  return false;
}
function airlock() { return { x: sub.x + sub.dir * 11, y: sub.y + 1.2 }; }

// ---------- items, contacts, goals ----------
function allItems() { return ITEMS.concat(ICE_ITEMS, G.s ? G.s.finds.map(f => ({ ...f, site: 'find' })) : []); }
function itemHere(it) { return !G.s.got[it.id] && !G.held[it.id] && !G.carry.includes(it.id); }
// A find by its id; a harpooned fish (v8) is 'kala:<day>:<school>:<fish>' and lies nowhere.
function itemById(id) { return String(id).startsWith('kala:') ? { id, k: 'kala' } : allItems().find(i => i.id === id); }
function contacts() {
  // v9: `r` is how big it is, for seeing it up close; `spot` is where the autopilot takes SISU for it.
  const list = SITES.map(s => ({ id: s.id, kind: s.kind, name: s.name, x: s.x + s.w * C / 2, y: s.y + s.h * C / 2,
    r: Math.max(s.w, s.h) * C / 2, box: [s.x, s.y, s.x + s.w * C, s.y + s.h * C], spot: s.spot }));
  for (const b of [BERG_SITE, BERG_EAST]) list.push({ id: b.id, kind: b.kind, name: b.name, x: b.x, y: b.y, r: 6, spot: b.spot });
  HOLES.forEach((h, n) => list.push({ id: 'railo' + n, kind: 'RAILO JÄÄSSÄ', name: 'Railo', x: holeMid(n), y: ICE_Y, r: 17,
    spot: [holeMid(n), SURF] }));
  for (const f of G.s.finds) list.push({ id: f.id, kind: 'PIENI KAIKU', name: 'Pieni löytö', x: f.x, y: f.y, r: 1,
    spot: [f.x, Math.round(floorY(f.x)) - 6] });
  return list;
}
function goalNow() {
  const s = G.s, f = s.flags;
  if (!f.pinged) return { text: 'Paina 📡 – kaiku paljastaa pohjan ja kohteet.', target: null };
  if (!f.kontti) return { text: 'Ruoka on vähissä. Aja kontin luo ja pysähdy. Sisällä puku päälle ja ulos ilmalukosta.', target: 'kontti' };
  if (!f.asema) return { text: 'Sonar kuuli metallia lahden pohjukassa. Tutki se.', target: 'asema' };
  // v6: while the parts are short, the station on the ice has some: its opening is where the sonar points.
  if (s.up.hull < 2) return s.inv.osat >= COST.hull[2] ? { text: 'Vahvista runko: 🏠 sisälle, alakerran työpajaan.', target: null }
    : { text: `Hylkykenttä on yli ${RATING[1]} metrissä. Kerää ⚙️ ${s.inv.osat}/${COST.hull[2]} ja vahvista runko.`
      + (f.pinta ? '' : G.mode !== 'ice' ? ' Aseman yläosa on jäällä: nouse railosta pintaan.'
        : inStation(walker.x) ? ' Vie aseman varaston osat SISUun.' : ' Asema A-3 on vasemmalla, jäätikön reunalla.'),
      target: f.pinta ? null : 'railo0' };
  if (!f.nordvik) return { text: 'Tutki hylkykenttä idässä. Pysy rungon syvyysrajan yläpuolella.', target: f.polaris ? 'nordvik' : 'polaris' };
  if (!s.inv.antenni) return { text: 'Etsi Nordlysin huoltovarasto K-7 jäävuoresta: itäkyljen railo vie sen luo.', target: 'itarailo' };
  if (!s.inv.vahvistin) return { text: 'Hae radion vahvistin tutkimusasemalta.', target: 'asema' };
  if (!f.end) return { text: 'Korjaa radio: 🏠 sisälle, yläkerran ohjaamoon.', target: null };
  // Chapter 2: down the continental slope, one hull level for each step.
  const hull = (lvl, where) => ({ target: null, text: s.inv.osat >= COST.hull[lvl] ? 'Vahvista runko: 🏠 sisälle, alakerran työpajaan.'
    : `${where} Kerää ⚙️ ${s.inv.osat}/${COST.hull[lvl]} ja vahvista runko ${RATING[lvl]} metriin.` });
  if (s.up.hull < 3) return hull(3, 'Mannerrinne alkaa jäävuorten takaa yli 260 metrissä.');
  if (!f.saga) return { text: 'Aja itään jäävuorten ohi. Tutki kaapelilaiva Saga rinteen reunalla – letkupuvulla.', target: 'saga' };
  if (s.up.hull < 4) return hull(4, 'Pohjalaskeutuja on yli 380 metrissä.');
  if (!f.laskeutuja) return { text: 'Laskeudu rinnettä alas Nordlysin pohjalaskeutujalle.', target: 'laskeutuja' };
  if (s.up.hull < 5) return hull(5, 'Nordlys on 900 metrissä.');
  if (!f.kartta) return { text: f.silta ? 'Nordlys on tyhjä. Etsi karttahuoneesta, minne miehistö lähti.'
    : 'Etsi tutkimusalus Nordlys rinteen juurelta, noin 900 metristä.', target: 'nordlys' };
  if (s.up.hull < 6) return hull(6, 'Lähteet ovat 1300 metrissä.');
  if (!s.inv.kortti && !f.end2) return { text: 'Seuraa naputusta syvään mereen: Lyran majakka lähteiden luona.', target: 'majakka' };
  if (!f.end2) return { text: 'Soita majakan muistikortti: 🏠 sisälle, ohjaamon radioon.', target: null };
  return { text: 'Luku 2 on päättynyt. Lyra kuuluu yhä radiosta, jostain syvältä.', target: null };
}
