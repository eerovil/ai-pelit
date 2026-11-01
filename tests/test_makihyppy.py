"""Mäkihyppy v1: the in-run, the take-off at the edge, the flight position, the telemark; a
two-round meet on points from the distance and the judges (#269)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/makihyppy/v1/"

# Test helpers in the page. jumpBot(tauAt, react, band, teleAt) plays one whole jump from the bar:
# it springs when tauAt seconds are left to the edge (null: never), looks at the flight position
# every `react` seconds and holds Taakse or Eteen when it is past `band`, and taps the telemark
# when the snow is teleAt seconds away (null: never). It returns the jump's result and reports it.
HELPERS = """() => {
  window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
  window.jumpBot = (tauAt, react, band, teleAt) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    action();
    let next = 0, teleDone = false, tapped = false;
    for (let i = 0; i < 2000 && th.phase !== 'land'; i++) {
      if (th.phase === 'inrun' && !tapped && tauAt !== null && (IN - th.s) / Math.max(1, th.v) <= tauAt) { action(); tapped = true; }
      if (th.phase === 'fly') {
        if (react !== null && th.ft >= next) { next = th.ft + react; th.inp = th.pos > band ? -1 : th.pos < -band ? 1 : 0; }
        if (!teleDone && teleAt !== null && th.ft > 0.6 && timeToLand(th) <= teleAt) { action(); teleDone = true; }
      }
      step(1 / 60);
    }
    const r = th.res;
    th.t = 99; step(0.001);
    return r;
  };
  // A fair player: springs about 60 ms before the edge give or take 80 ms, looks at the position
  // four times a second, sets the telemark 0.3 s before the snow give or take 0.2 s.
  window.fair = () => jumpBot(Math.max(-0.05, 0.06 + gs() * 0.08), 0.25, 0.12, 0.3 + gs() * 0.2);
  // A strong one: clean timing and a quick eye.
  window.strong = () => jumpBot(Math.max(-0.05, 0.06 + gs() * 0.03), 0.15, 0.05, 0.3 + gs() * 0.08);
  // A lazy one: never springs, hardly steers, never sets a telemark.
  window.lazy = () => jumpBot(null, 0.6, 0.4, null);
  // Whole meets alone at level lv: how many of k the player wins.
  window.meets = (lv, k, play) => {
    let won = 0;
    for (let i = 0; i < k; i++) {
      K.level = lv; K.drop('kesken'); K.quit(); soloComp();
      while (!K.ending) play();
      if (K.ending.at === 0) won++;
      K.ending = null; K.quit();
    }
    return won;
  };
}"""

# Math.random seeded (mulberry32) before the game loads, as in test_pituushyppy.py.
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
            page.evaluate(f"localStorage.setItem('ai-pelit:makihyppy:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def test_the_hill_and_the_points_follow_the_real_rules(site, context):
    page = open_game(site, context)
    # A good spring and a clean flight go past K, a perfect one about to the hill size.
    assert 136 <= page.evaluate("flightOf(UP, 0, 0)") <= 150
    assert page.evaluate("flightOf(UP, 0.1, 0)") > page.evaluate("flightOf(UP, 0.4, 0)") + 15
    assert page.evaluate("flightOf(UP, 0, 0)") > page.evaluate("flightOf(UP_NONE, 0, 0)") + 20
    # Wind against the jumper carries a little.
    assert 1 < page.evaluate("flightOf(UP, 0.1, 2) - flightOf(UP, 0.1, 0)") < 8
    # 60 points at K, 1.8 a metre; the distance to the half metre, never rounded up.
    assert page.evaluate("[distPoints(120), distPoints(130), distPoints(110), metresOf(124.9)]") == [60, 78, 42, 124.5]
    # Five judges; the highest and the lowest do not count.
    r = page.evaluate("judge(125.2, 'good', 0, 'tele', () => 0)")
    assert r["d"] == 125 and r["js"] == [20] * 5 and r["style"] == 60 and r["p"] == pytest.approx(69 + 60)
    r = page.evaluate("(() => { let i = 0; const n = [2, -2, 0, 0, 0]; return judge(120, 'good', 0, 'tele', () => n[i++]); })()")
    assert sorted(r["js"]) == [19.0, 20, 20, 20, 20] and r["style"] == 60
    # A fall costs most of the style; landing on both feet less.
    assert page.evaluate("judge(120, 'good', 0, 'fall', () => 0).style") <= 33
    assert page.evaluate("judge(120, 'good', 0, 'two', () => 0).style") == 54
    assert page.errors == []


def test_the_take_off_is_generous_in_time(site, context):
    page = open_game(site, context)
    got = page.evaluate("[0, 0.05, GOOD, 0.3, null].map(t => springOf(t).kind)")
    assert got == ["good", "good", "good", "early", "none"]
    assert page.evaluate("springOf(0.3).up") > page.evaluate("UP_NONE") + 1
    # Tapped just after the edge still springs, a little less.
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001); action(); while (th.phase === 'inrun') step(1 / 60); th.ft = 0.04; action()")
    assert page.evaluate("[th.spring.kind, th.spring.up > UP - 0.5, th.spring.up < UP]") == ["late", True, True]
    # Far up the in-run a tap is not a take-off yet.
    page.evaluate("th = null; K.quit(); soloComp(); th.t = 99; step(0.001); action(); step(0.5); action()")
    assert page.evaluate("th.tau === undefined")
    assert page.errors == []


def test_the_telemark_is_judged_by_time_before_the_snow(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("window.lands = []")
    for tele in (0.3, 1.5, None):
        page.evaluate("if (!th || K.ending) { K.ending = null; K.quit(); soloComp(); }")
        r = page.evaluate(f"jumpBot(0.06, 0.15, 0.05, {json.dumps(tele)})")
        page.evaluate(f"lands.push({json.dumps(r['landing'])})")
    assert page.evaluate("lands") == ["tele", "early", "two"]
    assert page.errors == []


def test_doing_nothing_in_the_air_falls_or_drops_short(site, context):
    page = open_game(site, context)
    page.click("#go")
    rs = page.evaluate("[...Array(6)].map(() => { if (!th || K.ending) { K.ending = null; K.quit(); soloComp(); } return jumpBot(0.06, null, 0, 0.3); })")
    for r in rs:
        assert r["landing"] in ("fall", "hand") or r["d"] < 115, r
    assert page.errors == []


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.throwers.length, K.comp.round, th.mine, th.phase]") == [12, 1, True, "wait"]
    r = page.evaluate("strong()")
    assert r["d"] > 115
    # The longest jump and the meet so far are saved at once.
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:makihyppy:pisin'))") == r["d"]
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:makihyppy:kesken')).round") == 2
    page.evaluate("while (!K.ending) strong()")
    assert page.evaluate("K.comp.final.length") == 10
    assert page.evaluate("K.ending.at") == 0
    page.evaluate("K.ending.t = 99; K.skip(); step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:makihyppy:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert "Pisin " in page.inner_text("#stats") and "Paras kisa " in page.inner_text("#stats")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    first = page.evaluate("fair()")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka kisaa (kierros ")
    page.click("#cont")
    assert page.evaluate("K.mine().marks[0].d") == first["d"]
    assert page.evaluate("th.mine")
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    page.click("#go")
    # With this seed 18, 12 and 0 of 20 for fair play at levels 1, 4 and 9, 9 for strong play at
    # level 9, 0 for lazy play at level 1.
    fair1, fair4, fair9, strong9, lazy1 = page.evaluate(
        "[meets(1, 20, fair), meets(4, 20, fair), meets(9, 20, fair), meets(9, 20, strong), meets(1, 20, lazy)]")
    assert fair1 >= 15          # level 1 is nearly always won by fair play
    assert 5 <= fair4 <= 17     # a middle level is a contest
    assert fair9 <= 4           # the top level is rarely won by fair play...
    assert strong9 >= 4         # ...but a clean jumper can win it
    assert lazy1 == 0           # lazy play never wins, even at level 1
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 231.4, "kisat": 4, "voitot": 1, "taso": 2, "pisin": 128.5})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("K.comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.marks = [{ d: 131.5, p: 139.7 }]; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    page.evaluate("fair(); draw()")
    assert page.errors == []


def test_turning_the_phone_keeps_the_jump(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001); action(); while (th.phase === 'inrun') step(1 / 60); for (let i = 0; i < 60; i++) step(1 / 60)")
    ft = page.evaluate("th.ft")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate(f"[th.phase, th.ft >= {ft}, land]") == ["fly", True, True]
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    assert page.evaluate("[K.comp.round, th.mine]") == [1, True]
    assert page.errors == []


def test_the_pads_steer_and_the_scene_is_the_action(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001)")
    pads = page.evaluate("pads()")
    taakse = next(p for p in pads if p["k"] == 1)
    eteen = next(p for p in pads if p["k"] == 2)
    page.mouse.click(180, 300)   # the scene: off the bar
    assert page.evaluate("th.phase") == "inrun"
    page.evaluate("while (th.phase === 'inrun') step(1 / 60); step(0.3)")
    page.mouse.move(eteen["x"] + 40, eteen["y"] + 40)
    page.mouse.down()
    assert page.evaluate("th.inp") == 1
    page.mouse.up()
    assert page.evaluate("th.inp") == 0
    page.mouse.move(taakse["x"] + 40, taakse["y"] + 40)
    page.mouse.down()
    assert page.evaluate("th.inp") == -1
    page.mouse.up()
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
    """The phone whose turn it is, by the host's meet."""
    pid = pages[0].evaluate("K.current() && K.current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_jump_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("K.comp.order.join()") == host.evaluate("K.comp.order.join()") for p in pages)
    # The first player on a phone jumps; the others watch it fly and land on the same distance.
    first = jumper_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("action(); while (th.phase === 'inrun') step(1 / 60); for (let i = 0; i < 40; i++) step(1 / 60)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'fly'", timeout=5000)
    first.evaluate("th.inp = 0; while (th.phase === 'fly') { th.inp = th.pos > 0.05 ? -1 : th.pos < -0.05 ? 1 : 0; step(1 / 60); }")
    want = first.evaluate("th.res.d")
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'land'", timeout=5000)
        assert p.evaluate("th.res.d") == want
    first.evaluate("th.t = 99; step(0.001)")
    seq = host.evaluate("K.comp.seq")
    for p in pages:
        p.wait_for_function(f"K.comp.seq === {seq}", timeout=5000)
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
        p.evaluate("fair()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("K.ending ? K.ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (K.ending) { K.ending.t = 99; K.skip(); step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:makihyppy:kisat')") == "1"
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_guest_cannot_jump_out_of_turn_or_send_a_made_up_jump(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    n = host.evaluate("K.comp.seq")
    if jumper_page(pages) is host:
        aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: K.comp.room, seq: {n}, mark: {{ d: 140, p: 160 }} }})")
        host.wait_for_timeout(300)
        assert host.evaluate("K.comp.seq") == n
        host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("fair()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("K.comp.seq")
    # A mark that no jump could make is not taken.
    aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: K.comp.room, seq: {n}, mark: {{ d: 999, p: 999 }} }})")
    host.wait_for_timeout(300)
    assert host.evaluate("K.comp.seq") == n
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    # "Jatka ilman heitä": the computer jumps Aino's turn.
    host.click("#aipr-goOn")
    host.wait_for_function(f"K.comp.seq > {n} && K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=5000)
    for p in pages:
        assert p.errors == []
        p.context.close()
