"""Eukonkanto v1 (#501): carry the wife over two logs and through the water pit, and do not drop her.

What the design review asked the code to answer (on the issue): the +15 s per drop is added once,
on the phone that runs the couple; a race with friends ends when everyone is in or 30 s after the
first; a couple still out then gets an estimated time, marked; and a phone saves and sends only its
own row of the delivered results, and only when that row is not an estimate."""
import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay
from yleisurheilu_asut import DECEMBER

URL = "games/eukonkanto/v1/"
SHARED = "ai-pelit:_asut:yleisurheilu"
KEY = "ai-pelit:eukonkanto:"
# Records what the game sends to the high-score list instead of sending it.
SPY = "() => { window.__sent = []; AiPelitScores.submit = s => { window.__sent.push(s); }; }"
# Plays this phone's own couple for a few seconds of race clock, the way a quick player would:
# feet in turn, a grab when the slip meter is past half, a jump just before each log.
PLAY = """(secs) => {
  let n = 0, foot = 1;
  for (let i = 0; i < secs * 60 && race && race.phase !== 'done'; i++) {
    if (race.phase === 'run' && me.fin === null) {
      if (i % 7 === 0) { press(foot); foot = 3 - foot; }
      if (me.s > 0.5) press(4);
      const lx = LOGS.find(l => l > me.x);
      if (lx !== undefined && lx - me.x < 0.25 + me.v * 0.2) press(3);
    }
    tick(1 / 60); n++;
  }
  return n;
}"""


def build(site):
    if not (site.games / "eukonkanto").exists():
        shutil.copytree(ROOT / "games" / "eukonkanto", site.games / "eukonkanto")
        site.build()


def open_game(site, browser, store=None, width=360, height=740):
    build(site)
    ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
    for k, v in (store or {}).items():
        ctx.add_init_script(f"localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))})")
    ctx.add_init_script(DECEMBER)
    page = ctx.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof race !== 'undefined' && window.AiPelitScores")
    page.evaluate(SPY)
    return page


def to_gun(page):
    """Starts a race alone and runs its clock to the gun, without waiting in real time."""
    page.click("#go")
    page.evaluate("() => { race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 0.05; tick(0.06); }")
    assert page.evaluate("race.phase") == "run"


def saved(page, name):
    v = page.evaluate(f"localStorage.getItem('{KEY}{name}')")
    return None if v is None else json.loads(v)


def test_a_race_alone_plays_to_the_end_and_saves_its_own_time(site, browser):
    page = open_game(site, browser)
    to_gun(page)
    page.evaluate(PLAY, 120)
    assert page.evaluate("race.phase") == "done"
    fin, row = page.evaluate("[me.fin, race.row]")
    assert 45 < fin < 120
    assert row["id"] == "me" and not row["est"] and row["fin"] == fin
    assert saved(page, "ennatys") == fin
    assert saved(page, "juoksut") == 1
    assert page.evaluate("window.__sent") == [fin]
    assert page.evaluate("me.down") == 0, "the jumps cleared both logs"
    page.evaluate("draw()")
    page.evaluate("race.doneT = 9; tick(0.01)")
    assert page.is_visible("#menu")
    assert "Ennätys" in page.inner_text("#stats")
    assert page.errors == []
    page.context.close()


def test_a_drop_adds_fifteen_seconds_once(site, browser):
    page = open_game(site, browser)
    to_gun(page)
    page.evaluate("() => { me.x = 230; me.v = 6; me.s = 0.999; tick(1 / 60); }")
    assert page.evaluate("[me.drops, me.downT > 0, me.v]") == [1, True, 0]
    # Picking her up takes a while and she cannot run meanwhile.
    page.evaluate("() => { press(1); press(2); }")
    assert page.evaluate("me.v") == 0
    page.evaluate("() => { for (let i = 0; i < 200 && me.downT > 0; i++) tick(1 / 60); }")
    page.evaluate("() => { me.x = TRACK - 0.01; me.v = 5; me.s = 0; tick(1 / 60); }")
    fin, clock = page.evaluate("[me.fin, me.finClock]")
    assert fin == pytest.approx(clock + 15, abs=0.02)
    # The results, the record and the list take fin as it is: nothing is added a second time.
    page.evaluate("() => { race.runners.forEach(r => { if (r !== me) r.card = 2; }); tick(1 / 60); }")
    assert page.evaluate("race.row.fin") == fin
    assert saved(page, "ennatys") == fin
    assert page.evaluate("window.__sent") == [fin]
    page.evaluate("race.doneT = 9; tick(0.01)")
    assert "1 pudotus" in page.inner_text("#result")
    assert page.errors == []
    page.context.close()


