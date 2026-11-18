"""Shakki v2 (#465): a move refused because of the king's safety says why, and the piece to blame shakes."""

import pytest

from test_shakki_v2 import open_game, set_moves, tap

PIN = ["e2e4", "e7e5", "d2d4", "f8b4", "c2c3", "d8h4"]  # white's f2 pawn is pinned by the queen on h4


def why(page, moves, frm, to, fen=None):
    return page.evaluate("""([ms, f, t, fen]) => {
      const g = playGame(ms, fen || undefined), r = whyIllegal(g.pos, sqIndex(f), sqIndex(t));
      return r && [r.text, r.shake.map(sqName).sort(), sqName(r.king)];
    }""", [moves, frm, to, fen])


@pytest.mark.parametrize("moves, fen, frm, to, want", [
    # A pinned piece.
    (PIN, None, "f2", "f3", ["Nappula on sidottu: kuningas jäisi uhatuksi.", ["h4"], "e1"]),
    # In check, a move that does not answer it.
    (["f2f3", "e7e5", "g2g4", "d8h4"], None, "a2", "a3", ["Shakki! Torju se ensin.", ["h4"], "e1"]),
    (["f2f3", "e7e5", "g2g4", "d8h4"], None, "g1", "h3", ["Shakki! Torju se ensin.", ["h4"], "e1"]),
    # The king onto an attacked square.
    (["e2e4", "d7d5", "e4d5", "d8d5", "d2d4", "d5e5"], None, "e1", "e2", ["Kuningas ei voi mennä uhatulle ruudulle.", ["e5"], "e2"]),
    # Castling in check, and across an attacked square.
    ([], "4k3/8/8/8/8/8/8/r3K2R w K - 0 1", "e1", "g1", ["Shakissa ei voi linnoittautua.", ["a1"], "e1"]),
    ([], "4k3/8/8/8/8/8/5r2/4K2R w K - 0 1", "e1", "g1", ["Linnoitus ei käy: kuningas kulkisi uhatun ruudun yli.", ["f2"], "f1"]),
    # Black's pinned knight, the board seen from black's side.
    (["e2e4", "d7d6", "d2d4", "b8c6", "f1b5"], None, "c6", "d4", ["Nappula on sidottu: kuningas jäisi uhatuksi.", ["b5"], "e8"]),
    # A piece's own way of moving needs no reason (Eero's choice), nor does a legal move.
    ([], None, "g1", "g3", None),
    ([], None, "c1", "e3", None),
    ([], None, "e2", "e5", None),
    (["e2e4", "e7e5"], None, "e4", "e5", None),
    ([], None, "g1", "f3", None),
    # Castling rights gone, or a piece between: the king's own rules, no reason either.
    (["e2e4", "e7e5", "e1e2", "e8e7", "e2e1", "e7e8", "g1f3", "g8f6", "f1c4", "f8c5"], None, "e1", "g1", None),
    ([], None, "e1", "g1", None),
])
def test_reasons_only_for_the_kings_safety(site, context, moves, fen, frm, to, want):
    page = open_game(site, context)
    assert why(page, moves, frm, to, fen) == want


def test_a_pinned_piece_says_why_and_the_blamed_piece_shakes(site, context):
    page = open_game(site, context)
    page.click("#colors button[data-c='w']")
    page.click("#play")
    set_moves(page, PIN)
    before = page.locator("#lastMove").inner_text()
    # The pinned pawn has no move at all: choosing it says why at once.
    tap(page, "f2")
    assert page.locator("#lastMove").inner_text() == "⚠ Nappula on sidottu: kuningas jäisi uhatuksi."
    assert "why" in page.get_attribute("#lastMove", "class")
    assert page.evaluate("why.shake.map(sqName)") == ["h4"]
    # The queen moves off its square while it shakes, and is back still after it.
    off = page.evaluate("shakeOf(sqIndex('h4'), why.t0 + 50)")
    assert abs(off) > 1
    assert page.evaluate("shakeOf(sqIndex('h4'), why.t0 + SHAKE_MS + 1)") == 0
    assert page.evaluate("shakeOf(sqIndex('e1'), why.t0 + 50)") == 0
    # A legal move clears it.
    tap(page, "g1")
    assert page.locator("#lastMove").inner_text() == before
    tap(page, "f3")
    assert page.evaluate("derived.uci[6]") == "g1f3"
    assert page.evaluate("why") is None
    assert page.errors == []


def test_a_wrong_tap_or_drag_says_why_only_for_the_king(site, context):
    page = open_game(site, context)
    page.click("#colors button[data-c='w']")
    page.click("#play")
    set_moves(page, ["f2f3", "e7e5", "g2g4", "d8h4"])
    before = page.locator("#lastMove").inner_text()
    # A knight's move that leaves the check: refused with the reason, the checking queen blamed.
    tap(page, "b1")
    tap(page, "c3")
    assert page.locator("#lastMove").inner_text() == "⚠ Shakki! Torju se ensin."
    assert page.evaluate("[selected, why.shake.map(sqName), derived.uci.length]") == [-1, ["h4"], 4]
    # A move against the knight's own way of moving: refused quietly, the reason goes.
    tap(page, "b1")
    tap(page, "b3")
    assert page.locator("#lastMove").inner_text() == before
    assert page.evaluate("[selected, why]") == [-1, None]
    # A drag to a square the king may not go to says why too.
    page.evaluate("WHY_MS = 400")
    a = page.evaluate("(() => { const p = squareXY(sqIndex('e1')); return [p[0] + view.cell / 2, p[1] + view.cell / 2]; })()")
    b = page.evaluate("(() => { const p = squareXY(sqIndex('f2')); return [p[0] + view.cell / 2, p[1] + view.cell / 2]; })()")
    page.mouse.move(*a); page.mouse.down(); page.mouse.move(*b, steps=5); page.mouse.up()
    assert page.locator("#lastMove").inner_text() == "⚠ Kuningas ei voi mennä uhatulle ruudulle."
    assert page.evaluate("derived.uci.length") == 4
    # The reason fades by itself.
    page.wait_for_function("why === null")
    assert page.locator("#lastMove").inner_text() == before
    assert page.errors == []


def test_the_reason_shows_sideways_too(site, context):
    page = open_game(site, context, {"width": 740, "height": 360})
    page.click("#colors button[data-c='w']")
    page.click("#play")
    set_moves(page, PIN)
    tap(page, "f2")
    line = page.locator("#paStatus .lastMove")
    assert line.inner_text() == "⚠ Nappula on sidottu: kuningas jäisi uhatuksi."
    assert line.get_attribute("class") == "lastMove why"
    assert page.errors == []
