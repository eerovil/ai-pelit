"""Mölkky v2 (the same game as v1, its tests run on v2): throw the kalikka at twelve numbered pins in a cottage yard, against the computer or 2-6 phones.

The world steps by hand (`run()`), so a whole game plays in a moment; each phone in a room is its
own Chromium context, and the room relay is `Relay` from test_rooms_lib. The yard is drawn with
three.js, so these tests run on the AgentDeck host (scripts/host-tests.sh), not in GitHub CI.
"""

import json

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/molkky/v2/"

# Steps the game by hand, 1/240 s at a time, while cond() holds, at most max seconds of game time.
RUN = "() => { window.run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += DT) update(DT); }; }"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context, first=0):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate(f"turn = {first}; toAim()")
    return page


# Twelve pins in a row across the yard, far enough apart to hit one at a time.
ROW = "() => setUp().map((p, i) => pin(p.n, -1.1 + i * 0.2, 3.5))"


def test_the_menu_starts_a_game_with_the_pins_set_up(site, context):
    page = start(site, context)
    assert page.evaluate("[phase, thrower(), score.join('-'), world.pins.filter(p => p.s === 'up').length]") == ["aim", "me", "0-0", 12]
    # The real setup: 1 and 2 in front, 7 9 8 at the back, 3.5 m from the line.
    assert page.evaluate("world.pins.filter(p => p.y < LINE + 0.01).map(p => p.n).sort()") == [1, 2]
    assert page.evaluate("world.pins.filter(p => p.y > LINE + 0.15).map(p => p.n)") == [7, 9, 8]
    assert page.locator("#menu").is_hidden()
    assert page.errors == []


def test_a_throw_into_the_bunch_knocks_several_over_and_scores_how_many(site, context):
    page = open_game(site, context)
    for st in [0, 1]:
        res = page.evaluate(f"() => {{ const w = simulate(setUp(), {{ x: 0, d: 3.35, st: {st} }}); return [fallen(w.pins).length, pointsOf(w.pins)]; }}")
        assert 3 <= res[0] <= 10 and res[1] == res[0], (st, res)


def test_one_pin_down_scores_its_number(site, context):
    page = open_game(site, context)
    res = page.evaluate(f"""() => {{
      const pins = ({ROW})(), p = pins.find(q => q.n === 9);
      const w = simulate(pins, aimAt(p.x, p.y, p.y - 0.25, 0));
      return [fallen(w.pins).map(q => q.n), pointsOf(w.pins)];
    }}""")
    assert res == [[9], 9]


def test_a_short_throw_or_a_leaning_pin_scores_nothing(site, context):
    page = open_game(site, context)
    assert page.evaluate("pointsOf(simulate(setUp(), { x: 0, d: 2, st: 0 }).pins)") == 0
    # A pin left leaning on another one does not count; one lying does.
    assert page.evaluate("(() => { const ps = setUp(); ps[0].s = 'lean'; ps[5].s = 'down'; return pointsOf(ps); })()") == 5


def test_the_crosswise_throw_is_wider_than_the_upright_one(site, context):
    page = open_game(site, context)
    # Aimed just beside a pin: upright it slides past, crosswise it catches it.
    res = page.evaluate(f"""() => {{
      const pins = ({ROW})(), p = pins.find(q => q.n === 7);
      return [0, 1].map(st => fallen(simulate(pins, aimAt(p.x + 0.07, p.y, p.y - 0.25, st)).pins).map(q => q.n));
    }}""")
    assert res[0] == [] and 7 in res[1]


def test_the_rules_exactly_fifty_over_it_back_to_twentyfive_three_misses_out(site, context):
    page = start(site, context)
    assert page.evaluate("score = [44, 0]; const m = rules(0, 6); [m.win, winner, score[0]]") == [True, 0, 50]
    assert page.evaluate("winner = -1; score = [44, 0]; const m2 = rules(0, 9); [m2.over, winner, score[0]]") == [True, -1, 25]
    # Two misses, then a hit, starts the count again; three in a row and the player is out.
    assert page.evaluate("score = [10, 10]; misses = [2, 0]; rules(0, 3); misses[0]") == 0
    res = page.evaluate("misses = [0, 2]; const m3 = rules(1, 0); [m3.out, outs[1], winner]")
    # Alone against the computer, the other player is then the last one left: they win.
    assert res == [True, True, 0]