def test_a_fall_in_the_step_that_reaches_the_line_comes_before_the_finish(site, browser):
    """Review on #506: her fall and the line in one step are taken in the order they came."""
    page = open_game(site, browser)
    to_gun(page)
    # She slips off at once, 10 cm before the line: a drop there, no finish this step.
    page.evaluate("() => { me.x = TRACK - 0.1; me.v = 7; me.s = 0.9999; tick(1 / 60); }")
    assert page.evaluate("[me.fin, me.drops, me.x < TRACK, me.downT > 0]") == [None, 1, True, True]
    # The pick-up's 1.8 s and the 15 s are both in the time when they cross after it.
    clock = page.evaluate("race.clock")
    # Up again and over the last 10 cm in the same turn: the page's own frames must not decide it.
    fin = page.evaluate("() => { for (let i = 0; i < 200 && me.downT > 0; i++) tick(1 / 60);"
                        " for (let i = 0; i < 10 && me.fin === null; i++) { me.v = 5; tick(1 / 60); } return me.fin; }")
    assert fin is not None and fin > clock + 1.75 + 15
    page.context.close()


def test_the_line_before_the_fall_in_one_step_is_a_finish(site, browser):
    page = open_game(site, browser)
    to_gun(page)
    # 1 cm to go at 7 m/s: the line comes in the first tenth of the step, the slip only past half.
    # Read in the same turn as the step: the page's own frames run the clock on between evaluates.
    fin, drops, clock = page.evaluate(
        "() => { me.x = TRACK - 0.01; me.v = 7; me.s = 0.995; tick(1 / 60); return [me.fin, me.drops, race.clock]; }")
    # The line at 0.0014 s into the 1/60 s step: the time is the clock at that moment.
    assert drops == 0 and fin == pytest.approx(clock - 1 / 60 + 0.0014, abs=0.006)
    page.context.close()


LOG_CASES = [
    # (what, x, v, y, vy, dt, tripped): the height counts as the couple crosses the log at 62 m.
    ("coming down, over the log as it crosses, under the clearing height by the end", 61.9, 6, 0.35, -1, 0.05, False),
    ("coming down, landed just before the log", 61.7, 6, 0.05, -1, 0.07, True),
    ("going up, under the clearing height as it crosses, over it by the end", 61.95, 6, 0.1, 4, 0.07, True),
    ("going up, already over the log as it crosses", 61.95, 6, 0.32, 3, 0.07, False),
]


@pytest.mark.parametrize("what,x,v,y,vy,dt,tripped", LOG_CASES, ids=[c[0][:30] for c in LOG_CASES])
def test_a_log_is_judged_at_the_moment_it_is_crossed(site, browser, what, x, v, y, vy, dt, tripped):
    """Review on #506: not by the height at the end of the step."""
    page = open_game(site, browser)
    to_gun(page)
    page.evaluate(f"() => {{ Object.assign(me, {{ x: {x}, v: {v}, y: {y}, vy: {vy}, s: 0 }}); tick({dt}); }}")
    assert page.evaluate("[me.hits, (me.down & 1) === 1, me.x > 62]") == [int(tripped), tripped, True], what
    assert page.errors == []
    page.context.close()


