'use strict';
// The world (v9 split it out of index.html, #161): the sea floor, the ice, the places to dive, the iceberg's caves,
// the finds, the crates, the logs, SISU's rooms, the game's state and its save, the chart's maps, the geometry and the goals.
const KEY = 'ai-pelit:last-signal:';
// v12 (#300): the world is 3.34 times as wide east of the bay, so v11's save would not fit an older version: v12 keeps
// its game under its own key and reads v11's (`peli`) only the first time, leaving it as it was (docs/making-games.md).
const SAVE12 = KEY + 'peli12';
// v13 (#300): the wrecks' rooms and crates moved, and a new crate (the pump) that v12 cannot draw: its own key again,
// reading v12's (then v11's) the first time.
const SAVE13 = KEY + 'peli13';
// v13 (#300): a site's grid cell is 1.5 m (2 m before): a room is one row, 2.7 m clear, as tall as SISU's.
const C = 1.5;
// v12 (#300): the bay up to 650 m stays as it was; east of it every place is WX() of where it was. The iceberg keeps its
// shape and moves east by BX, with the opening beside it.
const WX = x => x <= 650 ? x : Math.round(650 + (x - 650) * 3.34);
const BX = 3744;
const WORLD_W = WX(4500);
const SHELF_X = 240, SHELF_Y = 5;  // the ice shelf at the head of the bay
// v12 (#300): the hull is no longer reinforced; it takes any depth. Knowing where to go is what opens the deep.
const TANK = [0, 60, 90, 120, 150];  // tank level → seconds of air
// v7 (#145): two suits. The tank gear goes no deeper than TANK_MAX. The hose suit is joined to SISU by a hose that
// brings air, heat, power and the radio; its level gives its length (m). v12 (#300): the hose no longer wears on
// corners, so there are no hose guides and no emergency air.
const TANK_MAX = 260;
const HOSE = [0, 80, 120, 180, 260];
const LAMP = [0, 1, 1.45, 1.9];
const COST = { tank: [0, 0, 2, 3, 4], hose: [0, 0, 2, 3, 4], lamp: [0, 0, 2, 4] };
const DIVER_SPEED = 4.4, SUB_SPEED = 16;
const WALK = 4.2, CLIMB = 2.6;      // the person inside SISU (v3), in m/s
// v12 (#300): the sonar hears 300 m round SISU and a ping names what is within 150 m (v11: 1000 m and 450 m).
const HEAR = 300, PING = 150;
const BAG = 8;                      // the small finds a person carries at once (v12)

// The ice (v6, #143): the sea is frozen over from the ice shelf to the far end, the top of the ice at ICE_TOP and its
// underside at ICE_Y. SISU comes up only in the openings (HOLES, [x0, x1]); at SURF its tower and back are out of the
// water. The first opening is in front of the station on the ice shelf. The iceberg stands in the ice on its own.
// v12 (#300): the nomads camp by the second opening, and the fifth (new, east of the iceberg) is by the weather station.
const ICE_TOP = -0.8, ICE_Y = 3, SURF = 1.2;
// v13 (#300): the first opening is the moon pool under the research station Aurora.
const HOLES = [[256, 290], [WX(932), WX(932) + 34], [1994 + BX, 2028 + BX], [WX(3004), WX(3004) + 34], [6230, 6264]];
const BERG_X = [2084 + BX, 2420 + BX];
function holeAt(x) { return HOLES.findIndex(([a, b]) => x > a && x < b); }
function holeMid(n) { return (HOLES[n][0] + HOLES[n][1]) / 2; }
function underIce(x) { return x >= SHELF_X && holeAt(x) < 0 && !(x > BERG_X[0] && x < BERG_X[1]) && !smallBerg(x); }
// v13 (#300): icebergs of other sizes frozen into the sea ice, solid all through (no caves): [middle, width, depth
// under the water, height above it]. Their outlines are rough, always the same.
const BERGS = [[900, 34, 24, 9], [3800, 96, 72, 28], [7520, 150, 112, 44], [10300, 74, 64, 24], [12010, 52, 44, 18]].map(([m, w, d, h], n) => {
  const x0 = m - w / 2, poly = [], top = [];
  for (let k = 0; k <= 12; k++) {
    const t = k / 12, x = x0 + w * t, r = 0.75 + 0.25 * Math.sin(n * 7 + k * 2.3);
    poly.push([x, -1 + (Math.sin(Math.PI * t) ** 0.6) * d * r]);
    top.push([x, -(Math.sin(Math.PI * t) ** 0.8) * h * (0.7 + 0.3 * Math.cos(n * 3 + k * 1.7))]);
  }
  return { x0, x1: x0 + w, d, poly, top };
});
function smallBerg(x) { return BERGS.find(b => x > b.x0 && x < b.x1) || null; }
// The underside of the sea ice is not flat (v13): keels of ice hang down up to 4.5 m here and there, never near an
// opening, so SISU still comes up straight.
function keel(x) {
  const k = 0.5 + 0.5 * Math.sin(x * 0.021) * Math.sin(x * 0.0067 + 1);
  if (k < 0.72 || HOLES.some(([a, b]) => x > a - 45 && x < b + 45)) return 0;
  return (k - 0.72) / 0.28 * 4.5;
}
// The ice's cold: outside, the warmth meter runs down in WARM seconds (v6). STATION is only the shelf's height now.
const STATION = { floor: -2.5 };
const WARM = 60, WARMUP = 35;
// v12 (#300): the abandoned weather station east of the iceberg, by the fifth opening: two floors joined by a ladder,
// its door on the west side. `floors` are where the feet stand on each; `fl` in a room is its floor.
const SAA = { id: 'saa', name: 'Sääasema', x0: 6278, x1: 6318, floors: [-1.1, -4.6], roof: -8.1, ladders: [[0, 6290]], ladder: 6290, door: 'x0',
  rooms: [
    { id: 'aeteinen', name: 'Eteinen', x0: 6278, x1: 6286, fl: 0 },
    { id: 'avarasto', name: 'Varasto', x0: 6286, x1: 6302, fl: 0 },
    { id: 'akone', name: 'Generaattori', x0: 6302, x1: 6318, fl: 0 },
    { id: 'aradio', name: 'Sääkoppi', x0: 6278, x1: 6296, fl: 1 },
    { id: 'amakuu', name: 'Makuuhuone', x0: 6296, x1: 6318, fl: 1 }] };
// v12: the buildings on the ice: `door` is the wall with the door ('none': no door); the others are walked into only from
// inside.
// v13 (#300): the station on the ice is the research station Aurora (A-3 was its code; Eero, on #300). It stands over
// the first opening as over a moon pool: SISU comes up in the pool under it and the tower's hatch opens into the
// station. Three floors joined by ladders (`ladders`: [the floor below, x]); no door to the outside. A few of its crew
// stayed and live there (`CREW13`); v12's one-floor building on the shelf is gone.
const AUR = { id: 'aurora', name: 'Aurora', x0: 247, x1: 299, floors: [-1.1, -6, -9.5], roof: -13, door: 'none', pool: 0,
  ladders: [[0, 295.5], [1, 250]],
  rooms: [
    { id: 'atelakka', name: 'Telakka', x0: 247, x1: 292, fl: 0 },
    { id: 'svarasto', name: 'Varasto', x0: 292, x1: 299, fl: 0 },
    { id: 'aviljely', name: 'Vesiviljely', x0: 247, x1: 276, fl: 1 },
    { id: 'amessi', name: 'Messi', x0: 276, x1: 299, fl: 1 },
    { id: 'sradio', name: 'Radiohuone', x0: 247, x1: 264, fl: 2 },
    { id: 'slabra', name: 'Laboratorio', x0: 264, x1: 280, fl: 2 },
    { id: 'smakuu', name: 'Asuintilat', x0: 280, x1: 299, fl: 2 }] };
const CREW13 = [{ name: 'Ingrid', x: 268, fl: 1, lead: true, col: '#8a3a3a' }, { name: 'Jon', x: 290, fl: 1, col: '#3a5a8a' },
  { name: 'Mari', x: 255, fl: 2, col: '#5a7a3a' }];
const BLDS = [AUR, SAA];
function bldAt(x) { return BLDS.find(b => x > b.x0 && x < b.x1) || null; }
function inStation(x) { return !!bldAt(x); }
function stationRoom(x, fl = 0) { const b = bldAt(x); return b ? b.rooms.find(r => x >= r.x0 && x < r.x1 && r.fl === fl) || null : null; }
// v12 (#300): the nomads' camp on the ice by the second opening: tents, a fire that warms, and their elder to trade with.
const CAMP = { x0: HOLES[1][1] + 22, x1: HOLES[1][1] + 112, fire: HOLES[1][1] + 62, elder: HOLES[1][1] + 63.8 };
function nearFire(x) { return Math.abs(x - CAMP.fire) < 9; }

