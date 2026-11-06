function initScene(T){
  try{
    const renderer=new T.WebGLRenderer({canvas:$('scene'),antialias:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.shadowMap.enabled=true;
    renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.outputColorSpace=T.SRGBColorSpace;
    const scene=new T.Scene();scene.background=new T.Color('#b9d9d5');scene.fog=new T.Fog('#b9d9d5',80,230);
    scene.add(new T.HemisphereLight('#fff8da','#43674c',2.3));
    const sun=new T.DirectionalLight('#fff0c9',2.4);sun.position.set(-25,45,-15);sun.castShadow=true;
    sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-35;sun.shadow.camera.right=35;sun.shadow.camera.top=35;sun.shadow.camera.bottom=-35;sun.shadow.bias=-.001;scene.add(sun);scene.add(sun.target);
    const camera=new T.PerspectiveCamera(55,1,.1,350);
    scene3d={T,renderer,scene,camera,sun,hole:-1,group:null,ray:new T.Raycaster(),pointer:new T.Vector2(),
      position:new T.Vector3(),target:new T.Vector3(),moving:true,samples:0,elapsed:0,tuned:0,ghostKey:''};
    const observer=new ResizeObserver(()=>{const c=$('scene');renderer.setSize(c.clientWidth,c.clientHeight,false);camera.aspect=c.clientWidth/c.clientHeight;camera.updateProjectionMatrix();drag=null;dirty=true;askDraw();});observer.observe($('scene'));
    buildHole(round?round.hole:0);askDraw();
  }catch(e){$('error').hidden=false;}
}
function buildHole(index){
  if(!scene3d||scene3d.hole===index)return;
  const v=scene3d,{T,scene}=v,h=HOLES[index];
  if(v.group){scene.remove(v.group);v.group.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();}});}
  const group=new T.Group();scene.add(group);v.group=group;v.hole=index;v.ghostKey='';
  const mat=(colour,extra={})=>new T.MeshStandardMaterial({color:colour,roughness:.9,...extra});
  const add=(geo,material,x,y,z,parent=group)=>{const m=new T.Mesh(geo,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;};
  // A mown fairway winds through the rough; vertex colour avoids a network texture.
  const geo=new T.PlaneGeometry(180,h.length+170,64,100);geo.rotateX(-Math.PI/2);geo.translate(0,0,h.length/2);
  const pos=geo.attributes.position, colours=[];
  for(let i=0;i<pos.count;i++){
    const x=pos.getX(i),z=pos.getZ(i);pos.setY(i,ground(h,x,z));
    const centre=h.bend*Math.sin(clamp(z/h.length,0,1)*Math.PI),mown=Math.abs(x-centre)<8.5;
    const colour=new T.Color(mown?(Math.floor(z/5)%2?'#7eac65':'#89b36c'):'#527d48');
    colour.multiplyScalar(1+.035*Math.sin(x*2.1+z*1.7));colours.push(colour.r,colour.g,colour.b);
  }
  geo.setAttribute('color',new T.Float32BufferAttribute(colours,3));geo.computeVertexNormals();
  v.terrain=add(geo,mat('#ffffff',{vertexColors:true}),0,0,0);
  add(new T.BoxGeometry(2,.12,3),mat('#c8c6ad'),0,ground(h,0,0)-.025,0);
  const wood=mat('#6d5139'),leaf=mat('#355f43'),birch=mat('#dfdfc4');
  // Instances keep the whole forest inexpensive to draw on a phone.
  const trunks=new T.InstancedMesh(new T.CylinderGeometry(1,1,1,6),wood,h.trees.length);
  const crowns=new T.InstancedMesh(new T.ConeGeometry(1,1,7),leaf,h.trees.length*2);
  const dummy=new T.Object3D();let ci=0;
  h.trees.forEach((t,i)=>{
    const [x,z,r,height,kind]=t,y=ground(h,x,z);dummy.position.set(x,y+height/2,z);dummy.scale.set(r,height,r);dummy.updateMatrix();trunks.setMatrixAt(i,dummy.matrix);
    if(kind==='birch')trunks.setColorAt(i,new T.Color('#dedfc7'));else trunks.setColorAt(i,new T.Color('#72563b'));
    for(let j=0;j<2;j++){dummy.position.set(x,y+height*(.58+j*.19),z);dummy.scale.set(height*(kind==='birch'?.33:.28)*(1-j*.23),height*.63,height*.28*(1-j*.23));dummy.updateMatrix();crowns.setMatrixAt(ci++,dummy.matrix);crowns.setColorAt(ci-1,new T.Color(kind==='birch'?'#8eaa59':j?'#355e43':'#3c704c'));}
  });trunks.castShadow=crowns.castShadow=true;trunks.receiveShadow=true;group.add(trunks,crowns);
  for(const r of h.rocks){const rock=add(new T.DodecahedronGeometry(r[2],0),mat('#899285'),r[0],ground(h,r[0],r[1])-.3,r[1]);rock.scale.y=.7;}
  for(const w of h.water){const lake=add(new T.CircleGeometry(1,48),mat('#519eae',{metalness:.25,roughness:.25}),w.x,ground(h,w.x,w.z)+.08,w.z);lake.rotation.x=-Math.PI/2;lake.scale.set(w.rx,w.rz,1);}
  if(h.ob)for(const side of [-1,1])for(let z=-10;z<h.length+28;z+=8)add(new T.CylinderGeometry(.055,.055,.65,5),mat('#eae8d6'),side*h.ob,ground(h,side*h.ob,z)+.325,z);
  const basket=new T.Group(),[bx,bz]=h.basket,by=ground(h,bx,bz);basket.position.set(bx,by,bz);group.add(basket);
  const metal=mat('#c9d4c7',{metalness:.75,roughness:.35}),yellow=mat('#f1bf4a',{metalness:.3});
  add(new T.CylinderGeometry(.045,.045,1.8,8),metal,0,.9,0,basket);
  for(const [y,r,thick] of [[.5,.34,.025],[.72,.4,.025],[1.4,.4,.045]]){
    const ring=add(new T.TorusGeometry(r,thick,6,32),y>1?yellow:metal,0,y,0,basket);ring.rotation.x=Math.PI/2;
  }
  for(let i=0;i<16;i++){
    const a=i/16*Math.PI*2,x=Math.cos(a),z=Math.sin(a);
    const points=[new T.Vector3(x*.36,1.37,z*.36),new T.Vector3(x*.19,.85,z*.19),new T.Vector3(x*.1,.65,z*.1)];
    basket.add(new T.Line(new T.BufferGeometry().setFromPoints(points),new T.LineBasicMaterial({color:'#dde3d9'})));
    const bar=add(new T.CylinderGeometry(.008,.008,.23,4),metal,x*.34,.6,z*.34,basket);bar.rotation.z=x*.3;
  }
  add(new T.BoxGeometry(.6,.25,.015),yellow,.3,1.9,0,basket);
  v.basket=basket;
  v.disc=add(new T.CylinderGeometry(.13,.13,.025,24),mat('#f4ca72'),0,1,0);
  // A simple backhand figure gives immediate feedback while a throw is pulled back.
  const person=new T.Group();group.add(person);v.person=person;
  const shirt=mat('#f4d180'),pants=mat('#2c4f52'),skin=mat('#e4ad83');
  add(new T.CapsuleGeometry(.19,.37,3,8),shirt,0,1.03,0,person);
  add(new T.SphereGeometry(.15,12,8),skin,0,1.52,0,person);
  for(const x of [-.12,.12])add(new T.CylinderGeometry(.075,.06,.65,7),pants,x,.38,0,person);
  const arm=new T.Group();arm.position.set(.22,1.22,0);person.add(arm);v.arm=arm;
  const fore=add(new T.CylinderGeometry(.06,.06,.53,7),skin,.22,0,0,arm);fore.rotation.z=Math.PI/2;
  const shadow=add(new T.CircleGeometry(.5,24),new T.MeshBasicMaterial({color:'#193a2d',transparent:true,opacity:.18}),0,.02,0,person);shadow.rotation.x=-Math.PI/2;
  v.ghost=new T.Line(new T.BufferGeometry(),new T.LineBasicMaterial({color:'#fff3b4',transparent:true,opacity:.9}));group.add(v.ghost);
  v.endRing=add(new T.TorusGeometry(.6,.04,6,32),new T.MeshBasicMaterial({color:'#fff0b1'}),0,0,0);v.endRing.rotation.x=Math.PI/2;
  v.position.set(0,4,-8);v.target.set(0,1,20);v.camera.position.copy(v.position);v.moving=true;dirty=true;
}
function drawScene(dt){
  const v=scene3d,{T,camera,renderer}=v;buildHole(round?round.hole:0);
  const h=HOLES[v.hole],p=round?current():{lie:[0,0]},a=round?aim.angle:0;
  let eye,look;
  const flying=round?.phase==='fly'&&flight,disc=flying?flightPoint(flight,round.time):null;
  if(mapOpen){eye=new T.Vector3(0,h.length*.9+20,h.length*.5-5);look=new T.Vector3(0,0,h.length*.5);}
  else if(disc){const sa=round.shot.angle;eye=new T.Vector3(disc.x-Math.sin(sa)*6,disc.y+3.5,disc.z-Math.cos(sa)*6);look=new T.Vector3(disc.x,disc.y,disc.z+2);}
  else{const y=ground(h,...p.lie);eye=new T.Vector3(p.lie[0]-Math.sin(a)*10,y+5,p.lie[1]-Math.cos(a)*10);look=new T.Vector3(p.lie[0]+Math.sin(a)*9,y+.2,p.lie[1]+Math.cos(a)*9);}
  const blend=dt?1-Math.exp(-dt*7):1;v.position.lerp(eye,blend);v.target.lerp(look,blend);
  v.moving=v.position.distanceTo(eye)>.015||v.target.distanceTo(look)>.015;
  if(!v.moving){v.position.copy(eye);v.target.copy(look);}
  camera.position.copy(v.position);camera.lookAt(v.target);
  v.person.position.set(p.lie[0]-.5,ground(h,...p.lie),p.lie[1]-.2);v.person.rotation.y=a;
  v.person.visible=!mapOpen;v.arm.rotation.y=drag?-1.8*aim.power:disc?Math.max(0,.8-round.time)*2:.2;
  v.disc.visible=!!disc; if(disc){v.disc.position.set(disc.x,disc.y,disc.z);v.disc.rotation.set(disc.tilt,round.time*18,disc.tilt);v.disc.material.color.setHex(DISCS[round.shot.disc].colour);}
  v.ghost.visible=v.endRing.visible=!!(preview&&round?.phase==='aim');
  if(preview){const key=JSON.stringify([round.hole,round.seq,aim]);if(key!==v.ghostKey){v.ghostKey=key;
    v.ghost.geometry.dispose();v.ghost.geometry=new T.BufferGeometry().setFromPoints(preview.path.filter((_,i)=>i%3===0).map(q=>new T.Vector3(q.x,q.y+.02,q.z)));
    v.endRing.position.set(preview.lie[0],ground(h,...preview.lie)+.08,preview.lie[1]);}}
  v.sun.position.set(p.lie[0]-25,45,p.lie[1]-15);v.sun.target.position.set(...[p.lie[0],0,p.lie[1]]);
  if(round){const b=new T.Vector3(h.basket[0],ground(h,...h.basket)+2.3,h.basket[1]).project(camera),rect=$('scene').getBoundingClientRect();
    $('basketLabel').hidden=b.z>1||Math.abs(b.x)>.9||Math.abs(b.y)>.9||mapOpen;
    $('basketLabel').style.left=(b.x+1)*rect.width/2+'px';$('basketLabel').style.top=(1-b.y)*rect.height/2+'px';
    $('basketLabel').textContent='Kori · '+Math.round(distance(p.lie,h.basket))+' m';}
  renderer.render(v.scene,camera);tune(dt);
}
function groundAt(x,y){
  if(!scene3d)return null;const v=scene3d,r=$('scene').getBoundingClientRect();
  v.pointer.set((x-r.left)/r.width*2-1,-(y-r.top)/r.height*2+1);v.ray.setFromCamera(v.pointer,v.camera);
  const hits=v.ray.intersectObject(v.terrain);return hits.length?[hits[0].point.x,hits[0].point.z]:null;
}
function tune(dt){
  const v=scene3d;if(!dt||!round||round.phase!=='fly'||v.tuned>=2)return;
  v.samples++;v.elapsed+=dt;
  if(v.elapsed>2){if(v.samples/v.elapsed<40){if(!v.tuned)v.renderer.setPixelRatio(1);else v.renderer.shadowMap.enabled=false;v.tuned++;}else v.tuned=2;v.elapsed=v.samples=0;}
}
