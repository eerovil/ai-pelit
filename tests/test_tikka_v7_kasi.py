"""Tikanheitto v7 (#400): the throw is harder. The hand shakes, settles for a moment and tires, the
sight leaves the target after each dart, and the harder game has its own bests and lists."""

from conftest import turn
from test_tikka_v7 import RUN, open_plain, room, start

# Plays whole games through the real touch handlers. Each dart holds for `held` seconds; with
# `aimAt` the finger has brought the sight there, without it the finger never moved.
PLAYER = """() => {
  const touch = (type) => c.dispatchEvent(new PointerEvent(type, { pointerId: 7, clientX: 100, clientY: 400, bubbles: true }));
  window.dart = (held, aimAt) => {
    run(() => pause > 0 || flying || banner, 5);
    touch('pointerdown');
    if (aimAt) { aim.x = aimAt.x; aim.y = aimAt.y; }
    // A throw starts at a random moment of the hand's sway, as a person's does.
    wob = Math.random() * 500;
    run(() => hold && hold.t < held, held + 1);
    touch('pointerup');
    run(() => flying, 2);
  };
  window.playGame = (mk, held, aimAt) => {
    document.getElementById(mk).click();
    let score = 0;
    while (phase === 'play') {
      score = players[0].score;
      dart(held, aimAt);
      score = players[0].score;
      run(() => phase === 'play' && (pause > 0 || flying), 5);
    }
    return score;
  };
  window.games = (n, mk, held, aimAt) => Array.from({ length: n }, () => playGame(mk, held, aimAt));
}"""
MIDDLE = "{x: 0, y: 0}"


def play(site, context, saved=None):
    page = open_plain(site, context, saved)
    page.evaluate(PLAYER)
    return page


def mean(xs):
    return sum(xs) / len(xs)


def test_tapping_without_aiming_no_longer_wins(site, context):
    page = play(site, context)
    tap = page.evaluate("games(12, 'go', 0.15, null)")
    steady = page.evaluate(f"games(12, 'go', 1.3, {MIDDLE})")
    assert mean(tap) < 245, tap
    assert mean(steady) > mean(tap) + 25, (tap, steady)
    assert page.errors == []


def test_a_steady_aimed_game_scores_well_but_is_not_perfect(site, context):
    page = play(site, context)
    steady = page.evaluate(f"games(20, 'go', 1.3, {MIDDLE})")
    assert 255 < mean(steady) < 295, steady
    assert max(steady) < 300, steady


def test_letting_go_too_soon_or_too_late_costs_points(site, context):
    page = play(site, context)
    steady = page.evaluate(f"games(12, 'go', 1.3, {MIDDLE})")
    soon = page.evaluate(f"games(12, 'go', 0.3, {MIDDLE})")
    late = page.evaluate(f"games(12, 'go', 3.2, {MIDDLE})")
    assert mean(steady) > mean(soon) + 10, (steady, soon)
    assert mean(steady) > mean(late) + 10, (steady, late)


def test_the_sight_shows_when_the_hand_is_steady(site, context):
    page = play(site, context)
    assert page.evaluate("[0.3, 1.3, 2.5].map(isSteady)") == [False, True, False]
    amps = page.evaluate("[0, 1, 1.5, 3].map(swayAmp)")
    assert amps[0] > 3 * amps[1] and amps[1] == amps[2] and amps[3] > amps[2]


def test_the_sight_leaves_the_target_after_each_dart_and_at_the_start(site, context):
    page = play(site, context)
    page.click("#go")
    start_d = page.evaluate("Math.hypot(aim.x, aim.y)")
    assert 30 <= start_d <= 60
    for _ in range(4):
        moved = page.evaluate(f"""() => {{
            dart(1.3, {MIDDLE});
            run(() => pause > 0 || flying || banner, 5);
            return Math.hypot(aim.x, aim.y);
        }}""")
        assert 30 <= moved <= 60


