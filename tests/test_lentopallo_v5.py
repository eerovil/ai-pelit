"""Lentopallo v5: recorded sounds from the shared library public/lib/aanet-2/ (#222)."""

import json
import shutil

import pytest

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/lentopallo/v5/"
SOUNDS = ["pilli", "naksu", "lyonti", "verkko", "suhahdus", "hiekka", "aplodit", "voitto", "tappio"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""


@pytest.fixture
def game(site, context):
    shutil.copytree(ROOT / "games" / "lentopallo", site.games / "lentopallo")
    site.build()

    def start(ctx=context):
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site.url + URL)
        page.evaluate(SPY)
        page.click("#go")
        return page

    return start


def ready(page):
    page.wait_for_function(f"{SOUNDS}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('naksu', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


# The spy from the page's very start, so a page that reloads in a room records its first sounds too.
EARLY_SPY = """
window.heard = [];
Object.defineProperty(window, 'AiPelitAanet', { configurable: true, get() { return this._aanet; }, set(v) {
  const real = v.play;
  v.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
  this._aanet = v;
} });
"""


def test_a_rally_sounds_from_the_serve_to_the_applause(game):
    page = game()
    ready(page)
    page.evaluate("server = mine; ball.held = true; tossed = false; state = 'serve'; press(mine)")
    assert played(page) == ["naksu"]
    # A dig, then a spike: the same slap, the spike harder.
    page.evaluate("""() => {
      ball.served = true; touchSide = 0; touches = 0; mine.y = 0; mine.intent = 'set';
      Object.assign(ball, { x: mine.x, y: 1.2 }); hit(mine);
    }""")
    assert played(page) == ["lyonti"]
    page.evaluate("""() => {
      mine.cd = 0; mine.y = 0; mine.vy = 0; jump(mine);
      mine.y = 0.6; Object.assign(ball, { x: mine.x, y: mine.y + 2.5 }); hit(mine);
    }""")
    assert played(page) == ["suhahdus", "lyonti"]
    # Into the net, then down in the sand: the whistle, then the crowd claps.
    page.evaluate("""() => {
      Object.assign(ball, { x: -0.3, y: 1.5, vx: 6, vy: 0, held: false }); stepBall(0.1, true);
    }""")
    assert played(page) == ["verkko"]
    page.evaluate("""() => {
      state = 'play'; last = mine; touchSide = 1; touches = 0;
      Object.assign(ball, { x: 3, y: 0.2, vx: 0, vy: -3 }); stepBall(0.1, true);
    }""")
    assert played(page) == ["hiekka", "pilli", "aplodit"]
    assert page.evaluate("state") == "point"
    page.evaluate("score = [11, 4]; endMatch(true)")
    assert played(page) == ["voitto"]
    page.evaluate("score = [4, 11]; endMatch(false)")
    assert played(page) == ["tappio"]
    assert page.errors == []


def test_a_fault_with_the_ball_up_has_no_sand(game):
    page = game()
    ready(page)
    page.evaluate("""() => {
      tossed = true; ball.held = false; ball.served = true; state = 'play';
      touchSide = -1; touches = 3; last = mine; ball.y = 2; hit(mine);
    }""")
    assert played(page) == ["pilli", "aplodit"]
    assert page.evaluate("msg.s") == "Neljä kosketusta!"
    # Low over the sand is still in the air: the ball never touched it.
    page.evaluate("""() => {
      state = 'play'; touchSide = -1; touches = 3; last = mine; ball.y = 0.3; hit(mine);
    }""")
    assert played(page) == ["pilli", "aplodit"]


def test_without_the_sound_files_it_still_plays_with_its_beeps(game, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = game(ctx)
        page.evaluate("""() => {
          server = mine; ball.held = true; tossed = false; state = 'serve'; press(mine);
          for (let i = 0; i < 60 * 20; i++) update(1 / 60);
          score = [11, 4]; endMatch(true);
        }""")
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v4_saves_are_read_as_they_are(game):
    page = game()
    page.evaluate("""() => {
      localStorage.setItem('ai-pelit:lentopallo:taso', '3');
      localStorage.setItem('ai-pelit:lentopallo:voitot', '2');
      localStorage.setItem('ai-pelit:lentopallo:haviot', '5');
    }""")
    page.reload()
    assert "Taso 3" in page.inner_text("#foe")
    assert page.inner_text("#stats").startswith("Voitot 2 · Häviöt 5")
    assert page.errors == []



def test_a_guest_hears_the_hosts_sounds_from_the_snapshots(game):
    page = game()
    ready(page)
    # A guest plays what the host's counters say happened since the last snapshot, never the past.
    page.evaluate("""() => {
      window.snap = (st, fx) => { const s = snapshot(); s.st = st; s.fx = fx; applySnapshot(s); };
      state = 'play'; snap('play', [5, 3, 7]);
    }""")
    assert played(page) == []
    page.evaluate("snap('play', [6, 3, 7])")
    assert played(page) == ["naksu"]
    page.evaluate("snap('play', [6, 4, 7])")
    assert played(page) == ["verkko"]
    # Two at once: into the net, then down in the sand, in one snapshot.
    page.evaluate("snap('point', [6, 5, 8])")
    assert played(page) == ["verkko", "hiekka", "pilli", "aplodit"]
    # A point with no new ball in the sand (a fourth touch) has no sand, however low the ball.
    page.evaluate("state = 'play'; snap('play', [6, 5, 8]); ball.y = 0.1")
    page.evaluate("const s = snapshot(); s.st = 'point'; s.b[1] = 0.1; s.fx = [6, 5, 8]; applySnapshot(s)")
    assert played(page) == ["pilli", "aplodit"]
    assert page.errors == []


@pytest.fixture
def room(game, site, browser):
    relay, contexts = Relay(), []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        ctx.add_init_script(EARLY_SPY)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
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
            p.wait_for_function("mine && players.length && (state === 'serve' || state === 'play')")
        return host, guests

    play.relay = relay
    yield play
    for ctx in contexts:
        ctx.close()


def heard_on(page, name):
    page.wait_for_function(f"heard.some(h => h[0] === '{name}' && h[1])", timeout=5000)


def test_in_a_room_the_guest_hears_the_toss_the_net_and_the_sand(room):
    host, [guest] = room("Eero", "Aino")
    for p in (host, guest):
        ready(p)
    host.evaluate("server = mine; ball.held = true; tossed = false; state = 'serve'; press(mine)")
    heard_on(guest, "naksu")
    host.evaluate("state = 'play'; last = mine; touchSide = -1; Object.assign(ball, { x: -0.3, y: 1.5, vx: 6, vy: 0, held: false })")
    heard_on(guest, "verkko")
    host.evaluate("state = 'play'; last = mine; touchSide = 1; touches = 0; Object.assign(ball, { x: 3, y: 0.2, vx: 0, vy: -3, held: false })")
    for name in ("hiekka", "pilli"):
        heard_on(guest, name)
    assert host.errors == guest.errors == []


def test_a_guest_that_reloads_hears_the_match_end_once(room):
    host, [guest, third] = room("Eero", "Aino", "Iida")
    room.relay.drop(guest)
    host.wait_for_function("AiPelitRooms.waiting.length === 1")
    host.click("#aipr-goOn")
    host.wait_for_function("players[1].kind === 'cpu'")
    host.evaluate("score = [4, 11]; state = 'point'; pauseT = 0")
    third.wait_for_function("state === 'done'")
    # Back after a reload, the end comes again: the tune is asked for once (before a tap it may stay silent).
    room.relay.back(guest)
    guest.reload()
    guest.wait_for_function("document.querySelector('#aipr-result') && document.querySelector('#aipr-result').innerText.length > 0", timeout=8000)
    assert guest.evaluate("heard.filter(h => h[0] === 'voitto' || h[0] === 'tappio').map(h => h[0])") == ["voitto"]
    # Another reload, and the room sends the same end again: no tune this time.
    guest.reload()
    guest.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.connected", timeout=8000)
    guest.wait_for_timeout(500)
    assert guest.evaluate("heard.filter(h => h[0] === 'voitto' || h[0] === 'tappio').length") == 0
    assert host.errors == guest.errors == third.errors == []
