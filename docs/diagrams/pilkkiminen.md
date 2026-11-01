# Pilkkiminen: one contest, from the first hole to the result

How a contest of Pilkkiminen (ice fishing) plays. The view is from the side: the angler on the
ice, the hole, and the water down to the bottom. Five minutes on the clock; each fish is drilled
for, jigged in rhythm, struck and reeled in, and the biggest total catch wins. Alone three computer
anglers fish the same lake; with friends, 2–8 phones fish it each on its own phone through the
shared room library (see `moninpeli.md`).

```mermaid
flowchart TD
  S{Miten pelataan?}
  S -- Aloita pilkkikisa --> S1[Sinä ja kolme tietokoneen pilkkijää samalla järvellä]
  S -- Kavereiden kanssa --> S2[Huone: 2–8 puhelinta, sama järvi, kukin omassa paikassaan]
  S2 --> S3[Kukin pilkkii omalla puhelimellaan ja lähettää saaliinsa; huoneen tekijä pitää kelloa, tulostaulua ja järven kaloja]
  S1 --> A
  S3 --> A
  A{Onko paikassa jo reikä?} -- Ei --> B[Pyöritä sormella ympyrää: kaira menee jään läpi]
  A -- On --> C
  B --> C[Vedä alas tai ylös: pilkki kalojen syvyydelle]
  Z[Järven kalat: jokainen ui omaa reittiään paikasta toiseen] -.-> D
  C --> D{Onko kala lähellä pilkkiä?}
  D -- Ei --> M[🚶 Uusi paikka: valitse kohta järven kartalta]
  M --> A
  D -- On --> E[Pallo heiluu kalan tahdissa: napauta, kun se osuu reunaan]
  E --> F{Miten napautit?}
  F -- Tahdissa --> G[Kalan kiinnostus kasvaa]
  F -- Ohi tahdin --> H[Kiinnostus laskee]
  F -- Liian nopeasti --> I[Kala säikähtää ja ui pois]
  G --> J{Kiinnostus täynnä?}
  H --> E
  I --> D
  J -- Ei --> E
  J -- Kyllä --> K[Tärppi! Napauta heti]
  K -- Ehdit --> L[Kelaa: pidä sormi ruudulla, päästä irti kun siima kiristyy]
  K -- Myöhästyit --> I
  L --> N{Siima liian kireällä hetken?}
  N -- Kyllä --> O[Siima katkesi, uusi pilkki solmitaan]
  O --> C
  N -- Ei, kala reiällä --> P[Saalis punnitaan ja tallennetaan heti]
  P --> C
  P -.-> Z
  C -.-> T{Viisi minuuttia kulunut?}
  T -- Yksin --> U[Sijoitus tietokoneen pilkkijöitä vastaan; voitto nostaa tasoa]
  T -- Kavereiden kanssa --> V[Huoneen tekijä odottaa viimeiset saaliit, tulos kaikille kerran]
  class S2,S3,V violet
  class S,A,D,F,J,N,T amber
  class B,C,E,K,L,M blue
  class G,P,Z teal
  class U green
  class H,I,O rose
  class S1 blue
```

## Colours

- **blue**: what the player sees and does
- **amber**: a check that decides the path
- **teal**: the fish coming closer, and a fish landed
- **violet**: playing in a room
- **green**: the contest's result alone
- **rose**: a fish lost or scared away

## Boxes

