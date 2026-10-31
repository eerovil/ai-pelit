"""Keihäänheitto v3: a yellow mark says when to hold the throw, the whole runway shows from the
start, a held throw goes by itself at the last safe step, and the throw bar is off the feet (#166)."""

import json

import pytest
from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/keihas/v3/"
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
  window.ready = () => { if (th.phase === 'wait') { th.t = 99; step(0.001); } };
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


def test_the_green_angles_are_wider_and_still_throw_near_the_best(site, context):
    page = open_game(site, context)
    top = page.evaluate("Math.max(...[...Array(40).keys()].map(a => flight(-3, 8.3, a + 20).x))")
    lo, hi = page.evaluate("GREEN")
    assert hi - lo >= 12
    for a in (lo, hi):
        assert page.evaluate(f"flight(-3, 8.3, {a}).x") > top - 3
    assert page.errors == []


def test_starting_to_hold_in_the_yellow_and_holding_on_throws_green_and_legal(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready()")
    # Drum the feet at 8 a second up to the yellow mark, then hold the throw and never let go.
    page.evaluate("""() => {
        th.phase = 'run';
        let i = 0;
        while (th.x < zones(th.v).y0 + 0.6) { if (i % 8 === 0) press((i / 8) % 2 + 1); step(1 / 64); i++; }
        startAim(1);
        run(() => th.phase === 'aim', 5);
    }""")
    assert page.evaluate("th.phase") == "fly"
    lo, hi = page.evaluate("GREEN")
    assert lo <= page.evaluate("th.ang") <= hi
    assert page.evaluate("[th.mark > 55, th.why]") == [True, ""]
    page.evaluate("quick()")
    assert page.evaluate("comp.throwers.find(t => t.p === 'me').marks[0]") > 55
    assert page.errors == []


def test_holding_too_late_still_throws_but_running_over_without_holding_is_a_foul(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.v = 8; th.x = -2.6; startAim(1); run(() => th.phase === 'aim', 2)")
    # Pressed past the green: it goes at once, a low angle, but it counts.
    assert page.evaluate("[th.phase, th.why]") == ["fly", ""]
    assert page.evaluate("th.mark") > 0
    page.evaluate("quick(); run(() => th.phase === 'wait'); ready(); th.phase = 'run'; th.x = -0.2; th.v = 8; step(0.05)")
    assert page.evaluate("[th.phase, th.mark, th.why]") == ["land", -1, "Yliastuttu!"]
    # A slip of the thumb still does not throw.
    page.evaluate("quick(); run(() => th.phase === 'wait'); ready(); th.phase = 'run'; th.x = -15; th.v = 7; startAim(1); step(0.05); release()")
    assert page.evaluate("[th.phase, th.jav]") == ["run", None]
    assert page.errors == []


def test_the_same_foot_twice_adds_nothing_but_does_not_slow(site, context):
    page = open_game(site, context)
    page.click("#go")
    page.evaluate("ready(); for (let i = 0; i < 24; i++) { press(i % 2 + 1); step(1 / 8); }")
    v = page.evaluate("th.v")
    assert 7.5 <= v <= 9
    page.evaluate("press(th.foot)")
    assert page.evaluate("th.v") == v
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (390, 844)])
def test_upright_the_throw_bar_is_above_the_feet_and_the_gap_does_nothing(site, context, size):
    w, h = size
    page = open_game(site, context)
    turn(page, {"width": w, "height": h})
    page.click("#go")
    pads = page.evaluate("pads()")
    throw = [p for p in pads if p["k"] == 3]
    feet = sorted((p for p in pads if p["k"] != 3), key=lambda p: p["x"])
    assert len(throw) == 1 and [p["k"] for p in feet] == [1, 2]
    t = throw[0]
    # Nothing between the feet: they share the row, and the throw bar sits wholly above them.
    assert feet[0]["x"] + feet[0]["w"] + 20 > feet[1]["x"]
    assert all(t["y"] + t["h"] + 16 <= f["y"] for f in feet)
    assert all(p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["w"] <= w and p["y"] + p["h"] <= h for p in pads)
    assert feet[0]["h"] >= 80
    gap_y = (t["y"] + t["h"] + feet[0]["y"]) / 2
    assert page.evaluate(f"padAt({w / 4}, {gap_y})") == 0
    assert page.evaluate(f"padAt({w / 4}, {feet[0]['y'] + 10})") == 1
    assert page.evaluate(f"padAt({w * 3 / 4}, {feet[1]['y'] + 10})") == 2
    assert page.evaluate(f"padAt({w / 2}, {t['y'] + 10})") == 3
    # A finger on the feet never starts the throw: a real touch on each foot, then where v2's throw was.
    page.evaluate("ready()")
    fy = feet[0]["y"] + feet[0]["h"] / 2
    for cx in (w / 4, w * 3 / 4, w / 2 - 12, w / 2 + 12):
        page.mouse.click(cx, fy)
    assert page.evaluate("th.phase") == "run"
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (360, 740), (740, 360), (640, 360)])
def test_the_runway_strip_and_marks_show_from_the_first_step(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 71.23})
    turn(page, {"width": w, "height": h})
    page.click("#go")
    page.evaluate("ready(); th.phase = 'run'; th.x = -29; th.v = 3; draw()")
    # The strip lies inside the scene, under the ground's distance numbers.
    y = page.evaluate("Math.min(groundY + 44, sceneB - 14)")
    assert page.evaluate("groundY + 34") <= y and y + 12 <= page.evaluate("sceneB")
    # Its colours are on the canvas: the yellow and green of the marks.
    found = page.evaluate(f"""() => {{
        const d = x2d.getImageData(0, {y} * DPR + 4 * DPR, c.width, 1).data, seen = new Set();
        for (let i = 0; i < d.length; i += 4) seen.add([d[i], d[i + 1], d[i + 2]].join());
        return [seen.has('255,209,102'), seen.has('126,224,129')];
    }}""")
    assert found == [True, True]
    # At speed, the camera shows the yellow mark ahead before the thrower reaches it.
    page.evaluate("th.v = 8.3; th.x = zones(8.3).y0 - 4; blend = 0; draw()")
    assert page.evaluate("(zones(8.3).y0 - camX) * runS") < page.evaluate("SW")
    assert page.evaluate("groundY - 2.6 * runS") > page.evaluate("hudTop + 64")
    assert page.errors == []