// The sea floor, left to right: glacier bay, a ridge, the wreck field, a deep trench, the iceberg field, and
// in v2 the continental slope down in ledges, the Nordlys ledge at ~900 m and the deep sea beyond 1300 m.
const FLOOR = [[0, 105], [60, 112], [140, 118], [230, 122], [330, 126], [450, 132], [560, 136], [640, 136], [720, 130],
  [800, 138], [860, 104], [905, 110], [960, 180], [1040, 238], [1090, 246], [1180, 246], [1260, 242], [1340, 248],
  [1400, 248], [1470, 252], [1580, 252], [1660, 240], [1730, 300], [1765, 362], [1815, 362], [1850, 310], [1920, 250],
  [2000, 230], [2080, 270], [2200, 300], [2350, 290], [2480, 300], [2560, 330], [2700, 345], [2760, 400], [2830, 440],
  [2900, 445], [2950, 500], [3020, 580], [3120, 590], [3180, 650], [3260, 760], [3330, 860], [3400, 902], [3560, 906],
  [3640, 900], [3700, 960], [3780, 1090], [3850, 1210], [3920, 1320], [4000, 1345], [4160, 1350], [4260, 1330],
  [4380, 1352], [4460, 1300], [4500, 1250]].map(([x, y]) => [WX(x), y]);
// v12 (#300): stretched wide the floor would be flat as a table, so each long stretch gets a few gentle rises and dips
// (always the same ones), the sea floor round the sites included.
for (let i = FLOOR.length - 1; i > 0; i--) {
  const [x0, y0] = FLOOR[i - 1], [x1, y1] = FLOOR[i], n = Math.floor((x1 - x0) / 70);
  for (let k = n - 1; k >= 1; k--) {
    // v13 (#300): wider swings, and now and then a rocky ridge
    const x = x0 + (x1 - x0) * k / n, ridge = Math.max(0, Math.sin(x * 0.0029 + 0.7)) ** 12 * 26 * (0.5 + 0.5 * Math.sin(x * 0.07));
    const y = y0 + (y1 - y0) * k / n + Math.sin(x * 0.031) * 5 + Math.sin(x * 0.0113 + 1) * 7 + Math.sin(x * 0.0047 + 2) * 9 - ridge;
    FLOOR.splice(i, 0, [Math.round(x), Math.round(y)]);
  }
}
function floorY(x) {
  if (x <= FLOOR[0][0]) return FLOOR[0][1];
  let lo = 0, hi = FLOOR.length - 1;
  if (x >= FLOOR[hi][0]) return FLOOR[hi][1];
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (FLOOR[m][0] < x) lo = m; else hi = m; }
  const [x0, y0] = FLOOR[lo], [x1, y1] = FLOOR[hi];
  return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
}
function glacierX(y) { return 34 + Math.max(0, y) * 0.12; }

// Places the diver can swim into. '#' wall, '.' water inside, ' ' outside; letters are finds:
// r food, l medicine, o spare part, A radio amplifier, a air pocket, L the site's log; v12 (#300): u supplies.
// v12 (#300): crates, carried one at a time — F food, M medicine, P spare parts, U supplies, J junk, B any of them
// (the same for every phone) — and the furniture that shows inside: h bunk, t table, k cupboard, w wheel, e engine.
// The walls are thin plates (`WALL`) along the middle of the '#' cells, as in SISU, not 2 m blocks.
// v12: `x` is where the place was before the world grew (WX() moves it east); `at` keeps it where it is.
const SITES = [
  { id: 'asema', kind: 'METALLIRAKENNE', name: 'Auroran alamoduuli', shell: 'station', x: 150, y: 22, log: 'asema', sample: 'vesi',
    spot: [180, 46],  keep: {'L': 'asema:2,2', 'A': 'asema:17,5', 'S': 'asema:8,6'}, cells: [
      '#######################################',
      '#.L.h..k#..S..k.t..#..t.c..t.#.a..k.FB#',
      '###H##########H##########H#####H#######',
      'D..k.e..e...D...A..t...kD..P..B..J...U#',
      '#######################################'] },
  { id: 'kontti', kind: 'KONTTI', name: 'Kontti', shell: 'box', x: 596, floor: true, color: '#b5532c',
    spot: [575, 122], cells: [
      '########',
      '.F.B..o#',
      '.J.F..u#',
      '########'] },
  { id: 'polaris', kind: 'HYLKY', name: 'Polaris', shell: 'ship', x: 1104, floor: true, log: 'polaris',
    spot: [1180, 222],  keep: {'L': 'polaris:11,1'}, cells: [
      '           #######           ',
      '           #wL.k.#           ',
      '############..H############  ',
      '#.h.h..k#.g.t.c.t.#.k..h.h.# ',
      'D.......D....H....D......o.D ',
      '####H####################H## ',
      '#.e.e.P.#..B.F.J.B.U.J.M..B# ',
      '############################ '] },
  { id: 'kontit', kind: 'KONTTEJA', name: 'Konttipino', shell: 'box', x: 1362, floor: true, color: '#2f6f8f',
    spot: [1350, 228], cells: [
      '#######   ',
      '.B.J.o#   ',
      '#######   ',
      '  ########',
      '  .F.B.U.#',
      '  ########'] },
  { id: 'nordvik', kind: 'HYLKY', name: 'Nordvik', shell: 'ship', x: 1490, floor: true, log: 'nordvik',
    spot: [1478, 232],  keep: {'L': 'nordvik:20,4'}, cells: [
      '  ######                        ',
      '  #w.k.#                        ',
      '###.H.##########################',
      '#.h.h.k.#.g.t.c.t.#..L.k..t..k.#',
      'D...........H.....D....H......D#',
      '######H#####################H###',
      '#.e.e..P#.B.F.J.B.M.#.J.B.U.J.F#',
      '#.......D...........D..........#',
      '################################'] },
  { id: 'syva', kind: 'KONTTI', name: 'Avustuskontti', shell: 'box', x: 1780, floor: true, color: '#c9b23a', log: 'avustus',
    spot: [1770, 345],  keep: {'L': 'syva:2,2'}, cells: [
      '########',
      '.L.M.B.#',
      '.M.u.M.#',
      '########'] },
  // Chapter 2 (v2): the cable ship on the slope's edge, the Nordlys lander and containers on the ledges, the
  // research vessel Nordlys at the foot of the slope, and the Lyra beacon on the deep plain. A digit is a log,
  // named in the site's `logs`; T, V and K are the Nordlys diving tank, Lyra's lamp and the beacon's memory card.
  { id: 'saga', kind: 'HYLKY', name: 'Kaapelilaiva Saga', shell: 'ship', x: 2588, floor: true, log: 'saga',
    spot: [2570, 300],  keep: {'L': 'saga:4,1'}, cells: [
      '   #####                  ',
      '   #wL.#                  ',
      '####.H.###################',
      '#.h.h.#.g.t.c.#..k...o...#',
      'D............D...........D',
      '#####H####################',
      '#.e.e.P.#.B.U.J.#.B.J.F..#',
      '#.......D.......D........#',
      '##########################'] },
  { id: 'laskeutuja', kind: 'METALLIRAKENNE', name: 'Nordlysin pohjalaskeutuja', shell: 'station', x: 2842, floor: true,
    log: 'laskeutuja', spot: [2812, 414],  keep: {'L': 'laskeutuja:4,1'}, cells: [
      '  ######  ',
      '  #.L.k#  ',
      '###.H.####',
      '#.e..P..o#',
      '..a..B..##',
      '##########'] },
  { id: 'rinne', kind: 'KONTTEJA', name: 'Rinteen kontit', shell: 'box', x: 3052, floor: true, color: '#7a3f8f',
    spot: [3034, 566], cells: [
      '#######   ',
      '.P.B.o#   ',
      '#######   ',
      '  ########',
      '  .M.B.u.#',
      '  ########'] },
  { id: 'nordlys', kind: 'SUURI HYLKY', name: 'Tutkimusalus Nordlys', shell: 'rv', x: 3420, floor: true, deck: 2, sample: 'pullo',
    logs: { 1: 'silta', 2: 'labra', 3: 'kartta', 4: 'halli' }, spot: [3452, 879],
    rooms: [[38.5, 1, 'Karttahuone'], [46.5, 1, 'Komentosilta'], [4.5, 4, 'Työpaja'], [13.5, 4, 'Laboratorio'],
      [24.5, 4, 'Messi'], [36.5, 4, 'Sukellusvarusteet'], [49, 4, 'Keulavarasto'], [8.5, 7, 'Tutkimussukellusveneen halli'],
      [25.5, 7, 'Lastiruuma'], [42.5, 7, 'Konehuone']],  keep: {'3': 'nordlys:37,2', '1': 'nordlys:46,2', '2': 'nordlys:14,6', 'T': 'nordlys:37,6', 'S': 'nordlys:12,7', '4': 'nordlys:8,10', 'V': 'nordlys:13,11'}, cells: [
      '                                  ##################          ',
      '                                  #.k.3.t.D.w..1.k.D          ',
      '                                  #######H##########          ',
      '############D###############################D#################',
      '#.k.o.t.#.k.2.t.S.#.g.t.c.t.k.#.k..T..h.h.#.k.P.k.B.U.###     ',
      '#.......D.........D...........D...........D...........D##     ',
      '######H#########################H#############H#######        ',
      'D....4.......V..#.B.F.J.B.U.J.B.M.#..e..e..e..P..o..##        ',
      'D...............D.................D..............a.##         ',
      '##################################################            '] },
  { id: 'majakka', kind: 'HEIKKO SIGNAALI', name: 'Lyran majakka', shell: 'beacon', x: 4172, floor: true, sample: 'suomu',
    logs: { 4: 'majakka' }, spot: [4150, 1320],  keep: {'K': 'majakka:2,2', '4': 'majakka:4,2', 'S': 'majakka:5,3'}, cells: [
      '  #####  ',
      '###...###',
      '..K.4.P.#',
      '#..a.S..#',
      '#########'] },
  // v12 (#300): two more wrecks in the wider sea, full of crates; the nomads know where they lie.
  { id: 'aurora', kind: 'HYLKY', name: 'Kalastusalus Saukko', shell: 'ship', at: 2700, floor: true, log: 'aurora',
    spot: [2690, 220],  keep: {'L': 'aurora:11,1'}, cells: [
      '        #####        ',
      '        #wL.#        ',
      '#########.H.#########',
      '#.h.h.k.#.g.c.t#..F.#',
      'D.......D......D..B.D',
      '####H#########H######',
      '#.e.e.o.#.F.B.J.F.B.#',
      '#####################'] },
  { id: 'kestrel', kind: 'HYLKY', name: 'Rahtilaiva Kestrel', shell: 'ship', at: 4960, floor: true, log: 'kestrel',
    spot: [4950, 222],  keep: {'L': 'kestrel:30,2'}, cells: [
      '                            #######  ',
      '                            #wL.k.#  ',
      '                            ###H###  ',
      '                            #h.h.k#  ',
      '############################.g.t.##  ',
      '#.B.J.B.J.U.#.F.J.B.M.J.B.#..H...##  ',
      '#...........D.............D......#   ',
      '#.J.B.J.F.J.#.B.J.X.J.B.J.#.e.e.o#   ',
      '#...........D.............D...a..#   ',
      '##################################   '] },
];
// v12: the sites move east with the world (or stay where `at` puts them), their parking spot with them.
for (const s of SITES) {
  if (s.at != null) { s.x = s.at; continue; }
  const nx = WX(s.x);
  s.spot = [s.spot[0] + nx - s.x, s.spot[1]];
  s.x = nx;
}

