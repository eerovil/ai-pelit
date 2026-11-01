"""Pilkkiminen: drill a hole, jig in rhythm, reel the fish in; a five-minute contest alone or in a room.

The world steps by hand (`run()`), so a whole contest plays in a moment; each phone in a room is
its own Chromium context, and the room relay is `Relay` from test_rooms_lib.
"""

import json
import math

import pytest

from conftest import ROOT, turn
from test_rooms_lib import Relay

URL = "games/pilkki/v1/"

# Steps the game by hand, 1/60 s at a time, while cond() holds, at most max seconds of game time.
RUN = "() => { window.run = (cond, max = 30) => { for (let t = 0; t < max && cond(); t += DT) { update(DT); closing(DT); } }; }"

# Plays a fight as a careful player: reel while the line is easy, let go when it gets tight.
FIGHT = """() => {
  for (let t = 0; t < 120 && phase === 'fight'; t += DT) {
    holding = fight.T > 0.9 ? 0 : fight.T < 0.72 ? 1 : holding;
    update(DT);
  }
  holding = 0;
  return phase;
}"""

# Twitches the jig on the beat until the fish bites (or n twitches go by).
ON_BEAT = """(n) => {
  let k = 0;
  for (let i = 0; i < 60 / DT && phase === 'jig' && k < n; i++) {
    const before = Math.floor(beat);
    update(DT);
    if (Math.floor(beat) !== before) { twitch(); k++; }
  }
  return [phase, k];
}"""


