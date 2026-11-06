function showPlay(){
  $('menu').hidden=true;$('card').hidden=true;$('game').hidden=false;
  if(scene3d)buildHole(round.hole);renderUI();askDraw();
}
function renderUI(){
  if(!round)return;const h=HOLES[round.hole],p=current();
  $('holeLabel').textContent='VÄYLÄ '+(round.hole+1)+' / 9';$('holeName').textContent=h.name;
  const wind=Math.hypot(...h.wind);$('stats').textContent='Par '+h.par+' · '+h.length+' m · '+(wind?('Tuuli '+(h.wind[0]<0?'←':'→')+' '+wind.toFixed(1).replace('.',',')+' m/s'):'Tyyntä');
  $('turnLabel').textContent=round.phase==='fly'?'Kiekko lentää…':(hasTurn()?'Sinun heittosi':p.name+' heittää')+' · '+(p.strokes+1)+'. heitto';
  $('notice').textContent=round.phase==='fly'?'':round.notice||(round.hole===0?'Suuntaa vetämällä kentällä. Viiva näyttää lennon alun.':'');
  $('roster').replaceChildren();if(online)round.players.forEach((p,i)=>{
    const s=document.createElement('span');s.className=i===round.turn?'active':'';s.textContent=p.name+' · '+(p.done?relative(p.scores[round.hole]-h.par):p.strokes+' h');$('roster').append(s);
  });
  $('discs').replaceChildren();DISCS.forEach((d,i)=>{const b=document.createElement('button');b.textContent=d.name;b.className=i===aim.disc?'selected':'';b.disabled=!hasTurn();b.onclick=()=>{aim.disc=i;refreshPreview();renderUI();};$('discs').append(b);});
  $('throwPad').style.opacity=hasTurn()?'1':'.5';$('map').disabled=round.phase!=='aim';
  $('map').textContent=mapOpen?'↩ Heittopaikka':'🗺️ Kartta';renderPull();
}
function renderPull(){
  $('powerLabel').textContent=drag?Math.round(aim.power*100)+' % · noin '+Math.round(throwRange(HOLES[round.hole],current().lie,aim.disc,aim.power))+' m':'Vedä alas';
  $('curveLabel').textContent=drag?(aim.curve<-.15?'← Kaarre vasemmalle':aim.curve>.15?'Kaarre oikealle →':'Suoraan'):'Sivuttain kaartaa';
  $('discHandle').style.transform=drag?'translate('+aim.curve*65+'px,'+aim.power*pullLength()+'px)':'none';
}
function showCard(){
  $('game').hidden=true;$('menu').hidden=true;$('card').hidden=false;
  const h=HOLES[round.hole],end=round.phase==='end',p=round.players.find(p=>p.id===(online?R.me:'me'))||current();
  const total=p.scores.reduce((a,b)=>a+b,0),par=HOLES.slice(0,p.scores.length).reduce((a,h)=>a+h.par,0);
  $('cardEyebrow').textContent=end?'PUISTORATA · 9 VÄYLÄÄ':'VÄYLÄ '+(round.hole+1)+' · '+h.name;
  $('cardTitle').textContent=end?'Kierros valmis':holeResult(p.scores[round.hole],h.par);
  $('cardTotal').textContent=total+' heittoa · '+relative(total-par)+(end&&load('ennatys',null)===total-par?' · Ennätys!':'');
  $('scoreRows').replaceChildren();
  const rows=online?round.players.map(p=>[p.name,p.scores.reduce((a,b)=>a+b,0)+' h · '+relative(p.scores.reduce((a,b)=>a+b,0)-par)]):p.scores.map((n,i)=>[(i+1)+'. '+HOLES[i].name,n+' h · '+relative(n-HOLES[i].par)]);
  for(const [i,[label,value]] of rows.entries()){
    const row=document.createElement(online&&end?'summary':'div');row.className='row';
    for(const text of [online&&end?label+' ▾':label,value]){const s=document.createElement('span');s.textContent=text;row.append(s);}
    if(online&&end){
      const details=document.createElement('details');details.append(row);
      round.players[i].scores.forEach((n,k)=>{const line=document.createElement('div');line.textContent='Väylä '+(k+1)+': '+n+' heittoa ('+relative(n-HOLES[k].par)+')';line.style.cssText='padding:4px 0;color:#bfd4b5;font-size:11px';details.append(line);});
      $('scoreRows').append(details);
    }else $('scoreRows').append(row);
  }
  $('next').textContent=end?(online?'Takaisin huoneeseen':'Pelaa uudestaan'):(online&&!R.isHost?'Odotetaan seuraavaa väylää':'Seuraava väylä');
  $('next').disabled=!end&&online&&!R.isHost;$('toMenu').hidden=online;if(askName){askName=false;AiPelitScores.prompt();}askDraw();
}
function holeResult(n,par){if(n===1)return 'Hole in one!';const d=n-par;return d<=-2?'Eagle!':d===-1?'Birdie!':d===0?'Par':d===1?'Bogi':d===2?'Tuplabogi':relative(d);}
function pullLength(){return $('throwPad').clientHeight-49;}
$('throwPad').addEventListener('pointerdown',e=>{
  if(!myTurn()||drag||aimDrag)return;const r=$('throwPad').getBoundingClientRect();
  // Start at the disc, leaving the full drag range inside the screen.
  if(e.clientY>r.top+58)return;
  drag={id:e.pointerId,x:e.clientX,y:e.clientY};$('throwPad').setPointerCapture(e.pointerId);
  aim.power=0;aim.curve=0;refreshPreview();renderPull();
});
function movePull(e){if(!drag||e.pointerId!==drag.id)return;
  aim.power=clamp((e.clientY-drag.y)/pullLength(),0,1);aim.curve=clamp((e.clientX-drag.x)/65,-1,1);refreshPreview();renderPull();
}
$('throwPad').addEventListener('pointermove',movePull);
$('throwPad').addEventListener('pointerup',e=>{
  if(!drag||e.pointerId!==drag.id)return;movePull(e);drag=null;
  if(aim.power>=.04&&myTurn()){if(online&&!R.isHost){R.send({t:'shot',round:roomRound,seq:round.seq,...aim});}else startShot(aim);}
  renderPull();
});
function cancelDrag(){drag=null;renderPull();askDraw();}
$('throwPad').addEventListener('pointercancel',cancelDrag);
$('scene').addEventListener('pointerdown',e=>{
  if(!myTurn()||drag||aimDrag)return;
  aimDrag={id:e.pointerId,x:e.clientX,angle:aim.angle};$('scene').setPointerCapture(e.pointerId);
});
function moveAim(e){
  if(!aimDrag||e.pointerId!==aimDrag.id||!myTurn())return;
  // A screen-width drag turns half a circle; moving the camera cannot move the target under the finger.
  aim.angle=aimDrag.angle+(e.clientX-aimDrag.x)/$('scene').getBoundingClientRect().width*Math.PI;
  refreshPreview();
}
$('scene').addEventListener('pointermove',moveAim);
$('scene').addEventListener('pointerup',e=>{if(aimDrag?.id!==e.pointerId)return;moveAim(e);aimDrag=null;});
function cancelAim(e){if(aimDrag?.id===e.pointerId)aimDrag=null;}
$('scene').addEventListener('pointercancel',cancelAim);
$('scene').addEventListener('lostpointercapture',cancelAim);
$('map').onclick=()=>{if(!round||round.phase!=='aim')return;mapOpen=!mapOpen;renderUI();askDraw();};
$('play').onclick=newRound;$('resume').onclick=resumeRound;$('friends').onclick=()=>R.open();$('scores').onclick=()=>AiPelitScores.open();$('toMenu').onclick=menu;
$('next').onclick=()=>{if(round.phase==='hole')nextHole();else if(online)R.backToRoom('Kierros pelattu','win');else newRound();};
menu();
