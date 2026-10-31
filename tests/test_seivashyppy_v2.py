"""Seiväshyppy v2 (#165): v1 on the shared athletics library's bar-height format; v1's tests on v2."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/seivashyppy/v2/"

# Test helpers in the page: run(cond, max) steps the game 1/60 s at a time; go(v, px, sw, tr) plants
# at once at px metres with v m/s of run-up, swings the legs sw of the way up and lets go tr s after
# the plant; quick() lands it and reports it; fail() runs through; skip() passes the height.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); };
  window.ready = () => { if (th.phase === 'wait') { th.t = 99; step(0.001); } };
  window.go = (v, px = -4, sw = 1, tr = 1.0) => {
    ready();
    th.phase = 'run'; th.v = v; th.x = px;
    hold(1); th.sw = sw; th.tau = tr; letGoPole();
  };
  window.quick = () => { run(() => th && th.phase === 'fly', 6); th.t = 99; step(0.001); };
  window.fail = () => { ready(); th.phase = 'run'; th.x = -2; th.v = 8; step(0.02); th.t = 99; step(0.001); };
  window.skip = () => { ready(); pass(); };
  window.me = () => K.mine();
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
            page.evaluate(f"localStorage.setItem('ai-pelit:seivashyppy:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def test_speed_matters_most_then_the_plant_the_swing_and_the_push(site, context):
    page = open_game(site, context)
    clear = lambda v, px=-4, sw=1, tr=1.0: page.evaluate(f"vaultResult({px}, {v}, {sw}, {tr}).clear")
    assert 4.8 <= clear(8.3) <= 5.2
    assert clear(9.5) > clear(8.3) + 0.8
    assert clear(7) < clear(8.3) - 0.8
    # A plant at the edge of the green, legs left down, letting go early or late: each costs height.
    assert clear(8.3, px=-4.75) < clear(8.3) - 0.5
    assert clear(8.3, sw=0) < clear(8.3) - 0.8
    assert clear(8.3, tr=0.5) < clear(8.3) - 1
    assert clear(8.3, tr=1.45) < clear(8.3) - 0.5
    assert clear(8.3, tr=0.85) > clear(8.3) - 0.35
    # Too slow and the pole never stands up.
    assert page.evaluate("vaultResult(-4, 4, 1, 1).stall")
    assert page.errors == []


def test_run_throughs_too_early_too_late_or_never_and_a_slip_of_the_thumb(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.x = -5.2; th.v = 8; hold(1)")
    assert page.evaluate("[th.phase, th.res, th.why]") == ["land", "X", "Liian aikaisin: läpijuoksu"]
    page.evaluate("th.t = 99; step(0.001)")
    assert page.evaluate("me().rec[0]") == "X"
    page.evaluate("ready(); th.phase = 'run'; th.x = -3.0; th.v = 8; hold(1)")
    assert page.evaluate("th.why") == "Liian myöhään: läpijuoksu"
    page.evaluate("th.t = 99; step(0.001)")
    # Running past the green without planting.
    page.evaluate("ready(); th.phase = 'run'; th.x = -3.3; th.v = 8; run(() => th.phase === 'run', 1)")
    assert page.evaluate("th.why").startswith("Läpijuoksu")
    page.evaluate("th.t = 99; step(0.001)")
    # Three failures in a row: out, and the rest of the meet is vaulted at once.
    assert page.evaluate("[me().out, K.comp.over, K.ending.mark]") == [True, True, -1]
    assert page.errors == []


def test_a_stray_tap_at_the_start_or_far_from_the_zone_does_not_plant(site, context):
    page = open_game(site, context)
    page.click("#go")
    # Standing at the start (a tap that skipped the standings, or missed the pass button).
    page.evaluate("ready(); hold(1); letGo()")
    assert page.evaluate("[th.phase, th.res, me().rec[0] || '']") == ["ready", None, ""]
    # Running, but still well short of the green zone.
    page.evaluate("press(1); th.x = -12; th.v = 8; hold(1); letGo()")
    assert page.evaluate("[th.phase, th.res, th.px]") == ["run", None, None]
    # Just before the zone: still a run-through.
    page.evaluate("th.x = -5.5; hold(1)")
    assert page.evaluate("[th.phase, th.res, th.why]") == ["land", "X", "Liian aikaisin: läpijuoksu"]
    assert page.errors == []


def test_holding_swings_the_legs_up_and_letting_go_at_the_top_clears(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.x = -4; th.v = 8.3; hold(1)")
    assert page.evaluate("th.phase") == "pole"
    # Letting go of the press that planted the pole at once does not push off: still on the pole.
    page.evaluate("step(0.05); letGo()")
    assert page.evaluate("[th.phase, th.held]") == ["pole", False]
    page.evaluate("hold(1); run(() => th.tau < 0.99, 2)")
    assert page.evaluate("th.sw") > 0.95
    page.evaluate("letGo()")
    assert page.evaluate("[th.phase, th.res]") == ["fly", "O"]
    page.evaluate("quick()")
    assert page.evaluate("me().rec[0]") == "O"
    # The record is saved the moment the bar stays up.
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:seivashyppy:ennatys'))") == page.evaluate("K.comp.heights[0]")
    # Never letting go: the vaulter is let go of the pole half a second after it is straight.
    page.evaluate("run(() => !th.mine || th.phase === 'wait', 10); ready(); th.phase = 'run'; th.x = -4; th.v = 8.3; hold(1); run(() => th.phase === 'pole', 3)")
    assert page.evaluate("th.phase") == "fly" and 1.5 <= page.evaluate("th.tr") <= 1.55
    assert page.errors == []


def test_a_whole_meet_alone_passing_heights_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.throwers.length, K.comp.hi, th.mine, th.phase]") == [12, 0, True, "wait"]
    # Start at 3,70 m by passing the heights under it, then clear every height first time.
    for _ in range(60):
        if page.evaluate("K.comp.over"):
            break
        if page.evaluate("barH(K.comp.hi) < 3.7"):
            page.evaluate("skip()")
            continue
        if page.evaluate("soleWinner(me())"):
            page.evaluate("skip()")   # Lopeta kisa
            continue
        page.evaluate("go(9.2); quick()")
        if page.evaluate("barH(K.comp.hi - 1) === 3.7 && !K.comp.over"):
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:seivashyppy:kesken')).hi") >= 5
    assert page.evaluate("K.comp.over && K.ending.place === 1")
    assert page.evaluate("K.thrower(K.ending.res[0].id).rec.map(r => r || '').join('')").startswith("-----O")
    mark = page.evaluate("K.ending.mark")
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:seivashyppy:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:seivashyppy:ennatys'))") == mark
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.is_hidden("#cont")
    assert page.errors == []


def test_a_pass_after_a_failure_carries_it_and_three_in_a_row_is_out(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("fail()")
    page.evaluate("run(() => th.phase === 'wait'); skip()")   # passes its two other attempts at this height
    assert page.evaluate("[K.comp.hi, me().rec[0], me().run, me().out]") == [1, "X-", 1, False]
    page.evaluate("fail()")
    assert page.evaluate("[me().run, me().out]") == [2, False]
    page.evaluate("fail()")
    assert page.evaluate("[me().rec[1], me().out, K.comp.over]") == ["XX", True, True]
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert "ei hyväksyttyä tulosta" in page.inner_text("#result")
    assert page.evaluate("localStorage.getItem('ai-pelit:seivashyppy:voitot')") == "0"
    assert page.errors == []


def test_countback_fewer_failures_at_the_best_height_then_in_all(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("""() => {
      const [a, b, c, d] = K.comp.throwers;
      a.rec = ['O', 'XO', 'XXX'];
      b.rec = ['XO', 'O', 'XXX'];
      c.rec = ['O', 'O', 'XXX'];
      d.rec = ['XO', 'O', 'XXX'];
      K.comp.throwers.slice(4).forEach(t => t.rec = ['XXX']);
    }""")
    order = page.evaluate("standings().slice(0, 4).map(t => K.comp.throwers.indexOf(t))")
    assert order[:1] == [2]                       # cleared both first time
    assert order[1] in (1, 3) and order[2] in (1, 3)  # one failure, but at the lower height
    assert order[3] == 0                          # the failure at the best height counts most
    assert page.evaluate("[1, 3].map(i => placeOf(K.comp.throwers[i]))") == [2, 2]   # shared
    assert page.evaluate("placeOf(K.comp.throwers[0])") == 4
    assert page.errors == []


def test_the_computer_is_neither_trivial_nor_unbeatable(site, context):
    page = open_game(site, context)
    # Many meets at level 1, the player vaulting every height from 3,20 m, each vault a little off.
    res = page.evaluate("""() => {
      const play = (v, sw, tr) => {
        let wins = 0, top = [];
        for (let n = 0; n < 60; n++) {
          K.level = 1; K.quit(); K.solo();
          for (let k = 0; k < 400 && !K.comp.over; k++) {
            const t = current();
            if (soleWinner(t)) { K.take(K.comp.seq, 'S'); continue; }
            const r = vaultResult(-4 + K.gauss() * 0.2, v + K.gauss() * 0.25, sw, tr + K.gauss() * 0.1);
            K.take(K.comp.seq, r.clear >= barH(K.comp.hi) ? 'O' : 'X');
          }
          const cpu = standings().find(t => t.p === null);
          top.push(bestOf(cpu));
          if (placeOf(K.comp.throwers[0]) === 1 && bestOf(K.comp.throwers[0]) > 0) wins++;
        }
        K.ending = null;
        return [wins / 60, top.reduce((a, b) => a + b) / top.length];
      };
      return { lazy: play(6.0, 0.6, 0.8), fair: play(7.6, 0.95, 1.0), good: play(8.8, 1, 1.0) };
    }""")
    # Seeded, so the same every run: with seed 1 the fair player wins 26 of 60; seeds 2-8 gave
    # 29, 30, 31, 25, 20, 19 and 23, lazy always 0 and good always 60, the best computer 4,34-4,37 m.
    assert res["lazy"][0] == 0
    assert 0.15 < res["fair"][0] < 0.85
    assert res["good"][0] > 0.85
    assert 4.0 <= res["good"][1] <= 4.8   # the best computer vaulter at level 1
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("go(8.5); quick()")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka kisaa (rima ")
    page.click("#cont")
    assert page.evaluate("[me().rec[0], th.mine, K.comp.hi >= 1]") == ["O", True, True]
    page.evaluate("K.quit(); showMenu()")
    page.click("#go")
    assert page.evaluate("[K.comp.hi, me().rec.length]") == [0, 0]
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_pads_and_pass_button_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 4.6, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("K.comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.rec = ['XO', 'XX']; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    page.evaluate("ready(); draw()")
    pb = page.evaluate("passBox")
    assert pb["x"] >= page.evaluate("SX") and pb["x"] + pb["w"] <= page.evaluate("SX + SW")
    assert pb["y"] + pb["h"] <= page.evaluate("groundY - 1.9 * runS")   # over the vaulter's head
    # The bar with a metre over it fits under the score panel while vaulting.
    assert page.evaluate("groundY - (barH(K.comp.hi) + 1) * vaultS()") > page.evaluate("hudTop + 64")
    assert page.errors == []


def test_the_pass_button_acts_on_the_finger_lifting(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); draw()")
    pb = page.evaluate("passBox")
    page.mouse.move(pb["x"] + 20, pb["y"] + 10)
    page.mouse.down()
    assert page.evaluate("[K.comp.seq === th.seq, th.phase]") == [True, "ready"]
    page.mouse.up()
    assert page.evaluate("me().rec[0]") == "-"
    assert page.errors == []


def test_turning_the_phone_keeps_the_vault(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.x = -12; th.v = 7")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate("[th.phase, th.x > -13, land]") == ["run", True, True]
    page.evaluate("th.x = -4; hold(1)")
    turn(page, {"width": 360, "height": 740})
    page.wait_for_function("!land")
    assert page.evaluate("th.phase") in ("pole", "fly", "land")
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


def vaulter_page(pages):
    """The phone whose turn it is, by the host's competition."""
    pid = pages[0].evaluate("current() && current().p")
    return next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)


