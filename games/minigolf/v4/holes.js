'use strict';
// Metres, with y increasing down the course. The boundary is always solid.
var HOLES = [
  {name:'Suora', par:2, tee:[2,6.8], cup:[2,1.2]},
  {name:'Mutka', par:2, tee:[.7,6.8], cup:[3.1,1.1], walls:[[1.5,3,1.5,8]]},
  {name:'Puskurit', par:3, tee:[2,6.8], cup:[2,1.1], bumpers:[[1.2,4.4,.35],[2.8,3.3,.35],[1.6,2.4,.3]]},
  {name:'Hiekkaeste', par:3, tee:[2,6.8], cup:[2,1.1], sand:[[.2,3,2.5,1.6]]},
  {name:'Rinne', par:3, tee:[2,6.8], cup:[2,1.1], slopes:[[.2,2.4,3.6,2,.42,0]]},
  {name:'Lampi', par:3, tee:[.8,6.8], cup:[3,1.1], water:[[1.3,3.2,2.5,1.4]]},
  {name:'Siksak', par:3, tee:[.7,6.8], cup:[3.1,1.1], walls:[[1.5,5,4,5],[0,2.8,2.3,2.8]]},
  {name:'Tuulimylly', par:3, tee:[2,6.8], cup:[2,1.1], mill:[2,3.7,1.05,.65]},
  {name:'Loppukiri', par:4, tee:[2,6.8], cup:[2,1.1], sand:[[.2,4.7,1.2,1.2]],
    water:[[2.6,2.6,1.2,2]], slopes:[[.2,2,2.2,1.8,.38,0]], bumpers:[[1.7,4,.3]]}
].map(function(h) {
  return Object.assign({w:4,h:8,walls:[],bumpers:[],sand:[],water:[],slopes:[],mill:null},h);
});
