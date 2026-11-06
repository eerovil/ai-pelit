import shutil

import pytest

from conftest import ROOT, turn

URL = "games/marjakori/v2/"


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
      const alone = base(); alone.board[0].special = 'puuska'; const before = JSON.stringify(alone.board), left = alone.moves, rejected = Marjakori.trySwap(alone, 0, 1);
      const mixed = base(); [0, 7, 14].forEach(i => mixed.board[i].kind = 0); [3, 10, 17, 24].forEach(i => mixed.board[i].kind = 1); const made = Marjakori.specialFor(mixed.board, 0);
      const caught = base(); [0, 1, 2, 3, 4, 5, 6].forEach((i, k) => caught.board[i].kind = [0, 0, 0, 1, 0, 2, 3][k]); caught.board[4].special = 'puuska'; caught.board[4].vertical = true; const hit = Marjakori.trySwap(caught, 3, 4);
      return [four.board.some(c => c.special === 'puuska'), five.board.some(c => c.special === 'kimallus'), Marjakori.runs(cross.board).length, pair.ok, both.moves === moves - 1, both.score > 0, rejected.ok, alone.moves === left, JSON.stringify(alone.board) === before, made.t, made.place, hit.ok, caught.score > 60];
    }""")
    assert result == [True, True, 2, True, True, True, False, True, True, "puuska", 3, True, True]
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
      [0, 7, 14].forEach(i => s.board[i].kind = 5);
      [21, 28].forEach(i => s.board[i].kind = 0);
      let fills = [0, 0, 0, .21, .41, .61, .81], fill = 0;
      s.random = () => fills[fill++] ?? .37;
      Marjakori.resolve(s, 0);
      return s.board.filter(c => c.special).map(c => c.special);
    }""")
    assert result == ["kimallus"]
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
    page.evaluate("start(10)")
    page.wait_for_function("state && state.level === 10 && state.phase === 'play'")
    pair, box, moves = page.evaluate("[Marjakori.legalMoves(state)[0], boardBox, state.moves]")
    def centre(i):
        return {"x": box["x"] + (i % 7 + .5) * box["size"], "y": box["y"] + (i // 7 + .5) * box["size"]}
    a, b = centre(pair[0]), centre(pair[1])
    page.mouse.move(a["x"], a["y"]); page.mouse.down(); page.mouse.move(b["x"], b["y"], steps=3); page.mouse.up()
    page.wait_for_function(f"state.moves === {moves - 1}")
    page.wait_for_timeout(500)
    pair, box, moves = page.evaluate("[Marjakori.legalMoves(state)[0], boardBox, state.moves]")
    a, b = centre(pair[0]), centre(pair[1])
    page.mouse.click(a["x"], a["y"]); page.mouse.click(b["x"], b["y"])
    page.wait_for_function(f"state.moves === {moves - 1}")
    assert page.evaluate("[state.phase, state.moves, boardBox.x >= 0, boardBox.y >= 0, boardBox.x + boardBox.size * 7 <= innerWidth, boardBox.y + boardBox.size * 7 <= innerHeight]") == ["play", 14, True, True, True, True]
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


def test_idle_hint_finds_a_move_once_until_the_board_changes(site, context):
    page = open_game(site, context)
    page.evaluate("start(2)")
    page.wait_for_function("state && state.phase === 'play'")
    page.evaluate("""() => {
      window.hintCalls = 0; const legal = Marjakori.legalMoves;
      Marjakori.legalMoves = function () { window.hintCalls++; return legal.apply(this, arguments); };
      hintMove = null; lastAction = 0; ask();
    }""")
    page.wait_for_timeout(150)
    assert page.evaluate("window.hintCalls") == 1
    assert page.errors == []


def test_last_move_animates_before_menu_and_safe_insets_keep_everything_visible(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.wait_for_function("state && state.phase === 'play'")
    immediate = page.evaluate("""() => {
      let sent = null; AiPelitScores.submit = value => { sent = value; };
      state.goals.forEach(g => g.left = 0); state.mossLeft = 0;
      const move = Marjakori.legalMoves(state)[0]; play(move[0], move[1]);
      const best = JSON.parse(localStorage.getItem('ai-pelit:marjakori:parhaat'));
      return [state.phase, !!motion, menu.classList.contains('hidden'), JSON.parse(localStorage.getItem('ai-pelit:marjakori:taso')) === 2, best['1'] === state.score, sent === state.score];
    }""")
    assert immediate == ["win", True, True, True, True, True]
    page.reload()
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:marjakori:taso'))") == 2
    page.evaluate("start(2)")
    page.wait_for_function("state && state.phase === 'play'")
    page.evaluate("""() => { const root = document.documentElement.style; root.setProperty('--safe-top','21px'); root.setProperty('--safe-right','17px'); root.setProperty('--safe-bottom','19px'); root.setProperty('--safe-left','13px'); resize(); }""")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("boardBox && boardBox.x >= safe.left && boardBox.y >= safe.top && boardBox.x + boardBox.size * 7 <= innerWidth - safe.right && boardBox.y + boardBox.size * 7 <= innerHeight - safe.bottom")
    assert page.evaluate("[boardBox.x >= safe.left, boardBox.y >= safe.top, boardBox.x + boardBox.size * 7 <= innerWidth - safe.right, boardBox.y + boardBox.size * 7 <= innerHeight - safe.bottom]") == [True, True, True, True]
    assert page.evaluate("""() => { const a = document.querySelector('#ai-pelit-tulokset-nappi').getBoundingClientRect(), b = {left:boardBox.x,top:boardBox.y,right:boardBox.x+boardBox.size*7,bottom:boardBox.y+boardBox.size*7}; return a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom; }""")
    assert page.errors == []


def test_puuska_symbols_show_their_actual_direction(site, context):
    page = open_game(site, context)
    arrows = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 2), seen = [], text = ctx.fillText.bind(ctx);
      ctx.fillText = function (value) { seen.push(String(value)); return text.apply(ctx, arguments); };
      s.board[0].special = 'puuska'; s.board[0].vertical = true;
      s.board[1].special = 'puuska'; s.board[1].vertical = false;
      MarjakoriPiirto.draw(ctx, s, {x:0,y:0,w:280,h:280}, -1); ctx.fillText = text;
      return seen.filter(v => v === '↕' || v === '↔');
    }""")
    assert arrows == ["↕", "↔"]
    assert page.errors == []


def test_points_cap_at_five_times_and_a_stuck_board_shuffles(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const scores = [0, 1, 4, 8].map(wave => Marjakori.wavePoints([
        { cells: [0, 1, 2] }, { cells: [7, 14, 21, 28] }, { cells: [3, 10, 17, 24, 31] }
      ], wave));
      const cross = Marjakori.wavePoints([{ cells: [0, 1, 2] }, { cells: [1, 8, 15] }], 0);
      const bridge = Marjakori.wavePoints([{ cells: [0, 1, 2] }, { cells: [14, 15, 16] }, { cells: [0, 7, 14] }], 0);
      let stuck = null, seed = 1, s = Marjakori.newLevel(1, 1);
      while (!stuck && seed < 50000) {
        let random = seed++ >>> 0;
        s.board.forEach(c => { random = (Math.imul(random, 1664525) + 1013904223) >>> 0; c.kind = random % 6; c.special = ''; });
        if (!Marjakori.matched(s.board).size && !Marjakori.hasMove(s.board)) stuck = s;
      }
      const shuffled = stuck ? Marjakori.shuffle(stuck) : false;
      return [scores, cross, bridge, !!stuck, shuffled, stuck && !Marjakori.matched(stuck.board).size, stuck && Marjakori.hasMove(stuck.board)];
    }""")
    assert result == [[190, 380, 950, 950], 100, 100, True, True, True, True]
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
          const after = [JSON.parse(localStorage.getItem('ai-pelit:marjakori:taso')) === 2, JSON.parse(localStorage.getItem('ai-pelit:marjakori:parhaat'))['1'] >= 123, sent === null || sent >= 123, go.textContent];
      go.click(); return [after, state.level, state.phase, state.score];
    }""")
    assert saved == moves - 1
    assert won == [[True, True, True, "Seuraava taso"], 2, "play", 0]
    assert page.errors == []


def test_a_loaded_page_can_play_offline(site, context):
    page = open_game(site, context)
    context.set_offline(True)
    page.click("#go")
    page.wait_for_function("state && state.phase === 'play'")
    assert page.evaluate("""() => { const pair = Marjakori.legalMoves(state)[0], moves = state.moves; return [Marjakori.trySwap(state, pair[0], pair[1]).ok, state.moves === moves - 1]; }""") == [True, True]
    context.set_offline(False)
    assert page.errors == []


def test_one_swap_making_five_and_three_puts_kimallus_in_the_five(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const s = Marjakori.newLevel(1, 4);
      s.board.forEach((c, i) => Object.assign(c, { kind: (i % 7 + 2 * Math.floor(i / 7)) % 7, special: '' }));
      [9, 16, 30, 37, 24].forEach(i => s.board[i].kind = 7);
      [17, 23, 31].forEach(i => s.board[i].kind = 8);
      const before = Marjakori.matched(s.board).size;
      const r = Marjakori.trySwap(s, 23, 24);
      const first = s.events[0];
      return [before, r.ok, first.moves.some(m => m.from === 9 && m.to === 37),
              first.board.map((c, i) => c.special === 'kimallus' ? i : -1).filter(i => i >= 0)];
    }""")
    assert result == [0, True, True, [37]]
    assert page.errors == []


