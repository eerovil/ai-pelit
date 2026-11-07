function sendState(to){if(!online||!R.isHost||!round)return;R.send({t:'state',round:roomRound,state:round},to);}
function applyState(state){
  const previous=round,keep=previous&&previous.seq===state.seq&&myTurn();
  if(!keep)drag=aimDrag=null;
  round=state;
  if(previous&&round.seq>previous.seq){
    if(round.phase==='fly')sound('suhahdus');
    else if(previous.phase==='fly'){
      const hit={tree:'puu',rock:'puu',water:'loiskis',ob:'virhe',rattle:'metalli',basket:'metalli'}[round.event];
      if(hit)sound(hit);if(round.event==='basket')sound('onnistui',.08);
    }
  }
  const own=round.players.find(p=>p.id===R.me);if(own){const b=load('vaylat',[]);own.scores.forEach((n,i)=>{b[i]=b[i]==null?n:Math.min(b[i],n);});save('vaylat',b);}
  flight=round.phase==='fly'?fly(round.shot,HOLES[round.hole]):null;
  if(round.phase==='aim'&&!keep)resetAim();
  if(round.phase==='hole'||round.phase==='end'){if(round.phase==='end')finishRecord();showCard();}
  else showPlay();
}
function receive(m,from){
  if(!online||!m||m.round!==roomRound)return;
  if(R.isHost){
    if(m.t==='shot'&&round&&round.phase==='aim'&&!R.paused&&m.seq===round.seq&&from===current().id)startShot(m);
    return;
  }
  if(from!==roomHost)return;
  if((m.t==='state'||m.t==='result')&&m.state&&(!round||m.state.seq>=round.seq))applyState(m.state);
}
if(R){
  R.turns(id=>!!(online&&round&&round.phase==='aim'&&current().id===id));
  R.on('start',s=>{
    online=true;roomRound=s.round;roomHost=R.hostId;round=null;flight=drag=aimDrag=null;
    $('menu').hidden=$('card').hidden=true;
    if(R.isHost){round=fresh(s.players);resetAim();showPlay();sendState();}
    else{$('game').hidden=false;$('notice').textContent='Odotetaan rataa…';}
  });
  R.on('message',receive);R.on('hello',id=>sendState(id));
  R.on('skip',ids=>{
    if(!online||!R.isHost||!round||round.phase!=='aim'||!ids.includes(current().id))return;
    // The skipped player finishes this hole with par + 3, or their existing strokes if greater.
    current().strokes=Math.max(current().strokes,HOLES[round.hole].par+3);recordHole(current());round.notice='Vuoro ohitettu · '+current().name;advance();
  });
  R.on('lobby',menu);R.on('leave',menu);R.on('menu',menu);
}
