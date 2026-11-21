"""Kirkkis v12 (#480): a friend running across the yard glides on the other phones' screens, drawn from lib/sulava-1
between the spots their phone sends, instead of jumping to each one as it comes (on the host, v11) or chasing it
(on a guest). The host's rules still use the newest spot; only the drawing lags."""

import json
import shutil
from statistics import mean, pstdev

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kirkkis/v12/"

# A phone network: each message leaves 0-90 ms late, in order, as on a busy mobile connection.
JITTER = """() => { const send = AiPelitRooms.send.bind(AiPelitRooms); let free = 0, seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  AiPelitRooms.send = (m, to) => { const now = performance.now(), at = Math.max(free, now + rnd() * 90); free = at;
    setTimeout(() => send(m, to), at - now); }; }"""
# Records, each time the screen is drawn, where person `i` is drawn, and when a message arrived (so a stall of the
# test machine, with no message for a while, can be told from a jerk).
SAMPLE = """(i) => { window.__xs = []; window.__got = [];
  AiPelitRooms.on('message', () => window.__got.push(performance.now() / 1000));
  const d = window.draw;
  window.draw = () => { if (window.__xs.length < 300) window.__xs.push([performance.now() / 1000, people[i].x, people[i].y]); d(); }; }"""


def phones(site, browser, seeker, names=("Eero", "Aino")):
    """Phones in a room, computer players up to five; `seeker` (0 the host, 1 the first guest) counts first."""
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
    site.build()
    relay, pages = Relay(), []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                                  service_workers="block")
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.click("#multi")
        pages.append(page)
    host, guests = pages[0], pages[1:]
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    for g in guests:
        g.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
        g.click("#aipr-joinBtn")
        g.wait_for_function("AiPelitRooms.inRoom")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(pages)}")
    # The host picks the first seeker among the phones at random: make it the one asked for.
    host.evaluate(f"window.__rnd = Math.random; Math.random = () => {0.01 if seeker == 0 else 0.99}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("people.length === 5 && phase === 'count'")
    host.evaluate("Math.random = window.__rnd")
    assert host.evaluate("people.indexOf(seeker)") == seeker
    return pages


def glides(page):
    """The speed over each two drawn frames while the friend ran: always forward and about the same."""
    xs, got = page.evaluate("[window.__xs, window.__got]")
    sp = [(t2, ((c - a) ** 2 + (d - b) ** 2) ** 0.5 / (t2 - t0))
          for (t0, a, b), (t2, c, d) in zip(xs, xs[2:]) if t2 > t0]
    moving = [i for i, (_, v) in enumerate(sp) if v > 0.01]
    assert len(moving) > 60, len(moving)
    middle = sp[moving[0] + 8:moving[-1] - 8]

    def heard(t):
        return any(t - 0.3 <= g <= t for g in got)
    kept = [v for t, v in middle if heard(t)]
    shown = [round(v, 2) for _, v in middle]
    assert len(kept) > 0.8 * len(middle), (len(kept), len(middle))
    assert min(kept) > 0.3, shown
    m, sd = mean(kept), pstdev(kept)
    assert sd < 0.25 * m, (sd, m, shown)
    assert max(kept) < 2 * m, (max(kept), m, shown)


# A guest runs, seen on the host (whose rules keep the newest spot and whose screen draws it smoothly),
# and the host runs, seen on a guest (which in v11 chased the newest spot).
@pytest.mark.parametrize("walker", ["guest", "host"])
def test_a_friend_running_glides_on_the_other_phone(site, browser, walker):
    host, guest = phones(site, browser, seeker=0 if walker == "guest" else 1)
    run_and_watch(host, *((guest, host) if walker == "guest" else (host, guest)), others=[guest])


def test_a_friend_running_glides_on_a_third_phone_too(site, browser):
    """The host forwards a friend's spots with the friend's own clock, so a third phone draws them as smoothly."""
    host, aino, ville = phones(site, browser, seeker=0, names=("Eero", "Aino", "Ville"))
    host.evaluate(JITTER)
    run_and_watch(host, aino, ville, others=[aino, ville])


def run_and_watch(host, run, watch, others):
    me = run.evaluate("people.indexOf(player)")
    run.evaluate(JITTER)
    # Out in the open, running straight along the yard at three quarters of full speed (no sprint).
    run.evaluate("Object.assign(player, { x: 1, y: 11 })")
    watch.wait_for_function(f"Math.abs(people[{me}].x - 1) < 0.05 && Math.abs(people[{me}].y - 11) < 0.05", timeout=5000)
    watch.evaluate(SAMPLE, me)
    run.evaluate("joy = { id: -1, ox: 100, oy: 100, x: 140, y: 100 }")
    watch.wait_for_function("window.__xs.length >= 200", timeout=20000)
    run.evaluate("letGo()")
    assert run.evaluate("player.x") > 8  # it really ran, not into a wall
    glides(watch)
    # The host's rules know the friend where their phone last said, not where its screen draws them.
    if run is not host:
        x = run.evaluate("player.x")
        host.wait_for_function(f"Math.abs(people[{me}].x - {x}) < 0.05")
    errors = [e for p in (host, *others) for e in p.errors]
    assert not errors, errors