def test_a_lone_puuska_with_no_match_is_a_stuck_board(site, context):
    page = open_game(site, context)
    result = page.evaluate("""() => {
      const rows = ['0123450', '2345012', '4501234'];
      const s = Marjakori.newLevel(1, 1);
      s.board.forEach((c, i) => Object.assign(c, { kind: +rows[Math.floor(i / 7) % 3][i % 7], special: '' }));
      s.board[0].special = 'puuska';
      const stuck = [Marjakori.matched(s.board).size, Marjakori.legalMoves(s).length, Marjakori.hasMove(s.board)];
      s.board[0].special = 'kimallus';
      const kimallus = [Marjakori.hasMove(s.board), Marjakori.legalMoves(s).length > 0];
      s.board[0].special = 'puuska';
      Marjakori.shuffle(s);
      return [stuck, kimallus, Marjakori.matched(s.board).size, Marjakori.hasMove(s.board)];
    }""")
    assert result == [[0, 0, False], [True, True], 0, True]
    assert page.errors == []


WIN_NOW = """() => {
  state.goals.forEach(g => g.left = 0); state.mossLeft = 0;
  const move = Marjakori.legalMoves(state)[0]; play(move[0], move[1]);
  return [state.score, !!motion, !!document.querySelector('#ai-pelit-tulokset'),
          JSON.parse(localStorage.getItem('ai-pelit:_tulokset:jono') || '{}')['marjakori|main'] !== undefined,
          localStorage.getItem('ai-pelit:_pelaaja:kysytty')];
}"""
MENU_UP = "state.phase === 'win' && !motion && !menu.classList.contains('hidden')"
ASKED = "JSON.parse(localStorage.getItem('ai-pelit:_pelaaja:kysytty'))"


