# Agent guide — ai-pelit

AI-made phone games, played from one PWA at https://pelit.vilpponen.fi/. Only each game's
newest version is kept and played (#346, Eero's choice); the older ones are its history. Eero asks
for games as AgentDeck Works on this repository; the issue is the request, in Finnish. Write code
comments and pull requests in English; everything a player sees is Finnish unless the request
says otherwise.

Every model call carries this file, so it holds only what every task needs, in about 10k
characters (#558). The rest is in `docs/agents/`; each line below says when to read a file, and
you read it before that work, not after. A new rule or lesson goes in the matching file there. Add
it here only when every task needs it, in a line or two, and take something out to make room.

## Read first

- A new game or version: [docs/making-games.md](docs/making-games.md), how to make a game play
  well (controls, difficulty, saves, layout, tests). A new phone surprise gets one line in its
  "Phone gotchas", in the same pull request (#181).
- A new game, a new version or a "Palautteet" issue: [docs/agents/requests.md](docs/agents/requests.md).
- Before a game's first push: [docs/agents/rules.md](docs/agents/rules.md), the rules below in full.
- Before the first test run, before `gh pr ready`, on a failing test, after a review or a merge,
  taking over a pull request, a spec-only issue: [docs/agents/pull-requests.md](docs/agents/pull-requests.md).

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`. It needs a `category` (or the
  athletics `group`) and a `thumb.webp`; the build refuses a game without them.
- "<Peli> v<N> (<slug>): …" — a new version. First, in a commit of its own, move the game's one
  version folder (`git mv games/<slug>/v<N-1> games/<slug>/v<N>`) and its tests
  (`tests/test_<slug>_v<N-1>*.py` to `_v<N>`, and every `games/<slug>/v<N-1>` in them), then make
  the change in the next commits (#346). Append the version to `game.json` before any test: the
  build refuses a folder with no entry. `grep -rn "<slug>/v<N-1>" tests/` and run every file it
  finds, other games' tests too. The number is one above the game's highest ever. Before you
  build, check open pull requests and sibling Works for the same number.
- "Palautteet <päivä>: <N> kpl" — the players' feedback (#184). No pull request, and the feedback
  is private: never a player's nickname or words on an issue or pull request. Follow
  [requests.md](docs/agents/requests.md).
- Either way, take the shelf picture mid-play at 360 × 740:
  `python3 scripts/make_thumb.py <slug> <screenshot.png>`.
- Removing a game is Eero's decision (Ottelu, #469); a removed slug never comes back.

## Rules

Short forms; the full text and the reasons are in [docs/agents/rules.md](docs/agents/rules.md).

1. **A published version never changes; only the newest is kept.** Never edit a
   `games/<slug>/v<N>/` folder or its `game.json` entry once it is on `main`; a fix is a new
   version. The same holds for a published `public/lib/<name>-<N>/` folder: a fix is the next
   folder. CI runs `scripts/check_immutable.py`.
2. **One folder per game's version, self-contained.** Plain HTML, CSS and JavaScript, no build
   step, no TypeScript, no CDN, no fonts or images from the network; it plays offline, forever.
   The only network is this site's own `/api/`, as an extra the game never waits for. A version
   past about 2000 lines in one file is split into plain files with classic `<script src>` tags,
   unasked, and the pull request says so.
3. **Include the back chip.** Every `index.html` ends its body with
   `<script src="../../../back.js"></script>`; `data-corner` moves it off the game's own buttons.
4. **Phone first.** Touch only, playable at 360 × 640, no hover, no keyboard. Fill the screen
   with a fixed box, not `100dvh` (#181); safe-area insets; `touch-action: none` on the play
   area; sound through Web Audio only after the first tap. It also plays sideways at 740 × 360
   (#95), and turning the phone mid-round keeps the round.
5. **Saves stay on the phone, and survive new versions.** Only `localStorage`, keys
   `ai-pelit:<slug>:<name>` (`ai-pelit:_…` belongs to the shared scripts). A new version reads the
   old version's saves and never renames, resets or clears them. Never touch another game's keys.
6. **game.json** — `title`, one-line `description`, `category` (or `group`), and per version `n`
   (rising, never reused), `date` (YYYY-MM-DD, the merge day), `note` (one Finnish sentence),
   `request` (the issue text) and `issue` (`eerovil/ai-pelit#<n>`).
7. **Pin what the owner said.** Every behaviour the owner stated is in a test before the first
   push. Ask before building or dropping a mechanic the approved spec does not have.
8. **One step, several events.** Resolve events that fall in one step in time order, one exactly
   at the step's end included. Computer players and meters move only after the start.
9. **Scores you can reach.** Measure the best possible score, and set a computer opponent's cap
   from a simulation.
10. **Shared global scope.** Grep the version folder before adding a top-level name. A changed
    shape of a saved unfinished round gets a new key.
11. **Gestures.** Track the largest displacement during a touch, not where it ends.

## Online extras

The site is Cloudflare Pages; `/api/` is Pages Functions (`functions/api/[[path]].js` →
`server/api.js`) over a D1 database (`migrations/`). Shared scripts under `public/` (`back.js`,
`scores.js`, `rooms.js`, `kaverit.js`, `outfits.js`) serve every published version: change them
only in ways all of those keep working with. Read the file before you use or change its part:

- When a game or change uses one of these, [docs/agents/online-extras.md](docs/agents/online-extras.md): high scores (`scores.js`), play
  counts, outfits (`outfits.js`), feedback, friends, a schema change (a new migration, applied by
  hand right before the merge), `npm test` (only in the `node:22` container) and a preview deploy.
- Before you design, build or change a game played with friends,
  [docs/agents/rooms.md](docs/agents/rooms.md): "Live rooms" (the whole `rooms.js` API, the room
  page, voice, public rooms, turns, switching games), smooth movement (`lib/sulava-*`), and what
  to read before a room-game design. A small fix for a rare network race is yours to make
  without asking (#284).
- For an athletics event (group `yleisurheilu`), [docs/agents/athletics.md](docs/agents/athletics.md): its meet, podium and
  spectators (`lib/yleisurheilu-*/kisa.js`, `korkeus.js`).

## 3D games (three.js)

A 3D game imports three.js from the newest `public/lib/three-r*/`, never a copy and never
hand-made projection maths; its tests are marked `alone` and run only on this host. A published library
folder never changes (rule 1). Read [docs/agents/3d-games.md](docs/agents/3d-games.md) first: the
starter scene, add-ons, turning a 2D game into 3D, and slow phones.

## Sound effects

Recorded sounds come from the newest `public/lib/aanet-<N>/` and are played by name; only CC0,
no crowd noise, nothing loud (#337). Connect nothing to `ctx.destination` before `back.js` has
run. Read [docs/agents/sound.md](docs/agents/sound.md) first.

## Before you mark the pull request ready

The short list; every step, and what to do when one fails, is in
[docs/agents/pull-requests.md](docs/agents/pull-requests.md).

- `python3 -m pytest -q --changed-since origin/main`, `npm test` and `python3 scripts/build.py`
  pass, and `python3 scripts/check_immutable.py origin/main` after fetching and merging
  `origin/main`. The full browser suite never runs, not in CI and not by you (#65). A game's
  tests are `tests/test_<slug>_v<N>.py`, or carry `@pytest.mark.games("<slug>")`.
- Queue anything long with `agentdeck job submit`; run only a single test file directly. Never
  put an edit and a test run in one Bash call; run the test alone with
  `AGENTDECK_HEAVY_SLOT_HELD=1`. Leave the checkout alone while a job uses it.
- Prove each head you mark ready: `~/agentdeck/.venv/bin/agentdeck job submit --verification
  --session-token <token> --cwd <checkout> -- scripts/host-tests.sh`. It runs only the `alone`
  (3D) tests; run a 2D game's own tests separately. The deck merges only when that job and the
  pull request's CI are green on the same head.
- Merge `origin/main` (never rebase pushed commits) right before ready and after each review
  pass: `main` moves often, another Work may take the same version number, and GitHub runs no CI
  on a pull request that conflicts.
- Play it yourself at 360 × 740 in Playwright; screenshots of the shelf and the game mid-play go
  on the issue. A change to a shared file needs a game that uses it played the same way. The
  walkthrough: open the shelf, open the game, play one round, go back.
- For each changed file, grep the `## Boxes` sections in `docs/diagrams/` and update every box
  that names it; say in the pull request when none applies.
- A test you did not touch keeps failing: reproduce it on unchanged `origin/main` and find the
  cause. No retry commits, no guessed timing fix, no calling it flaky.
- A merge to `main` deploys at once. Wait with a commit wake-on named `deploy-cloudflare`, then
  ask the site itself. `verified` only once every flow the request names was tried on the real
  site; a touch change needs the owner's own phone.

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

Rebuild after every source edit. A prototype for Eero's phone is served with
`python3 scripts/serve_prototype.py <port>`, never plain `http.server` (#181). Ports, the service
worker and `tailscale serve`: read [docs/agents/local.md](docs/agents/local.md) before you serve
the site on this host.
