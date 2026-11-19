"""Shakki v3 (#465): practice mode's warnings count material, not heads."""

import pytest

from test_shakki_v3 import open_game


def risk(page, fen, frm, to):
    return page.evaluate("""([fen, f, t]) => {
      const pos = playGame([], fen).pos, m = legalMoves(pos).find(m => m.from === sqIndex(f) && m.to === sqIndex(t));
      const e = exposedBy(pos, m);
      return [e.self, e.others.map(sqName)];
    }""", [fen, frm, to])


@pytest.mark.parametrize("fen, frm, to, want", [
    # The rook leaves the e4 pawn, which a rook and a queen attack and a pawn guards: taking it
    # costs black a rook, so it is safe (counting heads, 2 against 1, called it lost).
    ("4r2k/8/8/8/q3P3/3P4/8/4R2K w - - 0 1", "e1", "f1", [False, []]),
    # The same pawn with no pawn to guard it is lost when the rook leaves.
    ("4r2k/8/8/8/4P3/8/8/4R2K w - - 0 1", "e1", "f1", [False, ["e4"]]),
    # The knight's only attacker is pinned to its king: it cannot take.
    ("7k/8/5n2/3NB3/8/8/8/3R3K w - - 0 1", "d1", "a1", [False, []]),
    # A rook facing a rook, guarded by a pawn: an even trade, not red.
    ("6k1/8/8/8/3r4/P7/1R6/6K1 w - - 0 1", "b2", "b4", [False, []]),
    # ...but a bishop attacks the same square too: the bishop takes it, so it is red.
    ("6k1/8/3b4/8/3r4/P7/1R6/6K1 w - - 0 1", "b2", "b4", [True, []]),
    # Taking a guarded knight with the rook loses the rook for a knight.
    ("6k1/8/8/2p5/1n6/8/1R6/6K1 w - - 0 1", "b2", "b4", [True, []]),
    # Taking a guarded rook with the rook is even.
    ("6k1/8/8/2p5/1r6/8/1R6/6K1 w - - 0 1", "b2", "b4", [False, []]),
])
def test_move_warnings(site, context, fen, frm, to, want):
    page = open_game(site, context)
    assert risk(page, fen, frm, to) == want
    assert page.errors == []


MOVES = ["e2e4", "a7a6", "g1f3", "h7h6", "d2d4", "b7b6", "c1g5", "a6a5"]  # the h6 pawn attacks the g5 bishop


def test_info_line_says_what_the_trade_loses(site, context):
    page = open_game(site, context)
    page.evaluate("""ms => startGame({moves: ms, mine: 'w', level: 0, white: {id: 'solo', name: 'Sinä'},
      black: {id: 'kone', name: 'Kone'}, practice: true}, false)""", MOVES)
    texts = page.evaluate("""() => ['g5', 'e4', 'h6'].map(s => infoText(derived.pos, sqIndex(s)))""")
    # The bishop: a pawn takes it, the knight takes back a pawn.
    assert "⚠ Sotilas h6 lyö sen: menetät 3, saat takaisin 1" in texts[0]
    # The e4 pawn is safe: no warning.
    assert "⚠" not in texts[1] and "Voit voittaa" not in texts[1]
    # Black's h6 pawn is guarded by g7: taking it with the bishop does not pay.
    assert "Voit voittaa" not in texts[2]
    assert page.errors == []


def test_info_line_says_what_you_can_win(site, context):
    page = open_game(site, context)
    page.evaluate("""ms => startGame({moves: ms, mine: 'w', level: 0, white: {id: 'solo', name: 'Sinä'},
      black: {id: 'kone', name: 'Kone'}, practice: true}, false)""",
                  ["e2e4", "e7e5", "g1f3", "f8c5", "f1c4", "h7h5", "f3e5", "d8e7"])
    f7, e5 = page.evaluate("""() => ['f7', 'e5'].map(s => infoText(derived.pos, sqIndex(s)))""")
    # The king cannot take back on f7 (the c4 bishop guards it), and the queen would be lost.
    assert "Voit voittaa sen: Ratsu e5 lyö, saat 1 etkä menetä mitään" in f7
    assert "⚠ Daami e7 lyö sen: menetät 3 etkä saa mitään takaisin" in e5
    assert page.errors == []