def start_level(page, n):
    page.evaluate(f"start({n})")
    page.wait_for_function("state && state.phase === 'play' && !motion")


def test_nickname_is_asked_once_after_the_winning_animation(site, context):
    page = open_game(site, context)
    # Looking at the list is not the question: it stays owed.
    page.evaluate("AiPelitScores.open()")
    page.wait_for_selector("#ai-pelit-tulokset")
    assert page.evaluate(ASKED) is None
    page.click("#ai-pelit-tulokset button:text-is('Sulje')")

    start_level(page, 1)
    first = page.evaluate(WIN_NOW)
    assert first[1:] == [True, False, True, None]  # queued at once, nothing covers the fall
    page.wait_for_function(MENU_UP)
    page.wait_for_selector("#ai-pelit-nimi")
    assert page.evaluate(ASKED) is True
    page.click("#ai-pelit-tulokset button:text-is('Sulje')")

    start_level(page, 2)
    page.evaluate(WIN_NOW)
    page.wait_for_function(MENU_UP)
    assert page.evaluate("!!document.querySelector('#ai-pelit-tulokset')") is False
    assert page.errors == []


def test_a_page_closed_during_the_winning_animation_still_owes_the_question(site, context):
    page = open_game(site, context)
    start_level(page, 1)
    assert page.evaluate(WIN_NOW)[1:] == [True, False, True, None]
    page.reload()
    assert page.evaluate(ASKED) is None
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:marjakori:taso'))") == 2
    start_level(page, 2)
    page.evaluate(WIN_NOW)
    page.wait_for_function(MENU_UP)
    page.wait_for_selector("#ai-pelit-nimi")
    assert page.errors == []


