"""Kirkkis v10: eight phones play one round in the same room (#370; up to v9 five)."""

import json
import shutil

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kirkkis/v10/"
NAMES = ["Eero", "Aino", "Eetu", "Iida", "Onni", "Venla", "Kalle", "Saara"]


def test_eight_phones_play_one_round(site, browser):
    shutil.copytree(ROOT / "games" / "kirkkis", site.games / "kirkkis", dirs_exist_ok=True)
    site.build()
    relay, contexts, pages = Relay(), [], []
    try:
        for name in NAMES:
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
        host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 8")
        assert host.locator("#aipr-info").inner_text() == "8 pelaajaa – huone on täynnä."
        host.click("#aipr-start")
        for name, p in zip(NAMES, pages):
            p.wait_for_function("people.length === 8 && (phase === 'count' || phase === 'seek')")
            cast = p.evaluate("people.map(q => [q.name, q.color])")
            # Every phone is in the round as itself: no computer player, eight colours.
            assert sorted(n for n, _ in cast) == sorted(NAMES)
            assert len({c for _, c in cast}) == 8
            assert p.evaluate("player.name") == name
        # Nobody moves, so once the counting ends the seeker names everyone at the base, and the
        # round ends with a result on every phone.
        for p in pages:
            p.wait_for_function("played && lastRes[0]", timeout=20000)
        for p in pages:
            assert p.errors == []
    finally:
        for ctx in contexts:
            ctx.close()
