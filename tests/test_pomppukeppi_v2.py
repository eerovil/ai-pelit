"""Pomppukeppi v2 (#482): hares on pogo sticks paint a tile board, alone against the computer."""
import json
import shutil

import pytest

from conftest import ROOT, turn

URL = "games/pomppukeppi/v2/"
KEY = "ai-pelit:pomppukeppi:"
TOUCH = """([t, x, y]) => document.getElementById('c').dispatchEvent(new PointerEvent(t,
  { pointerId: 9, clientX: x, clientY: y, bubbles: true, pointerType: 'touch' }))"""
# The erä ends now with my hare far ahead.
WIN_ERA = "() => { world.ph = 'play'; world.t = ERA_T; me.pts = 30; step(world, 0.01); }"
# A world in the page with nothing else going on: no computer moves, no boxes.
QUIET = "() => { brains = brains.map(() => null); world.hares.forEach(h => { h.want = -1; }); world.cashT = 99; world.qT = 99; }"


def open_game(site, context, width=360, height=740, saves=None):
    if not (site.games / "pomppukeppi").exists():
        shutil.copytree(ROOT / "games" / "pomppukeppi", site.games / "pomppukeppi")
        site.build()
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": height})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    if saves:
        page.add_init_script("(() => { const s = " + json.dumps(saves) + "; for (const k in s) localStorage.setItem('" + KEY + "' + k, s[k]); })()")
    page.goto(site.url + URL)
    page.wait_for_function("V3 || no3d", timeout=20000)
    return page


def go(page):
    page.click("#go")
    page.wait_for_function("mode === 'play' && world.ph === 'play'", timeout=8000)
    page.evaluate(QUIET)


def saved(page, k):
    v = page.evaluate(f"localStorage.getItem('{KEY}{k}')")
    return None if v is None else json.loads(v)


def test_the_menu_opens_the_first_board_only(site, context):
    page = open_game(site, context)
    assert page.evaluate("!!V3")
    boards = page.locator("#boards button")
    assert boards.count() == 3
    assert [boards.nth(i).is_disabled() for i in range(3)] == [False, True, True]
    assert "🔒" in boards.nth(1).inner_text()
    assert page.locator("#friends").is_visible()
    # The colour button goes round the four colours, and is kept.
    page.click("#col")
    assert "Sininen" in page.locator("#col").inner_text()
    assert saved(page, "vari") == 1
    assert page.errors == []


def test_the_stick_hops_my_hare_and_a_flick_waits_for_the_landing(site, context):
    page = open_game(site, context)
    go(page)
    assert page.evaluate("[me.x, me.y]") == [0, 0]
    # Held to the right: the hare hops right, one square a hop.
    page.evaluate(TOUCH, ["pointerdown", 150, 500])
    page.evaluate(TOUCH, ["pointermove", 210, 505])
    assert page.evaluate("myWant()") == 0
    page.wait_for_function("me.x >= 2", timeout=3000)
    assert page.evaluate("me.y") == 0
    # Its squares are painted its colour.
    assert page.evaluate("[tileAt(world, 0, 0), tileAt(world, 1, 0)]") == [0, 0]
    # A quick flick down, let go in mid-air: the next landing still hops down.
    page.evaluate(TOUCH, ["pointerup", 210, 505])
    page.evaluate("() => { me.p = 0.3; }")
    page.evaluate(TOUCH, ["pointerdown", 150, 500])
    page.evaluate(TOUCH, ["pointermove", 152, 560])
    page.evaluate(TOUCH, ["pointerup", 152, 560])
    y0 = page.evaluate("me.y")
    assert page.evaluate("myWant()") == 1
    page.wait_for_function(f"me.y === {y0} + 1", timeout=2000)
    # Used once: with no finger, it then bounces in place.
    page.wait_for_function("me.p < 0.5 && flick === -1", timeout=2000)
    x, y = page.evaluate("[me.x, me.y]")
    page.wait_for_timeout(800)
    assert page.evaluate("[me.x, me.y]") == [x, y]
    assert page.errors == []


