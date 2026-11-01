// AiPelitAanet (#205): recorded sound effects shared by the games, played through Web Audio.
// Load it with a classic <script src="../../../lib/aanet-1/aanet.js"></script> before the game's
// own script. The game names the sounds it uses once, then plays them by name:
//
//   AiPelitAanet.load(['askel', 'hiekka']);
//   AiPelitAanet.play('hiekka', { vol: 0.8, rate: 1.1 }) || tone(160, 0.2);
//
// play() returns false when nothing played (before the first tap, while the file is still
// loading, offline on the very first open, muted), so a game can fall back to its own beep.
// Nothing here ever throws, and a game plays the same without sound.
// The files sit beside this script; the service worker keeps them after their first use.
// This folder never changes once published: a new sound goes in aanet-2/.
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
  };

  var me = document.currentScript;
  var dir = me && me.src ? me.src.replace(/[^\/]*$/, '') : '';
  var ac = null;
  var files = {};   // name -> Promise of the file's bytes (null when it failed)
  var bufs = {};    // name -> decoded AudioBuffer
  var asked = {};   // name -> decoding started

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
        var p = ac.decodeAudioData(bytes, function (b) { bufs[name] = b; }, function () {});
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
    try { if (ac.state === 'suspended') ac.resume(); } catch (e) {}
  }
  ['pointerdown', 'touchend', 'keydown'].forEach(function (t) {
    window.addEventListener(t, unlock, true);
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
    names: function () { return Object.keys(SOUNDS); },
    file: function (name) { return SOUNDS[name]; },
  };
  window.AiPelitAanet = api;
})();