def test_three_phones_vault_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("K.comp.order.join()") == host.evaluate("K.comp.order.join()") for p in pages)
    # The first player on a phone vaults; the others watch the same vault.
    first = vaulter_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("go(8.5)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && (th.phase === 'fly' || th.phase === 'land')", timeout=5000)
        assert p.evaluate("[th.res, th.clear]") == first.evaluate("[th.res, th.clear]")
    first.evaluate("quick()")
    seq = host.evaluate("K.comp.seq")
    for p in pages:
        p.wait_for_function(f"K.comp.seq === {seq}", timeout=5000)
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"K.comp && K.comp.seq === {seq} && th", timeout=10000)
    # A guest's pass counts; then everyone runs through until all three are out.
    passed = False
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = vaulter_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        if p is not host and not passed:
            passed = True
            who, hi = host.evaluate("[current().id, K.comp.hi]")
            p.evaluate("skip()")
            host.wait_for_function(f"K.comp.seq > {n}", timeout=5000)
            assert host.evaluate(f"thrower('{who}').rec[{hi}]").endswith("-")
            continue
        p.evaluate("fail()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    assert passed
    for p in pages:
        p.wait_for_function("K.ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("K.ending ? K.ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (K.ending) { K.ending.t = 99; step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:seivashyppy:kisat')") == "1"
        assert p.errors == []
    assert first.evaluate("JSON.parse(localStorage.getItem('ai-pelit:seivashyppy:ennatys'))") > 3
    for p in pages:
        p.context.close()


def test_a_guest_cannot_vault_out_of_turn_and_an_away_phone_is_vaulted_for(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    # Play on until it is the host's turn, so Aino is the guest out of turn.
    for _ in range(10):
        if vaulter_page(pages) is host:
            break
        aino.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        aino.evaluate("go(8.5); quick()")
        host.wait_for_function(f"K.comp.seq > {n}", timeout=5000)
    assert vaulter_page(pages) is host
    # A well-formed result from Aino out of turn, for the turn now: the host ignores it.
    n, before = host.evaluate("[K.comp.seq, JSON.stringify(K.comp.throwers.map(t => t.rec))]")
    aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: K.comp.room, seq: {n}, mark: 'O' }})")
    host.wait_for_timeout(300)
    assert host.evaluate("[K.comp.seq, JSON.stringify(K.comp.throwers.map(t => t.rec))]") == [n, before]
    host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
    host.evaluate("go(8.5); quick()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("K.comp.seq")
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.click("#aipr-goOn")
    host.wait_for_function(f"K.comp.seq > {n} && K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=5000)
    relay.back(aino)
    host.wait_for_function("!K.comp.throwers.find(t => t.name === 'Aino').bot", timeout=8000)
    aino.wait_for_function(f"K.comp && K.comp.seq > {n}", timeout=8000)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_a_meet_kept_by_v1_goes_on_in_v2(site, context):
    # v1 kept its meet in its own shape (att, cons, a turn queue); v2 reads it and goes on.
    page = open_game(site, context)
    page.goto(site.url + "games/seivashyppy/v1/")
    page.evaluate(HELPERS)
    page.click("#go")
    page.evaluate("go(8.5); quick()")
    att = page.evaluate("comp.throwers.find(t => t.p === 'me').att[0]")
    page.goto(site.url + "games/seivashyppy/v2/")
    page.evaluate(HELPERS)
    assert page.inner_text("#cont").startswith("Jatka kisaa (rima ")
    page.click("#cont")
    assert page.evaluate("[me().rec[0], th.mine]") == [att, True]
    page.evaluate("go(9.2); quick()")
    rec = page.evaluate("me().rec.map(r => r || '')")
    # Back to v1: it still reads the meet (v2 keeps v1's fields beside its own) and goes on.
    page.goto(site.url + "games/seivashyppy/v1/")
    page.evaluate(HELPERS)
    cont = page.inner_text("#cont")
    assert cont.startswith("Jatka kisaa (rima ") and "NaN" not in cont
    page.click("#cont")
    v1att = page.evaluate("Object.assign([], comp.throwers.find(t => t.p === 'me').att).map(r => r || '')")
    assert v1att == rec
    assert page.evaluate("th && th.mine")
    page.evaluate("go(9.2); quick()")
    v1att = page.evaluate("Object.assign([], comp.throwers.find(t => t.p === 'me').att).map(r => r || '')")
    # And to v2 again: it takes up what v1 played.
    page.goto(site.url + "games/seivashyppy/v2/")
    page.evaluate(HELPERS)
    page.click("#cont")
    assert page.evaluate("me().rec.map(r => r || '')") == v1att
    assert page.evaluate("th.mine")
    assert page.errors == []


def test_the_plant_bar_sits_above_the_feet_and_the_gaps_do_nothing(site, context):
    # v2 (Keihäänheitto v3's controls, #166).
    page = open_game(site, context)
    page.click("#go")
    jump, left, right = page.evaluate("pads()")
    assert [jump["k"], left["k"], right["k"]] == [3, 1, 2]
    assert jump["w"] > 300 and jump["y"] + jump["h"] + 18 <= left["y"] and left["y"] == right["y"]
    assert page.evaluate(f"padAt(180, {jump['y'] + jump['h'] + 9})") == 0
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    pl = page.evaluate("pads()")
    for top, foot in ((pl[0], pl[1]), (pl[2], pl[3])):
        cx = top["x"] + top["w"] / 2
        assert page.evaluate(f"padAt({cx}, {top['y'] + top['h'] + 9})") == 0
        assert page.evaluate(f"[padAt({cx}, {top['y'] + 10}), padAt({cx}, {foot['y'] + 20})]") == [3, foot["k"]]
    assert page.errors == []


def test_a_v2_meet_reloaded_then_opened_in_v1_does_not_break(site, context):
    # The computer comes in higher up, so its attempts have gaps; after a reload JSON makes them
    # null. v1 reads every att entry as a string, so v2 keeps only the heights tried.
    page = open_game(site, context)
    page.click("#go")
    for _ in range(4):
        page.evaluate("ready(); go(9.2); quick()")
    assert page.evaluate("K.comp.throwers.some(t => t.p === null && [...t.rec].some(r => r === undefined))")
    page.reload()
    page.evaluate(HELPERS)
    page.click("#cont")
    page.evaluate("ready(); go(9.2); quick()")
    saved = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:seivashyppy:kesken'))")
    assert all(isinstance(v, str) for t in saved["throwers"] for v in t["att"].values())
    page.goto(site.url + "games/seivashyppy/v1/")
    page.evaluate(HELPERS)
    page.click("#cont")
    page.evaluate("draw(); go(9.2); quick(); draw()")
    assert page.evaluate("comp.throwers.length") == 12
    assert page.errors == []
