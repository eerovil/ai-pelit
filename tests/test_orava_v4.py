"""Orava v4: recorded sounds from the shared library public/lib/aanet-2/ (#224)."""

import shutil

from conftest import ROOT

URL = "games/orava/v4/"
SOUNDS = ["hyppy", "ruoho", "tomahdys", "rouske", "lintu", "osuma", "voitto", "tappio"]

RUN = "() => { window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); }; }"

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""

# Two pines 180 px apart with a branch each, and nothing else.
SMALL_FOREST = """() => {
  trees = [{ x: 100, h: 500, i: 0 }, { x: 280, h: 500, i: 1 }];
  branches = [{ t: 0, x0: 100, side: 1, len: 80, y: 260 }, { t: 0, x0: 100, side: 1, len: 80, y: 160 },
              { t: 1, x0: 280, side: -1, len: 80, y: 200 }];
  worldW = 400; martens = []; hawk = null;
  cones = [{ x: 400, y: 900, eaten: false }, { x: 600, y: 900, eaten: false }];
}"""


def open_game(site, context, level=None):
    # Only this game is built, so another game's unfinished folder cannot break the build.
    shutil.copytree(ROOT / "games" / "orava", site.games / "orava")
    site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    if level:
        page.goto(site.url + URL)
        page.evaluate(f"localStorage.setItem('ai-pelit:orava:taso', '{level}')")
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.evaluate(SPY)
    return page


def start(page, wait=True):
    page.click("#go")
    page.evaluate("input.left = input.right = input.up = input.down = false")
    if wait:
        page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('hyppy', { vol: 0 })", timeout=5000)
        page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_jumps_landings_and_cones_sound_as_asked(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate(SMALL_FOREST)
    # A leap off a branch tip to the next trunk: the jump, then paws catching it.
    page.evaluate("toBranch(branches[0], 78); input.right = true; pressJump(); step(1 / 60); input.right = false")
    page.evaluate("run(() => S.mode === 'air', 2)")
    assert page.evaluate("[S.mode, S.tree]") == ["trunk", 1]
    assert played(page) == ["hyppy", "ruoho"]
    # Dropping from a branch onto the one below is the same quiet landing.
    page.evaluate("toBranch(branches[0], 50); input.down = true; step(1 / 60); input.down = false; run(() => S.mode === 'air', 2)")
    assert page.evaluate("S.br.y") == 160
    assert played(page) == ["ruoho"]
    # Off the end of the world onto the ground: a thud.
    page.evaluate("trees = []; branches = []; worldW = 2000; Object.assign(S, { mode: 'ground', x: 300, y: 0 })")
    page.evaluate("pressJump(); step(1 / 60); run(() => S.mode === 'air', 2)")
    assert page.evaluate("S.mode") == "ground"
    assert played(page) == ["hyppy", "tomahdys"]
    # A cone: the crunch.
    page.evaluate("const k = cones[0]; Object.assign(S, { mode: 'air', x: k.x, y: k.y - 9, vx: 0, vy: 0 }); eat()")
    assert played(page) == ["rouske"]
    assert page.errors == []


def test_the_hawk_shrieks_a_hit_hurts_and_the_end_plays_its_tune(site, context):
    page = open_game(site, context, level=3)
    start(page)
    page.evaluate("martens = []; toTrunk(1, 200); hawk.t = 0; step(1 / 60)")
    assert played(page) == ["lintu"]
    page.evaluate("S.inv = 0; hurt('Haukka nappasi!', 1)")
    assert played(page) == ["osuma"]
    page.evaluate("hearts = 1; S.inv = 0; hurt('Haukka nappasi!', 1)")
    assert page.evaluate("phase") == "over"
    assert played(page) == ["osuma", "tappio"]
    assert page.errors == []


def test_eating_the_last_cone_plays_the_win_tune(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("cones.forEach(k => { if (!k.eaten) { Object.assign(S, { x: k.x, y: k.y - 9 }); eat(); } })")
    assert page.evaluate("phase") == "clear"
    assert played(page)[-1] == "voitto"
    assert page.evaluate("localStorage.getItem('ai-pelit:orava:taso')") == "2"
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx, level=3)
        start(page, wait=False)
        # Each v3 beep, by its first frequency, in window.beeps.
        page.evaluate("""() => {
          window.beeps = [];
          const real = tone;
          tone = (f0, ...rest) => { beeps.push(f0); return real(f0, ...rest); };
        }""")
        beeps = lambda: page.evaluate("beeps.splice(0)")
        assert page.evaluate("ac !== null")   # the tap turned the beeps on
        page.evaluate("martens = []; hawk.t = 0; step(1 / 60)")
        assert beeps() == [1400]                       # the hawk's shriek
        page.evaluate("Object.assign(S, { mode: 'ground', x: 30, y: 0 }); pressJump(); step(1 / 60)")
        assert beeps() == [420]                        # the jump
        page.evaluate("trees = []; branches = []; run(() => S.mode === 'air', 2)")
        assert beeps() == [220]                        # the landing
        page.evaluate("const k = cones[0]; Object.assign(S, { x: k.x, y: k.y - 9 }); eat()")
        assert beeps() == [900, 700]                   # the crunch
        page.evaluate("S.inv = 0; hurt('Haukka nappasi!', 1)")
        assert beeps() == [300]                        # the hit
        page.evaluate("hearts = 1; S.inv = 0; hurt('Haukka nappasi!', 1)")
        assert page.evaluate("phase") == "over"
        assert beeps() == [300, 300]                   # the hit, then the loss
        # A new go (the score list covers the menu after a loss, so start it in code).
        page.evaluate("startGo(); input.left = input.right = input.up = input.down = false; beeps.splice(0)")
        page.evaluate("cones.forEach(k => { if (!k.eaten) { Object.assign(S, { x: k.x, y: k.y - 9 }); eat(); } })")
        assert page.evaluate("phase") == "clear"
        assert beeps()[-4:] == [523, 659, 784, 1047]   # the win tune
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v3_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      localStorage.setItem('ai-pelit:orava:taso', '4');
      localStorage.setItem('ai-pelit:orava:ennatys', '321');
      localStorage.setItem('ai-pelit:_asut:orava', '"kurpitsa"');
    }""")
    page.goto(site.url + URL)
    text = page.inner_text("#menu")
    assert "4" in text and "321" in text
    assert page.locator("#asu").inner_text() == "👕 Asu: Kurpitsa"
    assert page.errors == []
