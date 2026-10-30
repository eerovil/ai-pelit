# AI-pelit

Tekoälyn tekemiä kännykkäpelejä yhdessä asennettavassa sovelluksessa:
https://pelit.vilpponen.fi/

- Pelihylly näyttää jokaisen pelin uusimman version; pelin sivulla ovat kaikki sen versiot, ja
  jokainen vanha versio on yhä pelattavissa.
- Asenna sovellus selaimen valikosta ("Asenna sovellus" / "Lisää kotivalikkoon"). Uudet pelit ja
  versiot tulevat näkyviin itsestään, ilman uudelleenasennusta.
- Kerran pelattu versio toimii ilman verkkoa. Pelien tallennukset pysyvät puhelimessa ja
  säilyvät, kun pelistä tulee uusi versio.
- Osassa peleistä on netin tuloslista (🏆 Tulokset). Nimimerkki valitaan kerran puhelimelle, ja se
  näkyy listoilla, kun ylläpitäjä on hyväksynyt sen osoitteessa `/yllapito/`. Ilman verkkoa
  tulos odottaa puhelimessa ja lähtee myöhemmin.
- Kirkkistä (v2) voi pelata kavereiden kanssa: yksi puhelin luo huoneen, muut liittyvät
  neljän kirjaimen koodilla tai QR-koodilla. 2–5 puhelinta, tyhjät paikat täyttävät
  tietokonepelaajat.
- Uusi peli tai versio tehdään AgentDeckissä: uusi Work tähän repoon.

## How it works

- `games/<slug>/v<N>/` — one self-contained version; never changed after merge.
- `games/<slug>/game.json` — title, description, and the version list.
- `games/<slug>/thumb.webp` — the game's picture on the shelf, a mid-play screenshot cut by
  `scripts/make_thumb.py`.
- `public/` — the shelf (`index.html`, `app.js`), the service worker (`sw.js`), the manifest,
  `back.js` (the "‹ Pelit" chip every game includes), `scores.js` (high-score lists), `rooms.js`
  (playing with friends in a live room) and `yllapito/` (approving nicknames).
- `functions/`, `server/`, `migrations/` — the site's `/api/` on Cloudflare Pages Functions and D1;
  `scripts/cloudflare_setup.py` sets them up. `rooms/` is the Worker that holds the live game
  rooms (a Durable Object per room code). See "Online extras" in AGENTS.md.
- `scripts/build.py` builds `_site/` with `catalog.json`; `scripts/check_immutable.py` guards
  published versions. A merge to `main` deploys to Cloudflare Pages, project `ai-pelit` (`.github/workflows/ci.yml`).
- [docs/diagrams/ai-pelit.md](docs/diagrams/ai-pelit.md) draws the whole flow;
  [docs/diagrams/tuloslistat.md](docs/diagrams/tuloslistat.md) the high-score lists;
  [docs/diagrams/moninpeli.md](docs/diagrams/moninpeli.md) playing with friends.

Rules for agents making games: [AGENTS.md](AGENTS.md).
Best practices for making a game that plays well: [docs/making-games.md](docs/making-games.md).
