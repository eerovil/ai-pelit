'use strict';
// Course geometry in metres. v10 (#493): every surface has a top height `h` (a ramp rises from `h` at y0 to
// `h1` at y1); the layouts are v8's, lifted into steps, ramps, drops and climbing stones.
const RADAT = (() => {
function original() {
const FIN = 140, LIMIT = 150;
const FLOORS = [
  { x0: -5, x1: 5, y0: -4, y1: 10, h: 0 },          // the start
  { x0: -5, x1: 5, y0: 10, y1: 14, h: 0, h1: 1 },   // a ramp up to the bars
  { x0: -5, x1: 5, y0: 14, y1: 37, h: 1 },          // the spinning bars, checkpoint 1
  { x0: -5, x1: 5, y0: 59.8, y1: 66, h: 2.2 },      // checkpoint 2, at the top of the stones
  { x0: -5, x1: 5, y0: 66, y1: 87, h: 1.2 },        // a drop to the sliding walls, checkpoint 3
  { x0: -5, x1: 5, y0: 109, y1: 112, h: 1.2 },      // checkpoint 4
  { x0: -3, x1: 3, y0: 112, y1: 130, h: 1.2, h1: 2.4 }, // the narrow bridge under the hammers, uphill
  { x0: -5, x1: 5, y0: 130, y1: 148, h: 3.2 },      // a step up to the finish
];
// Stepping stones over the gap, 1.8 m apart, each row a little higher; the middle row is one
// platform sliding sideways, as high as its own stones.
const STONE_ROWS = [[38.8, [-3.4, 0, 3.4]], [43, [-1.7, 1.7]], [47.2, [-4.2, 4.2]], [51.4, [-1.7, 1.7]], [55.6, [-3.4, 0, 3.4]]];
const STONE_H = [1.2, 1.4, 1.6, 1.8, 2.0];
STONE_ROWS.forEach(([y, xs], i) => xs.forEach(cx => {
  const hw = i === 2 ? 0.8 : 1.2;
  FLOORS.push({ x0: cx - hw, x1: cx + hw, y0: y, y1: y + 2.4, h: STONE_H[i], stone: true });
}));
const MOV = { y0: 47.2, y1: 49.6, hw: 1.6, a: 2.5, w: 1.1, h: 1.6 };
// Spinning discs that carry you round; hop from one to the next. As high as the floors beside them.
const DISCS = [{ x: -1.5, y: 91, r: 3.2, w: 0.9, h: 1.2 }, { x: 2, y: 98, r: 3, w: -1.1, h: 1.2 }, { x: -1, y: 105, r: 3.2, w: 1.2, h: 1.2 }];
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
return {id:'main', board:'main10', name:'Puomipuisto', fin:FIN, limit:LIMIT, floors:FLOORS, stones:STONE_ROWS, mov:MOV, discs:DISCS, sweepers:SWEEPERS, pushers:PUSHERS, bumpers:BUMPERS, hammers:HAMMERS, cps:CPS, sections:SECTIONS, path:PATH, belts:[], tiles:[]};
}
const floor = (y0, y1, hw = 5, h = 0, h1) => (h1 === undefined ? {x0:-hw, x1:hw, y0, y1, h} : {x0:-hw, x1:hw, y0, y1, h, h1});
const point = (y, x=0, s=0.6) => ({y,x,s});
function base(id,name,fin,limit) {
  return {id,name,fin,limit,floors:[],stones:[],mov:null,discs:[],sweepers:[],pushers:[],bumpers:[],hammers:[],belts:[],tiles:[],cps:[],sections:[],path:[]};
}
// Narrow tile lanes step sideways; no invisible floor underneath when a row disappears.
// v10: each row may stand `rise` m above the one before (stairs of tiles), from height h.
function grid(c,y,period=4.6,on=2.6,h=0,rise=0) {
  for(let row=0;row<6;row++) {
    const group=c.tiles.length, center=[0,1.3,-1.3,1.3,-1.3,0][row];
    for(let col=0;col<2;col++) c.tiles.push({x0:center-1.6+col*1.6,x1:center+col*1.6,y0:y+row*2,y1:y+row*2+2,period,on,ph:-row*0.45,h:Math.round((h+rise*row)*100)/100});
    c.path.push({y:y+row*2+1.6,xs:[center],tiles:group});
  }
}
const gate = (y,w,ph,lane=2.4) => ({y,w,ph,a:1.3,lane});
const main=original();
const h=base('hihna','Hihnatehdas',150,160);
h.board='hihna10';
// Jumps up over the gaps, a ramp down the bar bridge, a step up to the back belt, two stones climbing
// from side to side after it (#493: rising stones on every course) and a drop to the finish.
h.floors=[floor(-4,10),floor(10,34,2.4),floor(36.8,40,5,0.5),floor(40,56,2,0.5),floor(58.8,62,5,1),floor(62,82,2.2,1,0.2),floor(82,90,5,1),floor(90,114,2.4,1),floor(116.8,121,5,1.5),floor(121,138,2.1,1.5),floor(138,140.4,5,1.5),floor(149.8,158,5,1.2)];
h.belts=[{...floor(12,34,2.4),vx:0,vy:-3.3},{...floor(40,56,2,0.5),vx:3.5,vy:0},{...floor(90,114,2.4,1),vx:0,vy:-3.6},{...floor(121,138,2.1,1.5),vx:-3.3,vy:0}];
h.stones=[[142.2,[-1.8]],[146,[1.8]]];
h.stones.forEach(([y,xs],i)=>{xs.forEach(cx=>h.floors.push({x0:cx-0.9,x1:cx+0.9,y0:y,y1:y+2,h:[1.8,2.1][i],stone:true}));});
h.sweepers=[{x:0,y:66,len:3.2,w:2.2,ph:0.6},{x:0,y:72,len:3.2,w:-2.4,ph:2},{x:0,y:78,len:3.2,w:2.3,ph:4}];
h.pushers=[gate(17,1.4,0),gate(23,-1.5,2),gate(29,1.5,4),gate(45,1.3,1,2),gate(51,-1.4,3,2),gate(96,-1.4,2),gate(102,1.5,0),gate(108,-1.6,4),gate(127,1.4,3,2.1),gate(133,-1.5,1,2.1)];
h.cps=[0,9,38,60,85,119,139,151.5];
h.sections=[[10,'HIHNAPORTIT'],[40,'SIVUHIHNA'],[62,'PUOMISILTA'],[90,'VASTAHIHNA'],[121,'LOPPUPORTTI'],[140,'KIVET']];
h.path=[point(9),{y:18.2,gap:0},{y:24.2,gap:1},{y:30.2,gap:2},point(33),point(38),{y:46.2,gap:3},{y:52.2,gap:4},point(55),point(60),point(64,0,0.4),point(69,0,0.4),point(75,0,0.4),point(81),point(85),{y:97.2,gap:5},{y:103.2,gap:6},{y:109.2,gap:7},point(113),point(119),{y:128.2,gap:8},{y:134.2,gap:9},point(139),{y:143.2,xs:[-1.8]},{y:147,xs:[1.8]},point(151),point(154)];
const l=base('laatat','Laattalaakso',150,160);
l.board='laatat10';
// Tiles climbing like stairs, stones up and down, a ramp up through the gates, a drop to the bars.
l.floors=[floor(-4,18),floor(30,37,5,1.2),floor(37,50,2.4,1.2),floor(75,80,5,1),floor(80,94,2.3,1,2),floor(94,118,1.8,2),floor(118,130,2.4,1.2),floor(142,158,5,1.8)];
l.path=[point(16)]; grid(l,18,4.6,2.6,0.2,0.2);
l.path.push(point(33),{y:42.2,gap:0},{y:47.2,gap:1},point(49));
const stoneRows=[[51.5,[-2.4]],[55.7,[0]],[59.9,[2.4]],[64.1,[0]],[68.3,[-2.4]],[72.5,[0]]], stoneH=[1.4,1.6,1.8,1.6,1.4,1.2];
l.stones=stoneRows;
stoneRows.forEach(([y,xs],i)=>{xs.forEach(cx=>l.floors.push({x0:cx-0.85,x1:cx+0.85,y0:y+0.2,y1:y+2.2,h:stoneH[i],stone:true}));l.path.push({y:y+1.2,xs});});
l.pushers=[gate(41,1.4,1),gate(46,-1.5,3),gate(84,1.5,2,2.3),gate(89,-1.4,0,2.3)];
l.sweepers=[{x:0,y:121.5,len:3.2,w:2.4,ph:0.4},{x:0,y:126.5,len:3.2,w:-2.6,ph:2.1}];
l.hammers=[{y:98,w:2.1,ph:0},{y:103,w:1.9,ph:2.2},{y:108,w:2.3,ph:4.1},{y:113,w:2,ph:1}];
l.path.push(point(78),{y:85.2,gap:2},{y:90.2,gap:3},point(92),point(105,0,0.3),point(119),point(121.5,0,0.3),point(124),point(126.5,0,0.3),point(129)); grid(l,130,4.2,2.3,1.2); l.path.push(point(145),point(154));
l.cps=[0,16,33,49,78,92,120,128,144,151.5];
l.sections=[[16,'LAATTAPOLKU'],[37,'PORTTI'],[50,'HYPPYKIVET'],[94,'HEILURISILTA'],[118,'PUOMIT'],[130,'LAATAT']];
const f=base('finaali','Kaaosfinaali',180,190);
f.board='finaali10';
// A ramp up the bar bridge, a drop over the gap, tiles and stones climbing, the hammer bridge
// downhill and a step up to the finish.
f.floors=[floor(-4,12),floor(12,35,2.4,0,1.2),floor(35,41,5,1.2),floor(41,54,2.4,1.2),floor(56.8,59,5,0.6),floor(59,73,2.1,0.6),floor(73,77,5,0.6),floor(99,116,5,0.6),floor(128,132,5,1.8),floor(139,142,5,2.4),floor(142,166,1.7,2.4,1.4),floor(166,188,5,2)];
f.sweepers=[{x:0,y:17,len:3.2,w:2.3,ph:0},{x:0,y:23,len:3.2,w:-2.5,ph:1.2},{x:0,y:29,len:3.2,w:2.4,ph:2.6}];
f.belts=[{...floor(43,54,2.4,1.2),vx:0,vy:-3.6},{...floor(59,73,2.1,0.6),vx:-3.4,vy:0}];
f.pushers=[gate(46,1.5,1),gate(51,-1.4,3),gate(63,-1.5,2,2.1),gate(69,1.4,0,2.1)];
// The right bumper stands over the gap between the stones, on a post at their height.
f.bumpers=[{x:-2.2,y:135},{x:2.2,y:135,h:2.25}];
f.discs=[{x:-1.5,y:81,r:3,w:1.4,h:0.6},{x:2,y:88,r:2.8,w:-1.6,h:0.6},{x:-1,y:95,r:3,w:1.7,h:0.6}];
f.mov={y0:84,y1:86.4,hw:1.3,a:2.7,w:1.5,h:0.6};
f.hammers=[{y:146,w:2.2,ph:0},{y:151,w:1.9,ph:2.2},{y:156,w:2.4,ph:4.1},{y:161,w:2.1,ph:1}];
f.path=[point(10),point(15,0,0.3),point(21,0,0.3),point(27,0,0.3),point(33),point(37),{y:47.2,gap:0},{y:52.2,gap:1},point(53),point(57.8),{y:64.2,gap:2},{y:70.2,gap:3},point(75),point(81,-1.5,0.4),point(88,2,0.4),point(95,-1,0.4),point(102),point(114)];
f.stones=[[132.8,[-2]],[137,[2]]];
f.stones.forEach(([y,xs],i)=>{xs.forEach(cx=>f.floors.push({x0:cx-0.95,x1:cx+0.95,y0:y,y1:y+2.4,h:[2.1,2.4][i],stone:true}));});
grid(f,116,4.2,2.3,0.8,0.2); f.path.push(point(131),{y:134,xs:[-2]},{y:138.2,xs:[2]},point(141),point(153,0,0.25),point(168),point(184));
f.cps=[0,10,37,57.8,75,102,114,131,141,168,181.5];
f.sections=[[12,'PUOMISILTA'],[41,'HIHNAPORTIT'],[77,'LEVYT'],[114,'LAATTAPOLKU'],[132,'KIVET'],[142,'HEILURIT']];
return [main,h,l,f];
})();
