#!/usr/bin/env python3
"""Tells the site how much the voice relay was used this month (#322), every hour on the AgentDeck host.

    python3 scripts/turn_usage.py              # ask Cloudflare, write it to the site
    python3 scripts/turn_usage.py --dry-run    # print it, change nothing

Voice in rooms passes the sound through Cloudflare's TURN relay when two phones cannot reach each
other directly. It is free up to 1000 GB a month and billed after, and Cloudflare has no cap of its
own, so the site hands out relay credentials only while this month's use is under its cap (Eero's
choice; TURN_CAP in server/api.js) and this check has run within three days. The use is the whole
Cloudflare account's TURN traffic this month (UTC), in and out, which is what the free allowance
counts. Needs CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID (analytics read; on this host in
~/.local/share/ruokalista/cloudflare.env) and the admin key in ~/.local/share/ai-pelit/admin-key.
Run by scripts/systemd/ai-pelit-turn.timer (from origin/main).
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://pelit.vilpponen.fi/"
KEY_FILE = Path.home() / ".local/share/ai-pelit/admin-key"
QUERY = """query($a: String!, $s: Date!) { viewer { accounts(filter: {accountTag: $a}) {
  callsTurnUsageAdaptiveGroups(limit: 10000, filter: {date_geq: $s}) { sum { egressBytes ingressBytes } } } } }"""


def month_bytes(answer: dict) -> int:
    """The month's bytes in and out, from Cloudflare's GraphQL answer."""
    if answer.get("errors"):
        raise RuntimeError(f"cloudflare: {answer['errors']}")
    groups = answer["data"]["viewer"]["accounts"][0]["callsTurnUsageAdaptiveGroups"]
    return sum(int(g["sum"]["egressBytes"] or 0) + int(g["sum"]["ingressBytes"] or 0) for g in groups)


def ask_cloudflare(month_start: str) -> dict:
    body = {"query": QUERY, "variables": {"a": os.environ["CLOUDFLARE_ACCOUNT_ID"].strip('"'), "s": month_start}}
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN'].strip(chr(34))}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--site", default=SITE, help="another deploy, such as a preview (the same admin key)")
    args = ap.parse_args()
    for var in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not os.environ.get(var):
            sys.exit(f"set {var}")
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    used = month_bytes(ask_cloudflare(f"{month}-01"))
    print(f"{month}: {used / 1e9:.3f} GB")
    if args.dry_run:
        return 0
    req = urllib.request.Request(args.site + "api/admin/turn-usage", method="POST",
                                 data=json.dumps({"month": month, "bytes": used}).encode(), headers={
        "x-admin-key": KEY_FILE.read_text().strip(), "content-type": "application/json", "user-agent": "ai-pelit-turn",
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        print(f"{args.site}: {json.load(res)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