- **Miten pelataan?**: the menu in `games/pilkki/v1/index.html`: **Aloita pilkkikisa** (`newContest()`), **Jatka kisaa** when a contest alone was left unfinished (kept every two seconds as `ai-pelit:pilkki:kisa` by `keepContest()`), or **👥 Pelaa kavereiden kanssa** (`AiPelitRooms.open()`).
- **Sinä ja kolme tietokoneen pilkkijää samalla järvellä**: `cpuAnglers()` now and then lands for each rival a fish that is at its place, and that fish is gone from the lake; how often, and how often the bigger of two, grows with the level (`rivalRate()`).
- **Huone: 2–8 puhelinta, sama järvi, kukin omassa paikassaan**: `setupFor()` on the host sends the lake's seed (`makeLake()`) and a starting place for each phone.
- **Kukin pilkkii omalla puhelimellaan ja lähettää saaliinsa; huoneen tekijä pitää kelloa, tulostaulua ja järven kaloja**: each phone sends `me` (its catch, `sendMe()`) every second and after each fish; the host sends `s` (the clock and everyone's catch, `snapshot()`) twice a second. A catch on the host's list only grows, so a phone that reloads gets its catch back. The lake's fish are shared: the host swims them and sends them to every phone once a second (`pondMsg()`, `applyPond()`), and a guest moves them on between those (`follow()`). A fish that starts looking at a phone's jig is that phone's (`claim()`, first come first served, `taken()` on the others), so jigging and reeling run on that phone alone; let go or scared it goes back to the host (`release()`), landed it is gone on every phone (`caught()`, `gone`). A guest's catch counts only if the host accepts the fish was that phone's: the host then adds it to that player's total itself, once (`hostFish()`), so it counts even if the phone drops before it hears so, and tells the phone (`credit()` on `gone`; `nocatch` otherwise), and a phone that hears another got the fish first loses it, even mid-bite or on the line (`lost()`). A phone that comes back or is let go holds no fish (`freeClaims()`); one that comes back still reeling or biting claims that fish again (`applyPond()`). While the room waits for a phone that is away (`AiPelitRooms.paused`), the clock stops and no phone takes fishing input.
- **Onko paikassa jo reikä?**: `goTo()`; holes drilled this contest are in `holes`.
- **Pyöritä sormella ympyrää: kaira menee jään läpi**: `turnAuger()`; six turns of the finger round the auger (`TURNS`).
- **Vedä alas tai ylös: pilkki kalojen syvyydelle**: a drag in the water moves the jig (`jigD`); after a catch or a broken line it sinks back to the last depth by itself (`jigGoal`).
- **🚶 Uusi paikka: valitse kohta järven kartalta**: `drawMap()` and `moveTo()`; twelve places, shallow by the shore and deep in the middle, where the fish gather. A walk takes a couple of seconds.
- **Järven kalat: jokainen ui omaa reittiään paikasta toiseen**: `pond`, about a hundred single fish (`newFish()`, `SPECIES`) on a lake of 150 × 110 m. Each swims to a place that suits its kind, stays there half a minute to two minutes, then swims on (`swim()`, `leave()`); a frightened or lost fish swims off at once (`scare()`). A fish caught is gone for the rest of the contest, and none are added, so a fished-out place fills again only when fish swim there. The side view shows the fish within 5 m of the hole (`sight()`). The contest save keeps every fish (`pondSave()`), so a reload finds the lake as it was. In a room the fish are the host's and shared by every phone (see the room box).
- **Pallo heiluu kalan tahdissa: napauta, kun se osuu reunaan**: `period()` is the tempo of the fish the jig is working on (`target`); a perch likes fast twitches, a zander or a burbot slow ones.
- **Miten napautit?**: `twitch()`: within `WIN` (0.17 s) of the beat is good, faster than half a beat is a frenzy.
- **Tärppi! Napauta heti**: `bite()`, then `strike()` within about a second.
- **Kelaa: pidä sormi ruudulla, päästä irti kun siima kiristyy**: `fightStep()`: holding reels in and tightens the line, letting go gives the fish line; a fish pulls harder in rushes and tires over time (`pullOf()`).
- **Siima katkesi, uusi pilkki solmitaan**: `snap()`, when the tension stays over the limit for 0.4 s.
- **Saalis punnitaan ja tallennetaan heti**: `land()` saves the lifetime catch per kind (`kalat`) and the biggest fish ever (`suurin`).
- **Sijoitus tietokoneen pilkkijöitä vastaan; voitto nostaa tasoa**: `endContest()` saves `taso`, `ennatys` and `kisat`, and sends the catch in grams to the high-score list.
- **Huoneen tekijä odottaa viimeiset saaliit, tulos kaikille kerran**: `timeUp()` and `closing()` → `AiPelitRooms.deliver()`; each phone saves its result once in `ai-pelit:pilkki:kaverit` (`finish()`). The place comes from the end message's own player list (`roomStandings()`), so a phone that reloads after the end still gets its real place.