def test_fallen_pins_stand_up_where_they_lie_apart_from_each_other(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      const w = simulate(setUp(), { x: 0, d: 3.35, st: 1 });
      const mids = fallen(w.pins).map(p => [p.n, p.x + p.dx * PH / 2, p.y + p.dy * PH / 2]);
      raise(w.pins);
      let near = Infinity;
      for (const a of w.pins) for (const b of w.pins) if (a !== b) near = Math.min(near, Math.hypot(a.x - b.x, a.y - b.y));
      const off = Math.max(...mids.map(([n, mx, my]) => { const p = w.pins.find(q => q.n === n); return Math.hypot(p.x - mx, p.y - my); }));
      return { up: w.pins.every(p => p.s === 'up'), near, off };
    }""")
    assert res["up"] is True
    assert res["near"] >= page.evaluate("GAP") - 1e-3
    assert res["off"] < 0.06


def test_dragging_the_kalikka_down_throws_it_and_a_short_pull_does_not(site, context):
    page = start(site, context)
    px, py, pull = page.evaluate("[pad.x, pad.y, pad.pull]")
    page.mouse.move(px, py); page.mouse.down(); page.mouse.move(px, py + 8, steps=3); page.mouse.up()
    assert page.evaluate("phase") == "aim"
    # Pulled down about half way, a little left: it lands about 3.5 m out, right of the middle.
    page.mouse.move(px, py); page.mouse.down(); page.mouse.move(px - 20, py + 0.45 * pull, steps=8)
    assert 3.3 < page.evaluate("aim.d") < 3.7 and page.evaluate("aim.x") > 0.05
    page.mouse.up()
    assert page.evaluate("phase") == "fly"
    page.evaluate("run(() => phase === 'fly')")
    assert page.evaluate("phase") == "show"
    page.evaluate("run(() => phase === 'show')")
    assert page.evaluate("[phase, throwN, thrower()]") == ["aim", 1, "cpu"]
    assert page.errors == []


def test_the_throw_buttons_choose_upright_or_crosswise_and_it_stays(site, context):
    page = start(site, context)
    b = page.evaluate("styleBtns.find(b => b.s === 1)")
    page.mouse.click(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
    assert page.evaluate("[aim.st, myStyle]") == [1, 1]
    page.evaluate("doThrow({ x: 0, d: 2, st: aim.st }); run(() => !(phase === 'aim' && thrower() === 'me'), 60)")
    assert page.evaluate("[thrower(), aim.st]") == ["me", 1]


def test_a_tap_on_a_pin_aims_at_it(site, context):
    page = start(site, context)
    page.wait_for_function("V3 !== null")
    page.evaluate("camSnap(); draw()")
    sx, sy, px, py = page.evaluate("(() => { const p = world.pins.find(q => q.n === 6); const s = toScreen(p.x, p.y, PH / 2); return [s[0], s[1], p.x, p.y]; })()")
    page.mouse.click(sx, sy)
    slope = page.evaluate("slope")
    assert abs(slope - px / (py - page.evaluate("Y0"))) < 0.005
    assert page.evaluate("aimShown") is True


def test_the_computer_takes_exactly_what_it_needs(site, context):
    page = open_game(site, context)
    res = page.evaluate(f"""() => {{
      const pins = ({ROW})();
      const plan = cpuPlan(pins, 45, 0);
      return pointsOf(simulate(pins, plan).pins);
    }}""")
    assert res == 5
    # From the full setup it goes for many pins.
    assert page.evaluate("pointsOf(simulate(setUp(), cpuPlan(setUp(), 0, 0)).pins)") >= 5


def test_late_in_the_game_the_computer_plans_only_throws_it_can_make(site, context):
    page = start(site, context, first=1)
    # The pins have spread far: most stand past the longest throw (5.5 m) and one far to the side.
    res = page.evaluate("""() => {
      world.pins = setUp().map((p, i) => pin(p.n, -0.9 + (i % 6) * 0.36, i < 6 ? 6.3 : 7.0));
      world.pins[11].x = 4.6; world.pins[11].y = 4.2;
      score[1] = 40;
      const plan = cpuPlan(world.pins, 40, 0), predicted = pointsOf(simulate(world.pins, plan).pins);
      // The computer throws exactly its plan: no level error, no shaking hand.
      skillOf = () => ({ ex: 0, ew: 0 }); shaken = a => a; cpuPlan = () => plan;
      toAim();
      run(() => phase !== 'show', 30);
      return { plan, predicted, thrown: msg.pts, landed: aim };
    }""")
    assert res["plan"]["d"] <= page.evaluate("D_MAX") and abs(res["plan"]["x"]) <= 4
    assert res["predicted"] > 0
    assert res["thrown"] == res["predicted"]
    assert res["landed"]["d"] == res["plan"]["d"] and res["landed"]["x"] == res["plan"]["x"]


def test_a_whole_game_ends_saves_and_raises_the_level_on_a_win(site, context):
    page = start(site, context)
    # The phone throws at the nearest pin each time; the computer throws far too short.
    page.evaluate("""() => {
      cpuPlan = () => ({ x: 0, d: 1.5, st: 0 });
      skillOf = () => ({ ex: 0, ew: 0 });
      for (let k = 0; k < 400 && phase !== 'done'; k++) {
        if (phase === 'aim' && thrower() === 'me') {
          const p = world.pins.slice().sort((a, b) => a.y - b.y)[0];
          doThrow(aimAt(p.x, p.y, p.y - 0.25, 0), true);
        } else if (phase === 'show') next();
        else run(() => phase === 'fly' || (phase === 'aim' && thrower() === 'cpu'), 30);
      }
    }""")
    assert page.evaluate("[phase, winner, outs[1], misses[1]]") == ["done", 0, True, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:molkky:taso')") == "2"
    assert page.evaluate("localStorage.getItem('ai-pelit:molkky:voitot')") == "1"
    assert page.evaluate("localStorage.getItem('ai-pelit:molkky:peli')") == "null"
    assert page.locator("#result").inner_text().startswith("Voitit")
    assert page.locator("#foe").inner_text() == "Taso 2: vastassa Kesävieras"
    assert page.errors == []


def test_the_throws_points_show_and_a_tap_goes_on(site, context):
    page = start(site, context)
    page.evaluate("doThrow({ x: 0, d: 3.35, st: 1 }, true); run(() => phase === 'fly')")
    n = page.evaluate("fallen(world.pins).length")
    assert page.evaluate("[phase, msg.pts, score[0]]") == ["show", n, n]
    page.evaluate("phaseT = 1")
    page.mouse.click(180, 300)
    assert page.evaluate("[phase, thrower(), world.pins.every(p => p.s === 'up')]") == ["aim", "cpu", True]


def test_a_reload_mid_game_can_carry_the_game_on(site, context):
    page = start(site, context)
    page.evaluate("doThrow({ x: 0, d: 3.35, st: 1 }, true); run(() => phase === 'fly')")
    pins = page.evaluate("world.pins.map(p => [p.n, Math.round((p.x + (p.s === 'down' ? p.dx * PH / 2 : 0)) * 100)])")
    page.evaluate("score = [12, 3]; scoreThrow = () => {}")
    page.evaluate("const keep = clonePins(world.pins); raise(keep); save('peli', { pins: keep.map(p => [r3(p.x), r3(p.y)]), sc: score, mi: [0, 1], ou: outs, tu: 1, n: 1, lv: level })")
    page.reload()
    page.evaluate(RUN)
    assert page.locator("#resume").is_visible()
    assert "12–3" in page.locator("#resume").inner_text()
    page.click("#resume")
    assert page.evaluate("[phase, score.join('-'), misses.join('-'), turn, thrower()]") == ["aim", "12-3", "0-1", 1, "cpu"]
    now = page.evaluate("world.pins.map(p => [p.n, Math.round(p.x * 100)])")
    assert [n for n, _ in now] == [n for n, _ in pins]
    assert all(abs(a[1] - b[1]) <= 3 for a, b in zip(now, pins))


# ---------- v2 (#270): the pins stay in reach and in sight ----------

def test_a_whole_game_of_throws_keeps_the_pins_within_reach(site, context):
    """v1's pins rolled 10-13 m out and up to 9 m wide late in a game, past any throw."""
    page = open_game(site, context)
    res = page.evaluate("""() => {
      let far = 0, wide = 0, stuck = 0;
      for (let g = 0; g < 4; g++) {
        let pins = setUp(), sc = 0;
        for (let t = 0; t < 25; t++) {
          const plan = cpuPlan(pins, sc, 0), k = skillOf(3);
          const w = simulate(pins, shaken(clampAim({ x: plan.x + gauss() * k.ex, d: plan.d + gauss() * k.ew, st: plan.st })));
          sc += pointsOf(w.pins); if (sc > 50) sc = 25; if (sc === 50) sc = 0;
          raise(w.pins); pins = w.pins;
          const ys = pins.map(p => p.y), xs = pins.map(p => p.x);
          far = Math.max(far, ...ys); wide = Math.max(wide, Math.max(...xs) - Math.min(...xs));
          if (Math.min(...ys) > D_MAX + 0.4) stuck++;
        }
      }
      return { far, wide, stuck, yard: [YARD_Y, YARD_X], reach: D_MAX };
    }""")
    assert res["far"] <= res["yard"][0] + 1e-6 and res["wide"] <= 2 * res["yard"][1] + 1e-6, res
    assert res["stuck"] == 0 and res["yard"][0] < res["reach"] + 0.6, res