COUNT_DRAWS = """() => {
  window.draws = 0; const real = draw;
  draw = () => { window.draws++; real(); };
}"""
HINT_UP = "!hint.classList.contains('hidden')"


def settle(page):
    page.wait_for_function(
        "new Promise(done => requestAnimationFrame(() => requestAnimationFrame(() => done(true))))"
    )


def centre(page, i):
    box = page.evaluate("boardBox")
    return box["x"] + (i % 7 + .5) * box["size"], box["y"] + (i // 7 + .5) * box["size"]


def pixels(page):
    return page.evaluate("c.toDataURL()")


def start_quiet(page, width=360, height=740):
    page.set_viewport_size({"width": width, "height": height})
    start_level(page, 2)
    settle(page)


@pytest.mark.parametrize("width,height", [(360, 740), (390, 844), (740, 360)])
def test_a_menu_nobody_touches_draws_nothing(site, context, width, height):
    page = open_game(site, context)
    page.set_viewport_size({"width": width, "height": height})
    settle(page)
    page.evaluate(COUNT_DRAWS)
    page.wait_for_timeout(600)
    assert page.evaluate("draws") == 0
    assert page.errors == []


def test_a_menu_over_a_saved_round_shows_the_board_and_draws_no_more(site, context):
    page = open_game(site, context)
    start_quiet(page)
    page.reload()
    page.wait_for_function("window.boardBox && state && state.phase === 'play'")
    settle(page)
    page.evaluate(COUNT_DRAWS)
    # Past the hint's five seconds: the menu covers the board, so no hint and no timer wakes it.
    page.evaluate("lastAction = 0")
    page.wait_for_timeout(600)
    assert page.evaluate("[draws, hint.classList.contains('hidden')]") == [0, True]
    page.click("#go")
    page.wait_for_function(HINT_UP)
    assert page.errors == []


@pytest.mark.parametrize("width,height", [(360, 740), (390, 844), (740, 360)])
def test_a_level_nobody_touches_draws_nothing_before_or_during_the_hint(site, context, width, height):
    page = open_game(site, context)
    start_quiet(page, width, height)
    page.evaluate(COUNT_DRAWS)
    page.wait_for_timeout(600)
    assert page.evaluate("draws") == 0
    # The timer draws once as the five seconds end, then the hint moves by itself.
    page.evaluate("lastAction = Date.now() - 4800; ask()")
    page.wait_for_function(HINT_UP)
    settle(page)
    page.evaluate("draws = 0")
    seen = page.evaluate("""async () => {
      const seen = new Set();
      for (let i = 0; i < 12; i++) {
        seen.add(new DOMMatrix(getComputedStyle(hint).transform).m41.toFixed(1));
        await new Promise(done => setTimeout(done, 50));
      }
      return seen.size;
    }""")
    assert seen > 3
    assert page.evaluate("draws") == 0
    assert page.errors == []


def test_the_hint_marks_the_cell_it_names_and_never_takes_a_swipe(site, context):
    page = open_game(site, context)
    start_quiet(page)
    page.evaluate("lastAction = 0; ask()")
    page.wait_for_function(HINT_UP)
    box = page.evaluate("""() => {
      hint.style.animation = 'none';
      const r = hint.getBoundingClientRect(), i = hintMove[0];
      return [r.left - boardBox.x - (i % 7) * boardBox.size, r.top - boardBox.y - Math.floor(i / 7) * boardBox.size, r.width - boardBox.size, r.height - boardBox.size];
    }""")
    assert [round(n, 1) for n in box] == [2.5, 2.5, -5, -5]
    a, b, moves = page.evaluate("[hintMove[0], hintMove[1], state.moves]")
    ax, ay = centre(page, a)
    bx, by = centre(page, b)
    page.mouse.move(ax, ay); page.mouse.down(); page.mouse.move(bx, by, steps=4); page.mouse.up()
    page.wait_for_function(f"state.moves === {moves - 1}")
    assert page.evaluate("hint.classList.contains('hidden')") is True
    page.wait_for_function("!motion")
    assert page.evaluate("hint.classList.contains('hidden')") is True
    assert page.errors == []


def test_a_tap_shows_at_once_and_a_swap_animates_to_its_end_then_stops(site, context):
    page = open_game(site, context)
    start_quiet(page)
    still = pixels(page)
    page.evaluate(COUNT_DRAWS)
    pair = page.evaluate("Marjakori.legalMoves(state)[0]")
    page.mouse.click(*centre(page, pair[0]))
    settle(page)
    assert page.evaluate("selected") == pair[0]
    assert pixels(page) != still
    # The first tap also asks for full screen, which adds a draw of its own: count the next one.
    page.evaluate("draws = 0")
    page.mouse.click(*centre(page, pair[0]))
    settle(page)
    assert page.evaluate("[selected, draws]") == [-1, 1]
    assert pixels(page) == still
    page.mouse.click(*centre(page, pair[0]))
    moves = page.evaluate("state.moves")
    page.mouse.click(*centre(page, pair[1]))
    page.wait_for_function(f"state.moves === {moves - 1} && !motion")
    settle(page)
    assert page.evaluate("draws") > 10
    final = pixels(page)
    page.evaluate("draws = 0")
    page.wait_for_timeout(300)
    assert page.evaluate("draws") == 0
    page.evaluate("draw()")
    assert pixels(page) == final
    assert page.errors == []


def test_a_refused_swap_slides_back_and_stops(site, context):
    page = open_game(site, context)
    start_quiet(page)
    still = pixels(page)
    page.evaluate(COUNT_DRAWS)
    page.evaluate("""() => {
      for (let a = 0; a < 48; a++) {
        const next = Marjakori.clone(state);
        if ((a + 1) % 7 && !Marjakori.trySwap(next, a, a + 1).ok) { play(a, a + 1); return; }
      }
    }""")
    page.wait_for_function("draws > 3 && !motion")
    settle(page)
    assert pixels(page) == still
    page.evaluate("draws = 0")
    page.wait_for_timeout(300)
    assert page.evaluate("draws") == 0
    assert page.errors == []


def test_turning_the_phone_redraws_in_the_same_moment_and_keeps_the_round(site, context):
    page = open_game(site, context)
    start_quiet(page)
    board = page.evaluate("JSON.stringify(state.board)")
    page.evaluate("lastAction = 0; ask()")
    page.wait_for_function(HINT_UP)
    before = page.evaluate("hint.style.left")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function(f"hint.style.left !== '{before}'")
    assert page.evaluate("""() => {
      const blank = document.createElement('canvas'); blank.width = c.width; blank.height = c.height;
      return [W, H, c.toDataURL() === blank.toDataURL(), JSON.stringify(state.board)];
    }""") == [740, 360, False, board]
    # A new size fills the canvas in the same call, before the browser can show it empty.
    assert page.evaluate("""() => {
      c.style.width = '700px'; resize();
      const blank = document.createElement('canvas'); blank.width = c.width; blank.height = c.height;
      const empty = c.toDataURL() === blank.toDataURL(); c.style.width = ''; return empty;
    }""") is False
    assert page.errors == []


def test_coming_back_to_the_page_draws_the_board_again(site, context):
    page = open_game(site, context)
    start_quiet(page)
    still = pixels(page)
    page.evaluate(COUNT_DRAWS)
    # A phone may drop a canvas while the page is away: it must come back drawn.
    page.evaluate("ctx.clearRect(0, 0, W, H); document.dispatchEvent(new Event('visibilitychange'))")
    settle(page)
    assert page.evaluate("draws") == 1
    assert pixels(page) == still
    assert page.errors == []
