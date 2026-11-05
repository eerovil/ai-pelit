import shutil

from conftest import ROOT, turn

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


def test_greedy_bot_can_clear_every_level(site, context):
    page = open_game(site, context)
    wins = page.evaluate("""() => Array.from({length: 40}, (_, level) => {
      let wins = 0;
      for (let seed = 1; seed <= 20; seed++) {
        const s = Marjakori.newLevel(level + 1, seed);
        while (s.phase === 'play') {
          let best = null;
          Marjakori.legalMoves(s).forEach(m => {
            const next = Marjakori.clone(s); Marjakori.trySwap(next, m[0], m[1]);
            if (!best || next.score > best.score) best = { m, score: next.score };
          });
          if (!best) break;
          Marjakori.trySwap(s, best.m[0], best.m[1]);
        }
        if (s.phase === 'win') wins++;
      }
      return wins;
    })""")
    assert min(wins) >= 12
    assert page.errors == []


def test_any_legal_move_bot_does_not_breeze_past_later_levels(site, context):
    page = open_game(site, context)
    wins = page.evaluate("""() => Array.from({length: 31}, (_, offset) => {
      const level = offset + 10; let wins = 0;
      for (let seed = 1; seed <= 20; seed++) {
        const s = Marjakori.newLevel(level, seed); let turn = 0;
        while (s.phase === 'play') {
          const moves = Marjakori.legalMoves(s); if (!moves.length) break;
          const move = moves[(seed + turn++) % moves.length]; Marjakori.trySwap(s, move[0], move[1]);
        }
        if (s.phase === 'win') wins++;
      }
      return wins;
    })""")
    assert max(wins) <= 10
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


def test_four_five_crosses_and_two_specials_do_their_own_clear(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const base = () => {
        const s = Marjakori.newLevel(1, 4);
        s.board.forEach((c, i) => Object.assign(c, { kind: (i % 7 + 2 * Math.floor(i / 7)) % 7, moss: false, special: '' }));
        return s;
      };
      const four = base(); [0, 1, 2, 3, 4].forEach((i, k) => four.board[i].kind = [0, 0, 0, 1, 0][k]);
      Marjakori.trySwap(four, 3, 4);
      const five = base(); [0, 1, 2, 3, 4, 5].forEach((i, k) => five.board[i].kind = [0, 0, 0, 0, 1, 0][k]);
      Marjakori.trySwap(five, 4, 5);
      const cross = base(); [2, 8, 9, 10, 16].forEach(i => cross.board[i].kind = 0);
      const both = base(); both.board[0].special = 'puuska'; both.board[1].special = 'kimallus'; const moves = both.moves;
      const pair = Marjakori.trySwap(both, 0, 1);
      return [four.board[3].special, five.board[4].special, Marjakori.runs(cross.board).length, pair.ok, both.moves === moves - 1, both.score > 0];
    }""")
    assert result == ["puuska", "kimallus", 2, True, True, True]
    assert page.errors == []


def test_specials_target_the_neighbour_kind_and_their_run_direction(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 4);
      s.board.forEach((c, i) => c.kind = i % 6);
      const sparkle = Marjakori.specialCells(s.board, 0, { special: 'kimallus', kind: 0, aim: 3 });
      const vertical = Marjakori.specialCells(s.board, 23, { special: 'puuska', vertical: true });
      const horizontal = Marjakori.specialCells(s.board, 23, { special: 'puuska', vertical: false });
      return [sparkle, vertical, horizontal];
    }""")
    assert result == [[3, 9, 15, 21, 27, 33, 39, 45], [2, 9, 16, 23, 30, 37, 44], [21, 22, 23, 24, 25, 26, 27]]
    assert page.errors == []


