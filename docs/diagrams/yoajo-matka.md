# Yöajo: poliisi, tankkaus, Lappi ja loputon yö

The plan for Yöajo's next versions (#440): what the police do, how fuel works, the new things on
the road, the exits and junctions where the route turns, the three new Lapland legs to Utsjoki, the endless night and the whole-trip summary.
One leg's own rules (lights, overtaking, moose, cameras, coffee) are in `yoajo.md`; this diagram
shows only what is added around them. v12 (police and the police check) and v13 (road events) are built; v14–v16 are the approved plan, and their boxes are rewritten to the code as each is built. Paths name the version that adds each.

```mermaid
flowchart TD
  A[Valikko: osuudet 1–11, Loputon yö, Koko matka] --> B[Aja osuus]
  A --> LY[Loputon yö: etappi toisensa perään]
  LY --> B
  B --> C{Mitä tiellä?}
  C -- Poliisiauto näkee --> P{Mitä poliisi näkee?}
  P -- Enintään 10 yli --> P0[Poliisi ajaa ohi]
  P -- 10–19 yli tai häikäisy --> PS[Pysäytys ja sakko -150, matka jatkuu]
  P -- 20+ yli, vaarallinen ohitus, sulkuviiva --> PX[Siniset vilkut: Poliisi pysäytti, osuus päättyy]
  C -- Puhalluskoe --> PK{Pysähdyitkö poliisin kohdalle?}
  PK -- Kyllä --> PK1[0,00 promillea, hyvää matkaa +20]
  PK -- Ei --> PX
  C -- Tietyö ja liikennevalo --> TV{Odotitko vihreää?}
  TV -- Kyllä --> TV1[Yksi kaista, vastaantulijat ensin +20]
  TV -- Ei, punaisia päin --> TV2[Punaisia päin -50, hurjastelu]
  C -- Sumu notkossa --> SU[Pitkät heijastuvat: lähivaloilla näkee paremmin]
  C -- Rikki auto, varoituskolmio --> RA{Hiljensit ja kiersit väljästi?}
  RA -- Kyllä --> RA1[Väljä ohitus +20]
  RA -- Ei --> RA2[Liian läheltä -40]
  C -- Ambulanssi takana --> AM{Väistitkö oikealle?}
  AM -- Kyllä --> AM1[Päästit ohi +30]
  AM -- Ei 5 s --> AM2[Tukit ambulanssin -50]
  C -- Erikoiskuljetus vastaan --> EK[Saattoauto vilkuttaa: pientareelle ja hiljaa]
  EK -- Alle 50 --> EK1[Väistit erikoiskuljetusta +20]
  EK -- Yli 50 --> X
  TV -- Kartioiden sisään --> X
  C -- Aura-auto --> AU[Lumipilvi takana: ohita vasta kun näet eteen]
  C -- Musta jää --> MJ[Kiiltävä kohta: pito puolet, ei jarrua eikä äkkiohjausta]
  C -- Risteys tai liittymä, jossa käännytään --> KR{Käännyitkö opastetusta?}
  KR -- Kyllä, hiljaa --> KR1[Vilkku syttyy itsestään, matka jatkuu]
  KR -- Liian kovaa --> X
  KR -- Ajoit ohi --> KR2[Väärä tie: osuus päättyy]
  KR2 --> X
  C -- Tasoristeys --> TR{Puomit alhaalla?}
  TR -- Odotit --> TR1[Juna menee ohi +20]
  TR -- Ajoit päin --> X[Kolari: osuus päättyy]
  B -- Lapin osuudet ja loputon yö --> F{Polttoainetta?}
  F -- Vähissä --> FA[Huoltoasema: pysähdy mittarille, tankki täyttyy]
  F -- Loppui --> FX[Polttoaine loppui, auto rullaa pysähdyksiin]
  FX --> X
  PX --> X
  B --> Z[Perillä]
  Z --> S[Tähdet ja ennätys, seuraava osuus aukeaa]
  S --> KM[Koko matka: tähdet, pisteet, km, sakot, hirvet]
  LY -- Kolari, nukahdus, poliisi tai tankki tyhjä --> LT[Loppui: km ja pisteet listalle loputon]
  X --> A
  class A,B,LY,P0,SU,EK,AU,MJ,FA,KR1 blue
  class C,P,PK,TV,RA,AM,TR,F,KR amber
  class PK1,TV1,RA1,AM1,TR1,EK1 teal
  class PX,PS,TV2,RA2,AM2,FX,X,KR2 rose
  class Z,S,KM,LT green
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the path
- **teal**: points for driving well
- **rose**: a penalty, or the end of the leg
- **green**: arriving, records and the trip's totals

## Boxes

- **Valikko: osuudet 1–11, Loputon yö, Koko matka**: `menu()` in `ui.js` lists eleven legs (`LEGS` in `game.js`, three new after Rovaniemi in v15), a "🌌 Loputon yö" button (open once leg 1 is driven, `ajettu >= 1`) and a "🏁 Koko matka" button for the summary.
- **Poliisiauto näkee**: v12 `policeLeg()` and `policeSees()` in `games/yoajo/v12/poliisi.js`. Marked police cars (white, blue and yellow checks, a light bar, `policeMesh()` in `view.js`) from leg 2: 0, 1, 1, 2, 2, 2, 3, 3 on legs 1–8 (`POLICE_CARS`), in turn parked at a side road's mouth with a radar, oncoming, or driving ahead. A moving one sees the player within 250 m in front of it or 120 m behind (`SEE_AHEAD`, `SEE_BEHIND`), a parked one 200 m up the road and 60 m past (`RADAR`, `RADAR_PAST`), in a blizzard only as far as the beam reaches; `clearView()` hides the player over a crest or round a sharp bend. "🚓 Poliisi näkee" shows under the speedometer while one does.
- **Mitä poliisi näkee?**: v12 `police()` (Eero's choice after the challenge): 10 km/h over or less, nothing; more than 10 and under 20 over for a second, `fine()`; 20 or more over for half a second, `caught()`. `policeSaw()` from `unsafeOvertake()` (an unsafe overtake, or crossing a junction's solid line) and `policeDazzled()` from `lights()` (the dazzle `fine()`s when that police car sees the player, `policeSees()`; assumed). Out of their sight these keep their old minus points; cameras keep their fine.
- **Pysäytys ja sakko -150, matka jatkuu**: v12 `fine()` and `policeHold()`: a police car with blue lights (`partio`) comes up behind, the screen's left and right edges flash blue in turn (`dashboard()` in `ui.js`), "Siniset vilkut: pysähdy tien sivuun" and a short quiet siren (`sirenSound()` in `ui.js`); the car brakes itself to a stop on the shoulder, waits 3 s, then "Poliisi: ylinopeus 14 km/h, sakko -150" (or "häikäisit poliisiautoa") and the drive goes on. Counted in `tally.sakot` and `tally.poliisi`.
- **Siniset vilkut: Poliisi pysäytti, osuus päättyy**: v12 `caught()`: the police car's lights flash, a patrol pulls in behind, the siren plays and the leg ends on the crash screen (title "Poliisi pysäytti!") with the reason ("Poliisi pysäytti: 124 km/h, rajoitus 100.", "Poliisi pysäytti: vaarallinen ohitus.", "Poliisi pysäytti: ohitit sulkuviivan yli.") and a hint. In the endless night (v16) the run ends.
- **Pysähdyitkö poliisin kohdalle?**: v12: under 5 km/h for 1.5 s (`BLOW_STILL`) from 10 m before the officer to 3 m past, in the right half of the road (their side), then "Puhalla…" for 2 s with the brake held, then "0,00 ‰ – hyvää matkaa! +20" (`tally.puhallus`). More than 6 m past them without having blown ends the leg: "Poliisi pysäytti: ajoit puhalluskokeen ohi." Driving into the officer is a crash.
- **Puhalluskoe**: v12 `placeCheck()` and `policeCheck()`: from leg 3 (`CHECK_FROM`), one check a leg, 200 m into a pothole stretch (`CHECK_IN`), so under its 50 limit, clear of cameras, junctions, other signs and moose; a POLIISI sign 50 m into the stretch, cones along the edge (`checkCones()` in `view.js`), the police car with its lights on a widened shoulder (`road.pads`) and an officer with a vest and a red baton (`officerMesh()`). From 300 m: "Puhalluskoe N m: pysähdy poliisin kohdalle".
- **Tietyö ja liikennevalo**: v13 `roadLeg()` and `roadTick()` in `games/yoajo/v13/tie.js` (leg 2, `ROAD_EVENTS`; leg 1 keeps none of the new events): an 80 m stretch (`WORK_LEN`) with the right lane shut by cones, a temporary light at the stop line and a second line 40 m past the far end (`FAR_STOP`) where oncoming cars wait. A 26 s cycle (`WORK_CYCLE`): the player's green 6 s, then the oncoming cars' turn for 2.5 s once the stretch is empty (`worksOpen()`). Limit 50 from 120 m before, a TIETYÖ sign at 200 m, "Tietyö: yksi kaista, odota vihreää". Cars on both sides queue behind each other at their line (`roadMove()`). Clear of junctions, rest areas and police checks.
- **Odotitko vihreää?**: v13 `roadTick()`: past the stop line on red, −50 "Punaisia päin" (`tally.punaiset`, counted as reckless); stopped before the line on red and through on green, +20 "Odotit vihreää" (`tally.tietyo`). Into the cones of the shut lane: "Ajoit tietyömaalle.", the leg ends.
- **Sumu notkossa**: v13 `fogAt()` and `fogReach()` (legs 2–4): up to two of the leg's deepest dips, at least 600 m apart, 140 m of fog (`FOG_HALF`) thinning over its last 25 m. In it high beams reach only 30 m and low beams 45 m (`FOG_HIGH`, `FOG_LOW`), high beams whiten the screen (0.4) and earn no long-beam points, and the 3D fog closes in. "Sumua: lähivaloilla näkee paremmin".
- **Rikki auto, varoituskolmio**: v13 (legs 2, 3, 6): a car with its hazard lights blinking half on the shoulder (`BROKEN_LAT`), a red triangle 50 m before it (`triangleMesh()` in `view.js`) and a walker with a reflector beside it. Traffic in the player's lane rounds it only with the other lane free, otherwise waits behind it.
- **Hiljensit ja kiersit väljästi?**: v13: judged as the player goes by: under 0.8 m from it faster than 40 km/h, −40 "Liian läheltä rikkinäistä autoa" (`tally.lahelta`); a metre or more, +20 "Väljä ohitus".
- **Ambulanssi takana**: v13 `ambulance()` (legs 3, 4, 5, 8): it comes up from behind with blue lights and a siren (a blue strip flashes at the top of the screen, "Ambulanssi takana: väistä oikealle"), waits 18 m behind until the player moves right of 2.6 (`YIELD_LAT`), then passes. Other cars move right for it too, oncoming ones to their own edge.
- **Väistitkö oikealle?**: v13: moved right before 5 s behind (`BLOCK_TIME`): +30 "Päästit ambulanssin ohi" (`tally.ambulanssi`) when it has passed. After 5 s: −50 "Tukit ambulanssin" (`tally.tukit`, which also takes the third star), and it passes in the oncoming lane once that is clear.
- **Väistit erikoiskuljetusta +20**: v13 `roadTick()`: 50 km/h or less as the load goes by, +20 (`tally.erikois`).
- **Erikoiskuljetus vastaan**: v13 (legs 4, 7): two escort cars with orange beacons and between them a 16 m house 4.6 m wide (`loadMesh()`), half over the centre line, at 40 km/h; cars behind it follow at its speed. From 400 m "Erikoiskuljetus vastaan: oikeaan reunaan ja alle 50". Over 50 km/h as it goes by: "Vaaratilanne: ohitit erikoiskuljetuksen liian kovaa." and the leg ends; otherwise +20 (`tally.erikois`).
- **Aura-auto**: v13 (legs 5–8): a snowplough at 40 km/h with orange beacons ahead in the player's lane; within 50 m behind it (`CLOUD_BACK`) its snow cloud whitens the screen, thickest close up. Overtaking it is worth 60.
- **Musta jää**: v13 `iceAt()` and `gripAt()` (legs 5–8): up to two 50 m shiny patches, each after a "Liukas ajorata" sign 150 m before it; grip halves on them. "Musta jää: ei jarrua eikä äkkiohjausta".
- **Käännyitkö opastetusta?**: v14 `risteys.js`: 1–3 turns a leg along the real route, an exit ramp off the motorway (legs 1–2) or a crossroads where Valtatie 4 turns (from leg 3). Blue direction signs at 600 m and 150 m and an arrow on the screen show the way; the straight-on road is a real side road.
- **Vilkku syttyy itsestään, matka jatkuu**: v14 `autoBlink()` (Eero's choice: no signal buttons): the blinker lights from the steering as the car turns. A left turn in front of an oncoming car within 4 s is −50 and reckless.
- **Väärä tie: osuus päättyy**: v14 `wrongWay()` (Eero's choice): 250 m down the wrong road ends the leg on the crash screen, "Väärä tie: ajoit ohi käännöksen."; in the endless night it ends the run.
- **Tasoristeys**: v14 (leg 4 and Lapland): a level crossing with lights and barriers; a train passes in 6 s.
- **Polttoainetta?**: v15 `fuel()` in `tie.js` (Eero's choice: only on the Lapland legs and in the endless night): a gauge beside the speedometer; a Lapland leg starts with enough to reach its station at the limits; use grows with the speed squared. In the endless night fuel carries over between stages.
- **Huoltoasema: pysähdy mittarille, tankki täyttyy**: v15: a service station with pumps and coffee on each Lapland leg, and every other stage in the endless night; stopping at a pump fills 10 % a second. The rest areas on legs 1–8 stay as they are.
- **Koko matka: tähdet, pisteet, km, sakot, hirvet**: v15 `tripScreen()` in `ui.js`: the best points and stars per leg summed, plus lifetime counters saved as `ai-pelit:yoajo:tilasto` (km driven, legs driven, police stops, fines, moose and reindeer avoided). Shown from the menu, and after Rovaniemi and Utsjoki.
- **Loputon yö: etappi toisensa perään**: v16 `endless()` in a new `loputon.js`: stages of about 3 km made from a running seed, each a little harder (more traffic, worse weather, more moose, police). Between stages the screen fades for a second and the car keeps its speed, fuel and alertness.
- **Loppui: km ja pisteet listalle loputon**: v16: the run's points (with +20 a km driven) go to the high-score list `loputon`; the best is saved as `loputon`.
