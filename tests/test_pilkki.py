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


# A hole drilled, and the lake's only fish (a perch of 200 g) waiting at 2 m beside the jig.
def ready(page, sp="ahven", g=200):
    page.evaluate(f"""() => {{
      holes.push(spot.i); toJig(); jigD = 2;
      const f = newFish(spot, '{sp}'); f.g = {g}; f.d = 2; f.lx = f.wx = spot.x + 0.4; f.ly = f.wy = spot.y; f.linger = 999;
      pond = [f]; sight();
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
    res = page.evaluate("() => { twitch(); update(DT); const r = twitch(); return [r, phase, pond[0].flee > 0]; }")
    assert res == ["fast", "jig", True]


def test_a_missed_bite_lets_the_fish_go(site, context):
    page = start(site, context)
    ready(page)
    page.evaluate(ON_BEAT, 10)
    page.evaluate("run(() => phase === 'bite', 3)")
    assert page.evaluate("phase") == "jig"
    assert page.evaluate("pond[0].flee > 0 && pond[0].int === 0 && pond[0].go") is True


def test_holding_through_a_big_fish_s_rush_breaks_the_line(site, context):
    page = start(site, context)
    ready(page, "hauki", 5000)
    page.evaluate(ON_BEAT, 12)
    page.evaluate("strike(); holding = 1; run(() => phase === 'fight', 30)")
    assert page.evaluate("[phase, myG, pond.length, pond[0].go]") == ["snap", 0, 1, True]
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


def test_a_new_player_s_first_lost_contest_sends_level_1_with_its_score(site, context):
    page = start(site, context)
    assert page.evaluate("localStorage.getItem('ai-pelit:pilkki:taso')") == "1"
    page.evaluate("myG = 400; rivals[0].g = 900; left = 0.1; run(() => phase !== 'done', 2)")
    assert page.locator("#result").inner_text() == "2. sija: 0,40 kg"
    assert page.evaluate("AiPelitScores.games.pilkki.level()") == 1


def test_the_computer_anglers_get_better_level_by_level(site, context):
    page = open_game(site, context)
    means = page.evaluate("""() => [1, 6].map(l => {
      level = l; let tot = 0;
      for (let k = 0; k < 6; k++) {
        save('kisa', null); newContest(); holes.push(spot.i); toJig();
        const n = pond.length;
        run(() => true, CONTEST - 1);
        // What they land is gone from the lake.
        if (pond.length !== n - rivals.reduce((a, r) => a + r.n, 0)) return -1;
        tot += Math.max(...rivals.map(r => r.g));
      }
      return tot / 6;
    })""")
    # Level 1's best rival lands a kilo or two; level 6's far more.
    assert 700 < means[0] < 3500 and means[1] > means[0] * 1.5


def test_every_fish_swims_from_place_to_place_and_a_caught_one_is_gone(site, context):
    page = start(site, context)
    page.evaluate("holes.push(spot.i); toJig()")
    n = page.evaluate("pond.length")
    page.evaluate("pond.forEach(f => f.was = f.tgt)")
    page.evaluate("run(() => true, 150)")
    # Only the computer anglers fished: every other fish is still there, many now at another place.
    assert page.evaluate("pond.length + rivals.reduce((a, r) => a + r.n, 0)") == n
    page.evaluate("rivals = []")
    moved = page.evaluate("pond.filter(f => f.tgt !== f.was).length")
    assert moved > n * 0.4
    # A fished-out place stays empty when you walk off and come straight back...
    first = page.evaluate("spot.i")
    other = page.evaluate(f"lake.find(s => s.i !== {first}).i")
    page.evaluate(f"""() => {{
      pond = pond.filter(f => Math.abs(f.lx - spot.x) > 12 || Math.abs(f.ly - spot.y) > 12);
      for (const f of pond) {{ f.linger = 999; if (f.tgt === {first}) leave(f); }}
      moveTo(lake[{other}]); run(() => phase === 'walk', 10); holes.push(spot.i); toJig();
      moveTo(lake[{first}]); run(() => phase === 'walk', 10);
    }}""")
    assert page.evaluate("[spot.i, fish.length]") == [first, 0]
    # ...and gets a fish when one swims there.
    page.evaluate(f"const f = pond[0]; f.tgt = {first}; f.go = true; f.wx = spot.x; f.wy = spot.y")
    page.evaluate("run(() => !fish.length, 300)")
    assert page.evaluate("fish.length") == 1


def test_a_reload_keeps_every_fish_of_the_lake(site, context):
    page = start(site, context)
    page.evaluate("holes.push(spot.i); toJig(); run(() => true, 20)")
    here = page.evaluate("spot.i")
    # This place fished out (nothing near it), the rest of the lake as it swims.
    page.evaluate("pond = pond.filter(f => Math.abs(f.lx - spot.x) > 6 || Math.abs(f.ly - spot.y) > 4.5); sight()")
    before = page.evaluate("pond.map(f => [f.sp, f.g, f.tgt]).sort().join(';')")
    page.evaluate("keepContest()")
    page.reload()
    page.evaluate(RUN)
    page.click("#resume")
    assert page.evaluate("[spot.i, phase, fish.length]") == [here, "jig", 0]
    assert page.evaluate("pond.map(f => [f.sp, f.g, f.tgt]).sort().join(';')") == before


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

def give(host, guest, *weights):
    """The host accepts fish of these weights as caught by the guest's phone, as hostFish() does."""
    who = json.dumps(guest.evaluate("AiPelitRooms.me"))
    for g in weights:
        host.evaluate(f"""() => {{
          const f = newFish(lake[0], 'ahven'); f.g = {g}; pond.push(f); net.claims[f.id] = {who};
          hostFish({{ t: 'caught', round: net.round, id: f.id }}, {who});
        }}""")


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
    give(host, guest, 400, 440)
    host.wait_for_function("standings()[0].name === 'Aino' && standings()[0].g === 840", timeout=4000)
    third.wait_for_function("standings()[0].name === 'Aino'", timeout=4000)
    # The host's clock runs the contest: the others follow it.
    host.evaluate("left = 100")
    guest.wait_for_function("Math.abs(left - 100) < 2", timeout=4000)
    assert host.errors == guest.errors == third.errors == []


def test_the_host_ends_the_contest_and_every_phone_gets_its_place(room):
    host, [guest] = room("Eero", "Aino")
    host.evaluate("myG = 500; myN = 2")
    give(host, guest, 300, 300, 300, 300)
    guest.wait_for_function("myG === 1200 && myN === 4", timeout=4000)
    host.evaluate("left = 0.2")
    guest.evaluate("left = 0.2")
    for p, res, saved in [(host, "2. sija · 0,50 kg", '{"kisat":1,"voitot":0}'), (guest, "Voitit! 🏆 1,20 kg", '{"kisat":1,"voitot":1}')]:
        p.wait_for_function("phase === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0", timeout=6000)
        assert p.locator("#aipr-result").inner_text().startswith(res)
        assert p.evaluate("localStorage.getItem('ai-pelit:pilkki:kaverit')") == saved
    assert host.errors == guest.errors == []


def test_a_phone_s_own_report_never_changes_its_catch(room):
    host, [guest] = room("Eero", "Aino")
    give(host, guest, 900)
    guest.wait_for_function("myG === 900", timeout=4000)
    # A report of a bigger catch, a smaller one, or one for another round: the host's list stays.
    guest.evaluate("""() => {
      AiPelitRooms.send({ t: 'me', round: net.round, g: 99999, n: 50, sp: 3 });
      AiPelitRooms.send({ t: 'me', round: net.round, g: 400, n: 1, sp: 3 });
      AiPelitRooms.send({ t: 'me', round: 'old', g: 5000, n: 9, sp: 0 });
    }""")
    host.wait_for_timeout(600)
    aino = guest.evaluate("AiPelitRooms.me")
    assert host.evaluate(f"[net.board[{json.dumps(aino)}].g, net.board[{json.dumps(aino)}].n, net.board[{json.dumps(aino)}].sp]") == [900, 1, 3]
    assert host.errors == guest.errors == []


def test_a_paused_contest_takes_no_fishing_input(room):
    host, [guest] = room("Eero", "Aino")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=5000)
    ax, ay = host.evaluate("augerC()")
    host.mouse.move(ax + 50, ay)
    host.mouse.down()
    for i in range(1, 7 * 24):
        a = i / 24 * 2 * math.pi
        host.mouse.move(ax + 50 * math.cos(a), ay + 50 * math.sin(a))
    host.mouse.up()
    assert host.evaluate("[phase, drill, holes.length]") == ["drill", 0, 0]
    # A hole ready and a fish biting: a tap does not hook it while paused.
    host.evaluate("holes.push(spot.i); toJig(); jigD = 2; bite(pond[0])")
    host.mouse.click(180, 500)
    assert host.evaluate("[phase, myN]") == ["bite", 0]
    assert host.errors == []


