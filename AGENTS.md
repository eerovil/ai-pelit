# Agent guide — ai-pelit

AI-made phone games, played from one PWA at https://pelit.vilpponen.fi/. Every version
of every game stays playable. Eero asks for games as AgentDeck Works on this repository; the
issue is the request, in Finnish. Write code comments and pull requests in English; everything a
player sees is Finnish unless the request says otherwise.

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`.
- "<Peli> v<N> (<slug>): …" — a new version. Copy `games/<slug>/v<N-1>/` to `games/<slug>/v<N>/`
  and change the copy. Append the version to `game.json`.

## Rules

1. **A published version never changes.** Never edit, move or delete a `games/<slug>/v<N>/` folder
   or its `game.json` entry once it is on `main`; a fix is a new version. CI runs
   `scripts/check_immutable.py` and fails a pull request that does.
2. **One folder per version, self-contained.** Plain HTML, CSS and JavaScript in the folder, no
   build step, no CDN, no fonts or images from the network, no API calls. It must run offline,
   forever.
3. **Include the back chip.** Every version's `index.html` ends its body with
   `<script src="../../../back.js"></script>` (the build refuses one without it). It draws
   "‹ Pelit" in the top-left corner. When the game's own score or buttons are there, move the chip
   with `data-corner="top-right"`, `"bottom-left"` or `"bottom-right"` on that script tag.
4. **Phone first.** Portrait, touch only, playable on a 360 × 640 screen, no hover, no keyboard
   needed. Use `100dvh`, safe-area insets, and `touch-action: none` on the play area. Short
   sounds through Web Audio only after the first tap.
5. **Saves stay on the phone, and survive new versions.** Save only to `localStorage`, under keys
   `ai-pelit:<slug>:<name>`. All versions of a game share those keys: a new version must read
   the previous version's saved data (or migrate it in place) and never rename, reset or clear
   it. Never touch another game's keys.
6. **game.json** — `title`, one-line `description`, and per version `n` (1, 2, 3… in order),
   `date` (YYYY-MM-DD, the merge day), `note` (one Finnish sentence: what changed), `request`
   (the issue text) and `issue` (`eerovil/ai-pelit#<n>`).

## Before you mark the pull request ready

- `python3 -m pytest -q` and `python3 scripts/build.py` pass. On a PR also
  `python3 scripts/check_immutable.py origin/main`.
- Play it yourself at 360 × 740 in Playwright, and attach screenshots of the shelf and the game
  mid-play to the issue, as AgentDeck's evidence rule says.
- The use-case walkthrough is: open the shelf, open the game, play one round, go back.

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

The site is served from the root of its own name, and uses only relative links.
`scripts/make_icons.py` redraws the app icons (needs Pillow); the PNGs are committed.
