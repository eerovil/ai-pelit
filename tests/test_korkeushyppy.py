"""Korkeushyppy v1: a J run-up, a take-off, a flop with two taps; the bar rises (#153)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/korkeushyppy/v1/"

# Test helpers in the page: run(cond, max) steps the game 1/60 s at a time; go(d, v, a, k) takes
# off at once d metres before the bar at v m/s and taps over the bar at a and k seconds of flight
# (null: no tap); quick() lands it and reports it; ready() skips the standings to the run.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); };
  window.ready = () => { if (th.phase === 'wait') { th.t = 99; step(0.001); } };
  window.go = (d, v, a, k) => {
    ready();
    th.phase = 'run'; th.v = v; th.x = -d;
    jumpPress();
    const f = th.f;
    for (const at of [a, k]) { if (at === null) continue; while (f.t < at - 1e-9 && !f.done) flyStep(f); airTap(); }
  };
  window.quick = () => {
    if (th.f && !th.f.done) { th.f.acc = 99; step(0.001); }
    th.t = 99; step(0.001);
  };
  window.good = () => { go(1.05, 8, 0.3, 0.46); quick(); };
  window.bad = () => { go(1.05, 8, null, null); quick(); };
  window.mine = () => comp.jumpers.find(t => t.p === myId);
}"""


