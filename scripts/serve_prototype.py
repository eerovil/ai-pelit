#!/usr/bin/env python3
"""Serve the built site for a prototype on Eero's phone, with no caching (#181).

    python3 scripts/build.py && python3 scripts/serve_prototype.py [port]

The site's service worker (public/sw.js) serves a version folder from its own cache once it
has been played, so a phone never sees the next edit of a prototype, and a phone cannot clear
it easily. This server answers sw.js with a worker that deletes every cache, unregisters itself
and reloads the open pages (a 404 was not enough: Chrome kept serving the old worker's cache),
and tells the browser to keep nothing. It listens on 127.0.0.1 only: put it on
the tailnet with `tailscale serve --bg --https=<other port> http://127.0.0.1:<port>`.
"""

import functools
import http.server
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "_site"


# The browser checks sw.js for an update on each visit; this new one takes over at once, empties
# every cache, leaves, and reloads the open pages, which from then on come from this server.
KILL_SWITCH = b"""self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil((async () => {
  for (const k of await caches.keys()) await caches.delete(k);
  await self.registration.unregister();
  for (const c of await self.clients.matchAll({ type: 'window' })) c.navigate(c.url);
})()));
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0].endswith("/sw.js"):
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(KILL_SWITCH)))
            self.end_headers()
            self.wfile.write(KILL_SWITCH)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8191
    handler = functools.partial(Handler, directory=str(SITE))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"serve_prototype: {SITE} on http://127.0.0.1:{port}/ (a self-removing service worker, no cache)")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
