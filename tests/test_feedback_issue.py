"""The daily "Palautteet" issue (#184), from scripts/feedback_issue.py. The repository is public
and the feedback private: the issue names only numbers and games."""

import json
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
    # The App as `gh issue list --json author` names it (checked on #184), and as the REST API does.
    for login in ("app/agentdeck-eerovil", "agentdeck-eerovil[bot]"):
        app = {"is_bot": True, "login": login}
        issues = [
            {"number": 201, "author": {"login": "joku"}, "body": "<!-- feedback-ids: 9 -->"},  # forged
            {"number": 202, "author": {"login": "agentdeck-eerovil"}, "body": "<!-- feedback-ids: 9 -->"},  # a look-alike user
            {"number": 200, "author": app, "body": "...\n<!-- feedback-ids: 5,6,7,8 -->\n"},  # filed, never marked
            {"number": 150, "author": app, "body": "<!-- feedback-ids: 1,2 -->"},  # older, all marked
            {"number": 199, "author": None, "body": None},
        ]
        assert feedback_issue.filed_earlier(feedback, issues) == {200: [7, 8]}
    assert feedback_issue.filed_earlier(feedback, []) == {}


def test_an_issue_linked_but_never_labelled_is_started():
    app = {"login": "agentdeck-eerovil[bot]"}
    issues = [
        {"number": 300, "author": app, "state": "OPEN", "labels": [], "body": "<!-- feedback-ids: 7 -->"},
        {"number": 301, "author": app, "state": "OPEN", "labels": [{"name": "claude"}], "body": "<!-- feedback-ids: 8 -->"},
        {"number": 302, "author": app, "state": "CLOSED", "labels": [], "body": "<!-- feedback-ids: 9 -->"},
        {"number": 303, "author": {"login": "joku"}, "state": "OPEN", "labels": [], "body": "<!-- feedback-ids: 9 -->"},
    ]
    assert feedback_issue.unstarted(issues) == [300]


class Host:
    """The site and GitHub as the script sees them, recording what it does in order."""

    def __init__(self, feedback, issues=(), fail_link=False):
        self.feedback, self.issues, self.fail_link, self.done = feedback, list(issues), fail_link, []

    def call(self, method, path, key, body=None):
        if method == "GET":
            return {"feedback": [f for f in self.feedback if not f.get("issue")]}
        self.done.append(("link", body["issue"], body["ids"]))
        if self.fail_link:
            raise OSError("network down")
        for f in self.feedback:
            if f["id"] in body["ids"]:
                f["issue"] = body["issue"]
        return {"ok": True}

    def run(self, cmd, **kw):
        class Out:
            stdout = ""
        if cmd[:3] == ["gh", "issue", "list"]:
            Out.stdout = json.dumps(self.issues)
        elif cmd[:3] == ["gh", "issue", "create"]:
            assert "--label" not in cmd and kw["env"]["AGENTDECK_NO_OWNER_LABEL"] == "1"
            body = open(cmd[cmd.index("--body-file") + 1]).read()
            n = 300 + len(self.issues)
            self.issues.append({"number": n, "author": {"login": "app/agentdeck-eerovil"}, "state": "OPEN", "labels": [], "body": body})
            self.done.append(("create", n))
            Out.stdout = f"https://github.com/eerovil/ai-pelit/issues/{n}\n"
        elif cmd[:3] == ["gh", "issue", "edit"]:
            n = int(cmd[3])
            next(i for i in self.issues if i["number"] == n)["labels"].append({"name": cmd[cmd.index("--add-label") + 1]})
            self.done.append(("label", n))
        return Out


def run_script(monkeypatch, tmp_path, host):
    (tmp_path / "key").write_text("avain")
    monkeypatch.setattr(feedback_issue, "KEY_FILE", tmp_path / "key")
    monkeypatch.setattr(feedback_issue, "call", host.call)
    monkeypatch.setattr(feedback_issue, "titles", lambda: {})
    monkeypatch.setattr(feedback_issue.subprocess, "run", host.run)
    monkeypatch.setattr(sys, "argv", ["feedback_issue.py"])
    return feedback_issue.main()


def test_the_work_starts_only_after_its_feedback_is_linked(monkeypatch, tmp_path):
    host = Host([{**FEEDBACK[0]}, {**FEEDBACK[1]}])
    assert run_script(monkeypatch, tmp_path, host) == 0
    assert host.done == [("create", 300), ("link", 300, [7, 8]), ("label", 300)]


def test_a_run_cut_off_before_linking_is_finished_by_the_next(monkeypatch, tmp_path):
    host = Host([{**FEEDBACK[0]}, {**FEEDBACK[1]}], fail_link=True)
    try:
        run_script(monkeypatch, tmp_path, host)
    except OSError:
        pass
    assert host.done == [("create", 300), ("link", 300, [7, 8])]  # no label: no Work on an empty list
    host.fail_link, host.done = False, []
    run_script(monkeypatch, tmp_path, host)
    assert host.done == [("link", 300, [7, 8]), ("label", 300)]  # the same issue, not a new one
    host.done = []
    run_script(monkeypatch, tmp_path, host)
    assert host.done == []
