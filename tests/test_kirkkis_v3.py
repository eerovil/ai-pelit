"""Kirkkis v3: the same game as v2, with its room on the shared library public/rooms.js (#57).

Each phone is its own Chromium context; `Relay` (from test_rooms_lib.py) plays the room on
Cloudflare. The library itself is tested there; here, the game's part of it.
"""

import json

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kirkkis/v3/"
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"
COUNT_PLUS_SEEK = 10 + 100 + 3
TALLY = "JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto') || '{}').kierrokset || 0"


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name, path=URL):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        if name:
            ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + path)
        return page

    phone.relay = relay
    yield phone
    for ctx in contexts:
        ctx.close()


def make_room(phone):
    host = phone("Eero")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    return host, host.evaluate("AiPelitRooms.code")


def join(phone, name, code):
    page = phone(name)
    page.click("#multi")
    page.fill("#aipr-codeIn", code.lower())
    page.click("#aipr-joinBtn")
    page.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length > 1")
    return page


def start(host, guests, host_seeks=False):
    if host_seeks:
        host.evaluate("nextSeeker = { id: AiPelitRooms.me }")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {1 + len(guests)}")
    host.click("#aipr-start")
    for g in guests:
        g.wait_for_function("phase === 'count' && people.length === 5")
    # Everyone hides at once (far apart, out of the seeker's way), then most of the count is skipped.
    for i, g in enumerate(guests):
        if g.evaluate("seeker !== player"):
            g.evaluate(f"() => {{ const s = SPOTS.filter(s => dist(s, BASE) > 12)[{i} * 9]; player.x = s.x; player.y = s.y; }}")
            me = json.dumps(g.evaluate("AiPelitRooms.me"))
            host.wait_for_function(f"dist(people.find(p => p.id === {me}), BASE) > 12")
    host.evaluate("""() => { for (const b of bots) if (b !== seeker) { b.x = b.spot.x; b.y = b.spot.y; b.path = []; }
      if (seeker !== player) { const s = SPOTS.filter(s => dist(s, BASE) > 12).at(-1); player.x = s.x; player.y = s.y; } }""")
    host.evaluate("timer = 0.2")
    host.wait_for_function("phase === 'seek'")
    for g in guests:
        g.wait_for_function("phase === 'seek'")


def in_room_with_result(page):
    page.wait_for_function("phase === 'room' && document.getElementById('aipr-result').textContent !== ''", timeout=12000)


def test_alone_it_plays_as_before_and_keeps_the_saves(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("localStorage.setItem('ai-pelit:kirkkis:tilasto', JSON.stringify({ kierrokset: 3, pelastuit: 2, kirkattiin: 1, kirkkasit: 4 }))")
    page.goto(site.url + URL)
    assert page.locator("#total").inner_text() == "Kierroksia 3 · pelastuit 2 · kirkkasit 4"
    results = page.evaluate("""() => { const out = [];
      for (let r = 0; r < 4; r++) {
        newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
        while (phase !== 'menu' && t < 130) { step(1 / 30); t += 1 / 30; }
        out.push({ t, menu: phase === 'menu', next: nextSeeker.name, first: firstCaught ? firstCaught.name : null, seeker: seeker.name, n: people.length });
      } return out; }""")
    for r in results:
        assert r["menu"] and r["t"] < COUNT_PLUS_SEEK and r["n"] == 5
        assert r["next"] == (r["first"] or r["seeker"])
    assert page.evaluate(TALLY) == 7
    # The hider who reaches the base first is saved, and hears it.
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    page.evaluate("seeker.x = 26; seeker.y = 42; seeker.goal = { x: 26, y: 43 }; seeker.path = []")
    page.evaluate("player.x = 15; player.y = 20.9; step(1 / 30)")
    assert page.evaluate("[player.st, msg]") == ["saved", "Pelastuit! 🎉"]
    assert page.locator("#aipr").count() == 0  # the room screen is drawn only once it is opened
    assert errors == []


def test_each_phone_sees_its_own_view_and_the_host_runs_the_rules(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    host.wait_for_function("AiPelitRooms.members.length === 2")
    assert host.locator("#aipr-info").inner_text() == "2 pelaajaa. Tyhjät paikat täyttävät tietokonepelaajat."
    start(host, [guest], host_seeks=True)
    # Same cast on both phones: two people and three computer players.
    names = "people.map(p => p.name)"
    assert host.evaluate(names) == guest.evaluate(names) == ["Eero", "Aino", "Eetu", "Iida", "Onni"]
    assert guest.evaluate("[seeker.name, player.name, player.role]") == ["Eero", "Aino", "hider"]
    # The guest's finger moves the guest; the host sees the guest arrive where they went.
    guest.evaluate("player.x = 15; player.y = 31; player.a = 0")
    host.wait_for_function("Math.abs(people[1].x - 15) < 0.05 && Math.abs(people[1].y - 31) < 0.05")
    # The host looks at the guest, standing in the open: the guest is seen, and hears it.
    host.evaluate("""() => { player.x = 15; player.y = 26; player.a = Math.PI / 2;
      for (const b of bots) { b.x = 2.5; b.y = 24; b.goal = b.spot = { x: 2.5, y: 24 }; b.path = []; b.brave = 999; } }""")
    guest.wait_for_function("player.st === 'spotted' && msg === 'Sinut nähtiin! Juokse pesään!'")
    assert host.evaluate("msg") == "Näit Ainon! Pesään!"
    # Each phone draws only what its own player sees: the guest does not see the far bots.
    guest.wait_for_function("Math.hypot(people[2].x - 2.5, people[2].y - 24) < 0.3")
    assert guest.evaluate("canSee(player, people[2])") is False
    # The host reaches the base first: the guest is caught on both phones.
    host.evaluate("player.x = 15; player.y = 23")
    guest.wait_for_function("player.st === 'caught' && msg === 'Sinut kirkattiin! 😱'")
    # The round plays out; both phones go back to the room, each with its own result and tally.
    host.evaluate("timer = 0.1")
    in_room_with_result(host)
    in_room_with_result(guest)
    assert guest.locator("#aipr-result").inner_text() == "Sinut kirkattiin!"
    assert host.locator("#aipr-result").inner_text().startswith("Kirkkasit ")
    assert guest.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))")["kirkattiin"] == 1
    assert host.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))")["kirkkasit"] >= 1
    # The first one caught seeks next, and everyone is told.
    assert host.locator("#aipr-info").inner_text().endswith("Seuraavaksi etsii Aino.")
    assert guest.locator("#aipr-info").inner_text().endswith("Seuraavaksi etsii sinä.")
    assert host.locator("#aipr-start").inner_text() == "Uusi kierros"
    host.click("#aipr-start")
    guest.wait_for_function("phase === 'count' && seeker === player")
    assert host.errors == guest.errors == []


