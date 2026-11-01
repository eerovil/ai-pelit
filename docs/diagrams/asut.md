# Asut: the shared outfit picker, Halloween and Tylypahka costumes

How a game version lets the player pick an outfit for their figure (#158). One shared script,
`public/outfits.js`, draws the picker and keeps the choice on the phone; each game draws its own
figure in the chosen outfit. The six Halloween costumes are the same in every game, always
available, and come first in the picker around Halloween. The three Tylypahka costumes (#321:
Harry, Ron and Hermione) are in every game too, right after the game's own outfits.

```mermaid
flowchart TD
  subgraph Peli
    A[Valikon nappi: 👕 Asu] --> B[AiPelitOutfits.open]
    S[setup: pelin omat asut + piirto] --> L[Asulista: omat + 6 Halloween-asua + 3 Tylypahka-asua]
  end
  subgraph outfits.js
    B --> Q{Onko 20.10.–2.11.?}
    Q -- Kyllä --> H[Halloween, Tavalliset, Tylypahka; 🎃-tervehdys]
    Q -- Ei --> T[Tavalliset, Tylypahka, Halloween]
    H --> K[Kortit: peli piirtää hahmon kussakin asussa]
    T --> K
    K --> P[Pelaaja napauttaa asua]
    P --> V[Tallennus: ai-pelit:_asut:slug]
  end
  subgraph Pelaaminen
    V --> C[change: peli piirtää hahmon uudessa asussa]
    C --> R{Kavereiden huone?}
    R -- Kyllä --> M[Asun id lähtee pelaajan tiedoissa, muut piirtävät sen]
    R -- Ei --> D[Yksin: oma hahmo asussa]
  end
  class A,P blue
  class S,L,K violet
  class Q,R amber
  class H,T teal
  class V green
  class C,M,D rose
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
- **Asulista: omat + 6 Halloween-asua + 3 Tylypahka-asua**: `HALLOWEEN` in `public/outfits.js`: Kurpitsa, Noita, Haamu, Luuranko, Vampyyri, Muumio, and `TYLYPAHKA`: Harry, Ron, Hermione (black robe as the cape, house scarf, own hair; Harry's glasses and scar), each a palette plus a costume head drawn by `AiPelitOutfits.head()`. Orava's squirrel reads their `fur` colours instead.
- **Halloween, Tavalliset, Tylypahka**: `fill()` in `public/outfits.js`; on a low sideways screen each group's name is a small cell before its cards, so all of them fit without scrolling.
- **Onko 20.10.–2.11.?**: `season()` in `public/outfits.js`.
- **Tallennus: ai-pelit:_asut:slug**: one key per game, shared by all its versions.
- **Asun id lähtee pelaajan tiedoissa, muut piirtävät sen**: Aitajuoksu and Keihäänheitto send the outfit id with the player; a phone on an older version just draws its normal look.