@pytest.mark.parametrize("where", ["TRACK", "LOGS[0]", "WET[0]"])
def test_an_event_at_the_very_end_of_a_step_still_comes(site, browser, where):
    """Review on #506: 25 cm at 5 m/s is exactly a 0.05 s step; the line, the log or the edge counts."""
    page = open_game(site, browser)
    to_gun(page)
    got = page.evaluate(f"""() => {{
      Object.assign(me, {{ x: {where} - 0.25, v: 5, s: 0, y: 0, vy: 0 }}); tick(0.05);
      const a = [me.fin !== null, me.hits, wading(me)];
      if (me.fin === null) {{ me.v = 5; tick(0.05); }}
      return [...a, me.fin !== null, me.hits];
    }}""")
    want = {"TRACK": [True, 0, False, True, 0], "LOGS[0]": [False, 1, False, False, 1], "WET[0]": [False, 0, True, False, 0]}
    assert got == want[where]
    page.context.close()


def test_a_long_step_into_the_water_brakes_from_the_edge_on(site, browser):
    page = open_game(site, browser)
    to_gun(page)
    # 0.1 s on sand, then 0.4 s wading at 7 m/s: the water's braking takes it from the edge on.
    # On sand all the way it would still run at about 5.9 m/s.
    page.evaluate("() => { Object.assign(me, { x: WET[0] - 0.7, v: 7, s: 0 }); tick(0.5); }")
    assert page.evaluate("[wading(me), me.v < 3, me.x > WET[0]]") == [True, True, True]
    page.context.close()


@pytest.mark.parametrize("steps", [1, 30])
def test_a_fall_and_the_line_keep_their_order_in_long_and_short_steps(site, browser, steps):
    """The two are at least 0.3 s apart here, so the rate fixed per piece cannot swap them."""
    page = open_game(site, browser)
    to_gun(page)
    # Set and run in one turn, so the page's own frames cannot step in between.
    run = f"for (let i = 0; i < {steps}; i++) tick(0.5 / {steps});"
    # The fall at about 0.1 s, the line at about 0.43 s: she falls first.
    page.evaluate("() => { Object.assign(me, { x: TRACK - 3, v: 7, s: 0.95 }); " + run + " }")
    assert page.evaluate("[me.fin, me.drops]") == [None, 1]
    # The line at 0.05 s, the fall not before 0.18 s: a finish, no drop.
    page.context.close()
    page = open_game(site, browser)
    to_gun(page)
    page.evaluate("() => { Object.assign(me, { x: TRACK - 0.35, v: 7, s: 0.9 }); " + run + " }")
    assert page.evaluate("[me.fin !== null, me.drops]") == [True, 0]
    assert page.errors == []
    page.context.close()


def test_a_couple_still_out_gets_an_estimate_and_it_is_not_saved(site, browser):
    page = open_game(site, browser)
    to_gun(page)
    page.evaluate("() => { me.x = 200; me.v = 5; me.drops = 1; }")
    rows = page.evaluate("standings(race.clock)")
    mine = next(r for r in rows if r["id"] == "me")
    assert mine["est"] and mine["fin"] > page.evaluate("race.clock") + 15
    page.evaluate("finish(standings(race.clock))")
    assert saved(page, "ennatys") is None and saved(page, "juoksut") is None
    assert page.evaluate("window.__sent") == []
    page.evaluate("race.doneT = 9; tick(0.01)")
    assert "(arvio)" in page.inner_text("#result")
    page.context.close()


def test_a_win_alone_raises_the_level(site, browser):
    page = open_game(site, browser, {KEY + "taso": 3})
    to_gun(page)
    assert page.evaluate("race.runners.find(r => r.id === 'a').name") == "Ville ja Veera"
    page.evaluate("() => { race.runners.forEach(r => { if (r !== me) r.card = 2; }); me.x = TRACK - 0.01; me.v = 6; tick(1 / 60); }")
    assert page.evaluate("race.mine") == 0
    assert [saved(page, k) for k in ("taso", "voitot", "juoksut")] == [4, 1, 1]
    page.evaluate("race.doneT = 9; tick(0.01)")
    assert page.inner_text("#result").startswith("Voitit!")
    assert "Taso 4" in page.inner_text("#foe")
    page.context.close()