def open_game(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(RUN)
    return page


def start(site, context):
    page = open_game(site, context)
    page.click("#go")
    return page


# A hole drilled, and one perch of 200 g waiting at 2 m beside the jig.
def ready(page, sp="ahven", g=200):
    page.evaluate(f"""() => {{
      holes.push(spot.i); toJig(); jigD = 2;
      fish = [newFish(spot, '{sp}')]; fish[0].g = {g}; fish[0].d = 2; fish[0].home = 2; fish[0].x = 0.4;
      run(() => !target, 3);
    }}""")


def test_the_menu_starts_a_contest_at_a_new_hole(site, context):
    page = start(site, context)
    assert page.evaluate("[phase, left > 299, myG, holes.length]") == ["drill", True, 0, 0]
    assert page.locator("#menu").is_hidden()
    assert page.errors == []


def test_going_round_with_the_finger_drills_the_hole(site, context):
    page = start(site, context)
    ax, ay = page.evaluate("augerC()")
    page.mouse.move(ax + 50, ay)
    page.mouse.down()
    # Five turns are not enough; six are.
    for i in range(1, 5 * 24 + 1):
        a = i / 24 * 2 * math.pi
        page.mouse.move(ax + 50 * math.cos(a), ay + 50 * math.sin(a))
    assert page.evaluate("phase") == "drill" and 0.75 < page.evaluate("drill") < 0.9
    for i in range(5 * 24 + 1, 6 * 24 + 6):
        a = i / 24 * 2 * math.pi
        page.mouse.move(ax + 50 * math.cos(a), ay + 50 * math.sin(a))
    page.mouse.up()
    assert page.evaluate("[phase, holes.length, jigD]") == ["jig", 1, 0]
    # A drag down lowers the jig.
    page.mouse.move(180, 400)
    page.mouse.down()
    page.mouse.move(180, 560, steps=8)
    page.mouse.up()
    assert page.evaluate("jigD") > 1
    assert page.errors == []


def test_twitching_on_the_beat_makes_a_fish_bite_and_a_tap_hooks_it(site, context):
    page = start(site, context)
    ready(page)
    assert page.evaluate("target === fish[0] && period()") == 0.55
    phase, n = page.evaluate(ON_BEAT, 10)
    assert phase == "bite" and 4 <= n <= 6
    page.mouse.click(180, 500)
    assert page.evaluate("[phase, fight.fish.sp, fight.L > 1]") == ["fight", "ahven", True]
    assert page.errors == []


def test_off_the_beat_or_in_a_frenzy_no_fish_bites(site, context):
    page = start(site, context)
    ready(page)
    # Half a beat off, every time.
    res = page.evaluate("""() => {
      const out = [];
      for (let k = 0; k < 8; k++) {
        run(() => true, 0.2);
        run(() => Math.abs((beat - Math.floor(beat)) - 0.5) > 0.05, 3);
        out.push(twitch());
      }
      return [phase, out, fish[0].int];
    }""")
    assert res[0] == "jig" and set(res[1]) == {"off"} and res[2] == 0
    # Many taps at once frighten it away.
    res = page.evaluate("() => { twitch(); update(DT); const r = twitch(); return [r, phase, fish[0].flee > 0]; }")
    assert res == ["fast", "jig", True]


def test_a_missed_bite_lets_the_fish_go(site, context):
    page = start(site, context)
    ready(page)
    page.evaluate(ON_BEAT, 10)
    page.evaluate("run(() => phase === 'bite', 3)")
    assert page.evaluate("phase") == "jig"
    assert page.evaluate("fish[0].flee > 0 && fish[0].int === 0") is True


def test_holding_through_a_big_fish_s_rush_breaks_the_line(site, context):
    page = start(site, context)
    ready(page, "hauki", 5000)
    page.evaluate(ON_BEAT, 12)
    page.evaluate("strike(); holding = 1; run(() => phase === 'fight', 30)")
    assert page.evaluate("[phase, myG, fish.length]") == ["snap", 0, 1]
    # A new jig is tied on, and it goes back down by itself.
    page.evaluate("run(() => phase === 'snap', 5); run(() => jigGoal !== null, 5)")
    assert page.evaluate("phase") == "jig" and page.evaluate("jigD") > 1.5


@pytest.mark.parametrize("sp", ["ahven", "kuha", "hauki"])
def test_the_biggest_fish_of_each_kind_can_be_landed_by_letting_go_in_time(site, context, sp):
    page = start(site, context)
    big = page.evaluate(f"SPECIES['{sp}'].w[1]")
    ready(page, sp, big)
    page.evaluate(ON_BEAT, 12)
    page.evaluate("strike()")
    assert page.evaluate(FIGHT) == "caught"
    assert page.evaluate("[myG, myN, myBig.g]") == [big, 1, big]
    # The catch is saved the moment it is landed.
    assert json.loads(page.evaluate("localStorage.getItem('ai-pelit:pilkki:suurin')")) == {"s": sp, "g": big}
    assert json.loads(page.evaluate("localStorage.getItem('ai-pelit:pilkki:kalat')")) == {sp: 1}
    # A tap goes on, and the jig sinks back where the fish was.
    page.evaluate("phaseT = 1")
    page.mouse.click(180, 500)
    page.evaluate("run(() => jigGoal !== null, 5)")
    assert page.evaluate("phase") == "jig" and abs(page.evaluate("jigD") - 2) < 0.2


def test_moving_takes_the_angler_to_another_place_and_back_to_its_old_hole(site, context):
    page = start(site, context)
    first = page.evaluate("spot.i")
    page.evaluate("holes.push(spot.i); toJig()")
    page.evaluate("mapOpen = true")
    other = page.evaluate(f"lake.find(s => s.i !== {first})")
    sx, sy = page.evaluate(f"spotXY(lake[{other['i']}])")
    page.mouse.click(sx, sy)
    assert page.evaluate("[phase, spot.i, mapOpen]") == ["walk", other["i"], False]
    page.evaluate("run(() => phase === 'walk', 10)")
    assert page.evaluate("phase") == "drill"
    # Going back needs no drilling.
    page.evaluate(f"mapOpen = true; moveTo(lake[{first}]); run(() => phase === 'walk', 10)")
    assert page.evaluate("[phase, spot.i]") == ["jig", first]


def test_the_contest_ends_after_five_minutes_and_a_win_raises_the_level(site, context):
    page = start(site, context)
    page.evaluate("myG = 2500; myN = 9; rivals.forEach(r => r.g = 1000); left = 0.5; run(() => phase !== 'done', 2)")
    assert page.evaluate("phase") == "done"
    assert page.locator("#result").inner_text() == "Voitit kisan! 🏆 2,50 kg"
    assert page.locator("#board li.me").inner_text().startswith("Sinä (9)")
    saved = page.evaluate("['taso', 'ennatys', 'kisat'].map(k => localStorage.getItem('ai-pelit:pilkki:' + k))")
    assert saved == ["2", "2500", '{"pelatut":1,"voitot":1}']
    # A loss keeps the level. (The high-score list asked for a nickname over the menu.)
    page.locator("#ai-pelit-tulokset button", has_text="Sulje").click()
    page.click("#go")
    page.evaluate("myG = 300; rivals[1].g = 900; left = 0.1; run(() => phase !== 'done', 2)")
    assert page.locator("#result").inner_text() == "2. sija: 0,30 kg"
    assert page.evaluate("level") == 2
    assert page.errors == []


def test_the_computer_anglers_get_better_level_by_level(site, context):
    page = open_game(site, context)
    means = page.evaluate("""() => [1, 3, 6].map(l => {
      level = l; let tot = 0;
      for (let k = 0; k < 60; k++) {
        rivals = RIVALS.map(n => ({ name: n, g: 0, n: 0, spot: k % SPOTS }));
        for (let t = 0; t < CONTEST; t += 0.25) cpuAnglers(0.25);
        tot += Math.max(...rivals.map(r => r.g));
      }
      return tot / 60;
    })""")
    # Level 1's best rival lands about a kilo or so; it grows from there.
    assert 600 < means[0] < 2200 and means[0] < means[1] < means[2]


def test_a_reload_mid_contest_can_carry_it_on(site, context):
    page = start(site, context)
    page.evaluate("holes.push(spot.i); toJig(); myG = 700; myN = 3; left = 200; keepContest()")
    page.reload()
    page.evaluate(RUN)
    assert page.locator("#resume").is_visible()
    assert "3:20" in page.locator("#resume").inner_text()
    page.click("#resume")
    # The game's own frames keep the clock running while the test looks.
    assert page.evaluate("[phase, myG, myN, left > 199 && left <= 200]") == ["jig", 700, 3, True]


# ---------- Playing with friends ----------

@pytest.fixture
def room(site, browser):
    site.build(ROOT / "games")
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.evaluate(RUN)
        return page

    def play(*names):
        host = phone(names[0])
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
        code = host.evaluate("AiPelitRooms.code")
        guests = []
        for n in names[1:]:
            g = phone(n)
            g.click("#multi")
            g.fill("#aipr-codeIn", code)
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
            guests.append(g)
        host.wait_for_function(f"AiPelitRooms.members.filter(m => m.on).length === {len(names)}")
        host.click("#aipr-start")
        for p in [host, *guests]:
            p.wait_for_function("net.on && phase === 'drill'")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def test_friends_fish_the_same_lake_and_see_each_other_s_catch(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    # The same lake, each at its own place on it.
    lakes = [p.evaluate("JSON.stringify(lake.map(s => [s.mx, s.my, s.depth]))") for p in (host, guest, third)]
    assert lakes[0] == lakes[1] == lakes[2]
    assert len({p.evaluate("spot.i") for p in (host, guest, third)}) == 3
    # Aino lands a fish: the host's standings and Iida's show it.
    guest.evaluate("myG = 840; myN = 2; sendMe()")
    host.wait_for_function("standings()[0].name === 'Aino' && standings()[0].g === 840", timeout=4000)
    third.wait_for_function("standings()[0].name === 'Aino'", timeout=4000)
    # The host's clock runs the contest: the others follow it.
    host.evaluate("left = 100")
    guest.wait_for_function("Math.abs(left - 100) < 2", timeout=4000)
    assert host.errors == guest.errors == third.errors == []


def test_the_host_ends_the_contest_and_every_phone_gets_its_place(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("myG = 500; myN = 2")
    guest.evaluate("myG = 1200; myN = 4; sendMe()")
    host.wait_for_function("(net.board[Object.keys(net.board).find(k => k !== AiPelitRooms.me)] || {}).g === 1200", timeout=4000)
    host.evaluate("left = 0.2")
    guest.evaluate("left = 0.2")
    for p, res, saved in [(host, "2. sija · 0,50 kg", '{"kisat":1,"voitot":0}'), (guest, "Voitit! 🏆 1,20 kg", '{"kisat":1,"voitot":1}')]:
        p.wait_for_function("phase === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0", timeout=6000)
        assert p.locator("#aipr-result").inner_text().startswith(res)
        assert p.evaluate("localStorage.getItem('ai-pelit:pilkki:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_a_guest_that_reloads_mid_contest_keeps_its_catch(room):
    host, [guest] = room("Eero", "Aino")
    guest.evaluate("myG = 650; myN = 3; sendMe()")
    host.wait_for_function("Object.values(net.board).some(b => b.g === 650)", timeout=4000)
    guest.reload()
    guest.evaluate(RUN)
    guest.wait_for_function("net.on && myG === 650 && myN === 3", timeout=8000)
    assert guest.evaluate("phase") == "drill"
    assert guest.errors == []


# ---------- Screens ----------

@pytest.mark.parametrize("size", [(740, 360), (640, 360), (360, 640), (390, 844)])
def test_the_menu_and_the_game_fit_the_screen(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    for sel in ["#go", "#multi", "h1", "#stats"]:
        b = page.locator(sel).bounding_box()
        assert b["y"] >= 0 and b["y"] + b["height"] <= size[1] and b["x"] >= 0 and b["x"] + b["width"] <= size[0], sel
    page.click("#go")
    ok = page.evaluate("""() => moveBtn.x >= 0 && moveBtn.y > 40 && moveBtn.x + moveBtn.w < holeX - 60
      && waterBot - waterTop > 120 && meterY < H && holeX > 0 && holeX < W
      && mapBox.x >= 0 && mapBox.x + mapBox.w <= W && mapBox.y + mapBox.h + 64 <= H""")
    assert ok is True
    ctx.close()


def test_turning_the_phone_mid_contest_keeps_it(site, browser):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(site.url + URL)
    page.evaluate(RUN)
    page.click("#go")
    page.evaluate("holes.push(spot.i); toJig(); jigD = 2.5; myG = 400")
    turn(page, {"width": 740, "height": 360})
    page.wait_for_function("wide === true")
    assert page.evaluate("[phase, jigD, myG]") == ["jig", 2.5, 400]
    ctx.close()