def test_a_cascade_match_can_make_a_special(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 14);
      s.board.forEach((c, i) => { c.kind = (i % 7 + 2 * Math.floor(i / 7)) % 6; c.special = ''; });
      [0, 1, 2, 3].forEach(i => s.board[i].kind = 0);
      const made = Marjakori.specialFor(s.board, null);
      return [made.t, made.place, made.vertical];
    }""")
    assert result == ["puuska", 0, False]
    assert page.errors == []


def test_real_swipe_plays_and_keeps_a_round_on_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("window.boardBox && state && state.phase === 'play'")
    start_moves = page.evaluate("state.moves")
    pair = page.evaluate("Marjakori.legalMoves(state)[0]")
    box = page.evaluate("boardBox")
    def centre(i):
        return {"x": box["x"] + (i % 7 + .5) * box["size"], "y": box["y"] + (i // 7 + .5) * box["size"]}
    a, b = centre(pair[0]), centre(pair[1])
    page.mouse.move(a["x"], a["y"]); page.mouse.down(); page.mouse.move(b["x"], b["y"], steps=4); page.mouse.up()
    page.wait_for_function(f"state.moves === {start_moves - 1}")
    expected = page.evaluate("""() => { const pair = Marjakori.legalMoves(state)[0], next = Marjakori.clone(state); Marjakori.trySwap(next, pair[0], pair[1]); return [pair, JSON.stringify(next.board), next.moves]; }""")
    page.reload()
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:marjakori:kierros')).moves") == start_moves - 1
    assert page.evaluate("""(pair) => { const r = Marjakori.trySwap(state, pair[0], pair[1]); return [r.ok, JSON.stringify(state.board), state.moves]; }""", expected[0]) == [True, expected[1], expected[2]]
    assert page.errors == []


def test_active_round_fits_390px_and_landscape(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("window.boardBox && state && state.phase === 'play'")
    turn(page, {"width": 390, "height": 844})
    page.wait_for_function("boardBox && boardBox.x >= 0 && boardBox.y >= 0 && boardBox.x + boardBox.size * 7 <= innerWidth && boardBox.y + boardBox.size * 7 <= innerHeight")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("boardBox && boardBox.x >= 0 && boardBox.y >= 0 && boardBox.x + boardBox.size * 7 <= innerWidth && boardBox.y + boardBox.size * 7 <= innerHeight")
    assert page.evaluate("[state.phase, state.moves, boardBox.x >= 0, boardBox.y >= 0, boardBox.x + boardBox.size * 7 <= innerWidth, boardBox.y + boardBox.size * 7 <= innerHeight]") == ["play", 20, True, True, True, True]
    assert page.errors == []


def test_portrait_lists_every_goal_and_long_level_picker_scrolls(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      window.marjakoriText = []; const fill = ctx.fillText.bind(ctx);
      ctx.fillText = function (text) { window.marjakoriText.push(String(text)); return fill.apply(ctx, arguments); };
      start(8);
    }""")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("window.marjakoriText.some(t => t.startsWith('Kerää ')) && state.goals.length === 3 && state.mossLeft > 0")
    shown = page.evaluate("[state.goals.length, state.mossLeft, window.marjakoriText.filter(t => t.startsWith('Kerää ')).slice(-3).length, window.marjakoriText.some(t => t.startsWith('Puhdista sammal:')), boardBox.y, boardBox.y + boardBox.size * 7 <= innerHeight]")
    assert shown[:4] == [3, 1, 3, True]
    assert shown[4] >= 132 and shown[5]
    page.evaluate("localStorage.setItem('ai-pelit:marjakori:taso', '40')")
    page.reload()
    page.wait_for_function("levels.children.length === 40")
    page.evaluate("levels.scrollTop = levels.scrollHeight")
    assert page.evaluate("() => { const last = levels.lastElementChild.getBoundingClientRect(), box = levels.getBoundingClientRect(); return [levels.scrollHeight > levels.clientHeight, last.bottom <= box.bottom + 1, last.top >= box.top - 1]; }") == [True, True, True]
    turn(page, {"width": 740, "height": 360})
    page.evaluate("levels.scrollTop = levels.scrollHeight")
    assert page.evaluate("() => { const last = levels.lastElementChild.getBoundingClientRect(), box = levels.getBoundingClientRect(); return [last.bottom <= box.bottom + 1, last.top >= box.top - 1]; }") == [True, True]
    assert page.errors == []


def test_points_cap_at_five_times_and_a_stuck_board_shuffles(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const scores = [0, 1, 4, 8].map(wave => Marjakori.wavePoints([
        { cells: [0, 1, 2] }, { cells: [7, 14, 21, 28] }, { cells: [3, 10, 17, 24, 31] }
      ], wave));
      let stuck = null, seed = 1, s = Marjakori.newLevel(1, 1);
      while (!stuck && seed < 50000) {
        let random = seed++ >>> 0;
        s.board.forEach(c => { random = (Math.imul(random, 1664525) + 1013904223) >>> 0; c.kind = random % 6; c.special = ''; });
        if (!Marjakori.matched(s.board).size && !Marjakori.hasMove(s.board)) stuck = s;
      }
      const shuffled = stuck ? Marjakori.shuffle(stuck) : false;
      return [scores, !!stuck, shuffled, stuck && !Marjakori.matched(stuck.board).size, stuck && Marjakori.hasMove(stuck.board)];
    }""")
    assert result == [[190, 380, 950, 950], True, True, True, True]
    assert page.errors == []


def test_taps_persist_wins_and_allow_a_clean_next_round(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("window.boardBox && state && state.phase === 'play'")
    pair, box, moves = page.evaluate("[Marjakori.legalMoves(state)[0], boardBox, state.moves]")
    def centre(i):
        return {"x": box["x"] + (i % 7 + .5) * box["size"], "y": box["y"] + (i // 7 + .5) * box["size"]}
    a, b = centre(pair[0]), centre(pair[1])
    page.mouse.click(a["x"], a["y"]); page.mouse.click(b["x"], b["y"])
    page.wait_for_function(f"state.moves === {moves - 1}")
    saved = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:marjakori:kierros')).moves")
    won = page.evaluate("""() => {
      let sent = null; AiPelitScores.submit = n => { sent = n; };
      state.score = 123; state.phase = 'win'; finish();
      const after = [JSON.parse(localStorage.getItem('ai-pelit:marjakori:taso')), JSON.parse(localStorage.getItem('ai-pelit:marjakori:parhaat'))['1'], sent, go.textContent];
      go.click(); return [after, state.level, state.phase, state.score];
    }""")
    assert saved == moves - 1
    assert won == [[2, 123, 123, "Seuraava taso"], 2, "play", 0]
    assert page.errors == []


def test_a_loaded_page_can_play_offline(site, context):
    page = open_game(site, context)
    context.set_offline(True)
    page.click("#go")
    page.wait_for_function("state && state.phase === 'play'")
    assert page.evaluate("""() => { const pair = Marjakori.legalMoves(state)[0], moves = state.moves; return [Marjakori.trySwap(state, pair[0], pair[1]).ok, state.moves === moves - 1]; }""") == [True, True]
    context.set_offline(False)
    assert page.errors == []
