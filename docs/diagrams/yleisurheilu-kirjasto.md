# Yleisurheilukirjasto: the meet shared by the field events

How a field event's version uses the shared athletics library (#165): the game does the attempt
itself (the run-up, the throw or the jump, the drawing), the library runs everything around it:
the field of twelve, whose turn it is, the standings and the results board, the saves, the end of
the meet, and playing it with friends through `rooms.js`. First users: Pituushyppy v2, Keihäänheitto v4, Moukarinheitto v2, Korkeushyppy v2, Seiväshyppy v2. The folder is
frozen once published, like three.js: a change goes in the next folder. `yleisurheilu-2/` (#176,
first user Pituushyppy v5) adds the medal ceremony at the end of the meet; the next change goes in
`yleisurheilu-3/`. The bar-height format is still only in `yleisurheilu-1/` (Korkeushyppy and
Seiväshyppy add it to `yleisurheilu-2/` when they move to the ceremony).

```mermaid
flowchart TD
  subgraph Peli[Lajin oma koodi: games/slug/vN/index.html]
    G1[Valikko: Kisaan!, Jatka kisaa, kaverit]
    G2[Oma suoritus: vauhdinotto, ponnistus tai heitto]
    G3[Toisen puhelimen suoritus näkyy]
    G4[Kenttä, HUD ja tulostaulun paikka]
  end
  subgraph Kirjasto[public/lib/yleisurheilu-2/kisa.js]
    K1[meet: 12 kilpailijaa, tietokone täyttää]
    K2[Muoto: rounds 3 + 3 kierrosta]
    K3{Kenen vuoro?}
    K4[Tietokone tekee suorituksensa heti]
    K5[Tulos kirjataan kerran, seq]
    K6[Tulostaulu vuorojen välissä]
    K9[Palkintojenjako: korokkeelle, mitalit kaulaan, lopputulokset]
    K7[Tallennus: taso, voitot, kisat, ennätys, kesken]
    K8[Huone: isäntä vetää kisaa, välittää suoritukset]
  end
  G1 --> K1 --> K2 --> K3
  K1 -. Korkeus, Seiväs: vielä v1 .-> H1[yleisurheilu-1/korkeus.js: heights, rima nousee]
  H1 --> K3
  K3 -- Tietokone tai poissa oleva --> K4 --> K3
  K3 -- Tämä puhelin --> G2
  K3 -- Kaveri --> G3
  G2 -- K.report --> K5
  G2 -- K.send p, rel... --> K8 --> G3
  K5 --> K3
  K5 --> K6
  K5 -- Kisa ohi --> K9
  K9 --> K7 --> G1
  K9 -- Huoneessa --> K8
  G4 -- K.drawBoard --> K6
  G4 -- K.drawPodium --> K9
  class G1,G2,G4 blue
  class G3,K8 violet
  class K3 amber
  class K1,K2,K4,K5,H1 teal
  class K6,K7,K9 green
```

## Colours

- **blue**: the event's own screens and controls
- **violet**: playing with friends
- **amber**: a check that decides the path
- **teal**: the meet's rules
- **green**: the results and what they save

## Boxes

- **meet: 12 kilpailijaa, tietokone täyttää**: `AiPelitKisa.meet(opts)` in `public/lib/yleisurheilu-2/kisa.js` (`yleisurheilu-1/kisa.js` for the versions made before #176, the same but without the ceremony), loaded with a classic `<script>` after `rooms.js`. The game gives its slug (save keys), the computer's names (`foes`), its skill by level (`skill`, `spread`, `jitter`), how a computer turn goes (`cpu`), and hooks for a new turn (`turn`), a cleared turn (`clear`), the menu (`menu`) and its live messages (`live`, `watch`). The meet is `K.comp`, plain numbers, the same shape as the v1 games' (so a meet left unfinished in v1 goes on in v2).
- **Muoto: rounds 3 + 3 kierrosta**: `AiPelitKisa.rounds()` in `yleisurheilu-2/kisa.js`: the throws and the long jump. Rounds 1–3 in a drawn order, then the best eight three more, the last first; the standings by the best mark, then the second best.
- **yleisurheilu-1/korkeus.js: heights, rima nousee**: the bar-height format for the high jump and the pole vault, `AiPelitKisa.heights()`, used with v1's `kisa.js` (Korkeushyppy v2, Seiväshyppy v2). `yleisurheilu-2/` has no `korkeus.js` yet: the Korkeus and Seiväs versions that move to the ceremony add it there in their own pull requests (#176). The bar rises through the game's `heights(level)`, three attempts per height in the drawn order, passes, three failures in a row out, the last one in who leads may stop, the countback, and its own board (the attempts at this height; at the end the failures that settle a tie). The computer's start height and passes come from the game's `plan(t, comp)`.
- **Kenen vuoro?**: `advance()` and `follow()` in the library: the computer's turns up to the next player on a phone, then `opts.turn(t, mine, seq)` once per turn, where the game sets up its own attempt (`th`).
- **Tietokone tekee suorituksensa heti**: `opts.cpu(t, comp)`; also for a phone that is away after the host's "Jatka ilman heitä" (`R.on('continue')`), until it is back (`R.on('back')`).
- **Tulos kirjataan kerran, seq**: `K.report(seq, mark)`: alone or on the host it is recorded at once (`take()`), a guest sends `res`; the host takes it only from the phone whose turn it is and only for the turn now (`seq`), saves an unfinished meet alone (`kesken`) and sends the meet to every phone (`c`).
- **Tulostaulu vuorojen välissä**: `K.drawBoard(ctx, false, box)` draws the standings between turns into the box the game gives (`true` still draws v1's plain final board).
- **Palkintojenjako: korokkeelle, mitalit kaulaan, lopputulokset**: `K.drawPodium(ctx, box)` and `podium()` in `yleisurheilu-2/kisa.js` (#176): the top three hop onto the podium (bronze, silver, gold), an official walks over the blocks and hangs each medal around the neck, they cheer under confetti, and the final standings show under the podium (beside it on a phone on its side). The game may give `opts.look(row)` (an outfit palette) and `opts.chime(i)` (a sound per medal). `K.step(dt)` keeps it up `PODIUM_END` (11) seconds on every phone, then the menu or the room (`R.backToRoom()`, the top eight with `R.note()`); alone, a tap finishes the ceremony (`PODIUM_DONE`) and the next leaves it.
- **Tallennus: taso, voitot, kisat, ennätys, kesken**: `ai-pelit:<slug>:…`, the keys the v1 games already use. A win alone adds a win and a level; the best mark goes to the high-score list (`AiPelitScores.submit()`); `K.record(mark)` saves a record the moment it is set.
- **Huone: isäntä vetää kisaa, välittää suoritukset**: the library's `R.on('start' | 'message' | 'hello' | 'continue' | 'back' | 'lobby' | 'leave' | 'menu')`. The game's live messages (`opts.live`, e.g. Pituushyppy's `p`, `rel`, `leg`) go through `K.send()`; the host adds whose turn it is and passes them to every phone's `opts.watch`. Message types `c`, `res`, `end` and `fit` (an outfit, when the game gives `opts.fit`) are the library's. A returning or reloaded phone gets the meet from the host (`hello`).
- **Oma suoritus: vauhdinotto, ponnistus tai heitto**: the game's own code, unchanged from its previous version.
