# Jään alla: luku 1, sukellusvene ja sukeltaja

How chapter 1 of Jään alla plays (v1, #106). The player drives the one-person submarine SISU
under the arctic ice from Aurora station to the RV Nordlys wreck, the iceberg cave and the
crystal cave, swims inside them as a diver, and brings the radio antenna, a glowing crystal and
scrap home to fix the radio mast. Air, power, food and hull are the four needs; running out of
air or hull sends the player back to safety, never ends the story.

```mermaid
flowchart TD
  A[Valikko: Jatka tai Uusi peli] --> B[Tarina: SISU lähetetään Aurora-asemalle]
  B --> C[Ohjaa SISUa: ohjain, nouse, sukella]
  C --> D{Missä SISU on?}
  D -- Aseman alla --> E[Telakoidu: reaktori latautuu, peli tallentuu]
  E --> F[Asema: päiväkirja, kalat, varasto, työpaja, radiomasto]
  F --> C
  D -- Hylyn tai luolan ovella --> G[Sukella ulos ilmalukosta]
  D -- Kalaparvi tai merilevä --> H[+1 ruoka]
  D -- Kalmarin lähellä --> I[Jättikalmari tarraa: runko -20]
  D -- Pohja tai jää kovaa --> J[Kolahdus: runko kärsii]
  H --> C
  I --> K{Runko loppu?}
  J --> K
  K -- Ei --> C
  K -- Kyllä --> L[Hätäjärjestelmä vie asemalle, runko 40 %]
  L --> C
  G --> M[Sukeltaja ui sisällä, ilma vähenee]
  M --> N{Mihin sukeltaja koskee?}
  N -- Romu tai ruoka --> O[Reppuun]
  N -- Loki --> P[Tarina etenee: seuraava tavoite]
  N -- Antenni tai kristalli --> P
  N -- Ilmatasku --> Q[Ilma täyttyy]
  N -- Ilmalukko --> R[Palaa SISUun]
  O --> M
  P --> M
  Q --> M
  M --> S{Ilma loppu?}
  S -- Kyllä --> R
  R --> C
  F --> T{Antenni, kristalli ja 2 romua?}
  T -- Kyllä --> U[Radio toimii: Aino vastaa, luku 1 päättyy]
  class A,B,C blue
  class D,K,N,S,T amber
  class E,F,G,M,R teal
  class H,O,Q green
  class P,U violet
  class I,J,L rose
```

## Colours

- **blue**: what the player sees and does first
- **amber**: a check that decides the path
- **teal**: places and moving between SISU and the diver
- **green**: supplies and air gained
- **violet**: the story moving on
- **rose**: danger and the rescue that follows

## Boxes

- **Valikko: Jatka tai Uusi peli**: `games/jaan-alla/v1/index.html`, `showMenu()`. "Jatka" shows only when `ai-pelit:jaan-alla:peli` holds a save; "Uusi peli" over a save asks for a second tap first.
- **Tarina: SISU lähetetään Aurora-asemalle**: `newGame()` starts a fresh save (`fresh()`) and shows the intro panel.
- **Ohjaa SISUa: ohjain, nouse, sukella**: `stepSub()`: the stick turns and drives (12 m/s at most), the ▲ ▼ buttons rise and sink; `collideSub()` keeps SISU under the ice, above `floorY()` and out of the spheres and columns in `SPHERES` and `COLUMNS`. Driving uses power; the reactor gives a little back. With no power SISU crawls at 35 %, hungry at 70 %.
- **Missä SISU on?**: `currentAction()` shows the yellow action button when SISU is under the station's moon pool or within 15 m of a place's door (the blinking yellow light). `goal()` picks the current goal, shown at the top with an arrow and distance, and as a light column in the sea.
- **Telakoidu: reaktori latautuu, peli tallentuu**: `dock()` fills power and saves.
- **Asema: päiväkirja, kalat, varasto, työpaja, radiomasto**: `stationPanel()`: the log (`STATION_LOG`) sets the first goal; the fish farm gives 2 food every 2 minutes of play; the store gives 2 food and 1 scrap the first time and 1 scrap every 2 minutes of play after that, so scrap spent on repairs can never leave the radio unfixable; the workshop mends the hull fully for 1 scrap. Once the radio works, its button only replays Aino's message.
- **Sukella ulos ilmalukosta**: `enterSite()` first saves SISU's place outside, then builds the inside from the site's grid (`SITES[...].map`, `buildRoom()`) and puts the diver just inside the airlock with full air.
- **+1 ruoka**: a fish school (`SCHOOLS`, once a minute each) or the kelp forest (`KELP`, every 45 s) adds a food can to the bag; the 🎒 button eats one for +35 % food.
- **Jättikalmari tarraa: runko -20**: `stepSquid()`: the squid circles the crystal cave, chases SISU within 28 m, and after a grab swims home for 6 s. SISU outruns it.
- **Kolahdus: runko kärsii**: hitting anything faster than 5 m/s costs hull.
- **Hätäjärjestelmä vie asemalle, runko 40 %**: `hullOut()`; inventory and story are kept.
- **Sukeltaja ui sisällä, ilma vähenee**: `stepDive()`: grid collision with walls, air falls 1.3 % a second (2 % hungry); the camera stays out of walls (`drawDiver()`).
- **Mihin sukeltaja koskee?**: things are taken on touch (`take()`); taken ones are kept in the save (`taken`) and stay gone.
- **Tarina etenee: seuraava tavoite**: the Nordlys log, the cave message, the antenna and the crystal each set a flag that `goal()` reads.
- **Ilmatasku**: an `A` cell refills air at 40 % a second.
- **Ilma loppu?**: `airOut()` puts the player back in SISU at the door, keeping what was found.
- **Antenni, kristalli ja 2 romua?**: `mast()` says what is missing, or fixes the radio.
- **Radio toimii: Aino vastaa, luku 1 päättyy**: sets `flags.radio`, writes `ai-pelit:jaan-alla:luku1` (play time), and the player may keep exploring.
