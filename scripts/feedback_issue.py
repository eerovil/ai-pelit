#!/usr/bin/env python3
"""Files the players' new feedback (#184) as one "Palautteet" issue, once a day on the AgentDeck host.

    python3 scripts/feedback_issue.py            # file the new feedback, if there is any
    python3 scripts/feedback_issue.py --dry-run  # print the issue it would file, change nothing

Players write feedback on a game's page in the shelf (approved nicknames only); it waits in the
site's database until this script files it. The issue carries the `claude` label, so AgentDeck
starts a Work on it: its agent asks Eero about each item and turns a yes into a normal version
request (AGENTS.md, "Palautteet"). Each item is then marked with the issue's number, so it is
filed once. Run daily by scripts/systemd/ai-pelit-palautteet.timer (from origin/main); needs the admin key in
~/.local/share/ai-pelit/admin-key and a logged-in `gh`.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SITE = "https://pelit.vilpponen.fi/"
REPO = "eerovil/ai-pelit"
LABEL = "claude"  # the poller's ownership label: a Work starts on the issue
KEY_FILE = Path.home() / ".local/share/ai-pelit/admin-key"
TZ = ZoneInfo("Europe/Helsinki")


def call(method: str, path: str, key: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(SITE + path, data=data, method=method, headers={
        "x-admin-key": key, "content-type": "application/json", "user-agent": "ai-pelit-palautteet",
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def fi_date(iso: str) -> str:
    t = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    return f"{t.day}.{t.month}.{t.year} {t:%H.%M}"


def safe(text: str) -> str:
    """A player's words that cannot mention anyone, link an issue or hide in HTML: a zero-width
    space after @ and #, and < as &lt;."""
    return text.replace("<", "&lt;").replace("@", "@\u200b").replace("#", "#\u200b")


def quoted(text: str) -> list[str]:
    return ["> " + line if line else ">" for line in safe(text).split("\n")]


def issue_body(feedback: list[dict], titles: dict[str, str]) -> str:
    lines = [
        "Pelaajien uudet palautteet pelihyllystä (#184). Kysy minulta jokaisesta, korjataanko;"
        " kyllä-vastauksesta tee tavallinen versiopyyntö (AGENTS.md, \"Palautteet\").",
        "",
    ]
    for f in feedback:
        game = f"{titles.get(f['game'], f['game'])} ({f['game']})" + (f" v{f['version']}" if f.get("version") else "")
        lines += [f"## {f['id']}. {game}", f"{safe(f['name'])}, {fi_date(f['at'])}", ""]
        lines += quoted(f["text"])
        lines.append("")
    lines.append(f"<!-- feedback-ids: {','.join(str(f['id']) for f in feedback)} -->")
    return "\n".join(lines) + "\n"


def issue_title(feedback: list[dict], today: datetime) -> str:
    return f"Palautteet {today.day}.{today.month}.{today.year}: {len(feedback)} kpl"


MARKER = re.compile(r"<!-- feedback-ids: ([0-9,]+) -->")


def filed_earlier(feedback: list[dict], issues: list[dict]) -> dict[int, list[int]]:
    """Which of `feedback` an earlier run already filed, by its issue's feedback-ids marker:
    {issue number: [ids]}. A run that filed the issue but stopped before marking the items
    (network, a restart) is finished here instead of filing them again."""
    waiting = {f["id"] for f in feedback}
    found: dict[int, list[int]] = {}
    for issue in issues:
        for m in MARKER.finditer(issue.get("body") or ""):
            ids = [int(i) for i in m[1].split(",") if i and int(i) in waiting]
            if ids:
                found.setdefault(issue["number"], []).extend(ids)
                waiting -= set(ids)
    return found


def earlier_issues() -> list[dict]:
    out = subprocess.run(["gh", "issue", "list", "--repo", REPO, "--state", "all", "--search", "Palautteet in:title",
                          "--limit", "30", "--json", "number,body"], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def main() -> int:
    global SITE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the issue, file nothing")
    ap.add_argument("--site", default=SITE, help="another deploy, such as a preview (its own admin key)")
    args = ap.parse_args()
    SITE = args.site.rstrip("/") + "/"
    key = KEY_FILE.read_text().strip()
    feedback = call("GET", "api/admin/feedback?new=1", key)["feedback"]
    if not feedback:
        print("no new feedback")
        return 0
    if not args.dry_run:
        for number, ids in filed_earlier(feedback, earlier_issues()).items():
            call("POST", "api/admin/feedback", key, {"ids": ids, "issue": number})
            print(f"already filed in {REPO}#{number}: {ids}")
            feedback = [f for f in feedback if f["id"] not in ids]
        if not feedback:
            return 0
    with urllib.request.urlopen(urllib.request.Request(SITE + "catalog.json", headers={"user-agent": "ai-pelit-palautteet"}), timeout=30) as res:
        titles = {g["slug"]: g["title"] for g in json.load(res)["games"]}
    title, body = issue_title(feedback, datetime.now(TZ)), issue_body(feedback, titles)
    if args.dry_run:
        print(title, body, sep="\n\n")
        return 0
    with tempfile.NamedTemporaryFile("w", suffix=".md", dir="/var/tmp") as f:
        f.write(body)
        f.flush()
        out = subprocess.run(["gh", "issue", "create", "--repo", REPO, "--title", title, "--label", LABEL, "--body-file", f.name],
                             check=True, capture_output=True, text=True).stdout
    m = re.search(r"/issues/(\d+)", out)
    if not m:
        print(f"filed, but no issue number in: {out!r}", file=sys.stderr)
        return 1
    call("POST", "api/admin/feedback", key, {"ids": [f["id"] for f in feedback], "issue": int(m[1])})
    print(f"filed {len(feedback)} as {REPO}#{m[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
