'use strict';
// Pure simulation shared by play and the course-solvability tests.
var BALL_RADIUS=.11, CUP_RADIUS=.18, CUP_SPEED=2.3, MAX_SPEED=4.6, FIXED_DT=1/240;
function inRect(x,y,r) { return x>=r[0] && y>=r[1] && x<=r[0]+r[2] && y<=r[1]+r[3]; }
function golfBall(tee) { return {x:tee[0],y:tee[1],vx:0,vy:0,holed:false,water:false}; }
function wallHit(b,x1,y1,x2,y2,r,bounce) {
  var dx=x2-x1,dy=y2-y1,len=dx*dx+dy*dy;
  var t=len ? Math.max(0,Math.min(1,((b.x-x1)*dx+(b.y-y1)*dy)/len)) : 0;
  var nx=b.x-x1-t*dx,ny=b.y-y1-t*dy,d=Math.hypot(nx,ny);
  if(d>=r) return false;
  if(d<1e-8) { var speed=Math.hypot(b.vx,b.vy)||1; nx=-b.vx/speed; ny=-b.vy/speed; if(!nx&&!ny) nx=1; }
  else { nx/=d; ny/=d; }
  b.x+=nx*(r-d+.00001); b.y+=ny*(r-d+.00001);
  var along=b.vx*nx+b.vy*ny;
  if(along<0) { b.vx-=(1+bounce)*along*nx; b.vy-=(1+bounce)*along*ny; return true; }
  return false;
}
function golfStep(b,h,dt,time) {
  if(b.holed||b.water) return '';
  var speed=Math.hypot(b.vx,b.vy);
  if(speed===0) return '';
  var event='', sand=h.sand.some(r=>inRect(b.x,b.y,r));
  var friction=.55*(sand?4:1);
  var slowing=Math.max(0,speed-friction*dt)/speed;
  b.vx*=slowing; b.vy*=slowing;
  h.slopes.forEach(function(r) { if(inRect(b.x,b.y,r)) { b.vx+=r[4]*dt; b.vy+=r[5]*dt; } });
  b.x+=b.vx*dt; b.y+=b.vy*dt;
  h.walls.concat([[0,0,h.w,0],[h.w,0,h.w,h.h],[h.w,h.h,0,h.h],[0,h.h,0,0]])
    .forEach(function(w) { if(wallHit(b,...w,BALL_RADIUS,.7)) event='wall'; });
  h.bumpers.forEach(function(p) { if(wallHit(b,p[0],p[1],p[0],p[1],p[2]+BALL_RADIUS,1.1)) event='wall'; });
  if(h.mill) {
    var m=h.mill,a=time*m[3];
    for(var j=0;j<2;j++) {
      var x=Math.cos(a+j*Math.PI/2)*m[2],y=Math.sin(a+j*Math.PI/2)*m[2];
      if(wallHit(b,m[0]-x,m[1]-y,m[0]+x,m[1]+y,BALL_RADIUS+.045,.7)) event='wall';
    }
  }
  // Resolve corner overlaps and keep even a blade's push within the outer wall.
  b.x=Math.max(BALL_RADIUS,Math.min(h.w-BALL_RADIUS,b.x));
  b.y=Math.max(BALL_RADIUS,Math.min(h.h-BALL_RADIUS,b.y));
  speed=Math.hypot(b.vx,b.vy);
  if(speed>MAX_SPEED) { b.vx*=MAX_SPEED/speed; b.vy*=MAX_SPEED/speed; }
  if(h.water.some(r=>inRect(b.x,b.y,r))) { b.water=true; b.vx=b.vy=0; return 'water'; }
  var dx=h.cup[0]-b.x,dy=h.cup[1]-b.y,d=Math.hypot(dx,dy);
  if(d<CUP_RADIUS && speed<CUP_SPEED) { b.holed=true; b.x=h.cup[0]; b.y=h.cup[1]; b.vx=b.vy=0; return 'cup'; }
  if(d<CUP_RADIUS && !b.rim) { b.rim=true; event='rim'; }
  if(d>CUP_RADIUS*1.4) b.rim=false;
  if(speed<.05) { b.vx=b.vy=0; }
  if(sand&&!b.sand) event='sand';
  b.sand=sand;
  return event;
}
function simulateShot(h,start,a,p,time) {
  var b=golfBall([start.x,start.y]); b.vx=Math.cos(a)*p*MAX_SPEED; b.vy=Math.sin(a)*p*MAX_SPEED;
  var t=time||0;
  for(var i=0;i<240*25 && !b.holed&&!b.water&&(b.vx||b.vy);i++) { t+=FIXED_DT; golfStep(b,h,FIXED_DT,t); }
  return b;
}