# Math.random seeded (mulberry32) before the game loads, so the computer's skills and attempts and
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
            page.evaluate(f"localStorage.setItem('ai-pelit:korkeushyppy:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def clears(page, d, v, a, k):
    """The highest bar this jump clears (the lowest pass of the body over the plane of the bar)."""
    return page.evaluate(f"jumpResult({d}, {v}, 0, {json.dumps(a)}, {json.dumps(k)}).min")


def best_clear(page, d, v):
    """The highest bar a jump from d at v clears with the best-timed taps."""
    return page.evaluate(f"""() => {{
      let b = -9;
      for (let a = 0.15; a <= 0.6; a += 0.03) for (let k = a + 0.09; k <= 0.8; k += 0.03) b = Math.max(b, jumpResult({d}, {v}, 0, a, k).min);
      return b;
    }}""")


def test_the_flop_needs_the_take_off_spot_the_arch_and_the_legs(site, context):
    page = open_game(site, context)
    good = clears(page, 1.05, 8, 0.3, 0.46)
    assert 1.95 <= good <= 2.12
    # Without arching the hips sit low: well under the arched jump.
    assert clears(page, 1.05, 8, None, 0.46) < good - 0.1
    # Speed lifts: a slower run clears less.
    assert clears(page, 1.05, 6, 0.3, 0.46) < good - 0.15
    # Taking off in the green clears near the best; too close or too far knocks the bar.
    zone = page.evaluate("ZONE")
    top = best_clear(page, 1.05, 8)
    for d in zone:
        assert best_clear(page, d, 8) > top - 0.06, d
    assert best_clear(page, 0.4, 8) < top - 0.15
    assert best_clear(page, 2.2, 8) < top - 0.15
    why = lambda d, a, k, bar=1.85: page.evaluate(f"jumpResult({d}, 8, {bar}, {json.dumps(a)}, {json.dumps(k)})")
    near, far = why(0.3, 0.3, 0.46), why(2.8, 0.3, 0.46)
    assert not near["ok"] and near["why"].startswith("Liian läheltä")
    assert not far["ok"] and far["why"].startswith("Liian kaukaa")
    # The taps: none, the legs never lifted, the arch or the legs too early.
    assert why(1.05, None, None)["why"].startswith("Kaarra selkä") or why(1.05, None, None)["why"].startswith("Nosta jalat")
    assert why(1.05, 0.3, None)["why"] == "Nosta jalat: napauta toisen kerran"
    assert why(1.05, 0.1, 0.46)["why"] == "Kaari liian aikaisin: hartiat osuivat"
    assert why(1.05, 0.2, 0.3)["why"] == "Jalat liian aikaisin: lantio putosi rimaan"
    assert why(1.05, 0.3, 0.46)["ok"]
    # Each tap has room: a tenth of a second of flight either way still clears 1.85.
    for a, k in [(0.26, 0.46), (0.36, 0.46), (0.3, 0.42), (0.3, 0.52)]:
        assert why(1.05, a, k)["ok"], (a, k)
    assert page.errors == []


def test_running_takes_alternate_feet_the_curve_caps_speed_and_running_past_fails(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready()")
    page.evaluate("for (let i = 0; i < 24; i++) { press(i % 2 + 1); step(1 / 8); }")
    v = page.evaluate("th.v")
    assert 6.5 <= v <= 9.5
    page.evaluate("press(th.foot)")
    assert page.evaluate("th.v") < v
    # On the curve, more than VCURVE is not carried.
    page.evaluate("th.x = -5; th.v = 10; run(() => th.x < -3, 1)")
    assert page.evaluate("th.v") < 8.6
    # A take-off before the curve does nothing; running on past the bar is a failure.
    page.evaluate("th.x = -12; jumpPress()")
    assert page.evaluate("th.phase") == "run"
    page.evaluate("th.x = -1; th.v = 6; run(() => th.phase === 'run', 2)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", "X", "Ohijuoksu: et ponnistanut"]
    page.evaluate("quick()")
    assert page.evaluate("mine().rec[0]") == "X"
    assert page.errors == []


def test_the_rules_attempts_passes_and_countback(site, context):
    page = open_game(site, context)
    page.click("#go")
    h0 = page.evaluate("comp.heights[0]")
    # Fail once, then pass: the failure carries, so the next height has two attempts left.
    page.evaluate("bad(); ready()")
    assert page.evaluate("[comp.hi, comp.att, (mine().rec[0] || '')]") == [0, 2, "X"]
    page.evaluate("pass(); quick()")
    assert page.evaluate("mine().rec[0]") == "X-"
    assert page.evaluate("comp.hi") == 1
    page.evaluate("bad()")
    assert page.evaluate("mine().run") == 2
    page.evaluate("bad()")
    assert page.evaluate("comp.over && mine().out")
    assert page.evaluate("mine().rec.slice(0, 2)") == ["X-", "XX"]
    page.evaluate("ending.t = 99; step(0.01)")
    assert "ei hyväksyttyä tulosta" in page.inner_text("#result")
    assert page.evaluate("localStorage.getItem('ai-pelit:korkeushyppy:voitot')") == "0"
    assert h0 == page.evaluate("heightsFor(1)[0]")
    # Countback: the same best height, fewer failures there first, then fewer in all.
    order = page.evaluate("""() => {
      comp = newComp('solo', [{ name: 'A', p: 'a' }, { name: 'B', p: 'b' }, { name: 'C', p: 'c' }, { name: 'D', p: 'd' }], 1);
      comp.jumpers.length = 4;
      const [a, b, c, d] = comp.jumpers;
      a.rec = ['O', 'XO', 'XXX']; b.rec = ['XO', 'O', 'XXX']; c.rec = ['O', 'O', 'XXX']; d.rec = ['XO', 'O', 'XXX'];
      const r = standings().map(t => t.name + placeOf(t)).join(' ');
      comp = null; return r;
    }""")
    assert order == "C1 B2 D2 A4"
    assert page.errors == []


def test_heights_rise_in_steps_that_never_grow(site, context):
    page = open_game(site, context)
    for lv in (1, 4, 9):
        hs = page.evaluate(f"heightsFor({lv})")
        steps = [round(b - a, 2) for a, b in zip(hs, hs[1:])]
        assert steps[0] == 0.05 and min(steps) == 0.02
        assert all(a >= b for a, b in zip(steps, steps[1:]))
    assert page.errors == []


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[comp.jumpers.length, th.mine, th.phase]") == [12, True, "wait"]
    page.evaluate("good()")
    first = page.evaluate("comp.heights[0]")
    # The record is saved the moment the bar stays up; the meet is kept for a reload.
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:korkeushyppy:ennatys'))") == first
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:korkeushyppy:kesken')).jumpers.length") == 12
    for _ in range(60):
        if page.evaluate("comp.over"):
            break
        # The last one in may stop once they have won.
        page.evaluate("ready(); if (lastIn(mine()) && bestOf(mine()) >= 1.95) { stopMeet(); quick(); } else good()")
    assert page.evaluate("comp.over && ending.place === 1")
    best = page.evaluate("ending.mark")
    assert best >= 1.9
    page.evaluate("ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:korkeushyppy:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:korkeushyppy:ennatys'))") == best
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.is_hidden("#cont")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("good()")
    rec = page.evaluate("mine().rec")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka kisaa (rima ")
    page.click("#cont")
    assert page.evaluate("[mine().rec, th.mine, th.phase]") == [rec, True, "wait"]
    # Kisaan! starts a new meet instead.
    page.evaluate("comp = null; th = null; showMenu()")
    page.click("#go")
    assert page.evaluate("mine().rec.length") == 0
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      window.gs = () => Math.sqrt(-2 * Math.log(1 - Math.random())) * Math.cos(2 * Math.PI * Math.random());
      // A fair player: full speed less a little, taking off a normal 0.25 m off 1.1 m (about 0.03 s
      // at 8 m/s), each tap a normal 0.04 s of flight off (0.09 s of the slowed play). The last one
      // in stops once they have won. Lazy: a slow run, no arch, only the legs.
      window.attempt = lazy => {
        ready();
        if (lastIn(mine()) && bestOf(mine()) > 0) stopMeet();
        else {
          th.phase = 'run'; th.v = lazy ? 6.5 : 8 - Math.abs(gs()) * 0.3; th.x = -(1.1 + gs() * 0.25); jumpPress();
          const f = th.f;
          for (const at of lazy ? [0.46 + gs() * 0.04] : [0.3 + gs() * 0.04, 0.46 + gs() * 0.04]) {
            while (f.t < at && !f.done) flyStep(f);
            airTap();
          }
        }
        quick();
      };
      // Whole meets alone at level lv: how many of k the player wins.
      window.meets = (lv, k, lazy = false) => {
        let won = 0;
        for (let i = 0; i < k; i++) {
          level = lv; comp = null; th = null; ending = null; soloComp();
          while (!ending) attempt(lazy);
          if (ending.place === 1) won++;
          ending = null;
        }
        return won;
      };
    }""")
    # With this seed 0, 20, 19, 6 and 12 of 20; other seeds gave 0, 20, 20, 6, 10; 0, 20, 19, 8, 7;
    # 0, 20, 19, 9, 13; 0, 19, 20, 13, 8.
    lazy, l1, l4, l7, l10 = page.evaluate("[meets(1, 20, true), meets(1, 20), meets(4, 20), meets(7, 20), meets(10, 20)]")
    assert lazy <= 2
    assert l1 >= 17 and l4 >= 13
    assert 3 <= l7 <= 17 and 3 <= l10 <= 17
    # The best-timed jump beats even the strongest computer jumper possible (base 1.90 + 0.06 + 0.015).
    best = max(clears(page, 1.05, 8, a / 100, k / 100) for a in range(24, 40, 3) for k in range(40, 56, 3))
    assert best > page.evaluate("base(99) + 0.075")
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 1.91, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("comp.jumpers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.rec = ['O', 'XO', 'XX']; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    # The pass button sits in the scene, under the messages, and passes on the finger lifting.
    page.evaluate("ready(); draw()")
    b = page.evaluate("actBoxes[0]")
    sx, sw = page.evaluate("[SX, SW]")
    assert b["x"] >= 0 and b["x"] + b["w"] <= sw and b["y"] + b["h"] < page.evaluate("groundY - 1.9 * runS")
    page.mouse.click(sx + b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)
    assert page.evaluate("[th.phase, th.mark]") == ["land", "-"]
    # The highest bar and a jumper over it fit under the score panel while flying.
    assert page.evaluate("groundY - 2.7 * flyS") > page.evaluate("hudTop + 64")
    assert page.errors == []


def test_turning_the_phone_keeps_the_jump(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.x = -12; th.v = 7")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate("[th.phase, th.x > -13, land]") == ["run", True, True]
    # And in the air.
    page.evaluate("th.x = -1; jumpPress()")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    assert page.evaluate("th.phase") in ("air", "land")
    assert page.evaluate("th.f !== null")
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
        p.wait_for_function("comp && comp.jumpers.length === 12 && th", timeout=8000)
    return relay, pages


def jumper_page(pages):
    """The phone whose turn it is, by the host's competition."""
    pid = pages[0].evaluate("current() && current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_jump_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("comp.order.join()") == host.evaluate("comp.order.join()") for p in pages)
    # The first player on a phone jumps; the others watch the same flop and see the same result.
    first = jumper_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("go(1.05, 8, 0.3, 0.46)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && (th.phase === 'air' || th.phase === 'land')", timeout=5000)
    first.evaluate("quick()")
    seq = host.evaluate("comp.seq")
    for p in pages:
        p.wait_for_function(f"comp.seq === {seq}", timeout=5000)
    assert len({p.evaluate("JSON.stringify(comp.jumpers.map(t => t.rec))") for p in pages}) == 1
    assert first.evaluate("mine().rec.join('')") == "O"
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"comp && comp.seq === {seq} && th", timeout=10000)
    # Everyone clears two heights, then fails three times: then the computer finishes the meet.
    for _ in range(40):
        if host.evaluate("comp === null || comp.over"):
            break
        p = jumper_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("comp.seq")
        p.evaluate("mine().rec.filter(r => r && r.includes('O')).length < 2 ? good() : bad()")
        host.wait_for_function(f"comp.seq > {n} || comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("ending ? ending.res.map(r => r.name + r.best + r.place).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (ending) { ending.t = 99; step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:korkeushyppy:kisat')") == "1"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:korkeushyppy:ennatys'))") >= 1.5
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_guest_cannot_jump_out_of_turn_and_an_away_phone_is_jumped_for(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    # A result from the phone whose turn it is not is ignored.
    if jumper_page(pages) is host:
        n = host.evaluate("comp.seq")
        aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: comp.room, seq: {n}, mark: 'O' }})")
        host.wait_for_timeout(300)
        assert host.evaluate("comp.seq") == n
        host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("good()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("comp.seq")
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    # "Jatka ilman heitä": the computer jumps Aino's turn.
    host.click("#aipr-goOn")
    host.wait_for_function(f"comp.seq > {n} && comp.jumpers.find(t => t.name === 'Aino').bot", timeout=5000)
    relay.back(aino)
    host.wait_for_function("!comp.jumpers.find(t => t.name === 'Aino').bot", timeout=8000)
    aino.wait_for_function(f"comp && comp.seq > {n}", timeout=8000)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_in_a_room_only_a_turn_with_no_taps_times_out(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    p = jumper_page(pages)
    p.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
    # A slow player, tapping once a second for 70 s, keeps the turn.
    p.evaluate("""() => {
        th.phase = 'run';
        for (let s = 0; s < 70; s++) { th.x = -15; press(s % 2 + 1); for (let i = 0; i < 60; i++) step(1 / 60); }
    }""")
    assert p.evaluate("[th.phase, th.why]") == ["run", ""]
    # Nothing pressed for a minute: a failure.
    p.evaluate("th.x = -15; th.v = 0; run(() => th.phase === 'run', 65)")
    assert p.evaluate("[th.phase, th.mark, th.why]") == ["land", "X", "Aika loppui"]
    for q in pages:
        assert q.errors == []
        q.context.close()
