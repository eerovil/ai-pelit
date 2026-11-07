function showPlay(){
  $('menu').hidden=true;$('card').hidden=true;$('game').hidden=false;
  if(scene3d)buildHole(round.hole);renderUI();askDraw();
}
function renderUI(){
  if(!round)return;const h=HOLES[round.hole],p=current();
  $('holeLabel').textContent='VÄYLÄ '+(round.hole+1)+' / 9';$('holeName').textContent=h.name;
  const wind=Math.hypot(...h.wind);$('stats').textContent='Par '+h.par+' · '+h.length+' m · '+(wind?('Tuuli '+(h.wind[0]<0?'←':'→')+' '+wind.toFixed(1).replace('.',',')+' m/s'):'Tyyntä');
  $('turnLabel').textContent=round.phase==='fly'?'Kiekko lentää…':(hasTurn()?'Sinun heittosi':p.name+' heittää')+' · '+(p.strokes+1)+'. heitto';
  $('notice').textContent=round.phase==='fly'?'':round.notice||(round.hole===0?'Raahaa näkymää. Pyyhkäisy jatkuu kiekon lentona.':'');
  $('roster').replaceChildren();if(online)round.players.forEach((p,i)=>{
    const s=document.createElement('span');s.className=i===round.turn?'active':'';s.textContent=p.name+' · '+(p.done?relative(p.scores[round.hole]-h.par):p.strokes+' h');$('roster').append(s);
  });
  $('map').disabled=round.phase!=='aim';
  $('map').textContent=mapOpen?'↩ Heittopaikka':'🗺️ Kartta';renderPull();
}
function renderPull(){
  // While the disc flies there is nothing to swipe, so the throw hints step aside.
  if(round?.phase!=='aim'){$('powerLabel').textContent=$('curveLabel').textContent='';return;}
  $('powerLabel').textContent=drag?.type==='swipe'?Math.round(aim.power*100)+' % · pyyhkäisyn nopeus ja pituus':'Raahaa ruutua: katso ympärillesi';
  $('curveLabel').textContent=drag?.type==='swipe'?(Math.abs(aim.curve)<.05?'Kiekko suorassa':(aim.curve>0?'Kaarto ← · kallistus':'Kaarto → · kallistus')+' · '+Math.round(Math.abs(aim.curve)*45)+'°'):'Pyyhkäise kiekko ylös tai viistoon: heitto';
}
function showCard(){
  $('game').hidden=true;$('menu').hidden=true;$('card').hidden=false;
  const h=HOLES[round.hole],end=round.phase==='end',p=round.players.find(p=>p.id===(online?R.me:'me'))||current();
  const total=p.scores.reduce((a,b)=>a+b,0),par=HOLES.slice(0,p.scores.length).reduce((a,h)=>a+h.par,0);
  $('cardEyebrow').textContent=end?'PUISTORATA · 9 VÄYLÄÄ':'VÄYLÄ '+(round.hole+1)+' · '+h.name;
  $('cardTitle').textContent=end?'Kierros valmis':holeResult(p.scores[round.hole],h.par);
  $('cardTotal').textContent=total+' heittoa · '+relative(total-par)+(end&&load('ennatys',null)===total-par?' · Ennätys!':'');
  if(end&&round.rules!==5)$('cardTotal').textContent+=' · Vanha kierros, ei tuloslistalle';
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
// Drag the course to aim; swipe upward from the disc to throw.
function heldDiscPoint(rect){return {x:rect.left+rect.width*.5,y:rect.top+rect.height*.72};}
function heldDiscScreenPoint(rect){
  const rest=heldDiscPoint(rect),pulling=drag?.type==='swipe';
  return {
    x:rect.left+(pulling?clamp(rest.x-rect.left+drag.cx-drag.x,55,rect.width-55):rest.x-rect.left),
    y:rect.top+(pulling?clamp(rest.y-rect.top+drag.cy-drag.y,75,rect.height-60):rest.y-rect.top)
  };
}
function makeSwipeLaunch(){
  const v=scene3d;if(!v)return null;
  const rect=$('scene').getBoundingClientRect(),screen=heldDiscScreenPoint(rect),T=v.T;
  const forward=v.camera.getWorldDirection(new T.Vector3());
  const pivot=new T.Vector3(current().lie[0],ground(HOLES[round.hole],...current().lie)+1.5,current().lie[1]);
  const depth=Math.max(1,pivot.sub(v.camera.position).dot(forward));
  const ray=new T.Raycaster();
  ray.setFromCamera(new T.Vector2(2*(screen.x-rect.left)/rect.width-1,1-2*(screen.y-rect.top)/rect.height),v.camera);
  const origin=v.camera.position.clone().addScaledVector(ray.ray.direction,depth/ray.ray.direction.dot(forward));
  const right=new T.Vector3(1,0,0).applyQuaternion(v.camera.quaternion),up=new T.Vector3(0,1,0).applyQuaternion(v.camera.quaternion);
  const metresPerPixel=2*depth*Math.tan(v.camera.fov*Math.PI/360)/rect.height;
  const putting=distance(current().lie,HOLES[round.hole].basket)<10;
  const swipeScale=Math.min(1,rect.height*.0044/Math.max(.001,Math.hypot(drag.vx,drag.vy)));
  // Continue the recent finger motion from the visible release point; bank curves it later.
  const velocity=ray.ray.direction.clone().multiplyScalar(putting?1.8+aim.power*4:7+aim.power*20)
    .addScaledVector(right,drag.vx*swipeScale*800*metresPerPixel)
    .addScaledVector(up,-drag.vy*swipeScale*800*metresPerPixel);
  // Compress the high-power end without changing the release direction or short putts.
  if(!putting)velocity.multiplyScalar(1-.18*aim.power*aim.power);
  const speed=velocity.length(),yaw=Math.atan2(velocity.x,velocity.z);
  // A higher visible release allows a higher throw, relative to the camera gaze.
  const gazePitch=Math.asin(clamp(forward.y,-1,1));
  const rest=heldDiscPoint(rect);
  const releaseRise=clamp((rest.y-screen.y)/Math.max(1,rest.y-rect.top-75),0,1);
  const maxPitch=Math.min(85*Math.PI/180,gazePitch+(10+20*releaseRise)*Math.PI/180);
  const pitch=Math.min(maxPitch,Math.atan2(velocity.y,Math.hypot(velocity.x,velocity.z)));
  velocity.set(Math.sin(yaw)*Math.cos(pitch)*speed,Math.sin(pitch)*speed,Math.cos(yaw)*Math.cos(pitch)*speed);
  const rotation=v.camera.quaternion.clone().multiply(new T.Quaternion().setFromEuler(new T.Euler(.65,0,aim.curve*Math.PI/4)));
  return {origin:origin.toArray(),velocity:velocity.toArray(),
    angle:Math.atan2(velocity.x,velocity.z),pitch:Math.atan2(velocity.y,Math.hypot(velocity.x,velocity.z))*180/Math.PI,
    releaseScale:110/rect.height*depth*Math.tan(v.camera.fov*Math.PI/360)/.13,releaseRotation:rotation.toArray()};
}
$('scene').addEventListener('pointerdown',e=>{
  if(!round||!['aim','fly'].includes(round.phase)||mapOpen||drag)return;
  e.preventDefault();
  const rect=$('scene').getBoundingClientRect(),disc=heldDiscPoint(rect);
  // The disc is held only once the camera is back at the thrower's eyes after a flight.
  const pulling=myTurn()&&!scene3d?.moving&&Math.hypot((e.clientX-disc.x)/72,(e.clientY-disc.y)/55)<=1;
  drag={type:pulling?'swipe':'aim',id:e.pointerId,x:e.clientX,y:e.clientY,cx:e.clientX,cy:e.clientY,
    angle:view.yaw,pitch:view.pitch,power:aim.power,curve:aim.curve,
    samples:[{x:e.clientX,y:e.clientY,t:performance.now()}],lastMoved:performance.now(),
    fullSpeed:rect.height*.0028,fullLength:rect.height*.4};
  $('scene').setPointerCapture(e.pointerId);
  if(pulling){aim.curve=0;aim.power=0;}
  askDraw();renderPull();
});
function movePull(e){
  if(!drag||e.pointerId!==drag.id)return;
  const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
  drag.cx=e.clientX;drag.cy=e.clientY;
  if(drag.type==='aim'){
    const rect=$('scene').getBoundingClientRect();
    view.yaw=drag.angle-dx/rect.width*Math.PI;
    view.pitch=clamp(drag.pitch-dy/rect.height*90,-65,65);
    aim.angle=view.yaw;aim.pitch=view.pitch;
  }else{
    const now=performance.now();
    if(Math.hypot(e.clientX-drag.samples.at(-1).x,e.clientY-drag.samples.at(-1).y)>.5)drag.lastMoved=now;
    drag.samples.push({x:e.clientX,y:e.clientY,t:now});
    while(drag.samples.length>2&&drag.samples[1].t<now-120)drag.samples.shift();
    const first=drag.samples[0],dt=Math.max(16,now-first.t);
    drag.vx=(e.clientX-first.x)/dt;drag.vy=(e.clientY-first.y)/dt;
    const speed=drag.vy<0?Math.hypot(drag.vx,drag.vy):0;
    // Power needs both a fast flick and a long swipe: full power takes 40% of the screen height.
    const lengthPower=clamp(Math.max(0,-dy)/drag.fullLength,0,1);
    aim.power=now-drag.lastMoved>160?0:Math.min(lengthPower,Math.pow(clamp(speed/drag.fullSpeed,0,1),1.25));
    const putting=distance(current().lie,HOLES[round.hole].basket)<10;
    const sideways=putting?Math.sign(dx)*Math.max(0,Math.abs(dx)-3):dx;
    aim.curve=dy<0?clamp(Math.atan2(sideways,-dy)/(Math.PI/6),-1,1):0;
  }
  askDraw();renderPull();
}
$('scene').addEventListener('pointermove',movePull);
$('scene').addEventListener('pointerup',e=>{
  if(!drag||e.pointerId!==drag.id)return;
  movePull(e);
  const throwing=drag.type==='swipe'&&drag.y-e.clientY>=24&&aim.power>=.06&&myTurn();
  const launch=throwing?makeSwipeLaunch():null;
  if(drag.type==='swipe'&&!launch){aim.power=drag.power;aim.curve=drag.curve;}
  drag=null;
  if(launch){
    // A guest's throw goes to the host, which runs the round; alone or as host it starts here.
    if(online&&!R.isHost)R.send({t:'shot',round:roomRound,seq:round.seq,...aim,...launch});
    else startShot({...aim,...launch});
  }else askDraw();
  renderPull();
});
function cancelDrag(e){
  if(drag?.id!==e.pointerId)return;
  if(drag.type==='swipe'){aim.power=drag.power;aim.curve=drag.curve;}
  drag=null;askDraw();renderPull();
}
$('scene').addEventListener('pointercancel',cancelDrag);
$('scene').addEventListener('lostpointercapture',cancelDrag);
$('map').onclick=()=>{if(!round||round.phase!=='aim')return;mapOpen=!mapOpen;renderUI();askDraw();};
$('play').onclick=newRound;$('resume').onclick=resumeRound;$('friends').onclick=()=>R.open();$('scores').onclick=()=>AiPelitScores.open();$('toMenu').onclick=menu;
$('next').onclick=()=>{if(round.phase==='hole')nextHole();else if(online)R.backToRoom('Kierros pelattu','win');else newRound();};
menu();
