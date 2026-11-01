"""Kuulantyöntö v1 (#268): the shot put on the shared athletics library."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/kuula/v1/"

# Test helpers in the page: run(cond, max) steps the game 1/120 s at a time; put(k, off, ang) is a
# whole put: the standings skipped, the glide (1) or spin (2) started, Työnnä pressed off seconds
# from the power position and held until the angle is ang; quick() lands it and reports it.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 120) step(1 / 120); };
  window.put = (k = 1, off = 0, ang = 37) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    press(k);
    run(() => th.phase === 'move' && th.t < TECH[k].T + off - 1e-9, 5);
    if (th.phase !== 'move') return;
    startPush(1);
    run(() => th.phase === 'push' && th.ang < ang - 1e-9, 5);
    if (th.phase === 'push') release();
  };
  window.quick = () => {
    if (th.shot) { th.shot.t = th.shot.tl; step(0.001); }
    th.t = 99; step(0.001);
  };
}"""

# Math.random seeded (mulberry32) before the game loads, so the computer's skills and puts and
# the tests' own scatter are the same on every run.
SEEDED = """(() => {
  let s = %d >>> 0;
  Math.random = () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
})();"""

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""
SOUNDS = ['valinta', 'askel', 'suhahdus', 'ponnistus', 'onnistui', 'virhe', 'tomahdys', 'aplodit', 'ohhoo', 'mitali']


def open_game(site, context, saved=None, seed=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(SEEDED % seed)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:kuula:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def start(page):
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001)")


def test_speed_and_angle_put_further_and_the_mark_is_from_the_rim(site, context):
    page = open_game(site, context)
    glide, spin = page.evaluate("[flight(1, 0, 37), flight(2, 0, 37)]")
    # A perfect glide about 19 m, a perfect spin about 22 m, both straight down the middle.
    assert glide["mark"] == pytest.approx(19.4, abs=0.5)
    assert spin["mark"] == pytest.approx(22.3, abs=0.5)
    assert glide["why"] == spin["why"] == "" and glide["dev"] == spin["dev"] == 0
    # Measured from the inside of the rim, down to the centimetre.
    assert spin["mark"] == int(spin["d"] * 100 + 1e-6) / 100
    # The best angle is about 37°: flatter or steeper puts are shorter.
    best = page.evaluate("[...Array(61).keys()].map(a => a + 10).reduce((b, a) => flight(1, 0, a).d > flight(1, 0, b).d ? a : b)")
    assert 35 <= best <= 39
    for a in (20, 30, 45, 60):
        assert page.evaluate(f"flight(1, 0, {a}).d") < glide["d"] - 0.2
    # Inside the green angles a put loses little.
    for a in page.evaluate("GREEN"):
        assert page.evaluate(f"flight(1, 0, {a}).d") > glide["d"] - 0.5
    assert page.errors == []


def test_timing_the_push(site, context):
    page = open_game(site, context)
    start(page)
    # Good timing within the window, then a weaker put the earlier it is.
    on = page.evaluate("flight(1, 0, 37).d")
    edge = page.evaluate("flight(1, TECH[1].win, 37).d")
    early = page.evaluate("flight(1, -TECH[1].win - 0.15, 37).d")
    assert on - 1 < edge < on and early < on - 3
    # The glide goes straight however early; the spin pushed early goes wide.
    assert page.evaluate("flight(1, -0.5, 37).why") == ""
    assert page.evaluate("flight(2, -TECH[2].win, 37).why") == ""
    assert page.evaluate("flight(2, -2.5 * TECH[2].win, 37).why") == "Sektorin ulkopuolelle"
    # A real put, pushed on the dot, lands where flight() says.
    page.evaluate("put(1, 0, 37)")
    assert page.evaluate("[th.phase, th.ang, th.why]") == ["fly", 37, ""]
    page.evaluate("quick()")
    assert page.evaluate("K.mine().marks[0]") == page.evaluate("flight(1, th.off, 37).mark")
    assert page.errors == []


def test_over_the_board(site, context):
    page = open_game(site, context)
    start(page)
    # Pushed after the window: the weight is already over the board.
    page.evaluate("press(1); run(() => th.t < TECH[1].T + TECH[1].win - 0.01); th.t = TECH[1].T + TECH[1].win + 0.001; startPush(1)")
    assert page.evaluate("[th.phase, th.mark, th.why, th.over, th.shot]") == ["land", -1, "Liian myöhään: yli renkaan", True, None]
    page.evaluate("quick()")
    assert page.evaluate("K.mine().marks") == [-1]
    # No push at all: over the board the moment the window ends.
    page.evaluate("run(() => th.phase === 'wait'); th.t = 99; step(0.001); press(2); run(() => th.phase === 'move', 5)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Ei työntöä ajoissa: yli renkaan"]
    assert page.evaluate("th.t") < 0.02
    page.evaluate("quick()")
    # Held to the top, the put goes by itself, steep and short.
    page.evaluate("run(() => th.phase === 'wait'); th.t = 99; step(0.001); press(1); run(() => th.t < TECH[1].T); startPush(1); run(() => th.phase === 'push', 3)")
    assert page.evaluate("[th.phase, th.ang]") == ["fly", 70]
    assert page.evaluate("th.mark") < 12
    # The front foot touches the board just as the window ends, in both ways across.
    for k in (1, 2):
        assert page.evaluate(f"hip({k}, TECH[{k}].T + TECH[{k}].win) + foot({k})") == pytest.approx(0, abs=1e-9)
        assert page.evaluate(f"hip({k}, TECH[{k}].T) + REACH") < 0
    assert page.errors == []


