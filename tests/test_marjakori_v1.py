import shutil

from conftest import ROOT

URL = "games/marjakori/v1/"


def open_game(site, context):
    shutil.copytree(ROOT / "games" / "marjakori", site.games / "marjakori")
    site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    return page


def test_new_boards_have_no_ready_match_and_a_legal_move(site, context):
    page = open_game(site, context)
    assert page.evaluate("Array.from({length: 80}, (_, n) => { const s = Marjakori.newLevel(1, n + 1); return [Marjakori.matched(s.board).size, Marjakori.hasMove(s.board)]; })") == [[0, True]] * 80
    assert page.errors == []


def test_a_bad_swap_costs_nothing_and_a_legal_one_resolves(site, context):
    page = open_game(site, context)
    bad = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 9), before = JSON.stringify(s.board), moves = s.moves;
      let pair; for (let i = 0; !pair && i < 49; i++) for (const d of [1, 7]) {
        const b = i + d; if (b >= 49 || (d === 1 && i % 7 === 6)) continue;
        const t = Marjakori.clone(s); if (!Marjakori.trySwap(t, i, b).ok) { pair = [i, b]; break; }
      }
      const r = Marjakori.trySwap(s, pair[0], pair[1]);
      return [r.ok, s.moves === moves, JSON.stringify(s.board) === before];
    }""")
    assert bad == [False, True, True]
    good = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 7), moves = s.moves, pair = Marjakori.legalMoves(s)[0];
      const r = Marjakori.trySwap(s, pair[0], pair[1]); return [r.ok, s.moves === moves - 1, s.score > 0];
    }""")
    assert good == [True, True, True]
    assert page.errors == []


def test_real_swipe_plays_and_keeps_a_round_on_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("window.boardBox && state && state.phase === 'play'")
    pair = page.evaluate("Marjakori.legalMoves(state)[0]")
    box = page.evaluate("boardBox")
    def centre(i):
        return {"x": box["x"] + (i % 7 + .5) * box["size"], "y": box["y"] + (i // 7 + .5) * box["size"]}
    a, b = centre(pair[0]), centre(pair[1])
    page.mouse.move(a["x"], a["y"]); page.mouse.down(); page.mouse.move(b["x"], b["y"], steps=4); page.mouse.up()
    page.wait_for_function("state.moves === 19")
    page.reload()
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:marjakori:kierros')).moves") == 19
    assert page.errors == []