// The iceberg: an outline that is solid ice, hollowed by caves (segments with a radius). v12 (#300): the caves are
// natural — big chambers joined by narrow winding passages, one after another (v9's maze is gone): the way in on the
// west, a first chamber, the great hall with a shaft up to daylight, a lower cave with a crack down into the deep, and
// east of the hall more chambers, the farthest a dead end. The cache K-7 lies apart in the east, through the east crack
// (v7). The berg keeps its v11 shape and stands BX further east. `B()` moves a v11 point there.
const B = (x, y) => [x + BX, y];
const BERG = {
  poly: [[2088, -1], [2082, 30], [2090, 75], [2110, 130], [2150, 178], [2215, 203], [2295, 200], [2360, 172], [2400, 120],
    [2418, 60], [2420, -1]].map(p => B(...p)),
  top: [[2084, 0], [2096, -14], [2110, -18], [2124, -34], [2140, -36], [2158, -52], [2178, -48], [2196, -60], [2214, -54],
    [2236, -40], [2262, -44], [2286, -30], [2318, -38], [2336, -70], [2350, -66], [2366, -40], [2392, -26], [2412, -10], [2422, 0]].map(p => B(...p)),
  caves: [],
};
// The chambers and the passages between them, [x1, y1, x2, y2, radius] in v11's place (a chamber is a short wide one).
const HALL = { x: 2169 + BX, y: 49, r: 10 };
const CAVES = [
  [2058, 50, 2080, 49, 1.8], [2080, 49, 2102, 46, 1.5],                                // the way in
  [2102, 46, 2112, 50, 6.5],                                                            // the first chamber
  [2104, 50, 2100, 64, 1.4], [2100, 64, 2105, 74.5, 1.3], [2104, 74, 2106, 75, 4],        // down to a side chamber
  [2112, 50, 2126, 57, 1.4], [2126, 57, 2136, 54, 1.3], [2136, 54, 2160, 48, 1.5],        // the passage to the hall
  [2160, 48, 2178, 50, 10],                                                             // the great hall
  [2166, 45, 2164, 25, 1.6], [2164, 25, 2161, 12, 1.5], [2157, 9, 2165, 9, 2.4],         // the shaft up to the moulin's air
  [2176, 50, 2187, 68, 1.5], [2187, 68, 2177, 91, 1.4],                                // down from the hall
  [2170, 92, 2184, 90, 6.5],                                                            // the lower cave
  [2170, 92, 2158, 106, 1.3], [2158, 106, 2155, 121, 1.0],                              // the deep crack
  [2178, 50, 2200, 41, 1.5], [2200, 41, 2226, 48, 1.3],                                // east from the hall
  [2226, 48, 2234, 50, 7],                                                              // the east chamber
  [2234, 50, 2252, 66, 1.3], [2252, 66, 2270, 82, 1.4], [2270, 82, 2280, 84, 5.5],      // down to the far chamber
  [2230, 46, 2250, 34, 1.4], [2250, 34, 2268, 27, 1.3], [2268, 27, 2272, 27, 4],        // up to a small chamber
  [2184, 90, 2215, 95, 1.3], [2215, 95, 2240, 90, 1.4], [2240, 90, 2270, 82, 1.3],      // the low way round
  // v7 (#145): the cache K-7, and a crack in the east side, so a short hose reaches it from outside
  [2335, 99, 2368, 102, 5], [2366, 103, 2420, 105, 1.8]];
for (const [ax, ay, bx, by, r] of CAVES) BERG.caves.push([ax + BX, ay, bx + BX, by, r]);
const BERG_SITE = { id: 'jaavuori', kind: 'AUKKO JÄÄSSÄ', name: 'Jäävuoren luolasto', x: 2072 + BX, y: 52, spot: B(2050, 52) };
const BERG_EAST = { id: 'itarailo', kind: 'RAILO JÄÄSSÄ', name: 'Jäävuoren itärailo', x: 2416 + BX, y: 105, spot: B(2424, 105) };
// The moulin's daylight and the deep crack's glow (v9), where they are now.
const MOULIN = B(2161, 9), CRACK = B(2155, 121);
// v9: the caves as a grid of distances to their walls, 0.5 m apart and negative in the water, so the caves cost nothing
// to test; and the outline of the walls, cut into the 2 m squares (RV) that a lamp maps. v12: the walls are rough
// (`rough()`), wider swings in a big chamber than in a narrow passage, always the same.
const CF = { x0: 2040 + BX, y0: -4, s: 0.5, w: 800, h: 432 };
const CFD = new Float32Array(CF.w * CF.h).fill(9);
function rough(x, y) { return 0.55 * Math.sin(x * 0.61 + y * 0.23) + 0.45 * Math.sin(x * 0.19 - y * 0.73 + 1.3); }
for (const [ax, ay, bx, by, r] of BERG.caves) {
  const i0 = Math.max(0, Math.floor((Math.min(ax, bx) - r * 1.2 - 2 - CF.x0) / CF.s)), i1 = Math.min(CF.w - 1, Math.ceil((Math.max(ax, bx) + r * 1.2 + 2 - CF.x0) / CF.s));
  const j0 = Math.max(0, Math.floor((Math.min(ay, by) - r * 1.2 - 2 - CF.y0) / CF.s)), j1 = Math.min(CF.h - 1, Math.ceil((Math.max(ay, by) + r * 1.2 + 2 - CF.y0) / CF.s));
  for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
    const x = CF.x0 + i * CF.s, y = CF.y0 + j * CF.s, k = i + j * CF.w, v = segDist(x, y, ax, ay, bx, by) - r * (1 + 0.16 * rough(x, y));
    if (v < CFD[k]) CFD[k] = v;
  }
}
function caveD(x, y) {
  const fx = (x - CF.x0) / CF.s, fy = (y - CF.y0) / CF.s, i = Math.floor(fx), j = Math.floor(fy);
  if (!(i >= 0 && j >= 0 && i < CF.w - 1 && j < CF.h - 1)) return 9;
  const u = fx - i, v = fy - j, k = i + j * CF.w;
  return (CFD[k] * (1 - u) + CFD[k + 1] * u) * (1 - v) + (CFD[k + CF.w] * (1 - u) + CFD[k + CF.w + 1] * u) * v;
}
const RV = { x0: 2040 + BX, y0: -4, s: 2, w: 200, h: 108 };
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
const INV = { osa: 'osat' };  // the stores' name for a kind, where it differs
const KINDS = { r: 'ruoka', l: 'laake', o: 'osa', A: 'vahvistin', N: 'antenni', a: 'ilma', L: 'loki', T: 'saili', V: 'valo',
  K: 'kortti', S: 'nayte', u: 'tarvike' };
