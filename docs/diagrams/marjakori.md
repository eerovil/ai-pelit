# Marjakori: yksi taso, ensimmäisestä pyyhkäisystä tulokseen

Marjakori is a swipe match-3 game. The player swaps a forest shape with its neighbour, and three or more in a row or column disappear. A level is passed by collecting its target shapes or clearing moss within a limited number of moves.

```mermaid
flowchart TD
  A[Valikko: Jatka tai valitse taso] --> B[Taso alkaa: 7 × 7 lauta, ei valmiita rivejä, vähintään yksi siirto]
  B --> C[Pyyhkäise kuvio viereisen paikalle, tai napauta kahta vierekkäistä]
  C --> D{Kimallus tai kaksi erikoiskuviota?}
  D -- Kyllä --> H[Erikoiskuvio laukeaa]
  D -- Ei --> E{Syntyikö 3 tai enemmän samaa?}
  E -- Ei --> F[Kuviot palaavat, siirto ei kulu]
  F --> C
  E -- Kyllä --> G[Siirto kuluu, kuviot poistuvat, pisteet ja tavoite kasvavat]
  H --> G
  G --> I{Montako samaa?}
  I -- 3 --> K[Yläpuolen kuviot putoavat, uudet tulevat ylhäältä]
  I -- 4 --> J1[Syntyy Puuska: tyhjentää rivinsä tai sarakkeensa]
  I -- 5 tai L tai T --> J2[Syntyy Kimallus: poistaa kaikki yhtä lajia]
  J1 --> K
  J2 --> K
  K --> L{Syntyikö pudotuksesta uusi rivi?}
  L -- Kyllä: kerroin kasvaa --> G
  L -- Ei --> M{Tavoite täynnä?}
  M -- Kyllä --> N[Taso läpi: jäljellä olevat siirrot pisteiksi, taso ja ennätys talteen heti]
  N --> O[Tulos lähtee listalle, Seuraava taso]
  O --> B
  M -- Ei --> P{Siirtoja jäljellä?}
  P -- Ei --> Q[Ei onnistunut: Yritä uudelleen, mitään ei menetetä]
  Q --> B
  P -- Kyllä --> R{Onko laudalla siirtoa?}
  R -- Ei --> S[Lauta sekoittuu itsestään, ilmaiseksi]
  S --> C
  R -- Kyllä --> C

  class A,B,C blue
  class D,E,I,L,M,P,R amber
  class G,H,J1,J2,K,S violet
  class F,Q rose
  class N,O green
```

## Colours

- **blue**: what the player sees and does
- **amber**: a question the game asks
- **violet**: what the board does by itself
- **rose**: a try that did not work
- **green**: a level won and saved

## Boxes

- **Taso alkaa: 7 × 7 lauta, ei valmiita rivejä, vähintään yksi siirto**: `newLevel()` in `games/marjakori/v1/logiikka.js`, from a seed saved with the round, so a reload brings the same board.
- **Pyyhkäise kuvio viereisen paikalle, tai napauta kahta vierekkäistä**: the swap fires once the finger has moved about a third of a tile, without waiting for it to lift (`ohjaus` in `index.html`).
- **Kuviot palaavat, siirto ei kulu**: a swap that matches nothing costs nothing; the tiles slide back.
- **Syntyy Puuska: tyhjentää rivinsä tai sarakkeensa**: four in a line.
- **Syntyy Kimallus: poistaa kaikki yhtä lajia**: five in a line, or an L or T shape; swiped with a neighbour it takes every tile of that neighbour's kind.
- **Taso läpi: jäljellä olevat siirrot pisteiksi, taso ja ennätys talteen heti**: saved as `ai-pelit:marjakori:taso` and `:parhaat` the moment the level is won.
- **Tulos lähtee listalle, Seuraava taso**: the sum of each level's best points goes to `AiPelitScores.submit()`.
- **Lauta sekoittuu itsestään, ilmaiseksi**: `hasMove()` in `logiikka.js` is false, so the tiles are mixed until a move exists.
