#!/usr/bin/env python3
"""Set up and migrate the online parts on Cloudflare: D1 databases and the Pages project's bindings.

    CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=… python3 scripts/cloudflare_setup.py

Safe to run again; run it after adding a file to migrations/, before that change merges.

- Makes the D1 databases `ai-pelit` (production) and `ai-pelit-preview` (preview deploys) if
  they are missing, and applies every migrations/*.sql not yet applied, recording each in the
  same `d1_migrations` table `wrangler d1 migrations apply` uses.
- Binds them as `DB` on the Pages project `ai-pelit` (production and preview).
- Binds the live game rooms (#27) as `ROOMS`: the `Room` Durable Object of the `ai-pelit-rooms`
  Worker (rooms/). Deploy that Worker once first (`npx wrangler deploy -c rooms/wrangler.toml`;
  CI deploys it on every merge after that), or this step is skipped with a note.
- Makes the `ADMIN_KEY` secret (the nickname admin's key) when it is missing, and saves it on
  this host in ~/.local/share/ai-pelit/admin-key (mode 600). It is never printed.
- Binds the voice relay's key (#322) as the `TURN_KEY_ID` and `TURN_KEY_TOKEN` secrets, from
  ~/.local/share/ai-pelit/turn.env (two lines, `TURN_KEY_ID=…` and `TURN_KEY_TOKEN=…`). When the
  file is missing it makes a Cloudflare Realtime TURN key and saves it there, if the API token
  may (permission "Calls Write"); otherwise it says how to make one by hand, and voice in rooms
  works without the relay (phones connect directly, which some mobile networks block).
- Binds the invite notifications' signing key (#367) as the `VAPID_PRIVATE_KEY` secret, from
  ~/.local/share/ai-pelit/vapid.env (`VAPID_PUBLIC_KEY=…` and `VAPID_PRIVATE_KEY=…`). Its public
  half is written in server/api.js and public/kaverit.js, so a new pair is never made here: when
  the file is missing or its public key is not the one in server/api.js, the step is skipped with
  a note, and invites show only as banners.

The bindings live on the Pages project rather than in a wrangler.toml, so CI's deploy token
needs no D1 permission: `wrangler pages deploy` keeps the project's bindings.
"""

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "ai-pelit"
DATABASES = {"production": "ai-pelit", "preview": "ai-pelit-preview"}
KEY_FILE = Path.home() / ".local/share/ai-pelit/admin-key"
TURN_FILE = Path.home() / ".local/share/ai-pelit/turn.env"
VAPID_FILE = Path.home() / ".local/share/ai-pelit/vapid.env"
ROOMS_SCRIPT, ROOMS_CLASS = "ai-pelit-rooms", "Room"


def api(method: str, path: str, body=None):
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)["result"]
    except urllib.error.HTTPError as e:
        sys.exit(f"cloudflare: {method} {path} -> {e.code} {e.read().decode()[:500]}")


def database(name: str) -> str:
    for db in api("GET", f"/d1/database?name={name}"):
        if db["name"] == name:
            return db["uuid"]
    print(f"  creating D1 database {name}")
    return api("POST", "/d1/database", {"name": name})["uuid"]


def query(db: str, sql: str, params=None) -> list:
    return api("POST", f"/d1/database/{db}/query", {"sql": sql, "params": params or []})[0]["results"]


def migrate(db: str, name: str) -> None:
    query(db, "CREATE TABLE IF NOT EXISTS d1_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT,"
              " name TEXT UNIQUE, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)")
    done = {r["name"] for r in query(db, "SELECT name FROM d1_migrations")}
    for f in sorted((ROOT / "migrations").glob("*.sql")):
        if f.name in done:
            continue
        print(f"  {name}: applying {f.name}")
        query(db, f.read_text())
        query(db, "INSERT INTO d1_migrations (name) VALUES (?)", [f.name])