const ICON = { ruoka: '🥫', laake: '💊', osa: '⚙️', vahvistin: '📟', antenni: '📡', loki: '📓', saili: '➰', valo: '🔦', kortti: '💾',
  nayte: '🧪', kala: '🐟', tarvike: '🧥', pumppu: '🚰' };
const NAME = { ruoka: 'Ruoka-annos', laake: 'Lääkkeet', osa: 'Varaosa', vahvistin: 'Radion vahvistin', antenni: 'Radioantenni',
  saili: 'Nordlysin letkukela', valo: 'Lyran valonheitin', kortti: 'Majakan muistikortti', nayte: 'Näyte', kala: 'Kala',
  tarvike: 'Tarvikkeita' };
// v12 (#300): the crates' contents. A crate of food, medicine or spare parts counts in SISU's stores once on the shelf;
// supplies (warm clothes, blankets, lamp oil) are what the nomads trade for; junk is worth nothing to anyone.
// v13: X is Aurora's new water pump, carried like a crate.
const CRATE_K = { F: 'ruoka', M: 'laake', P: 'osa', U: 'tarvike', J: 'romu', X: 'pumppu' };
const CRATE = { ruoka: { label: 'RUOKA', col: '#d9772e' }, laake: { label: 'LÄÄKKEET', col: '#e8e8e8' },
  osa: { label: 'VARAOSIA', col: '#8fa3ab' }, tarvike: { label: 'TARVIKKEITA', col: '#7aa05a' }, romu: { label: 'ROMUA', col: '#6d6256' },
  pumppu: { label: 'VESIPUMPPU', col: '#3a7ab8' } };
const JUNK = ['KIRJOJA', 'ASTIOITA', 'KIVIÄ', 'TYHJÄ', 'SÄHKÖJOHTOA', 'PAPEREITA'];
// The same "random" for every phone: a number in [0, 1) from a crate's name.
function hash(str) { let h = 2166136261; for (const ch of str) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return (h >>> 0) / 4294967296; }
const BOX_W = 0.9, BOX_H = 0.7;
// v13: how many crates of each kind lay in each wreck in v12's world (its `CRATES0`), for moving a v12 save in.
const V12_SEA = {"asema":{"osa":2,"ruoka":2,"romu":1},"kontti":{"ruoka":2},"polaris":{"romu":5,"tarvike":4,"laake":2,"ruoka":1,"osa":2},
  "kontit":{"romu":2,"ruoka":1},"nordvik":{"romu":4,"tarvike":2,"laake":3,"ruoka":1,"osa":1},"syva":{"laake":3},
  "saga":{"osa":3,"ruoka":4,"romu":3,"tarvike":2},"laskeutuja":{"osa":1,"ruoka":1},"rinne":{"osa":1,"tarvike":1,"laake":2},
  "nordlys":{"osa":6,"ruoka":5,"laake":4,"romu":5,"tarvike":1},"majakka":{"osa":1},"aurora":{"osa":3,"ruoka":4,"romu":4,"tarvike":1},
  "kestrel":{"romu":13,"laake":3,"osa":4,"tarvike":2,"ruoka":3}};
// Every crate as the world first has it: [id, contents, how many, where, x, y] (`fresh()` copies it into the save).
const CRATES0 = [];
function crate0(id, ch, w, x, y) {
  const r = hash(id), k = CRATE_K[ch] || (r < 0.3 ? 'romu' : r < 0.55 ? 'ruoka' : r < 0.7 ? 'osa' : r < 0.85 ? 'tarvike' : 'laake');
  const n = k === 'romu' || k === 'pumppu' ? 0 : 2 + Math.floor(hash(id + 'n') * (k === 'ruoka' ? 3 : 2));
  CRATES0.push({ id, k, n, w, x, y, junk: k === 'romu' ? JUNK[Math.floor(hash(id + 'j') * JUNK.length)] : undefined });
}
const ITEMS = [];
for (const s of SITES) {
  s.h = s.cells.length;
  s.w = Math.max(...s.cells.map(r => r.length));
  if (s.floor) s.y = Math.min(...[0, 0.5, 1].map(f => floorY(s.x + f * s.w * C))) - s.h * C + 0.6;
  // SISU parks clear of the floor beside the site (v12: the stretched floor lies a little differently than in v11)
  if (s.floor) s.spot[1] = Math.min(s.spot[1], ...[-14, 0, 14].map(d => floorY(s.spot[0] + d) - 4));
  s.decor = [];
  s.cells.forEach((row, j) => [...row].forEach((ch, i) => {
    const log = ch === 'L' ? s.log : s.logs && s.logs[ch];
    // v13: the story's finds keep their v12 names (`keep`), so a save still knows which it has
    if (KINDS[ch] || log) ITEMS.push({ id: (s.keep && s.keep[ch]) || s.id + ':' + i + ',' + j, k: log ? 'loki' : KINDS[ch], x: s.x + i * C + C / 2,
      y: s.y + j * C + C / 2, site: s.id, log: log || null, sample: ch === 'S' ? s.sample : undefined });
    if (CRATE_K[ch] || ch === 'B') crate0(s.id + ':' + i + ',' + j, ch, 'sea', s.x + i * C + C / 2, s.y + j * C + C / 2 + 0.3);
    if ('htkwegcH'.includes(ch)) s.decor.push([ch, i, j]);
  }));
}
// v9: the cave's finds keep their numbers (a save remembers them by it); v12 puts them in the new chambers: air
// pockets in the far chamber, the hall, the lower cave, the moulin's air gap and the cache, the rest about the caves.
// v13 (#300): food and medicine are only in crates now, so the cave's tins and medicine became supplies and parts.
[['a', 2280, 81], ['a', 2172, 43], ['a', 2172, 93], ['a', 2161, 10], ['a', 2352, 97.5], ['u', 2284, 86],
  ['o', 2105, 76], ['u', 2271, 29],
  ['L', 2337, 100, 'k7'], ['N', 2366, 102], ['o', 2345, 104], ['o', 2356, 97], ['u', 2350, 101], ['o', 2361, 105],
  ['o', 2178, 95], ['L', 2155, 120, 'syvyys'], ['S', 2166, 55, 'jaa']].forEach(([ch, x, y, log], n) =>
  ITEMS.push(ch === 'S' ? { id: 'jaavuori:' + n, k: 'nayte', x: x + BX, y, site: 'jaavuori', log: null, sample: log }
    : { id: 'jaavuori:' + n, k: KINDS[ch], x: x + BX, y, site: 'jaavuori', log: log || null }));

// The station on the ice (v6): two notes, and the stores the crew left behind. v12: the weather station's (`site` 'saa').
const ICE_ITEMS = [
  { id: 'pinta:loki', k: 'loki', x: 258, y: -9.8, site: 'pinta', log: 'paivakirja' },
  { id: 'pinta:taulu', k: 'loki', x: 272, y: -9.8, site: 'pinta', log: 'taulu' },
  { id: 'pinta:u', k: 'tarvike', x: 286, y: -9.8, site: 'pinta' },
  { id: 'pinta:o1', k: 'osa', x: 297.5, y: -1.4, site: 'pinta' },
  { id: 'pinta:o2', k: 'osa', x: 297.5, y: -2.2, site: 'pinta' },
  { id: 'saa:loki', k: 'loki', x: 6284, y: -4.9, site: 'saa', log: 'saa' },
  { id: 'saa:u', k: 'tarvike', x: 6310, y: -4.9, site: 'saa' },
  { id: 'saa:o', k: 'osa', x: 6309, y: -1.4, site: 'saa' },
];
// v12: the crates on the ice, in Aurora's store (v13) and the weather station's, standing on their floors.
for (const [id, ch, x, y] of [['pinta:c1', 'P', 292.8, -1.1], ['pinta:c2', 'F', 293.8, -1.1], ['pinta:c3', 'U', 293.3, -1.8], ['pinta:c4', 'J', 278, -6],
  ['saa:c1', 'U', 6292, -1.1], ['saa:c2', 'F', 6295, -1.1], ['saa:c3', 'J', 6298, -1.1], ['saa:c4', 'M', 6298, -1.8], ['saa:c5', 'B', 6312, -1.1]])
  crate0(id, ch, 'ice', x, y);
