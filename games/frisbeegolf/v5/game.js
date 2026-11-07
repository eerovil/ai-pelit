const $=id=>document.getElementById(id), KEY='ai-pelit:frisbeegolf:';
const R=window.AiPelitRooms;
// The swipe throw (v5) plays differently from the throw pad, so it keeps its own list.
window.AiPelitScores?.board('v5','Frisbeegolf v5+');
// First-person camera: yaw follows the aim, pitch is the player's look up or down, degrees.
let view={yaw:0,pitch:-5};
let round=null, online=false, roomRound='', roomHost='', aim={pitch:12,angle:0,disc:1,power:.6,curve:0}, drag=null, aimDrag=null;
let flight=null, preview=null, mapOpen=false, scene3d=null, lastFrame=0, frame=0, dirty=true, askName=false;
function load(k,d){try{const v=localStorage.getItem(KEY+k);return v===null?d:JSON.parse(v);}catch(e){return d;}}
function save(k,v){try{localStorage.setItem(KEY+k,JSON.stringify(v));}catch(e){}}
function sound(name,vol=.25){window.AiPelitAanet?.play(name,{vol});}
window.AiPelitAanet?.load(['suhahdus','puu','loiskis','metalli','onnistui','virhe']);
function relative(n){return n===0?'E':n>0?'+'+n:'−'+Math.abs(n);}
function current(){return round.players[round.turn];}
function hasTurn(){return !!(round&&round.phase==='aim'&&(!online||current().id===R.me));}
function myTurn(){return hasTurn()&&(!online||!R.paused);}
function fresh(players=[{id:'me',name:'Sinä'}]){
  return {hole:0,turn:0,seq:0,phase:'aim',time:0,shot:null,notice:'',rules:5,order:players.map((_,i)=>i),
    players:players.map(p=>({id:p.id,name:p.name,lie:[0,0],strokes:0,scores:[],done:false}))};
}
function resetAim(){
  if(!round)return;const h=HOLES[round.hole],p=current();
  const minimumDistance=2,landingDistance=distance(p.lie,h.basket);
  if(landingDistance<minimumDistance){
    // Preserve the approach side; a lie exactly at the basket falls back toward the tee.
    const dx=landingDistance>.001?p.lie[0]-h.basket[0]:-h.basket[0];
    const dz=landingDistance>.001?p.lie[1]-h.basket[1]:-h.basket[1];
    const length=Math.hypot(dx,dz);
    p.lie=[h.basket[0]+(length?dx/length:0)*minimumDistance,h.basket[1]+(length?dz/length:-1)*minimumDistance];
    round.notice='Heittopaikka vähintään 2 metrin päässä korista';
  }
  const dist=distance(p.lie,h.basket);
  const pitch=dist<10?Math.atan2(ground(h,...h.basket)+1-ground(h,...p.lie)-1.5,Math.max(.1,dist))*180/Math.PI:12;
  aim={pitch:clamp(pitch,-65,50),angle:Math.atan2(h.basket[0]-p.lie[0],h.basket[1]-p.lie[1]),disc:1,power:dist<10?clamp(.22+dist*.085,.25,1):.65,curve:0};
  view={yaw:aim.angle,pitch:-5};
  drag=aimDrag=null;mapOpen=false;refreshPreview();
}
function refreshPreview(){preview=null;dirty=true;askDraw();}
function newRound(){online=false;round=fresh();flight=null;resetAim();showPlay();keepRound();}
function resumeRound(){const r=load('kierros',null);if(!validSaved(r))return;online=false;round=r;flight=null;resetAim();if(round.phase==='hole')showCard();else showPlay();}
function validSaved(r){return r&&Number.isInteger(r.hole)&&r.hole>=0&&r.hole<9&&['aim','hole'].includes(r.phase)&&Array.isArray(r.players)&&r.players.length===1&&r.players[0].lie?.every(Number.isFinite)&&r.players[0].scores?.length===(r.phase==='hole'?r.hole+1:r.hole)&&Number.isFinite(r.players[0].strokes);}
function keepRound(){if(!round||online||round.phase==='end')return;
  // A reload during flight replays the uncounted throw, never loses or doubles a stroke.
  if(round.phase==='fly')return;
  save('kierros',round);
}
function menu(){keepRound();round=null;online=false;flight=preview=drag=aimDrag=null;mapOpen=false;
  $('menu').hidden=false;$('game').hidden=true;$('card').hidden=true;
  $('resume').hidden=!validSaved(load('kierros',null));
  const best=load('ennatys',null);$('best').textContent=best===null?'Ensimmäinen kierros odottaa':'Ennätys: '+relative(best)+' · '+(best+COURSE_PAR)+' heittoa';
  if(scene3d)buildHole(0);dirty=true;askDraw();
}
function startShot(input){
  if(!round||round.phase!=='aim')return false;
  if(!Number.isFinite(input.angle)||!Number.isFinite(input.power)||!Number.isFinite(input.curve)||!Number.isInteger(input.disc)||input.disc<0||input.disc>2||input.power<.015||input.power>1||Math.abs(input.curve)>1)return false;
  // A swipe throw carries its release point and velocity; a guest's message is checked before use.
  const numbers=(a,n,max)=>Array.isArray(a)&&a.length===n&&a.every(x=>Number.isFinite(x)&&Math.abs(x)<=max);
  const lie=current().lie,h=HOLES[round.hole];
  const swipe=numbers(input.velocity,3,40)&&Math.hypot(...input.velocity)<=40&&numbers(input.origin,3,1e4)
    &&Math.hypot(input.origin[0]-lie[0],input.origin[2]-lie[1])<=3&&Math.abs(input.origin[1]-ground(h,...lie)-1.5)<=3;
  const rotation=numbers(input.releaseRotation,4,1.01)?input.releaseRotation.slice():undefined;
  keepRound();round.shot={pitch:clamp(Number.isFinite(input.pitch)?input.pitch:12,-65,50),angle:input.angle,power:input.power,curve:input.curve,disc:input.disc,lie:lie.slice(),seed:12345+round.seq*7919,
    origin:swipe?input.origin.slice():undefined,velocity:swipe?input.velocity.slice():undefined,
    releaseScale:Number.isFinite(input.releaseScale)?clamp(input.releaseScale,.2,5):undefined,releaseRotation:rotation};
  round.phase='fly';round.time=0;round.seq++;round.notice='';current().strokes++;
  flight=fly(round.shot,HOLES[round.hole]);preview=null;drag=aimDrag=null;mapOpen=false;
  sound('suhahdus');renderUI();askDraw();if(online)sendState();return true;
}
function nextThrower(){
  const active=round.order.filter(i=>!round.players[i].done);
  // Everyone tees off before anyone takes their second throw; ties retain tee honours.
  const tees=active.filter(i=>round.players[i].strokes===0);if(tees.length)return tees[0];
  active.sort((a,b)=>distance(round.players[b].lie,HOLES[round.hole].basket)-distance(round.players[a].lie,HOLES[round.hole].basket));
  return active.length?active[0]:-1;
}
function recordHole(p){
  p.scores[round.hole]=p.strokes;p.done=true;
  if(!online||p.id===R.me){const b=load('vaylat',[]);b[round.hole]=b[round.hole]==null?p.strokes:Math.min(b[round.hole],p.strokes);save('vaylat',b);}
}
function settleShot(){
  const p=current(),f=flight;p.lie=f.lie.slice();p.strokes+=f.penalty;
  const notices={tree:'Puu!',rock:'Kallio!',water:'Lampeen – lisäheitto',ob:'OB – lisäheitto',rattle:'Ketjut sylkivät!',grass:'Seuraava heitto kiekon luota',basket:'Kiekko korissa!'};
  round.notice=notices[f.reason];round.event=f.reason;
  const sounds={tree:'puu',rock:'puu',water:'loiskis',ob:'virhe',rattle:'metalli',basket:'metalli'};if(sounds[f.reason])sound(sounds[f.reason]);
  if(f.holed){recordHole(p);sound('onnistui',p.strokes<HOLES[round.hole].par?.12:.08);}
  flight=null;round.shot=null;advance();
}
function advance(){
  round.seq++;const next=nextThrower();
  if(next<0){round.phase=round.hole===8?'end':'hole';if(round.phase==='end')finishRecord();showCard();}
  else{round.turn=next;round.phase='aim';resetAim();showPlay();}
  keepRound();if(online&&R.isHost){sendState();if(round.phase==='end'){R.deliver({t:'result',round:roomRound,state:round});R.endRound();}}
}
function nextHole(){
  if(!round||round.phase!=='hole'||(online&&!R.isHost))return;
  const last=round.hole;round.order.sort((a,b)=>round.players[a].scores[last]-round.players[b].scores[last]);
  round.hole++;round.seq++;round.players.forEach(p=>{p.lie=[0,0];p.strokes=0;p.done=false;});
  round.turn=round.order[0];round.phase='aim';round.notice='';round.event='';resetAim();showPlay();keepRound();if(online)sendState();
}
function finishRecord(){
  const p=round.players.find(p=>p.id===(online?R.me:'me'));if(!p||p.scores.length!==9)return;
  if(online&&!R.once(roomRound))return;
  const total=p.scores.reduce((a,b)=>a+b,0)-COURSE_PAR,best=load('ennatys',null);
  save('ennatys',best===null?total:Math.min(best,total));save('kierroksia',load('kierroksia',0)+1);
  if(!online)save('kierros',null);
  // A saved round begun before the swipe throw (rules 1-3) stays a personal result, never a v5 list entry.
  askName=round.rules===5&&window.AiPelitScores?.submit(total,true)===true;
}
function step(dt){
  if(!round||round.phase!=='fly'||document.hidden||(online&&R.paused))return;
  round.time+=Math.max(0,Math.min(dt,.05));
  if(flight&&round.time>=flight.duration){if(!online||R.isHost)settleShot();else round.time=flight.duration;}
  dirty=true;
}
function askDraw(){if(!frame&&!document.hidden)frame=requestAnimationFrame(tick);}
function tick(t){frame=0;if(drag?.type==='swipe'&&performance.now()-drag.lastMoved>160&&aim.power>0){aim.power=0;refreshPreview();renderPull();}const dt=lastFrame?Math.min((t-lastFrame)/1000,.05):0;lastFrame=t;step(dt);
  if(scene3d){drawScene(dt);dirty=false;}
  if(round?.phase==='fly'||drag||scene3d?.moving)askDraw();
}
document.addEventListener('visibilitychange',()=>{drag=aimDrag=null;if(document.hidden){keepRound();if(frame)cancelAnimationFrame(frame);frame=0;}else{lastFrame=0;refreshPreview();}});
window.addEventListener('pagehide',keepRound);