def test_bishop_for_knight_is_even(site, context):
    # Eero's position: Nxc8 is a discovered check from the d2 queen, so only the king takes back:
    # a bishop for a knight, even, not green. Nxb7 is the same discovered check, and then nothing
    # can take back: the pawn is won. Black wins the d6 knight with the f8 bishop.
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const pos = playGame([], 'rnb2b2/1pqk4/2pN2pr/P6p/P1B2P1B/8/2PQ1RPP/3R2K1 w - - 0 1').pos;
      return ['c8', 'b7', 'd6'].map(s => hanging(pos, sqIndex(s)));
    }""")
    assert got == [False, True, True]
    # A bishop taking a guarded knight is even, not red.
    assert risk(page, "6k1/8/4p3/3n4/8/1B6/8/6K1 w - - 0 1", "b3", "d5") == [False, []]
    assert page.errors == []


def test_practice_counts_nothing_and_undoes_without_limit(site, context):
    from test_shakki_v3 import set_moves, tap
    page = open_game(site, context)
    page.click("#colors button[data-c='b']")
    page.click("#practice")
    assert page.evaluate("game.practice") is True
    assert page.locator("#resign").is_hidden() and page.locator("#undo").is_visible()
    assert "🎓 Harjoitus" in page.locator("#meName").inner_text()
    page.wait_for_function("derived.uci.length === 1 && !thinking")
    # Undo goes back past the computer's first move too: nothing of the player's to take back yet.
    assert page.locator("#undo").is_disabled()
    set_moves(page, ["f2f3", "e7e5", "g2g4"])
    # A tap on the opponent's piece shows who threatens and guards it.
    tap(page, "g4")
    assert page.locator("#lastMove").inner_text().startswith("Sotilas g4 (vastustajan):")
    tap(page, "d8")
    tap(page, "h4")
    page.wait_for_selector("#end:not(.hidden)")
    assert page.locator("#endTitle").inner_text() == "Voitit!"
    assert page.locator("#endStats").inner_text() == "Harjoituspeli: ei tilastoihin eikä avaa tasoja."
    assert page.evaluate("load('tilasto:0', null)") is None and not page.evaluate("unlocked(1)")
    # Undo from the end card: the mate is taken back, then the move before it, and so on.
    page.click("#endUndo")
    assert page.locator("#end").is_hidden() and page.evaluate("result") is None
    assert page.evaluate("derived.uci") == ["f2f3", "e7e5", "g2g4"]
    page.click("#undo")
    assert page.evaluate("derived.uci") == ["f2f3"]
    assert page.locator("#undo").is_disabled()
    # The practice game is saved as one, and the menu says so.
    page.click("#toMenu")
    assert page.locator("#resumePractice").inner_text().startswith("🎓 Jatka harjoitusta")
    page.click("#resumePractice")
    assert page.evaluate("game.practice") is True
    assert page.errors == []


def test_practice_fits_sideways(site, context):
    page = open_game(site, context, {"width": 740, "height": 360})
    page.click("#practice")
    page.wait_for_function("!thinking")
    box = page.locator("#undo").bounding_box()
    assert box and box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= 740 and box["y"] + box["height"] <= 360
    assert page.evaluate("document.scrollingElement.scrollHeight") <= 360
    assert page.errors == []


def test_en_passant_and_king_counts(site, context):
    page = open_game(site, context)
    # exd6 en passant takes a pawn; the knight takes back a pawn: even, not red.
    got = page.evaluate("""() => {
      const pos = playGame(['d7d5'], '4k3/3p4/8/4P3/2n5/8/8/4K3 b - - 0 1').pos;
      const m = legalMoves(pos).find(m => m.flag === 'ep');
      return exposedBy(pos, m).self;
    }""")
    assert got is False
    counts = page.evaluate("""() => {
      const c = (fen, s) => { const g = guardInfo(playGame([], fen).pos, sqIndex(s)); return [g.attackers.map(sqName), g.defenders.map(sqName)]; };
      return [c('3r4/8/8/3B4/4K3/8/8/7k w - - 0 1', 'd5'), c('3r2b1/8/8/3B4/4K3/8/8/7k w - - 0 1', 'd5'),
              c('8/8/4p3/3n4/4K3/8/8/k7 w - - 0 1', 'd5')];
    }""")
    # The king takes back after the one attacker took; not when a second one guards the square.
    assert counts[0] == [["d8"], ["e4"]]
    assert sorted(counts[1][0]) == ["d8", "g8"] and counts[1][1] == []
    # The king does not attack a guarded piece.
    assert counts[2] == [[], ["e6"]]
    assert page.errors == []


def test_practice_refused_capture_still_says_why(site, context):
    from test_shakki_v3 import set_moves, tap
    page = open_game(site, context)
    page.click("#colors button[data-c='b']")
    page.click("#practice")
    page.wait_for_function("derived.uci.length === 1 && !thinking")
    set_moves(page, ["e2e4", "b8c6", "d2d4", "f7f6", "d1h5"])
    tap(page, "c6")
    tap(page, "d4")
    assert page.locator("#lastMove").inner_text() == "⚠ Shakki! Torju se ensin."
    assert page.errors == []


def test_ended_practice_game_can_be_undone_after_a_reload(site, context):
    from test_shakki_v3 import set_moves, tap
    page = open_game(site, context)
    page.click("#colors button[data-c='b']")
    page.click("#practice")
    page.wait_for_function("derived.uci.length === 1 && !thinking")
    set_moves(page, ["f2f3", "e7e5", "g2g4"])
    tap(page, "d8")
    tap(page, "h4")
    page.wait_for_selector("#end:not(.hidden)")
    page.reload()
    page.wait_for_function("view.s > 0")
    assert page.locator("#resumePractice").inner_text().startswith("🎓 Jatka harjoitusta")
    page.click("#resumePractice")
    page.wait_for_selector("#end:not(.hidden)")
    page.click("#endUndo")
    assert page.evaluate("derived.uci") == ["f2f3", "e7e5", "g2g4"]
    assert page.errors == []


def test_promotion_moves_count_as_one_square(site, context):
    # A pawn whose only square is b8 (four promotions): its warning says "jos sotilas lähtee".
    page = open_game(site, context)
    page.evaluate("""() => startGame({moves: [], mine: 'w', level: 0, white: {id: 'solo', name: 'Sinä'},
      black: {id: 'kone', name: 'Kone'}, practice: true}, false)""")
    text = page.evaluate("""() => {
      derived = playGame([], '2N4r/1P4k1/8/8/8/8/8/6K1 w - - 0 1'); game.moves = [];
      selected = sqIndex('b7'); riskCache.key = '';
      return infoText(derived.pos, selected);
    }""")
    assert "jos sotilas lähtee, Rc8 jää ilman riittävää puolustusta" in text
    assert page.errors == []


def test_practice_never_replaces_an_unfinished_game(site, context):
    from test_shakki_v3 import set_moves
    page = open_game(site, context)
    page.click("#colors button[data-c='w']")
    page.click("#play")
    set_moves(page, ["e2e4", "e7e5", "g1f3"])
    page.click("#toMenu")
    page.click("#practice")
    page.wait_for_function("!thinking")
    set_moves(page, ["d2d4", "d7d5"])
    page.click("#toMenu")
    # Both games wait in the menu, each behind its own button, and fit it.
    assert page.locator("#resume").inner_text().startswith("Jatka peliä")
    assert page.locator("#resumePractice").inner_text().startswith("🎓 Jatka harjoitusta")
    page.click("#resume")
    assert page.evaluate("derived.uci.slice(0, 3)") == ["e2e4", "e7e5", "g1f3"] and not page.evaluate("game.practice")
    page.click("#toMenu")
    page.click("#resumePractice")
    assert page.evaluate("derived.uci") == ["d2d4", "d7d5"] and page.evaluate("game.practice") is True
    page.click("#toMenu")
    assert page.errors == []
    # The menu with both buttons fits upright and sideways (a new page reads the same saves).
    for size in ({"width": 360, "height": 640}, {"width": 740, "height": 360}):
        p = open_game(site, context, size)
        assert p.locator("#resume").is_visible() and p.locator("#resumePractice").is_visible()
        assert p.evaluate("document.scrollingElement.scrollHeight") <= size["height"]
        box = p.locator("#resumePractice").bounding_box()
        assert box["y"] + box["height"] <= size["height"]
        assert p.errors == []


def test_en_passant_takes_a_pawn_that_moved_two(site, context):
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const fen = '4k3/8/8/8/4p3/8/3P4/4K3 w - - 0 1', pos = playGame([], fen).pos;
      const m = legalMoves(pos).find(m => sqName(m.from) === 'd2' && sqName(m.to) === 'd4');
      const warn = exposedBy(pos, m).self;
      const after = playGame(['d2d4'], fen).pos, g = guardInfo(after, sqIndex('d4')), t = threat(after, sqIndex('d4'));
      return [warn, g.attackers.map(sqName), t && sqName(t.from), targetsOf(after, sqIndex('e4')).map(sqName)];
    }""")
    # d2d4 next to the e4 pawn: exd3 en passant wins it, so the move is red, and so is the pawn.
    assert got == [True, ["e4"], "e4", ["d4"]]
    # With no black pawn beside it, the same move is safe.
    safe = page.evaluate("""() => {
      const fen = '4k3/8/8/8/7p/8/3P4/4K3 w - - 0 1', pos = playGame([], fen).pos;
      const m = legalMoves(pos).find(m => sqName(m.from) === 'd2' && sqName(m.to) === 'd4');
      return exposedBy(pos, m).self;
    }""")
    assert safe is False
    assert page.errors == []
