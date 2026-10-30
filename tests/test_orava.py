"""Orava, the squirrel in the pines, in a phone-sized Chromium."""

from conftest import ROOT

URL = "games/orava/v1/"

# Steps the game by hand, 1/60 s at a time, until cond() is false or max seconds pass.
RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"

# Two pines 180 px apart with a branch each, and nothing else, so a test knows what is where.
SMALL_FOREST = """() => {
  trees = [{ x: 100, h: 500, i: 0 }, { x: 280, h: 500, i: 1 }];
  branches = [{ t: 0, x0: 100, side: 1, len: 80, y: 260 }, { t: 0, x0: 100, side: 1, len: 80, y: 160 },
              { t: 1, x0: 280, side: -1, len: 80, y: 200 }];
  worldW = 400; martens = []; hawk = null;
  cones = [{ x: 400, y: 900, eaten: false }];
}"""


def open_game(site, context, level=None):
    site.build(ROOT / "games")
    page = context.new_page()
    if level:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('ai-pelit:orava:taso', '{level}')")
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context, level=None):
    page = open_game(site, context, level)
    page.click("#go")
    page.evaluate("input.left = input.right = input.up = input.down = false")
    return page


def test_the_menu_shows_the_level_and_starts_a_go(site, context):
    page = open_game(site, context)
    assert page.inner_text("#level") == "Taso 1: 4 mäntyä, 10 käpyä"
    assert page.inner_text("#danger") == ""
    page.click("#go")
    assert page.evaluate("[phase, hearts, eaten, cones.length, S.mode]") == ["play", 3, 0, 10, "ground"]
    assert page.is_visible("#jump") and page.is_visible("#stick")


def test_every_cone_can_be_reached_from_a_branch_or_a_treetop(site, context):
    page = open_game(site, context)
    for n in (1, 3, 7):
        bad = page.evaluate(f"""() => {{
            makeForest({n});
            const near = (k, b) => Math.abs(k.y - b.y - 7) < 1 && (k.x - b.x0) * b.side > 0 && (k.x - b.x0) * b.side <= b.len;
            return cones.filter(k => !branches.some(b => near(k, b)) && !trees.some(t => k.x === t.x && k.y === t.h + 4)).length;
        }}""")
        assert bad == 0
        assert page.evaluate(f"cones.length === conesFor({n}) && trees.length === treesFor({n})")


def test_up_at_a_trunk_climbs_it_and_a_side_steps_onto_a_branch(site, context):
    page = start(site, context)
    page.evaluate(SMALL_FOREST)
    page.evaluate("Object.assign(S, { mode: 'ground', x: 106, y: 0 }); input.up = true; run(() => S.y < 255, 3)")
    assert page.evaluate("[S.mode, S.tree, S.x]") == ["trunk", 0, 100]
    page.evaluate("input.up = false; input.right = true; run(() => S.mode === 'trunk', 1)")
    assert page.evaluate("[S.mode, S.br.y]") == ["branch", 260]
    page.evaluate("run(() => S.mode === 'branch', 2)")
    # Ran off the tip: it falls on and lands on the next pine's branch a little lower.
    page.evaluate("input.right = false; run(() => S.mode === 'air', 2)")
    assert page.evaluate("[S.mode, S.br && S.br.t, S.br && S.br.y]") == ["branch", 1, 200]


def test_a_slanted_stick_at_a_branch_either_climbs_on_or_steps_out_not_both(site, context):
    page = start(site, context)
    page.evaluate(SMALL_FOREST)
    # Leaning up more than sideways: it climbs past the branch.
    page.evaluate("toTrunk(0, 240); input.up = input.right = true; input.vert = true; run(() => S.y < 300, 2)")
    assert page.evaluate("[S.mode, S.y >= 300]") == ["trunk", True]
    # Leaning sideways more: it steps out and keeps running out, never back onto the trunk.
    page.evaluate("""() => {
        toTrunk(0, 255); input.vert = false; window.modes = new Set();
        run(() => { modes.add(S.mode); return S.mode !== 'air'; }, 1);
    }""")
    assert page.evaluate("[...modes]") == ["trunk", "branch", "air"]
    page.evaluate("toTrunk(0, 255); input.vert = false; run(() => S.mode !== 'branch' || S.u < 40, 1)")
    assert page.evaluate("[S.mode, S.br.y]") == ["branch", 260]


def test_a_leap_from_a_branch_tip_catches_the_next_trunk(site, context):
    page = start(site, context)
    page.evaluate(SMALL_FOREST)
    page.evaluate("toBranch(branches[0], 78); input.right = true; pressJump(); step(1 / 60)")
    assert page.evaluate("S.mode") == "air"
    page.evaluate("run(() => S.mode === 'air', 2)")
    assert page.evaluate("[S.mode, S.tree]") == ["trunk", 1]


def test_down_on_a_branch_drops_to_the_one_below(site, context):
    page = start(site, context)
    page.evaluate(SMALL_FOREST)
    page.evaluate("toBranch(branches[0], 50); input.down = true; step(1 / 60); input.down = false; run(() => S.mode === 'air', 2)")
    assert page.evaluate("[S.mode, S.br.y]") == ["branch", 160]


