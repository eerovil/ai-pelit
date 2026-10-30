"""Hiihto v3 (#61): two styles, classic or skating, and a race with friends on the same course."""

import json

import pytest

from conftest import ROOT
from test_hiihto import BOT, EMPTY, RUN
from test_rooms_lib import Relay

URL = "games/hiihto/v3/"

# Skates one race as a good skater: the right glide wax (or the given one), pushes on alternate
# skis every 0.36 s (or always the same one), the tuck down the hills, and the other half of the
# skating lane round a slower skater when it is clear.
SKATE_BOT = """(opts) => {
  opts = opts || {};
  const tap = (px, py) => { down(7, px, py); up(7); };
  const swipe = d => { down(8, W / 2, H / 2); move(8, W / 2 + 60 * d, H / 2); up(8); };
  draw();
  if (mode === 'wax') { const r = ui.wax[opts.wax ?? bestGlide(course.weather.T)]; tap(r.x + 5, r.y + 5); }
  for (let i = 0; i < 400 && mode === 'count'; i++) step(1 / 60);
  let next = 0, holding = false, lastSteer = -9, side = 1;
  const slowIn = (lane, a, b) => npcs.some(o => o.slow && o.lane === lane && o.z - P.z > a && o.z - P.z < b);
  for (let i = 0; i < 60 * 900 && mode === 'race'; i++) {
    const g = gradeAt(P.z + 2);
    if (clock - lastSteer > 0.4 && P.fallT <= 0) {
      const look = 6 + P.v * 1.6, other = P.lane === 1 ? 2 : 1;
      if (P.lane === 0) { swipe(1); lastSteer = clock; }
      else if (slowIn(P.lane, -0.5, look) && !slowIn(other, -2.5, look)) { swipe(other > P.lane ? 1 : -1); lastSteer = clock; }
    }
    const blocked = slowIn(P.lane, 0, 3 + P.v);
    const wantHold = g < -0.02 && !blocked && P.v > 3;
    if (wantHold && !holding) { down(9, W / 2, H / 2); holding = true; }
    if (!wantHold && holding) { up(9); holding = false; }
    if (!holding && !blocked && clock >= next) {
      if (!opts.same) side = -side;
      tap(side < 0 ? W * 0.25 : W * 0.75, H / 2 + 40); next = clock + 0.36;
    }
    step(1 / 60);
  }
  if (holding) up(9);
  return { mode, t: P.t, par: course.par, falls, passes, stars: result && result.stars };
}"""


def open_game(site, context, saves=None):
    site.build(ROOT / "games")
    if saves:
        context.add_init_script("".join(
            f"localStorage.setItem('ai-pelit:hiihto:{k}', {json.dumps(json.dumps(v))});" for k, v in saves.items()))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site.url}{URL}")
    page.wait_for_function("typeof course === 'object' && ui.wax.length === 4")
    page.errors = errors
    return page


def tap_style(page, st):
    page.evaluate("st => { draw(); const r = ui.styles.find(r => r.style === st); down(1, r.x + 5, r.y + 5); up(1); }", st)


def test_classic_plays_as_before_and_reads_v2_saves(site, context):
    page = open_game(site, context, {"taso": 3, "ajat": {"1": 200.5}, "tahdet": {"1": 2}})
    assert page.evaluate("[style, level, maxLevel, bests[1], stars[1]]") == ["perinteinen", 3, 3, 200.5, 2]
    page.evaluate("level = 1; newRace()")
    r = page.evaluate(BOT)
    assert r["mode"] == "done" and r["stars"] >= 1 and r["passes"] >= 3, r
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:luistelu-ajat')") is None
    assert page.errors == []


