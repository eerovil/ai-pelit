"""Kirkkis v4: the real calls ("Ainon nimet!", "Omat nimet!") and "Kaikki pelastettu!" (#67).

Alone through the game's own step(); with friends through test_kirkkis_v3's room helpers.
"""

import json

import pytest

from conftest import ROOT
from test_kirkkis_v3 import in_room_with_result, join, start
from test_rooms_lib import Relay

URL = "games/kirkkis/v4/"
RUN = "s => { for (let i = 0; i < s * 30; i++) step(1 / 30); }"
STATS = "JSON.parse(localStorage.getItem('ai-pelit:kirkkis:tilasto'))"


def open_game(site, context, init=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if init:
        page.add_init_script(init)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


# The player hides behind the house, the count runs out, and one computer hider is put in the open
# below the base, looking away from it, where the seeker (at the base, facing it) sees them.
SEEN_HIDER = """() => { const o = bots.find(b => b !== seeker); o.x = 15; o.y = 26; o.left = true; o.goal = o.spot = { x: 15, y: 26 };
  o.path = []; o.brave = 999; seeker.x = 15; seeker.y = 24; seeker.a = Math.PI / 2; seeker.goal = BASE; seeker.path = [];
  for (const b of bots) if (b !== seeker && b !== o) { b.x = 2.5; b.y = 24; b.goal = b.spot = { x: 2.5, y: 24 }; b.path = []; b.brave = 999; }
  return people.indexOf(o); }"""


def test_old_saves_read_with_the_new_words(site, context):
    page = open_game(site, context, "localStorage.setItem('ai-pelit:kirkkis:tilasto', JSON.stringify({ kierrokset: 3, pelastuit: 2, kirkattiin: 1, kirkkasit: 4 }))")
    assert page.locator("#total").inner_text() == "Kierroksia 3 · pelastuit 2 · nimesit 4"
    assert "”Omat nimet!”" in page.locator(".help").inner_text()
    assert page.evaluate("SEEK_TIME") == 200
    assert page.errors == []


def test_the_seeker_calls_the_names_and_a_hider_who_gets_there_first_calls_omat_nimet(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    i = page.evaluate(SEEN_HIDER)
    page.evaluate("step(1 / 30)")
    assert page.evaluate(f"people[{i}].st") == "spotted"
    # The seeker reaches the base: "Ainon nimet!".
    page.evaluate("seeker.x = 15; seeker.y = 23; step(1 / 30)")
    name = page.evaluate(f"people[{i}].name")
    assert page.evaluate(f"[people[{i}].st, seeker.bubble]") == ["caught", f"{name}n nimet!"]
    # Two called at once: "Ainon nimet, Eetun nimet!", and the player is "Sinun nimet".
    page.evaluate("show(['kirk', [people.indexOf(player), 2]])")
    assert page.evaluate("[seeker.bubble, msg]") == [f"Sinun nimet, {page.evaluate('gen(people[2].name)')} nimet!", "Sinut nimettiin! 😱"]
    assert page.errors == []


def test_omat_nimet_after_someone_is_named_is_kaikki_pelastettu(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    i = page.evaluate(SEEN_HIDER)
    page.evaluate("step(1 / 30); seeker.x = 15; seeker.y = 23; step(1 / 30)")
    assert page.evaluate(f"[people[{i}].st, firstCaught === people[{i}]]") == ["caught", True]
    # A third hider is saved first, so the saved ones hide again too.
    page.evaluate("const o = hiders().find(h => h !== player && h.st === 'hiding'); o.st = 'saved'")
    # The seeker wanders off; the player runs to the base.
    page.evaluate("seeker.x = 26; seeker.y = 42; seeker.goal = { x: 26, y: 43 }; seeker.path = []")
    left = page.evaluate("timer")
    page.evaluate("player.x = 15; player.y = 20.9; step(1 / 30)")
    r = page.evaluate("""() => ({ phase, timer, seekLeft, seeker: seeker.st, at: dist(seeker, BASE), first: firstCaught,
      sts: hiders().map(h => h.st), left: hiders().some(h => h.left), bubble: player.bubble, msg })""")
    assert r["phase"] == "count" and abs(r["timer"] - 10) < 0.2 and r["seeker"] == "count" and r["at"] < 1.2
    assert abs(r["seekLeft"] - left) < 0.1 and r["first"] is None
    assert r["sts"] == ["hiding"] * 4 and not r["left"]
    assert r["bubble"] == "Omat nimet! Kaikki pelastettu!" and r["msg"] == "Kaikki pelastettu! Piiloudu!"
    # The seek clock goes on through the count, and the seeking starts where it left off.
    page.evaluate("player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    assert page.evaluate("[phase, seekLeft, seeker.st]") == ["seek", None, "seek"]
    assert abs(page.evaluate("timer") - (left - 10.1)) < 0.2
    # The computer hiders went to new places.
    assert page.evaluate("bots.filter(b => b !== seeker).every(b => dist(b, BASE) > 5)")
    assert page.errors == []


def test_a_hider_with_nobody_named_is_only_saved(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('hide'); player.x = 6; player.y = 0.6")
    page.evaluate(RUN, 10.1)
    page.evaluate("seeker.x = 26; seeker.y = 42; seeker.goal = { x: 26, y: 43 }; seeker.path = []")
    page.evaluate("player.x = 15; player.y = 20.9; step(1 / 30)")
    assert page.evaluate("[phase, player.st, player.bubble, msg]") == ["seek", "saved", "Omat nimet!", "Pelastuit! 🎉"]
    assert page.errors == []


def test_the_time_running_out_during_the_recount_saves_everyone_out(site, context):
    page = open_game(site, context)
    page.evaluate("newRound('seek')")
    page.evaluate(RUN, 10.1)
    page.evaluate("const h = hiders(); h[0].st = 'caught'; h[1].left = true; h[1].x = 15; h[1].y = 20.9; timer = 3; step(1 / 30)")
    assert page.evaluate("[phase, seeker === player, msg]") == ["count", True, "Kaikki pelastettu! 😮"]
    page.evaluate(RUN, 4)
    assert page.evaluate("phase") in ("end", "menu")
    assert page.evaluate("hiders().every(h => h.st === 'saved')")
    assert page.evaluate(STATS)["kirkkasit"] == 0
    assert page.errors == []


def test_rounds_against_the_computer_end_and_the_first_caught_seeks_next(site, context):
    page = open_game(site, context)
    results = page.evaluate("""() => { const out = [];
      for (let r = 0; r < 4; r++) {
        newRound(r % 2 ? 'seek' : 'hide'); let t = 0;
        while (phase !== 'menu' && t < 240) { step(1 / 30); t += 1 / 30; }
        out.push({ t, menu: phase === 'menu', next: nextSeeker.name, first: firstCaught ? firstCaught.name : null, seeker: seeker.name });
      } return out; }""")
    for r in results:
        assert r["menu"] and r["t"] < 10 + 200 + 10 + 3
        assert r["next"] == (r["first"] or r["seeker"])
    assert page.errors == []


@pytest.fixture
def phones(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        return page

    yield phone
    for ctx in contexts:
        ctx.close()


def test_with_friends_kaikki_pelastettu_reaches_every_phone(phones):
    host = phones("Eero")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    guest = join(phones, "Aino", host.evaluate("AiPelitRooms.code"))
    # The guest seeks.
    host.evaluate(f"nextSeeker = {{ id: {json.dumps(guest.evaluate('AiPelitRooms.me'))} }}")
    start(host, [guest])
    assert guest.evaluate("seeker === player")
    # One computer hider has been named, and another one gets to the base.
    host.evaluate("""() => { const [a, b] = bots; a.st = 'caught'; b.left = true; b.x = 15; b.y = 20.9; b.path = []; b.goal = BASE; }""")
    guest.wait_for_function("phase === 'count' && seekLeft !== null && msg === 'Kaikki pelastettu! 😮'")
    assert guest.evaluate("dist(player, BASE)") < 1.2
    host.wait_for_function("phase === 'count' && hiders().every(h => h.st === 'hiding')")
    assert host.evaluate("msg") == "Kaikki pelastettu! Piiloudu!"
    # The count runs out on the host; seeking goes on with the clock where it was.
    left = host.evaluate("seekLeft")
    host.evaluate("timer = 0.1")
    guest.wait_for_function("phase === 'seek' && seekLeft === null")
    assert host.evaluate("timer") < left
    host.evaluate("timer = 0.1")
    in_room_with_result(host)
    in_room_with_result(guest)
    # Whoever the seeker called after the recount counts; the named one before it was freed.
    assert guest.locator("#aipr-result").inner_text() in ("Kaikki pelastuivat!", "Nimesit 1/4!", "Nimesit 2/4!")
    assert host.errors == guest.errors == []
