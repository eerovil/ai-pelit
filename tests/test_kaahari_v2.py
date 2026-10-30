"""Kaahari v2: racing friends in a room, and the race alone still as in v1."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaahari/v2/"


def test_alone_the_race_still_runs_and_saves_the_win(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    assert page.evaluate("[race.mode, race.karts.map(k => k.kind).join()]") == ["solo", "me,cpu,cpu,cpu,cpu,cpu"]
    page.evaluate("""() => {
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150 });
    }""")
    page.wait_for_function("race.phase === 'over'", timeout=6000)
    assert page.inner_text("#result") == "🏆 Voitit kisan!"
    assert page.evaluate("localStorage.getItem('ai-pelit:kaahari:taso')") == "2"


def room_of_two(site, browser, track=None):
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
    if track is not None:
        host.locator(".room-track").nth(track).click()
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    assert guest.inner_text("#aipr-extra") == "Huoneen tekijä valitsee radan."
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=8000)
    return host, guest


def finish(page):
    page.evaluate("""() => {
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150 });
    }""")


def test_two_phones_race_on_the_hosts_track_with_four_computer_drivers(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser, track=2)
    assert guest.evaluate("[T.name, race.karts.map(k => k.name).join()]") == [
        "Laavaluola", "Eero,Sinä,Kaasu-Kalle,Rengas-Riikka,Turbo-Tuomas,Mutka-Maija"]
    assert host.evaluate("race.karts.map(k => k.kind).join()") == "me,net,cpu,cpu,cpu,cpu"
    assert guest.evaluate("race.karts.map(k => k.kind).join()") == "net,me,net,net,net,net"
    # The computer's karts drive on the host and show on the guest.
    guest.wait_for_function("race.karts[2].prog > 150", timeout=5000)
    # The guest's own kart reaches the host.
    guest.wait_for_function("me.prog > 100", timeout=5000)
    host.wait_for_function("race.karts[1].prog > 100", timeout=3000)
    # Both finish, the guest first: both get the same results, and the room screen again.
    finish(guest)
    host.wait_for_function("race.karts[1].fin !== null", timeout=3000)
    finish(host)
    for p in (host, guest):
        p.wait_for_function("(!race || race.phase === 'over') && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert guest.inner_text("#aipr-result").startswith("🏆 Voitit kisan!")
    assert host.inner_text("#aipr-result").startswith("2. sija")
    note = guest.inner_text("#aipr-room")
    assert "1. Sinä" in note and "2. Eero" in note
    assert guest.evaluate("localStorage.getItem('ai-pelit:kaahari:kisat')") == "1"
    # A race in a room does not change the level of the race alone.
    assert guest.evaluate("localStorage.getItem('ai-pelit:kaahari:taso')") is None
    assert host.errors == [] and guest.errors == []


def test_a_bomb_thrown_on_one_phone_hits_the_kart_of_another(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    # Everyone else far behind; the guest's kart a little ahead of the host's, in its line.
    host.evaluate("race.karts.forEach(k => { if (k.kind === 'cpu') { const q = at(T, me.s - 400, 0); Object.assign(k, { x: q.x, y: q.y, idx: q.i, s: me.s - 400, v: 0 }); k.ai.turboT = 99; k.ai.itemT = 99; } })")
    guest.evaluate("() => { const h = race.karts[0], p = at(T, h.s + 120, h.lat); Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: h.s + 120, v: 20, shield: 0 }); }")
    host.wait_for_timeout(300)
    host.evaluate("me.item = 'pommi'; useItem()")
    guest.wait_for_function("race.bombs.length > 0 || me.spin > 0", timeout=2000)
    guest.wait_for_function("me.spin > 0", timeout=3000)
    # The bomb is gone on both phones.
    host.wait_for_function("race.bombs.length === 0", timeout=3000)


def test_a_guest_reloaded_mid_race_gets_its_kart_back(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    guest.wait_for_function("me.prog > 300", timeout=8000)
    guest.reload()
    guest.wait_for_function("race && race.phase === 'run' && me.prog > 250", timeout=8000)
    assert guest.evaluate("me.kind") == "me"


def test_a_kart_between_the_camera_and_mine_is_not_drawn_over_the_view(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("soloRace(0)")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    # How many shapes drawKart paints for another kart `d` units in front of the camera.
    paints = """d => {
        const o = race.karts[1];
        Object.assign(o, { x: cam.x + cam.fx * d, y: cam.y + cam.fy * d, a: me.a, z: 0 });
        let n = 0; const fill = x.fill;
        x.fill = function () { n++; return fill.apply(this, arguments); };
        try { drawKart(o); } finally { x.fill = fill; }
        return n;
    }"""
    assert page.evaluate(paints, 30) == 0
    assert page.evaluate(paints, 150) > 0


def test_the_host_first_then_a_second_round_on_another_track(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    finish(host)
    host.wait_for_function("me.fin !== null", timeout=3000)
    finish(guest)
    for p in (host, guest):
        p.wait_for_function("(!race || race.phase === 'over') && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert host.inner_text("#aipr-result").startswith("🏆 Voitit kisan!")
    assert guest.inner_text("#aipr-result").startswith("2. sija")
    # Again, on Laavaluola: a fresh race on both phones, counted once more.
    host.locator(".room-track").nth(2).click()
    host.click("#aipr-start")
    for p in (host, guest):
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run' && T.name === 'Laavaluola'", timeout=8000)
        assert p.evaluate("[me.fin, me.lap, race.karts.every(k => k.fin === null)]") == [None, 0, True]
    assert guest.evaluate("localStorage.getItem('ai-pelit:kaahari:kisat')") == "1"
    assert host.errors == [] and guest.errors == []
