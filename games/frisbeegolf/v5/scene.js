function initScene(T){
  try{
    const renderer=new T.WebGLRenderer({canvas:$('scene'),antialias:true});
    renderer.setPixelRatio(Math.min(devicePixelRatio,1.6));renderer.shadowMap.enabled=true;
    renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.outputColorSpace=T.SRGBColorSpace;
    renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.08;
    const scene=new T.Scene();scene.background=new T.Color('#cfe4dc');scene.fog=new T.Fog('#cfe4dc',70,220);
    scene.add(new T.HemisphereLight('#fff6dc','#3f6446',2.1));
    const sun=new T.DirectionalLight('#ffe9bd',2.8);sun.position.set(-25,45,-15);sun.castShadow=true;
    sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-35;sun.shadow.camera.right=35;sun.shadow.camera.top=35;sun.shadow.camera.bottom=-35;sun.shadow.bias=-.001;sun.shadow.normalBias=.03;scene.add(sun);scene.add(sun.target);
    const camera=new T.PerspectiveCamera(55,1,.1,350);scene.add(camera);
    // Camera-space held disc follows the pointer directly in the course view.
    const heldFace=new T.MeshBasicMaterial({color:'#f4ca72',depthTest:false,fog:false});
    const heldRim=new T.MeshBasicMaterial({color:'#aa782f',depthTest:false,fog:false});
    const heldDisc=new T.Mesh(new T.CylinderGeometry(1,1,.12,48),[heldRim,heldFace,heldFace]);
    heldDisc.renderOrder=50;heldDisc.frustumCulled=false;camera.add(heldDisc);
    const stamp=new T.Mesh(new T.RingGeometry(.55,.59,40),new T.MeshBasicMaterial({color:'#fff2c0',side:T.DoubleSide,depthTest:false,fog:false}));
    stamp.rotation.x=-Math.PI/2;stamp.position.y=.065;stamp.renderOrder=51;heldDisc.add(stamp);
    const sky=makeSky(T);scene.add(sky);
    scene3d={T,renderer,scene,camera,sun,sky,heldDisc,heldFace,heldRim,hole:-1,group:null,
      position:new T.Vector3(),target:new T.Vector3(),moving:true,samples:0,elapsed:0,tuned:0,ghostKey:''};
    const observer=new ResizeObserver(()=>{const c=$('scene');renderer.setSize(c.clientWidth,c.clientHeight,false);camera.aspect=c.clientWidth/c.clientHeight;camera.updateProjectionMatrix();drag=aimDrag=null;askDraw();});observer.observe($('scene'));
    buildHole(round?round.hole:0);askDraw();
  }catch(e){$('error').hidden=false;}
}
// A deterministic pseudo-random number, so the scenery is the same on every phone and reload.
function noise(n){const x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x);}
// A sky dome that moves with the camera: blue overhead, pale at the treeline, a few soft clouds.
function makeSky(T){
  const sky=new T.Group(),geo=new T.SphereGeometry(300,24,14),pos=geo.attributes.position,colours=[];
  const top=new T.Color('#5e9fd0'),low=new T.Color('#cfe4dc');
  for(let i=0;i<pos.count;i++){const c=low.clone().lerp(top,clamp(pos.getY(i)/180,0,1)**.7);colours.push(c.r,c.g,c.b);}
  geo.setAttribute('color',new T.Float32BufferAttribute(colours,3));
  sky.add(new T.Mesh(geo,new T.MeshBasicMaterial({vertexColors:true,side:T.BackSide,fog:false,depthWrite:false})));
  const puffs=new T.InstancedMesh(new T.IcosahedronGeometry(1,1),new T.MeshBasicMaterial({color:'#ffffff',fog:false,transparent:true,opacity:.86,depthWrite:false}),60);
  const d=new T.Object3D();
  for(let i=0;i<60;i++){
    const cloud=Math.floor(i/6),a=cloud*.79+noise(cloud)*.4,r=210,part=i%6;
    d.position.set(Math.sin(a)*r+(part-2.5)*9,95+noise(cloud+40)*45+noise(i+9)*5,Math.cos(a)*r+noise(i)*8);
    const s=9+noise(i+3)*8;d.scale.set(s*1.4,s*.55,s);d.updateMatrix();puffs.setMatrixAt(i,d.matrix);
  }
  sky.add(puffs);sky.renderOrder=-1;return sky;
}
// A flat tape along a path: WebGL lines are one pixel thin on a phone, a tape keeps its width.
function tape(T,points,width,colour,alpha0,alpha1){
  const n=points.length,pos=new Float32Array(n*6),col=new Float32Array(n*8),index=[],c=new T.Color(colour);
  points.forEach((p,i)=>{
    const a=points[Math.max(0,i-1)],b=points[Math.min(n-1,i+1)],dx=b.x-a.x,dz=b.z-a.z,l=Math.hypot(dx,dz)||1;
    const nx=-dz/l*width/2,nz=dx/l*width/2,alpha=alpha0+(alpha1-alpha0)*(n>1?i/(n-1):0);
    pos.set([p.x+nx,p.y,p.z+nz,p.x-nx,p.y,p.z-nz],i*6);col.set([c.r,c.g,c.b,alpha,c.r,c.g,c.b,alpha],i*8);
    if(i)index.push(2*i-2,2*i-1,2*i,2*i-1,2*i+1,2*i);
  });
  const geo=new T.BufferGeometry();geo.setAttribute('position',new T.BufferAttribute(pos,3));
  geo.setAttribute('color',new T.BufferAttribute(col,4));geo.setIndex(index);return geo;
}
function buildHole(index){
  if(!scene3d||scene3d.hole===index)return;
  const v=scene3d,{T,scene}=v,h=HOLES[index];
  if(v.group){scene.remove(v.group);v.group.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material]){m.map?.dispose();m.dispose();}}});}
  const group=new T.Group();scene.add(group);v.group=group;v.hole=index;v.ghostKey='';
  const mat=(colour,extra={})=>new T.MeshStandardMaterial({color:colour,roughness:.9,...extra});
  const add=(geo,material,x,y,z,parent=group)=>{const m=new T.Mesh(geo,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m;};
  const fairway=z=>h.bend*Math.sin(clamp(z/h.length,0,1)*Math.PI);
  // A mown fairway winds through the rough; vertex colour avoids a network texture.
  const geo=new T.PlaneGeometry(180,h.length+170,72,110);geo.rotateX(-Math.PI/2);geo.translate(0,0,h.length/2);
  const pos=geo.attributes.position, colours=[];
  const stripeA=new T.Color('#86b46a'),stripeB=new T.Color('#93bd72'),rough=new T.Color('#5a8549'),deep=new T.Color('#46703e');
  for(let i=0;i<pos.count;i++){
    const x=pos.getX(i),z=pos.getZ(i);pos.setY(i,ground(h,x,z));
    const off=Math.abs(x-fairway(z)),edge=clamp((off-7.5)/3,0,1);
    const colour=(Math.floor(z/5)%2?stripeA:stripeB).clone().lerp(rough,edge).lerp(deep,clamp((off-30)/25,0,1)*.8);
    colour.multiplyScalar(1+.05*Math.sin(x*1.3+z*.9)*Math.sin(z*.31-x*.47));colours.push(colour.r,colour.g,colour.b);
  }
  geo.setAttribute('color',new T.Float32BufferAttribute(colours,3));geo.computeVertexNormals();
  v.terrain=add(geo,mat('#ffffff',{vertexColors:true}),0,0,0);v.terrain.castShadow=false;
  // The tee: a stone pad and a sign with the hole's number and par.
  add(new T.BoxGeometry(2,.14,3),mat('#cfcab0'),0,ground(h,0,0)-.02,0);
  const sign=document.createElement('canvas');sign.width=128;sign.height=96;const sc=sign.getContext('2d');
  sc.fillStyle='#24493b';sc.fillRect(0,0,128,96);sc.fillStyle='#f4ca72';sc.font='bold 54px system-ui,sans-serif';sc.textAlign='center';
  sc.fillText(String(index+1),64,58);sc.fillStyle='#f6f5df';sc.font='bold 20px system-ui,sans-serif';sc.fillText('PAR '+h.par,64,86);
  const board=add(new T.BoxGeometry(.9,.68,.05),[mat('#24493b'),mat('#24493b'),mat('#24493b'),mat('#24493b'),new T.MeshStandardMaterial({map:new T.CanvasTexture(sign),roughness:.8}),mat('#24493b')],1.9,ground(h,1.9,-1.4)+1.15,-1.4);
  board.material[4].map.colorSpace=T.SRGBColorSpace;board.rotation.y=Math.PI+.35;
  add(new T.CylinderGeometry(.04,.04,.85,6),mat('#6d5139'),1.9,ground(h,1.9,-1.4)+.42,-1.4);
  // Instances keep the whole forest inexpensive to draw on a phone.
  const spruces=h.trees.filter(t=>t[4]==='spruce'),birches=h.trees.filter(t=>t[4]==='birch');
  // A ring of scenery spruces outside the course hides the edge of the world; they are only drawn.
  const backdrop=[];
  for(let z=-60;z<h.length+80;z+=5.5)for(const side of [-1,1])for(let row=0;row<2;row++){
    const n=z*3.1+side*7+row*13;backdrop.push([fairway(z)+side*(46+row*12+noise(n)*10),z+noise(n+1)*4,0,9+noise(n+2)*7]);
  }
  for(let x=-40;x<=40;x+=6)for(const z of [-24-noise(x)*8,h.length+34+noise(x+5)*8])backdrop.push([x+noise(x+z)*3,z,0,9+noise(x*z)*6]);
  const trunkGeo=new T.CylinderGeometry(.75,1,1,7);
  const trunks=new T.InstancedMesh(trunkGeo,mat('#ffffff'),h.trees.length);
  const cones=new T.InstancedMesh(new T.ConeGeometry(1,1,8),mat('#ffffff',{flatShading:true}),(spruces.length+backdrop.length)*3);
  const blobs=new T.InstancedMesh(new T.IcosahedronGeometry(1,1),mat('#ffffff',{flatShading:true}),birches.length*3);
  const dummy=new T.Object3D(),colour=new T.Color();let ci=0,bi=0;
  h.trees.forEach((t,i)=>{
    const [x,z,r,height,kind]=t,y=ground(h,x,z),birch=kind==='birch';
    dummy.rotation.set(0,0,0);dummy.position.set(x,y+height*(birch?.42:.25),z);dummy.scale.set(r,height*(birch?.84:.5),r);dummy.updateMatrix();trunks.setMatrixAt(i,dummy.matrix);
    trunks.setColorAt(i,colour.set(birch?'#e6e3d2':'#6b4f37'));
  });
  // A spruce is three stacked cones; a birch two or three rounded leafy clumps.
  const spruce=(x,z,height,n)=>{
    const y=ground(h,x,z),wide=height*(.27+noise(n)*.05);
    for(let j=0;j<3;j++){
      dummy.rotation.set(0,noise(n+j)*3,0);dummy.position.set(x,y+height*(.36+j*.21),z);
      dummy.scale.set(wide*(1-j*.26),height*(.46-j*.07),wide*(1-j*.26));dummy.updateMatrix();
      cones.setMatrixAt(ci,dummy.matrix);cones.setColorAt(ci++,colour.set(j===2?'#3d7350':'#2f6043').multiplyScalar(.9+noise(n+5)*.2));
    }
  };
  spruces.forEach((t,i)=>spruce(t[0],t[1],t[3],i*3.7+index));
  backdrop.forEach((t,i)=>spruce(t[0],t[1],t[3],i*1.3+50));
  birches.forEach((t,i)=>{
    const [x,z,,height]=t,y=ground(h,x,z);
    for(let j=0;j<3;j++){
      const n=i*5+j+index,s=height*(.2-j*.035);
      dummy.rotation.set(noise(n)*2,noise(n+1)*2,0);dummy.position.set(x+(noise(n+2)-.5)*height*.18,y+height*(.7+j*.13),z+(noise(n+3)-.5)*height*.18);
      dummy.scale.set(s*1.05,s*1.15,s);dummy.updateMatrix();blobs.setMatrixAt(bi,dummy.matrix);
      blobs.setColorAt(bi++,colour.set(j===2?'#a5c062':'#86a94f').multiplyScalar(.9+noise(n+4)*.2));
    }
  });
  trunks.castShadow=cones.castShadow=blobs.castShadow=true;trunks.receiveShadow=cones.receiveShadow=blobs.receiveShadow=true;group.add(trunks,cones,blobs);
  // Grass tufts and meadow flowers in the rough; small and shadowless, so they cost little.
  const tufts=new T.InstancedMesh(new T.ConeGeometry(.12,.35,4),mat('#ffffff',{flatShading:true}),420);
  const flowers=new T.InstancedMesh(new T.IcosahedronGeometry(.07,0),mat('#ffffff',{roughness:.6}),160);
  const flowerColours=['#fff6e8','#f6d24c','#c58fd6','#f3a0b5'];
  let tuftCount=0,flowerCount=0;
  for(let i=0;i<420;i++){
    const z=-10+noise(i*2.3+index)*(h.length+30),side=noise(i*1.7)<.5?-1:1,x=fairway(z)+side*(9.5+noise(i*4.1)*28);
    if(hazard(h,x,z)==='water')continue;
    dummy.rotation.set(0,noise(i)*3,(noise(i+8)-.5)*.4);dummy.position.set(x,ground(h,x,z)+.12,z);const s=.7+noise(i+2)*.8;dummy.scale.set(s,s,s);dummy.updateMatrix();
    tufts.setMatrixAt(tuftCount,dummy.matrix);tufts.setColorAt(tuftCount++,colour.set(noise(i+6)<.5?'#4f7f3f':'#6d9748'));
    if(i<160){dummy.rotation.set(0,0,0);dummy.position.set(x+.4,ground(h,x+.4,z)+.22,z+.3);dummy.scale.set(1,1,1);dummy.updateMatrix();
      flowers.setMatrixAt(flowerCount,dummy.matrix);flowers.setColorAt(flowerCount++,colour.set(flowerColours[i%4]));}
  }
  tufts.count=tuftCount;flowers.count=flowerCount;group.add(tufts,flowers);
  for(const r of h.rocks){
    const rock=add(new T.DodecahedronGeometry(r[2],1),mat('#8b9488',{flatShading:true}),r[0],ground(h,r[0],r[1])-.3,r[1]);rock.scale.y=.7;
    const p=rock.geometry.attributes.position;for(let i=0;i<p.count;i++)p.setXYZ(i,p.getX(i)*(1+(noise(i)-.5)*.12),p.getY(i)*(1+(noise(i+3)-.5)*.12),p.getZ(i));rock.geometry.computeVertexNormals();
    for(let k=0;k<3;k++)add(new T.DodecahedronGeometry(.35+noise(k)*.3,0),mat('#7c867a',{flatShading:true}),r[0]+(k-1)*r[2]*.9,ground(h,r[0],r[1])+.05,r[1]+r[2]*(.6+noise(k+1)*.4));
  }
  for(const w of h.water){
    // A sandy shore, a darker deep middle and a glossy surface read as a pond from any angle.
    const y=ground(h,w.x,w.z);
    const shore=add(new T.CircleGeometry(1,48),mat('#c9b98b'),w.x,y+.05,w.z);shore.rotation.x=-Math.PI/2;shore.scale.set(w.rx+1.2,w.rz+1.2,1);shore.castShadow=false;
    const lake=add(new T.CircleGeometry(1,48),mat('#4c95a8',{metalness:.3,roughness:.15}),w.x,y+.08,w.z);lake.rotation.x=-Math.PI/2;lake.scale.set(w.rx,w.rz,1);lake.castShadow=false;
    const deepWater=add(new T.CircleGeometry(1,40),mat('#2f6f86',{metalness:.3,roughness:.15,transparent:true,opacity:.7}),w.x,y+.09,w.z);deepWater.rotation.x=-Math.PI/2;deepWater.scale.set(w.rx*.6,w.rz*.6,1);deepWater.castShadow=false;
    const reeds=new T.InstancedMesh(new T.CylinderGeometry(.02,.03,1,4),mat('#7b8b45'),40);
    for(let i=0;i<40;i++){const a=noise(i+w.x)*Math.PI*2,x=w.x+Math.sin(a)*w.rx*(.93+noise(i)*.1),z=w.z+Math.cos(a)*w.rz*(.93+noise(i+1)*.1);
      dummy.rotation.set((noise(i+2)-.5)*.3,0,(noise(i+3)-.5)*.3);dummy.position.set(x,y+.5,z);dummy.scale.set(1,.8+noise(i+4)*.6,1);dummy.updateMatrix();reeds.setMatrixAt(i,dummy.matrix);}
    group.add(reeds);
  }
  if(h.ob)for(const side of [-1,1])for(let z=-10;z<h.length+28;z+=8){
    add(new T.CylinderGeometry(.055,.055,.65,5),mat('#eae8d6'),side*h.ob,ground(h,side*h.ob,z)+.325,z);
    add(new T.CylinderGeometry(.06,.06,.12,5),mat('#d9534f'),side*h.ob,ground(h,side*h.ob,z)+.6,z);
  }
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
  const pad=add(new T.CylinderGeometry(1.1,1.1,.06,24),mat('#9a9580'),0,.01,0,basket);pad.castShadow=false;
  v.basket=basket;
  v.disc=add(new T.CylinderGeometry(.13,.13,.025,24),mat('#f4ca72'),0,1,0);
  // A soft blob under the flying disc shows its height, also far from the sun's shadow area.
  v.discShadow=new T.Mesh(new T.CircleGeometry(.2,20),new T.MeshBasicMaterial({color:'#12301f',transparent:true,opacity:.35,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2}));
  v.discShadow.rotation.x=-Math.PI/2;group.add(v.discShadow);
  v.position.set(0,4,-8);v.target.set(0,1,20);v.camera.position.copy(v.position);v.moving=true;
}
function drawScene(dt){
  const v=scene3d,{T,camera,renderer}=v;buildHole(round?round.hole:0);
  const h=HOLES[v.hole],p=round?current():{lie:[0,0]},a=round?aim.angle:0;
  let eye,look;
  const flying=round?.phase==='fly'&&flight,disc=flying?flightPoint(flight,round.time):null;
  if(mapOpen){eye=new T.Vector3(0,h.length*.9+20,h.length*.5-5);look=new T.Vector3(0,0,h.length*.5);}
  else if(disc){
    // Chase camera: stay behind the disc along its travel direction and look at it.
    // Dragging during the flight still orbits it, relative to the view at release.
    if(v.chaseSeq!==round.seq){v.chaseSeq=round.seq;v.chaseYaw0=view.yaw;}
    const before=flightPoint(flight,Math.max(0,round.time-.15));
    const dx=disc.x-before.x,dz=disc.z-before.z;
    const travel=Math.hypot(dx,dz)>.05?Math.atan2(dx,dz):v.chaseYaw0;
    const yaw=travel+view.yaw-v.chaseYaw0,gy=ground(h,disc.x,disc.z);
    eye=new T.Vector3(disc.x-Math.sin(yaw)*6,Math.max(disc.y+1.6,gy+1.2),disc.z-Math.cos(yaw)*6);
    look=new T.Vector3(disc.x,disc.y,disc.z);
  }
  else{
    const yaw=view.yaw,pitch=view.pitch*Math.PI/180,groundY=ground(h,...p.lie);
    eye=new T.Vector3(p.lie[0],groundY+1.5,p.lie[1]);
    look=eye.clone().add(new T.Vector3(Math.sin(yaw)*Math.cos(pitch)*10,Math.sin(pitch)*10,Math.cos(yaw)*Math.cos(pitch)*10));
  }
  // Follow smoothly in flight and when returning to the thrower; aiming drags stay direct.
  const blend=drag?.type==='aim'||!dt?1:1-Math.exp(-dt*(disc?6:8));
  v.position.lerp(eye,blend);v.target.lerp(look,blend);
  v.moving=v.position.distanceTo(eye)>.015||v.target.distanceTo(look)>.015;
  if(!v.moving){v.position.copy(eye);v.target.copy(look);}
  camera.position.copy(v.position);camera.lookAt(v.target);camera.updateMatrixWorld();v.sky.position.copy(v.position);
  v.disc.visible=v.discShadow.visible=!!disc; if(disc){v.disc.position.set(disc.x,disc.y,disc.z);v.disc.rotation.set(disc.tilt,round.time*18,disc.tilt);
    const releaseBlend=Math.max(0,1-round.time/.22);
    v.disc.scale.setScalar(1+((round.shot.releaseScale??1)-1)*releaseBlend);
    if(round.shot.releaseRotation){
      // Preserve the visible release bank. Spin about the disc normal, rather than
      // blending into world-axis Euler rotations that reverse the bank on screen.
      v.disc.quaternion.fromArray(round.shot.releaseRotation);
      v.disc.rotateZ(disc.tilt-flight.path[0].tilt);
      v.disc.rotateY(round.time*18);
    }v.disc.material.color.setHex(DISCS[round.shot.disc].colour);
    const gy=ground(h,disc.x,disc.z),high=Math.max(0,disc.y-gy);v.discShadow.position.set(disc.x,gy+.07,disc.z);v.discShadow.scale.setScalar(1+high*.12);v.discShadow.material.opacity=.4/(1+high*.25);}
  // The sun's shadow area follows what the camera looks at, so the flight keeps its shadows.
  v.sun.position.set(v.target.x-25,v.target.y+45,v.target.z-15);v.sun.target.position.copy(v.target);
  if(round){const b=new T.Vector3(h.basket[0],ground(h,...h.basket)+2.3,h.basket[1]).project(camera),rect=$('scene').getBoundingClientRect();
    $('basketLabel').hidden=b.z>1||Math.abs(b.x)>.9||Math.abs(b.y)>.9||mapOpen;
    $('basketLabel').style.left=(b.x+1)*rect.width/2+'px';$('basketLabel').style.top=(1-b.y)*rect.height/2+'px';
    $('basketLabel').textContent='Kori · '+Math.round(distance(p.lie,h.basket))+' m';}
  v.heldDisc.visible=!!(round?.phase==='aim'&&!mapOpen);
  if(v.heldDisc.visible){
    const rect=$('scene').getBoundingClientRect();
    const screen=heldDiscScreenPoint(rect),cx=screen.x-rect.left,cy=screen.y-rect.top;
    const depth=1.5,halfHeight=Math.tan(camera.fov*Math.PI/360)*depth;
    const x=cx/rect.width*2-1;
    const y=1-cy/rect.height*2;
    v.heldDisc.position.set(x*halfHeight*camera.aspect,y*halfHeight,-depth);
    v.heldDisc.scale.setScalar(110/rect.height*halfHeight);
    v.heldDisc.rotation.set(.65,0,aim.curve*Math.PI/4);
    v.heldFace.color.setHex(DISCS[aim.disc].colour);
    v.heldRim.color.setHex(DISCS[aim.disc].colour).multiplyScalar(.6);
  }
  renderer.render(v.scene,camera);tune(dt);
}
function tune(dt){
  const v=scene3d;if(!dt||!round||round.phase!=='fly'||v.tuned>=2)return;
  v.samples++;v.elapsed+=dt;
  if(v.elapsed>2){if(v.samples/v.elapsed<40){if(!v.tuned)v.renderer.setPixelRatio(1);else v.renderer.shadowMap.enabled=false;v.tuned++;}else v.tuned=2;v.elapsed=v.samples=0;}
}