def test_a_cash_in_turns_squares_into_points_and_clears_them(site, context):
    page = open_game(site, context)
    go(page)
    got = page.evaluate("""() => {
      for (let x = 0; x < 5; x++) world.tiles[x] = 0;
      world.cash = { x: 1, y: 1 };
      Object.assign(me, { fx: 1, fy: 0, x: 1, y: 1, p: 0.99 });
      step(world, 0.05);
      return [me.pts, me.cashN, world.cash, ownCount(world, me), world.cashT];
    }""")
    # Five painted and the box's own square: six points, the board clean, a new box in 3 s.
    assert got == [6, 1, None, 0, 3]
    page.wait_for_function("world.cash !== null", timeout=5000)
    assert page.errors == []


def test_a_square_two_hares_hop_for_goes_to_the_one_with_fewer_points(site, context):
    page = open_game(site, context)
    go(page)
    got = page.evaluate("""() => {
      const [a, b] = [world.hares[1], world.hares[2]];
      world.hares.forEach((h, i) => Object.assign(h, { x: 7, y: i, fx: 7, fy: i, p: 0.5 }));
      Object.assign(a, { x: 2, y: 3, fx: 2, fy: 3, p: 0.99, pts: 9, want: 0 });
      Object.assign(b, { x: 4, y: 3, fx: 4, fy: 3, p: 0.99, pts: 2, want: 2 });
      step(world, 0.05);
      return [[a.x, a.bumpN], [b.x, b.bumpN]];
    }""")
    assert got[1][0] == 3          # the one behind got it
    assert got[0][0] == 2          # the leader bounced in place
    assert got[0][1] == 1
    assert page.errors == []


def test_a_closed_ring_fills_on_aitaus(site, context):
    page = open_game(site, context, saves={"auki": "3", "kentta": "3"})
    go(page)
    assert page.evaluate("world.board") == 3
    got = page.evaluate("""() => {
      world.hares.forEach((h, i) => Object.assign(h, { x: 8, y: 8 - i, fx: 8, fy: 8 - i }));
      // An L from the left edge to the top edge round the top-left 2 x 2 corner, one square short.
      for (const [x, y] of [[0, 2], [1, 2], [2, 2], [2, 1]]) world.tiles[y * 9 + x] = 0;
      Object.assign(me, { fx: 2, fy: 1, x: 2, y: 0, p: 0.99, want: -1 });
      step(world, 0.05);
      return [[0, 0], [1, 0], [0, 1], [1, 1], [3, 3]].map(([x, y]) => tileAt(world, x, y));
    }""")
    assert got == [0, 0, 0, 0, -1]
    assert page.errors == []


def test_a_snowball_stuns_the_leader_and_a_spring_makes_hops_quick(site, context):
    page = open_game(site, context)
    go(page)
    got = page.evaluate("""() => {
      const lead = world.hares[2];
      lead.pts = 12;
      world.rand = () => 0.1;   // the snowball
      world.qbox = { x: 1, y: 0, life: 5 };
      Object.assign(me, { fx: 0, fy: 0, x: 1, y: 0, p: 0.99 });
      step(world, 0.05);
      const a = [me.gotK, lead.stun > 1];
      world.rand = () => 0.9;   // the spring
      world.qbox = { x: 2, y: 0, life: 5 };
      Object.assign(me, { fx: 1, fy: 0, x: 2, y: 0, p: 0.99, want: 0 });
      step(world, 0.05);
      return a.concat([me.gotK, me.fast > 4, me.hopT]);
    }""")
    assert got == ["lumi", True, "jousi", True, 0.2]
    # A stunned hare bounces in place.
    page.evaluate("() => { const l = world.hares[2]; l.want = 2; l.p = 0.99; }")
    x = page.evaluate("world.hares[2].x")
    page.wait_for_timeout(500)
    assert page.evaluate("world.hares[2].x") == x
    assert page.errors == []


def test_a_tie_replays_the_era(site, context):
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { world.hares[1].pts = 5; me.pts = 5; world.t = ERA_T; step(world, 0.01); }")
    assert page.evaluate("[world.ph, world.eraWin, me.wins, world.hares[1].wins]") == ["erä", None, 0, 0]
    page.wait_for_function("world.era === 2 && world.ph === 'count'", timeout=6000)
    assert page.evaluate("world.hares.map(h => h.pts)") == [0, 0, 0, 0]
    assert page.errors == []


