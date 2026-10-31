# Pituushyppy: one jump and one meet

How Pituushyppy plays (v1). A meet has twelve jumpers: the player and eleven computer jumpers
alone, or 2–8 phones in a room with the computer filling the rest. Everyone jumps three times in a
drawn order; the best eight jump three more, the last in the standings first. On their turn the
player takes a run-up by tapping the left and right foot in turn, holds "Hyppää" from the check
mark so the take-off angle rises, and lets go on the board before the line. In the air a tap throws
the legs forward for the landing. The computer's jumps are worked out at once.

```mermaid
flowchart TD
  M[Valikko: Kisaan!, Jatka kisaa tai kaverit] --> K[Kisa: 12 hyppääjää, arvottu järjestys]
  K --> T[Tulostaulu: kierros, sijat, viimeisin ja paras]
  T --> Q{Kenen vuoro?}
  Q -- Tietokone tai poissa oleva --> CPU[Tietokone hyppää heti]
  CPU --> NX
  Q -- Pelaaja tällä puhelimella --> R[Vauhdinotto: vasen, oikea vuorotellen]
  Q -- Kaveri toisella puhelimella --> WT[Kaverin hyppy näkyy, sama lento]
  R --> LN{Yli viivan ja armon ilman ponnistusta?}
  LN -- Kyllä --> X[X: yliastuttu, punainen lippu]
  LN -- Ei --> A[Pidä Hyppää merkistä: kulma nousee]
  A --> RL{Kosketus alle 0,1 s?}
  RL -- Kyllä --> R
  RL -- Ei --> F[Päästä irti laudalla: ponnistus]
  F --> L{Jalat eteen ajoissa?}
  L -- Liian aikaisin tai ei lainkaan --> DR[Jalat putoavat: lyhyempi]
  L -- Juuri ennen hiekkaa --> D
  L -- Liian myöhään --> HB[Kädet hiekkaan: paljon lyhyempi]
  DR --> D[Tulos viivasta lähimpään jälkeen, valkoinen lippu]
  HB --> D
  WT --> D
  WT --> X
  D --> NX{Kierros täynnä?}
  X --> NX
  NX -- Ei --> T
  NX -- Kolmas kierros --> CUT[8 parasta jatkaa, viimeisestä alkaen]
  NX -- Kuudes kierros --> END[Lopputulokset ja mitalit]
  CUT --> T
  END --> S[Ennätys, tuloslista, voitosta seuraava taso]
  S --> M
  END --> RM[Huoneessa: sijat kaikille, takaisin huoneeseen]
  class M,R,A,F,T blue
  class CPU,WT violet
  class Q,LN,RL,L,NX amber
  class K,D,DR,HB,CUT teal
  class X rose
  class END,S,RM green
```

## Colours

- **blue**: what the player sees and does
- **violet**: someone else jumping: the computer, or a friend on another phone
- **amber**: a check that decides the path
- **teal**: the meet's rules and the measured jump
- **rose**: a foul, marked X
- **green**: the end of the meet and what it saves

## Boxes