def test_two_steps_before_the_gun_are_a_yellow_then_a_red_card(site, browser):
    page = open_game(site, browser)
    page.click("#go")
    page.evaluate("() => { race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 9; tick(SET_AT + 0.05); press(1); }")
    assert page.evaluate("[race.phase, me.card]") == ["false", 1]
    page.evaluate("() => { tick(FS_SHOW + 0.01); tick(SET_AT + 0.05); press(2); }")
    assert page.evaluate("me.card") == 2
    page.evaluate("tick(FS_SHOW + 0.01)")
    assert page.evaluate("race") is None
    assert "hylätty" in page.inner_text("#result")
    assert saved(page, "juoksut") is None
    page.context.close()


def test_nobody_moves_or_slips_before_the_gun_even_after_a_false_start(site, browser):
    page = open_game(site, browser)
    page.click("#go")
    still = "race.runners.map(r => [r.x, r.s, r.v])"
    page.evaluate("() => { race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 9; }")
    before = page.evaluate(still)
    page.evaluate("() => { for (let i = 0; i < 40; i++) tick(0.05); }")  # 2 s of countdown
    assert page.evaluate(still) == before
    # A computer couple's false start, the card shown, and the countdown again: still nothing moves.
    page.evaluate("() => { const c = race.runners.find(r => r.kind === 'cpu'); c.ai.jumpy = SET_AT + 0.1; tick(SET_AT + 0.2); }")
    assert page.evaluate("race.phase") == "false"
    page.evaluate("() => { tick(FS_SHOW + 0.01); race.runners.forEach(r => { r.ai.jumpy = null; }); race.gunAt = 9; for (let i = 0; i < 40; i++) tick(0.05); }")
    assert page.evaluate("race.phase") == "cd"
    assert page.evaluate(still) == before
    assert page.errors == []
    page.context.close()


def test_the_menu_is_not_drawn_again_and_again(site, browser):
    page = open_game(site, browser)
    page.evaluate("() => { window.__draws = 0; const d = draw; window.draw = () => { window.__draws++; d(); }; }")
    page.wait_for_timeout(500)
    assert page.evaluate("window.__draws") == 0
    page.set_viewport_size({"width": 740, "height": 360})
    page.wait_for_timeout(300)
    assert 1 <= page.evaluate("window.__draws") <= 3, "turning the phone draws the scene once more"
    to_gun(page)
    page.wait_for_timeout(300)
    assert page.evaluate("window.__draws") > 6
    page.context.close()


@pytest.mark.parametrize("size", [(360, 740), (740, 360)])
def test_each_pad_is_where_it_is_drawn(site, browser, size):
    page = open_game(site, browser, width=size[0], height=size[1])
    to_gun(page)
    got = page.evaluate("pads().map(p => [p.k, padAt(p.x + p.w / 2, p.y + p.h / 2)])")
    assert sorted(k for k, _ in got) == [1, 2, 3, 4]
    assert all(k == hit for k, hit in got)
    # A tap on the scene does nothing.
    assert page.evaluate("padAt(W / 2, trackTop + 20)") == 0
    # Nor does one in a gap between pads, or above, below and beside them (review on #506).
    gaps = page.evaluate("""(() => { const p = {}; pads().forEach(q => { p[q.k] = q; });
      const mid = q => q.x + q.w / 2;
      return [[mid(p[3]), (p[3].y + p[3].h + p[1].y) / 2], [mid(p[4]), (p[4].y + p[4].h + p[2].y) / 2],
        [mid(p[3]), p[3].y - 3], [mid(p[1]), p[1].y + p[1].h + 3], [p[1].x - 3, p[1].y + 5]]; })()""")
    assert [page.evaluate(f"padAt({x}, {y})") for x, y in gaps] == [0, 0, 0, 0, 0]
    # Upright the feet are at the bottom, jump on the left and hold on the right above them.
    p = {k: (x, y) for k, x, y in page.evaluate("pads().map(p => [p.k, p.x, p.y])")}
    assert p[1][0] < p[2][0] and p[3][0] < p[4][0]
    assert p[3][1] < p[1][1] and p[4][1] < p[2][1]
    page.mouse.click(*page.evaluate("(() => { const q = pads().find(p => p.k === 4); return [q.x + q.w / 2, q.y + q.h / 2]; })()"))
    assert page.evaluate("me.holdT") > 0
    assert page.errors == []
    page.context.close()


