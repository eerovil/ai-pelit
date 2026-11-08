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
// Four columns, six rows; adjacent rows share an edge so the rhythm, not a tiny gap, is the challenge.
function grid(c,y,period=4.6,on=3.1) {
  for(let row=0;row<6;row++) {
    const group=c.tiles.length/4;
    for(let col=0;col<4;col++) c.tiles.push({x0:-4+col*2,x1:-2+col*2,y0:y+row*2,y1:y+row*2+2,period,on,ph:-row*0.4});
    c.path.push({y:y+row*2+1.6,x:0,s:0.35,tiles:group});
  }
}
const main=original();
const h=base('hihna','Hihnatehdas',150,160);
h.floors=[floor(-4,158)];
h.belts=[{...floor(12,21),vx:0,vy:-2},{...floor(25,34),vx:0,vy:-3},{...floor(38,47),vx:2.4,vy:0},{...floor(89,113),vx:0,vy:-2.3}];
h.sweepers=[{x:0,y:61,len:5.4,w:1.5,ph:0.6},{x:0,y:74,len:5.4,w:-1.7,ph:2}];
h.pushers=[{y:94,w:1.1,ph:0},{y:102,w:-1.2,ph:2},{y:110,w:1.5,ph:4}];
h.bumpers=[{x:-3,y:129},{x:0,y:133},{x:3,y:129}];
h.cps=[0,50,84,117,151.5];
h.sections=[[10,'HIHNAT'],[55,'PUOMIT'],[89,'SEINÄT'],[120,'LOPPUKIRI']];
h.path=[point(10),point(23),point(36),point(49,-1),point(57),point(69),point(84),point(92),{y:95.2,gap:0},{y:103.2,gap:1},{y:111.2,gap:2},point(120),point(135,1.8),point(154)];
const l=base('laatat','Laattalaakso',150,160);
l.floors=[floor(-4,18),floor(30,53),floor(75,94),floor(94,118,3),floor(118,130),floor(142,158)];
l.path=[point(16)]; grid(l,18);
l.path.push(point(33),point(51));
const stoneRows=[[54,[-3,0,3]],[58.2,[-1.5,1.5]],[62.4,[0]],[66.6,[-1.5,1.5]],[70.8,[-3,0,3]]];
l.stones=stoneRows;
stoneRows.forEach(([y,xs])=>{xs.forEach(cx=>l.floors.push({x0:cx-1.2,x1:cx+1.2,y0:y,y1:y+2.4,stone:true}));l.path.push({y:y+1.2,xs});});
l.hammers=[{y:99,w:1.5,ph:0},{y:106,w:1.3,ph:2.2},{y:113,w:1.8,ph:4.1}];
l.path.push(point(78),point(92),point(105,0,0.5),point(121),point(128)); grid(l,130,4.1,2.6); l.path.push(point(145),point(154));
l.cps=[0,33,77,120,144,151.5];
l.sections=[[16,'LAATAT'],[51,'KIVET'],[94,'HEILURIT'],[128,'LAATAT']];
const f=base('finaali','Kaaosfinaali',180,190);
f.floors=[floor(-4,77),floor(99,116),floor(128,141),floor(141,166,2.5),floor(166,188)];
f.sweepers=[{x:0,y:19,len:5.4,w:1.7,ph:0},{x:0,y:31,len:5.4,w:-1.9,ph:1.2}];
f.belts=[{...floor(43,53),vx:0,vy:-2.5},{...floor(58,72),vx:-2.4,vy:0}];
f.pushers=[{y:65,w:1.2,ph:1}];
f.bumpers=[{x:-3,y:135},{x:3,y:135}];
f.discs=[{x:-1.5,y:81,r:3.2,w:0.9},{x:2,y:88,r:3,w:-1.1},{x:-1,y:95,r:3.2,w:1.2}];
f.mov={y0:84,y1:86.4,hw:1.6,a:2.5,w:1.1};
f.hammers=[{y:147,w:1.6,ph:0},{y:154,w:1.3,ph:2.2},{y:161,w:1.9,ph:4.1}];
f.path=[point(10),point(25),point(38),point(55),point(63),{y:66.2,gap:0},point(75),point(81,-1.5,0.6),point(88,2,0.6),point(95,-1,0.6),point(102),point(114)];
grid(f,116); f.path.push(point(131),point(140),point(153,0,0.5),point(168),point(184));
f.cps=[0,38,75,102,131,168,181.5];
f.sections=[[12,'PUOMIT'],[41,'HIHNAT'],[77,'LEVYT'],[114,'LAATAT'],[141,'HEILURIT']];
return [main,h,l,f];
})();
