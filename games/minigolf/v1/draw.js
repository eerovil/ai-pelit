'use strict';
var canvas=$('c'),ctx=canvas.getContext('2d'),W=0,H=0,scale=1,ox=0,oy=0,side=false,rotationGrace=0,parkedAim=false;
function fit() {
  var box=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
  var rotated=W&&((box.width>box.height)!==side);
  W=box.width;H=box.height;side=W>H;
  if(rotated){rotationGrace=performance.now()+1000;if(dragging)dragging.reanchor=true;}
  canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
  var h=round?HOLES[round.hole]:HOLES[0];
  var top=side?76:112,bottom=side?46:100;
  scale=Math.min((W-44)/(side?h.h:h.w),(H-top-bottom)/(side?h.w:h.h));
  ox=(W-(side?h.h:h.w)*scale)/2;oy=top+(H-top-bottom-(side?h.w:h.h)*scale)/2;
  askDraw();
}
function P(x,y) { var h=round?HOLES[round.hole]:HOLES[0];return side?[ox+(h.h-y)*scale,oy+x*scale]:[ox+x*scale,oy+y*scale]; }
function worldVector(x,y) {return side?[y,-x]:[x,y];}
function screenVector(x,y) {return side?[-y,x]:[x,y];}
function path(points,fill,stroke,width) {
  ctx.beginPath();points.forEach((p,i)=>{var q=P(...p);i?ctx.lineTo(...q):ctx.moveTo(...q);});
  if(fill){ctx.closePath();ctx.fillStyle=fill;ctx.fill();}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width||1;ctx.stroke();}
}
function rect(r,fill) { path([[r[0],r[1]],[r[0]+r[2],r[1]],[r[0]+r[2],r[1]+r[3]],[r[0],r[1]+r[3]]],fill); }
function circle(x,y,r,fill,stroke,width) {var p=P(x,y);ctx.beginPath();ctx.arc(...p,r*scale,0,Math.PI*2);ctx.fillStyle=fill;ctx.fill();if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width||1;ctx.stroke();}}
// The same scattered sand grains every frame.
function grain(i) {var n=Math.sin(i*12.9898)*43758.5453;return n-Math.floor(n);}
function draw() {
  ctx.clearRect(0,0,W,H);
  var h=round?HOLES[round.hole]:HOLES[0];
  rect([-.12,-.12,h.w+.24,h.h+.24],'#897753');
  rect([0,0,h.w,h.h],'#4e9761');
  for(var y=0;y<h.h-.001;y+=.8) rect([0,y,h.w,Math.min(.4,h.h-y)],'#529b65');
  h.sand.forEach(function(r){rect(r,'#dbc58f');for(var i=0;i<30;i++){var x=r[0]+grain(i)*r[2],y=r[1]+grain(i+50)*r[3];circle(x,y,.018,'#b49a60');}});
  h.water.forEach(function(r){rect(r,'#4da5b5');for(var y=r[1]+.2;y<r[1]+r[3];y+=.3)path([[r[0]+.12,y],[r[0]+r[2]-.12,y]],null,'#88cbd2',1);});
  h.slopes.forEach(function(r){rect(r,'#73a866');for(var y=r[1]+.35;y<r[1]+r[3];y+=.6)for(var x=r[0]+.35;x<r[0]+r[2];x+=.6)path([[x-.09,y-.09],[x+.09,y],[x-.09,y+.09]],null,'#bed59b',2);});
  h.walls.forEach(w=>{path([[w[0],w[1]],[w[2],w[3]]],null,'#e5d7a5',8);path([[w[0],w[1]],[w[2],w[3]]],null,'#92835b',2);});
  h.bumpers.forEach(p=>{circle(p[0],p[1]+.04,p[2]+.04,'#376646');circle(...p,'#e5c270','#fbe4a4',3);circle(p[0],p[1],p[2]*.5,'#b68e48');});
  if(h.mill) {
    var m=h.mill,a=(round?round.time:0)*m[3];
    for(var j=0;j<2;j++){var x=Math.cos(a+j*Math.PI/2)*m[2],y=Math.sin(a+j*Math.PI/2)*m[2];path([[m[0]-x,m[1]-y],[m[0]+x,m[1]+y]],null,'#f2d9ad',8);}
    circle(m[0],m[1],.17,'#af7351');
  }
  circle(...h.cup,.23,'#326947');circle(...h.cup,.18,'#132b24');
  var cup=P(...h.cup);ctx.strokeStyle='#fff4d2';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(cup[0]+2,cup[1]-3);ctx.lineTo(cup[0]+2,cup[1]-29);ctx.stroke();ctx.fillStyle='#f4cb71';ctx.beginPath();ctx.moveTo(cup[0]+3,cup[1]-29);ctx.lineTo(cup[0]+20,cup[1]-23);ctx.lineTo(cup[0]+3,cup[1]-17);ctx.fill();
  var players=round?round.players:[{ball:golfBall(h.tee)}];
  players.forEach(function(p,i){var b=p.ball;if(b.holed||b.water)return;var active=!round||i===round.turn;ctx.globalAlpha=active?1:.35;circle(b.x+.035,b.y+.05,BALL_RADIUS*1.2,'#264936');circle(b.x,b.y,BALL_RADIUS,colors[i],'#ffffff',1);if(active)circle(b.x-.025,b.y-.03,.025,'white');ctx.globalAlpha=1;});
  if(round&&aim&&round.phase==='aim') {
    var b=round.players[round.turn].ball,dist=Math.min(3.5,Math.pow(aim.p*MAX_SPEED,2)/1.1),v=[Math.cos(aim.a),Math.sin(aim.a)];
    ctx.setLineDash([4,6]);path([[b.x,b.y],[b.x+v[0]*dist,b.y+v[1]*dist]],null,'#fff2bc',2);ctx.setLineDash([]);
    var q=P(b.x,b.y);ctx.strokeStyle='#ffdb83';ctx.lineWidth=2;ctx.beginPath();ctx.arc(...q,13+aim.p*7,0,2*Math.PI);ctx.stroke();
  }
}
function askDraw() { if(!raf&&!document.hidden) raf=requestAnimationFrame(frame); }
function frame(now) {
  raf=0;var dt=lastFrame?Math.min(.1,(now-lastFrame)/1000):0;lastFrame=now;
  if(round&&['aim','roll','hole'].includes(round.phase)&&(!online||!R.paused)) {
    if(authority()) step(dt);
    if(online&&R.isHost&&now-lastSend>66){sendState();lastSend=now;}
    if(round.phase==='roll'&&S) {if(!rollingSound)rollingSound=S.loop('rullaus',{vol:.08});var b=round.players[round.turn].ball;rollingSound.set({vol:Math.min(.12,Math.hypot(b.vx,b.vy)*.025),rate:.7+Math.hypot(b.vx,b.vy)*.15});}
    else stopSound();
  } else stopSound();
  draw();
  if(round&&['aim','roll','hole'].includes(round.phase)&&(round.phase==='roll'||(round.phase==='hole'&&!online)||HOLES[round.hole].mill)&&(!online||!R.paused)) askDraw();
  else lastFrame=0;
}
function pointer(e) { var r=canvas.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top]; }
function dragAim(e) {
  if(!dragging||e.pointerId!==dragging.id||!canAim())return;
  // A finger may move before the resize observer has seen the turn: an old box would read it as a wild pull.
  var box=canvas.getBoundingClientRect();if(box.width!==W||box.height!==H)fit();
  var p=pointer(e);
  if(dragging.reanchor){dragging.x=p[0];dragging.y=p[1];dragging.base=aim?{a:aim.a,p:aim.p}:null;dragging.reanchor=false;}
  var base=dragging.base?screenVector(Math.cos(dragging.base.a)*dragging.base.p*Math.min(W,H)*.3,Math.sin(dragging.base.a)*dragging.base.p*Math.min(W,H)*.3):[0,0];
  var dx=dragging.x-p[0]+base[0],dy=dragging.y-p[1]+base[1],len=Math.hypot(dx,dy),v=worldVector(dx,dy);
  aim={a:Math.atan2(v[1],v[0]),p:Math.min(1,len/(Math.min(W,H)*.3)),length:len};
  if(online&&performance.now()-dragging.sent>100){if(R.isHost)sendState();else R.send({t:'aim',round:roomRound,seq:round.seq,a:aim.a,p:aim.p});dragging.sent=performance.now();}
  updateHUD();askDraw();
}
canvas.addEventListener('pointerdown',function(e){if(!canAim()||dragging)return;var p=pointer(e);dragging={id:e.pointerId,x:p[0],y:p[1],sent:0,base:parkedAim&&aim?{a:aim.a,p:aim.p}:null};if(!parkedAim)aim=null;parkedAim=false;canvas.setPointerCapture(e.pointerId);});
canvas.addEventListener('pointermove',dragAim);
canvas.addEventListener('pointerup',function(e){
  if(!dragging||e.pointerId!==dragging.id)return;
  // A resize preserves the existing world-space aim until the finger next moves.
  if(!aim)dragAim(e);
  var shot=aim;dragging=null;aim=null;
  if(shot&&shot.length>=15&&canAim()) {
    if(authority())shoot(shot.a,shot.p,round.seq,round.players[round.turn].id);
    else R.send({t:'shot',round:roomRound,seq:round.seq,a:shot.a,p:shot.p});
  } else if(online) {if(R.isHost)sendState();else R.send({t:'aim',round:roomRound,seq:round.seq,a:0,p:0});}
  updateHUD();askDraw();
});
canvas.addEventListener('pointercancel',function(){
  dragging=null;
  if(aim&&canAim()&&performance.now()<rotationGrace){parkedAim=true;round.notice='Tähtäys säilyi · vedä säätääksesi, napauta lyödäksesi';}
  else {aim=null;parkedAim=false;}
  updateHUD();askDraw();
});
new ResizeObserver(fit).observe(canvas);
// The shared room library owns its pause screen; wake drawing when it resumes.
var wasPaused=false;
setInterval(function(){if(online&&round){var p=R.paused;if(p!==wasPaused){wasPaused=p;lastFrame=0;askDraw();}}},200);
fit();menu();
