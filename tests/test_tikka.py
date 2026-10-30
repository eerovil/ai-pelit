"""Tikanheitto, darts on a real board, in a phone-sized Chromium."""

import pytest
from conftest import ROOT, turn

URL = "games/tikka/v1/"

# Steps the game by hand, 1/60 s at a time, until cond() is false or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + URL)
    for k, v in (saved or {}).items():
        page.evaluate(f"localStorage.setItem('ai-pelit:tikka:{k}', '{v}')")
    if saved:
        page.goto(site.url + URL)
    page.evaluate(RUN)
    page.errors = errors
    return page


def land_at(page, mx, my):
    """Throws the current player's next dart at (mx, my) mm and lets it land."""
    page.evaluate(f"throwAt({mx}, {my}); run(() => flying !== null, 2)")


def test_the_board_scores_like_a_real_one(site, context):
    page = open_game(site, context)
    spots = {
        (0, 0): "Bull", (0, -11): "25", (0, -103): "T20", (0, -166): "D20", (0, -135): "20",
        (135, 0): "6", (0, 135): "3", (-135, 0): "11", (0, -180): "Ohi", (103, 0): "T6",
    }
    for (mx, my), label in spots.items():
        assert page.evaluate(f"scoreAt({mx}, {my}).label") == label
    assert page.evaluate("[scoreAt(0, -103).pts, scoreAt(0, -166).pts, scoreAt(0, 0).pts]") == [60, 40, 50]
    # Every spot the computer aims at scores what it aims for.
    bad = page.evaluate("""() => {
        const out = [];
        for (const n of ORDER) for (const m of [1, 2, 3]) {
            const s = spotOf(n, m), got = scoreAt(s.x, s.y).pts;
            if (got !== n * m) out.push([n, m, got]);
        }
        return out;
    }""")
    assert bad == []
    assert page.errors == []


def test_holding_moves_the_sight_and_letting_go_throws(site, context):
    page = open_game(site, context)
    page.click("#kisa")
    assert page.evaluate("[phase, mode, dartsLeft, round]") == ["play", "kisa", 3, 1]
    page.evaluate("aim = {x: 0, y: 0}")
    page.mouse.move(180, 650)
    page.mouse.down()
    page.mouse.move(180, 600, steps=4)
    page.evaluate("run(() => hold && hold.t < 0.3, 1)")
    assert page.evaluate("aim.y") < -30   # the finger went up, so did the sight
    page.mouse.up()
    assert page.evaluate("flying !== null && dartsLeft === 2")
    page.evaluate("run(() => flying !== null, 2)")
    assert page.evaluate("stuck.length") == 1
    # A brush of the screen does not throw.
    page.mouse.move(180, 650)
    page.mouse.down()
    page.mouse.up()
    assert page.evaluate("flying === null && dartsLeft === 2")
    assert page.errors == []


def test_a_points_match_is_ten_rounds_and_saves_the_record(site, context):
    page = open_game(site, context, {"ennatys": 100})
    page.click("#kisa")
    for _ in range(10):
        for _ in range(3):
            land_at(page, 0, -103)    # T20
        page.evaluate("run(() => pause > 0, 3)")
    page.evaluate("run(() => phase === 'play', 3)")
    assert page.evaluate("phase") == "menu"
    assert page.inner_text("#result") == "Pistekisa: 1800 p, uusi ennätys!"
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:ennatys')") == "1800"
    assert "Ennätys 1800 p" in page.inner_text("#stats")
    assert page.errors == []


def test_501_bust_puts_the_score_back_and_the_computer_takes_its_turn(site, context):
    page = open_game(site, context, {"vastus": "kova"})
    page.click("#go501")
    assert page.evaluate("players.map(p => [p.name, p.score, p.ai])") == [["Sinä", 501, None], ["Tietokone", 501, "kova"]]
    page.evaluate("players[0].score = turnStart = 70")
    land_at(page, 0, -135)   # 20, 50 left
    land_at(page, 0, -103)   # T20 would go under nought: bust
    assert page.evaluate("[players[0].score, pause > 0]") == [70, True]
    page.evaluate("run(() => pause > 0, 3)")
    assert page.evaluate("cur") == 1
    # The computer throws its three darts by itself, then it is the player's turn again.
    page.evaluate("run(() => cur === 1, 10)")
    assert page.evaluate("[cur, round]") == [0, 2]
    assert page.evaluate("players[1].score") < 501
    assert page.errors == []