def test_a_full_pull_throws_to_eight_metres_and_half_a_pull_about_four(site, context):
    page = start(site, context)
    px, py, pull = page.evaluate("[pad.x, pad.y, pad.pull]")
    page.mouse.move(px, py); page.mouse.down(); page.mouse.move(px, py + pull + 30, steps=6)
    assert page.evaluate("aim.d") == pytest.approx(8, abs=0.01)
    page.mouse.move(px, py + 0.5 * pull, steps=4)
    assert 3.6 < page.evaluate("aim.d") < 4.1
    page.mouse.move(px, py, steps=4); page.mouse.up()
    assert page.evaluate("phase") == "aim"


def test_pins_pushed_apart_at_the_yards_edge_stay_inside_it(site, context):
    page = open_game(site, context)
    res = page.evaluate("""() => {
      // Every pin fallen past the same far corner: stood up there, then set apart.
      const pins = setUp().map(p => Object.assign(pin(p.n, 5 + p.n * 0.001, 12), { s: 'down', dx: 1, dy: 0 }));
      pins[3].x = 5; pins[4].x = 5;   // two on the very same spot
      raise(pins);
      let near = Infinity;
      for (const a of pins) for (const b of pins) if (a !== b) near = Math.min(near, Math.hypot(a.x - b.x, a.y - b.y));
      return { inside: pins.every(p => Math.abs(p.x) <= YARD_X + 1e-9 && p.y <= YARD_Y + 1e-9 && p.y >= 1.2), near, gap: GAP };
    }""")
    assert res["inside"] is True
    assert res["near"] >= res["gap"] - 1e-3


