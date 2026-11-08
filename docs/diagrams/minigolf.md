# Minigolf: one round, from the first hole to the result

How a round of Minigolf plays (#340). The course is seen from above, and the whole
hole fits on the screen. Each stroke is aimed by pulling back anywhere on the screen, like a
sling; the ball rolls, bounces off walls, slows in sand and drifts on slopes. Nine holes, each
with its par; alone the player plays against par and their own record, with friends 2–6 phones
take turns on each hole through the shared room library (see `moninpeli.md`).
Minigolf v3 makes every visible aim playable at a small minimum power and lets firmer putts
drop into the cup, while shots that are still too fast continue across it.

```mermaid
flowchart TD
  S{Miten pelataan?}
  S -- Pelaa --> A
  S -- Jatka kierrosta --> A2[Kesken jäänyt kierros jatkuu samasta reiästä]
  S -- Kavereiden kanssa --> R[Huone: 2–6 puhelinta, jokainen eri värisellä pallolla]
  R --> R2[Huoneen tekijä pyörittää kierrosta, vuorossa oleva lähettää lyönnin]
  A2 --> B
  R2 --> A
  A[Reikä alkaa: koko rata näkyy, par kerrottu] --> A3[Aloittaja vaihtuu joka reiälle vuorotellen]
  A3 --> B{Kenen vuoro?}
  B --> C[Vedä mistä tahansa taaksepäin: viiva näyttää suunnan ja voiman]
  C --> D{Näkyykö nuoli?}
  D -- Ei --> C
  D -- Kyllä --> E[Päästä irti: pallo lähtee vähintään minimivoimalla]
  E --> F[Pallo vierii: seinät kimmottavat, hiekka hidastaa, rinne kallistaa, tuulimylly torjuu]
  F --> G{Mihin pallo päätyy?}
  G -- Veteen --> H[+1 lyönti, pallo takaisin lyöntipaikalle]
  G -- Reiän yli yhä liian kovaa --> I[Pallo hyppää reiän yli ja vierii eteenpäin]
  G -- Reikään aiempaa kovemmalla vauhdilla --> J[Reiässä: lyönnit kirjataan]
  G -- Pysähtyy --> K{Vähintään 6 lyöntiä?}
  H --> K
  I --> F
  K -- Ei --> B
  K -- Kyllä --> L[Reiän tulos 7, siirrytään eteenpäin]
  J --> M{Kaikki reiässä tai tulos 7?}
  L --> M
  M -- Ei, seuraava pelaaja --> B
  M -- Kyllä --> N{Yhdeksän reikää pelattu?}
  N -- Ei --> V[Yksin seuraava reikä itsestään, kavereiden kanssa tuloskortti ja Seuraava reikä]
  V --> A
  N -- Kyllä --> O[Tuloskortti: lyönnit, par, ero]
  O --> P{Yksin vai kavereiden kanssa?}
  P -- Yksin --> Q[Ennätys ja tuloslista, Pelaa uudestaan]
  P -- Kavereiden kanssa --> T[Tulos kaikille kerran, takaisin huoneeseen]
  class R,R2,T violet
  class S,B,D,G,K,M,N,P amber
  class A,A2,A3,C,E,O,V blue
  class F,I teal
  class J,Q green
  class H,L rose
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the path
- **teal**: the ball moving
- **violet**: playing in a room
- **green**: a hole made, a record
- **rose**: a penalty or the stroke limit

## Boxes

- **Miten pelataan?**: the menu in `games/minigolf/v3/index.html`: **Pelaa** (`newRound()`), **Jatka kierrosta** when a round alone was left unfinished (saved on release, after every stroke and when the page hides as `ai-pelit:minigolf:kierros`), **👥 Pelaa kavereiden kanssa** (`AiPelitRooms.open()`), the best total, and the top 10 as a short scrolling list (`#menuBoard`, filled by `menu()` from `AiPelitScores.list`), with **🏆 Tuloslista** for the whole list.
- **Huone: 2–6 puhelinta, jokainen eri värisellä pallolla**: `rooms.js` with `data-min="2" data-max="6"`; each player's ball gets its own colour in room order, and `updateHUD()` shows the players as a row of those colours with names (`#who`), the one on turn marked.
- **Huoneen tekijä pyörittää kierrosta, vuorossa oleva lähettää lyönnin**: the host runs the physics and sends snapshots (as Curling does); the phone on turn sends `aim` while dragging and `shot` when it lets go. `turns()` makes the room wait only for the phone on turn; "Ohita vuoro" scores that player 7 on the hole.
- **Reikä alkaa: koko rata näkyy, par kerrottu**: `nextHole()` in `games/minigolf/v3/game.js` reads the hole from `holes.js`; `fit()` scales it to the screen, turned 90° when the phone is sideways.
- **Aloittaja vaihtuu joka reiälle vuorotellen**: in a room, `nextHole()` advances `starterId` through the stable player-id ring and sets `round.turn` from it, so successive holes start with successive players. `keepNextStarter()` saves the next id under `ai-pelit:minigolf:aloittaja:<room code>`, so the rotation continues into the next nine-hole round and survives a host reload; `roomRotation()` drops players no longer in the new round and appends newcomers. Solo play always starts with its only player.
- **Vedä mistä tahansa taaksepäin: viiva näyttää suunnan ja voiman**: `dragAim()`: the ball goes the opposite way to the finger's pull, the pull's length (up to 30 % of the screen's short side) is the power. Only the aim line shows it (`drawAimLine()` in `draw.js`, #438; no power bar since v2): an arrow from the ball that grows longer (`aimLineLength()`, 0.35–3.45 m), thicker and from pale yellow to red (`aimLineColor()`) as the pull grows. Turning the phone mid-pull keeps the aim: `fit()` marks the drag to re-anchor at the finger, and if the browser cancels the pointer in the turn the aim stays parked (`parkedAim`) until the next drag or tap; it never fires by itself.
- **Näkyykö nuoli?**: Minigolf v3 removes v2's 15 px release threshold in `draw.js`. A tap with no aim still does nothing, but once a non-zero pull has made the arrow visible, releasing always starts a stroke.
- **Päästä irti: pallo lähtee vähintään minimivoimalla**: `shoot()` in `game.js` clamps any visible pull below 10 % power to that minimum, so even a one-pixel aim moves the ball a small but visible distance. Larger pulls keep their existing proportional power, including full power.
- **Pallo vierii: seinät kimmottavat, hiekka hidastaa, rinne kallistaa, tuulimylly torjuu**: `step(dt)` in `game.js` calls `golfStep()` in `golf.js`, fixed 1/240 s steps so a fast ball never passes through a wall.
- **Pallo hyppää reiän yli ja vierii eteenpäin**: the ball drops only when it is over the cup slower than the capture speed (`CUP_SPEED` in `golf.js`). Minigolf v3 raises it from 1.4 to 2.3 m/s, so ordinary firm putts drop while a near-full-speed shot can still lip out.
- **Reiän tulos 7, siirrytään eteenpäin**: the stroke limit of Finnish rata-minigolf: a ball not holed in six strokes scores 7.
- **Tuloskortti: lyönnit, par, ero**: `showCard()` in `game.js`; alone, this round and each hole's record (`reiat`, column Ennätys); with friends, every player's column.
- **Ennätys ja tuloslista, Pelaa uudestaan**: `finishRecord()` saves `paras` and `reiat` the moment the last hole is done, in a round alone only; `AiPelitScores.submit(total, true)` with `data-order="low"`; on the phone's first score `showCard()` then calls `AiPelitScores.prompt()`, so the nickname question comes over the finished card. A round in a room counts only in `kaverit`.
- **Tulos kaikille kerran, takaisin huoneeseen**: `AiPelitRooms.deliver()`; each phone saves its result once (`once(round)`).

- **Yksin seuraava reikä itsestään, kavereiden kanssa tuloskortti ja Seuraava reikä**: alone, `advance()` shows the hole's result as a notice (a touch on the course hides any notice at once, `hideNotice()`) and `step()` calls `nextHole()` after 1.2 s, with no scorecard between holes; the card comes at the end. In a room, `showCard()` shows all nine rows and the running totals after each hole, and `nextHole()` begins the next when the host taps.
- **+1 lyönti, pallo takaisin lyöntipaikalle**: `settle()` adds one penalty, capped at 7, and restores `round.origin`. If that brings the count to at least six without holing, the hole scores 7.
- **Tulos kaikille kerran, takaisin huoneeseen**: the retained `result` includes the complete scorecard. A reloaded phone gets it in the room's expandable result card (`R.extra`), since the shared library opens the room after a completed round. New rounds clear the card; stopping a round clears game state on every phone.

`public/scores.js` and `server/api.js` register `minigolf`, lowest nine-hole total on `main`, displayed as lyöntiä. Only the host accepts shots, with matching room round, turn sequence and active player id; all other input is ignored. `draw.js` rotates both course and aiming vectors for landscape and sleeps between changes except while a ball or windmill moves. Sound uses the quiet `aanet-5` library; no crowd sounds. Kiekkoammunta v1 adds independent `trap` and `skeet` score entries (Trap first, N/25); this box’s existing behavior is unchanged. Frisbeegolf v1 adds its own `main` entry to these registries: lowest strokes against par wins, displayed as `E`, `−2` or `+5`; this box keeps its existing behavior. Frisbeegolf now uses its separate `v3` leaderboard; versions 1–2 are not accepted there (#338). From v5 (#429) its rounds go to a new `v5` list, the shelf's first, and the `v3` list stays for v3–v4. Kaaosrata v6 (#454) adds `hihna`, `laatat` and `finaali` to its separate score entry; `main` keeps its old times and remains its first list. This box keeps its existing behaviour.
