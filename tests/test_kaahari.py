"""Kaahari, the kart race, in a phone-sized Chromium."""

from conftest import ROOT

URL = "games/kaahari/v1/"


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    return page


def start(site, context, track=0):
    page = open_game(site, context)
    page.evaluate(f"soloRace({track})")
    page.wait_for_function("race.phase === 'run'", timeout=6000)
    return page


def test_nobody_moves_before_the_countdown_ends(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("input.right = true; input.drift = true")
    page.wait_for_timeout(1500)
    assert page.evaluate("[race.phase, race.karts.every(k => k.v === 0)]") == ["cd", True]


def test_the_karts_drive_round_the_track(site, context):
    page = start(site, context)
    page.wait_for_function("me.prog > 60 && race.karts.every(k => k.prog > 0)", timeout=4000)


def test_a_long_slide_gives_a_turbo_when_let_go(site, context):
    page = start(site, context, 1)
    page.wait_for_function("me.v > 100", timeout=3000)
    page.evaluate("input.drift = true; input.right = true")
    page.wait_for_function("me.drift === 1", timeout=1000)
    page.evaluate("input.right = false")
    page.wait_for_function(f"me.dTime > {1.5}", timeout=3000)
    page.evaluate("input.drift = false")
    page.wait_for_timeout(50)
    assert page.evaluate("[me.drift, me.boost > 0.6]") == [0, True]


def test_a_short_slide_gives_nothing(site, context):
    page = start(site, context, 1)
    page.wait_for_function("me.v > 100", timeout=3000)
    page.evaluate("input.drift = true; input.right = true")
    page.wait_for_function("me.drift === 1", timeout=1000)
    page.evaluate("input.drift = false; input.right = false")
    page.wait_for_timeout(50)
    assert page.evaluate("[me.drift, me.boost <= 0]") == [0, True]


def test_a_crate_gives_an_item_and_the_turbo_speeds_up(site, context):
    page = start(site, context)
    page.evaluate("const c0 = race.crates[0]; c0.x = me.x; c0.y = me.y")
    page.wait_for_function("me.item !== null", timeout=1000)
    page.evaluate("me.item = 'turbo'; useItem()")
    assert page.evaluate("[me.item, me.boost > 1]") == [None, True]
    page.wait_for_function("me.v > 200", timeout=2000)


def test_a_bomb_spins_out_the_kart_ahead(site, context):
    page = start(site, context)
    page.evaluate("""() => {
        // The rest of the grid out of the way, far behind.
        race.karts.slice(2).forEach((k, n) => { const q = at(T, me.s - 300 - 30 * n, 0); Object.assign(k, { x: q.x, y: q.y, idx: q.i, s: me.s - 300 - 30 * n, v: 0 }); });
        const o = race.karts[1], p = at(T, me.s + 90, me.lat);
        Object.assign(o, { x: p.x, y: p.y, a: p.a, idx: p.i, s: me.s + 90, v: 0, shield: 0 });
        Object.assign(o.ai, { lane: me.lat / T.hw, want: me.lat / T.hw, laneT: 10, itemT: 99, turboT: 99 });
        me.item = 'pommi'; useItem();
    }""")
    page.wait_for_function("race.karts[1].spin > 0", timeout=2000)
    assert page.evaluate("me.spin") == 0


def test_the_last_lap_finishes_the_race_and_saves_the_win(site, context):
    page = start(site, context)
    # The player a few metres before the line on the last lap, everyone else far behind.
    page.evaluate("""() => {
        race.karts.forEach(k => { if (k !== me) { k.prog = -2000; } });
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150 });
    }""")
    page.wait_for_function("me.fin !== null", timeout=2000)
    page.wait_for_function("race.phase === 'over'", timeout=5000)
    assert page.is_visible("#menu")
    assert page.inner_text("#result") == "🏆 Voitit kisan!"
    saved = page.evaluate("['taso', 'voitot', 'kisat'].map(k => localStorage.getItem('ai-pelit:kaahari:' + k))")
    assert saved == ["2", "1", "1"]
    assert "Hiekkaranta" in page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kaahari:ennatykset'))")


def test_the_saved_level_and_track_are_read_back(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:kaahari:taso', '4'); localStorage.setItem('ai-pelit:kaahari:rata', '2')")
    page.reload()
    assert page.inner_text("#stats").startswith("Taso 4")
    assert "Laavaluola" in page.inner_text(".track.on")


def test_racing_again_after_a_finish_starts_a_fresh_race(site, context):
    page = start(site, context)
    page.evaluate("""() => {
        const p = at(T, T.L - 25, 0);
        Object.assign(me, { x: p.x, y: p.y, a: p.a, idx: p.i, s: T.L - 25, prog: 3 * T.L - 25, lap: 2, v: 150, item: 'tnt', fruit: 7 });
    }""")
    page.wait_for_function("race.phase === 'over'", timeout=6000)
    page.click("#go")
    assert page.evaluate("[race.phase, me.lap, me.fin, me.item, me.fruit, me.prog < 0]") == ["cd", 0, None, None, 0, True]
    assert page.inner_text("#result") == ""
    page.wait_for_function("race.phase === 'run'", timeout=5000)


def test_both_arrows_at_once_on_a_390_px_phone_drive_straight(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    try:
        page = ctx.new_page()
        page.goto(site.url + URL)
        page.evaluate("soloRace(0)")
        page.wait_for_function("race.phase === 'run'", timeout=6000)
        # Every button inside the screen, the arrows clear of the item and slide buttons.
        boxes = page.evaluate("layout(), BTN")
        assert boxes["right"]["x"] + boxes["right"]["w"] < boxes["item"]["cx"] - boxes["item"]["r"]
        assert boxes["drift"]["cx"] + boxes["drift"]["r"] <= 390 and boxes["left"]["y"] + boxes["left"]["h"] <= 844
        # Two fingers, one on each arrow: no turn.
        for sel in ("left", "right"):
            b = boxes[sel]
            page.evaluate(f"c.dispatchEvent(new PointerEvent('pointerdown', {{ pointerId: {1 if sel == 'left' else 2}, clientX: {b['x'] + b['w'] / 2}, clientY: {b['y'] + b['h'] / 2}, bubbles: true }}))")
        assert page.evaluate("[input.left, input.right]") == [True, True]
        page.wait_for_timeout(300)
        assert page.evaluate("Math.abs(input.steer)") < 0.01
    finally:
        ctx.close()