def test_a_leap_from_the_ground_lands_about_190_px_on(site, context):
    page = start(site, context)
    page.evaluate("trees = []; branches = []; worldW = 2000; Object.assign(S, { mode: 'ground', x: 300, y: 0 })")
    page.evaluate("input.right = true; pressJump(); step(1 / 60); input.right = false; run(() => S.mode === 'air', 2)")
    assert page.evaluate("S.mode") == "ground"
    assert 160 < page.evaluate("S.x - 300") < 220


def test_eating_every_cone_wins_the_level_and_saves_it(site, context):
    page = start(site, context)
    page.evaluate("const k = cones[0]; Object.assign(S, { mode: 'air', x: k.x, y: k.y - 9, vx: 0, vy: 0 }); eat()")
    assert page.evaluate("[eaten, points, cones[0].eaten]") == [1, 10, True]
    page.evaluate("cones.forEach(k => { if (!k.eaten) { Object.assign(S, { x: k.x, y: k.y - 9 }); eat(); } })")
    assert page.evaluate("[phase, level, hearts]") == ["clear", 2, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:orava:taso')") == "2"
    assert page.evaluate("+localStorage.getItem('ai-pelit:orava:kavyt')") == 10
    page.evaluate("run(() => phase === 'clear', 3)")
    assert page.inner_text("#result").startswith("Taso 1 läpi!")
    assert page.inner_text("#level") == "Taso 2: 5 mäntyä, 12 käpyä"
    assert "Näätä" in page.inner_text("#danger")


def test_the_time_running_out_ends_the_go_on_the_same_level(site, context):
    page = start(site, context)
    page.evaluate("timeLeft = 0.05; run(() => phase === 'play', 1)")
    assert page.evaluate("[phase, level]") == ["over", 1]
    page.evaluate("run(() => phase === 'over', 3)")
    assert page.inner_text("#result") == "Aika loppui! 0/10 käpyä, 0 p"
    assert page.inner_text("#go") == "Uudestaan"


def test_a_marten_knocks_the_squirrel_off_and_three_hits_end_the_go(site, context):
    page = start(site, context, level=2)
    assert page.evaluate("martens.length") == 1
    for n in (2, 1):
        page.evaluate("const m = martens[0]; m.pause = 9; toTrunk(m.tree, m.y); S.inv = 0; step(1 / 60)")
        assert page.evaluate("[hearts, S.mode]") == [n, "air"]
    page.evaluate("const m = martens[0]; toTrunk(m.tree, m.y); S.inv = 0; step(1 / 60)")
    assert page.evaluate("[hearts, phase, level]") == [0, "over", 2]


def test_the_hawk_misses_a_squirrel_on_a_trunk_but_takes_one_on_a_branch(site, context):
    page = start(site, context, level=3)
    page.evaluate("martens = []; toTrunk(1, 200); hawk.t = 0; run(() => hawk.state !== 'fly', 3); run(() => hawk.state === 'fly', 4)")
    assert page.evaluate("hearts") == 3
    page.evaluate("""() => {
        const b = branches.find(b => b.t === 1); toBranch(b, b.len / 2);
        hawk.state = 'wait'; hawk.t = 0; run(() => hawk.state !== 'fly', 3); run(() => hawk.state === 'fly' && hearts === 3, 4);
    }""")
    assert page.evaluate("hearts") == 2


def test_the_stick_and_the_jump_button_drive_the_squirrel(site, context):
    page = start(site, context)
    box = page.locator("#stick").bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 50, cy, steps=3)
    assert page.evaluate("[input.right, input.left, input.up, input.down]") == [True, False, False, False]
    page.mouse.move(cx + 40, cy - 40, steps=3)
    assert page.evaluate("[input.right, input.up]") == [True, True]
    page.mouse.up()
    assert page.evaluate("[input.right, input.up]") == [False, False]
    page.evaluate("Object.assign(S, { mode: 'ground', x: 20, y: 0 })")
    page.locator("#jump").tap()
    page.wait_for_function("S.mode === 'air'", timeout=1000)


def test_a_new_go_after_a_lost_one_starts_afresh(site, context):
    page = start(site, context, level=2)
    page.evaluate("const k = cones[0]; Object.assign(S, { mode: 'air', x: k.x, y: k.y - 9 }); eat(); hearts = 1; timeLeft = 0.02; run(() => phase !== 'menu', 4)")
    assert page.inner_text("#go") == "Uudestaan"
    # The first score opens the high-score list over the menu (it asks a nickname); start past it.
    # The clock is read in the same call as startGo(): on a busy machine it ticks between two calls.
    full, left = page.evaluate("startGo(); [40 + 6 * cones.length, timeLeft]")
    assert page.evaluate("[phase, hearts, eaten, points, cones.every(k => !k.eaten), S.mode, martens.length, level]") == \
        ["play", 3, 0, 0, True, "ground", 1, 2]
    assert left == full


def test_the_controls_fit_a_390_px_phone_side_by_side(site, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    try:
        page = start(site, ctx)
        stick, jump = page.locator("#stick").bounding_box(), page.locator("#jump").bounding_box()
        assert stick["x"] >= 0 and jump["x"] + jump["width"] <= 390
        assert stick["x"] + stick["width"] < jump["x"]
        assert jump["y"] + jump["height"] <= 844 and stick["y"] + stick["height"] <= 844
        # The squirrel on the ground stands above the controls, not behind them.
        assert page.evaluate("sy(0)") < stick["y"] + 30
    finally:
        ctx.close()
# CI timing probe for #123, not to be merged