def test_an_outfit_picked_in_another_event_is_worn_here(site, browser):
    page = open_game(site, browser, {SHARED: "noita"})
    assert page.inner_text("#asu") == "👕 Asu: Noita"
    page.click("#go")
    assert page.evaluate("me.asu") == "noita"
    page.context.close()


# #337: no crowd noise; #355: on aanet-5, the sounds Eero found too loud softer.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401,E402


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/eukonkanto/v1")


# ---------- With friends ----------

@pytest.fixture
def couples(site, browser):
    build(site)
    relay = Relay()
    contexts = []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi'," + json.dumps(json.dumps(name)) + ")")
        p = ctx.new_page()
        p.errors = []
        p.on("pageerror", lambda e: p.errors.append(str(e)))
        relay.attach(p)
        p.goto(site.url + URL)
        p.wait_for_function("typeof race !== 'undefined' && window.AiPelitScores")
        p.evaluate(SPY)
        return p

    yield phone
    for c in contexts:
        c.close()


def gid(page):
    return json.dumps(page.evaluate("AiPelitRooms.me"))


def race_with(phone, n=2):
    host = phone("Testi1")
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    code = host.evaluate("AiPelitRooms.code")
    pages = [host]
    for i in range(1, n):
        p = phone("Testi" + str(i + 1))
        p.click("#multi")
        p.fill("#aipr-codeIn", code)
        p.click("#aipr-joinBtn")
        p.wait_for_function("AiPelitRooms.inRoom")
        pages.append(p)
    host.wait_for_function(f"AiPelitRooms.members.filter(p => p.on).length === {n}")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=12000)
    return pages


def test_two_phones_race_and_each_keeps_its_own_time(couples):
    host, guest = race_with(couples)
    assert host.evaluate("race.runners.length") == 2
    # The guest drops her once and comes in; the host comes in clean.
    guest.evaluate("() => { me.drops = 1; me.x = TRACK - 0.02; me.v = 6; }")
    guest.wait_for_function("me.fin !== null")
    gfin = guest.evaluate("me.fin")
    host.wait_for_function(f"race.runners.find(r => r.id === {json.dumps(guest.evaluate('R.me'))}).fin === {gfin}")
    host.evaluate("() => { me.x = TRACK - 0.02; me.v = 6; }")
    for p in (host, guest):
        p.wait_for_function("race && race.phase === 'done'", timeout=8000)
    hres, gres = host.evaluate("race.results"), guest.evaluate("race.results")
    assert hres == gres
    grow = next(r for r in gres if r["id"] == guest.evaluate("R.me"))
    assert grow["fin"] == gfin and grow["drops"] == 1 and not grow["est"]
    hfin = host.evaluate("me.fin")
    assert saved(host, "ennatys") == hfin and saved(guest, "ennatys") == gfin
    assert host.evaluate("window.__sent") == [hfin] and guest.evaluate("window.__sent") == [gfin]
    # Back in the room.
    for p in (host, guest):
        p.wait_for_function("race === null", timeout=8000)
    assert host.errors == [] and guest.errors == []


def test_a_guest_whose_finish_the_host_never_heard_saves_nothing(couples):
    host, guest = race_with(couples)
    # The guest crosses the line on its own phone, but nothing it sends reaches the host any more.
    guest.evaluate("() => { R.send = () => {}; me.x = TRACK - 0.02; me.v = 6; }")
    guest.wait_for_function("me.fin !== null")
    # The host comes in and the race ends (as it would 30 s after it): the guest's row is an estimate.
    host.evaluate("() => { me.x = TRACK - 0.02; me.v = 6; }")
    host.wait_for_function("me.fin !== null")
    host.evaluate("() => { race.firstFin = race.clock - LATE - 1; }")
    for p in (host, guest):
        p.wait_for_function("race && race.phase === 'done'", timeout=8000)
    row = guest.evaluate("race.row")
    assert row["est"] and row["id"] == guest.evaluate("R.me")
    assert saved(guest, "ennatys") is None and saved(guest, "juoksut") is None
    assert guest.evaluate("window.__sent") == []
    assert saved(host, "ennatys") == host.evaluate("me.fin")
    guest.evaluate("race.doneT = 9; tick(0.01)")
    assert host.errors == [] and guest.errors == []