def test_a_match_alone_saves_between_eras_and_its_end_opens_the_next_board(site, context):
    page = open_game(site, context)
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    go(page)
    # Saved at the start, never mid-erä.
    assert saved(page, "kesken1") == {"b": 1, "era": 1, "wins": [0, 0, 0, 0], "best": [0, 0, 0, 0]}
    page.evaluate(WIN_ERA)
    page.wait_for_function(f"localStorage.getItem('{KEY}kesken1').includes('\"era\":2')", timeout=3000)
    assert saved(page, "kesken1")["wins"] == [1, 0, 0, 0]
    # A reload goes on with the match, in the next erä.
    page.reload()
    page.wait_for_function("mode === 'play' && world", timeout=10000)
    assert page.evaluate("[world.era, me.wins, me.best]") == [2, 1, 30]
    page.evaluate("() => { window.sent = []; AiPelitScores.submit = s => { sent.push(s); }; }")
    page.wait_for_function("world.ph === 'play'", timeout=6000)
    page.evaluate("() => { brains = brains.map(() => null); }")
    page.evaluate("() => { world.ph = 'play'; world.t = ERA_T; me.pts = 41; step(world, 0.01); }")
    # The deciding erä: the board opened, the record, the save gone and the score sent, at once.
    page.wait_for_function("result !== null", timeout=2000)
    assert saved(page, "auki") == 2
    assert saved(page, "ennatys") == {"1": 41}
    assert saved(page, "kesken1") is None
    assert page.evaluate("sent") == [41]
    page.wait_for_function("mode === 'end'", timeout=6000)
    assert page.locator("#endTitle").inner_text() == "Voitit ottelun!"
    assert "Kivikko aukesi" in page.locator("#endOpen").inner_text()
    assert "uusi ennätys" in page.locator("#endNote").inner_text()
    page.click("#toMenu")
    assert page.locator("#boards button").nth(1).is_enabled()
    assert page.errors == []


def test_a_finished_or_broken_saved_match_is_dropped(site, context):
    page = open_game(site, context, saves={"kesken1": json.dumps({"b": 1, "era": 3, "wins": [2, 1, 0, 0], "best": [9, 9, 0, 0]})})
    page.wait_for_function("mode === 'menu'")
    assert saved(page, "kesken1") is None
    page.evaluate(f"localStorage.setItem('{KEY}kesken1', '{{broken')")
    page.reload()
    page.wait_for_function("mode === 'menu'")
    assert saved(page, "kesken1") is None
    assert page.errors == []


def test_the_computer_hares_paint_and_cash_in(site, context):
    page = open_game(site, context)
    got = page.evaluate("""() => {
      const out = [];
      for (const b of [1, 2, 3]) {
        const w = newWorld(b, [0, 1, 2, 3].map(i => ({ id: 'c' + i, name: 'c' + i, kind: 'cpu' })), 11 + b);
        const br = w.hares.map((h, i) => cpuBrain(BOARDS[b - 1].cpu, 5 + i));
        while (w.era === 1 && !w.over) { w.hares.forEach((h, i) => cpuThink(w, h, br[i])); step(w, 1 / 30); }
        out.push(w.hares.map(h => [h.cashN, h.best]));
      }
      return out;
    }""")
    for board in got:
        # A hare may miss every cash-in by chance: on seed 14 of board 3 one does, while 45 other
        # seeds (15 per board) had none that did.
        assert sum(cash >= 1 for cash, _ in board) >= 3, board
        assert max(best for _, best in board) >= 15, board
    assert page.errors == []


def test_sideways_the_menu_fits_and_turning_keeps_the_round(site, context):
    page = open_game(site, context, 740, 360)
    for sel in ("#go", "#friends", "#col"):
        box = page.locator(sel).bounding_box()
        assert box["y"] >= 0 and box["y"] + box["height"] <= 360, sel
    assert page.evaluate("document.scrollingElement.scrollHeight") <= 360
    go(page)
    page.evaluate("() => { me.pts = 7; }")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_timeout(300)
    assert page.evaluate("[mode, me.pts, LAND]") == ["play", 7, False]
    assert page.errors == []


