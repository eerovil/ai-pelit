// AiPelitAanet (#205): recorded sound effects shared by the games, played through Web Audio.
// aanet-2 is aanet-1 with more sounds and loops (an engine, wind, wheels rolling).
// Load it with a classic <script src="../../../lib/aanet-2/aanet.js"></script> before the game's
// own script. The game names the sounds it uses once, then plays them by name:
//
//   AiPelitAanet.load(['askel', 'hiekka']);
//   AiPelitAanet.play('hiekka', { vol: 0.8, rate: 1.1 }) || tone(160, 0.2);
//
// A loop (an engine, wind) runs until stopped, and follows the game through set():
//
//   const engine = AiPelitAanet.loop('moottori', { vol: 0.5 });
//   engine.set({ rate: 0.8 + speed / 40, vol: 0.3 + speed / 100 });   // each frame is fine
//   engine.stop();
//
// The handle works the same before the first tap or while the file loads: the sound starts once
// it can, with the latest set() values.
// play() returns false when nothing played (before the first tap, while the file is still
// loading, offline on the very first open, muted), so a game can fall back to its own beep.
// Nothing here ever throws, and a game plays the same without sound.
// The files sit beside this script; the service worker keeps them after their first use.
// This folder never changes once published: a new sound goes in aanet-3/.
(function () {
  'use strict';
  // Name -> file, and what it is. A name is lowercase Finnish without dots.
  var SOUNDS = {
    askel: 'askel.mp3',          // a footstep on a hard track
    askel2: 'askel2.mp3',        // the other foot
    ponnistus: 'ponnistus.mp3',  // a foot on a wooden board, a take-off
    hiekka: 'hiekka.mp3',        // landing in sand
    tomahdys: 'tomahdys.mp3',    // a soft heavy thud
    osuma: 'osuma.mp3',          // a light hit
    metalli: 'metalli.mp3',      // a hit on metal
    puu: 'puu.mp3',              // a hit on wood
    potku: 'potku.mp3',          // a kick or a punch
    suhahdus: 'suhahdus.mp3',    // a whoosh through the air
    loiskis: 'loiskis.mp3',      // a splash in water
    naksu: 'naksu.mp3',          // a click
    valinta: 'valinta.mp3',      // a short select blip
    onnistui: 'onnistui.mp3',    // a confirmation
    virhe: 'virhe.mp3',          // an error buzz
    nousu: 'nousu.mp3',          // an arcade power-up
    hyppy: 'hyppy.mp3',          // an arcade jump
    aplodit: 'aplodit.mp3',      // applause, about 4.5 s
    yleiso: 'yleiso.mp3',        // a shouting crowd, about 4 s
    ohhoo: 'ohhoo.mp3',          // a crowd's "ooh", a near miss
    voitto: 'voitto.mp3',        // a short rising tune: a win
    tappio: 'tappio.mp3',        // a short falling tune: a loss
    mitali: 'mitali.mp3',        // four rising steel-drum notes: a medal
    // New in aanet-2 (#205). LOOP: made to repeat, play it with loop().
    pilli: 'pilli.mp3',         // a referee whistle, short
    pilli2: 'pilli2.mp3',       // a referee whistle, two blasts: full time
    lahto: 'lahto.mp3',         // a starting pistol
    rima: 'rima.mp3',           // a bar or a hurdle falling, metal clatter
    seivas: 'seivas.mp3',       // a pole planted in the box, metal clunk
    lyonti: 'lyonti.mp3',       // a palm hitting a ball
    verkko: 'verkko.mp3',       // a ball into a net
    gongi: 'gongi.mp3',         // a gong
    kello: 'kello.mp3',         // a bell ring
    lumi: 'lumi.mp3',           // a footstep in snow
    ruoho: 'ruoho.mp3',         // a footstep on grass
    lasku: 'lasku.mp3',         // a skateboard or scooter landing, wooden clack
    pop: 'pop.mp3',             // a skateboard ollie pop
    boing: 'boing.mp3',         // a cartoon spring boing
    jousi: 'jousi.mp3',         // a metal spring, a trampoline bed
    putoaminen: 'putoaminen.mp3', // a cartoon falling whistle
    kitka: 'kitka.mp3',         // tyres screeching
    kolari: 'kolari.mp3',       // a crash, metal crunch
    lasi: 'lasi.mp3',           // glass breaking
    rajahdys: 'rajahdys.mp3',   // an explosion
    torvi: 'torvi.mp3',         // a car horn
    kamera: 'kamera.mp3',       // a camera shutter
    jarru: 'jarru.mp3',         // an air brake hiss
    ketju: 'ketju.mp3',         // a chain lift clanking
    kirkuna: 'kirkuna.mp3',     // riders screaming
    halytys: 'halytys.mp3',     // a warning alarm
    kaiku: 'kaiku.mp3',         // a sonar ping with echo
    kupla: 'kupla.mp3',         // one bubble
    jaa: 'jaa.mp3',             // ice cracking
    narina: 'narina.mp3',       // a creak, wood or a hull
    karhu: 'karhu.mp3',         // a bear growl
    lintu: 'lintu.mp3',         // a crow caw, a bird of prey warning
    rouske: 'rouske.mp3',       // a crunchy bite
    vauva: 'vauva.mp3',         // a baby's short sound
    nams: 'nams.mp3',           // eating, a smack of lips
    royhtays: 'royhtays.mp3',   // a burp
    pruut: 'pruut.mp3',         // spitting, a raspberry
    litsahdus: 'litsahdus.mp3', // a wet splat of food
    lusikka: 'lusikka.mp3',     // cutlery clattering on the floor
    moottori: 'moottori.mp3',   // LOOP: a car engine; set rate by speed
    kartti: 'kartti.mp3',       // LOOP: a small kart engine; set rate by speed
    rullaus: 'rullaus.mp3',     // LOOP: wheels or a ball rolling
    tuuli: 'tuuli.mp3',         // LOOP: wind
    sade: 'sade.mp3',           // LOOP: rain
    syvyys: 'syvyys.mp3',       // LOOP: deep underwater rumble
    sukellusvene: 'sukellusvene.mp3', // LOOP: a submarine engine
    kuplat: 'kuplat.mp3',       // LOOP: bubbles
    humina: 'humina.mp3',       // LOOP: machinery hum
  };

  var me = document.currentScript;
  var dir = me && me.src ? me.src.replace(/[^\/]*$/, '') : '';
  var ac = null;
  var files = {};   // name -> Promise of the file's bytes (null when it failed)
  var bufs = {};    // name -> decoded AudioBuffer
  var asked = {};   // name -> decoding started
  var loops = [];   // the loops running or waiting for their sound

  function context() {
    if (ac) return ac;
    try {
      var C = window.AudioContext || window.webkitAudioContext;
      if (C) ac = new C();
    } catch (e) { ac = null; }
    return ac;
  }

  function decode(name) {
    if (asked[name] || !files[name] || !context()) return;
    asked[name] = true;
    files[name].then(function (bytes) {
      if (!bytes) return;
      try {
        // The callback form also works on older Safari, where decodeAudioData returns no promise.
        var p = ac.decodeAudioData(bytes, function (b) { bufs[name] = b; wake(); }, function () {});
        if (p && p.catch) p.catch(function () {});
      } catch (e) { /* an undecodable file just stays silent */ }
    });
  }

  function load(names) {
    (names || []).forEach(function (name) {
      if (!SOUNDS.hasOwnProperty(name) || files[name]) return;
      files[name] = fetch(dir + SOUNDS[name])
        .then(function (r) { return r.ok ? r.arrayBuffer() : null; })
        .catch(function () { return null; });
      decode(name);
    });
  }

  // Browsers allow sound only after a tap: the first one anywhere on the page resumes it.
  function unlock() {
    if (!context()) return;
    for (var name in files) decode(name);
    try {
      if (ac.state === 'suspended') { var r = ac.resume(); if (r && r.then) r.then(wake, function () {}); }
    } catch (e) {}
    wake();
  }

  // Starts every loop that waits and now can: its sound decoded, sound on.
  function wake() {
    loops.forEach(function (l) { if (!l.src) l.start(); });
  }

  function Loop(name, opts) {
    this.name = name;
    this.vol = opts && opts.vol !== undefined ? opts.vol : 1;
    this.rate = opts && opts.rate ? opts.rate : 1;
    this.src = null;
    this.gain = null;
    this.start();
  }
  Loop.prototype.start = function () {
    if (this.src || this.stopped || api.muted || !ac || ac.state !== 'running' || !bufs[this.name]) return;
    try {
      var b = bufs[this.name], src = ac.createBufferSource(), g = ac.createGain();
      src.buffer = b;
      src.loop = true;
      // MP3 decoders may pad the ends with a few ms of silence: loop inside them.
      if (b.duration > 0.5) { src.loopStart = 0.03; src.loopEnd = b.duration - 0.03; }
      src.playbackRate.value = this.rate;
      g.gain.value = this.vol;
      src.connect(g);
      g.connect(ac.destination);
      src.start(ac.currentTime, b.duration > 0.5 ? 0.03 : 0);
      this.src = src;
      this.gain = g;
    } catch (e) { this.src = null; }
  };
  Loop.prototype.set = function (o) {
    if (!o) return this;
    if (o.vol !== undefined) this.vol = o.vol;
    if (o.rate) this.rate = o.rate;
    if (this.src) {
      try {
        // A short glide, so a value set each frame does not crackle.
        var t = ac.currentTime;
        this.gain.gain.setTargetAtTime(api.muted ? 0 : this.vol, t, 0.03);
        this.src.playbackRate.setTargetAtTime(this.rate, t, 0.03);
      } catch (e) {}
    } else this.start();
    return this;
  };
  Loop.prototype.stop = function () {
    this.stopped = true;
    if (this.src) { try { this.src.stop(); } catch (e) {} }
    this.src = null;
    var i = loops.indexOf(this);
    if (i >= 0) loops.splice(i, 1);
  };
  Loop.prototype.playing = function () { return !!this.src; };
  ['pointerdown', 'touchend', 'keydown'].forEach(function (t) {
    window.addEventListener(t, unlock, true);
  });
  // A loop must not go on with the phone in the pocket: sound sleeps while the page is hidden.
  document.addEventListener('visibilitychange', function () {
    if (!ac) return;
    try { if (document.hidden) ac.suspend(); else ac.resume(); } catch (e) {}
  });

  var api = {
    muted: false,
    load: load,
    unlock: unlock,
    // Whether the sound is loaded and decoded, so that play() can play it.
    ready: function (name) { return !!bufs[name]; },
    play: function (name, opts) {
      if (api.muted || !ac || ac.state !== 'running' || !bufs[name]) return false;
      try {
        var src = ac.createBufferSource(), g = ac.createGain(), o = opts || {};
        src.buffer = bufs[name];
        if (o.rate) src.playbackRate.value = o.rate;
        g.gain.value = o.vol === undefined ? 1 : o.vol;
        src.connect(g);
        g.connect(ac.destination);
        src.start(ac.currentTime + (o.delay || 0));
        return true;
      } catch (e) { return false; }
    },
    // A sound that repeats until stop(); see the top of this file. Never null.
    loop: function (name, opts) {
      var l = new Loop(name, opts);
      loops.push(l);
      return l;
    },
    names: function () { return Object.keys(SOUNDS); },
    file: function (name) { return SOUNDS[name]; },
  };
  window.AiPelitAanet = api;
})();