def test_the_host_ending_the_round_stops_the_race_everywhere(couples):
    host, guest = race_with(couples)
    host.evaluate("AiPelitRooms.stopRound()")
    for p in (host, guest):
        p.wait_for_function("race === null", timeout=8000)
    assert saved(host, "juoksut") is None and saved(guest, "juoksut") is None
    assert host.errors == [] and guest.errors == []


def test_three_phones_race_and_end_on_one_result(couples):
    pages = race_with(couples, 3)
    assert all(p.evaluate("race.runners.length") == 3 for p in pages)
    for i, p in enumerate(pages):
        p.evaluate(f"() => {{ me.x = TRACK - 0.02 - {i} * 0.5; me.v = 6; }}")
    for p in pages:
        p.wait_for_function("race && race.phase === 'done'", timeout=10000)
    res = [p.evaluate("race.results") for p in pages]
    assert res[0] == res[1] == res[2]
    assert not any(r["est"] for r in res[0])
    for p in pages:
        assert saved(p, "ennatys") == p.evaluate("me.fin")
    assert all(p.errors == [] for p in pages)


def test_a_guest_reloaded_mid_race_takes_its_couple_back(couples):
    host, guest = race_with(couples)
    guest.evaluate("() => { me.x = 80; me.v = 6; me.drops = 1; }")
    host.wait_for_function(f"race.runners.find(r => r.id === {gid(guest)}).x > 79")
    guest.reload()
    guest.wait_for_function("race && race.mode === 'net' && race.phase === 'run'", timeout=12000)
    guest.wait_for_function("me.x > 79 && me.drops === 1", timeout=8000)
    assert host.evaluate(f"race.runners.find(r => r.id === {gid(guest)}).x") > 79
    assert host.errors == [] and guest.errors == []


def test_a_guest_back_from_away_keeps_what_the_computer_ran(couples):
    host, guest = race_with(couples)
    g = gid(guest)
    # The computer runs the guest's couple while it is away, over the line, and hands it back
    # before the guest has heard any of it: the guest's own copy is still back at the start.
    host.evaluate(f"""() => {{ takeOver([{g}]); const r = race.runners.find(r => r.id === {g});
      r.x = TRACK - 0.02; r.v = 6; move(r, 1 / 60, race.clock); giveBack({g}); }}""")
    fin = host.evaluate(f"race.runners.find(r => r.id === {g}).fin")
    assert fin is not None
    guest.wait_for_function(f"me.fin === {fin}", timeout=8000)
    host.wait_for_function(f"!race.runners.find(r => r.id === {g}).give", timeout=8000)
    assert host.evaluate(f"race.runners.find(r => r.id === {g}).fin") == fin
    assert host.evaluate(f"race.runners.find(r => r.id === {g}).x") >= 253.5
    assert host.errors == [] and guest.errors == []


def test_a_host_reloaded_mid_race_loses_the_round_and_nothing_is_saved(couples):
    host, guest = race_with(couples)
    guest.evaluate("() => { me.x = TRACK - 0.02; me.v = 6; }")
    guest.wait_for_function("me.fin !== null")
    host.reload()
    guest.wait_for_function("race === null", timeout=12000)
    assert saved(guest, "ennatys") is None and guest.evaluate("window.__sent") == []
    assert guest.errors == []


def test_every_sound_it_loads_is_played():
    """Review on #506: a loaded sound nobody plays is a download for nothing on every new phone."""
    import re
    src = (ROOT / "games" / "eukonkanto" / "v1" / "index.html").read_text()
    loaded = set(re.findall(r"'([a-z0-9]+)'", re.search(r"S\.load\(\[(.*?)\]\)", src).group(1)))
    played = set(re.findall(r"S\.(?:play|loop)\('([a-z0-9]+)'", src)) | {"askel", "askel2"}  # the feet pick one of two
    assert loaded == played
