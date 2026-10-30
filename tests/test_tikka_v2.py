"""Tikanheitto v2: Mökkitikka by default, and games with friends in a room (#118)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/tikka/v2/"

# Steps the game by hand, 1/60 s at a time, until cond() is false or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    for k, v in (saved or {}).items():
        page.evaluate(f"localStorage.setItem('ai-pelit:tikka:{k}', '{v}')")
    if saved:
        page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def land_at(page, mx, my):
    page.evaluate(f"throwAt({mx}, {my}); run(() => flying !== null, 2)")


def test_the_cottage_board_scores_ten_in_the_middle_down_to_one(site, context):
    page = open_game(site, context)
    spots = {(0, 0): "10", (0, 17.5): "10", (0, 20): "9", (34.5, 0): "9", (0, -35): "8",
             (100, 0): "5", (0, 170): "1", (0, -171): "Ohi"}
    for (mx, my), label in spots.items():
        assert page.evaluate(f"mokkiAt({mx}, {my}).label") == label
    assert page.evaluate("[mokkiAt(0, 0).pts, mokkiAt(0, 160).pts, mokkiAt(0, 200).pts]") == [10, 1, 0]
    assert page.errors == []


def test_mokkitikka_is_the_first_button_and_a_full_game_saves_its_own_record(site, context):
    page = open_game(site, context, {"ennatys": 412, "voitot": 2})
    # v1's saves are still read.
    assert page.inner_text("#stats") == "Ennätykset: Pistekisa 412 p · Voittoja tietokoneesta 2"
    assert page.inner_text("#go") == "Mökkitikka"
    page.click("#go")
    assert page.evaluate("[phase, mode, players.length, dartsLeft]") == ["play", "mokki", 1, 3]
    for _ in range(10):
        for _ in range(3):
            land_at(page, 0, 0)
        page.evaluate("run(() => pause > 0, 3)")
    page.evaluate("run(() => phase === 'play', 3)")
    assert page.inner_text("#result") == "Mökkitikka: 300 p, uusi ennätys!"
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:mokki')") == "300"
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:ennatys')") == "412"
    assert page.inner_text("#stats").startswith("Ennätykset: Mökkitikka 300 p · Pistekisa 412 p")
    assert page.errors == []


def test_pistekisa_and_501_still_play_on_the_darts_board(site, context):
    page = open_game(site, context, {"vastus": "kaveri"})
    page.click("#kisa")
    assert page.evaluate("[mode, scoreAt(0, -103).label]") == ["kisa", "T20"]
    page.evaluate("phase = 'menu'; showMenu()")
    page.click("#go501")
    assert page.evaluate("[mode, players.map(p => p.score)]") == ["501", [501, 501]]
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 740), (740, 360), (390, 844)])
@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_the_panel_fits_every_player_count_with_no_text_on_text(site, context, size, n):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    page.click("#go")
    page.evaluate(f"""() => {{
        players = Array.from({{ length: {n} }}, (_, i) => Object.assign(player('Pelaaja ' + (i + 1)), {{ score: 288 }}));
        cur = {n} - 1; resize();
        turnDarts = [mokkiAt(0, 0), mokkiAt(0, 0), mokkiAt(0, 0)];
        draw();
    }}""")
    texts, panel = page.evaluate("panelTexts"), page.evaluate("PANEL")
    assert "10 · 10 · 10" in [t["text"] for t in texts]
    for i, a in enumerate(texts):
        assert panel["x"] <= a["x0"] and a["x1"] <= panel["x"] + panel["w"], a
        assert panel["y"] <= a["y0"] and a["y1"] <= panel["y"] + panel["h"], a
        for b in texts[i + 1:]:
            assert not (a["x0"] < b["x1"] and b["x0"] < a["x1"] and a["y0"] < b["y1"] and b["y0"] < a["y1"]), (a, b)
    # The board is below the panel (upright) or beside it (sideways), and on the screen.
    top, bottom = page.evaluate("BY - R_ALL * K"), page.evaluate("BY + R_ALL * K")
    assert top >= 0 and bottom <= h
    if w < h:
        assert top >= panel["y"] + panel["h"]
    else:
        assert page.evaluate("BX + R_ALL * K") <= panel["x"]
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360), (640, 360), (390, 844)])
def test_the_menu_fits_without_scrolling(site, context, size):
    w, h = size
    page = open_game(site, context, {"mokki": 231, "ennatys": 412, "voitot": 3})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#kisa", "#go501", "#opps", "#stats"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    assert page.errors == []


# ---- With friends ----

def room(site, browser, names):
    """The first phone makes a room, the others join it, and the game starts."""
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host = pages[0]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for guest in pages[1:]:
        guest.click("#multi")
        guest.fill("#aipr-codeIn", code)
        guest.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    return relay, pages


def start(pages):
    pages[0].click("#aipr-start")
    for p in pages:
        p.wait_for_function("phase === 'play' && players.length > 1", timeout=8000)


def throw_turn(page, mx, my, host):
    """The phone whose turn it is throws its three darts at (mx, my) mm, waiting for each to land."""
    page.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    for k in range(3):
        page.evaluate(f"release({mx}, {my})")
        host.wait_for_function(f"dartsLeft === {2 - k} && !flying", timeout=5000)


def test_three_phones_play_mokkitikka_in_turns_and_the_best_wins(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host, aino, ville = pages
    # The host picks the game under the players; the others see who picks.
    assert host.inner_text("#tk-room .on") == "Mökkitikka"
    assert "Pelin valitsee" in aino.inner_text("#tk-room")
    start(pages)
    assert aino.evaluate("[mode, players.map(p => p.name), cur, mine()]") == ["mokki", ["Eero", "Aino", "Ville"], 0, False]
    host.evaluate("round = 10; sync()")
    # Eero throws 5s, Aino tens, Ville 8s. Every phone sees each turn's darts and scores.
    throw_turn(host, 100, 0, host)
    aino.wait_for_function("cur === 1 && players[0].score === 15", timeout=8000)
    assert ville.evaluate("players[0].score") == 15
    throw_turn(aino, 0, 0, host)
    host.wait_for_function("players[1].score === 30 && players[1].tens === 3")
    ville.wait_for_function("cur === 2 && players[1].score === 30", timeout=8000)
    # Ville reloads before his turn: the host gives him the game back.
    ville.reload()
    ville.wait_for_function("phase === 'play' && cur === 2 && players[1].score === 30 && mine()", timeout=10000)
    throw_turn(ville, 0, -40, host)
    for p in pages:
        p.wait_for_function("AiPelitRooms.inRoom && phase === 'menu' && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert aino.inner_text("#aipr-result").startswith("Voitit! 30 p")
    assert ville.inner_text("#aipr-result").startswith("2. sija · 24 p")
    assert host.inner_text("#aipr-result").startswith("3. sija · 15 p")
    # Each phone keeps its own Mökkitikka record.
    assert aino.evaluate("localStorage.getItem('ai-pelit:tikka:mokki')") == "30"
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_a_guest_cannot_throw_out_of_turn_and_the_host_sees_its_sight(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    host.click("#tk-room [data-m='501']")
    start(pages)
    assert aino.evaluate("mode") == "501"
    # Not Aino's turn: a throw message from her is ignored by the host.
    aino.evaluate("AiPelitRooms.send({ t: 'th', round: net.round, x: 0, y: 0, n: 1 })")
    host.wait_for_timeout(300)
    assert host.evaluate("[cur, dartsLeft, players[0].score, players[1].score]") == [0, 3, 501, 501]
    throw_turn(host, 0, -103, host)   # 180
    aino.wait_for_function("cur === 1 && players[0].score === 321 && mine()", timeout=8000)
    # Aino holds her finger: the host sees her sight move.
    aino.mouse.move(180, 650)
    aino.mouse.down()
    aino.mouse.move(220, 600, steps=4)
    host.wait_for_function("seen !== null", timeout=3000)
    aino.wait_for_function("hold && hold.t > 0.2")
    aino.mouse.up()
    host.wait_for_function("dartsLeft === 2", timeout=5000)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_a_phone_away_pauses_and_then_the_computer_throws_for_it(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    start(pages)
    throw_turn(host, 0, 0, host)
    aino.wait_for_function("cur === 1 && mine()", timeout=8000)
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    held = host.evaluate("[cur, dartsLeft, players[1].score]")
    host.wait_for_timeout(500)
    assert host.evaluate("[cur, dartsLeft, players[1].score]") == held
    # "Jatka ilman heitä": the computer throws Aino's turn, and it is Eero's again.
    host.click("#aipr-goOn")
    host.wait_for_function("players[1].ai === 'keski'", timeout=4000)
    # Three aimed darts and the turn's end take about 5 s.
    host.wait_for_function("cur === 0 && round === 2 && players[1].score > 0", timeout=15000)
    # Aino comes back and gets her player back.
    relay.back(aino)
    host.wait_for_function("players[1].ai === null", timeout=8000)
    aino.wait_for_function("phase === 'play' && cur === 0 && players[1].score > 0", timeout=8000)
    for p in pages:
        assert p.errors == []
        p.context.close()
