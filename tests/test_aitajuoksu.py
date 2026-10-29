"""Aitajuoksu in a phone-sized Chromium, alone and in a room of two phones."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/aitajuoksu/v1/"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    page.wait_for_function("race && race.phase === 'run'", timeout=5000)
    return page


def test_taps_on_alternate_feet_run_and_the_same_foot_does_not(site, context):
    page = start(site, context)
    page.evaluate("step(me, 1); step(me, 2); step(me, 1)")
    fast = page.evaluate("me.v")
    assert fast > 2.5
    page.evaluate("me.v = 0; me.foot = 1; step(me, 1); step(me, 1)")
    assert page.evaluate("me.v") == 0


def test_a_tap_before_the_gun_does_nothing(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("soloRace(); race.gunAt = 99; race.cdT = 1.5")
    page.evaluate("press(1); press(2); press(1)")
    assert page.evaluate("[me.v, race.phase, warn > 0]") == [0, "cd", True]


def test_a_jump_clears_a_hurdle_and_running_into_one_knocks_it_down(site, context):
    page = start(site, context)
    # Jumped in time: over it, still at speed.
    page.evaluate("Object.assign(me, { x: 11.2, v: 8, y: 0, vy: 0 }); jump(me)")
    page.wait_for_function("me.x > 14 && me.y === 0", timeout=3000)
    assert page.evaluate("[me.hits, me.down]") == [0, 0]
    # No jump: down it goes, and so does the speed.
    page.evaluate("Object.assign(me, { x: 20.5, v: 8, y: 0, vy: 0 })")
    page.wait_for_function("me.hits === 1", timeout=3000)
    assert page.evaluate("[me.down, me.v < 4.5]") == [2, True]


def test_the_finish_ends_the_race_and_a_win_raises_the_level(site, context):
    page = start(site, context)
    page.evaluate("race.runners.forEach(r => { if (r !== me) r.rate = 1; }); Object.assign(me, { x: 99.5, v: 9, down: 1023 })")
    page.wait_for_function("me.fin !== null", timeout=2000)
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=12000)
    assert page.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:taso')") == "2"
    assert page.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:voitot')") == "1"
    assert page.inner_text("#result").startswith("Voitit!")
    page.reload()
    assert "Taso 2" in page.inner_text("#foe")
    assert "Ennätys" in page.inner_text("#stats")


def test_the_computer_runs_the_whole_race(site, context):
    page = start(site, context)
    page.evaluate("Object.assign(me, { x: 101, fin: 99 })")  # out of the way
    page.wait_for_function("race.runners.filter(r => r !== me).every(r => r.x > 30)", timeout=8000)
    # The computer jumps most hurdles: three on the way, at most one down each.
    assert page.evaluate("race.runners.filter(r => r !== me).map(r => r.hits).every(h => h <= 2)")


def room_of_two(site, browser):
    """Eero's phone makes a room, Aino's joins it, and the race is on."""
    relay = Relay()
    pages = []
    for name in ["Eero", "Aino"]:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host, guest = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=6000)
    return host, guest


def test_two_phones_race_and_both_get_the_results(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    pages = [host, guest]
    assert guest.evaluate("race.runners.map(r => r.name)") == ["Eero", "Aino"]
    # The guest's own steps reach the host.
    guest.evaluate("step(me, 1); step(me, 2); Object.assign(me, { x: 40 })")
    host.wait_for_function("race.runners[1].x >= 40", timeout=3000)
    # A reload mid-race gives the guest its runner back where it was.
    guest.reload()
    guest.wait_for_function("race && race.phase === 'run' && me.x >= 40", timeout=8000)
    # The guest finishes first, then the host.
    guest.evaluate("Object.assign(me, { x: 99.8, v: 9, down: 1023 })")
    host.wait_for_function("race.runners[1].fin !== null", timeout=3000)
    host.evaluate("Object.assign(me, { x: 99.8, v: 9, down: 1023 })")
    # The results name everyone, each phone itself as "Sinä".
    guest.wait_for_function("race && race.phase === 'done'", timeout=5000)
    assert guest.evaluate("race.results.map(r => r.name)") == ["Aino", "Eero"]
    for p in pages:
        p.wait_for_function("AiPelitRooms.inRoom && !race && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert guest.inner_text("#aipr-result").startswith("1. sija")
    assert host.inner_text("#aipr-result").startswith("2. sija")
    assert "1. Aino" in host.inner_text("#aipr")
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()


def test_a_guest_in_first_ends_the_race_for_a_host_that_stopped(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    host.evaluate("race.late = 1")
    guest.evaluate("Object.assign(me, { x: 99.8, v: 9, down: 1023 })")
    # The host never runs; the race ends a second after the guest's finish.
    for p in (host, guest):
        p.wait_for_function("AiPelitRooms.inRoom && !race && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert guest.inner_text("#aipr-result").startswith("1. sija")
    assert host.inner_text("#aipr-result") == "Et ehtinyt maaliin"
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()
