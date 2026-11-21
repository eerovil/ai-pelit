# Asut: the shared outfit picker, Halloween, Christmas and Tylypahka costumes

How a game version lets the player pick an outfit for their figure (#158). One shared script,
`public/outfits.js`, draws the picker and keeps the choice on the phone; each game draws its own
figure in the chosen outfit. The six Halloween costumes are the same in every game, always
available, and come first in the picker around Halloween. From #311 the athletics events share
one choice (`data-share="yleisurheilu"`) and one set of everyday kits, so the outfit picked in
any of them is worn in every event (Mäkihyppy too from v12, #469; Ottelu, which shared it, was
removed in #469). The three Tylypahka
costumes (#321: Harry, Ron and Hermione) are in every game too, right after the everyday outfits.
The five Christmas costumes (#473) are in the picker of every game except Orava, and only in November and December, first
from 3 November; outside it a saved Christmas choice waits and the game's default is worn.

```mermaid
flowchart TD
  subgraph Peli
    A[Valikon nappi: 👕 Asu] --> B[AiPelitOutfits.open]
    S[setup: pelin omat asut + piirto] --> L[Asulista: omat + 6 Halloween-asua + 5 jouluasua + 3 Tylypahka-asua]
    Y[Yleisurheilun yhteiset 7 asua] --> L
  end
  subgraph outfits.js
    B --> J{Onko marras- tai joulukuu?}
    J -- Ei --> Q{Onko 20.10.–2.11.?}
    J -- Kyllä --> JQ{Onko 1.–2.11.?}
    JQ -- Kyllä --> HJ[Halloween, Joulu, Tavalliset, Tylypahka; 🎃-tervehdys]
    JQ -- Ei --> JT[Joulu, Tavalliset, Tylypahka, Halloween; 🎄-tervehdys]
    Q -- Kyllä --> H[Halloween, Tavalliset, Tylypahka; 🎃-tervehdys]
    Q -- Ei --> T[Tavalliset, Tylypahka, Halloween; ei jouluasuja]
    H --> F{data-share yleisurheilu?}
    T --> F
    HJ --> F
    JT --> F
    F -- Ei --> K[Kortit ja liikkuva esikatselu: pelin oma piirto]
    F -- Kyllä --> FK[Kortit ja liikkuva esikatselu: yhteinen hahmo edestä]
    FK --> P
    K --> P[Pelaaja napauttaa asua]
    P --> G{data-share?}
    G -- Ei --> V[Tallennus: ai-pelit:_asut:slug]
    G -- Kyllä --> W[Tallennus: ai-pelit:_asut:yleisurheilu + pelin oma]
  end
  subgraph Pelaaminen
    V --> C[change: peli piirtää hahmon uudessa asussa]
    W --> C
    C --> HP[Pää kääntyy vauhdissa, ilmassa ja tuulettaessa: headPose]
    C --> R{Kavereiden huone?}
    R -- Kyllä --> M[Asun id lähtee pelaajan tiedoissa, muut piirtävät sen]
    R -- Ei --> D[Yksin: oma hahmo asussa]
  end
  class A,P blue
  class S,L,K,FK,Y violet
  class Q,R,G,F,J,JQ amber
  class H,T,HJ,JT teal
  class V,W green
  class C,M,D,HP rose
```

## Colours

- **blue**: what the player taps
- **violet**: the game's own outfits and drawing
- **amber**: a check that decides the path
- **teal**: the picker's order
- **green**: the save on the phone
- **rose**: the figure in the game

## Boxes

- **Valikon nappi: 👕 Asu**: the menu button each game draws; shows the outfit now, e.g. "👕 Asu: Kurpitsa".
- **setup: pelin omat asut + piirto**: `AiPelitOutfits.setup({outfits, draw, change})` in the game's script; the first own outfit is the default.
- **Asulista: omat + 6 Halloween-asua + 5 jouluasua + 3 Tylypahka-asua**: `HALLOWEEN` in `public/outfits.js`: Kurpitsa, Noita, Haamu, Luuranko, Vampyyri, Muumio, and `TYLYPAHKA`: Harry, Ron, Hermione (black robe as the cape, house scarf, own hair; Harry's glasses and scar), each a palette plus a costume head drawn by `AiPelitOutfits.head()`. Orava's squirrel reads their `fur` colours instead. From #473 also `JOULU` in `public/outfits.js`: Joulupukki, Tonttu, Poro, Lumiukko, Piparkakku (`joulu: true`; legs in skin colour under the shorts like the everyday kits, as the published games and `kisa.js` draw them; heads `pukki`, `tonttu`, `poro`, `lumiukko`, `pipari` drawn by `head()`, `frontHead()` and so `sideHead()` and `figure()`). They are always in the list, so `get(id)` finds a friend's Christmas outfit in a room; only the picker and `current()` follow the season. A game passes `joulu: false` to leave them out; Orava gets none (Eero's choice): the library leaves them out for `data-game="orava"`, since Orava v6 cannot draw their heads.
- **Onko marras- tai joulukuu?**: `jouluSeason()` in `public/outfits.js` (#473): 1 November to 31 December, the phone's own date. Outside it `fill()` leaves the Christmas group out and `current()` returns the game's default when the saved choice is a Christmas costume; the saved key is left as it is, so the costume is back next November.
- **Onko 1.–2.11.?**: both seasons at once: `season()` is still true, so Halloween stays first for its last two days.
- **Joulu, Tavalliset, Tylypahka, Halloween; 🎄-tervehdys**: the group "🎄 Joulu" first, cards on a dark green background, and the line "Hyvää joulua! Pukeudu joulupukiksi, tontuksi tai poroksi." on a tall screen.
- **Halloween, Joulu, Tavalliset, Tylypahka; 🎃-tervehdys**: 1–2 November only.
- **Halloween, Tavalliset, Tylypahka**: `fill()` in `public/outfits.js`; on a low sideways screen each group's name is a small cell before its cards, so all of them fit without scrolling. When they still would not (#473: the athletics' seven kits with four groups), `open()` lays them out again with smaller cards (`tight`). The picker's canvases are `position:static`, so a game's own `canvas{position:fixed}` (Mäkihyppy, Voimistelu) leaves them in place.
- **Onko 20.10.–2.11.?**: `season()` in `public/outfits.js`. Upright the cards scroll inside the picker; sideways every group fits at once (`tests/test_outfits_lib.py`).
- **data-share yleisurheilu?**: `FIGURE` in `public/outfits.js` (#469): `SHARE === 'yleisurheilu'`.
- **Kortit ja liikkuva esikatselu: pelin oma piirto**: `fill()` draws each card with the game's `draw`, and `preview()` puts a 150 px canvas (`#ai-pelit-asut-esikatselu`) at the top where the game's own figure hops in the outfit the player taps; Orava, Trampoliini and Voimistelu keep their own figure (Eero's choice, #469). On a low sideways screen the preview is left out.
- **Kortit ja liikkuva esikatselu: yhteinen hahmo edestä**: `figure(ctx, dress(o), …)` in `public/outfits.js`, the front-facing athlete the podium and spectators of `lib/yleisurheilu-10/` and `-11/` draw too; costume heads face forward (`frontHead()`), and the preview's figure looks around, nods and cheers.
- **Pää kääntyy vauhdissa, ilmassa ja tuulettaessa: headPose**: `AiPelitOutfits.headPose(state, t)` (#469) returns `{tilt}` for `run` (a bob with the stride), `takeoff`, `air` (back), `land` (chin down), `cheer` and `idle`; Korkeushyppy v15, Pituushyppy v18, Keihäs v17, Kuula v11 and Seiväshyppy v16 pass it to `AiPelitOutfits.sideHead()` (a `headTilt(a)` of their own picks the state), Mäkihyppy v12 adds it to its head angle in `drawJumper()`. Drawing only: no result reads it.
- **Tallennus: ai-pelit:_asut:slug**: one key per game, shared by all its versions.
- **Yleisurheilun yhteiset 7 asua**: `AiPelitOutfits.yleisurheilu` in `public/outfits.js` (#311): Perus, Sinivalkoinen, Musta, Punainen, Vihreä, Kulta, Neon, the ids the events had on their own, so an earlier choice is found. Used from Pituushyppy v10, Korkeushyppy v6, Seiväshyppy v7, Moukari v6, Keihäs v9, Kuula v3, Aitajuoksu v10, Mäkihyppy v12 and Saappaanheitto v1 (Ottelu v7 used them until it was removed, #469).
- **data-share?**: `data-share="yleisurheilu"` on the script tag. `current()` reads the shared key. The first time a phone opens a game of the group, `adopt()` makes an earlier choice the group's: the first valid one in the fixed order of `SHARED_FROM` (Keihäs, Aitajuoksu, Kuula, then the game itself), so every game shows the same outfit whichever opens first.
- **Tallennus: ai-pelit:_asut:yleisurheilu + pelin oma**: a pick is saved under both keys, so the game's older versions, which read only their own, follow it too.
- **Asun id lähtee pelaajan tiedoissa, muut piirtävät sen**: Aitajuoksu sends the outfit id with the runner, the field events through the athletics library's `fit` option (`kisa.js`); a phone on an older version just draws its normal look.
