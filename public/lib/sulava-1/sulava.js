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
// slower than real time, so the player never jumps back or forth when they change.
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
    var out = {};
    var api = { delay: Math.min(maxD, Math.max(minD, 0.12)), push: push, snap: snap, at: at, reset: reset, size: function () { return S.length; } };

    function copy(v) { var o = {}; for (var k = 0; k < keys.length; k++) o[keys[k]] = +v[keys[k]] || 0; return o; }
    function far(a, b) {
      if (!(jump < Infinity)) return false;
      var dx = a[keys[0]] - b[keys[0]], dy = keys[1] ? a[keys[1]] - b[keys[1]] : 0;
      return Math.sqrt(dx * dx + dy * dy) > jump;
    }
    function reset() { S = []; lags = []; pt = null; last = null; }
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
      if (S.length > KEEP) S.shift();
      lag(a, t);
      late += ((a - t) - offset() - late) * 0.2;
      var want = Math.min(maxD, Math.max(minD, gap + 2 * late));
      api.delay += (want - api.delay) * 0.2;
    }
    function blend(a, b, f) {
      for (var k = 0; k < keys.length; k++) {
        var key = keys[k], d = b[key] - a[key];
        if (angles[key]) d = wrap(d);
        out[key] = a[key] + d * f;
      }
      return out;
    }
    function at(a) {
      if (!S.length) return null;
      a = a === undefined ? now() : a;
      var target = a - offset() - api.delay;
      var dt = last === null ? 0 : a - last;
      last = a;
      if (pt === null || dt > 1 || dt < 0 || Math.abs(target - pt) > 1) pt = target;  // first frame, or the page slept
      else pt += dt + Math.max(-CATCH * dt, Math.min(CATCH * dt, target - pt - dt));
      var first = S[0], n = S[S.length - 1];
      if (pt <= first.t) return blend(first.v, first.v, 0);
      for (var k = 1; k < S.length; k++) if (pt <= S[k].t) {
        var p = S[k - 1];
        return blend(p.v, S[k].v, (pt - p.t) / (S[k].t - p.t));
      }
      var q = S[S.length - 2];
      if (!q || n.t - q.t > 0.5) return blend(n.v, n.v, 0);  // no speed to go on with
      return blend(q.v, n.v, 1 + Math.min(pt - n.t, extra) / (n.t - q.t));
    }
    return api;
  }

  window.AiPelitSulava = { track: track, now: now };
})();
