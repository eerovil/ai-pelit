// Outfits in the 3D games (#568): the 3D pieces of an outfit from the shared picker (outfits.js).
// A published folder never changes; a fix is lib/asut3d-2/ (rule 1). Classic script, global
// AiPelitAsut3d; every builder takes the game's own three.js module (THREE) as its first argument,
// so it works with any three-r*/ release. Load it after outfits.js:
//
//   <script src="../../../outfits.js" data-game="<slug>" data-share="3d"></script>
//   <script src="../../../lib/asut3d-1/asut3d.js"></script>
//
// then, once:
//
//   let outfit = AiPelitAsut3d.setup({
//     default: 'haalari',            // the id worn by a phone that never picked (from kolmiD)
//     button: 'asu',                 // a <button> id or element to open the picker with; given a
//                                    // container instead, a "👕 Asu" button is made inside it
//     change(o) { outfit = o; ... }, // a pick: rebuild the player's figure
//   });
//
// and with three.js loaded:
//
//   const fig = AiPelitAsut3d.figure(THREE, outfit);   // a whole person, 1.8 tall, feet at y 0,
//   scene.add(fig);                                    // facing +z; turn fig.userData.joints.*
//
// A game with a body of its own takes only the pieces: head(THREE, outfit) (radius about 1,
// centred, facing +z: scale it to the game's head), cape(THREE, outfit, { w, h }) (hangs down from
// y 0, null without a cape) and torso(THREE, outfit, { w, h, d, round }) (ribs, a stripe; null when
// there is nothing). In a room, send AiPelitOutfits.current().id with the player and build a
// friend from AiPelitOutfits.get(id); rebuild one figure when that player's id changes.
(function () {
  'use strict';
  var TAU = Math.PI * 2;

  // Geometries and materials, made once for each three.js module.
  var kits = [];
  function kit(T) {
    for (var i = 0; i < kits.length; i++) if (kits[i].T === T) return kits[i];
    var k = { T: T, mats: {}, ball: new T.SphereGeometry(1, 16, 12), box: new T.BoxGeometry(1, 1, 1),
      cyl: new T.CylinderGeometry(1, 1, 1, 16), cone: new T.ConeGeometry(1, 1, 16) };
    kits.push(k);
    return k;
  }
  // kind: '' (lit), 'glow' (unlit, for a pumpkin's face or a red nose), 'two' (both sides lit).
  function mat(k, col, kind) {
    var key = col + '|' + (kind || '');
    if (!k.mats[key]) {
      var T = k.T;
      k.mats[key] = kind === 'glow' ? new T.MeshBasicMaterial({ color: col })
        : new T.MeshStandardMaterial({ color: col, roughness: 0.8, side: kind === 'two' ? T.DoubleSide : T.FrontSide });
    }
    return k.mats[key];
  }
  // A mesh on par at (x, y, z), scaled (sx, sy, sz).
  function put(k, par, geo, col, x, y, z, sx, sy, sz, kind) {
    var m = new k.T.Mesh(geo, mat(k, col, kind));
    m.position.set(x, y, z); m.scale.set(sx, sy === undefined ? sx : sy, sz === undefined ? sx : sz);
    par.add(m);
    return m;
  }

  // ---- The head: radius about 1, centre at 0, the face towards +z ----
  function head(T, o, opts) {
    o = o || {};
    var k = kit(T), h = new T.Group(), kind = o.head || null;
    var ball = k.ball, box = k.box, cyl = k.cyl, cone = k.cone;
    function face(col) { put(k, h, ball, col || o.skin || '#f0c8a0', 0, 0, 0, 1); }
    function eyes(col, glow) { for (var s = -1; s <= 1; s += 2) put(k, h, ball, col || '#1a1a1a', s * 0.37, 0.13, 0.93, 0.12, 0.12, 0.08, glow ? 'glow' : ''); }
    function hairCap(col) {
      var c = new T.Mesh(new T.SphereGeometry(1.06, 16, 8, 0, TAU, 0, Math.PI * 0.45), mat(k, col));
      c.rotation.x = -0.35; c.position.y = 0.02; h.add(c); return c;
    }
    function beanie(col, bob) {
      var c = new T.Mesh(new T.SphereGeometry(1.08, 16, 8, 0, TAU, 0, Math.PI / 2), mat(k, col));
      c.position.y = 0.13; h.add(c);
      put(k, h, ball, bob || '#ffffff', 0, 1.2, 0, 0.37);
    }
    if (kind === 'naamio') {
      // The hero mask: the hood in the suit's colour behind, the dark mask, two white lenses.
      put(k, h, ball, o.top || '#1fb5a8', 0, -0.05, -0.4, 1.15, 1.1, 1);
      face(o.mask || '#1b1f2e');
      for (var s = -1; s <= 1; s += 2) put(k, h, ball, '#ffffff', s * 0.38, 0.15, 0.9, 0.3, 0.2, 0.12, 'glow').rotation.z = -s * 0.35;
    } else if (kind === 'pumpkin') {
      put(k, h, ball, '#e8711a', 0, 0, 0, 1.25, 1.05, 1.15);
      for (var r = -1; r <= 1; r++) put(k, h, ball, '#c85a10', r * 0.62, 0, 0, 0.3, 1.04, 1.0);
      put(k, h, cyl, '#4a6b22', 0, 1.15, 0, 0.13, 0.4, 0.13);
      for (s = -1; s <= 1; s += 2) put(k, h, box, '#ffd23a', s * 0.42, 0.25, 1.1, 0.28, 0.28, 0.1, 'glow').rotation.z = Math.PI / 4;
      put(k, h, box, '#ffd23a', 0, -0.35, 1.08, 0.8, 0.18, 0.1, 'glow');
    } else if (kind === 'witch') {
      face(o.skin || '#9fd17a'); eyes();
      hairCap(o.hair || '#2a2a2a');
      put(k, h, ball, o.hair || '#2a2a2a', 0, -0.4, -0.5, 1, 1.2, 0.6);
      put(k, h, cone, o.skin || '#9fd17a', 0, -0.05, 1.05, 0.13, 0.4, 0.13).rotation.x = Math.PI / 2;
      put(k, h, cyl, '#2a1640', 0, 0.75, 0, 1.7, 0.1, 1.7);
      put(k, h, cyl, '#9a5ad0', 0, 0.88, 0, 0.93, 0.2, 0.93);
      put(k, h, cone, '#2a1640', 0, 1.75, -0.1, 0.95, 2, 0.95).rotation.x = -0.2;
    } else if (kind === 'ghost') {
      put(k, h, ball, o.skin || '#f4f4f8', 0, 0, 0, 1.05, 1.2, 1.05);
      for (s = -1; s <= 1; s += 2) put(k, h, ball, '#141418', s * 0.38, 0.15, 0.98, 0.2, 0.3, 0.08, 'glow');
      put(k, h, ball, '#141418', 0, -0.4, 0.95, 0.22, 0.28, 0.08, 'glow');
    } else if (kind === 'skull') {
      put(k, h, ball, o.skin || '#ece6d6', 0, 0, 0, 1, 1.05, 1);
      for (s = -1; s <= 1; s += 2) put(k, h, ball, '#141418', s * 0.38, 0.12, 0.82, 0.28, 0.28, 0.2, 'glow');
      put(k, h, cone, '#141418', 0, -0.18, 0.95, 0.12, 0.25, 0.06, 'glow');
      put(k, h, box, '#141418', 0, -0.55, 0.86, 0.7, 0.18, 0.1, 'glow');
      for (var t = 0; t < 4; t++) put(k, h, box, o.skin || '#ece6d6', -0.24 + t * 0.16, -0.55, 0.9, 0.12, 0.14, 0.06);
    } else if (kind === 'vampire') {
      face(o.skin || '#e8e0ec'); eyes('#c0102a', true);
      hairCap(o.hair || '#121212');
      put(k, h, cone, o.hair || '#121212', 0, 0.72, 0.8, 0.25, 0.4, 0.1).rotation.x = Math.PI;
      for (s = -1; s <= 1; s += 2) put(k, h, cone, '#ffffff', s * 0.15, -0.45, 0.9, 0.06, 0.2, 0.06).rotation.x = Math.PI;
      // The tall collar, open at the front.
      var col = new T.Mesh(new T.CylinderGeometry(1.3, 0.95, 1.1, 16, 1, true, Math.PI * 0.5, Math.PI), mat(k, o.cape || '#9b1024', 'two'));
      col.position.y = -0.55; h.add(col);
    } else if (kind === 'mummy') {
      face(o.skin || '#e9dfc4');
      var tor = new T.TorusGeometry(1.0, 0.07, 6, 24);
      [[-0.55, 0.2], [-0.15, -0.15], [0.45, 0.15], [0.75, -0.25]].forEach(function (b) {
        var m = new T.Mesh(tor, mat(k, '#cfc2a0')); m.rotation.x = Math.PI / 2 + b[1];
        m.position.y = b[0]; m.scale.setScalar(Math.sqrt(Math.max(0.1, 1 - b[0] * b[0])) * 1.02); h.add(m);
      });
      put(k, h, box, '#2a2018', 0, 0.15, 0.9, 0.9, 0.18, 0.12, 'glow');
      put(k, h, ball, '#ffffff', 0.3, 0.15, 0.97, 0.1, 0.1, 0.05, 'glow');
    } else if (kind === 'pukki' || kind === 'tonttu') {
      // The Christmas heads come from Pulkkamäki v6's dressHead() (#473), at this size and facing.
      face(); eyes();
      var brim = new T.Mesh(new T.SphereGeometry(1.1, 16, 8, 0, TAU, 0, Math.PI / 2), mat(k, '#ffffff'));
      brim.position.y = 0.13; brim.scale.y = 0.35; h.add(brim);
      var tall = kind === 'tonttu';
      put(k, h, cone, '#d42a2a', 0, 1.33, -0.2, 1.0, tall ? 2.8 : 2.0, 1.0).rotation.x = -0.35;
      put(k, h, ball, '#ffffff', 0, tall ? 2.67 : 2.2, -0.67, 0.33);
      if (kind === 'pukki') {
        var beard = new T.Mesh(new T.SphereGeometry(0.87, 12, 8, 0, TAU, Math.PI / 2, Math.PI / 2), mat(k, '#f4f4f4'));
        beard.position.set(0, -0.27, 0.33); beard.scale.set(1, 1.4, 0.9); h.add(beard);
      }
    } else if (kind === 'poro') {
      face(o.skin || '#8a5a36'); eyes();
      for (s = -1; s <= 1; s += 2) {
        put(k, h, cyl, '#5a3a1e', s * 0.67, 1.47, 0, 0.15, 1.87, 0.15).rotation.z = -s * 0.4;
        put(k, h, cyl, '#5a3a1e', s * 1.13, 2.0, 0, 0.12, 0.93, 0.12).rotation.z = s * 0.6;
      }
      put(k, h, ball, '#ff2020', 0, -0.13, 1.07, 0.27, 0.27, 0.27, 'glow');
    } else if (kind === 'lumiukko') {
      face(o.skin || '#f6f8fc'); eyes('#111111');
      put(k, h, cyl, '#1a1a22', 0, 0.8, 0, 1.33, 0.17, 1.33);
      put(k, h, cyl, '#1a1a22', 0, 1.53, 0, 0.8, 1.33, 0.8);
      put(k, h, cone, '#ff7a1a', 0, -0.07, 1.33, 0.2, 0.93, 0.2).rotation.x = Math.PI / 2;
    } else if (kind === 'pipari') {
      face(o.skin || '#b8733a'); eyes('#ffffff');
      var smile = new T.Mesh(new T.TorusGeometry(0.4, 0.08, 4, 12, Math.PI), mat(k, '#ffffff'));
      smile.rotation.z = Math.PI; smile.position.set(0, -0.27, 0.93); h.add(smile);
    } else if (kind === 'harry' || kind === 'ron' || kind === 'hermione') {
      face(o.skin); eyes('#2a1e14');
      var hair = o.hair || '#1d1712';
      hairCap(hair);
      if (kind === 'hermione') [[-0.85, -0.1, -0.2], [0.85, -0.1, -0.2], [-0.7, -0.6, -0.3], [0.7, -0.6, -0.3], [0, 0.4, -0.6], [0, -0.4, -0.7]]
        .forEach(function (p) { put(k, h, ball, hair, p[0], p[1], p[2], 0.6); });
      else if (kind === 'harry') for (t = 0; t < 5; t++) put(k, h, cone, hair, -0.5 + t * 0.25, 0.85, 0.55, 0.15, 0.4, 0.15).rotation.x = 0.9;
      if (kind === 'harry') {
        var ring = new T.TorusGeometry(0.24, 0.04, 6, 16);
        for (s = -1; s <= 1; s += 2) { var g = new T.Mesh(ring, mat(k, '#1a1a1a')); g.position.set(s * 0.37, 0.13, 0.98); h.add(g); }
        put(k, h, box, '#1a1a1a', 0, 0.13, 1.0, 0.26, 0.05, 0.05);
        put(k, h, box, '#c0392b', 0.25, 0.62, 0.8, 0.05, 0.25, 0.05).rotation.z = 0.6;
      } else if (kind === 'ron') {
        for (s = -1; s <= 1; s += 2) for (t = 0; t < 3; t++) put(k, h, ball, '#c47a4a', s * (0.42 + t * 0.1), -0.18 - (t % 2) * 0.08, 0.92, 0.05);
      }
      // The house scarf round the neck.
      var sc = new T.Mesh(new T.TorusGeometry(0.72, 0.2, 8, 20), mat(k, o.scarf || '#9b1b1b'));
      sc.rotation.x = Math.PI / 2; sc.position.y = -0.95; h.add(sc);
      var st = new T.Mesh(new T.TorusGeometry(0.8, 0.06, 6, 20), mat(k, '#e8b730'));
      st.rotation.x = Math.PI / 2; st.position.y = -0.85; h.add(st);
    } else {
      // An everyday head: the face, and a beanie when the outfit has one, else its hair.
      face(); eyes();
      if (o.pipo) beanie(o.pipo, o.tupsu); else hairCap(o.hair || '#3b2a1a');
    }
    return h;
  }

  // ---- A cape: w wide, h long, hanging down from y 0 (turn the group to blow it back) ----
  function cape(T, o, opts) {
    if (!o || !o.cape) return null;
    opts = opts || {};
    var k = kit(T), w = opts.w || 0.5, len = opts.h || 0.9, g = new T.Group();
    g.userData.cloth = put(k, g, k.box, o.cape, 0, -len / 2, 0, w, len, 0.04);
    return g;
  }

  // ---- Chest pieces, for a torso w × h × d centred at 0 (round: a cylinder of diameter w) ----
  function torso(T, o, opts) {
    if (!o || !(o.bones || o.stripe)) return null;
    opts = opts || {};
    var k = kit(T), w = opts.w || 0.5, hh = opts.h || 0.6, d = opts.d || 0.3, g = new T.Group();
    var front = (opts.round ? w / 2 : d / 2) + 0.005;
    if (o.bones) {
      var bone = o.skin || '#ece6d6';
      put(k, g, k.box, bone, 0, 0, front, w * 0.08, hh * 0.75, 0.02);
      for (var i = 0; i < 3; i++) put(k, g, k.box, bone, 0, hh * (0.25 - i * 0.15), front, w * (0.8 - i * 0.1), hh * 0.06, 0.02);
    } else if (o.stripe) {
      if (opts.round) put(k, g, k.cyl, o.stripe, 0, -hh * 0.05, 0, w * 0.52, hh * 0.12, w * 0.52);
      else put(k, g, k.box, o.stripe, 0, -hh * 0.05, 0, w * 1.04, hh * 0.12, d * 1.06);
    }
    return g;
  }

  // ---- A whole person: 1.8 tall, feet at y 0, facing +z ----
  // userData.joints: body (the group the rest hangs on), head, armL/armR (shoulders), elbL/elbR,
  // handL/handR, legL/legR (hips), kneeL/kneeR; a joint's +x turns its limb backward. Seittisankari's
  // hero (#529) is the model, and its poses fit these joints.
  function figure(T, o, opts) {
    o = o || {};
    var k = kit(T), g = new T.Group(), body = new T.Group(), J = { body: body };
    g.add(body);
    var top = o.top || '#2f6fd0', bottom = o.bottom || '#26324a', shoe = o.shoe || '#222222';
    var hand = o.mitt || (o.head === 'skull' ? o.skin : null) || o.skin || '#f0c8a0';
    put(k, body, k.box, top, 0, 1.12, 0, 0.5, 0.62, 0.3);
    var chest = torso(T, o, { w: 0.5, h: 0.62, d: 0.3 });
    if (chest) { chest.position.y = 1.12; body.add(chest); }
    put(k, body, k.box, bottom, 0, 0.86, 0, 0.46, 0.14, 0.28);
    J.head = new T.Group(); J.head.position.set(0, 1.56, 0); J.head.scale.setScalar(0.2); body.add(J.head);
    J.head.add(head(T, o));
    var cp = cape(T, o, { w: 0.52, h: 0.95 });
    if (cp) { cp.position.set(0, 1.42, -0.17); cp.rotation.x = 0.12; body.add(cp); J.cape = cp; }
    function joint(par, x, y) { var j = new T.Group(); j.position.set(x, y, 0); par.add(j); return j; }
    [['L', -0.33], ['R', 0.33]].forEach(function (s) {
      var key = s[0], x = s[1];
      var sh = joint(body, x, 1.38); put(k, sh, k.box, top, 0, -0.14, 0, 0.14, 0.3, 0.16);
      var el = joint(sh, 0, -0.27); put(k, el, k.box, top, 0, -0.12, 0, 0.12, 0.26, 0.14);
      J['hand' + key] = put(k, el, k.ball, hand, 0, -0.29, 0, 0.09);
      J['arm' + key] = sh; J['elb' + key] = el;
      var hip = joint(body, x * 0.42, 0.84); put(k, hip, k.box, bottom, 0, -0.21, 0, 0.2, 0.44, 0.22);
      var kn = joint(hip, 0, -0.42); put(k, kn, k.box, bottom, 0, -0.2, 0, 0.18, 0.42, 0.2);
      put(k, kn, k.box, shoe, 0, -0.42, 0.05, 0.19, 0.08, 0.3);
      J['leg' + key] = hip; J['knee' + key] = kn;
    });
    g.userData.joints = J;
    g.userData.outfit = o.id || null;
    return g;
  }

  // ---- The picker, with the 3D games' common set and this game's default first ----
  function setup(opts) {
    opts = opts || {};
    var O = window.AiPelitOutfits;
    if (!O) return null;
    var list = (opts.outfits || O.kolmiD).slice();
    for (var i = 1; i < list.length; i++) if (list[i].id === opts.default) { list.unshift(list.splice(i, 1)[0]); break; }
    var cur = O.setup({ outfits: list, draw: opts.draw, change: opts.change,
      halloween: opts.halloween, joulu: opts.joulu, tylypahka: opts.tylypahka });
    var b = typeof opts.button === 'string' ? document.getElementById(opts.button) : opts.button;
    if (b && b.tagName !== 'BUTTON') {
      var nb = document.createElement('button');
      nb.type = 'button'; nb.textContent = '👕 Asu';
      if (opts.buttonClass) nb.className = opts.buttonClass;
      b.appendChild(nb); b = nb;
    }
    if (b) b.addEventListener('click', function () { O.open(); });
    return cur;
  }

  window.AiPelitAsut3d = { setup: setup, figure: figure, head: head, cape: cape, torso: torso };
})();
