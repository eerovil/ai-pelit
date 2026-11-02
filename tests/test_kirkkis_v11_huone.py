"""Kirkkis v10: up to eight phones play one round in the same room (#370; up to v9 five)."""

import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kirkkis/v11/"
NAMES = ["Eero", "Aino", "Eetu", "Iida", "Onni", "Venla", "Kalle", "Saara"]


# Eight phones, the most a room takes; three, where computer players fill the round up to five.
@pytest.mark.parametrize("count", [8, 3])
def test_phones_play_one_round(site, browser, count):
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
    site.build()
    relay, contexts, pages = Relay(), [], []
    try:
        for name in NAMES[:count]:
            ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True,
                                      service_workers="block")
            contexts.append(ctx)
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
        code = host.evaluate("AiPelitRooms.code")
        for g in guests:
            g.fill("#aipr-codeIn", code.lower())
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {count}")
        if count == 8:
            assert host.locator("#aipr-info").inner_text() == "8 pelaajaa – huone on täynnä."
        size = max(count, 5)
        host.click("#aipr-start")
        for name, p in zip(NAMES, pages):
            p.wait_for_function(f"people.length === {size} && (phase === 'count' || phase === 'seek')")
            cast = p.evaluate("people.map(q => [q.name, q.color, !q.id])")
            # Every phone is in the round as itself, computer players only up to five, each its own colour.
            assert sorted(n for n, _, bot in cast if not bot) == sorted(NAMES[:count])
            assert sum(bot for _, _, bot in cast) == size - count
            assert len({c for _, c, _ in cast}) == size
            assert p.evaluate("player.name") == name
        # With no computer players nobody moves, so once the counting ends the seeker names everyone
        # at the base and the round ends with a result on every phone. Computer hiders run off and
        # hide, so there the seeking starts on every phone.
        for p in pages:
            p.wait_for_function("played && lastRes[0]" if count == 8 else "played || phase === 'seek'", timeout=20000)
        for p in pages:
            assert p.errors == []
    finally:
        for ctx in contexts:
            ctx.close()
