// Shooting in turns in a room (#339). Every player shoots the same 25 discs, about five a turn.
// The host keeps `match`: whose turn it is and every player's results. The phone on turn plays
// its own discs with the same code as a round alone, so a shot never waits for the network, tells
// the host after each target, and sends what it does as `live` messages for the others to draw.
// A lost `live` costs only a moment of the picture: `state` and `entry` carry everything that counts.
// v4 (#540): a watching phone draws the shooter's aim from lib/sulava-1, a moment in the past, and
// holds the disc launches, shots and hits until that moment, so the sight and the discs stay together.
"use strict";
// The first target of each of a player's five turns, then the end of the list. Skeet's doubles
// make its turns 4, 5, 5, 5 and 6 discs.
const TURNS = { trap: [0, 5, 10, 15, 20, 25], skeet: [0, 3, 6, 10, 13, 17] };
let roomMode = load("huonelaji", "trap") === "skeet" ? "skeet" : "trap",
  roomEl = null,
  lastAim = 0,
  sentAim = null,
  aimTimer = 0;
// A watching phone: the shooter's aim (one track per turn, `trackSeq`), the other `live` messages
// waiting for the drawn moment to reach them (`held`), and when the last aim came (`aimHeard`).
let aimTrack = null,
  trackSeq = 0,
  held = [],
  aimHeard = -9,
  aimNow = null,
  flushTimer = 0;
