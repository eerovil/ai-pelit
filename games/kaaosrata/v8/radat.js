'use strict';
// Course geometry in metres. The first course preserves v5 exactly.
const RADAT = (() => {
function original() {
const FIN = 140, LIMIT = 150;
const FLOORS = [
  { x0: -5, x1: 5, y0: -4, y1: 37 },          // start, the spinning bars, checkpoint 1
  { x0: -5, x1: 5, y0: 59.8, y1: 87 },        // checkpoint 2, the sliding walls, checkpoint 3
  { x0: -5, x1: 5, y0: 109, y1: 112 },        // checkpoint 4
  { x0: -3, x1: 3, y0: 112, y1: 130 },        // the narrow bridge under the hammers
  { x0: -5, x1: 5, y0: 130, y1: 148 },        // the finish
];
// Stepping stones over the gap, 1.8 m apart; the middle row is one platform sliding sideways.
const STONE_ROWS = [[38.8, [-3.4, 0, 3.4]], [43, [-1.7, 1.7]], [47.2, [-4.2, 4.2]], [51.4, [-1.7, 1.7]], [55.6, [-3.4, 0, 3.4]]];
STONE_ROWS.forEach(([y, xs], i) => xs.forEach(cx => {
  const hw = i === 2 ? 0.8 : 1.2;
  FLOORS.push({ x0: cx - hw, x1: cx + hw, y0: y, y1: y + 2.4, stone: true });
}));
const MOV = { y0: 47.2, y1: 49.6, hw: 1.6, a: 2.5, w: 1.1 };
// Spinning discs that carry you round; hop from one to the next.
const DISCS = [{ x: -1.5, y: 91, r: 3.2, w: 0.9 }, { x: 2, y: 98, r: 3, w: -1.1 }, { x: -1, y: 105, r: 3.2, w: 1.2 }];
// Low spinning bars: jump over, or get swept away. Each has a solid hub.
const SWEEPERS = [{ x: 0, y: 18, len: 5.4, w: 1.5, ph: 0 }, { x: 0, y: 28, len: 5.4, w: -1.9, ph: 1.2 }];
// Walls sliding sideways: two blocks a row, always a gap somewhere. Too tall to jump.
const PUSHERS = [{ y: 67.5, w: 1.3, ph: 0 }, { y: 72.5, w: -1.0, ph: 2 }, { y: 77.5, w: 1.7, ph: 4 }];
const BUMPERS = [{ x: -3, y: 81.5 }, { x: 0, y: 82.5 }, { x: 3, y: 81.5 }];
// Big balls swinging across the bridge: they knock you off it.
const HAMMERS = [{ y: 116, w: 1.6, ph: 0 }, { y: 121, w: 1.3, ph: 2.2 }, { y: 126, w: 1.9, ph: 4.1 }];
// Where you come back after a fall, and the line to cross to get there.
const CPS = [0, 35.5, 61.4, 85.5, 110.5, FIN + 1.5];
const SECTIONS = [[12, 'PUOMIT'], [37, 'KIVET'], [63, 'SEINÄT'], [87, 'LEVYT'], [112, 'HEILURIT']];

const PATH = [
  { y: 10, x: 0, s: 3 }, { y: 22, x: 0, s: 4 }, { y: 35.5, x: 0, s: 3 },
  { y: 40, xs: STONE_ROWS[0][1] }, { y: 44.2, xs: STONE_ROWS[1][1] }, { y: 48.4, mov: true },
  { y: 52.6, xs: STONE_ROWS[3][1] }, { y: 56.8, xs: STONE_ROWS[4][1] }, { y: 61.4, x: 0, s: 3 },
  { y: 66, x: 0, s: 3 }, { y: 68.6, gap: 0 }, { y: 73.6, gap: 1 }, { y: 78.6, gap: 2 }, { y: 85.5, x: 0, s: 2.5 },
  { y: 91, x: -1.5, s: 1.2 }, { y: 98, x: 2, s: 1.2 }, { y: 105, x: -1, s: 1.2 }, { y: 110.5, x: 0, s: 2 },
  { y: 121, x: 0, s: 1.2 }, { y: 132, x: 0, s: 2 }, { y: FIN + 4, x: 0, s: 3 },
];
return {id:'main', name:'Puomipuisto', fin:FIN, limit:LIMIT, floors:FLOORS, stones:STONE_ROWS, mov:MOV, discs:DISCS, sweepers:SWEEPERS, pushers:PUSHERS, bumpers:BUMPERS, hammers:HAMMERS, cps:CPS, sections:SECTIONS, path:PATH, belts:[], tiles:[]};
}
const floor = (y0, y1, hw = 5) => ({x0:-hw, x1:hw, y0, y1});
const point = (y, x=0, s=0.6) => ({y,x,s});
function base(id,name,fin,limit) {
  return {id,name,fin,limit,floors:[],stones:[],mov:null,discs:[],sweepers:[],pushers:[],bumpers:[],hammers:[],belts:[],tiles:[],cps:[],sections:[],path:[]};
}
// Narrow tile lanes step sideways; no invisible floor underneath when a row disappears.
function grid(c,y,period=5.2,on=3.3) {
  for(let row=0;row<6;row++) {
    const group=c.tiles.length, center=[0,1.1,1.1,0,-1.1,0][row];
    for(let col=0;col<2;col++) c.tiles.push({x0:center-1.6+col*1.6,x1:center+col*1.6,y0:y+row*2,y1:y+row*2+2,period,on,ph:-row*0.45});
    c.path.push({y:y+row*2+1.6,xs:[center],tiles:group});
  }
}
const gate = (y,w,ph) => ({y,w,ph,a:1.15,lane:3.1});
const main=original();
const h=base('hihna','Hihnatehdas',150,160);
h.board='hihna7';
h.floors=[floor(-4,10),floor(10,34,3.1),floor(36.2,40),floor(40,56,2.5),floor(58.2,62),floor(62,82,3),floor(82,90),floor(90,114,3.1),floor(116.2,121),floor(121,140,2.7),floor(140,158)];
h.belts=[{...floor(12,34,3.1),vx:0,vy:-2.6},{...floor(40,56,2.5),vx:2.8,vy:0},{...floor(90,114,3.1),vx:0,vy:-3},{...floor(121,140,2.7),vx:-2.6,vy:0}];
h.sweepers=[{x:0,y:68,len:3.4,w:1.5,ph:0.6},{x:0,y:77,len:3.4,w:-1.7,ph:2}];
h.pushers=[gate(19,0.9,0),gate(28,-1.05,2),gate(47,0.85,1),gate(98,-0.9,2),gate(108,1.05,0),gate(130,0.9,3)];
h.bumpers=[{x:0,y:145}];
h.cps=[0,9,38,60,85,119,142,151.5];
h.sections=[[10,'HIHNAPORTIT'],[40,'SIVUHIHNA'],[62,'PUOMISILTA'],[90,'VASTAHIHNA'],[121,'LOPPUPORTTI']];
h.path=[point(9),{y:20.2,gap:0},{y:29.2,gap:1},point(33),point(38),{y:48.2,gap:2},point(55),point(60),point(67),point(75),point(85),{y:99.2,gap:3},{y:109.2,gap:4},point(113),point(119),{y:131.2,gap:5},point(142),point(147,1.8),point(154)];
const l=base('laatat','Laattalaakso',150,160);
l.board='laatat7';
l.floors=[floor(-4,18),floor(30,37),floor(37,50,3.1),floor(75,80),floor(80,94,3),floor(94,118,2.3),floor(118,130),floor(142,158)];
l.path=[point(16)]; grid(l,18);
l.path.push(point(33),{y:43.2,gap:0},point(49));
const stoneRows=[[51.5,[-2]],[55.7,[0]],[59.9,[2]],[64.1,[0]],[68.3,[-2]],[72.5,[0]]];
l.stones=stoneRows;
stoneRows.forEach(([y,xs])=>{xs.forEach(cx=>l.floors.push({x0:cx-1.1,x1:cx+1.1,y0:y,y1:y+2.4,stone:true}));l.path.push({y:y+1.2,xs});});
l.pushers=[gate(42,1,1),gate(86,1.1,2)];
l.hammers=[{y:99,w:1.5,ph:0},{y:106,w:1.3,ph:2.2},{y:113,w:1.8,ph:4.1}];
l.path.push(point(78),{y:87.2,gap:1},point(92),point(105,0,0.35),point(121),point(128)); grid(l,130,4.8,2.8); l.path.push(point(145),point(154));
l.cps=[0,16,33,49,78,92,120,128,144,151.5];
l.sections=[[16,'LAATTAPOLKU'],[37,'PORTTI'],[50,'HYPPYKIVET'],[94,'HEILURISILTA'],[128,'LAATAT']];
const f=base('finaali','Kaaosfinaali',180,190);
f.board='finaali7';
f.floors=[floor(-4,12),floor(12,35,3.1),floor(35,41),floor(41,54,3.1),floor(56.2,59),floor(59,73,2.7),floor(73,77),floor(99,116),floor(128,132),floor(139,142),floor(142,166,2.1),floor(166,188)];
f.sweepers=[{x:0,y:19,len:3.5,w:1.7,ph:0},{x:0,y:29,len:3.5,w:-1.9,ph:1.2}];
f.belts=[{...floor(43,54,3.1),vx:0,vy:-3},{...floor(59,73,2.7),vx:-2.8,vy:0}];
f.pushers=[gate(48,1,1),gate(66,-1.05,2)];
f.bumpers=[{x:-3,y:135},{x:3,y:135}];
f.discs=[{x:-1.5,y:81,r:3.2,w:0.9},{x:2,y:88,r:3,w:-1.1},{x:-1,y:95,r:3.2,w:1.2}];
f.mov={y0:84,y1:86.4,hw:1.6,a:2.5,w:1.1};
f.hammers=[{y:147,w:1.6,ph:0},{y:154,w:1.3,ph:2.2},{y:161,w:1.9,ph:4.1}];
f.path=[point(10),point(24),point(37),{y:49.2,gap:0},point(53),point(57.8),{y:67.2,gap:1},point(75),point(81,-1.5,0.4),point(88,2,0.4),point(95,-1,0.4),point(102),point(114)];
f.stones=[[132.8,[-1.7]],[137,[1.7]]];
f.stones.forEach(([y,xs])=>{xs.forEach(cx=>f.floors.push({x0:cx-1.2,x1:cx+1.2,y0:y,y1:y+2.4,stone:true}));});
grid(f,116,4.8,2.8); f.path.push(point(131),{y:134,xs:[-1.7]},{y:138.2,xs:[1.7]},point(141),point(153,0,0.3),point(168),point(184));
f.cps=[0,10,37,57.8,75,102,114,131,141,168,181.5];
f.sections=[[12,'PUOMISILTA'],[41,'HIHNAPORTIT'],[77,'LEVYT'],[114,'LAATTAPOLKU'],[132,'KIVET'],[142,'HEILURIT']];
return [main,h,l,f];
})();