def test_skating_is_its_own_style_with_its_own_times(site, context):
    page = open_game(site, context)
    tap_style(page, "luistelu")
    assert page.evaluate("[style, localStorage.getItem('ai-pelit:hiihto:tyyli')]") == ["luistelu", '"luistelu"']
    assert page.evaluate("ui.wax.length === 4 && waxList()[0].name") == "Pakkanen"
    # The par is the skating one: a skate is faster than the stride on the same course.
    skate_par = page.evaluate("course.par")
    page.evaluate("style = 'perinteinen'; newRace()")
    assert skate_par < page.evaluate("course.par")
    page.evaluate("style = 'luistelu'; newRace()")
    r = page.evaluate(SKATE_BOT)
    assert r["mode"] == "done" and r["t"] < r["par"] and r["stars"] >= 1, r
    assert r["passes"] >= 3, r
    saved = page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:hiihto:luistelu-ajat'))")
    assert abs(saved["1"] - r["t"]) < 0.01
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:ajat')") is None
    assert page.evaluate("localStorage.getItem('ai-pelit:hiihto:taso')") == "2"
    # The style stays picked after a reload.
    page.reload()
    page.wait_for_function("typeof course === 'object'")
    assert page.evaluate("style") == "luistelu"
    assert page.errors == []


def test_skating_wants_alternate_skis(site, context):
    page = open_game(site, context)
    tap_style(page, "luistelu")
    page.evaluate(EMPTY.replace("bestWax", "bestGlide"), 1)
    page.evaluate("P.z = 20; P.v = 3; P.t = 5; P.side = 1")
    alt = page.evaluate("push(P, -1)")
    page.evaluate("P.t = 10")
    same = page.evaluate("push(P, -1)")
    assert alt > 2 * same
    assert page.evaluate("hint()[0]").startswith("Vuorotellen")
    # A tap on the left half pushes the left ski, on the right half the right one.
    page.evaluate("P.t = 20; P.sameT = 0; down(3, W * 0.2, H / 2); up(3)")
    assert page.evaluate("P.side") == -1
    page.evaluate("P.t = 21; down(3, W * 0.8, H / 2); up(3)")
    assert page.evaluate("P.side") == 1
    # Uphill the edge grips: the skater gets up a steep hill with no V step.
    z = page.evaluate("(() => { for (let z = 0; z < course.len; z++) if (gradeAt(z) > 0.1) return z; })()")
    top = page.evaluate("z => { while (gradeAt(z) > 0.03) z += 1; return z; }", z)
    climb = """z => { P.z = z - 10; P.v = 2; let next = 0;
      for (let i = 0; i < 60 * 40; i++) { if (P.t >= next) { push(P, -P.side); next = P.t + 0.34; } physics(P, 1 / 60); }
      return P.z; }"""
    assert page.evaluate(climb, z) > top
    assert page.errors == []


def test_the_wrong_glide_wax_is_slow(site, context):
    page = open_game(site, context)
    tap_style(page, "luistelu")
    # Level 1 is −6 °C: the wet-snow wax drags.
    assert page.evaluate("glideFit(GLIDES[3], -6).drag") > 0.04
    r = page.evaluate(SKATE_BOT, {"wax": 3})
    assert r["mode"] == "done", r
    assert page.evaluate("result.note").startswith("Luistovoide ei sopinut")


@pytest.mark.parametrize("w,h", [(360, 640), (390, 844)])
def test_it_fits_a_small_phone(site, browser, w, h):
    ctx = browser.new_context(viewport={"width": w, "height": h}, is_mobile=True, has_touch=True)
    page = open_game(site, ctx)
    page.evaluate("draw()")
    boxes = page.evaluate("[...ui.wax, ...ui.styles, ui.friends].map(r => [r.x, r.y, r.x + r.w, r.y + r.h])")
    for x0, y0, x1, y1 in boxes:
        assert 0 <= x0 and x1 <= w and 40 <= y0 and y1 <= h
    # Nothing overlaps: the wax buttons sit between the style switch and the friends button.
    assert max(b[3] for b in boxes[:4]) < boxes[6][1]
    assert min(b[1] for b in boxes[:4]) > boxes[4][3]
    ctx.close()