def test_501_ends_on_exactly_nought_and_counts_the_win(site, context):
    page = open_game(site, context)
    page.click("#go501")
    page.evaluate("players[0].score = turnStart = 32")
    land_at(page, *page.evaluate("[spotOf(16, 2).x, spotOf(16, 2).y]"))   # D16
    page.evaluate("run(() => phase === 'play', 4)")
    assert page.evaluate("phase") == "menu"
    assert page.inner_text("#result") == "Voitit! Heitit 1 tikan."
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:voitot')") == "1"
    assert page.errors == []


def test_a_friend_takes_turns_on_the_same_phone(site, context):
    page = open_game(site, context, {"vastus": "kaveri"})
    page.click("#go501")
    assert page.evaluate("players.map(p => [p.name, p.ai])") == [["Pelaaja 1", None], ["Pelaaja 2", None]]
    for _ in range(3):
        land_at(page, 0, -135)
    page.evaluate("run(() => pause > 0, 3)")
    assert page.evaluate("[cur, players[0].score, bot]") == [1, 441, None]
    page.evaluate("players[1].score = turnStart = 40")
    land_at(page, 0, -166)  # D20
    page.evaluate("run(() => phase === 'play', 4)")
    assert page.inner_text("#result") == "Pelaaja 2 voitti!"
    assert page.evaluate("localStorage.getItem('ai-pelit:tikka:voitot')") is None
    assert page.errors == []


@pytest.mark.parametrize("size", [(740, 360), (640, 360), (360, 640)])
def test_the_menu_fits_without_scrolling(site, context, size):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#kisa", "#go501", "#opps"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h


def test_turning_the_phone_keeps_the_round_and_the_board_clear_of_the_panel(site, context):
    page = open_game(site, context)
    page.click("#kisa")
    land_at(page, 0, -103)
    turn(page, {"width": 740, "height": 360})
    page.wait_for_timeout(100)
    assert page.evaluate("[phase, players[0].score, dartsLeft, LAND]") == ["play", 60, 2, True]
    board_right = page.evaluate("BX + R_ALL * K")
    assert board_right <= page.evaluate("PANEL.x")
    assert page.evaluate("BY - R_ALL * K") >= 0 and page.evaluate("BY + R_ALL * K") <= 360
    # The panel sits under the corner chips.
    chip = page.locator("#ai-pelit-tulokset-nappi").bounding_box()
    assert page.evaluate("PANEL.y") >= chip["y"] + chip["height"]
    assert page.errors == []


def test_a_second_finger_does_not_steer_or_throw(site, context):
    page = open_game(site, context)
    page.click("#kisa")
    page.evaluate("run(() => true, 0.1)")
    page.evaluate("""() => {
        const c = document.getElementById('c');
        const ev = (type, id, x, y) => c.dispatchEvent(new PointerEvent(type, { pointerId: id, clientX: x, clientY: y, bubbles: true }));
        aim = { x: 0, y: 0 };
        ev('pointerdown', 1, 180, 650);
        ev('pointerdown', 2, 100, 650);
        ev('pointermove', 2, 100, 500);   // the second finger moves: the sight stays
        window.afterSecond = aim.y;
        run(() => hold.t < 0.3, 1);
        ev('pointerup', 2, 100, 500);     // the second finger lifts: no throw
        window.thrownAfterSecond = dartsLeft;
        ev('pointerup', 1, 180, 650);     // the first finger lifts: the dart flies
    }""")
    assert page.evaluate("[afterSecond, thrownAfterSecond, dartsLeft, flying !== null]") == [0, 3, 2, True]
    assert page.errors == []


def test_a_reload_keeps_the_record_wins_and_opponent(site, context):
    page = open_game(site, context, {"ennatys": 512, "voitot": 3, "vastus": "kova"})
    assert page.inner_text("#stats") == "Ennätys 512 p · Voittoja tietokoneesta 3"
    assert page.evaluate("document.querySelector('#opps .on').dataset.o") == "kova"
    page.click("#opps [data-o=helppo]")
    page.reload()
    assert page.evaluate("document.querySelector('#opps .on').dataset.o") == "helppo"
    assert page.errors == []


def test_on_a_390_px_phone_the_board_and_panel_fit_under_the_chips(site, context):
    page = open_game(site, context)
    turn(page, {"width": 390, "height": 844})
    page.click("#kisa")
    w, h = 390, 844
    left, right = page.evaluate("BX - R_ALL * K"), page.evaluate("BX + R_ALL * K")
    top, bottom = page.evaluate("BY - R_ALL * K"), page.evaluate("BY + R_ALL * K")
    assert left >= 0 and right <= w and bottom <= h - 60
    assert top >= page.evaluate("PANEL.y + PANEL.h")
    chip = page.locator("#ai-pelit-tulokset-nappi").bounding_box()
    assert page.evaluate("PANEL.y") >= chip["y"] + chip["height"]
    assert page.errors == []