def test_a_whole_meet_alone_still_saves_on_v2s_keys(site, context):
    page = open_game(site, context, {"taso": 3, "voitot": 2, "kisat": 5, "ennatys": 60.5})
    assert page.inner_text("#foe").startswith("Taso 3: ")
    page.click("#go")
    for _ in range(6):
        page.evaluate("go(9, 37, -3.5); quick()")
    page.evaluate("ending.t = 99; step(0.01)")
    assert page.inner_text("#result").startswith("🥇 Voitit kisan!")
    saved = page.evaluate("['taso', 'voitot', 'kisat'].map(k => localStorage.getItem('ai-pelit:keihas:' + k))")
    assert saved == ["4", "3", "6"]
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:keihas:ennatys'))") > 70
    assert page.errors == []


@pytest.mark.parametrize("size", [(360, 640), (740, 360), (640, 360)])
def test_the_menu_fits(site, context, size):
    w, h = size
    page = open_game(site, context, {"ennatys": 71.23, "kisat": 4, "voitot": 1, "taso": 2})
    turn(page, {"width": w, "height": h})
    assert page.evaluate("document.scrollingElement.scrollHeight") <= h
    for sel in ("#go", "#multi", "#asu", "#stats", "#foe"):
        b = page.locator(sel).bounding_box()
        assert b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["width"] <= w and b["y"] + b["height"] <= h, sel
    assert page.errors == []


def test_two_phones_see_the_held_throw_go_by_itself(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    pages = []
    for name in ("Eero", "Aino"):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(HELPERS)
        pages.append(page)
    host, aino = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    aino.click("#multi")
    aino.fill("#aipr-codeIn", host.evaluate("AiPelitRooms.code"))
    aino.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("comp && comp.throwers.length === 12 && th", timeout=8000)
    pid = host.evaluate("current().p")
    me = next(p for p in pages if p.evaluate("AiPelitRooms.me") == pid)
    other = aino if me is host else host
    me.wait_for_function("th.mine && th.phase === 'ready'", timeout=8000)
    me.evaluate("th.phase = 'run'; th.v = 8.5; th.x = zones(8.5).y0 + 0.5; startAim(1); run(() => th.phase === 'aim', 5)")
    assert me.evaluate("[th.phase, th.why]") == ["fly", ""]
    other.wait_for_function("th && !th.mine && th.phase === 'fly'", timeout=5000)
    assert other.evaluate("th.mark") == me.evaluate("th.mark")
    mark = me.evaluate("th.mark")
    me.evaluate("quick()")
    host.wait_for_function(f"comp.throwers.some(t => t.marks[0] === {mark} && t.p === {json.dumps(pid)})", timeout=5000)
    for p in pages:
        assert p.errors == []
        p.context.close()