// The lab (v8, #151): each sample, once studied in SISU's lab, tells a little of what happened and helps for good.
const SAMPLES = {
  vesi: { name: 'Merivesinäyte', where: 'aseman alamoduulista', paras: [
    { t: 'Vesi on puhdasta, eikä säteilymittari värähdäkään. Planktonia on enemmän kuin koskaan.', c: 'log' },
    { t: 'Virtausmittari näyttää, miten vesi kulkee lahdelta itään. Ajat nyt virran mukana.' }],
    gain: 'SISU kulkee 10 % nopeammin' },
  jaa: { name: 'Jääydin', where: 'jäävuoren suuresta salista', paras: [
    { t: 'Jään kerrokset ovat kuin vuosirenkaat. Ylimpien joukossa on ohut punainen juova: rautapölyä taivaalta, samana keväänä.', c: 'log' },
    { t: 'Nyt tiedät, miten valo taittuu jäässä. Suuntaat lampun niin, että se kantaa.' }],
    gain: 'lamppu kantaa jäävuoren luolissa kolmanneksen kauemmas' },
  pullo: { name: 'Nordlysin näytepullo', where: 'Nordlysin laboratoriosta', paras: [
    { t: 'Pullon etiketissä lukee »Päivä 0, pinta». Vedessä on rautaa ja varautuneita hiukkasia, jotka satoivat taivaalta samana päivänä kuin revontulet.', c: 'log' },
    { t: 'Pullon alla on Nordlysin kaikuluotaimen säätötaulukko. Säädät SISUn sonarin samoin.' }],
    gain: 'sonarin ping kuuluu 200 metriin' },
  bakteeri: { name: 'Lähteiden bakteerimatto', where: 'lämpimien lähteiden luota', paras: [
    { t: 'Bakteerit elävät lähteiden lämmöstä ja kemiasta, eivät auringosta – ja voivat hyvin. Täällä alhaalla mikään ei muuttunut.', c: 'log' },
    { t: 'Opit niiltä saman kuin Nordlysin tutkijat: kylmässä eletään säästeliäästi.' }],
    gain: 'nälkä kasvaa viidenneksen hitaammin' },
  suomu: { name: 'Valokalan suomu', where: 'Lyran majakalta', paras: [
    { t: 'Suomu hehkuu vielä mikroskoopin alla. Kalat ovat sokeita: ne seuraavat valoa ja tärinää.', c: 'log' },
    { t: 'Himmennät valot, kun ne lähestyvät. Ne eivät enää ryntää päin yhtä kovaa.' }],
    gain: 'valokalat tönivät puolet vähemmän' },
};
// v8: the bacterial mat by the hot vents, beside Lyra's beacon.
ITEMS.push({ id: 'lahteet:bakteeri', k: 'nayte', x: WX(4172) - 8, y: Math.round((floorY(WX(4172) - 8) - 0.9) * 10) / 10, site: 'majakka', log: null, sample: 'bakteeri' });
// A studied sample's help (v8): 1 while not studied.
function lab(key, k) { return G.s && G.s.lab && G.s.lab[key] ? k : 1; }
const LOGS = {
  asema: { title: 'Aseman päiväkirja', paras: [
    { t: '2.3. Revontulet eivät sammu, vaikka on päivä. Kompassit pyörivät ympyrää.', c: 'log' },
    { t: '4.3. Mantereelta ei vastata millään taajuudella. Satelliittipuhelin näyttää vain viivaa.', c: 'log' },
    { t: '6.3. Nordlys hakee meidät huomenna. Jätin radion varavahvistimen tutkimusmoduuliin – jos joku joskus tarvitsee sitä.', c: 'log' },
    { t: 'Joku muukin on siis ollut täällä. Minne he lähtivät?' }] },
  paivakirja: { title: 'Auroran radiopäiväkirja', paras: [
    { t: '»1.3. Aurinko ei noussut, vaikka kalenterin mukaan pitäisi. Revontulet loistavat keskipäivällä.»', c: 'log' },
    { t: '»5.3. Meri jäätyy umpeen. Vain railot pysyvät auki. Nordlys lupasi lähettää veneen alakautta, jään alta.»', c: 'log' },
    { t: '»7.3. Koiravaljakko kävi. Nomadit, poroja ja koiria. He leiriytyvät seuraavan railon luo itään ja vaihtavat tietoa tavarasta. He tietävät, missä laivat makaavat.»', c: 'log' },
    { t: 'Nordlys haki suurimman osan. Kolme jäi pitämään asemaa käynnissä – ja odottamaan apua. Apu tuli meren alta, niin kuin sinäkin.' },
    { t: 'Nomadien leiri on itäisen railon luona: se näkyy nyt merikartalla.', c: 'msg' }] },
  taulu: { title: 'Laboratorion valkotaulu', paras: [
    { t: 'Taululle on kirjoitettu isoin kirjaimin: »JÄÄ PAKSUNEE 4 CM / VRK. PINTA EI OLE TURVALLINEN. ALAS MODUULIIN.»', c: 'log' },
    { t: 'Alla pienemmällä: »Kaikki varaosat ja ruoka varastoon. Jos joku tulee perässä, ottakoon.»', c: 'log' },
    { t: 'Varasto on telakan päädyssä, alakerrassa.', c: 'msg' }] },
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
  // v12 (#300)
  saa: { title: 'Sääaseman päiväkirja', paras: [
    { t: '»Tuulimittari pyörii yhä, vaikka kukaan ei lue sitä. Paine laskee joka päivä vähän.»', c: 'log' },
    { t: '»Rahtilaiva Kestrel ajoi myrskyssä karille hylkykentän itäpuolella, trenssin reunalla. Lasti jäi ruumaan.»', c: 'log' },
    { t: 'Kestrelin alue näkyy nyt merikartalla.', c: 'msg' }] },
  aurora: { title: 'Saukon saalispäiväkirja', paras: [
    { t: '»Verkot tulivat tyhjinä kolme päivää. Neljäntenä taivas paloi vihreänä, ja kalat nousivat pintaan katsomaan.»', c: 'log' },
    { t: '»Lähdemme nomadien mukaan jäälle. Meri ei enää ruoki meitä.»', c: 'log' },
    { t: 'Saukko on täynnä tavaraa. Ota vain se, mitä tarvitset.' }] },
  kestrel: { title: 'Kestrelin lastiluettelo', paras: [
    { t: 'Luettelossa on satoja rivejä: kirjoja, astioita, kaapelia – ja muutama laatikko ruokaa ja lääkkeitä.', c: 'log' },
    { t: 'Kaikkea ei voi viedä. Etsi ne, joita tarvitset.', c: 'msg' }] },
};
// The deep sea (v2): glowing fish swim slow loops (x, y, reach across, reach up and down, speed) and bump into the
// diver or SISU; hot vents stand on the deep plain as solid chimneys.
const FISH = [[3300, 742, 22, 6, 0.3], [3600, 860, 28, 8, 0.25], [3810, 1075, 16, 8, 0.35], [4080, 1300, 36, 10, 0.22],
  [4300, 1288, 30, 10, 0.28], [4425, 1262, 18, 8, 0.32]].map(([x, ...r]) => [WX(x), ...r]);