def test_without_3d_the_board_is_drawn_flat(site, context):
    if not (site.games / "pomppukeppi").exists():
        shutil.copytree(ROOT / "games" / "pomppukeppi", site.games / "pomppukeppi")
        site.build()
    context.route("**/three.module.js", lambda r: r.abort())
    page = context.new_page()
    page.set_viewport_size({"width": 360, "height": 740})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("no3d", timeout=10000)
    go(page)
    page.evaluate(TOUCH, ["pointerdown", 150, 500])
    page.evaluate(TOUCH, ["pointermove", 150, 560])
    page.wait_for_function("me.y >= 2", timeout=3000)
    assert page.evaluate("flat && flat.s > 20")
    assert page.errors == []


# One erä in the page's own world: hare 0 played by `mine`, three computer hares on board 1.
ERA_WITH = """(mine) => {
  const w = newWorld(1, [0, 1, 2, 3].map(i => ({ id: 'h' + i, name: 'h' + i, kind: i ? 'cpu' : 'me' })), 7);
  const br = w.hares.map((h, i) => i ? cpuBrain(BOARDS[0].cpu, 3 + i) : null);
  const h0 = w.hares[0];
  let painted = 0, win = null, pts = 0, best = 0;
  while (w.era === 1 && !w.over) {
    w.hares.forEach((h, i) => { if (i) cpuThink(w, h, br[i]); });
    if (mine === 'still') h0.want = -1;
    else {
      // Paint, but never hop onto the cash box: a square of someone else's or a blank one first.
      const ok = [0, 1, 2, 3].filter(d => canHop(w, h0, d) && !(w.cash && w.cash.x === h0.x + DIRS[d][0] && w.cash.y === h0.y + DIRS[d][1]));
      const fresh = ok.filter(d => tileAt(w, h0.x + DIRS[d][0], h0.y + DIRS[d][1]) !== h0.i);
      h0.want = fresh.length ? fresh[0] : ok.length ? ok[(h0.hopN * 7) % ok.length] : -1;
    }
    if (w.ph === 'play') painted = Math.max(painted, ownCount(w, h0));
    step(w, 1 / 30);
    if (w.eraWin && !win) { win = w.eraWin; pts = h0.pts; best = Math.max(...w.hares.slice(1).map(h => h.pts)); }
  }
  return { pts, cash: h0.cashN, painted, win, best };
}"""


def test_standing_still_or_only_painting_loses_the_era(site, context):
    # Spec: neither standing still nor only painting may win.
    page = open_game(site, context)
    still = page.evaluate(ERA_WITH, "still")
    assert still["pts"] == 0 and still["win"] not in (None, "h0") and still["best"] > 0, still
    paint = page.evaluate(ERA_WITH, "paint")
    assert paint["painted"] >= 8 and paint["cash"] == 0 and paint["pts"] == 0, paint
    assert paint["win"] not in (None, "h0"), paint
    assert page.errors == []


def end_screen(page):
    go(page)
    page.evaluate(WIN_ERA)
    page.wait_for_function("world.era === 2 && world.ph === 'play'", timeout=8000)
    page.evaluate(QUIET)
    page.evaluate("() => { world.t = ERA_T; me.pts = 31; step(world, 0.01); }")
    page.wait_for_function("mode === 'end'", timeout=6000)


def fits(page, sels, w, h):
    for sel in sels:
        box = page.locator(sel).bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= w and box["y"] >= 0 and box["y"] + box["height"] <= h, (sel, box)
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h


@pytest.mark.parametrize("size", [(360, 640), (390, 844), (740, 360)])
def test_the_menu_and_the_end_screen_fit_the_screen(site, context, size):
    w, h = size
    page = open_game(site, context, w, h)
    fits(page, ("#go", "#friends", "#col", "#boards"), w, h)
    end_screen(page)
    fits(page, ("#endTitle", "#endList", "#again", "#toMenu"), w, h)
    assert page.errors == []


