"""Pituushyppy v2: v1 on the shared athletics library (public/lib/yleisurheilu-1/kisa.js, #165)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/pituushyppy/v2/"

# Test helpers in the page: run(cond, max) steps the game 1/60 s at a time; go(v, ang, at, q) takes
# off at once from `at` metres with v m/s of run-up at ang degrees, and throws the legs forward q
# seconds before the sand (null: never); quick() lands it and reports it.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); };
  window.go = (v, ang, at, q = 0.22) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    th.phase = 'run'; th.v = v; th.x = at;
    startAim(1); th.aimT = (ang - AIM0) / AIM_RATE; th.ang = ang; release();
    if (q !== null && th.phase === 'fly') { th.ft = th.f.t - q; legs(); }
  };
  window.quick = () => {
    if (th.phase === 'fly') { th.ft = th.f.t; step(0.001); }
    th.t = 99; step(0.001);
  };
}"""


# Math.random seeded (mulberry32) before the game loads, as in test_moukari.py, so the computer's
# skills and jumps and the tests' own scatter are the same on every run.
SEEDED = """(() => {
  let s = %d >>> 0;
  Math.random = () => {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
})();"""


def open_game(site, context, saved=None, seed=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(SEEDED % seed)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:pituushyppy:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def mark(page, at, v, ang, q=0.22, wind=0):
    q = "null" if q is None else q
    return page.evaluate(f"jumpMark({at}, {v}, {ang}, {q}, {wind})")


def test_the_best_angle_is_about_20_degrees_and_speed_jumps_further(site, context):
    page = open_game(site, context)
    best = page.evaluate("[...Array(40).keys()].map(a => a + 5).reduce((b, a) => takeoff(0, 8.3, a).xl > takeoff(0, 8.3, b).xl ? a : b)")
    assert 18 <= best <= 22
    assert 6.0 <= mark(page, 0, 8.3, 20)["mark"] <= 6.7
    assert mark(page, 0, 9.5, 20)["mark"] > mark(page, 0, 8.3, 20)["mark"] + 1
    # The angles drawn green jump within about 20 cm of the best.
    top = page.evaluate("takeoff(0, 8.3, 20).xl")
    for a in page.evaluate("GREEN"):
        assert page.evaluate(f"takeoff(0, 8.3, {a}).xl") > top - 0.25
    # Measured from the line: taking off half a metre early loses half a metre.
    assert mark(page, 0, 8.3, 20)["mx"] - mark(page, -0.5, 8.3, 20)["mx"] == pytest.approx(0.5, abs=0.001)
    # Down to the centimetre, never rounded up; a tail wind helps a little.
    m = mark(page, -0.1, 8.3, 20)
    assert m["mark"] == int(m["mx"] * 100) / 100
    assert 0.05 < mark(page, 0, 8.3, 20, wind=2)["mx"] - mark(page, 0, 8.3, 20)["mx"] < 0.2
    assert page.errors == []


def test_the_legs_early_late_or_not_at_all(site, context):
    page = open_game(site, context)
    good = mark(page, 0, 8.3, 20, 0.22)
    early = mark(page, 0, 8.3, 20, 0.6)
    late = mark(page, 0, 8.3, 20, 0.02)
    none = mark(page, 0, 8.3, 20, None)
    assert good["kind"] == "good" and early["kind"] == "early" and late["kind"] == "late" and none["kind"] == "none"
    # Feet dropping costs a few decimetres; falling back on the hands most of a metre.
    assert 0.25 < good["mark"] - early["mark"] < 0.6
    assert 0.25 < good["mark"] - none["mark"] < 0.7
    assert good["mark"] - late["mark"] > 0.6
    # The whole good window is close to the best.
    lo, hi = page.evaluate("LEGS")
    for q in (lo, (lo + hi) / 2, hi):
        assert mark(page, 0, 8.3, 20, q)["mark"] > good["mark"] - 0.1
    assert page.errors == []


def test_stepping_over_the_line_is_a_foul_and_a_slip_of_the_thumb_is_not_a_jump(site, context):
    page = open_game(site, context)
    assert mark(page, 0.03, 8.3, 20) ["why"] == "Yliastuttu"
    assert mark(page, 0, 8.3, 20)["mark"] > 0   # on the line is still on the board
    page.click("#go")
    # Running over the line and on past the grace without taking off.
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.x = -0.2; th.v = 8; step(0.05)")
    assert page.evaluate("th.phase") == "run"   # 25 cm past the line: still within the grace
    page.evaluate("step(0.1)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Yliastuttu"]
    page.evaluate("draw()")
    page.evaluate("quick()")
    assert page.evaluate("K.comp.throwers.find(t => t.p === 'me').marks") == [-1]
    # v2: holding Hyppää on to the line is no foul: the jump goes by itself, from the line.
    page.evaluate("run(() => th.phase === 'wait'); th.phase = 'run'; th.x = -1; th.v = 8; startAim(1); run(() => th.phase === 'aim', 1)")
    assert page.evaluate("[th.phase, th.relX, th.ang > 5]") == ["fly", 0, True]
    page.evaluate("quick()")
    assert page.evaluate("K.comp.throwers.find(t => t.p === 'me').marks[1]") > 4
    # A touch shorter than 0.1 s does not jump: back to running.
    page.evaluate("run(() => th.phase === 'wait'); th.phase = 'run'; th.x = -15; th.v = 7; startAim(1); step(0.05); release()")
    assert page.evaluate("[th.phase, th.f]") == ["run", None]
    # Holding raises the angle: about 20° after a third of a second.
    page.evaluate("startAim(1); run(() => th.aimT < 0.33, 1)")
    assert 19 <= page.evaluate("th.ang") <= 22
    # Letting go takes off from where the foot is; a tap in the air throws the legs forward once.
    page.evaluate("th.x = -0.3; release()")
    assert page.evaluate("[th.phase, th.relX]") == ["fly", -0.3]
    page.evaluate("run(() => th.f.t - th.ft > 0.2, 2); legs(); const q = th.q; legs(); window.q1 = q")
    assert page.evaluate("th.q === q1 && q1 > 0.15")
    page.evaluate("run(() => th.phase === 'fly', 2)")
    assert page.evaluate("[th.phase, th.kind, th.mark > 4]") == ["land", "good", True]
    assert page.errors == []


def test_the_take_off_is_generous_in_time(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001)")
    # Holding never fouls (v2): still holding when the foot reaches the line takes off by itself,
    # from the line, a legal jump measured from the line.
    flown = page.evaluate("""() => {
        th.phase = 'run'; th.v = 8.5; th.x = -0.3; startAim(1); th.aimT = 0.33; th.x = 8.5 * 0.06; step(0.001);
        return [th.phase, th.relX];
    }""")
    assert flown == ["fly", 0]
    page.evaluate("quick()")
    me = "K.comp.throwers.find(t => t.p === 'me').marks"
    assert page.evaluate(me)[0] > 6
    # v2: held on far past the line in one step, it still takes off at the line.
    page.evaluate("run(() => th.phase === 'wait'); th.phase = 'run'; th.v = 8.5; th.x = -0.3; startAim(1); th.aimT = 0.33; th.x = 8.5 * 0.15; step(0.001)")
    assert page.evaluate("[th.phase, th.relX]") == ["fly", 0]
    page.evaluate("quick()")
    assert page.evaluate(me)[1] > 6
    # Running past the grace without holding is a foul.
    page.evaluate("run(() => th.phase === 'wait'); th.phase = 'run'; th.v = 8.5; th.x = 8.5 * 0.15; step(0.001)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Yliastuttu"]
    page.evaluate("quick()")
    assert page.evaluate(me)[2] == -1
    # The clean zone: the green last stretch before the line and the grace after it are at least
    # 180 ms of running at top speed; an early release only costs distance.
    zone, grace = page.evaluate("[ZONE, GRACE]")
    assert zone + grace >= 0.18 and grace >= 0.08
    assert mark(page, -0.5, 8.5, 20)["mark"] < mark(page, -0.1, 8.5, 20)["mark"]
    assert page.errors == []


def test_running_takes_alternate_feet_and_the_same_foot_twice_slows(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001)")
    page.evaluate("for (let i = 0; i < 24; i++) { press(i % 2 + 1); step(1 / 8); }")
    v = page.evaluate("th.v")
    assert 7.5 <= v <= 9
    assert page.evaluate("[th.phase, th.x < 0]") == ["run", True]
    page.evaluate("press(th.foot)")
    assert page.evaluate("th.v") < v
    assert page.errors == []


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.throwers.length, K.comp.round, th.mine, th.phase]") == [12, 1, True, "wait"]
    for rnd in range(1, 7):
        assert page.evaluate("K.comp.round") == rnd
        page.evaluate("go(9, 20, -0.05); quick()")
        # The record is saved the moment the jumper lands.
        if rnd == 1:
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pituushyppy:ennatys'))") > 6.6
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pituushyppy:kesken')).round") == 2
    assert page.evaluate("K.comp.over && K.ending.at === 0")
    assert page.evaluate("K.comp.final.length") == 8
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:pituushyppy:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.is_hidden("#cont")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("go(8, 20, -0.2); quick()")
    first = page.evaluate("K.comp.throwers.find(t => t.p === 'me').marks[0]")
    assert first > 5
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    page.click("#cont")
    assert page.evaluate("[K.comp.round, K.comp.throwers.find(t => t.p === 'me').marks[0], th.mine]") == [2, first, True]
    page.evaluate("K.quit(); showMenu()")
    page.click("#go")
    assert page.evaluate("[K.comp.round, K.comp.throwers.find(t => t.p === 'me').marks.length]") == [1, 0]
    assert page.errors == []


