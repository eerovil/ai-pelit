// One event of the match, inside the match page's frame (#168). The match page (index.html) loads
// a published event version's own page here, with this file in place of rooms.js and without
// scores.js and back.js. It hands the event the match's room (Ottelu.proxy) and changes the
// shared athletics library (public/lib/yleisurheilu-1/) as it loads: Ottelu.patch() gives the
// event the match's field, three rounds and its own saves. The event's own code is untouched.
(function () {
  'use strict';
  var O = parent.Ottelu;
  window.AiPelitRooms = O.proxy;
  // kisa.js sets window.AiPelitKisa once; catch it there, before the event's script uses it.
  var kisa;
  Object.defineProperty(window, 'AiPelitKisa', {
    configurable: true,
    get: function () { return kisa; },
    set: function (v) { kisa = O.patch(v, window); },
  });
})();