- **Valikko: Kisaan!, Jatka kisaa tai kaverit**: `showMenu()` in `games/pituushyppy/v1/index.html`. "Kisaan!" starts a new meet at the player's level (`taso`); "Jatka kisaa (kierros N/6)" shows when a meet alone was left unfinished (`kesken`, saved after each of the player's jumps, so a reload or a trip to the shelf keeps it); "👥 Pelaa kavereiden kanssa" opens the room (`public/rooms.js`, 2–8 phones). The menu shows meets, wins and the record (`kisat`, `voitot`, `ennatys`).
- **Kisa: 12 hyppääjää, arvottu järjestys**: `newComp()`: the players, then computer jumpers up to twelve (`FIELD`), each with a skill around `base(level)` metres (5.20 m at level 1, 25 cm more per level up to 7.00 m); the order of rounds 1–3 is drawn once (`order0`), and a seed (`seed`) gives every jump its wind.
- **Tulostaulu: kierros, sijat, viimeisin ja paras**: `drawBoard()`, shown for 3.5 s (`BOARD_T`) before each player's turn; alone a tap skips it. The standings (`standings()`) go by the best jump, then the second best, as in a real meet; a dashed line shows the cut after eight.
- **Kenen vuoro?**: `advance()` jumps for every computer jumper up to the next player on a phone; `follow()` makes the turn each phone draws (`th`), its own (`mine`) or someone else's, with the wind for it (`windFor(seq)`, −1.5 to +2.5 m/s, shown as "Tuuli").
- **Tietokone hyppää heti**: `cpuMark()`: the skill plus a scatter of 20 cm and 5 cm per m/s of wind, a foul about one time in seven. In a room the host's "Jatka ilman heitä" hands an away phone's jumps to the computer (`R.on('continue')`) until it is back (`R.on('back')`); while a phone is away the meet waits (`R.paused`).
- **Vauhdinotto: vasen, oikea vuorotellen**: `press()`: a step on the other foot adds speed, more the slower the jumper goes (as in Keihäänheitto and Aitajuoksu), the same foot twice slows; about 8.3 m/s at eight taps a second. The bar in the score panel shows the speed; the green part of the runway is the last 120 ms of running before the line at the speed now (`ZONE`), so with the grace past the line the clean take-off zone is 200 ms; an earlier release is legal but shorter, as the jump is measured from the line, the yellow "merkki" 2.8 m before it is where to start holding.
- **Yli viivan ja armon ilman ponnistusta?**: `step()` and `overLimit()`: timing is measured in time, not distance, and holding Hyppää never fouls by itself. The foot may pass the line by up to 80 ms of running (`GRACE`, at least 8 cm); a release within it takes off at the line (`release()`), so it is legal and measured from the line. Only running on past that, holding or not, is a foul, "Yliastuttu", with the shoe's print in the plasticine. In a room 45 s with no tap (`TURN_MAX`, counted in `th.idle`) is a foul, "Aika loppui".
- **Pidä Hyppää merkistä: kulma nousee**: `startAim()`: holding the middle pad (upright), the top pad of either side column or anywhere on the scene (sideways) raises the take-off angle from 5° at 45° a second (`AIM_RATE`); the dial beside the jumper shows it, green from 16° to 24° (`GREEN`), the angles within about 20 cm of the best. The jumper crouches and keeps most of the speed.
- **Kosketus alle 0,1 s?**: `release()`: a touch shorter than `TAP_MIN` is a slip of the thumb and goes back to running.
- **Päästä irti laudalla: ponnistus**: `jumpNow()` and `takeoff()`: the take-off is from where the foot is (`relX`); the speed is the run-up plus 1.2 m/s, less the steeper the take-off (`STEEP`), so the best angle is about 20°: 8.3 m/s jumps about 6.4 m, 9.5 m/s about 7.6 m. The camera turns to the board and the whole pit.
- **Jalat eteen ajoissa?**: `legs()` and `reachOf()`: a tap in the air (any pad or the scene) throws the legs forward, once; it counts by how long was left before the sand (`q`). 0.12–0.34 s (`LEGS`) is a good landing, the heels about 0.55–0.6 m ahead of the body.
- **Jalat putoavat: lyhyempi**: earlier than that, or no tap at all, the feet come down under the body ("Liian aikaisin: jalat putosivat", "Jalat jäivät alas"), some 40–55 cm shorter.
- **Kädet hiekkaan: paljon lyhyempi**: later, the jumper falls back and the hands make the nearest mark ("Liian myöhään: kädet hiekkaan"), up to a metre shorter.
- **Tulos viivasta lähimpään jälkeen, valkoinen lippu**: `jumpMark()` and `landed()`: the mark is measured from the take-off line to the nearest break in the sand, down to the centimetre (rounded down), plus 5 cm per m/s of wind; landing short of the pit is a foul. The official by the board raises a white flag (red for a foul), a tape runs from the line to the mark, and a new record is saved at once (`ennatys`). The jumper's phone reports it (`res`); the host records it once (`seq`) and sends the meet to everyone (`c`).
- **Kaverin hyppy näkyy, sama lento**: the jumper's phone sends where its jumper is twelve times a second (`p`), the take-off (`rel`) and when the legs went forward (`leg`); the host passes them on, and every phone flies the same jump with `jumpNow()`, waiting at the sand for `leg`, and lands on the same mark.
- **8 parasta jatkaa, viimeisestä alkaen**: after round 3 `advance()` keeps the best eight (`final`), each later round in reverse order of the standings. With no player on a phone left in the final the rest is jumped at once.
- **Lopputulokset ja mitalit**: `over()` and `netEnd()`: the standings with 🥇🥈🥉, shown for a few seconds.
- **Ennätys, tuloslista, voitosta seuraava taso**: `netEnd()` saves `kisat`, and alone a win adds `voitot` and the next level (`taso`); the meet's best jump goes to the high-score list with `AiPelitScores.submit()` (`pituushyppy` in `public/scores.js` and `server/api.js`, see `tuloslistat.md`).
- **Huoneessa: sijat kaikille, takaisin huoneeseen**: the host sends the results with `R.deliver()`; each phone saves its own meet once (`R.once()`), shows its place and the top eight in the room (`afterEnd()`, `R.note()`, `R.backToRoom()`).
