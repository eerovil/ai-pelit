// A fixed-step flight model: the same hole and throw produce the same path on every phone.
const DISCS = [
  {name:'Draiveri', speed:10, glide:5, turn:-1, fade:3, range:150, colour:0xffb64e},
  {name:'Midari', speed:5, glide:4, turn:0, fade:1, range:85, colour:0x52d9ba},
  {name:'Putteri', speed:2, glide:3, turn:0, fade:.15, range:35, colour:0xf48ca5},
];
const CHAIN_MAX=9;
function clamp(x,a,b) { return Math.max(a,Math.min(b,x)); }
function catches(h,p,speed) {
  const y=p.y-ground(h,...h.basket);
  return Math.hypot(p.x-h.basket[0],p.z-h.basket[1])<=.38&&y>=.5&&y<=1.3&&speed<=CHAIN_MAX;
}
function throwRange(h,lie,disc,power) {
  const max=distance(lie,h.basket)<10?12:DISCS[disc].range;
  return max*clamp(power,0,1);
}
function fly(shot,h,shake=true) {
  const d=DISCS[shot.disc], start=shot.lie;
  let seed=(shot.seed||1)>>>0;
  const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const angle=shot.angle+(shake?(rand()-.5)*.014:0);
  const range=throwRange(h,start,shot.disc,shot.power)*(shake?1+(rand()-.5)*.018:1);
  const putt=distance(start,h.basket)<10;
  const duration=putt?.5+range/6:1+range/(d.speed*1.8+4);
  const speed=range/duration, arc=putt?.25:1+range*.022*d.glide/4;
  const dx=Math.sin(angle), dz=Math.cos(angle), path=[];
  const sy=ground(h,...start)+1.05;
  let safe=start.slice(), reason='grass', inBasket=false, hit=false;
  const point=(t)=>{
    const side=putt?0:range*(shot.curve*.22*t*t+d.turn*.012*Math.sin(Math.PI*t)+d.fade*.009*t*t*t);
    const x=start[0]+dx*range*t+dz*side+h.wind[0]*t*t*duration*.38;
    const z=start[1]+dz*range*t-dx*side+h.wind[1]*t*t*duration*.38;
    const endY=ground(h,x,z)+.05;
    return {x,z,y:sy*(1-t)+endY*t+4*arc*t*(1-t),t:t*duration,tilt:shot.curve*.7+t*d.fade*.04};
  };
  // No step travels more than 12 cm, including fast throws past the basket and thin trunks.
  const steps=Math.max(60,Math.ceil(range/.12));
  for(let i=0;i<=steps;i++) {
    const p=point(i/steps);path.push(p);
    if(catches(h,p,speed)) {reason='basket';inBasket=true;break;}
    const bh=ground(h,...h.basket);
    if(!hit&&Math.hypot(p.x-h.basket[0],p.z-h.basket[1])<.38&&p.y-bh>=.5&&p.y-bh<=1.3) {
      reason='rattle';hit=true;break;
    }
    if(h.trees.some(t=>Math.hypot(p.x-t[0],p.z-t[1])<t[2]+.1&&p.y<ground(h,t[0],t[1])+t[3])) {
      reason='tree';hit=true;break;
    }
    if(h.rocks.some(r=>Math.hypot(p.x-r[0],p.z-r[1])<r[2]&&p.y<ground(h,r[0],r[1])+r[2]*.65)) {
      reason='rock';hit=true;break;
    }
  }
  let p=path[path.length-1];
  if(!inBasket) {
    // A collision drops to its foot; an ordinary landing slides a little farther.
    const landing={...p,y:ground(h,p.x,p.z)+.05,t:p.t+.28};path.push(landing);p=landing;
    if(!hit)for(let i=1;i<=12;i++) {
      const q={...p,x:p.x+dx*range*.018*i/12,z:p.z+dz*range*.018*i/12,t:p.t+i*.035};
      q.y=ground(h,q.x,q.z)+.05;path.push(q);
    }
  }
  // Find the last safe boundary before the final hazardous landing, even if it flew over water.
  p=path[path.length-1]; const danger=inBasket?'':hazard(h,p.x,p.z);
  if(danger) {
    for(const q of path)if(!hazard(h,q.x,q.z))safe=[q.x,q.z];
    // Move back toward the previous safe lie, leaving a small margin at the boundary.
    const a=distance(safe,start);if(a>.1)safe=[safe[0]+(start[0]-safe[0])*.15/a,safe[1]+(start[1]-safe[1])*.15/a];
    reason=danger;
  }
  return {path,lie:danger?safe:[p.x,p.z],reason,holed:inBasket,penalty:danger?1:0,duration:path[path.length-1].t};
}
function flightPoint(f,t) {
  const a=f.path;let lo=0,hi=a.length-1;
  while(lo<hi){const m=(lo+hi+1)>>1;if(a[m].t<=t)lo=m;else hi=m-1;}
  const p=a[lo],q=a[Math.min(lo+1,a.length-1)],r=q.t===p.t?0:clamp((t-p.t)/(q.t-p.t),0,1);
  return {x:p.x+(q.x-p.x)*r,y:p.y+(q.y-p.y)*r,z:p.z+(q.z-p.z)*r,tilt:p.tilt};
}
