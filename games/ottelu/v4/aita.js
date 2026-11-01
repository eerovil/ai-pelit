// The 100 m hurdles in the match (#287). Aitajuoksu has no athletics library to patch, so the
// match page loads this file after the race's own script, in the race's frame, and changes the
// race there; the published race (games/aitajuoksu/v7/) is untouched. A classic script shares
// the race's globals: its functions are replaced here by name, its `let`s are read and set.
//
// In the match the race is always 100 m with hurdles, run by the match's eight athletes (the same
// names, colours and ids as in the field events, from Ottelu.field()), one run, and its results
// go to the match instead of the race's own saves, high scores and menu.
(function () {
  'use strict';
  var O = parent.Ottelu;
  dist = 100; hurdles = true;
  setTrack(100, true);

  // The computer's runners tap faster the higher the match's level, as Aitajuoksu's do, spread
  // around it so the field strings out.
  var SPREAD = [0.4, 0.2, 0, -0.15, -0.3, -0.5, -0.7, -0.9];
  function cpuRate(k) { return Math.min(10.2, 6.5 + 0.4 * ((O.level() || 1) - 1)) + SPREAD[k % SPREAD.length]; }
  // This race's runners as the match's field: a phone's runner keeps the race's own id (its
  // phone's, or 'me' alone) and gets the match's as `mid`; the computer's are added after them.
  function dress(rs) {
    var f = O.field(), humans = f.filter(function (a) { return a.p !== null; });
    rs.forEach(function (r) {
      var a = humans.find(function (h) { return h.p === r.id; });
      if (a) { r.mid = a.id; r.name = a.name; r.color = a.col; }
    });
    f.filter(function (a) { return a.p === null; }).forEach(function (a, k) {
      var host = race.mode === 'solo' || R.isHost;
      var r = runner(a.id, a.name, a.col, host ? 'cpu' : 'net', cpuRate(k));
      r.mid = a.id;
      rs.push(r);
    });
    layout();
  }
  soloRace = function () {
    newRace('solo', '', [runner('me', 'Sinä', '#3f8ad8', 'me', 0, outfit.id)], 100, true);
    dress(race.runners);
  };
  // With friends the race's own start makes the phones' runners; the computer's join on every
  // phone, in the same lanes, and the host runs them.
  R.on('start', function () { if (race && race.mode === 'net') dress(race.runners); });

  // A red card alone is out of this race, not out of the match: the others run it to the end.
  afterFalse = function () { countdown(); };
  var tick0 = tick;
  tick = function (dt) {
    tick0(dt);
    if (race && race.mode === 'solo' && race.phase === 'run' && me.card >= 2 && race.runners.every(out)) soloOver();
  };

  // The results: shown by the race as ever, then to the match, with nothing saved for Aitajuoksu.
  finish = function (res) {
    if (!race || race.phase === 'done') return;
    race.phase = 'done'; race.doneT = 0; race.results = res;
    var mine = race.mode === 'solo' ? 'me' : R.me;
    race.mine = res.findIndex(function (r) { return r.id === mine; });
    race.time = race.mine >= 0 ? res[race.mine].fin : null;
    var f = O.field();
    O.scored(res.map(function (r) {
      var u = race.runners.find(function (o) { return o.id === r.id; }), a = u && f.find(function (b) { return b.id === u.mid; });
      return a ? { id: a.id, name: a.name, p: a.p, col: a.col, best: r.dq ? null : r.fin } : null;
    }).filter(Boolean));
  };
  afterResults = function () { race = null; O.over(); };

  // The race's results, as the race draws them, with rows short enough that all eight fit
  // between the top bar and the pads on a small phone (the race's own are 30 px a row).
  drawResults = function () {
    var W = SW, res = race.results, top = land ? safeT + 6 : trackTop + 10, bottom = land ? H - safeB - 6 : ctrlTop - 6;
    var rowH = Math.max(18, Math.min(30, Math.floor((bottom - top - 64) / res.length))), h = 60 + rowH * res.length;
    var y0 = land ? Math.max(top, Math.min(trackTop + 10, bottom - h)) : top;
    var fs = Math.min(17, rowH - 6);
    x.fillStyle = 'rgba(10,20,40,.88)'; rr(20, y0, W - 40, h, 16); x.fill();
    x.fillStyle = '#ffd166'; x.textAlign = 'center'; x.font = '900 22px system-ui';
    x.fillText('Tulokset', W / 2, y0 + 34);
    res.forEach(function (r, i) {
      var y = y0 + 58 + (i + 0.7) * rowH, mine = i === race.mine;
      x.fillStyle = r.color; x.beginPath(); x.arc(44, y - fs * 0.35, Math.min(7, fs * 0.4), 0, 7); x.fill();
      x.textAlign = 'left'; x.font = (mine ? '900 ' : '600 ') + fs + 'px system-ui'; x.fillStyle = mine ? '#ffd166' : '#fff';
      var name = race.mode === 'net' && r.id === R.me ? 'Sinä' : r.name;
      x.fillText((i + 1) + '. ' + name, 58, y);
      x.textAlign = 'right'; x.fillText(r.dq ? 'Hylätty' : r.fin === null ? '–' : fmt(r.fin), W - 36, y);
    });
    race.resultsBox = { top: y0, bottom: y0 + h };
  };
})();