def test_a_game_saved_by_v1_with_pins_far_away_continues_within_reach(site, context):
    page = open_game(site, context)
    # v1 saved its game under the same key, with the pins 10-13 m out and wide, and two misses.
    page.evaluate("""() => save('peli', { pins: setUp().map((p, i) => [-4 + i * 0.7, 10 + (i % 4)]),
      sc: [30, 41], mi: [2, 0], ou: [false, false], tu: 0, n: 17, lv: level })""")
    page.reload()
    page.evaluate(RUN)
    page.click("#resume")
    res = page.evaluate("""() => {
      let near = Infinity;
      for (const a of world.pins) for (const b of world.pins) if (a !== b) near = Math.min(near, Math.hypot(a.x - b.x, a.y - b.y));
      return { phase, sc: score.join('-'), mi: misses.join('-'), n: throwN, near,
        inside: world.pins.every(p => Math.abs(p.x) <= YARD_X + 1e-9 && p.y <= YARD_Y + 1e-9),
        reachable: pointsOf(simulate(world.pins, cpuPlan(world.pins, 0, 0)).pins) > 0 };
    }""")
    assert res["phase"] == "aim" and res["sc"] == "30-41" and res["mi"] == "2-0" and res["n"] == 17
    assert res["inside"] is True and res["reachable"] is True
    assert res["near"] >= page.evaluate("GAP") - 1e-3


