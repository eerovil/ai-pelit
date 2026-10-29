# AI-pelit

Tekoälyn tekemiä kännykkäpelejä yhdessä asennettavassa sovelluksessa:
https://eero.vilpponen.fi/ai-pelit/

- Pelihylly näyttää jokaisen pelin uusimman version; pelin sivulla ovat kaikki sen versiot, ja
  jokainen vanha versio on yhä pelattavissa.
- Asenna sovellus selaimen valikosta ("Asenna sovellus" / "Lisää kotivalikkoon"). Uudet pelit ja
  versiot tulevat näkyviin itsestään, ilman uudelleenasennusta.
- Kerran pelattu versio toimii ilman verkkoa. Pelien tallennukset pysyvät puhelimessa ja
  säilyvät, kun pelistä tulee uusi versio.
- Uusi peli tai versio tehdään AgentDeckissä: uusi Work tähän repoon. Pelin sivulla on valmis
  teksti kopioitavaksi.

## How it works

- `games/<slug>/v<N>/` — one self-contained version; never changed after merge.
- `games/<slug>/game.json` — title, description, and the version list.
- `public/` — the shelf (`index.html`, `app.js`), the service worker (`sw.js`), the manifest and
  `back.js`, the "‹ Pelit" chip every game includes.
- `scripts/build.py` builds `_site/` with `catalog.json`; `scripts/check_immutable.py` guards
  published versions. A merge to `main` deploys to GitHub Pages (`.github/workflows/ci.yml`).
- [docs/diagrams/ai-pelit.md](docs/diagrams/ai-pelit.md) draws the whole flow.

Rules for agents making games: [AGENTS.md](AGENTS.md).