const cur = () => match.players[match.turn];
const mine = () => cur().id === R.me;
const turnEnd = () => TURNS[match.mode][match.lap + 1];
const hits = (p) => p.results.filter((v) => v === true).length;
function offsetOf(index) {
  return (match.mode === "trap" ? TRAP : SKEET)
    .slice(0, index)
    .reduce((n, e) => n + e[1].length, 0);
}
function sendState(to) {
  if (online && R.isHost && match)
    R.send({ t: "state", round: roomRound, match }, to);
}
// Every `live` carries the shooter's own clock (`at`), which the watchers' track learns to follow.
function live(k, data) {
  if (online && match && round && !round.watch)
    R.send({ t: "live", k, round: roomRound, seq: shooting, at: AiPelitSulava.now(), ...data });
}
// At most ten aims a second while the finger moves, and one more once it stops: without that last
// one a watching phone would carry the sight on at its last speed and leave it past where it stopped.
// `jump` (a new target) is drawn there at once instead of gliding from the last target's aim.
function liveAim(force, jump) {
  if (!online || !round || round.watch) return;
  clearTimeout(aimTimer);
  aimTimer = 0;
  const now = performance.now(),
    wait = 100 - (now - lastAim);
  if (!force && wait > 0) {
    aimTimer = setTimeout(liveAim, wait, true);
    return;
  }
  const same = sentAim && sentAim.yaw === round.aim.yaw && sentAim.pitch === round.aim.pitch;
  lastAim = now;
  sentAim = { yaw: round.aim.yaw, pitch: round.aim.pitch };
  live("aim", jump ? { aim: sentAim, jump: true } : { aim: sentAim });
  if (!same) aimTimer = setTimeout(liveAim, 110, true);
}
// A watching phone, each frame: the aim the track draws now, and the messages whose moment it reached.
function watchTick() {
  if (!aimTrack) return;
  aimNow = aimTrack.at();
  const t = aimTrack.time;
  while (held.length && (t === null || !(held[0].at > t))) play(held.shift());
  watchAim();
  // rAF stops on a hidden page, and between draws: the held hits still land, on a timer.
  clearTimeout(flushTimer);
  flushTimer = held.length ? setTimeout(watchTick, 40) : 0;
}
// The sampled aim goes on the round last: a held `fly` (syncView, view, prepare) and a watcher's gap
// ending in step() both reset round.aim to a target's start, which would show for one frame.
function watchAim() {
  if (aimNow && round && round.watch && round.seq === trackSeq) {
    round.aim.yaw = aimNow.yaw;
    round.aim.pitch = aimNow.pitch;
  }
}
// Keep drawing while the sight may still glide: its delay, the guess past the last aim, the easing.
function watchBusy() {
  return online && (held.length > 0 || AiPelitSulava.now() - aimHeard < 1.2);
}
function dropTrack() {
  aimTrack = null;
  aimNow = null;
  trackSeq = 0;
  held = [];
  clearTimeout(flushTimer);
  flushTimer = 0;
}
// This phone's turn: tell the host how far it got. The results are the whole list, so a message
// lost while the phone was off the network is made up for by the next one.
function report() {
  const m = {
    t: "entry",
    round: roomRound,
    seq: shooting,
    index: round.index,
    results: round.results,
  };
  if (R.isHost) takeEntry(R.me, m);
  else R.send(m);
}
function ownEntryDone() {
  if (round.index >= turnEnd()) {
    round.phase = "wait";
    round.discs = [];
    round.shots = [];
    round.message = "";
  } else prepare();
  hud();
  report();
}
function takeEntry(id, m) {
  if (id !== cur().id || m.seq !== match.seq || !Number.isInteger(m.index) ||
      m.index <= match.index || m.index > turnEnd() || !Array.isArray(m.results))
    return;
  const from = offsetOf(match.index),
    to = offsetOf(m.index);
  for (let i = from; i < to; i++)
    if (typeof m.results[i] !== "boolean") return;
  for (let i = from; i < to; i++) cur().results[i] = m.results[i];
  match.index = m.index;
  if (match.index === turnEnd()) nextTurn();
  else {
    sendState();
    syncView();
  }
}
function nextTurn() {
  match.seq++;
  match.turn++;
  if (match.turn === match.players.length) {
    match.turn = 0;
    match.lap++;
  }
  if (match.lap === TURNS[match.mode].length - 1) {
    match.over = true;
    R.deliver({ t: "result", round: roomRound, match });
    R.endRound();
  } else {
    match.index = TURNS[match.mode][match.lap];
    sendState();
  }
  syncView();
}
// Draw the target the round is at, for the phone on turn or for one watching it.
function view() {
  const own = mine(),
    wasWatching = !round || round.watch;
  round = {
    mode: match.mode,
    index: match.index,
    offset: offsetOf(match.index),
    results: cur().results.slice(),
    phase: "ready",
    discs: [],
    shots: [],
    ammo: 0,
    shotIndex: 0,
    aim: { yaw: 0, pitch: 0.12 },
    time: 0,
    gap: 0,
    message: "",
    watch: !own,
    seq: match.seq,
  };
  shooting = own ? match.seq : 0;
  prepare();
  showPlay();
  if (own && wasWatching) sound("onnistui", 0.06);
}
function syncView(force) {
  if (!online || !match) return;
  if (match.over) {
    roomEnd();
    return;
  }
  if (mine() && round && shooting === match.seq) {
    if (round.index > match.index) report();
    hud();
    return;
  }
  // A watching phone lets the disc in the air finish; the end of its gap brings it back here.
  const watching = round && round.watch && round.seq === match.seq;
  const busy = round && round.watch && (round.phase === "flight" || round.phase === "gap");
  if (!force && (busy || (watching && round.index === match.index))) {
    hud();
    return;
  }
  view();
}
// A `live` from the phone on turn: its aim goes on the track at once, the rest waits for its moment.
function hear(m) {
  if (mine()) return;
  if (!Number.isFinite(m.at)) m.at = null;
  if (m.seq !== trackSeq) {
    // A new turn, and a new phone's clock: what the last turn still held is drawn now.
    while (held.length) play(held.shift());
    aimTrack = AiPelitSulava.track({ keys: ["yaw", "pitch"] });
    aimNow = null;
    trackSeq = m.seq;
  }
  if (m.aim && Number.isFinite(m.aim.yaw) && Number.isFinite(m.aim.pitch)) {
    const aim = { yaw: m.aim.yaw, pitch: m.aim.pitch };
    if (m.jump) aimTrack.snap(m.at, aim);
    else aimTrack.push(m.at, aim);
    aimHeard = AiPelitSulava.now();
  }
  if (m.k !== "aim") held.push(m);
  watchTick();
  wake();
}
function play(m) {
  if (m.k === "fly") {
    if (!match || m.seq !== match.seq) return;
    if (!Array.isArray(m.discs) || m.discs.length > 2 || !m.discs.every((d) =>
        d && ["x", "y", "z", "vx", "vy", "vz", "age"].every((k) => Number.isFinite(d[k]))))
      return;
    syncView(true);
    if (!round || !round.watch) return;
    round.phase = "flight";
    round.discs = m.discs.map((d) => ({ ...d }));
    round.message = "";
  }
  if (!round || !round.watch || screen !== "play" || round.seq !== m.seq) return;
  if (m.k === "shot" && m.shot && Number.isFinite(m.shot.delay)) {
    round.shots.push({ ...m.shot });
    round.ammo = Math.max(0, round.ammo - 1);
    round.shotIndex++;
    flash = 0.14;
    sound("lahto", 0.19, 0.8);
  }
  if (m.k === "res") {
    const d = round.discs.find((d) => d.slot === m.slot);
    if (d) resolveDisc(d, m.hit === true);
  }
  hud();
  wake();
}
function receive(m, from) {
  if (!online || !m || m.round !== roomRound) return;
  if (R.isHost) {
    if (!match || match.over) return;
    if (m.t === "entry") takeEntry(from, m);
    if (m.t === "live" && from === cur().id && m.seq === match.seq) {
      R.send(m);
      hear(m);
    }
  } else if (from === roomHost) {
    if ((m.t === "state" || m.t === "result") && m.match && Array.isArray(m.match.players)) {
      match = m.match;
      syncView();
    }
    if (m.t === "live" && match && m.seq === match.seq) hear(m);
  }
}
function who() {
  $("who").hidden = false;
  $("who").replaceChildren(
    ...match.players.map((p, i) => {
      const n = document.createElement("span");
      n.textContent = p.name + " " + (i === match.turn && round ? count() : hits(p));
      if (i === match.turn) n.className = "on";
      return n;
    }),
  );
}
function watchHint(pair) {
  const small = document.createElement("small");
  small.textContent = pair ? "Tupla" : "Kiekko " + (round.offset + 1) + "/25";
  $("hint").textContent = cur().name + " ampuu";
  $("hint").append(small);
}
function standings() {
  const rows = [...match.players].sort((a, b) => hits(b) - hits(a));
  return rows.map((p) => ({
    name: p.name,
    id: p.id,
    score: hits(p),
    rank: 1 + rows.filter((q) => hits(q) > hits(p)).length,
  }));
}
function roomEnd() {
  const rows = standings(),
    me = rows.find((r) => r.id === R.me),
    name = match.mode === "trap" ? "Trap" : "Skeet";
  // Solo records and room results stay apart, as in Minigolf.
  if (me && R.once(roomRound)) {
    const saved = load("kaverit", { rounds: 0, best: 0 });
    save("kaverit", {
      rounds: (saved.rounds || 0) + 1,
      best: Math.max(saved.best || 0, me.score),
    });
  }
  screen = "result";
  pointer = null;
  boardRequest++;
  for (const id of ["menu", "hud", "hint", "ammo", "pause"]) $(id).hidden = true;
  $("result").hidden = false;
  $("resultLabel").textContent = name + " · huone";
  $("resultScore").textContent = (me ? me.score : 0) + "/25";
  const shared = me && rows.filter((r) => r.rank === me.rank).length > 1;
  $("record").textContent = me
    ? (shared ? "Jaettu " : "") + me.rank + ". sija · " + rows.length + " pelaajaa"
    : "";
  $("again").textContent = "Takaisin huoneeseen";
  $("toMenu").hidden = true;
  $("boardTitle").textContent = "Huoneen tulokset";
  $("board").replaceChildren(
    ...rows.map((r) => {
      const row = document.createElement("div");
      for (const text of [r.rank + ".", r.name, r.score + "/25"]) {
        const s = document.createElement("span");
        s.textContent = text;
        row.append(s);
      }
      return row;
    }),
  );
  wake();
}
function backToRoom() {
  const rows = standings(),
    first = rows.filter((r) => r.rank === 1),
    me = rows.find((r) => r.id === R.me);
  R.backToRoom(
    (first.length > 1 ? "Tasapeli" : first[0].name + " voitti") + " · " + first[0].score + "/25",
    me && me.rank === 1 ? "win" : "lose",
  );
}
function roomWait() {
  screen = "wait";
  for (const id of ["menu", "result", "hud", "ammo", "pause"]) $(id).hidden = true;
  $("hint").hidden = false;
  $("hint").textContent = "Odotetaan huoneen tekijää…";
  wake();
}
function leaveRound() {
  online = false;
  match = null;
  round = null;
  shooting = 0;
  dropTrack();
  $("who").hidden = true;
  $("again").textContent = "Uudestaan";
  $("toMenu").hidden = false;
  $("boardTitle").textContent = "Parhaat tulokset · vieritä";
  showMenu();
}
// In a room the host picks the discipline under the players; the others see who picks.
function roomControls() {
  if (!roomEl) {
    roomEl = document.createElement("div");
    roomEl.id = "kk-room";
    roomEl.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b || !R.isHost) return;
      roomMode = b.dataset.m;
      save("huonelaji", roomMode);
      roomControls();
    });
    R.extra(roomEl);
  }
  if (R.isHost) {
    const row = document.createElement("div");
    row.className = "chips";
    for (const [m, text] of [["trap", "Trap"], ["skeet", "Skeet"]]) {
      const b = document.createElement("button");
      b.dataset.m = m;
      b.textContent = text;
      if (m === roomMode) b.className = "on";
      row.append(b);
    }
    roomEl.replaceChildren(row);
  } else {
    const h = R.members && R.members.find((m) => m.id === R.hostId),
      p = document.createElement("p");
    p.className = "help";
    p.textContent = "Lajin valitsee " + (h ? h.name : "huoneen tekijä") + ".";
    roomEl.replaceChildren(p);
  }
}
if (R) {
  R.turns((id) => !!(online && match && !match.over && cur().id === id));
  R.on("start", (s) => {
    online = true;
    roomRound = s.round;
    roomHost = R.hostId;
    match = null;
    round = null;
    shooting = 0;
    dropTrack();
    pointer = null;
    effects = [];
    if (R.isHost) {
      match = {
        mode: roomMode,
        seq: 1,
        lap: 0,
        turn: 0,
        index: 0,
        over: false,
        players: s.players.map((p) => ({
          id: p.id,
          name: p.name,
          results: Array(25).fill(null),
        })),
      };
      sendState();
      syncView();
    } else roomWait();
  });
  R.on("message", receive);
  R.on("hello", (id) => sendState(id));
  // The host skips an away player's turn: the discs left in it are misses.
  R.on("skip", (ids) => {
    if (!online || !R.isHost || !match || match.over || !ids.includes(cur().id)) return;
    const to = offsetOf(turnEnd());
    for (let i = offsetOf(match.index); i < to; i++) cur().results[i] = false;
    nextTurn();
  });
  R.on("peers", roomControls);
  R.on("lobby", leaveRound);
  R.on("menu", leaveRound);
  R.on("leave", leaveRound);
}
