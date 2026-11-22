# Pelihylly: haku, kategoriat ja viimeksi pelatut

The shelf's front page once there are many games (#523, the "Haku" layout Eero picked from the
prototype). Every game is its own short row, athletics events too; the phone's recently played
games sit on top, then a search box and category buttons narrow the list. Everything runs on the
phone from `catalog.json`, so it works offline.

```mermaid
flowchart TD
  A[Hylly avautuu] --> K[Kutsut ja avoimet huoneet, kuten ennen]
  K --> R{Onko puhelimessa viimeksi pelattuja?}
  R -- Kyllä --> RV[Viimeksi pelatut: rivi kuvia, napautus pelaa heti]
  R -- Ei --> H
  RV --> H[Hakukenttä: Etsi peliä]
  H --> C[Napit: Kaikki, Uudet, Päivitetyt, Kaverikaaos, Talvi...]
  L[Lista: jokainen peli omana rivinään, yleisurheilulajit myös]
  C --> J{Mikä nappi?}
  J -- Uudet --> JU[Julkaisujärjestys: uusin peli ensin]
  J -- Päivitetyt --> JP[Uusin versio ensin]
  J -- Kaikki tai kategoria --> JS[Suosituimmat ensin]
  JU --> L
  JP --> L
  JS --> L
  L --> F{Osuuko nimi tai kuvaus hakuun ja kategoriaan?}
  F -- Kyllä --> ROW[Rivi: kuva, nimi, versio, pelattu N kertaa, ● N, ▶]
  F -- Ei yhtään --> E[Ei osumia.]
  ROW -- napautus riviin --> P[Pelin sivu]
  ROW -- ▶ --> G[Peli koko ruudulla]
  RV --> G
  G -. back.js kirjaa pelin .-> M[ai-pelit:_hylly:viimeksi]
  M --> R
  Y[Vanha osoite #/yleisurheilu] --> C
  B[build.py: jokaisella pelillä category game.jsonissa] --> L
  class A,K,RV,H,C,L,ROW,E,P,G,JU,JP,JS blue
  class R,F,J amber
  class M,B teal
  class Y rose
```

## Colours

- **blue**: what the player sees and taps
- **amber**: a check that decides what shows
- **teal**: where the shelf's data comes from
- **rose**: an old address that still has to work

## Boxes

- **Kutsut ja avoimet huoneet, kuten ennen**: `drawPlaying()` and `showRooms()` in `public/app.js`, unchanged, above everything else.
- **Viimeksi pelatut: rivi kuvia, napautus pelaa heti**: up to 8 games from `ai-pelit:_hylly:viimeksi`, newest first, only slugs the catalog still lists; a sideways row of pictures, each a `games/<slug>/v<N>/` link, so the shelf's click handler adds the game's page under it as for ▶. Hidden when the list is empty.
- **Hakukenttä: Etsi peliä**: filters while typing, case-insensitive, on the game's name and description. The text and the chosen category are kept in `sessionStorage` (`ai-pelit:_hylly:haku`), so back from a game finds the same list.
- **Napit: Kaikki, Uudet, Päivitetyt, Kaverikaaos, Talvi...**: "Kaikki" (the default), "Uudet", "Päivitetyt", then one button per category that has games, from `catalog.json`'s `categories` (`CATEGORIES` in `scripts/build.py`). They replace the old sort menu.
- **Julkaisujärjestys: uusin peli ensin**: by the game's `released` in `catalog.json`: its first version's date, ties by when `games/<slug>/game.json` was added to git.
- **Uusin versio ensin**: the catalog's own order (`scripts/build.py`), as the old Päivitetyt sort.
- **Suosituimmat ensin**: all-time plays from `GET /api/plays`, ties in catalog order.
- **Lista: jokainen peli omana rivinään, yleisurheilulajit myös**: no group card any more; `renderShelf()` lists `catalog.games` one row each.
- **Rivi: kuva, nimi, versio, pelattu N kertaa, ● N, ▶**: a 36 × 48 picture, the name, `v<N> · pelattu N kertaa`, the green "playing now" number, and a round ▶ that opens the newest version. The description and the no. 1 score show on the game's page only.
- **Vanha osoite #/yleisurheilu**: a group's old address opens the shelf with that category chosen; a grouped game's page goes back with "‹ Kaikki pelit".
- **ai-pelit:_hylly:viimeksi**: `public/back.js` puts the opened game's slug first in this list (at most 8) each time a version page opens, except a page a game reloads itself to go on (`ai-pelit:_jatkuu`), as with the play count.
- **build.py: jokaisella pelillä category game.jsonissa**: each `games/<slug>/game.json` names `"category": "<key>"`; the build refuses a missing or unknown key and writes the categories into `catalog.json`.