def test_a_guest_that_reloads_after_the_end_gets_its_real_place(room):
    host, [guest] = room("Eero", "Aino")
    give(host, guest, 200)
    host.evaluate("myG = 900; myN = 3")
    guest.wait_for_function("myG === 200", timeout=4000)
    # Aino's phone is away while the host lets the contest run out without it.
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1", timeout=5000)
    host.click("#aipr-goOn")
    host.evaluate("left = 0.2")
    host.wait_for_function("phase === 'done'", timeout=6000)
    room.relay.back(guest)
    guest.reload()
    guest.evaluate(RUN)
    guest.wait_for_function("phase === 'done' && document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0", timeout=8000)
    assert guest.locator("#aipr-result").inner_text().startswith("2. sija · 0,20 kg")
    assert guest.evaluate("localStorage.getItem('ai-pelit:pilkki:kaverit')") == '{"kisat":1,"voitot":0}'
    assert guest.errors == []


def test_friends_fish_one_shared_lake_of_fish(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    for p in (guest, third):
        p.wait_for_function("pond.length > 50", timeout=5000)
    ids = host.evaluate("pond.map(f => f.id).sort((a, b) => a - b).join()")
    assert guest.evaluate("pond.map(f => f.id).sort((a, b) => a - b).join()") == ids
    # The same fish in about the same place on every phone.
    host.evaluate("window.at = Object.fromEntries(pond.map(f => [f.id, [f.lx, f.ly, f.sp, f.g]]))")
    off = guest.evaluate("""(at) => pond.map(f => at[f.id] ? (at[f.id][2] === f.sp && at[f.id][3] === f.g ? Math.hypot(f.lx - at[f.id][0], f.ly - at[f.id][1]) : 99) : 99)""",
                         host.evaluate("window.at"))
    assert max(off) < 3
    # Aino lands a fish: it is gone from every phone's lake, and the catch is hers.
    caught = guest.evaluate("""() => {
      const f = pond[0]; claim(f);
      fight = { fish: f, L: 0, T: 0, over: 0, burst: 0, next: 9, t: 0, sway: 0 }; phase = 'fight';
      land(); return [f.id, f.g];
    }""")
    for p in (host, third):
        p.wait_for_function(f"!pond.some(f => f.id === {caught[0]})", timeout=4000)
    # It counts on her phone once the host has said it was hers.
    guest.wait_for_function(f"myG === {caught[1]} && myN === 1", timeout=4000)
    # In her lifetime records once, though the host's lists after it carry its receipt too.
    guest.wait_for_timeout(1200)
    assert sum(json.loads(guest.evaluate("localStorage.getItem('ai-pelit:pilkki:kalat')")).values()) == 1
    assert guest.evaluate("pond.some(f => f.id === %d)" % caught[0]) is False
    host.wait_for_function("standings().find(s => s.name === 'Aino').g === %d" % caught[1], timeout=4000)
    assert host.errors == guest.errors == third.errors == []


def test_a_guest_jigs_and_lands_a_shared_fish_by_playing(room):
    host, [guest] = room("Eero", "Aino")
    guest.wait_for_function("pond.length > 50", timeout=5000)
    # Aino drills and holds her jig at the depth of a fish in sight; the host's phone stays still.
    host.evaluate("holes.push(spot.i); toJig()")
    guest.evaluate("""() => {
      holes.push(spot.i); toJig(); sight();
      const f = fish[0] || pond[0];
      f.lx = f.wx = spot.x + 0.5; f.ly = f.wy = spot.y; f.linger = 999; f.go = false; sight();
      jigD = f.d; window.want = f.id;
    }""")
    phase, n = guest.evaluate(ON_BEAT, 14)
    assert phase == "bite"
    assert guest.evaluate("biter.id === want")
    host.wait_for_function(f"net.claims[{guest.evaluate('want')}] === {json.dumps(guest.evaluate('AiPelitRooms.me'))}", timeout=4000)
    guest.evaluate("strike()")
    assert guest.evaluate(FIGHT) == "caught"
    host.wait_for_function(f"!pond.some(f => f.id === {guest.evaluate('want')})", timeout=4000)
    assert host.errors == guest.errors == []


def test_a_catch_the_host_accepted_counts_even_if_the_phone_misses_the_answer(room):
    host, [guest] = room("Eero", "Aino")
    guest.wait_for_function("pond.length > 50", timeout=5000)
    aino = guest.evaluate("AiPelitRooms.me")
    # Aino's phone has a fish on the line; its connection drops just as its "caught" reaches the
    # host, so the host's answer never gets to it.
    x, g = guest.evaluate("""() => {
      const f = pond[0]; f.look = true; claim(f); holes.push(spot.i); toJig();
      fight = { fish: f, L: 1, T: 0.3, over: 0, burst: 0, next: 9, t: 0, sway: 0 }; phase = 'fight';
      return [f.id, f.g];
    }""")
    host.wait_for_function(f"net.claims[{x}] === {json.dumps(aino)}", timeout=4000)
    room.relay.drop(guest)
    host.evaluate(f"hostFish({{ t: 'caught', round: net.round, id: {x} }}, {json.dumps(aino)})")
    # The host counted it to her the moment it accepted it.
    assert host.evaluate(f"[pond.some(f => f.id === {x}), standings().find(s => s.name === 'Aino').g]") == [False, g]
    # She reloads while away and comes back: the catch is hers on her phone too, counted once.
    room.relay.back(guest)
    guest.reload()
    guest.evaluate(RUN)
    guest.wait_for_function(f"net.on && myG === {g} && myN === 1", timeout=8000)
    host.wait_for_timeout(1200)
    assert host.evaluate("standings().find(s => s.name === 'Aino').g") == g
    assert guest.evaluate("[myG, myN]") == [g, 1]
    # Its lifetime records have the fish too, once, however many host lists come after.
    sp = host.evaluate(f"net.board[{json.dumps(aino)}].fish[0][1]")
    guest.wait_for_timeout(1200)
    assert json.loads(guest.evaluate("localStorage.getItem('ai-pelit:pilkki:kalat')")) == {sp: 1}
    assert json.loads(guest.evaluate("localStorage.getItem('ai-pelit:pilkki:suurin')")) == {"s": sp, "g": g}
    assert host.errors == guest.errors == []


def test_two_phones_racing_for_one_fish_only_the_first_gets_it(room):
    host, [guest] = room("Eero", "Aino")
    guest.wait_for_function("pond.length > 50", timeout=5000)
    me = host.evaluate("AiPelitRooms.me")
    reel = """(id) => {
      const f = pond.find(q => q.id === id); f.look = true; holes.push(spot.i); toJig(); lastDepth = 2;
      fight = { fish: f, L: 2, T: 0.3, over: 0, burst: 0, next: 9, t: 0, sway: 0 }; phase = 'fight';
    }"""
    # The host's phone had the fish first; Aino's phone lands it before it hears so: it does not count.
    x = host.evaluate("const f = pond[1]; net.claims[f.id] = AiPelitRooms.me; f.id")
    guest.evaluate(reel, x)
    guest.evaluate("holding = 1; fight.L = 0.001; fightStep(DT); holding = 0")
    assert guest.evaluate("phase") == "caught"
    guest.wait_for_function("!Object.keys(net.pending).length", timeout=4000)
    assert guest.evaluate("[myG, myN]") == [0, 0]
    assert host.evaluate(f"[pond.some(f => f.id === {x}), net.claims[{x}]]") == [True, me]
    host.wait_for_timeout(1200)
    assert host.evaluate("standings().find(s => s.name === 'Aino').g") == 0
    # On the line when it hears the host gave the fish to another: it slips off, nothing is counted.
    guest.evaluate("afterCatch()")
    y = host.evaluate("const f = pond[2]; net.claims[f.id] = AiPelitRooms.me; f.id")
    guest.evaluate(reel, y)
    host.evaluate("AiPelitRooms.send(pondMsg())")
    guest.wait_for_function("phase === 'jig' && !fight", timeout=4000)
    assert guest.evaluate("[myG, myN]") == [0, 0]
    assert host.errors == guest.errors == []


def test_a_fish_is_one_phone_s_at_a_time(room):
    host, [guest] = room("Eero", "Aino")
    guest.wait_for_function("pond.length > 50", timeout=5000)
    me, aino = host.evaluate("AiPelitRooms.me"), guest.evaluate("AiPelitRooms.me")
    # The host's phone got this fish first: Aino's claim is turned down, and she lets it go.
    x = host.evaluate("const f = pond[1]; net.claims[f.id] = AiPelitRooms.me; f.id")
    guest.evaluate(f"const f = pond.find(q => q.id === {x}); f.look = true; claim(f)")
    guest.wait_for_function(f"net.claims[{x}] === {json.dumps(me)} && !pond.find(q => q.id === {x}).look", timeout=4000)
    assert host.evaluate(f"net.claims[{x}]") == me
    # Aino claims another: the host's phone leaves it alone while she has it.
    y = guest.evaluate("const f = pond[2]; f.look = true; claim(f); f.id")
    host.wait_for_function(f"net.claims[{y}] === {json.dumps(aino)}", timeout=4000)
    assert host.evaluate(f"taken(pond.find(f => f.id === {y}))") is True
    # Scared off on her phone, it is free again and swims away on the host.
    guest.evaluate(f"scare(pond.find(q => q.id === {y}), 3)")
    host.wait_for_function(f"!net.claims[{y}] && pond.find(f => f.id === {y}).go", timeout=4000)
    # A phone whose connection drops and comes back keeps the fish it is reeling.
    w = guest.evaluate("""() => {
      const f = pond[4]; f.look = true; claim(f); holes.push(spot.i); toJig(); lastDepth = 2;
      fight = { fish: f, L: 2, T: 0.3, over: 0, burst: 0, next: 9, t: 0, sway: 0 }; phase = 'fight'; return f.id;
    }""")
    host.wait_for_function(f"net.claims[{w}] === {json.dumps(aino)}", timeout=4000)
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=5000)
    room.relay.back(guest)
    host.wait_for_function(f"!AiPelitRooms.paused && net.claims[{w}] === {json.dumps(aino)}", timeout=8000)
    assert guest.evaluate(f"[phase, fight && fight.fish.id]") == ["fight", w]
    guest.evaluate("fight = null; toJig()")
    # A phone that reloads holds no fish any more.
    z = guest.evaluate("const f = pond[3]; f.look = true; claim(f); f.id")
    host.wait_for_function(f"net.claims[{z}] === {json.dumps(aino)}", timeout=4000)
    guest.reload()
    guest.evaluate(RUN)
    host.wait_for_function(f"!net.claims[{z}]", timeout=8000)
    guest.wait_for_function("net.on && pond.length > 50", timeout=8000)
    assert host.errors == guest.errors == []


def test_a_guest_that_reloads_mid_contest_keeps_its_catch(room):
    host, [guest] = room("Eero", "Aino")
    give(host, guest, 200, 200, 250)
    guest.wait_for_function("myG === 650", timeout=4000)
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