const VENTS = [[4062, 12], [4112, 8], [4232, 14], [4318, 10]].map(([x, h]) => [WX(x), h]);
const VENT_X = VENTS[0][0] - 22;  // nothing of the vents west of this
function fishAt(n, t) {
  const [x, y, rx, ry, sp] = FISH[n];
  return { x: x + Math.sin(t * sp + n * 2) * rx, y: y + Math.sin(t * sp * 1.7 + n) * ry, dir: Math.cos(t * sp + n * 2) >= 0 ? 1 : -1 };
}
// Schools of small fish (v8, #151) in the shallow bay and the wreck field: (x, y, reach across, reach up and down,
// how many). They come back each night; a speared one is a fish carried home and cooked in the galley.
const SCHOOLS = [[372, 40, 22, 6, 7], [530, 78, 26, 8, 6], [760, 96, 20, 6, 7], [1230, 205, 22, 8, 7], [1640, 214, 18, 6, 6]].map(([x, ...r]) => [WX(x), ...r]);
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
// v13 (#300): SISU is drawn and moves 15 % bigger than these numbers say, so the person (who keeps their size) no longer
// hits the lower deck's ceiling with their head. Hull coordinates stay as they were; SS turns them into metres.
const SS = 1.15;
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
// `carry` is this phone's own share of it (v12: the bag, BAG at most). `asked`: finds this phone has asked the host
// for on this dive.
const G = { mode: 'menu', s: null, t: 0, hold: false, paused: false, sc: 4, cx: 380, cy: 30, ping: null, pingCd: 0,
  carry: [], held: {}, asked: {}, homeT: 0, toastT: 0, hitCd: 0, warnCd: 0, saveCd: 0, lastGoal: '', fishCd: 0,
  card: '', iceCd: 0, hoseSaid: false, harpCd: 0, spear: null, pending: {}, parviSaid: false, bagCd: 0 };
const sub = { x: 330, y: 30, vx: 0, vy: 0, dir: 1, face: 1, prop: 0 };
// `kit` (v7): the suit, 'tank' or 'hose'; `harp` (v12): the harpoon taken along from the suit room.
const diver = { x: 0, y: 0, vx: 0, vy: 0, dir: 1, air: 60, ang: 0, kit: 'tank', harp: false };
// This phone's hose-suit diver's hose (v7): the corners it bends round on its way from the airlock, and its length.
const hose = { pts: [], len: 0 };
// The person inside SISU: where they stand, whether the diving suit is on, and where a tap sent them (`to`).
const crew = { x: 0.6, y: UP, dir: 1, suit: false, kit: 'tank', harp: false, to: null, room: 'ohjaamo', said: '', walkT: 0, moving: false,
  climbing: false, mark: null };
// The person out on the ice (v6), in world metres (y down, the feet at y): `warm` runs down outside, `to` is a tap;
// v12: `fl` the floor they are on in a building, `toFl` the floor a tap sent them to.
const walker = { x: 0, y: 0, dir: 1, to: null, warm: 100, walkT: 0, moving: false, climbing: false, suit: false, room: '', fl: 0, toFl: 0 };
const input = { x: 0, y: 0 };
// Playing with friends (v5, #138): null when playing alone. See "playing with friends" below.
let net = null;
const snow = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), z: 0.4 + Math.random() * 0.8 }));
const bubbles = [];

