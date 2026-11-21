// Smooth movement of the other players in a room (#480). A phone hears where another player is
// only when a message arrives, 10-12 times a second and at uneven gaps; drawing each one straight
// at its newest spot (or chasing it fast) shows every uneven gap as a jerk. A track keeps the last
// few spots it heard for one player and is drawn a moment in the past, gliding between the two
// spots around that moment. Load it as a classic script before the game's own:
//
//   <script src="../../../lib/sulava-1/sulava.js"></script>
//
//   const tr = AiPelitSulava.track({ keys: ['x', 'y'], angles: [], jump: 8 });
//   tr.push(stamp, { x, y });        // on each message: stamp = the sending phone's own clock in
//                                    // seconds (AiPelitSulava.now() there), or null for "now here"
//   tr.snap(stamp, { x, y });        // a jump the game knows of (a new round, a respawn): no glide
//   const s = tr.at();               // each frame: { x, y } to draw (one object, reused), or null
//                                    // before the first spot
//   tr.time                          // the moment at() last drew, on the sender's clock: for a
//                                    // game's own extras that should lag with the player (a hose)
//
// Options (defaults): keys ['x', 'y'], angles [] (keys that wrap in radians, blended the short way
// round), jump Infinity (a move longer than this between two spots, measured on the first two keys,
// is a jump), minDelay 0.06, maxDelay 0.25, extra 0.25 (how far past the newest spot a late
// player keeps going at its last speed before it stops).
//
// The sending phone's clock is never compared with this one's: each track learns its own offset
// as the smallest (arrival - stamp) it saw in the last two seconds, so a late message cannot pull
// it, and the delay is the usual gap between spots plus twice how late they usually are, kept
// within minDelay..maxDelay. The drawn moment follows a change of either at most 20% faster or
// slower than real time, so the player never jumps back or forth when they change. A late player
// is drawn on a guess (going on at their last speed); when the next spot shows the guess was off
// (they had started or stopped), the difference is drawn away over about a tenth of a second.
//
// A published library folder never changes (AGENTS.md, "3D games"): a fix goes in sulava-2/.
(function () {
  'use strict';
  var now = function () { return performance.now() / 1000; };
  var KEEP = 8, WINDOW = 2, CATCH = 0.2;

  function wrap(d) { while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI; return d; }

  function track(opt) {
    opt = opt || {};
    var keys = opt.keys || ['x', 'y'], angles = {}, i;
    for (i = 0; i < (opt.angles || []).length; i++) angles[opt.angles[i]] = true;
    var jump = opt.jump === undefined ? Infinity : opt.jump;
    var minD = opt.minDelay === undefined ? 0.06 : opt.minDelay;
    var maxD = opt.maxDelay === undefined ? 0.25 : opt.maxDelay;
    var extra = opt.extra === undefined ? 0.25 : opt.extra;
    var S = [], lags = [], gap = 0.1, late = 0.02, pt = null, last = null;
    // When the player was drawn on a guess (past the newest spot) and a spot then comes that says
    // otherwise, the difference is drawn away over EASE s instead of in one frame: err, per key.
    var out = {}, was = {}, err = {}, guessed = false, heard = 0, seen = 0, EASE = 0.1;
    // After a jump of the drawn moment (the first frame, a page that slept) no guess is drawn until a
    // new spot comes: the player waits at the newest spot known.
    var still = false;
    var api = { time: null, delay: Math.min(maxD, Math.max(minD, 0.12)), push: push, snap: snap, at: at, reset: reset, size: function () { return S.length; } };

    function copy(v) { var o = {}; for (var k = 0; k < keys.length; k++) o[keys[k]] = +v[keys[k]] || 0; return o; }
    function far(a, b) {
      if (!(jump < Infinity)) return false;
      var dx = a[keys[0]] - b[keys[0]], dy = keys[1] ? a[keys[1]] - b[keys[1]] : 0;
      return Math.sqrt(dx * dx + dy * dy) > jump;
    }
    function reset() { S = []; lags = []; pt = null; last = null; err = {}; guessed = false; }
    function offset() { var m = Infinity; for (var k = 0; k < lags.length; k++) if (lags[k][1] < m) m = lags[k][1]; return m; }
    function lag(a, t) {
      lags.push([a, a - t]);
      while (lags.length > 1 && lags[0][0] < a - WINDOW) lags.shift();
    }
    function snap(t, v, a) {
      a = a === undefined ? now() : a;
      if (t === null || t === undefined) t = a;
      reset();
      S.push({ t: t, v: copy(v) });
      lag(a, t);
      pt = t - api.delay;
      last = a;
    }
    function push(t, v, a) {
      a = a === undefined ? now() : a;
      if (t === null || t === undefined) t = a;
      var n = S.length ? S[S.length - 1] : null, s = copy(v);
      if (!n || t < n.t - 1 || far(n.v, s)) { snap(t, v, a); return; }  // the first spot, a restarted clock, a jump
      if (t <= n.t) return;                                              // old or repeated: already heard
      var g = t - n.t;
      if (g < 1) gap += (g - gap) * 0.2;
      S.push({ t: t, v: s });
      heard++; still = false;
      if (S.length > KEEP) S.shift();
      lag(a, t);
      late += ((a - t) - offset() - late) * 0.2;
      var want = Math.min(maxD, Math.max(minD, gap + 2 * late));
      api.delay += (want - api.delay) * 0.2;
    }
    function blend(a, b, f, o) {
      for (var k = 0; k < keys.length; k++) {
        var key = keys[k], d = b[key] - a[key];
        if (angles[key]) d = wrap(d);
        o[key] = a[key] + d * f;
      }
      return o;
    }
    // Where the spots put the player at moment p (into o); sets guess when p is past the newest spot.
    var guess = false;
    function sample(p, o) {
      var first = S[0], n = S[S.length - 1];
      guess = false;
      if (p <= first.t) return blend(first.v, first.v, 0, o);
      for (var k = 1; k < S.length; k++) if (p <= S[k].t) {
        var q0 = S[k - 1];
        return blend(q0.v, S[k].v, (p - q0.t) / (S[k].t - q0.t), o);
      }
      guess = true;
      var q = S[S.length - 2];
      if (still || !q || n.t - q.t > 0.5) return blend(n.v, n.v, 0, o);  // no speed to go on with
      return blend(q.v, n.v, 1 + Math.min(p - n.t, extra) / (n.t - q.t), o);
    }
    function at(a) {
      if (!S.length) return null;
      a = a === undefined ? now() : a;
      var target = a - offset() - api.delay;
      var dt = last === null ? 0 : a - last;
      last = a;
      if (pt === null || dt > 1 || dt < 0 || Math.abs(target - pt) > 1) { pt = target; still = true; }  // first frame, or the page slept
      else pt += dt + Math.max(-CATCH * dt, Math.min(CATCH * dt, target - pt - dt));
      var k, key, fade = Math.exp(-Math.max(0, dt) / EASE);
      if (guessed && heard !== seen && api.time !== null && dt > 0 && dt <= 1) {
        // A spot came after a guessed frame: what that frame should have drawn, by the spots now known.
        sample(api.time, was);
        for (k = 0; k < keys.length; k++) {
          key = keys[k];
          var d = out[key] - was[key];
          if (angles[key]) d = wrap(d);
          err[key] = d;
        }
      }
      seen = heard;
      api.time = pt;
      var o = sample(pt, out);
      guessed = guess;
      for (k = 0; k < keys.length; k++) {
        key = keys[k];
        if (!err[key]) continue;
        err[key] *= fade;
        if (Math.abs(err[key]) < 1e-4) err[key] = 0;
        o[key] += err[key];
      }
      return o;
    }
    return api;
  }

  window.AiPelitSulava = { track: track, now: now };
})();
