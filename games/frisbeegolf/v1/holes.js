// Coordinates are metres; +z points down the fairway. The course never changes with a reload.
const HOLES = [
  {name:'Puiston portti', par:3, length:45, basket:[0,45], bend:0, hill:0},
  {name:'Koivukuja', par:3, length:62, basket:[4,62], bend:0, hill:.4},
  {name:'Kuusikon reuna', par:3, length:78, basket:[-8,78], bend:-5, hill:.7},
  {name:'Tuuliniitty', par:3, length:85, basket:[8,85], bend:4, hill:.8, wind:[1.2,.2]},
  {name:'Lammen laita', par:4, length:110, basket:[-10,110], bend:-8, hill:.5,
    water:[{x:8,z:52,rx:12,rz:17}]},
  {name:'Kallion yli', par:3, length:72, basket:[0,72], bend:0, hill:2, wind:[-.8,.3], rocks:[[-7,38,2.8]]},
  {name:'Metsän mutka', par:4, length:130, basket:[-14,130], bend:-11, hill:1,
    ob:29, wind:[.6,-.5]},
  {name:'Rantatuuli', par:3, length:95, basket:[6,95], bend:5, hill:.5,
    water:[{x:-13,z:48,rx:11,rz:21}], ob:30, wind:[-1.5,.5]},
  {name:'Kotikorille', par:4, length:140, basket:[0,140], bend:0, hill:1.3, ob:28, wind:[.8,.3]},
].map((h,i)=>{
  h.tee=[0,0]; h.wind=h.wind||[0,0]; h.water=h.water||[]; h.rocks=h.rocks||[];
  h.trees=[];
  for(let row=0;row<Math.ceil(h.length/7)+3;row++) {
    const z=row*7-7, centre=h.bend*Math.sin(Math.max(0,z)/h.length*Math.PI);
    for(const side of [-1,1]) {
      const n=row*13+i*19+(side+1)*11;
      h.trees.push([centre+side*(12+(n%7)),z,.28+(n%3)*.07,5+n%5,n%3===0?'birch':'spruce']);
      if(row%2===0)h.trees.push([centre+side*(24+n%13),z+3,.4,7+n%4,'spruce']);
    }
  }
  h.trees.push([-6,9,.25,6,'birch'],[7,20,.3,7,'spruce'],[-8,h.length-12,.3,6,'birch']);
  // A readable obstacle on later holes; every tee retains an open route on either side.
  if(i===2||i===6)h.trees.push([2,h.length*.52,.55,8,'birch']);
  return h;
});
const COURSE_PAR = HOLES.reduce((n,h)=>n+h.par,0);
function ground(h,x,z) {
  return h.hill*Math.sin(Math.max(0,Math.min(h.length,z))/h.length*Math.PI)+.12*Math.sin(x*.17)*Math.sin(z*.09);
}
function distance(a,b) { return Math.hypot(a[0]-b[0],a[1]-b[1]); }
function hazard(h,x,z) {
  if(h.water.some(w=>((x-w.x)/w.rx)**2+((z-w.z)/w.rz)**2<1))return 'water';
  if(h.ob&&(Math.abs(x)>h.ob||z< -12||z>h.length+26))return 'ob';
  return '';
}