def test_the_harder_game_has_its_own_bests_and_lists(site, context):
    page = play(site, context, {"mokki": 300, "ennatys": 1350})
    assert page.inner_text("#stats") == ""
    page.evaluate("""() => {
      window.sent = [];
      const board = AiPelitScores.board, submit = AiPelitScores.submit;
      AiPelitScores.board = (id, label) => { window.list = id; return board(id, label); };
      AiPelitScores.submit = sc => { sent.push([window.list, sc]); return submit(sc); };
    }""")
    mokki = page.evaluate(f"playGame('go', 1.3, {MIDDLE})")
    assert page.evaluate("sent") == [["mokki2", mokki]]
    assert "uusi ennätys" in page.inner_text("#result")
    kisa = page.evaluate("playGame('kisa', 1.3, spotOf(20, 3))")
    assert page.evaluate("sent.at(-1)") == ["kisa2", kisa]
    assert page.inner_text("#stats") == f"Ennätykset: Mökkitikka {mokki} p · Pistekisa {kisa} p"
    # The old bests stay as they were.
    assert page.evaluate("[load('mokki', 0), load('ennatys', 0)]") == ["300", "1350"]


def test_a_guests_dart_goes_where_the_sight_was_and_its_sight_then_leaves(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, guest = pages
    start(pages)
    host.evaluate("() => { for (let i = 0; i < 3; i++) { release(0, 0); while (flying) step(1 / 60); } }")
    guest.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    guest.evaluate(RUN)
    guest.evaluate(PLAYER)
    guest.evaluate(f"dart(1.3, {MIDDLE})")
    host.wait_for_function("turnDarts.length === 1", timeout=5000)
    assert 30 <= guest.evaluate("Math.hypot(aim.x, aim.y)") <= 60
    assert 0 < host.evaluate("stuck[0] && Math.hypot(stuck[0].x, stuck[0].y)") < 70
    assert host.errors == [] and guest.errors == []


def test_a_brush_or_a_cancelled_touch_throws_nothing_and_leaves_the_sight(site, context):
    page = play(site, context)
    page.click("#go")
    before = page.evaluate("[aim.x, aim.y, dartsLeft]")
    page.evaluate("dart(0.05, null)")
    assert page.evaluate("[aim.x, aim.y, dartsLeft]") == before
    page.evaluate("""() => {
      c.dispatchEvent(new PointerEvent('pointerdown', { pointerId: 7, clientX: 100, clientY: 400, bubbles: true }));
      run(() => hold && hold.t < 1.3, 2);
      c.dispatchEvent(new PointerEvent('pointercancel', { pointerId: 7, bubbles: true }));
    }""")
    assert page.evaluate("[aim.x, aim.y, dartsLeft]") == before
    assert page.evaluate("hold") is None


def test_two_players_on_one_phone_each_keep_their_own_sight(site, context):
    page = play(site, context, {"vastus": "kaveri"})
    page.click("#go501")
    for who in (0, 1):
        assert page.evaluate("cur") == who
        for _ in range(3):
            page.evaluate("dart(1.3, spotOf(20, 1))")
        left = page.evaluate("[players[cur].aim.x, players[cur].aim.y]")
        assert page.evaluate("[aim.x, aim.y]") == left
        page.evaluate("run(() => pause > 0 || flying, 5)")
    # Back to the first player: their sight is where their hand came back to, not the second's.
    assert page.evaluate("cur") == 0
    assert page.evaluate("aim.x === players[0].aim.x && aim.y === players[0].aim.y")
    assert page.evaluate("aim.x !== players[1].aim.x")


def test_the_computers_sight_keeps_to_a_steady_hand(site, context):
    page = play(site, context, {"vastus": "kova"})
    page.click("#go501")
    page.evaluate("players[1].score = 501; cur = 1; startTurn(); run(() => bot && bot.t < 0.8, 2)")
    assert page.evaluate("bot !== null")
    assert page.evaluate("swayAmp(HAND.settled)") == 28


def test_the_menu_fits_a_wider_phone_and_a_game_goes_on_when_it_turns(site, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True)
    page = play(site, ctx)
    fits = "(() => { const m = document.getElementById('menu'); return m.scrollHeight <= m.clientHeight && m.scrollWidth <= m.clientWidth; })()"
    assert page.evaluate(fits)
    page.click("#go")
    page.evaluate(f"dart(1.3, {MIDDLE})")
    aim = page.evaluate("[aim.x, aim.y, dartsLeft]")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("LAND")
    assert page.evaluate("[aim.x, aim.y, dartsLeft]") == aim
    assert page.evaluate("phase") == "play"
    page.evaluate(f"dart(1.3, {MIDDLE})")
    assert page.evaluate("dartsLeft") == 1
    assert page.errors == []
    ctx.close()
