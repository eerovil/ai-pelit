'use strict';
var R=window.AiPelitRooms, S=window.AiPelitAanet;
var round=null, online=false, roomRound=0, roomHost='', aim=null, dragging=null;
var colors=['#fff5d8','#f3b765','#8bc8ff','#e7a3d3','#b2e077','#c4b0ff'];
var raf=0,lastFrame=0,accumulator=0,lastSend=0,rollingSound=null,lastNoise=0;
var $=id=>document.getElementById(id);
var noticeTimer=0,lastNotice='',askName=false;
var PAR=HOLES.reduce((n,h)=>n+h.par,0);
function load(key,fallback) { try { var x=localStorage.getItem('ai-pelit:minigolf:'+key); return x===null?fallback:JSON.parse(x); } catch(e) { return fallback; } }
function save(key,v) { try { localStorage.setItem('ai-pelit:minigolf:'+key,JSON.stringify(v)); } catch(e) {} }
function clone(x) { return JSON.parse(JSON.stringify(x)); }
function total(p) { return p.scores.reduce((n,x)=>n+(x||0),0); }
function relative(n) { return n===0?'par':n>0?'+'+n:String(n).replace('-','−'); }
function sound(name,vol) { if(S) S.play(name,{vol:vol===undefined?.25:vol}); }
if(S) S.load(['puu','osuma','hiekka','loiskis','naksu','onnistui','rullaus']);
function stopSound() { if(rollingSound) rollingSound.stop(); rollingSound=null; }
function keepRound() { if(round&&!online) save('kierros',round); }
function mine() { return round&&(!online||round.players[round.turn].id===R.me); }
function authority() { return !online||R.isHost; }
function canAim() { return round&&round.phase==='aim'&&mine()&&(!online||!R.paused); }
function fresh(players) {
  return {hole:0,turn:0,seq:0,phase:'aim',time:0,shotTime:0,
    players:players.map(p=>({id:p.id,name:p.name,scores:[],ball:golfBall(HOLES[0].tee),strokes:0})),notice:'Reikä 1/9 · Suora · Par 2'};
}
function newRound() {
  online=false; roomRound=0; round=fresh([{id:'solo',name:'Sinä'}]);
  aim=dragging=null; accumulator=0; keepRound(); showPlay();
}
function validSave(s) {
  return s&&Number.isInteger(s.hole)&&s.hole>=0&&s.hole<9&&['aim','roll','hole','end'].includes(s.phase)
    &&s.players&&s.players.length===1&&s.players[0].ball&&Number.isFinite(s.players[0].ball.x)
    &&Array.isArray(s.players[0].scores)&&s.players[0].scores.every(n=>Number.isInteger(n)&&n>=1&&n<=7);
}
function resumeRound() {
  var s=load('kierros',null); if(!validSave(s)) return;
  online=false; round=s; aim=dragging=null; accumulator=0;
  if(round.phase==='end') { finishRecord(); showCard(); } else showPlay();
}
function menu() {
  stopSound(); if(R)R.extra(null); aim=dragging=null; round=null; online=false;
  $('menu').style.display='flex'; $('card').style.display='none';
  $('hud').classList.add('hidden'); $('bottom').classList.add('hidden'); $('notice').textContent='';
  var best=load('paras',null); $('best').textContent=Number.isFinite(best)?'Paras: '+best+' lyöntiä ('+relative(best-PAR)+')':'Radan par on '+PAR+'.';
  var s=load('kierros',null); $('resume').classList.toggle('hidden',!validSave(s)||s.phase==='end');
  if(validSave(s)) $('resume').textContent='Jatka kierrosta · reikä '+(s.hole+1);
  askDraw();
}
function showPlay() {
  $('menu').style.display='none'; $('card').style.display='none';
  $('hud').classList.remove('hidden'); $('bottom').classList.remove('hidden');
  updateHUD(); askDraw();
}
function updateHUD() {
  if(!round) return;
  var h=HOLES[round.hole],p=round.players[round.turn];
  $('hud').replaceChildren(); var strong=document.createElement('strong'); strong.textContent=h.name;
  $('hud').append(strong,document.createTextNode('Reikä '+(round.hole+1)+'/9 · Par '+h.par+' · Lyönnit '+p.strokes));
  if(online) {
    var who=document.createElement('div');who.id='who';
    round.players.forEach(function(q,i){
      var row=document.createElement('span'),dot=document.createElement('i'),name=document.createElement('b');
      row.className=i===round.turn?'on':'';dot.style.background=colors[i];name.textContent=q.name;row.append(dot,name);who.append(row);
    });
    $('hud').append(who);
  }
  $('hint').textContent=round.phase==='roll'?'Pallo vierii…':online?(mine()?'Sinun vuorosi · vedä ja päästä irti':p.name+' lyö'):'Vedä taaksepäin ja päästä irti';
  $('notice').textContent=round.notice||'';
  if(round.notice&&round.notice!==lastNotice){
    clearTimeout(noticeTimer);lastNotice=round.notice;var held=round;
    noticeTimer=setTimeout(function(){if(round===held){round.notice='';lastNotice='';$('notice').textContent='';sendState();}},1500);
  }
  $('power').firstElementChild.style.width=(aim?aim.p*100:0)+'%';
}
function sendState(to) { if(online&&R.isHost&&round) R.send({t:'state',round:roomRound,state:round,aim:aim},to); }
function finishRecord() {
  if(!round||round.phase!=='end') return;
  if(online&&!R.once(roomRound)) return;
  var p=online?round.players.find(p=>p.id===R.me):round.players[0]; if(!p) return;
  var score=total(p);
  if(online) {
    var records=load('kaverit',{rounds:0,best:null});
    save('kaverit',{rounds:(records.rounds||0)+1,best:records.best===null?score:Math.min(records.best,score)});
    return;
  }
  var best=load('paras',null);
  // Solo progress and room results are intentionally separate.
  if(best===null||score<best) save('paras',score);
  var holes=load('reiat',[]); if(!Array.isArray(holes)) holes=[];
  p.scores.forEach((n,i)=>{holes[i]=Number.isFinite(holes[i])?Math.min(holes[i],n):n;}); save('reiat',holes);
  // The first score asks for a nickname: put off until the card is under it (see showCard).
  if(window.AiPelitScores) askName=AiPelitScores.submit(score,true)===true;
}
function showCard() {
  stopSound(); $('card').style.display='flex'; $('menu').style.display='none';
  $('hud').classList.add('hidden'); $('bottom').classList.add('hidden'); $('notice').textContent='';
  var end=round.phase==='end';
  $('cardTag').textContent=end?'Yhdeksän reikää pelattu':'Reikä '+(round.hole+1)+'/9';
  $('cardTitle').textContent=end?'Kierros pelattu!':HOLES[round.hole].name;
  var mineP=round.players.find(p=>p.id===(online?R.me:'solo'))||round.players[0];
  var parSoFar=HOLES.slice(0,round.hole+1).reduce((n,h)=>n+h.par,0);
  $('summary').textContent=total(mineP)+' lyöntiä · '+relative(total(mineP)-parSoFar)+(end&&!online&&total(mineP)===load('paras',null)?' · Oma ennätys!':'');
  $('cardNames').textContent=online?round.players.map((p,i)=>(i+1)+': '+p.name).join(' · '):'';
  var table=$('scoreRows'); table.replaceChildren();
  var caption=document.createElement('caption'); caption.textContent=online?'Pelaajat numerojärjestyksessä':'Tuloskortti'; table.append(caption);
  var head=table.createTHead().insertRow();
  var bests=load('reiat',[]);if(!Array.isArray(bests))bests=[];
  var bestOf=i=>Number.isFinite(bests[i])?bests[i]:'–',extra=online?[]:['Ennätys'];
  ['Reikä','Par',...round.players.map((p,i)=>online?String(i+1):'Sinä'),...extra].forEach(s=>{var th=document.createElement('th');th.textContent=s;head.append(th);});
  var body=table.createTBody();
  HOLES.forEach((h,i)=>{var row=body.insertRow(); [String(i+1),h.par,...round.players.map(p=>p.scores[i]||'–'),...(online?[]:[bestOf(i)])].forEach(s=>row.insertCell().textContent=s);});
  var foot=table.createTFoot().insertRow(); ['Yht.',PAR,...round.players.map(total),...(online?[]:[HOLES.every((h,i)=>Number.isFinite(bests[i]))?HOLES.reduce((n,h,i)=>n+bests[i],0):'–'])].forEach(s=>foot.insertCell().textContent=s);
  if(online&&end) {
    var details=document.createElement('details'),label=document.createElement('summary');
    label.textContent='Tuloskortti · '+total(mineP)+' lyöntiä';details.append(label);
    var names=document.createElement('p');names.textContent=$('cardNames').textContent;details.append(names);
    var copy=table.cloneNode(true);copy.removeAttribute('id');copy.style.cssText='width:100%;text-align:center;font-size:13px';details.append(copy);
    R.extra(details);
  }
  $('next').textContent=end?(online?'Takaisin huoneeseen':'Pelaa uudestaan'):(authority()?'Seuraava reikä':'Odotetaan huoneen tekijää');
  $('next').disabled=!end&&!authority(); $('toMenu').classList.toggle('hidden',online||!end);
  $('board').replaceChildren();
  if(end&&window.AiPelitScores) AiPelitScores.list('minigolf').then(function(data){ if(!round||round.phase!=='end')return; $('board').replaceChildren(); (data.rows||[]).slice(0,10).forEach(row=>$('board').append(AiPelitScores.row('minigolf',row,false))); }).catch(function(){});
  if(askName){askName=false;AiPelitScores.prompt();}
  askDraw();
}
function nextHole() {
  if(!round||round.phase!=='hole'||!authority()) return;
  round.hole++; round.turn=0; round.seq++; round.phase='aim'; round.shotTime=0;
  round.players.forEach(p=>{p.strokes=0;p.ball=golfBall(HOLES[round.hole].tee);});
  round.notice='Reikä '+(round.hole+1)+'/9 · '+HOLES[round.hole].name+' · Par '+HOLES[round.hole].par;
  keepRound(); showPlay(); sendState();
}
function advance() {
  aim=dragging=null; round.seq++;
  if(round.players.every(p=>p.scores[round.hole]!==undefined)) {
    round.phase=round.hole===8?'end':'hole';
    if(round.phase==='end') {
      finishRecord(); keepRound();
      if(online) { R.deliver({t:'result',round:roomRound,state:round}); R.endRound(); }
    } else {round.holeTime=0;keepRound();}
    if(online||round.phase==='end')showCard();else {updateHUD();askDraw();}
    sendState(); return;
  }
  for(var i=1;i<=round.players.length;i++) { var k=(round.turn+i)%round.players.length;
    if(round.players[k].scores[round.hole]===undefined) {round.turn=k;break;}
  }
  round.phase='aim'; keepRound(); updateHUD(); sendState(); askDraw();
}
function settle() {
  var p=round.players[round.turn],b=p.ball;
  if(b.water) {
    p.strokes=Math.min(7,p.strokes+1); p.ball=golfBall(round.origin); round.notice='Veteen · yksi rangaistuslyönti'; sound('loiskis');
  } else if(b.holed) {
    p.scores[round.hole]=p.strokes;
    var d=p.strokes-HOLES[round.hole].par;
    round.notice=p.strokes===1?'Yhdellä reikään!':d===0?'Par!':d===-1?'Birdie!':d===1?'Bogi':relative(d);
    sound('naksu',.2); sound('onnistui',.2);
    // Per-hole progress is earned now, even if this round is never finished.
    if(!online) { var records=load('reiat',[]); if(!Array.isArray(records)) records=[];
      records[round.hole]=Math.min(records[round.hole]||7,p.strokes);save('reiat',records); }
  }
  if(p.scores[round.hole]===undefined&&p.strokes>=6) { p.scores[round.hole]=7; round.notice='Lyöntiraja · reiän tulos 7'; }
  stopSound(); advance();
}
function shoot(a,p,seq,id) {
  if(!round||round.phase!=='aim'||!authority()||(online&&R.paused)||seq!==round.seq||id!==round.players[round.turn].id) return false;
  if(!Number.isFinite(a)||!Number.isFinite(p)||p<=0||p>1) return false;
  var player=round.players[round.turn],b=player.ball;
  round.origin=[b.x,b.y]; player.strokes++; b.vx=Math.cos(a)*p*MAX_SPEED; b.vy=Math.sin(a)*p*MAX_SPEED;
  round.phase='roll'; round.shotTime=0; round.notice=''; aim=dragging=null;
  sound('puu'); keepRound(); updateHUD(); sendState(); askDraw(); return true;
}
function step(dt) {
  if(!round||!authority()||(online&&R.paused))return;
  if(round.phase==='hole'&&!online){round.holeTime=(round.holeTime||0)+dt;if(round.holeTime>=1.2)nextHole();return;}
  if(!['aim','roll'].includes(round.phase))return;
  accumulator+=dt;
  while(accumulator>=FIXED_DT) {
    accumulator-=FIXED_DT; round.time+=FIXED_DT;
    if(round.phase==='roll') {
      round.shotTime+=FIXED_DT;
      var b=round.players[round.turn].ball,e=golfStep(b,HOLES[round.hole],FIXED_DT,round.time);
      if(e&&round.time-lastNoise>.08) { if(e==='wall') sound('osuma',.16); if(e==='sand')sound('hiekka',.16);lastNoise=round.time; }
      if(round.shotTime>25) b.vx=b.vy=0;
      if(!b.vx&&!b.vy) {settle();break;}
    }
  }
}
// The host's own events play its sounds; a guest hears them from the state it is sent.
function hearState(was,now) {
  if(!was||was.hole!==now.hole) return;
  if(was.phase==='aim'&&now.phase==='roll') sound('puu');
  var a=was.players[was.turn],b=now.players[was.turn];
  if(a&&b&&b.ball.holed&&!a.ball.holed) {sound('naksu',.2);sound('onnistui',.2);}
  if(now.notice!==was.notice&&/^Veteen/.test(now.notice||'')) sound('loiskis');
}
function receive(m,from) {
  if(!online||!m||m.round!==roomRound) return;
  if(R.isHost) {
    if(!round) return;
    if(m.t==='shot') shoot(m.a,m.p,m.seq,from);
    if(m.t==='aim'&&round.phase==='aim'&&from===round.players[round.turn].id&&m.seq===round.seq&&Number.isFinite(m.a)&&Number.isFinite(m.p)) {
      aim={a:m.a,p:Math.max(0,Math.min(1,m.p))};sendState();updateHUD();askDraw();
    }
  } else if(from===roomHost&&(m.t==='state'||m.t==='result')&&m.state) {
    var ownAim=dragging&&mine()?aim:null;
    var was=round;round=clone(m.state);hearState(was,round); aim=ownAim&&mine()&&round.phase==='aim'?ownAim:m.aim||null; accumulator=0;
    if(round.phase!=='aim'||!mine())dragging=null;
    if(round.phase==='end') {finishRecord();showCard();}
    else if(round.phase==='hole') showCard(); else showPlay();
  }
}
if(R) {
  R.turns(id=>!!(round&&online&&round.phase==='aim'&&round.players[round.turn].id===id));
  R.on('start',function(s) {
    R.extra(null);online=true;roomRound=s.round;roomHost=R.hostId;round=null;aim=dragging=null;accumulator=0; stopSound();
    if(R.isHost) { round=fresh(s.players);showPlay();sendState(); }
    else { $('menu').style.display='none';$('card').style.display='none';$('notice').textContent='Odotetaan rataa…'; }

  });
  R.on('message',receive);
  R.on('hello',id=>sendState(id));
  R.on('skip',function(ids) {
    if(!online||!R.isHost||!round||round.phase!=='aim'||!ids.includes(round.players[round.turn].id))return;
    round.players[round.turn].scores[round.hole]=7;round.notice='Vuoro ohitettu · tulos 7';advance();
  });
  R.on('lobby',menu); R.on('menu',menu);
  R.on('leave',menu);
}
$('play').onclick=newRound; $('resume').onclick=resumeRound;
$('friends').onclick=()=>R.open(); $('scores').onclick=()=>AiPelitScores.open();
$('toMenu').onclick=menu;
$('next').onclick=function() {
  if(!round) return;
  if(round.phase==='hole') nextHole();
  else if(round.phase==='end') {if(online) R.backToRoom('Kierros pelattu','win');else newRound();}
};
document.addEventListener('visibilitychange',function(){
  aim=dragging=null; if(document.hidden){keepRound();stopSound();}else{lastFrame=0;askDraw();}
});
window.addEventListener('pagehide',keepRound);
