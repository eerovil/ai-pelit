# Sormiskeitti: one round, from push to ceiling

How one round of Sormiskeitti plays from v2 on. Taps push the board along the table, one tap on
the ramp is the ollie, and from v2 one tap in the air lets the fingers go, which flicks the board
higher. Each level's ceiling now grows toward a top that good play can still reach, so no level
is impossible as level 8 was in v1. From v3 the level and the record are saved on the phone, so
closing the game no longer loses them. From v4 a tap just after the lip still counts as a
perfect ollie, because the green zone lasts only about 100 ms at full speed. From v7 (#229) the
round sounds with recorded effects from the shared sound library (see `aanikirjasto.md`); each
box that makes a sound names it.

Since #346 only each game's newest version folder is kept: a `games/<slug>/v<N>/` path below that is not the newest names a version that is history now (its files are in git's history, and the site sends its address to the newest), and what it says about that version is how it was.

v8 (#337) loads `aanet-4`, which plays the loudest sounds (the winning tune) quieter; nothing else changed.

```mermaid
flowchart TD
  S[Avaa peli: taso ja ennätys puhelimesta] --> A
  A[Napauta: aloita] --> B[Napauta nopeasti: potkaise vauhtia, renkaat rullaavat]
  B --> C{Napautus rampin yläpäässä tai heti reunan jälkeen?}
  C -- Myöhään tai heti reunan jälkeen --> D[Täydellinen ollie x1.3: pop ja onnistui]
  C -- Aikaisin tai ei --> E[Heikompi ollie: pop]
  D --> F[Ilmalento]
  E --> F
  F --> G{Napautus ilmassa?}
  G -- Ylimmillään --> H[Täydellinen irrotus: suuri lisävauhti]
  G -- Aikaisin tai myöhään --> I[Pienempi lisävauhti]
  G -- Ei --> J[Ei lisävauhtia]
  H --> K{Osuiko kattoon?}
  I --> K
  J --> K
  K -- Kyllä --> KK[Kattoon: puu]
  KK --> L[Alastulo: lasku ja voitto. Taso läpi: seuraava katto vähän korkeammalla]
  L --> T[Tallenna seuraava taso ja ennätys]
  M --> T2[Tallenna ennätys]
  K -- Ei --> M[Alastulo: lasku ja tappio. Jäi X cm vajaaksi: sama taso uudestaan]
  class A,B blue
  class C,G,K amber
  class D,E,F teal
  class H,I,J violet
  class L green
  class KK green
  class S,T,T2 teal
  class M rose
```

## Colours

- **blue**: the player's taps on the table
- **amber**: a check that decides the path
- **teal**: the ollie and the flight, as in v1, and the saved progress (v3)
- **violet**: the new mid-air let-go (v2)
- **green**: level passed
- **rose**: level failed, try again

## Boxes

- **Napauta nopeasti: potkaise vauhtia, renkaat rullaavat**: v7 runs the `rullaus` loop from `aanet-2` (`wheels` in `games/sormiskeitti/v7/index.html`); `step()` sets its volume and rate from the speed while rolling, and silences it in the air and between rounds.
- **Täydellinen ollie x1.3: pop ja onnistui**: v7's `tap()` plays `pop`, and for a perfect ollie (on the ramp or late) `onnistui` just after it.
- **Kattoon: puu**: v7's `step()` plays `puu` when the board bonks the ceiling.
- **Alastulo: lasku ja voitto. Taso läpi: seuraava katto vähän korkeammalla**: v7's `finish()` plays `lasku` when the board comes back to the lip, then `voitto` on a win or `tappio` on a miss; rolling back down the ramp with no air plays only `tappio`. The level: `ceilH()`: each level closes 15 % of the gap to `CEIL_TOP` (60 cm), so level 8 is 46 cm instead of v1's 57 cm, which no tapping could reach.
- **Täydellinen irrotus: suuri lisävauhti**: `tap()` in `games/sormiskeitti/v2/index.html`: when the board's upward speed is within 1 of zero (the top of the flight) it gets `LETGO_BEST` (9) more speed; the "IRTI!" hint shows just before.
- **Pienempi lisävauhti**: further from the top the boost falls by 1.2 per unit of speed, down to `LETGO_MIN` (3). Only one let-go per flight.
- **Avaa peli: taso ja ennätys puhelimesta**: v3 reads `ai-pelit:sormiskeitti:level` and `ai-pelit:sormiskeitti:best` from `localStorage` (`load()`); with nothing saved it starts at level 1.
- **Tallenna seuraava taso ja ennätys**: `finish()` saves the record every round and, on a win, the next level, so a reload starts there.
- **Napautus rampin yläpäässä tai heti reunan jälkeen?**: `tap()`: on the ramp, past 1.3 rad (v3: 1.42) is perfect and past 1.1 good; from v4 a tap up to `OLLIE_GRACE` (8) frames after the lip is a perfect ollie too, and the flight so far is redone as if it had been at the lip. Only after that does a tap mean the let-go.
