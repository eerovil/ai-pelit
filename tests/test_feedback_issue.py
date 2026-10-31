"""The daily "Palautteet" issue (#184), from scripts/feedback_issue.py. The repository is public
and the feedback private: the issue names only numbers and games."""

import sys
from datetime import datetime

from conftest import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import feedback_issue  # noqa: E402

FEEDBACK = [
    {"id": 7, "name": "Aino", "game": "hiihto", "version": 9, "text": "Rata 3 on liian vaikea.\n\nJa liian pitkä.", "at": "2026-10-31T16:05:00.000Z"},
    {"id": 8, "name": "Bertta", "game": "uusi", "version": None, "text": "Kiva!", "at": "2026-11-01T08:00:00Z"},
]


def test_the_public_issue_names_numbers_and_games_never_a_player_or_their_words():
    body = feedback_issue.issue_body(FEEDBACK, {"hiihto": "Hiihto"})
    assert "- 7. Hiihto (hiihto) v9\n- 8. uusi (uusi)\n" in body
    assert "--show" in body
    assert body.rstrip().endswith("<!-- feedback-ids: 7,8 -->")
    for private in ("Aino", "Bertta", "Rata 3", "liian", "Kiva"):
        assert private not in body
    assert feedback_issue.issue_title(FEEDBACK, datetime(2026, 11, 1)) == "Palautteet 1.11.2026: 2 kpl"
    # 200 items, the most one run takes, stay far under GitHub's body limit.
    many = [{**FEEDBACK[0], "id": i, "game": "x" * 40} for i in range(100000, 100200)]
    assert len(feedback_issue.issue_body(many, {})) < 65536 // 2


def test_show_prints_the_feedback_in_full_for_the_agent():
    out = feedback_issue.shown(FEEDBACK[:1], {"hiihto": "Hiihto"})
    assert out == "## 7. Hiihto (hiihto) v9\nAino, 31.10.2026 18.05\n\nRata 3 on liian vaikea.\n\nJa liian pitkä.\n"


def test_a_run_that_stopped_after_filing_is_finished_by_its_own_issue_only():
    feedback = [{"id": 7}, {"id": 8}, {"id": 9}]
    app = {"login": feedback_issue.AUTHOR}
    issues = [
        {"number": 201, "author": {"login": "joku"}, "body": "<!-- feedback-ids: 9 -->"},  # forged
        {"number": 200, "author": app, "body": "...\n<!-- feedback-ids: 5,6,7,8 -->\n"},  # filed, never marked
        {"number": 150, "author": app, "body": "<!-- feedback-ids: 1,2 -->"},  # older, all marked
        {"number": 199, "author": None, "body": None},
    ]
    assert feedback_issue.filed_earlier(feedback, issues) == {200: [7, 8]}
    assert feedback_issue.filed_earlier(feedback, []) == {}
