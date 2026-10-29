# AI-pelit: how a game is played and how a new one is made

The AI-pelit PWA (eerovil/eeron-omat-taskit#149). Playing is a static page on GitHub Pages: the shelf lists every
game, each game lists its versions, and any version opens full screen. A new game or version is
always started from AgentDeck (Eero's choice): the agent writes it into a new version folder,
and the merge deploys it. The app has no form.

```mermaid
flowchart TD
  subgraph Pelaaminen
    A[Puhelin avaa pelit.vilpponen.fi] --> B[Pelihylly: uusin versio jokaisesta pelistä]
    B --> C[Pelin sivu: versiot v1, v2, v3...]
    C --> D[Pelaa versiota koko ruudulla]
    D --> E{Verkko poissa?}
    E -- Kyllä --> F[Service worker antaa välimuistista]
    E -- Ei --> G[Haetaan /games/slug/vN/]
  end
  subgraph Uusi peli tai versio AgentDeckissä
    C -. kopioi teksti .-> H[AgentDeck: uusi Work ai-pelit-repoon]
    H --> L[Agentti aloittaa Workin]
    L --> M[Agentti kirjoittaa games/slug/vN/ ja game.json]
    M --> N[PR, katselmointi, automaattinen merge]
    N --> O[GitHub Pages julkaisee]
    O --> B
  end
  class A,B,C,D blue
  class E amber
  class F,G teal
  class H violet
  class L,M,N rose
  class O green
```

## Colours

- **blue**: what the player sees and taps
- **amber**: a check that decides the path
- **teal**: where the game's files come from
- **violet**: where Eero starts a new game or version
- **rose**: AgentDeck's agent work, on Eero's existing subscription
- **green**: the deploy that makes the new version live

## Boxes

- **Pelihylly: uusin versio jokaisesta pelistä**: `public/index.html` rendered from `catalog.json` (first game: Sormiskeitti v1), which `scripts/build.py` builds from every `games/*/game.json`.
- **Pelin sivu: versiot v1, v2, v3...**: lists each version with its date and the change note; every version stays playable.
- **Pelaa versiota koko ruudulla**: opens `/games/<slug>/v<N>/index.html` directly (not in an iframe) with the "‹ Pelit" chip from `public/back.js`.
- **Service worker antaa välimuistista**: `public/sw.js`: the shell and `catalog.json` network-first, version folders cache-first once played.
- **AgentDeck: uusi Work ai-pelit-repoon**: Eero writes "Uusi peli: …" or "<peli> v<N>: …"; each game page shows that text ready to copy.
- **Agentti kirjoittaa games/slug/vN/ ja game.json**: a new version is always a new folder; old version folders are never edited.
- **GitHub Pages julkaisee**: `.github/workflows/ci.yml`: tests, then `actions/deploy-pages`. No secrets.
