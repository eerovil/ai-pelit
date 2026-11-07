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
  const direct=Array.isArray(shot.velocity)&&Array.isArray(shot.origin);
  const angle=shot.angle+(!direct&&shake?(rand()-.5)*.014:0);
  const range=throwRange(h,start,shot.disc,shot.power)*(!direct&&shake?1+(rand()-.5)*.018:1);
  const putt=distance(start,h.basket)<10;
  const pitch=clamp(shot.pitch??12,-65,65)*Math.PI/180,g=direct?4.5:putt?.65:4.5;
  const speed=direct?Math.hypot(...shot.velocity):putt?.8+shot.power*7.5:Math.sqrt(Math.max(.05,range)*g/Math.sin(24*Math.PI/180));
  const velocity=direct?shot.velocity:[Math.sin(angle)*speed*Math.cos(pitch),speed*Math.sin(pitch),Math.cos(angle)*speed*Math.cos(pitch)];
  const origin=direct?shot.origin:[start[0],ground(h,...start)+1.5,start[1]];
  const vx=Math.hypot(velocity[0],velocity[2]),vy=velocity[1];
  const duration=(vy+Math.sqrt(vy*vy+2*g*Math.max(4,origin[1]-ground(h,...start)+4+h.hill*2)))/g;
  const dx=velocity[0]/Math.max(.01,vx),dz=velocity[2]/Math.max(.01,vx),path=[];
  let safe=start.slice(),reason='grass',inBasket=false,hit=false,obstacle=null;
  // Prototype tuning, not measured aerodynamic coefficients. Fade depends on speed,
  // so a low flight can hit the ground before a strong low-speed finish develops.
  const dragRate=.16,fadeSpeed=5+d.speed*.9;
  // Bank pull starts strong and dies out (time constant bankTau), and sideways drift is
  // damped, so a late fade can overcome the curve.
  const bankPull=10,bankTau=1.4,bankDamp=.4;
  let fadeOffset=0,fadeVelocity=0,bankOffset=0,bankVelocity=0,previousTime=0;
  const point=t=>{
    const elapsed=t*duration;
    const forwardSpeed=direct?vx*Math.exp(-dragRate*elapsed):vx;
    const travel=direct?vx*(1-Math.exp(-dragRate*elapsed))/dragRate:vx*elapsed;
    const progress=travel/Math.max(range,1);
    // Smooth response: fast discs retain a gentle finish instead of a hard zero-fade cutoff.
    const slow=(.04+.96/(1+(forwardSpeed/fadeSpeed)**4))*(1-Math.exp(-elapsed/.7));
    if(direct){
      const dt=elapsed-previousTime;
      const acceleration=-forwardSpeed*(.03+d.fade*.06)*slow;
      fadeOffset+=fadeVelocity*dt+.5*acceleration*dt*dt;
      fadeVelocity+=acceleration*dt;
      const bankAcceleration=bankPull*shot.curve*Math.exp(-elapsed/bankTau)-bankDamp*bankVelocity;
      bankOffset+=bankVelocity*dt+.5*bankAcceleration*dt*dt;
      bankVelocity+=bankAcceleration*dt;previousTime=elapsed;
    }
    const fade=direct?fadeOffset:range*d.fade*.009*progress**3;
    // Positive tilt pulls screen-left; zero tilt adds no sideways pull.
    const bankCurve=direct?bankOffset:-shot.curve*range*.22*progress*progress;
    const turn=direct?0:range*d.turn*.012*Math.sin(Math.PI*progress);
    const side=fade+bankCurve+turn;
    return {x:origin[0]+dx*travel+dz*side+h.wind[0]*elapsed*elapsed*.03,
      z:origin[2]+dz*travel-dx*side+h.wind[1]*elapsed*elapsed*.03,
      y:origin[1]+vy*elapsed-.5*g*elapsed*elapsed,t:elapsed,tilt:shot.curve*.7*(direct?Math.exp(-elapsed/(2*bankTau)):1)+(direct?-slow*(.15+d.fade*.08):progress*d.fade*.04)};
  };
  // No step travels more than 12 cm, including fast throws past the basket and thin trunks.
  const steps=Math.max(60,Math.ceil(vx*duration/.12));
  for(let i=0;i<=steps;i++) {
    const p=point(i/steps);path.push(p);
    if(i>0&&p.y<=ground(h,p.x,p.z)+.05){p.y=ground(h,p.x,p.z)+.05;break;}
    if(catches(h,p,speed)) {reason='basket';inBasket=true;break;}
    const bh=ground(h,...h.basket);
    if(!hit&&Math.hypot(p.x-h.basket[0],p.z-h.basket[1])<.38&&p.y-bh>=.5&&p.y-bh<=1.3) {
      reason='rattle';hit=true;break;
    }
    const tree=h.trees.find(t=>Math.hypot(p.x-t[0],p.z-t[1])<t[2]+.1&&p.y<ground(h,t[0],t[1])+t[3]);
    if(tree) {
      obstacle=[tree[0],tree[1],tree[2]+.1];
      reason='tree';hit=true;break;
    }
    const rock=h.rocks.find(r=>Math.hypot(p.x-r[0],p.z-r[1])<r[2]&&p.y<ground(h,r[0],r[1])+r[2]*.65);
    if(rock) {
      obstacle=[rock[0],rock[1],rock[2]];
      reason='rock';hit=true;break;
    }
  }
  let p=path[path.length-1];
  if(!inBasket) {
    // A collision drops to its foot; an ordinary landing slides a little farther.
    const landing={...p,t:p.t+.28};
    if(obstacle){
      // Leave the next lie outside the collision footprint, on the side of impact.
      const ox=p.x-obstacle[0],oz=p.z-obstacle[1],length=Math.hypot(ox,oz),radius=obstacle[2]+.05;
      landing.x=obstacle[0]+(length?ox/length:-dx)*radius;
      landing.z=obstacle[1]+(length?oz/length:-dz)*radius;
    }
    landing.y=ground(h,landing.x,landing.z)+.05;path.push(landing);p=landing;
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
