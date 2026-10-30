"""Kaaosrata in a phone-sized Chromium, alone and in a room of two phones."""

import json

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/kaaosrata/v1/"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    page.wait_for_function("race && race.phase === 'run'", timeout=6000)
    # The computer's players out of the way, standing still at the start.
    page.evaluate("race.runners.forEach(r => { if (r !== me) Object.assign(r, { kind: 'net', x: -4, y: -3, vx: 0, vy: 0 }); })")
    return page


def put(page, **kw):
    page.evaluate(f"Object.assign(me, {{ z: 0, vx: 0, vy: 0, vz: 0, stun: 0, cd: 0, fall: 0 }}, {json.dumps(kw)})")


def test_the_stick_runs_up_the_course_and_a_tap_jumps(site, context):
    page = start(site, context)
    put(page, x=0, y=2)
    page.evaluate("input.x = 0; input.y = 1")
    page.wait_for_function("me.y > 5", timeout=3000)
    page.evaluate("input.y = 0; press()")
    page.wait_for_function("me.z > 0.5", timeout=1000)
    page.wait_for_function("me.z === 0", timeout=2000)
    assert page.evaluate("me.fall") == 0


def test_a_tap_before_the_start_does_not_move_or_jump(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("soloRace(); input.y = 1; press()")
    page.wait_for_timeout(600)
    assert page.evaluate("[race.phase, me.y, me.z, me.jq]") == ["cd", 0, 0, 0]


def test_off_the_floor_you_fall_and_come_back_at_the_last_checkpoint(site, context):
    page = start(site, context)
    # Between two stepping stones, past the first checkpoint.
    put(page, x=-1.7, y=40, cp=1)
    page.wait_for_function("me.fall > 0", timeout=2000)
    page.wait_for_function("me.fall === 0", timeout=3000)
    assert page.evaluate("[me.y, me.cp, Math.abs(me.x) <= 3]") == [35.5, 1, True]


def test_a_jump_over_the_gap_lands_on_a_stone(site, context):
    page = start(site, context)
    put(page, x=0, y=36.5, vy=5.5, cp=1)
    page.evaluate("input.x = 0; input.y = 1; press()")
    page.wait_for_function("me.y > 39.5 && me.z === 0", timeout=2000)
    page.evaluate("input.y = 0")
    page.wait_for_timeout(300)
    assert page.evaluate("me.fall") == 0


def test_a_spinning_bar_sweeps_away_a_player_standing_in_its_way(site, context):
    page = start(site, context)
    put(page, x=3, y=18)
    page.wait_for_function("me.knocks > 0", timeout=6000)
    assert page.evaluate("me.stun > 0 || Math.hypot(me.x - 3, me.y - 18) > 0.5")


def test_players_bump_each_other_apart(site, context):
    page = start(site, context)
    put(page, x=0, y=5)
    page.evaluate("const o = race.runners[1]; Object.assign(o, { kind: 'cpu', x: 0.3, y: 5, z: 0, vx: -4, vy: 0, fall: 0 }); o.ai.skill = 0")
    page.wait_for_timeout(100)
    assert page.evaluate("Math.hypot(me.x - race.runners[1].x, me.y - race.runners[1].y)") >= 0.75


# Two runners overlapping, the first having finished or not, then one round of bumping: how far
# the second one was pushed, and how fast.
OVERLAP = """fin => {
  const a = race.runners[0], b = race.runners[1];
  Object.assign(a, { x: 0, y: 135, z: 0, vx: 4, vy: 0, fall: 0, fin });
  Object.assign(b, { x: 0.3, y: 135, z: 0, vx: 0, vy: 0, fall: 0, fin: null });
  bumps();
  return [Math.abs(b.x - 0.3) + Math.abs(b.y - 135), Math.hypot(b.vx, b.vy)];
}"""


def test_a_finished_player_cannot_push_one_still_racing(site, context):
    page = start(site, context)
    page.evaluate("race.runners[1].kind = 'cpu'")  # the second one moved here too, so it can be pushed
    assert page.evaluate(OVERLAP, 12.5) == [0, 0]
    pushed, speed = page.evaluate(OVERLAP, None)
    assert pushed > 0.1 and speed > 1


def test_the_finish_ends_the_race_and_a_win_raises_the_level(site, context):
    page = start(site, context)
    put(page, x=0, y=139.5, vy=5, cp=4)
    page.evaluate("input.y = 1")
    page.wait_for_function("me.fin !== null", timeout=2000)
    page.wait_for_function("!race && !document.getElementById('menu').classList.contains('hidden')", timeout=12000)
    assert page.evaluate("localStorage.getItem('ai-pelit:kaaosrata:taso')") == "2"
    assert page.evaluate("localStorage.getItem('ai-pelit:kaaosrata:voitot')") == "1"
    assert page.inner_text("#result").startswith("Voitit!")
    page.reload()
    assert "Taso 2" in page.inner_text("#foe")
    assert "Ennätys" in page.inner_text("#stats")


def test_the_computer_gets_through_the_whole_course(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    # A whole race at 30 steps a second, run as fast as the page can; this phone's player stays put.
    done = page.evaluate("""() => {
      soloRace(); race.phase = 'run'; race.late = 999;
      Object.assign(me, { kind: 'net', y: -60 });
      for (let i = 0; i < LIMIT * 30 && race.phase === 'run'; i++) tick(1 / 30);
      return race.runners.filter(r => r.bot && r.fin !== null).length;
    }""")
    assert done >= 5


def room_of_two(site, browser):
    """Eero's phone makes a room, Aino's joins it, and the race is on."""
    relay = Relay()
    pages = []
    for name in ["Eero", "Aino"]:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        pages.append(page)
    host, guest = pages
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    guest.click("#multi")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=8000)
    return host, guest


def test_two_phones_race_with_bots_and_both_get_the_results(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    pages = [host, guest]
    names = ["Eero", "Aino", "Jellu", "Pomppu-Pekka", "Kumi-Kaisa", "Hytky"]
    assert guest.evaluate("race.runners.map(r => r.name)") == names
    assert host.evaluate("race.runners.map(r => r.kind)") == ["me", "net", "cpu", "cpu", "cpu", "cpu"]
    # The bots run on the host and show on the guest.
    guest.wait_for_function("race.runners[2].best > 3", timeout=5000)
    # The guest's own player reaches the host.
    guest.evaluate("Object.assign(me, { x: 0, y: 36, cp: 1, vx: 0, vy: 0 })")
    host.wait_for_function("race.runners[1].y >= 35.5 && race.runners[1].cp === 1", timeout=3000)
    # A reload mid-race gives the guest its player back where it was.
    guest.reload()
    guest.wait_for_function("race && race.phase === 'run' && me.y >= 35 && me.cp === 1", timeout=8000)
    # Both run in, the guest first.
    guest.evaluate("Object.assign(me, { x: 0, y: 139.5, vy: 5, cp: 4 }); input.y = 1")
    host.wait_for_function("race.runners[1].fin !== null", timeout=3000)
    host.evaluate("Object.assign(me, { x: 0, y: 139.5, vy: 5, cp: 4 }); input.y = 1")
    guest.wait_for_function("race && race.phase === 'done'", timeout=8000)
    assert guest.evaluate("race.results.slice(0, 2).map(r => r.name)") == ["Aino", "Eero"]
    for p in pages:
        p.wait_for_function("AiPelitRooms.inRoom && !race && document.getElementById('aipr-result').textContent !== ''", timeout=10000)
    assert guest.inner_text("#aipr-result").startswith("1. sija")
    assert host.inner_text("#aipr-result").startswith("2. sija")
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()


def test_in_a_room_a_finished_guest_cannot_push_the_host(site, browser):
    site.build(ROOT / "games")
    host, guest = room_of_two(site, browser)
    # On the host, its own player is runners[1] here and the guest's player runners[0]: swap them in.
    flip = OVERLAP.replace("race.runners[0], b = race.runners[1]", "race.runners[1], b = race.runners[0]")
    assert host.evaluate(flip, 12.5) == [0, 0]
    pushed, _ = host.evaluate(flip, None)
    assert pushed > 0.1
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()
