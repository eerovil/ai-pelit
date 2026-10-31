"""Keihäänheitto v4 (#165): v1's meet and room tests, now run by the shared athletics library."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/keihas/v4/"

# Test helpers in the page: run(cond, max) steps the game 1/60 s at a time; go(v, ang, at) throws
# at once from `at` metres with v m/s of run-up and ang degrees; quick() lands it and reports it.
HELPERS = """() => {
  window.run = (cond, max = 10) => { for (let t = 0; t < max && cond(); t += 1 / 60) step(1 / 60); };
  window.go = (v, ang, at) => {
    if (th.phase === 'wait') { th.t = 99; step(0.001); }
    th.phase = 'run'; th.v = v; th.x = at;
    startAim(1); th.aimT = (ang - AIM0) / AIM_RATE; th.ang = ang; release();
  };
  window.quick = () => {
    if (th.jav) { th.jav.acc = 30; step(0.001); }
    th.t = 99; step(0.001);
  };
}"""


def open_game(site, context, saved=None):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    if saved:
        for k, v in saved.items():
            page.evaluate(f"localStorage.setItem('ai-pelit:keihas:{k}', {json.dumps(json.dumps(v))})")
        page.goto(site.url + URL)
    page.evaluate(HELPERS)
    return page


def test_a_whole_meet_alone_is_won_and_saved(site, context):
    page = open_game(site, context)
    page.click("#go")
    assert page.evaluate("[K.comp.throwers.length, K.comp.round, th.mine, th.phase]") == [12, 1, True, "wait"]
    for rnd in range(1, 7):
        assert page.evaluate("K.comp.round") == rnd
        page.evaluate("go(9, 36, -3.5); quick()")
        # The record is saved the moment it lands.
        if rnd == 1:
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:keihas:ennatys'))") > 70
            assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:keihas:kesken')).round") == 2
    assert page.evaluate("K.comp.over && K.ending.at === 0")
    assert page.evaluate("K.comp.final.length") == 8
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat', 'kesken'].map(k => localStorage.getItem('ai-pelit:keihas:' + k))")
    assert saved == ["2", "1", "1", None]
    assert page.inner_text("#foe").startswith("Taso 2: ")
    assert page.is_hidden("#cont")
    assert page.errors == []


def test_a_meet_goes_on_after_a_reload(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("go(8, 36, -3); quick()")
    first = page.evaluate("K.comp.throwers.find(t => t.p === 'me').marks[0]")
    page.reload()
    page.evaluate(HELPERS)
    assert page.inner_text("#cont") == "Jatka kisaa (kierros 2/6)"
    page.click("#cont")
    assert page.evaluate("[K.comp.round, K.comp.throwers.find(t => t.p === 'me').marks[0], th.mine]") == [2, first, True]
    # Kisaan! starts a new meet instead.
    page.evaluate("K.quit(); showMenu()")
    page.click("#go")
    assert page.evaluate("[K.comp.round, K.comp.throwers.find(t => t.p === 'me').marks.length]") == [1, 0]
    assert page.errors == []


def test_three_fouls_leave_you_out_of_the_final_eight(site, context):
    page = open_game(site, context)
    page.click("#go")
    for _ in range(3):
        page.evaluate("go(8, 36, -0.5); quick()")
    assert page.evaluate("K.comp.over && !K.ending.fin")
    page.evaluate("K.ending.t = 99; step(0.01)")
    assert "ei finaaliin" in page.inner_text("#result")
    assert page.evaluate("localStorage.getItem('ai-pelit:keihas:voitot')") == "0"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844), (740, 360), (640, 360)])
def test_the_menu_board_and_pads_fit(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 71.23, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    page.click("#go")
    page.evaluate("K.comp.throwers.forEach((t, i) => { t.name = 'Wwwwwwwwwwwwwww' + i; t.marks = [88.88, -1, 77.77]; }); draw()")
    box = page.evaluate("boardBox")
    assert box["y"] >= 0 and box["y"] + box["h"] <= page.evaluate("sceneB")
    assert box["rowH"] >= 18
    for p in page.evaluate("pads()"):
        assert p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h
    # The thrower on the runway fits under the score panel.
    assert page.evaluate("groundY - 2.6 * runS") > page.evaluate("hudTop + 64")
    assert page.errors == []


def test_turning_the_phone_keeps_the_throw(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("th.t = 99; step(0.001); th.phase = 'run'; th.x = -12; th.v = 7")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("land")
    assert page.evaluate("[th.phase, th.x > -13, land]") == ["run", True, True]
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


def test_three_phones_throw_in_turns_and_every_phone_sees_the_same_meet(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host = pages[0]
    assert all(p.evaluate("K.comp.order.join()") == host.evaluate("K.comp.order.join()") for p in pages)
    # The first player on a phone throws; the others watch the same javelin fly and land.
    first = thrower_page(pages)
    first.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    first.evaluate("go(8.5, 36, -3)")
    others = [p for p in pages if p is not first]
    for p in others:
        p.wait_for_function("th && !th.mine && th.phase === 'fly'", timeout=5000)
        assert p.evaluate("th.mark") == first.evaluate("th.mark")
    first.evaluate("quick()")
    seq = host.evaluate("K.comp.seq")
    for p in pages:
        p.wait_for_function(f"K.comp.seq === {seq}", timeout=5000)
    # Aino reloads mid-meet and gets it back from the host.
    aino = pages[1]
    aino.reload()
    aino.evaluate(HELPERS)
    aino.wait_for_function(f"K.comp && K.comp.seq === {seq} && th", timeout=10000)
    # Everyone throws on until the end.
    for _ in range(40):
        if host.evaluate("K.comp === null || K.comp.over"):
            break
        p = thrower_page(pages)
        p.wait_for_function("th && th.mine && (th.phase === 'wait' || th.phase === 'ready')", timeout=8000)
        n = host.evaluate("K.comp.seq")
        p.evaluate("go(8.5, 36, -3); quick()")
        host.wait_for_function(f"K.comp.seq > {n} || K.comp.over", timeout=5000)
    for p in pages:
        p.wait_for_function("K.ending !== null || (AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== '')", timeout=10000)
    res = [p.evaluate("K.ending ? K.ending.res.map(r => r.name + r.best).join() : ''") for p in pages]
    assert res[0] and res.count(res[0]) == 3
    for p in pages:
        p.evaluate("if (K.ending) { K.ending.t = 99; step(0.01); }")
        p.wait_for_function("AiPelitRooms.inRoom && document.getElementById('aipr-result').textContent !== ''", timeout=5000)
        assert p.evaluate("localStorage.getItem('ai-pelit:keihas:kisat')") == "1"
        assert p.evaluate("JSON.parse(localStorage.getItem('ai-pelit:keihas:ennatys'))") > 60
        assert p.errors == []
    for p in pages:
        p.context.close()


def test_a_guest_cannot_throw_out_of_turn_and_an_away_phone_is_thrown_for(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, aino = pages
    # A result from the phone whose turn it is not is ignored.
    if thrower_page(pages) is host:
        n = host.evaluate("K.comp.seq")
        aino.evaluate(f"AiPelitRooms.send({{ t: 'res', round: K.comp.room, seq: {n}, mark: 99 }})")
        host.wait_for_timeout(300)
        assert host.evaluate("K.comp.seq") == n
        host.wait_for_function("th.mine && th.phase !== 'wait'", timeout=8000)
        host.evaluate("go(8, 36, -3); quick()")
    aino.wait_for_function("th && th.mine", timeout=8000)
    n = host.evaluate("K.comp.seq")
    relay.drop(aino)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    # "Jatka ilman heitä": the computer throws Aino's turn.
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
    p = thrower_page(pages)
    p.wait_for_function("th && th.mine && th.phase !== 'wait'", timeout=8000)
    # A slow player, tapping once a second for 60 s, keeps the turn.
    p.evaluate("""() => {
        th.phase = 'run';
        for (let s = 0; s < 60; s++) { th.x = -20; press(s % 2 + 1); for (let i = 0; i < 60; i++) step(1 / 60); }
    }""")
    assert p.evaluate("[th.phase, th.why]") == ["run", ""]
    # Nothing pressed for 45 s: a foul.
    p.evaluate("th.x = -20; th.v = 0; run(() => th.phase === 'run', 50)")
    assert p.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Aika loppui"]
    for q in pages:
        assert q.errors == []
        q.context.close()