# Eero's case: pins spread far out and to both sides, to the yard's edges.
SPREAD = """() => { world.pins = setUp().map((p, i) => pin(p.n, [-2, 2, -1.5, 1.2, 0.3, -0.6, 1.6, -1.8, 0.8, 1.9, -1.0, 0.1][i],
  [4.2, 5.1, 5.8, 6.6, 7.4, 8.5, 4.8, 7.0, 6.1, 8.0, 3.3, 5.5][i])); turn = 0; toAim(); camSnap(); draw(); }"""


@pytest.mark.parametrize("size", [(360, 740), (390, 844), (740, 360)])
def test_every_pin_spread_to_the_sides_is_in_sight_and_can_be_tapped(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.wait_for_function("V3 !== null")
    page.evaluate(SPREAD)
    spots = page.evaluate("world.pins.map(p => [p.n, ...toScreen(p.x, p.y, PH / 2)])")
    top, bottom = page.evaluate("[hudBottom(), wide ? H : pad.y - 20]")
    assert all(4 <= sx <= size[0] - 4 and top <= sy <= bottom for _, sx, sy, _ in spots), spots
    # A tap on the pin furthest to the right aims at it.
    n, sx, sy, _ = max(spots, key=lambda q: q[1])
    page.mouse.click(sx, sy)
    px, py = page.evaluate(f"(() => {{ const p = world.pins.find(q => q.n === {n}); return [p.x, p.y]; }})()")
    assert page.evaluate("slope") == pytest.approx(px / (py - page.evaluate("Y0")), abs=0.01)
    ctx.close()


# ---------- Playing with friends ----------

@pytest.fixture
def room(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(RUN)
        return page

    def play(*names):
        host = phone(names[0])
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
        code = host.evaluate("AiPelitRooms.code")
        guests = []
        for n in names[1:]:
            g = phone(n)
            g.click("#multi")
            g.fill("#aipr-codeIn", code)
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
            guests.append(g)
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
        host.click("#aipr-start")
        for p in [host, *guests]:
            p.wait_for_function("phase === 'aim'")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def test_three_phones_take_turns_in_the_rooms_order(room):
    host, [aino, iida] = room("Eero", "Aino", "Iida")
    assert host.evaluate("players.map(p => p.name)") == ["Eero", "Aino", "Iida"]
    ids = [p.evaluate("AiPelitRooms.me") for p in (host, aino, iida)]
    host.evaluate("turn = 1; toAim()")
    aino.wait_for_function("myTurn()")
    assert host.evaluate("myTurn()") is False
    iida.wait_for_function("phase === 'aim' && !myTurn() && nameOf(turn) === 'Aino'")
    # Aino drags: the host sees her aim; she lets go: the kalikka flies on every phone.
    px, py, pull = aino.evaluate("[pad.x, pad.y, pad.pull]")
    aino.mouse.move(px, py); aino.mouse.down(); aino.mouse.move(px, py + 0.45 * pull, steps=6)
    host.wait_for_function("aimShown && aim.d > 3", timeout=3000)
    aino.mouse.up()
    host.wait_for_function("phase === 'fly'", timeout=3000)
    iida.wait_for_function("phase === 'fly' || phase === 'show'", timeout=3000)
    # Then Iida's turn, then Eero's.
    host.evaluate("run(() => phase === 'fly'); next()")
    assert host.evaluate("thrower()") == ids[2]
    iida.wait_for_function("myTurn()", timeout=3000)
    host.evaluate("doThrow({ x: 0, d: 2, st: 0 }); run(() => phase === 'fly'); next()")
    assert host.evaluate("thrower()") == ids[0]
    assert host.errors == aino.errors == iida.errors == []


def test_the_winner_is_heard_by_every_phone_once(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("turn = 1; score = [20, 48]; toAim()")
    guest.wait_for_function("myTurn()")
    # Aino needs 2: the host plays her throw for her, knocking pin 2 alone.
    host.evaluate("""world.pins = setUp().map((p, i) => pin(p.n, -1.1 + i * 0.2, 3.5));
      const p = world.pins.find(q => q.n === 2); doThrow(aimAt(p.x, p.y, p.y - 0.25, 0), true); run(() => phase === 'fly')""")
    assert host.evaluate("[msg.pts, winner]") == [2, 1]
    host.evaluate("next()")
    for p, res, saved in [(host, "Aino voitti", '{"voitot":0,"haviot":1}'), (guest, "Voitit! 🏆", '{"voitot":1,"haviot":0}')]:
        p.wait_for_function("phase === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0")
        assert p.locator("#aipr-result").inner_text() == res
        assert p.evaluate("localStorage.getItem('ai-pelit:molkky:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_a_throw_out_of_turn_or_sent_twice_is_ignored(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("turn = 0; toAim()")
    guest.wait_for_function("phase === 'aim' && !myTurn()")
    guest.evaluate("AiPelitRooms.send({ t: 'throw', round: net.round, n: throwN, x: 0, d: 3.3, st: 1 })")
    host.wait_for_timeout(400)
    assert host.evaluate("phase") == "aim"
    host.evaluate("doThrow({ x: 0, d: 2, st: 0 }); run(() => phase === 'fly'); next()")
    guest.wait_for_function("myTurn()", timeout=5000)
    guest.evaluate("const m = { t: 'throw', round: net.round, n: throwN, x: 0, d: 2, st: 0 }; AiPelitRooms.send(m); AiPelitRooms.send(m)")
    host.wait_for_function("phase === 'fly'", timeout=3000)
    host.evaluate("run(() => phase === 'fly'); next()")
    host.wait_for_timeout(300)
    assert host.evaluate("[throwN, misses.join('-'), phase, myTurn()]") == [2, "1-1", "aim", True]
    assert host.errors == guest.errors == []


def test_a_phone_let_go_is_thrown_for_by_the_computer(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    host.evaluate("turn = 1; toAim()")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("thrower() === 'cpu'")
    host.wait_for_function("phase === 'fly'", timeout=8000)
    assert host.errors == third.errors == []


def test_a_guest_that_reloads_mid_game_gets_it_back(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("turn = 0; toAim(); doThrow({ x: 0, d: 3.35, st: 1 }, true); run(() => phase === 'fly'); next()")
    fallen_n = host.evaluate("score[0]")
    guest.reload()
    guest.evaluate(RUN)
    guest.wait_for_function(f"phase === 'aim' && myTurn() && score[0] === {fallen_n}", timeout=8000)
    assert guest.errors == []


# ---------- Screens ----------

@pytest.mark.parametrize("size", [(740, 360), (640, 360), (360, 640), (390, 844)])
def test_the_menu_the_pad_and_the_pins_fit_the_screen(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    for sel in ["#go", "#multi", "h1"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] >= 0 and b["x"] + b["width"] <= size[0], sel
    page.click("#go")
    page.evaluate("turn = 0; toAim()")
    # The pad, its whole pull and the throw buttons are on the screen, and apart from each other.
    inside = page.evaluate("""() => styleBtns.every(b => b.x >= 0 && b.y >= 0 && b.x + b.w <= W && b.y + b.h <= H)
      && pad.x > 0 && pad.y + pad.pull <= H && pad.pull >= 120
      && styleBtns.every(b => Math.hypot(pad.x - (b.x + b.w / 2), pad.y - (b.y + b.h / 2)) > 60)""")
    assert inside is True
    # Every pin is in view, under the score board and above the pad.
    page.wait_for_function("V3 !== null")
    page.evaluate("camSnap(); draw()")
    spots = page.evaluate("world.pins.map(p => toScreen(p.x, p.y, PH / 2))")
    top, bottom = page.evaluate("[hudBottom(), wide ? H : pad.y - 20]")
    assert all(0 <= sx <= size[0] and top <= sy <= bottom for sx, sy, _ in spots), (spots, top, bottom)
    ctx.close()


def test_turning_the_phone_mid_game_keeps_the_game(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.evaluate("turn = 0; toAim(); doThrow({ x: 0, d: 3.35, st: 1 }, true); run(() => phase === 'fly'); next()")
    sc = page.evaluate("score[0]")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide === true")
    assert page.evaluate("[phase, score[0], thrower()]") == ["aim", sc, "cpu"]
    ctx.close()
