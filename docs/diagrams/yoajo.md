# Yöajo: one leg of the night drive

How one leg of Yöajo plays (v1, #181; v4 drives with one thumb as a round stick and adds the reckless-driving rules; v3 steers and presses the gas with one thumb a side; v2 is the same game, sized from the real screen so it fits at once after going full screen: `index.html` and `fitCheck()` in `games/yoajo/v2/ui.js`). The player drives at night up Valtatie 4 from Helsinki
to Rovaniemi, one leg a level, seen in 3D from behind the car. In v1 and v2 the car pulls up
to speed by itself and the player steers and brakes with buttons; in v3 the left thumb steers and
the right thumb presses the gas or brakes, by how far each slides. The player also switches the
high beams. On the road come oncoming cars,
slow tractors, trucks and cars to overtake, walkers, reckless drivers, bad stretches, speed
cameras, moose (and reindeer in Lapland), rain and snow, and the driver grows sleepy.

```mermaid
flowchart TD
  A[Valitse osuus, Aja] --> B[Aja: ohjaa, kaasuta, jarruta, valot]
  B --> C{Mitä tiellä?}
  C -- Vastaantulija --> D{Pitkät pois ajoissa?}
  D -- Kyllä --> D1[Lähivaloille ajoissa +20]
  D -- Ei --> D2[Häikäisit, vastaantulija vilkuttaa -30]
  C -- Traktori, rekka tai auto edellä --> E{Vastaan tulee joku?}
  E -- Ei --> E1[Ohitus +40..60]
  E -- Kyllä --> E2[Odota takana, lähivaloilla]
  E -- Ohitit silti, vastaantulija alle 180 m --> E3[Vaarallinen ohitus -50, ei ohituspisteitä]
  B --> P{Pitkät tyhjällä tiellä?}
  P -- Kyllä --> P1[+5 joka 100 m, ei katuvaloissa]
  P -- Ei, 6 s --> P2[Muistutus: pitkät päälle]
  B --> R{Yli rajoituksen 20 tai enemmän?}
  R -- Kyllä --> R1[Hurjastelu -25, joka 5 s uudelleen]
  C -- Jalankulkija --> F{Väljästi ohi?}
  F -- Kyllä --> F1[Väljä ohitus +20]
  F -- Ei --> F2[Liian läheltä -40]
  C -- Hirvi tai poro --> G{Jarrutit tai väistit?}
  G -- Ei --> X[Kolari: osuus päättyy]
  C -- Huono tie --> H{Hitaasti kuoppien yli?}
  H -- Ei --> H1[Kuoppa -15, neljäs kova isku puhkaisee renkaan]
  H1 --> X
  C -- Nopeuskamera --> K{Yli rajoituksen +5?}
  K -- Kyllä --> K1[Salama, sakko -150]
  K -- Ei --> K2[Rajoituksissa +25]
  C -- Hurjastelija --> L[Ohittaja omalla kaistalla: väistä pientareelle]
  B --> V{Väsyttää?}
  V -- Levähdysalue --> V1[Kahvitauko: vireys täyteen, +10 s]
  V -- Ei taukoa --> V2[Silmät painuvat kiinni]
  V2 --> X
  B --> Y{Ojaan tai kolari?}
  Y -- Kyllä --> X
  B --> Z[Perillä kaupungissa]
  Z --> S[Tähdet: perillä, tavoiteajassa, ilman sakkoja, hurjastelua ja häikäisyjä]
  S --> T[Seuraava osuus aukeaa, ennätys tuloslistalle]
  X --> A
  class A,B,E2,L,P2 blue
  class C,D,E,F,G,H,K,V,Y,P,R amber
  class D1,E1,F1,K2,V1,P1 teal
  class D2,F2,H1,K1,V2,X,E3,R1 rose
  class Z,S,T green
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the path
- **teal**: points for driving well
- **rose**: a penalty, or the end of the leg
- **green**: arriving, stars and records

## Boxes

- **Valitse osuus, Aja**: the menu (`menu()` in `games/yoajo/v1/ui.js`) lists the eight legs of `LEGS` in `game.js`, from Helsinki → Järvenpää to Oulu → Rovaniemi; a leg opens when the one before is driven (`maxLeg`, saved as `ai-pelit:yoajo:taso`). Each leg has its own weather (dry, rain, snow, blizzard) and its own mix of traffic. `newLeg()` builds the road (`makeRoad()`: bends and hills from the leg's seed), the speed limits and signs, and the list of what happens where (`events`).
- **Aja: ohjaa, kaasuta, jarruta, valot**: `drive()` in `game.js`. v1 and v2: the car pulls up to 130 km/h by itself unless JARRU is held, and ◀ ▶ buttons steer fully. v3 (#181 feedback, Eero's choice): one thumb a side, anywhere below the top line (`thumbs` and `setThumbs()` in `games/yoajo/v3/ui.js`). The left thumb slides sideways from where it landed: a short slide is a gentle turn, a long one sharper than v1's buttons (`input.steer`, the slide to the power 1.4). The right thumb is the gas: landing is a light press (35 %), sliding up gives more, up to full, and sliding down past where it landed brakes by how far (`input.gas`, `input.brake`). Off the gas the engine slows the car a little. A bend pushes the car outwards, more the faster and the slipperier (`WEATHER[...].grip`). VALOT (a button in the middle in v3) switches between low beams (42 m) and high beams (135 m), less in rain and snow; `view.js` draws them as one spot light, so what is beyond the beam stays dark. v4 (#181, Eero's choice after trying a prototype): one thumb as a round stick like Areena's, 56 px across its radius, wherever the thumb lands (`oneThumbGuide()`, `STICK` in `games/yoajo/v4/ui.js`): sideways steers, up is gas, down brakes, and diagonals do both. The lights move to the lower right corner. The menu's "Ohjaus" switch picks v3's two thumbs instead (saved as `ohjaus`). v4 also gives traffic a speed habit (`cruise()` in `game.js`): each car keeps to the limit where it is, some 12–22 km/h under (the ones to overtake), most about at it, a few 6–15 over; trucks keep to 80 or up to 4 km/h over. The reckless driver from behind slows behind the player instead of driving into them. Limits change less (one stretch every 1.3–2 km), and 60 (villages, with street lights) comes only from leg 5.
- **Pitkät pois ajoissa?**: `lights()` in `game.js`. An oncoming car is released 620 m ahead; if the high beams were on when it came into sight and are off before it is 150 m away, +20. Still on at 150 m: −30 and it flashes its own at the player. A car ahead within 70 m dazzled for 1.5 s costs −20. v4 (#181: the dazzle came too easily): judged at 90 m, and a car ahead after 2.5 s within 50 m.
- **Ohitus +40..60**: `meet()`: passing a slow vehicle in the player's direction scores once (tractor 40, car 50, truck 60). Same-direction cars keep behind slower ones and behind the player.
- **Väljä ohitus +20**: walkers keep to the left edge facing traffic, or now and then the right edge; a third have no reflector and show only in the beam. Passing with under a metre of room above 40 km/h costs −40; touching one ends the leg as a near miss ("Vaaratilanne").
- **Jarrutit tai väistit?**: a moose (or a reindeer on the last leg) steps out of the forest about four seconds of driving ahead, after a warning sign; some stop on the road. Its eyes shine in the beam (`deerMesh()` in `view.js`).
- **Kuoppa -15, neljäs kova isku puhkaisee renkaan**: `holes()`: a bad stretch after an "Epätasainen tie" sign has potholes; below 50 km/h they do nothing, above it they jolt the car; the fourth hit above 70 km/h bursts a tyre.
- **Yli rajoituksen +5?**: `cameras()`: a camera stands 340 m after its sign; over the limit by more than 5 km/h it flashes and fines −150, otherwise +25.
- **Ohittaja omalla kaistalla: väistä pientareelle**: two kinds of reckless drivers (`move()`): one from behind with high beams on, overtaking when nobody comes and cutting in; one oncoming, pulling out from behind a truck into the player's lane with its high beams on.
- **Kahvitauko: vireys täyteen, +10 s**: `tiredness()` (#181 "Kuskia väsyttää"), from leg 3. Sleepiness grows with the road driven; past 40 % the eyes close for a moment now and then (black lids in `dashboard()`), longer as it grows. Stopping in the rest area's bay (a sign, then a paved bay and a lit kiosk on the right) wakes the driver; without a stop they fall asleep after the rest area, before the town.
- **Tähdet: perillä, tavoiteajassa, ilman sakkoja, hurjastelua ja häikäisyjä**: (v4 adds the reckless-driving count to the third star) `finish()`: one star for arriving, two within the target time (`parTime()`: the leg at the speed limits, at most 90 on snow, plus 20 %), three also with no fines, no dazzling and no close passes. Time under the target gives 10 points a second.
- **Seuraava osuus aukeaa, ennätys tuloslistalle**: stars and best points per leg are saved (`tahdet`, `pisteet`), and the furthest leg driven to the end as `ajettu` (`taso`, the furthest leg open, stops at 8). The points of every leg driven to the end, even at zero or below after fines, go to the leg's high-score list `osa-N` (`public/scores.js`, `server/api.js`), with `ajettu` shown beside them. `buildWorld()` and `dispose()` in `view.js` free the old leg's 3D pictures and the passed traffic, so driving leg after leg does not fill the phone's memory.
- **Vaarallinen ohitus -50, ei ohituspisteitä**: v4 `unsafeOvertake()` in `game.js`, judged before any pass is scored in the same moment: being past the centre line while an oncoming car is within 180 m costs 50, once a car, and every vehicle passed before the car is back in its lane earns nothing (`P.unsafe`).
- **+5 joka 100 m, ei katuvaloissa**: v4 `highBeams()`: every 100 m on high beams earns 5 points, announced every 500 m and shown on the end screen as "Pitkillä ajettu". Not under street lights (`streetLit()`: the town at the end and the villages). After 6 s on low beams with an empty road ahead, a reminder.
- **Hurjastelu -25, joka 5 s uudelleen**: v4 `reckless()`: 20 km/h or more over the limit for over a second costs 25, and again every 5 s it goes on.