def room_of_two(site, browser, style="perinteinen", relay=None):
    """Eero's phone makes a room and picks the style, Aino's joins, and the round starts."""
    site.build(ROOT / "games")
    relay = relay or Relay()
    pages = []
    for name in ["Eero", "Aino"]:
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e, page=page: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        page.wait_for_function("typeof course === 'object'")
        pages.append(page)
    host, guest = pages
    host.evaluate("draw(); down(1, ui.friends.x + 5, ui.friends.y + 5); up(1)")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
    if style == "luistelu":
        host.click("#hiihto-room button[data-s=luistelu]")
    code = host.evaluate("AiPelitRooms.code")
    guest.evaluate("AiPelitRooms.open()")
    guest.fill("#aipr-codeIn", code)
    guest.click("#aipr-joinBtn")
    host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 2")
    guest.wait_for_function("document.getElementById('hiihto-room').textContent.includes('Eero')")
    host.click("#aipr-start")
    for p in pages:
        p.wait_for_function("net && net.cfg && mode === 'wax'", timeout=6000)
    return host, guest


def wax_and_go(pages):
    for p in pages:
        p.evaluate("draw(); const r = ui.wax[bestFor(style, course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1)")
    for p in pages:
        p.wait_for_function("mode === 'race'", timeout=8000)


def test_two_phones_ski_the_same_course_and_the_first_in_wins(site, browser):
    host, guest = room_of_two(site, browser, "luistelu")
    pages = [host, guest]
    # Same course, same style, same grannies and skaters to start with, for everyone.
    a, b = (p.evaluate("[level, style, course.len, npcs.map(o => Math.round(o.z))]") for p in pages)
    assert a == b and a[1] == "luistelu"
    # The guest's own style choice is not changed by the room's.
    assert guest.evaluate("localStorage.getItem('ai-pelit:hiihto:tyyli')") is None
    # The start waits for everyone's wax.
    host.evaluate("draw(); const r = ui.wax[bestGlide(course.weather.T)]; down(1, r.x + 5, r.y + 5); up(1)")
    host.wait_for_timeout(600)
    assert host.evaluate("[mode, net.phase]") == ["ready", "wax"]
    wax_and_go([guest])
    # Each sees the other on the trail.
    guest.evaluate("P.z = 120")
    host.wait_for_function("net.skiers[1].z >= 120", timeout=3000)
    host.evaluate("P.z = 60")
    guest.wait_for_function("net.skiers[0].z >= 60 && net.skiers[0].z < 100", timeout=3000)
    assert guest.evaluate("livePlace()") == 1
    # A reload mid-race gives the guest its skier back where it was.
    guest.reload()
    guest.wait_for_function("net && mode === 'race' && P.z >= 120", timeout=8000)
    # The guest finishes first, then the host; both get the same results.
    guest.evaluate("P.z = course.len - 0.5; P.v = 8")
    host.wait_for_function("net.skiers[1].fin !== null", timeout=4000)
    host.evaluate("P.z = course.len - 0.5; P.v = 8")
    for p in pages:
        p.wait_for_function("net && net.res", timeout=6000)
    assert guest.evaluate("net.res.map(r => r.name)") == ["Aino", "Eero"]
    assert host.evaluate("net.res.map(r => r.name)") == ["Aino", "Eero"]
    # The skating time is saved as a skating time on each phone.
    guest_t = guest.evaluate("net.res[0].fin")
    saved = guest.evaluate("JSON.parse(localStorage.getItem('ai-pelit:hiihto:luistelu-ajat'))")
    assert list(saved) == ["1"] and abs(saved["1"] - guest_t) < 0.01, saved
    assert guest.evaluate("localStorage.getItem('ai-pelit:hiihto:ajat')") is None
    for p in pages:
        p.evaluate("resultT = 2; down(1, W / 2, H / 2); up(1)")
        p.wait_for_function("AiPelitRooms.inRoom && !net && document.getElementById('aipr-result').textContent !== ''", timeout=6000)
    assert guest.inner_text("#aipr-result").startswith("1. sija")
    assert host.inner_text("#aipr-result").startswith("2. sija")
    assert "1. Aino" in host.inner_text("#aipr")
    # Back alone, each phone has its own style again.
    assert guest.evaluate("style") == "perinteinen"
    assert host.errors == guest.errors == []
    for p in pages:
        p.context.close()


