'use strict';

var MarjakoriPiirto = (function () {
  var colors = ['#4268d8', '#f2a739', '#e94b5f', '#e8d8bd', '#66a95b', '#9a6d3f'];
  var names = ['mustikka', 'lakka', 'mansikka', 'sieni', 'lehti', 'käpy'];
  function shape(ctx, cx, cy, r, kind) {
    ctx.save(); ctx.translate(cx, cy); ctx.fillStyle = colors[kind]; ctx.strokeStyle = '#25342a'; ctx.lineWidth = Math.max(1, r / 12);
    if (kind === 1) { ctx.beginPath(); for(var l=0;l<7;l++){var a=l*Math.PI*2/7-Math.PI/2;ctx.arc(Math.cos(a)*r*.34,Math.sin(a)*r*.34,r*.34,a-Math.PI*.45,a+Math.PI*.45);}ctx.fill(); }
    else if (kind === 3) { ctx.beginPath(); ctx.arc(0, -r * .15, r * .6, Math.PI, 0); ctx.fill(); ctx.fillStyle = '#f4ecd7'; ctx.fillRect(-r * .18, -r * .15, r * .36, r * .72); }
    else if (kind === 4) { ctx.beginPath(); ctx.moveTo(0, -r*.7); ctx.quadraticCurveTo(r*.75, -r*.15, 0, r*.75); ctx.quadraticCurveTo(-r*.75, -r*.15, 0, -r*.7); ctx.fill(); ctx.stroke(); }
    else if (kind === 5) { ctx.beginPath(); for (var i=0;i<10;i++) { var a=i*Math.PI/5-Math.PI/2, q=i%2?r*.48:r*.75; ctx.lineTo(Math.cos(a)*q,Math.sin(a)*q); } ctx.closePath(); ctx.fill(); ctx.stroke(); }
    else { ctx.beginPath(); ctx.arc(0, 0, r * .62, 0, Math.PI * 2); ctx.fill(); if (kind === 2) { ctx.fillStyle='#56a84b'; ctx.beginPath(); ctx.ellipse(0,-r*.62,r*.3,r*.18,0,0,Math.PI*2); ctx.fill(); } }
    ctx.restore();
  }
  function draw(ctx, s, box, selected, motion) {
    var n = Marjakori.SIZE, z = Math.min(box.w, box.h) / n, ox = box.x + (box.w - z*n)/2, oy = box.y + (box.h-z*n)/2, board = motion && motion.before ? motion.before.board : s.board;
    ctx.save(); ctx.fillStyle='#1d3b32'; ctx.fillRect(ox-7,oy-7,z*n+14,z*n+14);
    for (var i=0;i<board.length;i++) { var p={x:i%n,y:Math.floor(i/n)}, c=board[i], x=ox+(p.x+.5)*z, y=oy+(p.y+.5)*z, dy=motion&&motion.fall?(1-motion.t)*z*2:0;
      if(motion&&motion.before){if(i===motion.a){x+=((motion.b%n)-(motion.a%n))*z*motion.t;y+=(Math.floor(motion.b/n)-Math.floor(motion.a/n))*z*motion.t;}else if(i===motion.b){x+=((motion.a%n)-(motion.b%n))*z*motion.t;y+=(Math.floor(motion.a/n)-Math.floor(motion.b/n))*z*motion.t;}}
      ctx.fillStyle = (i===selected ? '#ffe28a' : '#eff4d7'); ctx.fillRect(ox+p.x*z+1,oy+p.y*z+1,z-2,z-2);
      if (s.moss[i]) { ctx.fillStyle='#638f45'; ctx.fillRect(ox+p.x*z+4,oy+p.y*z+z*.74,z-8,z*.18); }
      shape(ctx,x,y+dy,z*.43,c.kind);
      if (c.special) { ctx.fillStyle='#fff9bc'; ctx.font='bold '+Math.max(12,z*.37)+'px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(c.special==='puuska'?'↔':'✦',x,y); }
    }
    ctx.restore(); return { x: ox, y: oy, size: z };
  }
  return { draw: draw, names: names, colors: colors };
}());
