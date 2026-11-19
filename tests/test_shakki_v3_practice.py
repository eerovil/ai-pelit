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
