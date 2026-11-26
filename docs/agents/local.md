# Running it locally

Read before you serve the site on this host or show Eero a prototype on his phone.

Moved here unchanged from `AGENTS.md` (#558), which keeps a short form and links here. "Rule N" means the numbered rules in [rules.md](rules.md); a section named in quotes is listed in [AGENTS.md](../../AGENTS.md).

## Running it locally

    python3 scripts/build.py && python3 -m http.server -d _site 8000

The site is served from the root of its own name, and uses only relative links.

Check the port is free with `ss -ltnp`, serve the worktree's own `_site` by absolute path, and
rebuild after every source edit. Run Playwright scripts with `python3 -P`, not `-I`.

A prototype for Eero's phone is served with `python3 scripts/serve_prototype.py <port>`, never
plain `http.server` (#181): the service worker (`public/sw.js`) keeps a played version folder in
its own cache, so the phone never sees the next edit, and the phone cannot clear that cache.
The script answers `sw.js` with a worker that empties every cache, unregisters itself and
reloads the page (a 404 was not enough: Chrome kept the old worker), and sends
`Cache-Control: no-store`. On a phone that had the old worker, the first visit after this still
shows the cached copy; the page then reloads itself with the new one. It listens on 127.0.0.1 only, so give `tailscale serve` a
different port (`--https=8190 http://127.0.0.1:8191`): a server on all addresses takes the
tailnet's port itself, and the phone gets a TLS error.
`scripts/make_icons.py` redraws the app icons (needs Pillow); the PNGs are committed.
