# Tests, the pull request, the merge and the live check

Read before you queue the first test run, before you mark a pull request ready, when a test fails, after a review or a merge, when you take over a pull request, and on a spec-only issue.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## Before you mark the pull request ready

- `python3 -m pytest -q --changed-since origin/main`, `npm test` and `python3 scripts/build.py`
  pass. On a PR also `python3 scripts/check_immutable.py origin/main`, after fetching and merging
  `origin/main`, so it also sees a number another Work has taken since.
  The full browser suite
  never runs, not in CI and not by you (#65, Eero's choice): with `--changed-since` a game's own
  tests run only when the change touches `games/<slug>/` or that game's test file (#37), and a
  change outside `games/` runs only the shared tests, the ones tied to no game. So name a game's
  tests `tests/test_<slug>.py` (or `test_<slug>_<more>.py`, dashes as underscores), or mark a test
  that plays a game with `@pytest.mark.games("<slug>")`. Within a game only the test files of the
  changed versions run (#116): a file tests the `_v<N>` in its name and every `games/<slug>/v<N>`
  written in it. So a new version's tests go in `tests/test_<slug>_v<N>.py`, or name its folder
  (the moved test files of the version before, see "What a request means").
  Editing an existing test file of the game runs all of them (they import each other); a new test
  file runs only itself; a version no file names runs all of them.
  GitHub CI runs them on four workers (`-n 4 --dist loadfile -m "not alone"`, pytest-xdist). The
  tests of 3D games (versions that load `lib/three`, marked `alone` by `tests/conftest.py`) never
  run in CI (#123): on GitHub's runner they had to run one at a time and took most of the run.
  They run on the AgentDeck host, four side by side: prove each head you mark ready with
  `~/agentdeck/.venv/bin/agentdeck job submit --verification --session-token <token> --cwd <checkout> -- scripts/host-tests.sh`.
  On this host the tests' Chromium draws 3D on the graphics card, not in software on the
  processor (#248: `GPU_ARGS` in `tests/conftest.py`); a run with 3D tests ends with a
  `WebGL:` line naming the card, or SwiftShader when it fell back to software.
  When you change a shared file (`public/back.js`, `rooms.js`, `scores.js`...), play a game that
  uses it yourself, and grep every game's tests for counts of what it shows.
- A run proves only the head it ran on. Queue anything long (the `--changed-since` run, the host
  tests) with `agentdeck job submit`, and run only a single test file directly. Read
  `~/agentdeck/.venv/bin/agentdeck job list` first and reuse a green run on this exact head; each
  push or merge of `origin/main` makes a new head, so run again and quote only that run. Leave the
  checkout alone while a job uses it.
- `scripts/host-tests.sh` runs only `alone` (3D) tests, and exit code 5, nothing selected, counts as
  green. Report only the tests its output names, and its `WebGL:` line; run a 2D game's own tests
  separately. A file's name proves nothing either: `tests/test_hiljaiset_aanet.py` holds helpers and
  no test, so see a file collected (`python3 -m pytest --collect-only -q <file>`) before you cite it.
- So that green verification job and the pull request's CI are the last checks before release:
  the deck merges only when both are green on the same head. A merge to `main` deploys at once
  (#65): the deploy job runs only `npm test` and the build (seconds), then the rooms Worker and
  the site. `main` runs no browser tests; they already passed on the pull request's head.
  To wait for it, register a commit wake-on for the merge commit named `deploy-cloudflare`, never
  polling: this repository sends no deployment events, so a deployment wake-on does not fire
  (#207). Then ask the site itself: `curl -s -o /dev/null -w '%{http_code}' "https://pelit.vilpponen.fi/<new path>?x=$RANDOM"`
  and the game's versions in `catalog.json`. A 404 right after the merge is the deploy still
  running: look again a minute later before calling it not live (#205).
- Record a live check as `verified` only once every merged change in the Work is live and you have
  tried each flow the request names on the real site. Green tests are not that, and a touch change
  needs the owner's own phone (docs/making-games.md).
- GitHub runs no pull-request CI while the pull request conflicts with `main` (#346): the push
  starts no run, so a wake-on for the `test` check never fires, and neither closing and reopening
  nor an empty commit helps. When no run appears for a pushed head, read `gh pr view <n> --json
  mergeable,mergeStateStatus` once. If it says `CONFLICTING` or `DIRTY`, merge `origin/main` into
  the branch (never rebase pushed commits), fix the conflict, push, and register the wake-on again
  for the new head. `main` moves often here (many Works at once), and another Work often takes
  the same version number, so merge `origin/main` right before you mark the pull request ready (then commit every doc
  and diagram edit, run `python3 scripts/build.py` and `python3 scripts/check_immutable.py
  origin/main`, and queue one verification job)
  and again after each review pass, and on a long-running pull request before each push. Before
  you build, check open pull requests and sibling Works for the same game's next number. A pull
  request that needs another open version change merges it in before review and again once it lands.
- Never put an edit (`sed -i`, a heredoc) in the same Bash call as a test run: the AgentDeck
  queue hook refuses the whole chain. Edit in one call, then run the test alone with
  `AGENTDECK_HEAVY_SLOT_HELD=1`.
- A fix for a chance-based test (a throw, a random round): run it once with a short timeout and
  measure its real range before you queue a long job on it.
- A test you did not touch keeps failing: reproduce it on unchanged `origin/main` and find the cause
  before you change it. No retry commits, no guessed timing fix, no calling it flaky.
- Before you add a new row to a list in `public/app.js`, grep `tests/` for that list's class
  selectors (`.friend`, `.friend .meta`) and give the new row a class of its own, so the old
  tests do not pick it up.
- Play it yourself at 360 × 740 in Playwright, and attach screenshots of the shelf and the game
  mid-play to the issue, as AgentDeck's evidence rule says.
  For a 3D game, launch Chromium with `tests/conftest.py`'s `GPU_ARGS`, so it draws on the card.
- `games/<slug>/thumb.webp` shows the current version mid-play.
- The use-case walkthrough is: open the shelf, open the game, play one round, go back.

- There is no `package-lock.json`: run `npm test` in the `node:22` container, never `npm ci`.
  Run the container step once by hand before you queue it.
- When a game gains hills, trips, boards or a version number, grep `tests/`, `docs/`,
  `game.json` for the old count, "only" wording and the old version name, and
  fix them in the same commit.
- In a browser test, set state, read it and trigger the action in one `page.evaluate` call; after
  a send, wait with `wait_for_function` instead of asserting at once.
- Drive timing tests at a fixed pace and take bounds from the frame's own time. Reproduce a
  CI-only failure with `taskset -c 0,1 … -n 4` from the exact failing line, and change one factor
  at a time (audio backend, CPU). A failure only under load can be a real bug: do not loosen the
  test.
- A change to a shared file such as `public/rooms.js` also needs a game that uses it played at
  360 × 740, with the screenshots on the issue, before you mark the pull request ready.
- A review finding in one game or trip is checked in every sibling game and trip, and fixed in
  the same pull request.
- See a new test fail without the fix, from the owner's exact state. Run each new parametrized
  case alone before you queue the suite.

## Taking over a pull request, and specs

- When you take over a pull request another Work started, read every earlier review comment and
  every test it asked for, and cover each one before you first mark it ready.
- On a spec-only issue, end the turn that posts the spec with the approval question in the
  question box in that same turn, not with a prose summary.

- Before editing again after an approval, read the pull request's state: if it merged, branch from
  `origin/main` and never push the deleted branch again.
- When the owner asked for a diagram, copy the six `classDef` colour lines of AgentDeck's diagram guide
  ("Diagrams" in `GET $AGENTDECK_URL/api/live-prototype/guide`) into the first diagram comment on the issue: the
  files in `docs/diagrams/` hold only the `class` lines.
