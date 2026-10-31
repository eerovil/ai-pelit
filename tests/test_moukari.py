"""Moukarinheitto v1: swing, turn in rhythm, let go into the sector; a six-round meet (#153)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/moukari/v1/"

# Test helpers in the page: run(cond, max) steps the game 1/120 s at a time; tapAt(n, err) waits
# for the n-th low point and taps Vauhtia err seconds before it; letGo(dev) waits until the hammer
# is where letting go throws dev degrees off the middle and presses Irti!; spin(turns, err, dev)
# is a whole throw: a tap at every low point up to the one that starts the last turn, and the
# release in that turn; quick() lands it and reports it.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 120) step(1 / 120); };
  window.tapAt = (n, err = 0) => {
    run(() => th.phase === 'spin' && (n * TAU - th.a) / omega(th.a, th.v) > err, 5);
    if (th.phase === 'spin') press(1);
  };
  window.letGo = (dev = 0) => {
    const at = ((PHI_REL + dev * DEG / HELP - PHI_LOW) % TAU + TAU) % TAU;
    let T = Math.floor(th.a / TAU) * TAU + at;
    if (T < th.a) T += TAU;
    run(() => th.phase === 'spin' && th.a < T, 5);
    press(2);
  };
  window.spin = (turns = 4, err = 0, dev = 0) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    press(1);
    for (let n = 1; n < SWINGS + turns; n++) tapAt(n, err);
    if (th.phase === 'spin') letGo(dev);
  };
  window.quick = () => {
    if (th.jav) { th.jav.acc = 30; step(0.001); }
    th.t = 99; step(0.001);
  };
}"""


# Math.random seeded (mulberry32) before the game loads, so the computer's skills and throws and
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


def open_game(site, context, saved=None, seed=1):
    site.build(ROOT / "games")
    page = context.new_page()
    page.add_init_script(SEEDED % seed)
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:moukari:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def start(page):
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001)")


def test_speed_throws_further_and_the_mark_is_from_the_rim(site, context):
    page = open_game(site, context)
    assert page.evaluate("range(29.4)") == pytest.approx(85, abs=2)
    assert page.evaluate("range(26)") == pytest.approx(67, abs=2)
    assert page.evaluate("range(9)") < 12
    # Let go on the right side the hammer goes straight down the middle of the sector.
    f = page.evaluate("flight(5 * TAU + ((PHI_REL - PHI_LOW) % TAU + TAU) % TAU, 27)")
    assert f["why"] == "" and abs(f["dev"]) < 0.01 and abs(f["lx"]) < 0.01
    # Measured from the inside of the rim (the centre less 1.0675 m), down to the centimetre.
    assert f["mark"] == pytest.approx(f["ly"] - 1.0675, abs=0.011)
    assert f["mark"] == int(f["mark"] * 100 + 1e-6) / 100
    assert page.errors == []


def test_wide_throws_go_out_of_the_sector_or_into_the_cage(site, context):
    page = open_game(site, context)
    at = "(dev => 5 * TAU + ((PHI_REL + dev * DEG / HELP - PHI_LOW) % TAU + TAU) % TAU)"
    for dev, why in [(0, ""), (15, ""), (-15, ""), (19, "Sektorin ulkopuolelle"), (-20, "Sektorin ulkopuolelle"),
                     (30, "Osui häkkiin"), (-45, "Osui häkkiin"), (120, "Osui häkkiin")]:
        f = page.evaluate(f"flight({at}({dev}), 27)")
        assert f["why"] == why, dev
        assert (f["mark"] < 0) == bool(why)
    # A hammer into the net stops there and drops.
    page.click("#go")
    page.evaluate("spin(4, 0, 40); run(() => th.phase === 'fly', 6)")
    assert page.evaluate("[th.phase, th.mark, th.why, th.jav.s <= th.jav.stopS + 1e-6]") == ["land", -1, "Osui häkkiin", True]
    assert page.evaluate("Math.hypot(...hammerAt(th.jav).slice(0, 2))") < 7.5
    assert page.errors == []


