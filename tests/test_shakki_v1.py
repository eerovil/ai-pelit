"""Shakki v1 (#465): the rules, the computer's levels, taps on the board, saves and layout."""

import pytest

from conftest import ROOT, turn

URL = "games/shakki/v1/"


def open_game(site, context, size=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if size:
        page.set_viewport_size(size)
    page.errors = []
    page.on("pageerror", lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    page.wait_for_function("view.s > 0")
    return page


def tap(page, name):
    """Taps the middle of the named square, as a finger would."""
    x, y = page.evaluate(f"(() => {{ const p = squareXY(sqIndex('{name}')); return [p[0] + view.cell / 2, p[1] + view.cell / 2]; }})()")
    page.mouse.click(x, y)


def set_moves(page, moves):
    """Puts the game in a position by its moves (setup only; the test then plays by taps)."""
    page.evaluate("ms => { clearTimeout(aiTimer); thinking = false; game.moves = ms; derived = playGame(ms); result = null; keepSolo(); updateHUD(); askDraw(); }", moves)


def perft(page, fen, depth):
    return page.evaluate("""([fen, depth]) => {
      function perft(pos, d) { if (!d) return 1; let n = 0;
        for (const m of legalMoves(pos)) { const u = makeMove(pos, m); n += perft(pos, d - 1); unmakeMove(pos, m, u); } return n; }
      return perft(parseFen(fen), depth);
    }""", [fen, depth])


def test_move_generation_matches_known_counts(site, context):
    page = open_game(site, context)
    # The standard move-path counts (perft): castling, en passant, promotion and pins all in them.
    assert perft(page, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3) == 8902
    assert perft(page, "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2) == 2039
    assert perft(page, "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3) == 2812
    assert perft(page, "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 2) == 264
    assert page.errors == []


def test_game_endings_and_finnish_notation(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const st = ms => { const g = playGame(ms); return [gameStatus(g), g.texts]; };
      const out = {};
      out.fool = st(['f2f3', 'e7e5', 'g2g4', 'd8h4']);
      // Knights out and back twice: the start position for the third time.
      out.rep = st(['g1f3', 'g8f6', 'f3g1', 'f6g8', 'g1f3', 'g8f6', 'f3g1', 'f6g8']);
      out.notYet = st(['g1f3', 'g8f6', 'f3g1', 'f6g8', 'g1f3', 'g8f6', 'f3g1']);
      const patti = parseFen('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1');
      out.patti = gameStatus({pos: patti, keys: [posKey(patti)]});
      const lone = parseFen('8/8/4k3/8/8/2B5/4K3/8 w - - 0 1');
      out.material = gameStatus({pos: lone, keys: [posKey(lone)]});
      const fifty = parseFen('8/8/4k3/8/8/2R5/4K3/8 w - - 100 80');
      out.fifty = gameStatus({pos: fifty, keys: [posKey(fifty)]});
      out.illegal = playGame(['e2e5']);
      out.castle = playGame(['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1c4', 'g8f6', 'e1g1']).texts.pop();
      return out;
    }""")
    assert r["fool"][0]["why"] == "matti" and r["fool"][0]["result"] == "0-1"
    assert r["fool"][1] == ["f3", "e5", "g4", "Dh4#"]
    assert r["rep"][0]["why"] == "toisto"
    assert r["notYet"][0]["over"] is False
    assert r["patti"]["why"] == "patti" and r["patti"]["result"] == "½-½"
    assert r["material"]["why"] == "materiaali"
    assert r["fifty"]["why"] == "50"
    assert r["illegal"] is None
    assert r["castle"] == "O-O"


def test_every_level_plays_legal_moves_and_the_strong_ones_see_mate(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => {
      const out = [];
      for (let l = 0; l < LEVELS.length; l++) {
        const g = playGame(['e2e4', 'e7e5', 'g1f3', 'b8c6']);
        const t = performance.now(), m = computerMove(g.pos, l, g.keys);
        out.push({ok: !!findMove(g.pos, moveUci(m)), ms: performance.now() - t});
      }
      // A back-rank mate in one, and a queen left hanging.
      const mate = parseFen('6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1');
      const hang = parseFen('rnb1kbnr/pppp1ppp/8/4p3/4P2q/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1');
      const fixed = () => 0.5;
      return {out, mate: [2, 3, 4].map(l => moveUci(computerMove(mate, l, [posKey(mate)], fixed))),
        hang: [2, 3, 4].map(l => moveUci(computerMove(hang, l, [posKey(hang)], fixed)))};
    }""")
    for lv in r["out"]:
        assert lv["ok"]
        # Each level stops itself in time (the strongest at 1.6 s), so a slow phone never hangs.
        assert lv["ms"] < 2500
    assert r["mate"] == ["a1a8"] * 3
    assert r["hang"] == ["f3h4"] * 3


def test_strong_level_beats_the_beginner(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      let n = 1;
      const rand = () => { n = (n * 16807) % 2147483647; return n / 2147483647; };
      LEVELS[3].ms = 400;
      let ms = [];
      for (let i = 0; i < 240; i++) {
        const g = playGame(ms), st = gameStatus(g);
        if (st.over) return st;
        ms.push(moveUci(computerMove(g.pos, g.pos.turn === 'w' ? 3 : 0, g.keys, rand)));
      }
      return {over: false};
    }""")
    assert res["over"] and res["result"] == "1-0"


def test_play_by_taps_computer_answers_and_the_game_is_saved(site, context):
    page = open_game(site, context)
    page.click("#levels button[data-l='0']")
    page.click("#colors button[data-c='w']")
    page.click("#play")
    tap(page, "e2")
    # The pawn's two squares are offered, and nothing else.
    assert sorted(page.evaluate("movesFrom(selected).map(moveUci)")) == ["e2e3", "e2e4"]
    tap(page, "e4")
    assert page.evaluate("derived.uci[0]") == "e2e4"
    assert page.locator("#status").inner_text() == "Kone miettii…"
    # A tap while the computer thinks does nothing.
    tap(page, "d2")
    assert page.evaluate("selected") == -1
    page.wait_for_function("derived.uci.length === 2 && !thinking")
    assert page.locator("#status").inner_text() == "Sinun vuorosi"
    # Dragging a piece moves it too.
    a = page.evaluate("(() => { const p = squareXY(sqIndex('g1')); return [p[0] + view.cell / 2, p[1] + view.cell / 2]; })()")
    b = page.evaluate("(() => { const p = squareXY(sqIndex('f3')); return [p[0] + view.cell / 2, p[1] + view.cell / 2]; })()")
    page.mouse.move(*a); page.mouse.down(); page.mouse.move(*b, steps=5); page.mouse.up()
    assert page.evaluate("derived.uci[2]") == "g1f3"
    page.wait_for_function("derived.uci.length === 4 && !thinking")
    saved = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:shakki:peli'))")
    assert saved["moves"] == page.evaluate("derived.uci") and saved["level"] == 0 and saved["mine"] == "w"
    moves = saved["moves"]
    page.reload()
    page.wait_for_function("view.s > 0")
    assert page.locator("#resume").is_visible()
    assert "Aloittelija" in page.locator("#resume").inner_text()
    page.click("#resume")
    assert page.evaluate("derived.uci") == moves
    assert page.evaluate("myTurn()")
    # Back to the menu keeps it too.
    page.click("#toMenu")
    assert page.locator("#resume").is_visible()
    assert page.errors == []


def test_black_mates_by_taps_and_the_win_is_counted_once(site, context):
    page = open_game(site, context)
    page.click("#levels button[data-l='2']")
    page.click("#colors button[data-c='b']")
    page.click("#play")
    # The board turns: black at the bottom.
    assert page.evaluate("flipped()") is True
    set_moves(page, ["f2f3", "e7e5", "g2g4"])
    tap(page, "d8")
    tap(page, "h4")
    page.wait_for_selector("#end:not(.hidden)")
    assert page.locator("#endTitle").inner_text() == "Voitit!"
    assert page.locator("#endSub").inner_text() == "Shakkimatti."
    assert page.evaluate("load('tilasto:2', null)") == {"v": 1, "h": 0, "t": 0}
    assert page.evaluate("localStorage.getItem('ai-pelit:shakki:peli')") is None
    # Looking at the board and back shows the same result; nothing is counted again.
    page.click("#peek")
    assert page.locator("#end").is_hidden()
    page.click("#showEnd")
    assert page.locator("#end").is_visible()
    page.click("#endMenu")
    assert "1 voittoa" in page.locator("#levelInfo").inner_text()
    assert page.locator("#resume").is_hidden()
    page.click("#play")
    assert page.evaluate("derived.uci.length") <= 1 and page.evaluate("result") is None
    assert page.errors == []


def test_promotion_picker_and_resign_twice(site, context):
    page = open_game(site, context)
    page.click("#colors button[data-c='w']")
    page.click("#play")
    set_moves(page, ["a2a4", "b7b5", "a4b5", "a7a6", "b5a6", "c8b7", "a6b7", "b8c6"])
    tap(page, "b7")
    tap(page, "a8")
    page.wait_for_selector("#promo:not(.hidden)")
    assert page.locator("#promoPieces button").count() == 4
    page.click("#promoPieces button[data-p='n']")
    assert page.evaluate("derived.uci[8]") == "b7a8n"
    assert page.evaluate("derived.pos.b[0]") == "N"
    page.wait_for_function("derived.uci.length === 10 && !thinking")
    page.click("#resign")
    assert page.locator("#resign").inner_text() == "Varmasti?"
    assert page.evaluate("result") is None
    page.click("#resign")
    page.wait_for_selector("#end:not(.hidden)")
    assert page.locator("#endSub").inner_text() == "Luovutit."
    assert page.evaluate("load('tilasto:2', null)") == {"v": 0, "h": 1, "t": 0}
    assert page.errors == []


@pytest.mark.parametrize("size", [{"width": 360, "height": 640}, {"width": 360, "height": 740},
                                  {"width": 390, "height": 844}, {"width": 740, "height": 360}])
def test_menu_and_board_fit_every_screen(site, context, size):
    page = open_game(site, context, size)
    for sel in ["#play", "#friends", "#levels button[data-l='4']", "#colors button[data-c='arvo']"]:
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= size["height"], sel
        assert box["x"] >= 0 and box["x"] + box["width"] <= size["width"], sel
    page.click("#play")
    v = page.evaluate("view")
    assert v["s"] >= 300
    assert v["x"] >= 0 and v["x"] + v["s"] <= size["width"] and v["y"] + v["s"] <= size["height"]
    # The buttons and names stay off the board, and on the screen.
    for sel in ["#resign", "#toMenu", "#meName", "#oppoName"]:
        box = page.locator(sel).bounding_box()
        assert box["y"] + box["height"] <= size["height"] and box["x"] + box["width"] <= size["width"] + 1, sel
        on_board = (box["x"] < v["x"] + v["s"] and box["x"] + box["width"] > v["x"] and
                    box["y"] < v["y"] + v["s"] and box["y"] + box["height"] > v["y"])
        assert not on_board, sel
    # The back chip's corner is off the board too.
    assert v["y"] >= 50 or v["x"] >= 110
    assert page.errors == []


def test_turning_the_phone_keeps_the_game(site, context):
    page = open_game(site, context)
    page.click("#play")
    tap(page, "e2")
    tap(page, "e4")
    page.wait_for_function("derived.uci.length === 2 && !thinking")
    moves = page.evaluate("derived.uci")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("view.land")
    assert page.evaluate("derived.uci") == moves
    tap(page, "d2")
    tap(page, "d4")
    assert page.evaluate("derived.uci[2]") == "d2d4"
    assert page.errors == []
