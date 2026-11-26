# What a request means

Read for a new game, a new version or a "Palautteet" issue.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## What a request means

- "Uusi peli: …" — a new game. Pick a short slug (lowercase, digits, dashes), make
  `games/<slug>/v1/index.html` and `games/<slug>/game.json`.
- "<Peli> v<N> (<slug>): …" — a new version. Move the game's one version folder to the next
  number in a commit of its own (`git mv games/<slug>/v<N-1> games/<slug>/v<N>`), then make the
  change in the next commits, so the pull request shows only what changed (#346). Move its tests
  along the same way: `git mv` each `tests/test_<slug>_v<N-1>*.py` to `_v<N>`, and change every
  `games/<slug>/v<N-1>` in the game's test files to `v<N>`. Append the version to `game.json` before
  you run a test: the build, and so any test that builds the site, refuses a folder with no entry.
  Other games' tests name versions too (`tests/test_scores.py` names Puhelinkoppi's, Hiihto's and
  Piano's): `grep -rn "<slug>/v<N-1>" tests/` and run every file it finds before the first push,
  not only the game's own tests.
  The number is one above the game's highest ever (Puhelinkoppi went from `v2/` to `v5/`).
  If the version is past about 2000 lines in one file, split it into files (rule 2) as part of
  this version, without being asked, and say so in the pull request. Do the same for a new game
  that grows past it.
- "Palautteet <päivä>: <N> kpl" — the players' feedback (#184), filed once a day by
  `scripts/feedback_issue.py`. The feedback is private and this repository public, so the issue
  lists only each item's number and game; read the items with
  `python3 scripts/feedback_issue.py --show <this issue's number>` (it uses the admin key on this
  host). No pull request: for each item, look at the game it names, then ask Eero in the
  question box whether to fix it (quote it there, and say in one line what you would change;
  group items that ask the same). Each yes becomes a normal request issue,
  "<Peli> v<N> (<slug>): <what to change, in Finnish>", made with `gh issue create --label claude`
  (the poller's ownership label, so it starts its own Work; check its labels after). Write it in
  your own words and naming this issue: never a player's nickname or their words, on any issue
  or pull request. Post only Eero's yes or no per item number on this issue, then close it. Post his answers on the
  issue, then close it.
- Either way, take the game's picture for the shelf (#33): during your mid-play check at
  360 × 740, save a screenshot of a moment that shows the game well and run
  `python3 scripts/make_thumb.py <slug> <screenshot.png>`. It writes `games/<slug>/thumb.webp`.
  A new game needs one (the build refuses a game without it); retake it in a new version when the
  game looks different.
- A new game picks its shelf category (#523): `"category": "<key>"` in its `game.json`, one of
  `CATEGORIES` in `scripts/build.py` (kaverikaaos, talvi, yleisurheilu, pallo, temput, vauhti,
  seikkailu, rauhalliset); the build refuses a game without one. The shelf's buttons filter by it.
  A new category is added there, only when no key fits.
- An athletics event (#153) adds `"group": "yleisurheilu"` instead (`GROUPS` in
  `scripts/build.py`), which gives it its category. The shelf shows every game as its own row
  (#523), so a group no longer gathers games on the shelf; `#/yleisurheilu` opens the shelf with
  that button on.
- Ottelu (#168), the athletics match, was removed whole (#469, Eero's choice): nobody played it.
  `scripts/removed_games.py` names it, so `check_immutable.py` let its folders go,
  `catalog.json` lists it under `removed`, `_redirects` and `public/sw.js` send its addresses to
  the shelf, and its slug may not come back. Removing another game is a decision of Eero's, named
  there with its issue. An event version needs nothing for Ottelu any more; the events' code for
  its frame stays as history.

How to make a game that plays well (controls, difficulty, saves, layout, tests), from what Eero
asked to change in past versions: [docs/making-games.md](../making-games.md). Read it before you
start a new game or version. Its "Phone gotchas" list is what only showed on a real phone: when you
hit a new one (a layout, touch, sound or browser surprise), add one line there in the same pull
request, with the version that taught it (#181, Eero's choice).
