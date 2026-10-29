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


def main() -> int:
    for var in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not os.environ.get(var):
            sys.exit(f"set {var}")
    configs = {}
    key = admin_key()
    rooms = rooms_namespace()
    for env, name in DATABASES.items():
        db = database(name)
        print(f"{name}: {db}")
        migrate(db, name)
        configs[env] = {
            "d1_databases": {"DB": {"id": db}},
            "env_vars": {"ADMIN_KEY": {"type": "secret_text", "value": key}},
        }
        if rooms:
            configs[env]["durable_object_namespaces"] = {"ROOMS": {"namespace_id": rooms}}
    api("PATCH", f"/pages/projects/{PROJECT}", {"deployment_configs": configs})
    bound = "DB, ADMIN_KEY and ROOMS" if rooms else "DB and ADMIN_KEY"
    print(f"pages project {PROJECT}: {bound} bound (they apply from the next deploy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