// v12 (#300): `crates` every crate as it is now (see cargo.js), `areas` the places a hint points to, `trade` how many
// trades the nomads have made, `pack` what was taken from the stores into a bag and not yet brought back.
function fresh() {
  return { v: 1, w12: 1, w13: 1, day: 1, t: 0, sub: { x: 330, y: 30, dir: 1 }, m: { food: 70, health: 100, hull: 100 },
    inv: { ruoka: 2, laake: 1, osat: 0, vahvistin: 0, antenni: 0, kortti: 0, kala: 0, tarvike: 0 }, up: { tank: 1, hose: 1, lamp: 1 },
    got: {}, known: {}, flags: {}, finds: [{ id: 'f0', k: 'osa', x: 700, y: floorY(700) - 0.9 }], findN: 1,
    lab: {}, caught: {}, heard: {}, seen: {}, chart: '', cave: '', crates: CRATES0.map(c => ({ ...c })), areas: {}, trade: 0, pack: {} };
}
// Where a v11 place is in v12's wider world: the iceberg's surroundings move with it, the rest by WX().
function toW12(x) { return x > 2030 && x < 2460 ? x + BX : WX(x); }
function load() {
  try {
    // v12 (#300): its own save first; else v11's (or older), brought into the wider world below, its key left as it was.
    let s = JSON.parse(localStorage.getItem(SAVE13));
    if (!(s && s.v === 1)) s = JSON.parse(localStorage.getItem(SAVE12));
    if (!(s && s.v === 1)) s = JSON.parse(localStorage.getItem(KEY + 'peli'));
    // A v1 save loads as it is (AGENTS.md rule 5); the parts v2 added start empty, v7's hose at its first level,
    // v8's fish, lab and schools empty. v9's chart starts from what the save already knows (`seedMaps`).
    if (s && s.v === 1) { const f = fresh(), o = Object.assign(f, s); o.inv = Object.assign({ kortti: 0, kala: 0, tarvike: 0 }, s.inv);
      o.up = Object.assign({ hose: 1 }, s.up);
      if (!('chart' in s)) o.seed = true;
      if (!s.w12) {
        // v12: SISU and the night's finds move with the world; the chart and the cave map start again from what the save
        // knew (the places are elsewhere now); the hose guides become spare parts, two for one; every crate is where
        // the world first has it; the hull's upgrades no longer matter.
        o.sub = { ...o.sub, x: toW12(o.sub.x) };
        o.finds = (o.finds || []).map(f => { const x = toW12(f.x); return { ...f, k: f.k === 'ohjain' ? 'osa' : f.k, x, y: Math.floor((floorY(x) - 0.9) * 10) / 10 }; });
        o.inv.osat = (o.inv.osat || 0) + Math.floor(((o.inv.ohjain || 0) + (o.guides || []).length) / 2);
        delete o.inv.ohjain; delete o.guides; delete o.up.hull;
        o.chart = ''; o.cave = ''; o.seed = true; o.w12 = 1;
      }
      if (!s.w13) {
        // v13: the wrecks' rooms are new, so the crates still lying where v12's world put them go where v13's has them.
        // A crate the player moved (it has `vy` or `hw`, which only lifting and letting go give) stays where it is and
        // settles there; one on the shelf, in SISU or on the ice stays too, but for those in v12's station on the
        // shelf (gone: they move to Aurora's store). As many of each wreck's crates as the player took from it (moved,
        // shelved or used up: v12's own crates there, `V12_SEA`, less those still untouched) are left out of its new
        // ones, of the same contents where it has them. Food and medicine lying loose became crates, so a night's find
        // of them is a spare part.
        // (a save from v11 or older got v13's own crates just above: nothing to move)
        const moved = c => !s.w12 || c.w !== 'sea' || 'vy' in c || 'hw' in c;
        // v12's station on the shelf is gone: its crates the player never touched are replaced by Aurora's own; one the
        // player moved there (lifted and let go) goes, as it is, into Aurora's store by the dock.
        let shelfN = 0;
        const kept = (o.crates || []).filter(c => moved(c) && !(c.w === 'ice' && c.x < 240 && !('vy' in c || 'hw' in c)))
          .map(c => c.w === 'ice' && c.x < 240 ? { ...c, x: 292.6 + (shelfN++ % 6), y: AUR.floors[0] - 2, f: 1 } : c.w === 'sea' ? { ...c, f: 1 } : c);
        const left = {};
        for (const c of o.crates || []) if (!moved(c)) { const site = c.id.split(':')[0]; left[site] = left[site] || {}; left[site][c.k] = (left[site][c.k] || 0) + 1; }
        const fresh13 = CRATES0.filter(c => !kept.some(k => k.id === c.id) && (c.w === 'sea' || c.id.startsWith('pinta:'))).map(c => ({ ...c }));
        if (s.w12) for (const [site, kinds] of Object.entries(V12_SEA)) {
          const take = [];
          for (const [k, n] of Object.entries(kinds)) for (let m = 0; m < n - ((left[site] || {})[k] || 0); m++) take.push(k);
          for (const k of take) {
            const here = fresh13.filter(c => c.w === 'sea' && c.id.startsWith(site + ':') && c.k !== 'pumppu');  // the pump is new
            const c = here.find(c => c.k === k) || here[here.length - 1];
            if (c) fresh13.splice(fresh13.indexOf(c), 1);
          }
        }
        o.crates = kept.concat(fresh13);
        o.finds = (o.finds || []).map(f => f.k === 'ruoka' || f.k === 'laake' ? { ...f, k: 'osa' } : f);
        o.w13 = 1;
      }
      // what was taken from the stores into a bag and lost with a reload goes back into the stores
      for (const [k, n] of Object.entries(o.pack || {})) o.inv[INV[k] || k] = (o.inv[INV[k] || k] || 0) + n;
      o.pack = {};
      // v13: so do Aurora's greens taken that day and not yet brought home
      o.inv.ruoka = (o.inv.ruoka || 0) + (o.tuore || 0); o.tuore = 0;
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
  try { localStorage.setItem(SAVE13, JSON.stringify(G.s)); } catch (e) {}
}

// ---------- the chart (v9, #160) ----------
// The chart in the navigation room shows only what has been explored: 20 m squares of the sea that SISU's lamp, a
// ping, a diver or a walker has reached (`chartSeen`), and the iceberg's outline as far as a lamp has lit it
// (`caveSeen`). A contact is first heard (❓), then known once a ping names its kind, then seen up close (its name).
// Both maps are kept in the save as bits.
const CH = { x0: 0, y0: -60, s: 20, w: Math.ceil(WORLD_W / 20) + 1, h: 74 };
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
  const lamps = [[sub.x, sub.y, 0, 0, 22, 0], [sub.x + f * 14 * SS, sub.y + 0.5, f > 0 ? 0.12 : Math.PI - 0.12, 60 * L, 0, 0.42]];
  const walkers = [];
  const mark = d => {
    const l = lampOf(d);
    lamps.push([...l, 0.55]);
    if (nearBerg(d.x, d.y) && pip(d.x, d.y, BERG.poly)) lampPoly(l[0], l[1], l[2], 0.55, l[3], l[4], true);
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
    if (!s.heard[c.id] && Math.hypot(c.x - sub.x, c.y - sub.y) < HEAR) { s.heard[c.id] = 1; G.mapNew = true; }
    if (s.seen[c.id]) continue;
    const near = (x, y) => c.box ? [Math.max(c.box[0], Math.min(c.box[2], x)), Math.max(c.box[1], Math.min(c.box[3], y))] : [c.x, c.y];
    if (lamps.some(l => lampSees(l, ...near(l[0], l[1]))) || walkers.some(w => Math.hypot(c.x - w.x, c.y - w.y) < 30 + c.r)) {
      s.seen[c.id] = s.heard[c.id] = 1; G.mapNew = true;
    }
  }
}
// A lamp's lit footprint on the chart: rays round its glow and across its beam, each marking the squares it passes
// until it meets rock, ice or a wall, so no light reaches the chart through a wall.
function chartLamp([x, y, mid, len, near, half]) {
  const ray = (a, L) => {
    const cx = Math.cos(a), cy = Math.sin(a);
    for (let t = 0; t <= L; t += 2) {
      const px = x + cx * t, py = y + cy * t;
      if (solid(px, py)) break;
      const i = Math.floor((px - CH.x0) / CH.s), j = Math.floor((py - CH.y0) / CH.s), n = i + j * CH.w;
      if (i >= 0 && j >= 0 && i < CH.w && j < CH.h && !chartSeen[n]) { chartSeen[n] = 1; G.mapNew = true; }
    }
  };
  if (near) for (let k = 0; k < 12; k++) ray(k / 12 * 2 * Math.PI, near);
  if (len) for (let k = -2; k <= 2; k++) ray(mid + half * k / 2, len);
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
function nearBerg(x, y) { return x > BERG_X[0] - 6 && x < BERG_X[1] + 4 && y < 206; }
function inBerg(x, y) { return nearBerg(x, y) && pip(x, y, BERG.poly) && !inCave(x, y); }
function siteAt(x, y) {
  for (const s of SITES) {
    const i = Math.floor((x - s.x) / C), j = Math.floor((y - s.y) / C);
    if (i >= 0 && j >= 0 && i < s.w && j < s.h) return s;
  }
  return null;
}
function cellAt(s, x, y) { return s.cells[Math.floor((y - s.y) / C)][Math.floor((x - s.x) / C)] || ' '; }
// v12 (#300): a site's walls are thin plates, WALL thick, along the middle of its '#' cells and on to the next '#'
// cell beside, above or below, as SISU's walls are; the rest of a '#' cell is water.
const WALL = 0.3;
function wallAt(s, x, y, t = WALL / 2) {
  const i = Math.floor((x - s.x) / C), j = Math.floor((y - s.y) / C), u = x - s.x - i * C - C / 2, v = y - s.y - j * C - C / 2;
  const at = (p, q) => (s.cells[q] || '')[p] === '#';
  if (Math.abs(v) <= t && (Math.abs(u) <= t || (u < 0 && at(i - 1, j)) || (u > 0 && at(i + 1, j)))) return true;
  return Math.abs(u) <= t && ((v < 0 && at(i, j - 1)) || (v > 0 && at(i, j + 1)));
}
// The plates as rectangles [x, y, w, h], for drawing (kept on the site).
function walls(s) {
  if (s.plates) return s.plates;
  const r = s.plates = [], t = WALL / 2;
  s.cells.forEach((row, j) => [...row].forEach((ch, i) => {
    if (ch !== '#') return;
    const cx = s.x + i * C + C / 2, cy = s.y + j * C + C / 2;
    r.push([cx - t, cy - t, WALL, WALL]);
    if (row[i + 1] === '#') r.push([cx, cy - t, C, WALL]);
    if ((s.cells[j + 1] || '')[i] === '#') r.push([cx - t, cy, WALL, C]);
  }));
  return r;
}
// Where something at (x, y) inside a site comes to rest: the top of the next plate below (v12, crates and furniture).
function siteFloor(s, x, y) {
  const i = Math.floor((x - s.x) / C);
  for (let j = Math.max(0, Math.floor((y - s.y) / C)); j < s.h; j++) {
    const cy = s.y + j * C + C / 2 - WALL / 2;
    if ((s.cells[j] || '')[i] === '#' && cy >= y - 0.01) return cy;
  }
  return null;
}
// Is (x, y) rock, ice or wall? A big body (the submarine) cannot enter a site's rooms either.
function solid(x, y, big) {
  if (y > floorY(x)) return true;
  if (x < glacierX(y) || x > WORLD_W - 8) return true;
  if (y < SHELF_Y && x < SHELF_X) return true;
  if (iceOn && y < ICE_Y + keel(x) && underIce(x)) return true;
  if (inBerg(x, y)) return true;
  const sb = y < 120 && smallBerg(x);
  if (sb && y < sb.d + 1 && pip(x, y, sb.poly.concat([[sb.x1, -1], [sb.x0, -1]]))) return true;
  if (x > VENT_X) for (const [vx, h] of VENTS) if (Math.abs(x - vx) < 1.6 + (y - floorY(vx) + h) * 0.08 && y > floorY(vx) - h) return true;
  const s = siteAt(x, y);
  if (!s) return false;
  const ch = cellAt(s, x, y);
  return big ? ch !== ' ' : ch === '#' && wallAt(s, x, y);
}
// Does SISU at (x, y) touch only the sea ice (v6)? Then it stops softly, without a bump; anything else still bumps.
let iceOn = true;
function onlyIce(x, y) { iceOn = false; const hit = subHits(x, y); iceOn = true; return !hit; }
function subHits(x, y) {
  for (let a = 0; a < 12; a++) {
    const t = a / 12 * Math.PI * 2;
    if (solid(x + Math.cos(t) * 13.6 * SS, y + Math.sin(t) * 2.4 * SS, true)) return true;
  }
  return solid(x, y - 5 * SS, true);
}
function diverHits(x, y) {
  for (let a = 0; a < 8; a++) {
    const t = a / 8 * Math.PI * 2;
    if (solid(x + Math.cos(t) * 0.5, y + Math.sin(t) * 0.5)) return true;
  }
  return false;
}
function airlock() { return { x: sub.x + sub.dir * 11 * SS, y: sub.y + 1.2 * SS }; }

// ---------- items, contacts, goals ----------
function allItems() { return ITEMS.concat(ICE_ITEMS, G.s ? G.s.finds.map(f => ({ ...f, site: 'find' })) : []); }
function itemHere(it) { return !G.s.got[it.id] && !G.held[it.id] && !G.carry.includes(it.id); }
// A find by its id; a harpooned fish (v8) is 'kala:<day>:<school>:<fish>' and lies nowhere.
// v12: goods taken from the stores into a bag are 'pack:<kind>:<n>'.
function itemById(id) {
  id = String(id);
  if (id.startsWith('kala:')) return { id, k: 'kala' };
  if (id.startsWith('pack:')) return { id, k: id.split(':')[1], site: 'pack' };
  if (id.startsWith('tuore:')) return { id, k: 'ruoka', site: 'pack' };  // v13: Aurora's greens
  return allItems().find(i => i.id === id);
}
function contacts() {
  // v9: `r` is how big it is, for seeing it up close; `spot` is where the autopilot takes SISU for it.
  const list = SITES.map(s => ({ id: s.id, kind: s.kind, name: s.name, x: s.x + s.w * C / 2, y: s.y + s.h * C / 2,
    r: Math.max(s.w, s.h) * C / 2, box: [s.x, s.y, s.x + s.w * C, s.y + s.h * C], spot: s.spot }));
  for (const b of [BERG_SITE, BERG_EAST]) list.push({ id: b.id, kind: b.kind, name: b.name, x: b.x, y: b.y, r: 6, spot: b.spot });
  HOLES.forEach((h, n) => list.push({ id: 'railo' + n, kind: 'RAILO JÄÄSSÄ', name: n === AUR.pool ? 'Tutkimusasema Aurora' : 'Railo', x: holeMid(n), y: ICE_Y, r: 17,
    spot: [holeMid(n), SURF] }));
  for (const f of G.s.finds) list.push({ id: f.id, kind: 'PIENI KAIKU', name: 'Pieni löytö', x: f.x, y: f.y, r: 1,
    spot: [f.x, Math.round(floorY(f.x)) - 6] });
  return list;
}

// ---------- hints and search areas (v12, #300) ----------
// The sea is too wide to ping all over: a far place is found from a hint — a log or the nomads — which puts a search
// area on the chart (a circle AREA_R round a point near the place, never on it). The autopilot goes to the area; the
// place itself is found there by hand, with the sonar. A hint about an opening (the nomads' camp, the weather station)
// names the opening outright. `HINTS[key]`: `sites` get an area each, `holes` become known.
const AREA_R = 150;
const HINTS = {
  leiri: { holes: [1] }, hylyt: { sites: ['polaris', 'nordvik'] }, aurora: { sites: ['aurora'] }, saa: { holes: [4] },
  kontit: { sites: ['kontit', 'syva'] }, rinne: { sites: ['rinne'] }, kestrel: { sites: ['kestrel'] },
  k7: { sites: ['itarailo'] }, saga: { sites: ['saga'] }, laskeutuja: { sites: ['laskeutuja'] }, nordlys: { sites: ['nordlys'] },
  majakka: { sites: ['majakka'] } };
// The hint a log gives when it is read.
const LOG_HINT = { paivakirja: 'leiri', nordvik: 'k7', k7: 'saga', saga: 'laskeutuja', laskeutuja: 'nordlys', kartta: 'majakka', saa: 'kestrel' };
function learn(key) {
  const s = G.s, h = HINTS[key];
  if (!h) return;
  for (const id of h.sites || []) if (!s.areas[id]) { s.areas[id] = 1; G.mapNew = true; }
  for (const n of h.holes || []) { s.heard['railo' + n] = s.known['railo' + n] = 1; G.mapNew = true; }
}
// Every hint the save has earned, again: a save from v11 has read logs that now point somewhere.
function relearn() {
  const s = G.s;
  for (const [log, key] of Object.entries(LOG_HINT)) if (s.flags[log]) learn(key);
  for (let n = 0; n < (s.trade || 0); n++) learn(TRADES[n].hint);
}
// A search area: its centre, the same for every phone, 70–140 m from the place and inside the sea.
function areaOf(id) {
  const c = contacts().find(k => k.id === id);
  if (!c) return null;
  const a = hash(id + 'a') * Math.PI * 2, d = 70 + hash(id + 'd') * 70;
  let x = Math.max(SHELF_X + 60, Math.min(WORLD_W - 60, c.x + Math.cos(a) * d));
  // never in the iceberg: beside it, east of it
  if (x > BERG_X[0] - 45 && x < BERG_X[1] + 30) x = BERG_X[1] + 35 + d * 0.3;
  const sb = BERGS.find(b => x > b.x0 - 25 && x < b.x1 + 25);
  if (sb) x = sb.x1 + 30;
  const y = Math.max(ICE_Y + 14, Math.min(floorY(x) - 16, c.y + Math.sin(a) * d * 0.5));
  return { id: 'area:' + id, site: id, name: c.name, x, y, r: AREA_R };
}
// The areas still worth showing: those whose place has not yet been named by a ping.
function areas() { return G.s ? Object.keys(G.s.areas || {}).filter(id => !(G.s.known[id] || G.s.seen[id])).map(areaOf).filter(Boolean) : []; }
// The goal's target as the chart and the sonar point to it: the place once heard, else its area if a hint gave one.
function aimAt(id) {
  if (!id || G.s.heard[id] || G.s.known[id] || G.s.seen[id] || !G.s.areas[id]) return id;
  return 'area:' + id;
}
function goalNow() {
  const g = goalText(), s = G.s;
  return { text: g.text, target: g.target && aimAt(g.target), site: g.target };
}
function goalText() {
  const s = G.s, f = s.flags;
  if (!f.pinged) return { text: 'Paina 📡 – kaiku paljastaa pohjan ja kohteet.', target: null };
  if (!f.kontti) return { text: 'Ruoka on vähissä. Aja kontin luo ja pysähdy. Sisällä puku päälle ja ulos ilmalukosta.', target: 'kontti' };
  if (!f.asema) return { text: 'Sonar kuuli metallia lahden pohjukassa. Tutki se.', target: 'asema' };
  // v12 (#300): the station's top on the ice tells of the nomads, who know where the wrecks lie.
  if (!f.paivakirja && !f.nordvik) return { text: G.mode !== 'ice' ? 'Tutkimusasema Aurora on jäällä railon yllä: nouse railoon sen alle ja kiipeä tornista asemalle.'
    : bldAt(walker.x) === AUR ? 'Radiopäiväkirja on ylimmän kerroksen radiohuoneessa: tikkaita ylös.' : 'Aurora on lahden pohjukassa.', target: 'railo0' };
  if (!s.trade && !f.nordvik) return { text: G.mode === 'ice' && holeAt(sub.x) === 1 ? 'Nomadien leiri on railon itäpuolella. Vie heille ruokaa ja lääkkeitä.'
    : 'Nomadit leiriytyvät itäisen railon luona. Ota varastosta reppuun 🥫 ja 💊 ja nouse railosta jäälle.', target: 'railo1' };
  if (!f.nordvik) return { text: 'Nomadien mukaan hylyt makaavat itään. Aja alueelle ja etsi ne sonarilla 📡.', target: f.polaris ? 'nordvik' : 'polaris' };
  // v13 (#300): Aurora's survivors need a new pump for their hydroponics (only before the antenna, so an older save
  // that got that far is not sent back).
  if (!f.pumppu && !s.inv.antenni) {
    const mc = G.s.crates.find(c => c.k === 'pumppu' && c.w === 'held' && c.by === me());
    if (!f.ingrid) return { text: 'Puhu Auroran Ingridille: nouse aseman railoon lahdella ja kiipeä tornista asemalle.', target: 'railo0' };
    return mc ? { text: 'Vie pumppu Auroran vesiviljelyyn Ingridille.', target: 'railo0' }
      : { text: 'Ingrid tarvitsee vesipumpun. Rahtilaiva Kestrel kuljetti niitä: etsi pumppu sen ruumasta.', target: 'kestrel' };
  }
  if (!s.inv.antenni) return { text: 'Etsi Nordlysin huoltovarasto K-7 jäävuoresta: itäkyljen railo vie sen luo.', target: 'itarailo' };
  if (!s.inv.vahvistin) return { text: 'Hae radion vahvistin tutkimusasemalta.', target: 'asema' };
  if (!f.end) return { text: 'Korjaa radio: 🏠 sisälle, yläkerran ohjaamoon.', target: null };
  // Chapter 2: down the continental slope, each place found from the last one's log.
  if (!f.saga) return { text: 'Aja itään jäävuoren ohi. Etsi kaapelilaiva Saga rinteen reunalta – letkupuvulla.', target: 'saga' };
  if (!f.laskeutuja) return { text: 'Laskeudu rinnettä alas Nordlysin pohjalaskeutujalle.', target: 'laskeutuja' };
  if (!f.kartta) return { text: f.silta ? 'Nordlys on tyhjä. Etsi karttahuoneesta, minne miehistö lähti.'
    : 'Etsi tutkimusalus Nordlys rinteen juurelta, noin 900 metristä.', target: 'nordlys' };
  if (!s.inv.kortti && !f.end2) return { text: 'Seuraa naputusta syvään mereen: Lyran majakka lähteiden luona.', target: 'majakka' };
  if (!f.end2) return { text: 'Soita majakan muistikortti: 🏠 sisälle, ohjaamon radioon.', target: null };
  return { text: 'Luku 2 on päättynyt. Lyra kuuluu yhä radiosta, jostain syvältä.', target: null };
}

// v12: the crates in the wrecks rest where they fell, on a plate or the sea floor, before anyone comes.
for (const c of CRATES0) if (c.w === 'sea') {
  let y = c.y;
  while (y < c.y + 40 && ![-0.38, 0, 0.38].some(dx => solid(c.x + dx, y + 0.01))) y += 0.02;
  c.y = y;
}
// v13: SISU is bigger and the floor rougher, so each site's parking spot rises until SISU fits there.
for (const s of SITES) for (let k = 0; k < 60 && subHits(...s.spot); k++) s.spot[1] -= 1;
