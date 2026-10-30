#!/bin/sh
# The 3D games' browser tests (marked alone by tests/conftest.py) run only on the AgentDeck host,
# never in GitHub CI (#123, Eero's choice): on GitHub's 4-core runner they had to run one at a
# time and took 9 of a 14-minute run. A Work agent proves its pull request's head with
#   ~/agentdeck/.venv/bin/agentdeck job submit --verification --session-token <token> --cwd <checkout> -- scripts/host-tests.sh
# and the deck merges only on that green run plus finished, green GitHub CI on the same head.
# Their software WebGL is heavy on the CPU: two side by side, at low priority so the host's other
# agents come first. Four at once took 2 min 4 s but failed a Hiihto v8 race on a busy host; two
# passed every 3D test in 2 min 48 s (#123).
# Only the changed games' 3D tests run (#37, #116); exit code 5 is "no test was selected".
set -e
cd "$(dirname "$0")/.."
git fetch -q origin main
nice -n 10 python3 -m pytest -q -p no:cacheprovider -n 2 --dist loadfile -m alone --changed-since origin/main || [ $? -eq 5 ]
