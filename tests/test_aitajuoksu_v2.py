"""Aitajuoksu v2: a step before the gun is a false start, with a yellow and then a red card."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/aitajuoksu/v2/"


def set_position(site, context):
    """A race alone, "Valmiit…" called, the gun far off and no eager computer."""
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.click("#go")
    page.evaluate("race.gunAt = 99; race.cdT = 1.5; race.runners.forEach(r => { r.ai.jumpy = null; })")
    return page


def test_a_tap_on_your_marks_only_warns(site, context):
    page = set_position(site, context)
    page.evaluate("race.cdT = 0.3; press(1)")
    assert page.evaluate("[me.v, me.card, race.phase, warn > 0]") == [0, 0, "cd", True]


def test_a_first_false_start_is_a_yellow_card_and_the_start_again(site, context):
    page = set_position(site, context)
    page.evaluate("press(1)")
    assert page.evaluate("[me.card, race.phase, race.fs.card]") == [1, "false", 1]
    # More taps while the card shows do nothing more.
    page.evaluate("press(2); press(1)")
    assert page.evaluate("me.card") == 1
    page.wait_for_function("race.phase === 'cd' && race.cdT < 0.5", timeout=5000)
    assert page.evaluate("[me.card, me.v, race.fs]") == [1, 0, None]
    # The second start goes on to the gun as before.
    page.evaluate("race.runners.forEach(r => { r.ai.jumpy = null; })")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    page.evaluate("step(me, 1); step(me, 2)")
    assert page.evaluate("me.v") > 1
    assert page.errors == []


def test_a_second_false_start_is_a_red_card_and_out(site, context):
    page = set_position(site, context)
    page.evaluate("me.card = 1; press(1)")
    assert page.evaluate("[me.card, race.phase]") == [2, "false"]
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=6000)
    assert "hylätty" in page.inner_text("#result")
    # No race counted, no time saved.
    assert page.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:juoksut')") is None
    assert page.errors == []


def test_a_computer_runner_with_a_red_card_stays_out_and_comes_last(site, context):
    page = set_position(site, context)
    page.evaluate("const a = race.runners[0]; a.card = 1; a.ai.jumpy = 1.5")
    page.wait_for_function("race.phase === 'false'", timeout=3000)
    assert page.evaluate("[race.runners[0].card, race.fs.id]") == [2, "a"]
    page.wait_for_function("race.phase === 'cd'", timeout=5000)
    page.evaluate("race.gunAt = 1; race.runners.forEach(r => { r.ai.jumpy = null; })")
    page.wait_for_function("race.phase === 'run' && race.clock > 1", timeout=5000)
    assert page.evaluate("race.runners[0].x") == 0
    page.evaluate("race.runners.forEach(r => { if (r.card < 2) Object.assign(r, { x: 99.5, v: 9, down: 1023 }); })")
    page.wait_for_function("race.phase === 'done'", timeout=8000)
    res = page.evaluate("race.results")
    assert res[-1]["id"] == "a" and res[-1]["dq"] is True
    assert all(r["fin"] is not None for r in res[:-1])
    assert page.errors == []


def test_a_guest_false_start_reaches_the_host_and_the_red_card_ends_their_race(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two_at_set(site, browser)
    guest.evaluate("press(1)")
    host.wait_for_function("race.phase === 'false' && race.runners[1].card === 1", timeout=3000)
    guest.wait_for_function("race.phase === 'false' && me.card === 1 && race.fs.card === 1", timeout=3000)
    host.wait_for_function("race.phase === 'cd'", timeout=5000)
    host.evaluate("race.gunAt = 99; race.cdT = 1.5")
    guest.wait_for_function("race.phase === 'cd' && race.cdT > 1", timeout=3000)
    guest.evaluate("press(2)")
    host.wait_for_function("race.runners[1].card === 2", timeout=3000)
    guest.wait_for_function("me.card === 2", timeout=3000)
    # The host runs alone; the race ends when it finishes.
    host.wait_for_function("race.phase === 'cd'", timeout=5000)
    host.evaluate("race.gunAt = 0.1")
    host.wait_for_function("race.phase === 'run'", timeout=3000)
    host.evaluate("Object.assign(me, { x: 99.8, v: 9, down: 1023 })")
    for p in (host, guest):
        p.wait_for_function("AiPelitRooms.inRoom && !race && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert host.inner_text("#aipr-result").startswith("1. sija")
    assert "hylätty" in guest.inner_text("#aipr-result")
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()


def room_of_two_at_set(site, browser):
    """room_of_two at v2, stopped at "Valmiit…" before the gun."""
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
    host.wait_for_function("race && race.mode === 'net' && race.phase === 'cd'", timeout=6000)
    host.evaluate("race.gunAt = 99; race.cdT = 1.5")
    guest.wait_for_function("race && race.mode === 'net' && race.phase === 'cd' && race.cdT > 1", timeout=6000)
    return host, guest
