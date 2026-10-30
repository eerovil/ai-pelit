"""Aitajuoksu v3: 100, 200 or 400 m, with or without hurdles, each with its own record."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/aitajuoksu/v3/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


def run(page):
    """Start a race from the menu and have the gun go at once, with no eager computer."""
    page.click("#go")
    page.evaluate("race.gunAt = 0.05; race.runners.forEach(r => { r.ai.jumpy = null; })")
    page.wait_for_function("race.phase === 'run'", timeout=3000)


def test_the_menu_picks_the_distance_and_hurdles_and_keeps_them(site, context):
    page = open_game(site, context)
    assert page.evaluate("[dist, hurdles, TRACK, H_N]") == [100, True, 100, 10]
    page.click("#dists [data-d='400']")
    page.click("#hurd [data-h='0']")
    assert page.evaluate("document.querySelector('#dists .on').textContent") == "400 m"
    assert page.evaluate("document.querySelector('#hurd .on').textContent") == "Ilman aitoja"
    page.reload()
    assert page.evaluate("[dist, hurdles]") == [400, False]
    run(page)
    assert page.evaluate("[TRACK, H_N, race.dist, race.hurdles, race.late]") == [400, 0, 400, False, 80]
    assert page.errors == []


def test_longer_hurdle_races_space_their_hurdles(site, context):
    page = open_game(site, context)
    page.click("#dists [data-d='200']")
    run(page)
    assert page.evaluate("HURDLES") == [16 + 19 * i for i in range(10)]
    page.evaluate("race = null; showMenu()")
    page.click("#dists [data-d='400']")
    run(page)
    assert page.evaluate("HURDLES") == [45 + 35 * i for i in range(10)]


def test_without_hurdles_nothing_knocks_and_the_computer_never_jumps(site, context):
    page = open_game(site, context)
    page.click("#hurd [data-h='0']")
    run(page)
    page.evaluate("Object.assign(me, { x: 11, v: 9 })")
    page.wait_for_function("race.runners.filter(r => r !== me).every(r => r.x > 20)", timeout=8000)
    assert page.evaluate("race.runners.every(r => r.hits === 0 && r.y === 0)")


def test_each_race_keeps_its_own_record_and_list(site, context):
    page = open_game(site, context)
    # v1-v2's 100 m hurdles record carries on.
    page.evaluate("localStorage.setItem('ai-pelit:aitajuoksu:ennatys', '15.5')")
    page.reload()
    assert "15,50" in page.inner_text("#stats")
    page.click("#dists [data-d='200']")
    page.click("#hurd [data-h='0']")
    assert "Ennätys" not in page.inner_text("#stats")
    page.evaluate("""window.sent = []; const S = AiPelitScores, b = S.board;
      S.board = (id, label) => { window.sent.push(['board', id, label]); b(id, label); };
      S.submit = t => window.sent.push(['submit', t]);""")
    run(page)
    page.evaluate("race.runners.forEach(r => { if (r !== me) r.rate = 1; }); Object.assign(me, { x: 199.5, v: 9 })")
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=12000)
    rec = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:aitajuoksu:ennatys-200-tasainen'))")
    assert 0 < rec < 5
    assert page.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:ennatys')") == "15.5"
    # The time went to this race's own list.
    sent = page.evaluate("window.sent")
    i = next(i for i, e in enumerate(sent) if e[0] == "submit")
    assert sent[i - 1] == ["board", "200-tasainen", "200 m ilman aitoja"]
    page.click("#dists [data-d='100']")
    page.click("#hurd [data-h='1']")
    assert "15,50" in page.inner_text("#stats")
    assert page.errors == []


def test_in_a_room_the_hosts_race_is_everyones(site, browser):
    site.build(ROOT / "games")
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
    # The host picks under the players: 200 m with no hurdles.
    host.click("#aj-room [data-d='200']")
    host.click("#aj-room [data-h='0']")
    assert host.evaluate("[dist, hurdles]") == [200, False]
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    assert "Matkan valitsee" in guest.inner_text("#aj-room")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.dist === 200 && !race.hurdles && TRACK === 200 && H_N === 0", timeout=6000)
    # The guest's own menu choice stays its own.
    assert guest.evaluate("[dist, hurdles]") == [100, True]
    # A guest that reloads before the gun gets the host's race again.
    guest.reload()
    guest.wait_for_function("race && race.mode === 'net' && race.dist === 200 && !race.hurdles && TRACK === 200", timeout=8000)
    host.evaluate("race.gunAt = 0.05")
    for p in pages:
        p.wait_for_function("race.phase === 'run'", timeout=4000)
    guest.evaluate("Object.assign(me, { x: 199.8, v: 9 })")
    host.wait_for_function("race.runners[1].fin !== null", timeout=3000)
    host.evaluate("Object.assign(me, { x: 199.8, v: 9 })")
    for p in pages:
        p.wait_for_function("AiPelitRooms.inRoom && !race && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert guest.inner_text("#aipr-result").startswith("1. sija")
    assert guest.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:ennatys-200-tasainen')") is not None
    assert guest.evaluate("localStorage.getItem('ai-pelit:aitajuoksu:ennatys')") is None
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()
