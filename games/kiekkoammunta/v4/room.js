// Shooting in turns in a room (#339). Every player shoots the same 25 discs, about five a turn.
// The host keeps `match`: whose turn it is and every player's results. The phone on turn plays
// its own discs with the same code as a round alone, so a shot never waits for the network, tells
// the host after each target, and sends what it does as `live` messages for the others to draw.
// A lost `live` costs only a moment of the picture: `state` and `entry` carry everything that counts.
"use strict";
// The first target of each of a player's five turns, then the end of the list. Skeet's doubles
// make its turns 4, 5, 5, 5 and 6 discs.
const TURNS = { trap: [0, 5, 10, 15, 20, 25], skeet: [0, 3, 6, 10, 13, 17] };
let roomMode = load("huonelaji", "trap") === "skeet" ? "skeet" : "trap",
  roomEl = null,
  lastAim = 0;
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
function live(k, data) {
  if (online && match && round && !round.watch)
    R.send({ t: "live", k, round: roomRound, seq: shooting, ...data });
}
function liveAim() {
  const now = performance.now();
  if (!online || now - lastAim < 100) return;
  lastAim = now;
  live("aim", { aim: round.aim });
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
  aimTo = null;
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
function hear(m) {
  if (m.k === "fly") {
    if (!Array.isArray(m.discs) || m.discs.length > 2 || !m.discs.every((d) =>
        d && ["x", "y", "z", "vx", "vy", "vz", "age"].every((k) => Number.isFinite(d[k]))))
      return;
    syncView(true);
    if (!round || !round.watch) return;
    round.phase = "flight";
    round.discs = m.discs.map((d) => ({ ...d }));
    round.message = "";
  }
  if (!round || !round.watch || screen !== "play") return;
  if (m.aim && Number.isFinite(m.aim.yaw) && Number.isFinite(m.aim.pitch)) {
    if (m.k === "fly") round.aim = { yaw: m.aim.yaw, pitch: m.aim.pitch };
    aimTo = { yaw: m.aim.yaw, pitch: m.aim.pitch };
  }
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
  aimTo = null;
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
    aimTo = null;
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
