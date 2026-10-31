# Last Signal: sukellusvene, sonar ja sukellukset

How a day in Last Signal plays (v1 #125, v2 #129, v3 #132). The player drives the submarine SISU through a side view
of an arctic sea (glacier bay, wreck field, iceberg caves), listens with the sonar, stops, swims out with limited
air, and brings finds home. Inside SISU (v3) they walk as a person between rooms on two decks: they eat in the
galley, heal, repair and upgrade, sleep in the bunk, and put on the diving suit to leave by the airlock. The amplifier and the antenna
fix the radio and end chapter 1. Chapter 2 (v2) goes down the continental slope to the empty research vessel
Nordlys and on to the deep sea, where the cold and glowing fish cost air or hull. Nothing ends the game:
hunger, air and the hull each send the player back.

```mermaid
flowchart TD
  A[Valikko: Jatka tai Uusi peli] --> B[Aja SISUa: ohjain, syvyys / runkoraja]
  B --> C[📡 Ping: kaiku piirtää pohjan, kohteet nimetään]
  C --> B
  B --> D{Syvemmällä kuin runko kestää?}
  D -- Kyllä --> E[Paine: runko kärsii]
  E --> F{Runko loppu?}
  F -- Kyllä --> G[Hätänousu turvasyvyyteen, runko 25 %]
  F -- Ei --> B
  G --> B
  SU --> I[Sukeltaja ui, happi vähenee, kohde avautuu poikkileikkaukseksi]
  I --> J{Mihin sukeltaja koskee?}
  J -- Ruoka, lääke, varaosa, radion osa --> K[Mukaan: lasketaan vasta kotona]
  J -- Loki --> L[Tarina etenee: seuraava tavoite]
  J -- Ilmatasku --> M[Happi täyttyy]
  K --> I
  L --> I
  M --> I
  I --> CO{Yli 600 metrin syvyydessä?}
  CO -- Kyllä --> CP[Kylmä vesi: happi kuluu nopeammin, paitsi lähteiden luona]
  CP --> I
  I --> FI[Valokala tönäisee: −8 s happea, SISUlle −5 % runkoa]
  FI --> I
  I --> N{Happi loppu?}
  N -- Kyllä --> O[Takaisin SISUun, löydöt jäävät paikoilleen, kunto -25]
  N -- Ei, ilmalukolla --> P[Palaa veneeseen: löydöt varastoon]
  O --> Q
  P --> Q
  B --> Q[🏠 Sisälle: ihminen SISUn kahdessa kerroksessa]
  Q --> QW[Napauta huonetta tai kävele ohjaimella, tikkaat kerrosten välillä]
  QW --> QR{Missä huoneessa seisot?}
  QR -- Keittiö, varasto --> R[Syö annos, ota lääke]
  QR -- Työpaja --> S[Korjaa runko, paineenkesto, happisäiliö, valonheitin]
  QR -- Punkka --> T[Nuku: uusi päivä, virta tuo pieniä löytöjä]
  QR -- Navigointi --> LB[Lokikirja: luetut viestit uudelleen]
  QR -- Sukelluspuvut --> PU[Puku päälle tai pois]
  QR -- Ilmalukko --> SU{Puku päällä?}
  SU -- Ei --> QW
  QR -- Ohjaamo --> U{Radio: vahvistin ja antenni?}
  QR -- Ohjaamo, ⛵ --> B
  R --> QW
  S --> QW
  T --> QW
  LB --> QW
  PU --> QW
  U -- Kyllä --> V[Viimeinen signaali: Nordlys vastaa, luku 1 päättyy]
  U -- Ei --> QW
  V --> Y[Luku 2: Mannerrinne, runko 620 / 1000 / 1450 m]
  Y --> Z[Saga ja pohjalaskeutuja rinteellä]
  Z --> NA[Tutkimusalus Nordlys 900 m: tyhjä, miehistö lähti Lyralla]
  NA --> NC[Happisäiliö ja Lyran valonheitin: varusteet paranevat]
  NA --> NB[Karttahuone: reitti lähteille]
  NB --> ND[Syvä meri: Lyran majakka ja muistikortti]
  ND --> NE[Radio: Lyran äänet, luku 2 päättyy]
  B --> W{Ruoka ja kunto loppu?}
  W -- Kyllä --> X[Pyörryt: uusi päivä, kunto 35]
  X --> Q
  class A,B,C,Q,QW blue
  class D,F,J,N,U,W,CO,QR,SU amber
  class I,K,M,P,R,S,T,NC,LB,PU teal
  class E,G,O,X,CP,FI rose
  class L,V,Y,Z,NA,NB,ND,NE green
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the path
- **teal**: diving, finds and life inside SISU
- **rose**: damage or a setback that never ends the game
- **green**: the story moving on

## Boxes

- **Aja SISUa: ohjain, syvyys / runkoraja**: `stepSub()` in `games/last-signal/v4/index.html` (v3, v2 and v1 in their own folders) turns the stick (`input`) into speed, bumps off the sea floor (`floorY()`), the glacier, the ice shelf, the iceberg (`inBerg()`), the hot vents (`VENTS`) and the wrecks (`solid(…, true)`); a hard bump costs hull (`bump()`). Below 300 m `subBoost()` speeds SISU up (up to 2.2×) so the long slope does not drag. The HUD shows depth against the hull's rating (`RATING`: 160, 260, 380, 620, 1000, 1450 m); within 25 m of it "Runko natisee". Saved every 4 s.
- **📡 Ping: kaiku piirtää pohjan, kohteet nimetään**: `doPing()` sends a ring out to 450 m; contacts inside it become known (`G.s.known`) and `drawSonar()` draws the floor, the iceberg and the wrecks in sonar green for a moment. Contacts up to 1000 m show at the screen's edge as "TUNTEMATON KONTAKTI, 640 m" until pinged; the current goal's contact is yellow (`goalNow().target`).
- **Paine: runko kärsii**: `pressure()`: below the rating the hull loses 4 % a second and "PAINE! Nouse ylemmäs" shows. Since v4 this goes on during a dive and inside SISU too ("PAINE! SISU on liian syvällä"); v3 and earlier spared the hull once the player left the helm.
- **Hätänousu turvasyvyyteen, runko 25 %**: `breach()` ends a dive or a walk inside (the haul is lost) and lifts SISU to 40 m above the hull's rating (v1 lifted it to the surface, a long way back from the deep sea); the hull is never fatal.
- **Sukeltaja ui, happi vähenee, kohde avautuu poikkileikkaukseksi**: `stepDive()`. Sites are grids in `SITES` (2 m cells: station A-3, two containers, the wrecks Polaris and Nordvik, the aid container in the trench); `drawSite()` fades the hull away to show the rooms when the diver is inside. The iceberg's caves are segments with a radius in `BERG.caves` (way in, upper caves, the great chamber, the side passage to cache K-7, the lower cave, the deep crack). In a big cave `diveScale()` widens the view, and `drawLayout()` shows the ice around the caves (layers, cracks, bubbles) so the great chamber reads as a hall in the ice.
- **Mukaan: lasketaan vasta kotona**: finds go into `G.carry`; `endDive(false)` moves them into `G.s.inv` and `G.s.got`.
- **Tarina etenee: seuraava tavoite**: a log (`LOGS`) opens a card and sets a flag; `goalNow()` reads the flags: container → station → hull upgrade → wrecks (Nordvik's map) → iceberg cache (antenna) → station amplifier → radio.
- **Takaisin SISUun, löydöt jäävät paikoilleen, kunto -25**: `endDive(true)`: the haul is lost but its finds wait where they were; the person comes to in the airlock.
- **Palaa veneeseen: löydöt varastoon**: `endDive(false)`; since v3 the person then stands in the airlock, still in the suit (`crew`), not at the helm.
- **🏠 Sisälle: ihminen SISUn kahdessa kerroksessa**: `openHome()` (the 🏠 corner button, or "🚶 Sisälle" when SISU is almost still) zooms in and puts the person (`crew`) at the helm. `drawInterior()` draws the rooms of `ROOMS` as in the SISU picture of #125: the reactor in the stern and the airlock in the bow full height; upstairs the galley, control room, navigation and bunk; downstairs electrical, workshop, stores (one tin per ration), diving suits. `drawCrew()` draws the person. Sideways the whole of SISU fits; upright the view follows the person. The first visit shows a card on how to walk (`flags.koti`). Time stands still inside: no hunger.
- **Napauta huonetta tai kävele ohjaimella, tikkaat kerrosten välillä**: a tap on the canvas goes to `walkTo()`, which picks the room and deck; `stepCrew()` walks there, by the ladder (`LADDER`) when it is on the other deck. The stick walks along a deck (`DECK_X`), right on the stick right on the screen whichever way SISU faces (the inside is drawn mirrored when it faces left), and climbs when pushed up or down at the ladder; halfway the person holds on.
- **Missä huoneessa seisot?**: `roomOf()` and `enterRoom()`; once the person stands still, `roomActs()` puts the room's one or two actions on the big buttons (`#act`, `#act2`) above its name. The reactor and electrical rooms only say something (`say`).
- **Korjaa runko, paineenkesto, happisäiliö, valonheitin**: the workshop's two buttons: one spare part mends 35 % hull; `upgradeCard()` buys upgrades with spare parts (`COST`).
- **Nuku: uusi päivä, virta tuo pieniä löytöjä**: `sleep()`; `newFinds()` drops up to three small finds on the floor within the hull's reach, so food never runs out for good.
- **Lokikirja: luetut viestit uudelleen**: `logBook()` lists every log read so far (`LOGS`, found in `G.s.got`) to read again, under the current goal.
- **Puku päälle tai pois**: the suit room's button toggles `crew.suit`; one suit leaves its hook while worn.
- **Puku päällä?**: the airlock's button: "🌊 Sukella ulos" runs `startDive()`, which puts the diver at the bow airlock with a full tank (`TANK`: 60, 90, 120 s); without the suit it says "Pue ensin puku" and cannot be pressed.
- **Radio: vahvistin ja antenni?**: the control room's second button opens `radio()`; its first, "⛵ Ruoriin", and the ⛵ corner button anywhere inside, go back to driving (`closeHome()`).
- **Viimeinen signaali: Nordlys vastaa, luku 1 päättyy**: `radio()` with both parts sets `flags.end`; play goes on.
- **Pyörryt: uusi päivä, kunto 35**: `faint()`, when hunger has emptied health; since v3 the person wakes in the bunk.
- **Kylmä vesi: happi kuluu nopeammin, paitsi lähteiden luona**: `chill()`: below `COLD` (600 m) air drains 1.35× (`CHILL`), not within 16 m of a vent's top (`nearVent()`); the HUD's air shows ❄️.
- **Valokala tönäisee: −8 s happea, SISUlle −5 % runkoa**: `FISH` swim fixed loops (`fishAt()`) on the slope's foot and the deep plain; in `stepDive()` one within 2.8 m takes 8 s of air (never below 1 s) and pushes the diver away; in `stepSub()` one beside SISU takes 5 % hull. Once per 3 s (`G.fishCd`).
- **Luku 2: Mannerrinne, runko 620 / 1000 / 1450 m**: `chapter2()` shows the chapter's card once (`flags.ch2`), after the last signal or on opening a v1 save whose chapter 1 ended. `goalNow()` then walks: hull 380 → Saga → hull 620 → lander → hull 1000 → Nordlys's chart room → hull 1450 → the beacon → the radio.
- **Saga ja pohjalaskeutuja rinteellä**: the sites `saga` (cable ship, 260–380 m) and `laskeutuja` (Nordlys's lander, 380–620 m), with `rinne` (containers) beside it; their logs point down the slope.
- **Tutkimusalus Nordlys 900 m: tyhjä, miehistö lähti Lyralla**: the site `nordlys`, a 62 × 13 grid drawn by `drawNordlys()`; inside, `drawLayout()` names its rooms (`rooms`: bridge, chart room, labs, workshop, mess, diving gear, bow store, the research sub's hangar, hold, engine room). Logs by digit (`logs`): bridge, lab, chart room, hangar.
- **Happisäiliö ja Lyran valonheitin: varusteet paranevat**: the finds `T` and `V`; `endDive()` raises the tank to 150 s and the lamp to its third level, or pays 2 spare parts when that level was already bought.
- **Syvä meri: Lyran majakka ja muistikortti**: the site `majakka` on the deep plain (~1340 m) among the vents and a whale's bones (`drawDeep()`); its log ties back to the tapping in the iceberg's crack; its memory card (`K`, `inv.kortti`) goes home.
- **Radio: Lyran äänet, luku 2 päättyy**: `radio()` with the card sets `flags.end2`; play goes on.