def test_three_fouls_leave_you_out_of_the_final_eight(site, context):
    page = open_game(site, context)
    page.click("#go")
    for _ in range(3):
        page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.x = -0.05; th.v = 8; step(0.2); quick()")
    assert page.evaluate("K.comp.over && !K.ending.fin")
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert "ei finaaliin" in page.inner_text("#result")
    assert page.evaluate("localStorage.getItem('ai-pelit:pituushyppy:voitot')") == "0"
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
      // One jump: run-up speed v, letting go dt seconds from the line (negative: before it), the
      // angle ang, the legs q seconds before the sand (null: never). Past the grace it is a foul.
      window.jumpAs = (v, dt, ang, q) => {
        if (th.phase === 'wait') { th.t = 99; step(0.001); }
        th.phase = 'run'; th.v = v; th.x = -1;
        startAim(1); th.aimT = (ang - AIM0) / AIM_RATE; th.ang = ang; th.x = v * dt;
        step(0.0001);
        if (th.phase === 'aim') {
          release();
          if (q !== null) { th.ft = th.f.t - q; legs(); }
          th.ft = th.f.t; step(0.001);
        }
        th.t = 99; step(0.001);
      };
      // A fair player: about 8.4 m/s (eight to nine taps a second), letting go about 50 ms before
      // the line give or take 60 ms, the angle 20° give or take 3°, the legs on time give or take 80 ms.
      window.fair = () => jumpAs(8.4 + gs() * 0.3, -0.05 + gs() * 0.06, 20 + gs() * 3, 0.23 + gs() * 0.08);
      // A strong player: fast tapping (9.4 m/s) and clean timing.
      window.strong = () => jumpAs(9.4 + gs() * 0.15, -0.02 + gs() * 0.03, 20 + gs() * 1.5, 0.23 + gs() * 0.04);
      // A lazy one: slow, letting go far back, flat, never the legs.
      window.lazy = () => jumpAs(6.5, -0.15, 12, null);
      // Whole meets alone at level lv: how many of k the player wins.
      window.meets = (lv, k, play) => {
        let won = 0;
        for (let i = 0; i < k; i++) {
          K.level = lv; K.quit(); soloComp();
          while (!K.ending) play();
          if (K.ending.at === 0) won++;
          K.ending = null;
        }
        return won;
      };
    }""")
    # With this seed 20, 13 and 0 of 20 for fair play at levels 1, 4 and 9, 14 for strong play at
    # level 9, 0 for lazy play at level 1 (seeds 2, 3, 7 and 42 gave 19-20, 11-14, 0, 12-16, 0).
    fair1, fair4, fair9, strong9, lazy1 = page.evaluate(
        "[meets(1, 20, fair), meets(4, 20, fair), meets(9, 20, fair), meets(9, 20, strong), meets(1, 20, lazy)]")
    assert fair1 >= 17          # level 1 is nearly always won by fair play
    assert 6 <= fair4 <= 17     # a middle level is a contest
    assert fair9 <= 3           # the top level is rarely won by fair play...
    assert strong9 >= 6         # ...but a fast, clean jumper can win it
    assert lazy1 == 0           # lazy play never wins, even at level 1
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 6.23, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("K.comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.marks = [7.88, -1, 6.77]; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    # The jumper on the runway fits under the score panel, and so does the top of a jump.
    assert page.evaluate("groundY - 2.6 * runS") > page.evaluate("hudTop + 64")
    assert page.evaluate("groundY - (H0 + 0.6 + 0.9) * flyS") > page.evaluate("hudTop + 64")
    page.evaluate("go(9, 20, -0.05, null); th.ft = 0.3; draw()")
    assert page.errors == []


def test_turning_the_phone_keeps_the_jump(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.x = -12; th.v = 7")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate("[th.phase, th.x > -13, land]") == ["run", True, True]
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    assert page.evaluate("[th.phase, K.comp.round]") == ["run", 1]
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


def jumper_page(pages):
    """The phone whose turn it is, by the host's competition."""
    pid = pages[0].evaluate("K.current() && K.current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_jump_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("K.comp.order.join()") == host.evaluate("K.comp.order.join()") for p in pages)
    # The first player on a phone jumps; the others watch the same jump land on the same mark.
    first = jumper_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("go(8.5, 20, -0.1, 0.2)")
    want = first.evaluate("jumpMark(th.relX, th.vrel, th.ang, th.q, th.wind).mark")
    assert want > 5
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'land'", timeout=5000)
        assert p.evaluate("th.mark") == want
    first.evaluate("quick()")
    seq = host.evaluate("K.comp.seq")
    for p in pages:
        p.wait_for_function(f"K.comp.seq === {seq}", timeout=5000)
    assert host.evaluate("K.comp.throwers.find(t => t.name === 'Eero' || t.name === 'Aino' || t.name === 'Ville') !== undefined")
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"K.comp && K.comp.seq === {seq} && th", timeout=10000)
    # Everyone jumps on until the end.
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = jumper_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("go(8.5, 20, -0.1); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("K.ending ? K.ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (K.ending) { K.ending.t = 99; step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:pituushyppy:kisat')") == "1"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:pituushyppy:ennatys'))") > 5
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_guest_cannot_jump_out_of_turn_and_an_away_phone_is_jumped_for(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    if jumper_page(pages) is host:
        n = host.evaluate("K.comp.seq")
        aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: K.comp.room, seq: {n}, mark: 9.99 }})")
        host.wait_for_timeout(300)
        assert host.evaluate("K.comp.seq") == n
        host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("go(8, 20, -0.1); quick()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("K.comp.seq")
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    # "Jatka ilman heitä": the computer jumps Aino's turn.
    host.click("#aipr-goOn")
    host.wait_for_function(f"K.comp.seq > {n} && K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=5000)
    relay.back(aino)
    host.wait_for_function("!K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=8000)
    aino.wait_for_function(f"K.comp && K.comp.seq > {n}", timeout=8000)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_in_a_room_only_a_turn_with_no_taps_times_out(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    p = jumper_page(pages)
    p.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
    p.evaluate("""() => {
        th.phase = 'run';
        for (let s = 0; s < 60; s++) { th.x = -20; press(s % 2 + 1); for (let i = 0; i < 60; i++) step(1 / 60); }
    }""")
    assert p.evaluate("[th.phase, th.why]") == ["run", ""]
    p.evaluate("th.x = -20; th.v = 0; run(() => th.phase === 'run', 50)")
    assert p.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Aika loppui"]
    for q in pages:
        assert q.errors == []
        q.context.close()


def test_a_meet_kept_by_v1_goes_on_in_v2_and_the_saves_carry_over(site, context):
    # v1 and v2 share the saves: a meet left unfinished in v1 goes on here.
    v1 = open_game(site, context)
    v1.goto(site.url + "games/pituushyppy/v1/")
    v1.evaluate(HELPERS)
    v1.click("#go")
    v1.evaluate("go(8, 20, -0.2); quick()")
    first = v1.evaluate("comp.throwers.find(t => t.p === 'me').marks[0]")
    v1.goto(site.url + URL)
    v1.evaluate(HELPERS)
    assert v1.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    assert "Ennätys" in v1.inner_text("#stats")
    v1.click("#cont")
    assert v1.evaluate("[K.comp.round, K.mine().marks[0], th.mine]") == [2, first, True]
    assert v1.errors == []


def test_the_jump_bar_sits_above_the_feet_and_the_gap_does_nothing(site, context):
    # v2 (Keihäänheitto v3's controls, #166): upright the jump is a full-width bar above the feet.
    page = open_game(site, context)
    page.click("#go")
    jump, left, right = page.evaluate("pads()")
    assert [jump["k"], left["k"], right["k"]] == [3, 1, 2]
    assert jump["w"] > 300 and jump["y"] + jump["h"] + 18 <= left["y"] and left["y"] == right["y"]
    gap = jump["y"] + jump["h"] + 9
    assert page.evaluate(f"padAt(180, {gap})") == 0
    assert page.evaluate(f"[padAt(180, {jump['y'] + 10}), padAt(60, {left['y'] + 20}), padAt(300, {left['y'] + 20})]") == [3, 1, 2]
    # Sideways too: the gap between each column's jump pad and its foot does nothing.
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    pl = page.evaluate("pads()")
    for top, foot in ((pl[0], pl[1]), (pl[2], pl[3])):
        cx = top["x"] + top["w"] / 2
        assert page.evaluate(f"padAt({cx}, {top['y'] + top['h'] + 9})") == 0
        assert page.evaluate(f"[padAt({cx}, {top['y'] + 10}), padAt({cx}, {foot['y'] + 20})]") == [3, foot["k"]]
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    # The yellow zone: start holding there, and the angle is green at the line.
    z = page.evaluate("zones(8.5)")
    lo, hi = page.evaluate("GREEN")
    for start in (z["y0"] + 0.05, z["y1"] - 0.05):
        page.evaluate(f"th.t = 99; step(0.001); th.phase = 'run'; th.v = 8.5; th.x = {start}; startAim(1); run(() => th.phase === 'aim', 2)")
        assert page.evaluate("[th.phase, th.relX]") == ["fly", 0]
        assert lo - 1 <= page.evaluate("th.ang") <= hi + 1
        page.evaluate("quick()")
    assert page.errors == []
