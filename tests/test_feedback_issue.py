"""The daily "Palautteet" issue's text (#184), from scripts/feedback_issue.py."""

import sys
from datetime import datetime

from conftest import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import feedback_issue  # noqa: E402


def test_the_issue_quotes_each_feedback_with_its_game_and_writer():
    feedback = [
        {"id": 7, "name": "Aino", "game": "hiihto", "version": 9, "text": "Rata 3 on liian vaikea.\n\nJa liian pitkä.", "at": "2026-10-31T16:05:00.000Z"},
        {"id": 8, "name": "Bertta", "game": "uusi", "version": None, "text": "Kiva!", "at": "2026-11-01T08:00:00Z"},
    ]
    body = feedback_issue.issue_body(feedback, {"hiihto": "Hiihto"})
    assert "## 7. Hiihto (hiihto) v9\nAino, 31.10.2026 18.05\n\n> Rata 3 on liian vaikea.\n>\n> Ja liian pitkä.\n" in body
    assert "## 8. uusi (uusi)\nBertta, 1.11.2026 10.00\n\n> Kiva!\n" in body
    assert body.rstrip().endswith("<!-- feedback-ids: 7,8 -->")
    assert feedback_issue.issue_title(feedback, datetime(2026, 11, 1)) == "Palautteet 1.11.2026: 2 kpl"


def test_a_player_cannot_mention_anyone_or_hide_text():
    assert feedback_issue.quoted("@eerovil katso #12 <!-- x -->") == ["> @\u200beerovil katso #\u200b12 &lt;!-- x -->"]