def test_a_hop_into_a_rock_a_hole_or_off_the_board_bounces_in_place(site, context):
    page = open_game(site, context, saves={"auki": "2", "kentta": "2"})
    go(page)
    assert page.evaluate("world.board") == 2
    # Kivikko: a rock at (2, 2), a hole at (2, 5); right is 0, left 2, up 3.
    got = page.evaluate("""() => [[1, 2, 0], [1, 5, 0], [0, 0, 2], [0, 0, 3]].map(([x, y, d]) => {
      world.hares.forEach((h, i) => { if (h !== me) Object.assign(h, { x: 7, y: 7 - i, fx: 7, fy: 7 - i }); });
      Object.assign(me, { fx: x, fy: y, x, y, p: 0.99, want: d });
      step(world, 0.05);
      return [me.x, me.y, me.fx, me.fy];
    })""")
    assert got == [[1, 2, 1, 2], [1, 5, 1, 5], [0, 0, 0, 0], [0, 0, 0, 0]]
    assert page.evaluate("[tileAt(world, 2, 2), tileAt(world, 2, 5)]") == [-2, -3]
    assert page.errors == []


def test_on_aitaus_a_ring_with_another_hare_inside_does_not_fill(site, context):
    page = open_game(site, context, saves={"auki": "3", "kentta": "3"})
    go(page)
    got = page.evaluate("""() => {
      world.hares.forEach((h, i) => Object.assign(h, { x: 8, y: 8 - i, fx: 8, fy: 8 - i }));
      Object.assign(world.hares.find(h => h !== me), { x: 0, y: 0, fx: 0, fy: 0, p: 0.2, want: -1 });   // inside the corner
      for (const [x, y] of [[0, 2], [1, 2], [2, 2], [2, 1]]) world.tiles[y * 9 + x] = 0;
      Object.assign(me, { fx: 2, fy: 1, x: 2, y: 0, p: 0.99, want: -1 });
      step(world, 0.05);
      return [[0, 0], [1, 0], [0, 1], [1, 1]].map(([x, y]) => tileAt(world, x, y));
    }""")
    # (0,0) is my start square, so it is mine already; the other hare on it keeps the rest blank.
    assert got[1:] == [-1, -1, -1], got
    assert page.errors == []


def test_on_aitaus_a_line_across_the_board_fills_the_bigger_side_the_others_are_not_on(site, context):
    # Review of #487: the biggest area fills too, when no other hare is in it (spec D9).
    page = open_game(site, context, saves={"auki": "3", "kentta": "3"})
    go(page)
    got = page.evaluate("""() => {
      world.hares.forEach((h, i) => { if (h !== me) Object.assign(h, { x: 8, y: i, fx: 8, fy: i }); });
      for (let y = 0; y < 8; y++) world.tiles[y * 9 + 7] = 0;
      Object.assign(me, { fx: 6, fy: 8, x: 7, y: 8, p: 0.99, want: -1 });
      step(world, 0.05);
      return { left: [[0, 0], [3, 3], [6, 8], [0, 8]].map(([x, y]) => tileAt(world, x, y)),
               rock: tileAt(world, 4, 4), right: [0, 4, 8].map(y => tileAt(world, 8, y) === 0) };
    }""")
    assert got == {"left": [0, 0, 0, 0], "rock": -2, "right": [False, False, False]}
    assert page.errors == []


def test_a_swapped_hare_colour_repaints_its_3d_squares(site, context):
    # Review of #487: a room may swap a computer hare's colour with a phone's; painted squares follow.
    page = open_game(site, context)
    go(page)
    page.evaluate("() => { world.tiles[3 * 8 + 3] = 0; }")
    page.wait_for_timeout(200)
    hexes = "() => { const c = new V3.col.constructor(); V3.tiles.getColorAt(3 * 8 + 3, c); return [c.getHexString(), new V3.col.constructor(COLORS[me.col]).getHexString()]; }"
    a = page.evaluate(hexes)
    assert a[0] == a[1]
    page.evaluate("() => { const o = world.hares[1], c = me.col; me.col = o.col; o.col = c; }")
    page.wait_for_timeout(200)
    b = page.evaluate(hexes)
    assert b[0] == b[1] and b[0] != a[0]
    assert page.errors == []