def rooms_namespace() -> str | None:
    for ns in api("GET", "/workers/durable_objects/namespaces"):
        if ns.get("script") == ROOMS_SCRIPT and ns.get("class") == ROOMS_CLASS:
            return ns["id"]
    print(f"  no {ROOMS_SCRIPT} Worker yet: deploy rooms/ first, then run this again to bind ROOMS")
    return None


def admin_key() -> str:
    if KEY_FILE.is_file():
        return KEY_FILE.read_text().strip()
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(24)
    KEY_FILE.touch(mode=0o600)
    KEY_FILE.write_text(key + "\n")
    print(f"  made a new admin key in {KEY_FILE}")
    return key


def turn_key() -> dict | None:
    if not TURN_FILE.is_file():
        url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}/calls/turn_keys"
        req = urllib.request.Request(url, data=json.dumps({"name": PROJECT}).encode(), method="POST", headers={
            "Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as r:
                made = json.load(r)["result"]
        except urllib.error.HTTPError as e:
            print(f"  no TURN key ({e.code}): the token may not make one. Make one in the Cloudflare dashboard"
                  f" (Realtime > TURN Server > Create) and write its id and token into {TURN_FILE}"
                  " as TURN_KEY_ID=… and TURN_KEY_TOKEN=…, then run this again")
            return None
        TURN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TURN_FILE.touch(mode=0o600)
        TURN_FILE.write_text(f"TURN_KEY_ID={made['uid']}\nTURN_KEY_TOKEN={made['key']}\n")
        print(f"  made a TURN key, saved in {TURN_FILE}")
    pairs = dict(line.split("=", 1) for line in TURN_FILE.read_text().split() if "=" in line)
    if not pairs.get("TURN_KEY_ID") or not pairs.get("TURN_KEY_TOKEN"):
        print(f"  {TURN_FILE} needs TURN_KEY_ID=… and TURN_KEY_TOKEN=…")
        return None
    return {k: {"type": "secret_text", "value": pairs[k]} for k in ("TURN_KEY_ID", "TURN_KEY_TOKEN")}


def vapid_key() -> dict | None:
    if not VAPID_FILE.is_file():
        print(f"  no {VAPID_FILE}: invites are not sent as notifications")
        return None
    pairs = dict(line.split("=", 1) for line in VAPID_FILE.read_text().split() if "=" in line)
    public = pairs.get("VAPID_PUBLIC_KEY", "")
    if not public or not pairs.get("VAPID_PRIVATE_KEY") or f"'{public}'" not in (ROOT / "server/api.js").read_text():
        print(f"  {VAPID_FILE} does not match VAPID_PUBLIC in server/api.js: invites are not sent as notifications")
        return None
    return {"VAPID_PRIVATE_KEY": {"type": "secret_text", "value": pairs["VAPID_PRIVATE_KEY"]}}


def main() -> int:
    for var in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not os.environ.get(var):
            sys.exit(f"set {var}")
    configs = {}
    key = admin_key()
    rooms = rooms_namespace()
    turn = turn_key()
    vapid = vapid_key()
    for env, name in DATABASES.items():
        db = database(name)
        print(f"{name}: {db}")
        migrate(db, name)
        configs[env] = {
            "d1_databases": {"DB": {"id": db}},
            "env_vars": {"ADMIN_KEY": {"type": "secret_text", "value": key}, **(turn or {}), **(vapid or {})},
        }
        if rooms:
            configs[env]["durable_object_namespaces"] = {"ROOMS": {"namespace_id": rooms}}
    api("PATCH", f"/pages/projects/{PROJECT}", {"deployment_configs": configs})
    bound = "DB, ADMIN_KEY" + (", TURN_KEY_*" if turn else "") + (", VAPID_PRIVATE_KEY" if vapid else "") + (" and ROOMS" if rooms else "")
    print(f"pages project {PROJECT}: {bound} bound (they apply from the next deploy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