def test_pads_pick_the_way_then_push_and_let_go(site, context):
    page = open_game(site, context)
    start(page)
    pads = page.evaluate("pads()")
    assert [p["k"] for p in pads] == [1, 2]
    p = pads[1]
    page.touchscreen.tap(p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)
    assert page.evaluate("[th.phase, th.k]") == ["move", 2]
    # Now the whole pad area is Työnnä: held down, the angle rises; lifted, the shot goes.
    p = page.evaluate("pads()")
    assert [q["k"] for q in p] == [3]
    page.evaluate("run(() => th.t < TECH[2].T)")
    page.mouse.move(180, p[0]["y"] + 40)
    page.mouse.down()
    page.evaluate("run(() => th.ang < 37)")
    assert page.evaluate("th.phase") == "push"
    page.mouse.up()
    # (Real time passes between the steps here, so the angle may have gone a little further.)
    phase, ang = page.evaluate("[th.phase, th.ang]")
    assert phase == "fly" and 37 <= ang <= 42
    assert page.errors == []


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.throwers.length, K.comp.round, th.mine, th.phase]") == [12, 1, True, "wait"]
    for rnd in range(1, 7):
        assert page.evaluate("K.comp.round") == rnd
        page.evaluate(f"put({2 if rnd % 2 else 1}, 0.01, 37); quick()")
        if rnd == 1:
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kuula:ennatys'))") > 21
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kuula:kesken')).round") == 2
    assert page.evaluate("K.comp.over && K.ending.at === 0")
    assert page.evaluate("K.comp.final.length") == 8
    page.evaluate("K.ending.t = 99; step(0.01); K.skip(); step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:kuula:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("put(1, 0.03, 35); quick()")
    first = page.evaluate("K.mine().marks[0]")
    assert first > 17
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    page.click("#cont")
    assert page.evaluate("[K.comp.round, K.mine().marks[0], th.mine]") == [2, first, True]
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("""() => {
      window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
      window.fresh = () => { th = Object.assign({}, th, { phase: 'ready', t: 0, shot: null, mark: null, over: false }); };
      window.many = (k, play) => { const out = []; for (let i = 0; i < k; i++) { fresh(); play(); out.push(th.mark); } return out; };
      // A fair player: the glide, the push a normal 0.07 s off the power position, the angle 4° off.
      window.fair = () => put(1, gs() * 0.07, Math.round(37 + gs() * 4));
      window.meets = (lv, k) => {
        let won = 0;
        for (let i = 0; i < k; i++) {
          K.level = lv; K.quit(); soloComp();
          while (!K.ending) { th.t = 99; step(0.001); fair(); quick(); }
          if (K.ending.at === 0) won++;
          K.ending = null;
        }
        return won;
      };
    }""")
    skills = lambda lv: page.evaluate(f"(() => {{ const k = K.level, c = K.comp, t0 = th, sh = K.shown, kept = localStorage.getItem('ai-pelit:kuula:kesken'); K.level = {lv}; K.solo(); const s = K.comp.throwers.slice(1).map(t => t.skill); K.comp = c; th = t0; K.shown = sh; K.level = k; if (kept) localStorage.setItem('ai-pelit:kuula:kesken', kept); return s; }})()")
    # Lazy: the glide and a quick tap of Työnnä right away. Far behind level 1.
    lazy = page.evaluate("many(20, () => put(1, -0.9, 14))")
    assert max(lazy) < min(skills(1)) - 3
    # Reckless: always the spin, pushing a random bit early or late. Many fouls, no easy win.
    wild = page.evaluate("many(40, () => put(2, gs() * 0.2, 37))")
    assert sum(m < 0 for m in wild) >= 15
    # Fair play wins nearly every meet at level 1, under half at level 5, hardly any at level 7.
    l1, l5, l7 = page.evaluate("[meets(1, 20), meets(5, 20), meets(7, 20)]")
    assert l1 >= 18, l1
    assert l5 <= 12, l5
    assert l7 <= 4, l7
    # A perfect spin still beats the strongest computer at the top level.
    top = page.evaluate("flight(2, 0, 37).mark")
    assert top > max(skills(30)) + 0.5
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 18.23, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#asu", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("K.comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.marks = [18.88, -1, 17.77]; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    page.evaluate("th.t = 99; step(0.001)")
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    # Close up, the whole circle and the board are in the scene, and the thrower's head is under
    # the texts; in flight, a 23 m put's highest point is in the scene too.
    page.evaluate("blend = 0; camera(0)")
    l, r, sw = page.evaluate("[(-2 * CIRCLE_R - camX) * runS, (BOARD_W - camX) * runS, SW]")
    assert 0 <= l and r <= sw
    assert page.evaluate("groundY - 2.0 * runS") > page.evaluate("hudTop + 146")
    assert page.evaluate("groundY - 7 * flyS") > page.evaluate("hudTop + 64")
    assert page.errors == []


def test_turning_the_phone_keeps_the_put(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("press(2); run(() => th.t < 0.5)")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate("[th.phase, th.k, th.t >= 0.5, land]") == ["move", 2, True, True]
    assert page.errors == []


def test_a_put_sounds_from_the_turn_to_the_landing(site, context):
    page = open_game(site, context)
    page.evaluate(SPY)
    page.click("#go")
    page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('valinta', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0); th.t = 99; step(0.001)")
    played = lambda: [n for n, ok in page.evaluate("heard.splice(0)") if ok]
    assert played() == ["valinta"]
    page.evaluate("press(1)")
    assert played() == ["askel"]
    page.evaluate("run(() => th.t < TECH[1].T); startPush(1)")
    assert played() == ["ponnistus"]
    page.evaluate("run(() => th.ang < 37); release()")
    assert played() == ["suhahdus"]
    # The first put of the meet leads it: the thud, then the crowd claps.
    page.evaluate("quick()")
    assert played() == ["tomahdys", "aplodit"]
    # Over the board: the crowd goes ooh.
    page.evaluate("run(() => th.phase === 'wait'); th.t = 99; step(0.001); heard.splice(0); put(2, 0.2, 37)")
    assert played() == ["suhahdus", "ohhoo"]
    assert page.errors == []


# ---- With friends ----

def room(site, browser, names):
    """The first phone makes a room, the others join it, and the meet starts."""
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in names:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(HELPERS)
        pages.append(page)
    host = pages[0]
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    for guest in pages[1:]:
        guest.click("#multi")
        guest.fill("#aipr-codeIn", code)
        guest.click("#aipr-joinBtn")
    host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("K.comp && K.comp.throwers.length === 12 && th", timeout=8000)
    return relay, pages


def thrower_page(pages):
    """The phone whose turn it is, by the host's competition."""
    pid = pages[0].evaluate("K.current() && K.current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_put_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("K.comp.order.join()") == host.evaluate("K.comp.order.join()") for p in pages)
    first = thrower_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("put(2, 0.01, 38)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'fly'", timeout=5000)
        assert p.evaluate("[th.mark, th.k]") == first.evaluate("[th.mark, th.k]")
    first.evaluate("quick()")
    seq = host.evaluate("K.comp.seq")
    for p in pages:
        p.wait_for_function(f"K.comp.seq === {seq}", timeout=5000)
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"K.comp && K.comp.seq === {seq} && th", timeout=10000)
    # Everyone puts on until the end; one put goes over the board.
    for i in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = thrower_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate(f"put(1, {0.3 if i == 1 else 0.01}, 37); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("K.ending ? K.ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (K.ending) { K.ending.t = 99; step(0.01); K.skip(); step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:kuula:kisat')") == "1"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:kuula:ennatys'))") > 18
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_foul_shows_on_every_phone_and_a_minute_with_no_tap_is_one(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    p = thrower_page(pages)
    q = aino if p is host else host
    p.wait_for_function("th && th.mine && th.phase === 'ready'", timeout=8000)
    # Never pushing: over the board, and the other phone sees it.
    p.evaluate("press(1); run(() => th.phase === 'move', 5)")
    q.wait_for_function("th && th.phase === 'land' && th.why === 'Ei työntöä ajoissa: yli renkaan' && th.over", timeout=5000)
    n = host.evaluate("K.comp.seq")
    p.evaluate("quick()")
    host.wait_for_function(f"K.comp.seq > {n}", timeout=5000)
    # The next phone on its turn: a minute standing at the back of the circle is a foul.
    p = thrower_page(pages)
    p.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
    p.evaluate("run(() => th.phase === 'ready', 59)")
    assert p.evaluate("th.phase") == "ready"
    p.evaluate("run(() => th.phase === 'ready', 2)")
    assert p.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Aika loppui"]
    for r in pages:
        assert r.errors == []
        r.context.close()