def test_rhythm_taps_add_speed_and_bad_taps_lose_it(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("press(1)")
    assert page.evaluate("[th.phase, th.v]") == ["spin", 9]
    # On the low point: faster. Out of rhythm: slower.
    page.evaluate("tapAt(1, 0)")
    v1 = page.evaluate("th.v")
    assert v1 > 14
    page.evaluate("run(() => th.a < 1.5 * TAU); press(1)")
    assert page.evaluate("th.v") == pytest.approx(v1 - 1.6, abs=0.01)
    # Irti! does nothing in the swings, before the first turn's low point.
    page.evaluate("run(() => th.a < 1.9 * TAU); press(2)")
    assert page.evaluate("th.phase") == "spin"
    # A second tap in the same window does nothing more.
    page.evaluate("tapAt(2, 0)")
    v2 = page.evaluate("th.v")
    page.evaluate("press(1)")
    assert page.evaluate("th.v") == v2
    # A low point with no tap slows a little.
    page.evaluate("run(() => th.a < 3 * TAU + 1)")
    assert page.evaluate("th.v") == pytest.approx(v2 - 0.8, abs=0.01)
    assert page.errors == []


def test_fouls_in_the_circle(site, context):
    page = open_game(site, context)
    start(page)
    # Out of rhythm at the red speed: the hammer pulls the thrower out of the circle.
    page.evaluate("press(1); for (let n = 1; n <= 4; n++) tapAt(n, 0)")
    assert page.evaluate("th.v") >= page.evaluate("RED")
    page.evaluate("run(() => th.a < 4.5 * TAU); press(1)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Rytmi petti: ulos ympyrästä"]
    page.evaluate("quick()")
    assert page.evaluate("comp.throwers.find(t => t.p === 'me').marks") == [-1]
    # Not letting go before the low point that would start a fifth turn.
    page.evaluate("run(() => th.phase === 'wait'); th.t = 99; step(0.001); press(1); run(() => th.phase === 'spin', 30)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Ei irti ajoissa: ulos ympyrästä"]
    assert page.evaluate("th.a") == pytest.approx(6 * 6.2832, abs=0.2)
    assert page.errors == []


def test_the_fifth_turn_never_starts_so_a_release_in_it_cannot_score(site, context):
    page = open_game(site, context)
    start(page)
    # Every low point tapped up to the one that starts the fourth turn: the fastest legal hammer.
    page.evaluate("press(1); for (let n = 1; n < LAPS; n++) tapAt(n, 0)")
    assert page.evaluate("[th.phase, Math.floor(th.a / TAU) - SWINGS + 1]") == ["spin", 4]
    # Waiting for the release spot after the fourth turn ends: the foul comes at the low point first.
    page.evaluate("run(() => th.phase === 'spin' && th.a < LAPS * TAU + ((PHI_REL - PHI_LOW) % TAU + TAU) % TAU)")
    assert page.evaluate("[th.phase, th.mark, th.why, th.jav]") == ["land", -1, "Ei irti ajoissa: ulos ympyrästä", None]
    page.evaluate("press(2)")
    assert page.evaluate("[th.jav, th.mark]") == [None, -1]
    # Let go in the fourth turn instead, and it scores.
    page.evaluate("quick(); run(() => th.phase === 'wait'); th.t = 99; step(0.001); press(1); for (let n = 1; n < LAPS; n++) tapAt(n, 0)")
    page.evaluate("letGo(0)")
    assert page.evaluate("[th.phase, th.a > (LAPS - 1) * TAU, th.a < LAPS * TAU]") == ["fly", True, True]
    page.evaluate("quick()")
    assert page.evaluate("comp.throwers.find(t => t.p === 'me').marks[1]") > 0
    assert page.errors == []


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[comp.throwers.length, comp.round, th.mine, th.phase]") == [12, 1, True, "wait"]
    for rnd in range(1, 7):
        assert page.evaluate("comp.round") == rnd
        page.evaluate("spin(4, 0.01, 0); quick()")
        # The record is saved the moment it lands.
        if rnd == 1:
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:moukari:ennatys'))") > 80
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:moukari:kesken')).round") == 2
    assert page.evaluate("comp.over && ending.at === 0")
    assert page.evaluate("comp.final.length") == 8
    page.evaluate("ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:moukari:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.is_hidden("#cont")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("spin(3, 0.02, 5); quick()")
    first = page.evaluate("comp.throwers.find(t => t.p === 'me').marks[0]")
    assert first > 50
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    page.click("#cont")
    assert page.evaluate("[comp.round, comp.throwers.find(t => t.p === 'me').marks[0], th.mine]") == [2, first, True]
    page.evaluate("comp = null; th = null; showMenu()")
    page.click("#go")
    assert page.evaluate("[comp.round, comp.throwers.find(t => t.p === 'me').marks.length]") == [1, 0]
    assert page.errors == []


def test_three_fouls_leave_you_out_of_the_final_eight(site, context):
    page = open_game(site, context)
    page.click("#go")
    for _ in range(3):
        page.evaluate("spin(4, 0, 25); quick()")
    assert page.evaluate("comp.over && !ending.fin")
    page.evaluate("ending.t = 99; step(0.01)")
    assert "ei finaaliin" in page.inner_text("#result")
    assert page.evaluate("localStorage.getItem('ai-pelit:moukari:voitot')") == "0"
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("""() => {
      window.fresh = () => { th = Object.assign({}, th, { phase: 'ready', a: 0, v: 0, chk: 0, tapped: {}, jav: null, mark: null, out: null }); };
      window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
      window.many = (k, play) => { const out = []; for (let i = 0; i < k; i++) { fresh(); play(); out.push(th.mark); } return out; };
      // A fair player: every tap a normal 0.05 s off the low point, letting go about 6° off.
      window.fair = () => { press(1); for (let n = 1; n < LAPS; n++) tapAt(n, gs() * 0.05); if (th.phase === 'spin') letGo(gs() * 6); };
      // Whole meets alone at level lv, the player throwing fair: how many of k they win.
      window.meets = (lv, k) => {
        let won = 0;
        for (let i = 0; i < k; i++) {
          level = lv; comp = null; th = null; ending = null; soloComp();
          while (!ending) { th.t = 99; step(0.001); fair(); quick(); }
          if (ending.at === 0) won++;
          ending = null;
        }
        return won;
      };
    }""")
    skills = lambda lv: page.evaluate(f"newComp('solo', [{{ name: 'x', p: 'me' }}], {lv}).throwers.slice(1).map(t => t.skill)")
    # Lazy: one tap to start, no rhythm, let go in the first turn. Short, far behind level 1.
    lazy = page.evaluate("many(20, () => { press(1); run(() => th.a < 3 * TAU + 0.1); letGo(0); })")
    assert max(lazy) < min(skills(1)) - 10
    # Reckless: tapping Vauhtia eight times a second and letting go in the fourth turn.
    wild = page.evaluate("many(20, () => { press(1); for (let i = 0; i < 80 && th.phase === 'spin' && th.a < 5 * TAU + 3; i++) { run(() => true, 0.125); press(1); } if (th.phase === 'spin') letGo(0); })")
    assert max(wild) < min(skills(1))
    # Fair play wins nearly every meet at level 1, under half at level 7 and hardly any at level 9:
    # with this seed 20, 8 and 0 of 20 (other seeds gave 20, 9, 0; 20, 10, 2; 20, 8, 0).
    l1, l7, l9 = page.evaluate("[meets(1, 20), meets(7, 20), meets(9, 20)]")
    assert l1 >= 18
    assert l7 <= 12
    assert l9 <= 4
    # Perfect timing still beats the strongest computer at the top level.
    page.evaluate("comp = null; ending = null; level = 1; soloComp(); th.t = 99; step(0.001)")
    top = page.evaluate("many(1, () => { press(1); for (let n = 1; n < LAPS; n++) tapAt(n, 0); letGo(0); })")[0]
    assert top > max(skills(30)) + 2
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_cage_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 71.23, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.marks = [88.88, -1, 77.77]; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    # Close up, the whole cage is in the scene under the score panel; in flight, the sector to 90 m.
    pts = page.evaluate("blend = 0; camera(0); X0 = SW / 2; Y0 = (hudTop + 64 + sceneB) / 2; CAGE.map(q => P(q[0], q[1]))")
    top, bottom, sw = page.evaluate("[hudTop + 64, sceneB, SW]")
    for px, py in pts:
        assert 0 <= px <= sw and top - 30 <= py <= bottom, (px, py)
    far = page.evaluate("blend = 1; camera(0); [P(Math.sin(HALF) * 91, Math.cos(HALF) * 91), P(-Math.sin(HALF) * 91, Math.cos(HALF) * 91)]")
    for px, py in far:
        assert 0 <= px <= sw and 0 <= py <= bottom, (px, py)
    assert page.errors == []


def test_turning_the_phone_keeps_the_throw(site, context):
    page = open_game(site, context)
    start(page)
    page.evaluate("press(1); tapAt(1); tapAt(2); run(() => th.a < 2.5 * TAU)")
    a, v = page.evaluate("[th.a, th.v]")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    # The hammer keeps going round (real time passes, so a low point may go by untapped).
    assert page.evaluate("[th.phase, th.a >= %f, th.v > %f - 2, land]" % (a, v)) == ["spin", True, True, True]
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
        p.wait_for_function("comp && comp.throwers.length === 12 && th", timeout=8000)
    return relay, pages


def thrower_page(pages):
    """The phone whose turn it is, by the host's competition."""
    pid = pages[0].evaluate("current() && current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_throw_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("comp.order.join()") == host.evaluate("comp.order.join()") for p in pages)
    # The first player on a phone throws; the others watch the same hammer fly and land.
    first = thrower_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("spin(4, 0.01, 3)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'fly'", timeout=5000)
        assert p.evaluate("th.mark") == first.evaluate("th.mark")
    first.evaluate("quick()")
    seq = host.evaluate("comp.seq")
    for p in pages:
        p.wait_for_function(f"comp.seq === {seq}", timeout=5000)
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"comp && comp.seq === {seq} && th", timeout=10000)
    # Everyone throws on until the end; one throw goes into the cage.
    for i in range(40):
        if host.evaluate("comp === null || comp.over"):
            break
        p = thrower_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("comp.seq")
        p.evaluate(f"spin(4, 0.01, {40 if i == 1 else 0}); quick()")
        host.wait_for_function(f"comp.seq > {n} || comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("ending ? ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (ending) { ending.t = 99; step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:moukari:kisat')") == "1"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:moukari:ennatys'))") > 70
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_foul_in_the_circle_shows_on_every_phone_and_an_away_phone_is_thrown_for(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    # A result from the phone whose turn it is not is ignored.
    if thrower_page(pages) is host:
        n = host.evaluate("comp.seq")
        aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: comp.room, seq: {n}, mark: 99 }})")
        host.wait_for_timeout(300)
        assert host.evaluate("comp.seq") == n
        host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("spin(4, 0.01, 0); quick()")
    aino.wait_for_function("th && th.mine && th.phase === 'ready'", timeout=8000)
    # Aino never lets go: out of the circle, and the host sees it.
    aino.evaluate("press(1); run(() => th.phase === 'spin', 30)")
    host.wait_for_function("th && th.phase === 'land' && th.why === 'Ei irti ajoissa: ulos ympyrästä'", timeout=5000)
    n = host.evaluate("comp.seq")
    aino.evaluate("quick()")
    host.wait_for_function(f"comp.seq > {n}", timeout=5000)
    assert host.evaluate("comp.throwers.find(t => t.name === 'Aino').marks[0]") == -1
    # Aino's next turn: her phone drops out, and the computer throws for her.
    for _ in range(4):
        if host.evaluate("current() && current().name === 'Aino'"):
            break
        host.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("spin(4, 0.01, 0); quick()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("comp.seq")
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"comp.seq > {n} && comp.throwers.find(t => t.name === 'Aino').bot", timeout=5000)
    relay.back(aino)
    host.wait_for_function("!comp.throwers.find(t => t.name === 'Aino').bot", timeout=8000)
    aino.wait_for_function(f"comp && comp.seq > {n}", timeout=8000)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_in_a_room_a_minute_with_no_tap_is_a_foul(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    p = thrower_page(pages)
    p.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
    p.evaluate("run(() => th.phase === 'ready', 59)")
    assert p.evaluate("th.phase") == "ready"
    p.evaluate("run(() => th.phase === 'ready', 2)")
    assert p.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Aika loppui"]
    for q in pages:
        assert q.errors == []
        q.context.close()