def test_a_phone_reloaded_mid_round_gets_the_round_back(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest], host_seeks=True)
    where = host.evaluate("[r2(people[1].x), r2(people[1].y)]")
    guest.reload()
    guest.wait_for_function("phase === 'seek' && player.name === 'Aino' && seeker.name === 'Eero'", timeout=8000)
    assert guest.evaluate("[r2(player.x), r2(player.y)]") == where
    assert host.evaluate("people[1].ctrl") == "remote"
    # It moves again, and the host sees it.
    guest.evaluate("player.x = 15; player.y = 31")
    host.wait_for_function("Math.abs(people[1].y - 31) < 0.05")
    assert host.errors == guest.errors == []


def test_the_round_waits_for_a_phone_that_drops_off_and_the_computer_can_take_over(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest])
    phones.relay.drop(guest)
    host.wait_for_function("document.getElementById('aipr-pauseText').textContent === '⏸ Odotetaan: Aino'")
    held = host.evaluate("timer")
    host.wait_for_timeout(600)
    assert host.evaluate("timer") == held
    # Back again: the round goes on where it was.
    phones.relay.back(guest)
    host.wait_for_function("!AiPelitRooms.paused && timer < " + str(held), timeout=8000)
    guest.wait_for_function("AiPelitRooms.connected && phase === 'seek' && !AiPelitRooms.paused")
    # Dropped again, and the host goes on without them: a computer player takes over.
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("people[1].ctrl === 'bot' && timer < " + str(host.evaluate("timer")))
    # When the phone comes back, it takes its player back.
    phones.relay.back(guest)
    host.wait_for_function("people[1].ctrl === 'remote'", timeout=8000)
    guest.wait_for_function("phase === 'seek' && AiPelitRooms.connected")
    assert host.errors == guest.errors == []


def test_a_phone_away_when_the_round_ends_gets_its_result_once(phones):
    host, code = make_room(phones)
    guest = join(phones, "Aino", code)
    start(host, [guest], host_seeks=True)
    phones.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.evaluate("timer = 0.1")
    in_room_with_result(host)
    # Back after the round ended: the guest gets the finished round, and saves its result.
    phones.relay.back(guest)
    in_room_with_result(guest)
    assert guest.evaluate(TALLY) == 1
    assert guest.locator("#aipr-result").inner_text() in ("Pelastuit! 🎉", "Sinut kirkattiin!")
    # A reload hears nothing new and saves nothing twice.
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.connected", timeout=10000)
    guest.wait_for_timeout(500)
    assert guest.evaluate(TALLY) == 1
    # The next round still has the guest in it.
    host.click("#aipr-start")
    guest.wait_for_function("phase === 'count' && people.length === 5", timeout=8000)
    assert host.errors == guest.errors == []


def test_a_kirkkis_v2_room_is_refused(phones):
    # A v2 page makes its own room, which names no game.
    old = phones(None, "games/kirkkis/v2/")
    old.click("#multi")
    old.click("#create")
    old.wait_for_function("net.joined")
    code = old.evaluate("net.code")
    page = phones("Aino")
    page.click("#multi")
    page.fill("#aipr-codeIn", code)
    page.click("#aipr-joinBtn")
    page.wait_for_function("!AiPelitRooms.inRoom && document.getElementById('aipr-err').textContent === 'Huone on toisessa pelissä.'")
    assert page.errors == []


def test_five_phones_fill_the_cast(phones):
    host, code = make_room(phones)
    guests = [join(phones, n, code) for n in ["Aino", "Eetu", "Iida", "Onni"]]
    host.wait_for_function("AiPelitRooms.members.length === 5")
    assert host.locator("#aipr-info").inner_text() == "5 pelaajaa – huone on täynnä."
    start(host, guests)
    assert host.evaluate("[people.length, bots.length]") == [5, 0]
    for g in guests:
        assert g.evaluate("people.filter(p => p.isPlayer).length") == 1
    assert host.errors == [] and all(g.errors == [] for g in guests)