def test_a_race_ends_a_while_after_the_first_finish(site, browser):
    host, guest = room_of_two(site, browser)
    wax_and_go([host, guest])
    host.evaluate("net.firstFin = null")
    guest.evaluate("P.z = course.len - 0.5; P.v = 8")
    host.wait_for_function("net.firstFin !== null", timeout=4000)
    # The host never gets there: a minute after the guest's finish the race is over.
    host.evaluate("net.clock = net.firstFin + 61")
    for p in (host, guest):
        p.wait_for_function("net && net.res", timeout=6000)
    assert guest.evaluate("[net.res[0].name, net.res[1].fin]") == ["Aino", None]
    assert host.evaluate("result.t") is None
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()


def test_the_computer_skis_for_a_friend_who_left(site, browser):
    relay = Relay()
    host, guest = room_of_two(site, browser, relay=relay)
    wax_and_go([host, guest])
    relay.drop(guest)
    # The race waits for the phone that went away, until the host goes on without it.
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    z = host.evaluate("P.z")
    host.evaluate(RUN, 2)
    assert host.evaluate("P.z") == z
    host.click("#aipr-goOn")
    host.wait_for_function("net.skiers[1].kind === 'cpu' && !AiPelitRooms.paused", timeout=4000)
    host.evaluate(RUN, 10)
    assert host.evaluate("net.skiers[1].z") > 20
    # Back again, the friend skis on from where the computer got to.
    relay.back(guest)
    guest.wait_for_function("!AiPelitRooms.paused && P.z > 20", timeout=8000)
    host.wait_for_function("net.skiers[1].kind === 'net'", timeout=4000)
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()


def test_a_finish_the_computer_skied_is_not_the_players_own(site, browser):
    relay = Relay()
    host, guest = room_of_two(site, browser, relay=relay)
    wax_and_go([host, guest])
    relay.drop(guest)
    host.wait_for_function("AiPelitRooms.paused", timeout=8000)
    host.click("#aipr-goOn")
    host.wait_for_function("net.skiers[1].kind === 'cpu' && !AiPelitRooms.paused", timeout=4000)
    # The computer takes Aino's skier over the line while her phone is away.
    host.evaluate("net.skiers[1].p.z = course.len - 0.5; net.skiers[1].p.v = 8")
    host.wait_for_function("net.skiers[1].fin !== null", timeout=4000)
    relay.back(guest)
    guest.wait_for_function("mode === 'done' && result && result.cpu", timeout=8000)
    # She keeps her place in the race, but it is not her time: nothing is saved or sent.
    assert guest.evaluate("[meK().fin !== null, result.stars, result.record]") == [True, 0, False]
    assert guest.evaluate("['luistelu-ajat', 'ajat', 'tahdet', 'taso'].map(k => localStorage.getItem('ai-pelit:hiihto:' + k))") == [None] * 4
    assert guest.evaluate("localStorage.getItem('ai-pelit:_tulokset:jono')") in (None, "{}")
    # The host finishes; both get the same places, Aino first.
    host.evaluate("P.z = course.len - 0.5; P.v = 8")
    for p in (host, guest):
        p.wait_for_function("net && net.res", timeout=6000)
    assert guest.evaluate("net.res.map(r => r.name)") == ["Aino", "Eero"]
    assert guest.evaluate("['ajat', 'taso'].map(k => localStorage.getItem('ai-pelit:hiihto:' + k))") == [None, None]
    assert host.errors == guest.errors == []
    for p in (host, guest):
        p.context.close()
