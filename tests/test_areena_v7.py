"""Areena: recorded sounds from the shared library (v5, #212), and from v7 (#369) 2-8 phones in
one room, everyone against everyone."""

import json
import shutil

from conftest import ROOT
from test_rooms_lib import Relay

URL = "games/areena/v7/"
SOUNDS = ["gongi", "suhahdus", "osuma", "potku", "tomahdys", "voitto", "tappio"]

# Every AiPelitAanet.play() call, with whether it played, in window.heard.
SPY = """() => {
  window.heard = [];
  const real = AiPelitAanet.play;
  AiPelitAanet.play = (name, o) => { const ok = real(name, o); heard.push([name, ok]); return ok; };
}"""
NOTHING = "{ mx: 0, my: 0, sword: false, bow: false, dash: false, lead: 0 }"


def open_game(site, context):
    # Only this game is built, so another game's unfinished folder cannot break the build.
    shutil.copytree(ROOT / "games" / "areena", site.games / "areena")
    site.build()
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(site.url + URL)
    page.evaluate(SPY)
    return page


def start_fight(page):
    page.click("#go")
    page.wait_for_function(f"{SOUNDS!r}.every(AiPelitAanet.ready)", timeout=10000)
    page.wait_for_function("AiPelitAanet.play('gongi', { vol: 0 })", timeout=5000)
    page.evaluate("heard.splice(0)")


def played(page):
    return [n for n, ok in page.evaluate("heard.splice(0)") if ok]


def test_a_fight_sounds_from_the_gong_to_the_win(site, context):
    page = open_game(site, context)
    start_fight(page)
    page.evaluate("stateT = 0.001; step(0.01)")
    assert played(page) == ["gongi"]
    page.evaluate(f"act(me, foe, {{ ...{NOTHING}, sword: true }}, 0.001)")
    page.evaluate(f"act(foe, me, {{ ...{NOTHING}, bow: true }}, 0.001)")
    page.evaluate(f"act(me, foe, {{ ...{NOTHING}, dash: true }}, 0.001)")
    assert played(page) == ["suhahdus", "suhahdus", "suhahdus"]
    # An arrow (8-10) is a light hit, a sword (16-20) a big one.
    page.evaluate("me.dash = 0; damage(me, 9, foe.x, foe.y, 0); damage(foe, 18, me.x, me.y, 0)")
    assert played(page) == ["osuma", "potku"]
    page.evaluate("foe.hp = 5; damage(foe, 18, me.x, me.y, 0)")
    assert played(page) == ["potku", "tomahdys"]
    page.evaluate("stateT = 0.001; step(0.01)")
    assert page.evaluate("state") == "over"
    assert played(page) == ["voitto"]
    assert page.evaluate("localStorage.getItem('ai-pelit:areena:taso')") == "2"
    assert page.errors == []


def test_a_lost_fight_plays_the_loss_tune(site, context):
    page = open_game(site, context)
    start_fight(page)
    page.evaluate("stateT = 0.001; step(0.01); heard.splice(0); me.hp = 1; damage(me, 18, foe.x, foe.y, 0); stateT = 0.001; step(0.01)")
    assert played(page)[-1] == "tappio"
    assert page.errors == []


def test_without_the_sound_files_it_still_plays_with_its_beeps(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/*.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        page.evaluate("stateT = 0.001; step(0.01); foe.hp = 1; damage(foe, 18, me.x, me.y, 0); stateT = 0.001; step(0.01)")
        assert page.evaluate("state") == "over"
        assert played(page) == []
        assert page.errors == []
    finally:
        ctx.close()


def test_v4_saves_are_read_as_they_are(site, context):
    page = open_game(site, context)
    page.evaluate("""() => {
      for (const [k, v] of [['taso', 4], ['voitot', 3], ['haviot', 2]]) localStorage.setItem('ai-pelit:areena:' + k, JSON.stringify(v));
      localStorage.setItem('ai-pelit:areena:nimi', JSON.stringify('Testi'));
    }""")
    page.goto(site.url + URL)
    assert page.inner_text("#stats") == "Voitot 3 · Häviöt 2"
    assert "(taso 4)" in page.inner_text("#foe")
    assert page.input_value("#name") == "Testi"
    assert page.errors == []


def test_the_next_fight_starts_with_the_gong_again(site, context):
    page = open_game(site, context)
    start_fight(page)
    page.evaluate("stateT = 0.001; step(0.01); foe.hp = 1; damage(foe, 18, me.x, me.y, 0); stateT = 0.001; step(0.01)")
    assert played(page)[-1] == "voitto"
    page.click("#go")
    page.evaluate("stateT = 0.001; step(0.01)")
    assert played(page) == ["gongi"]
    assert page.errors == []


def test_a_friends_phone_plays_the_same_sounds_from_the_hosts_state(site, context):
    """The friend's phone only sees the host's numbers; the sounds come from what changed in them."""
    page = open_game(site, context)
    start_fight(page)
    # Play the friend's side of a duel: a state message as the host sends it, then the next ones.
    page.evaluate("""() => {
      onlineFight({ host: false, round: 1, players: [{ id: 'h', name: 'Isäntä' }, { id: R.me, name: 'Minä' }] });
      window.msg = (st, a, b) => guestState({ t: 's', round: 1, st, T: 1, L: 90, f: [a, b], ar: [] });
      window.base = () => pack(foe);
      window.mine = () => pack(me);
      msg('count', base(), mine()); heard.splice(0);
    }""")
    page.evaluate("msg('fight', base(), mine())")
    assert played(page) == ["gongi"]
    # The host's own fighter (a) swings and the friend's (b) loses 9: a whoosh and a light hit.
    page.evaluate("const a = base(), b = mine(); a[5] = 0.3; b[2] = me.hp - 9; msg('fight', a, b)")
    assert played(page) == ["suhahdus", "osuma"]
    # Both at once in one message: a sword hit on the host's fighter and the knockout.
    page.evaluate("const a = base(); a[2] = 0; a[5] = 0; msg('ko', a, mine())")
    assert played(page) == ["potku", "tomahdys"]
    page.evaluate("net.done = false; R.backToRoom = () => {}; finishOnline({ w: R.me })")
    assert played(page) == ["voitto"]
    assert page.errors == []


def test_the_opponents_sword_on_the_player_is_a_big_hit(site, context):
    """Alone, the player takes 30 % less: a 16 from the sword becomes 11, still a sword hit."""
    page = open_game(site, context)
    start_fight(page)
    page.evaluate("stateT = 0.001; step(0.01); heard.splice(0); me.dash = 0; const hp = me.hp; damage(me, 16, foe.x, foe.y, 0); window.lost = hp - me.hp")
    assert page.evaluate("lost") == 11
    assert played(page) == ["potku"]
    assert page.errors == []


def test_a_knockout_without_its_thud_is_only_the_hit(site, browser):
    ctx = browser.new_context(viewport={"width": 360, "height": 740}, service_workers="block")
    try:
        ctx.route("**/tomahdys.mp3", lambda route: route.abort())
        page = open_game(site, ctx)
        page.click("#go")
        page.wait_for_function("AiPelitAanet.ready('potku')", timeout=10000)
        page.wait_for_function("AiPelitAanet.play('gongi', { vol: 0 })", timeout=5000)
        page.evaluate("stateT = 0.001; step(0.01); heard.splice(0); foe.hp = 1; damage(foe, 18, me.x, me.y, 0)")
        # #337: no crowd after the knockout.
        assert played(page) == ["potku"]
        assert page.errors == []
    finally:
        ctx.close()


# #337: the version on aanet-4, without crowd noise.
from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, "games/areena/v7")


# ---------- v7 (#369): 2-8 phones, everyone against everyone ----------

# This phone hosts a round of `n` players without a real room: what it would send is kept in
# window.sent, what it delivers in window.delivered, its result in window.result.
def host_round(page, n, me=0):
    page.evaluate(f"""() => {{
      window.sent = []; window.delivered = []; window.result = null;
      R.send = (m, to) => sent.push(m); R.deliver = m => delivered.push(m); R.endRound = () => {{}};
      R.backToRoom = (t, cls) => {{ result = [t, cls]; }};
      const players = Array.from({{ length: {n} }}, (_, i) => ({{ id: 'p' + i, name: 'Pelaaja ' + (i + 1) }}));
      players[{me}] = {{ id: R.me, name: 'Minä' }};
      onlineFight({{ host: true, round: 1, players }});
      stateT = 0.001; step(0.01);
    }}""")


def test_eight_phones_start_at_their_own_spots_with_their_own_colours(site, context):
    page = open_game(site, context)
    host_round(page, 8)
    spots = page.evaluate("fighters.map(f => [f.x, f.y])")
    assert len(spots) == 8 and len({tuple(s) for s in spots}) == 8
    assert page.evaluate("fighters.map(f => f.color)") == page.evaluate("COLORS.map(c => c[0])")
    assert page.evaluate("[state, foe, me.name, me.color]") == ["fight", None, "Minä", "#3d8bfd"]
    # No one starts inside a pillar or the wall.
    assert page.evaluate("fighters.every(f => { const x = f.x, y = f.y; hitWall(f); return f.x === x && f.y === y; })")
    assert page.errors == []


def test_each_phone_draws_its_own_fighter_blue_and_at_the_bottom(site, context):
    page = open_game(site, context)
    # The room's second player starts at the top: its phone turns the arena round.
    host_round(page, 4, me=1)
    assert page.evaluate("[me.color, fighters[0].color, flip()]") == ["#3d8bfd", "#e5484d", True]
    assert page.evaluate("W2(me.x, me.y)[1] > oy + AH * scale / 2")
    # Up on the stick is up on the screen: down in the arena.
    page.evaluate("pad.id = 1; pad.ox = 100; pad.oy = 600; pad.x = 100; pad.y = 550")
    assert page.evaluate("playerInput().my") == 1
    host_round(page, 4, me=2)
    page.evaluate("pad.id = 1; pad.ox = 100; pad.oy = 600; pad.x = 100; pad.y = 550")
    assert page.evaluate("[flip(), playerInput().my]") == [False, -1]
    assert page.errors == []


def test_a_sword_hits_everyone_in_reach_in_front_and_no_one_behind(site, context):
    page = open_game(site, context)
    host_round(page, 4)
    hp = page.evaluate("""() => {
      const [a, b, c, d] = fighters;
      a.x = 170; a.y = 200; b.x = 170; b.y = 170; c.x = 195; c.y = 180; d.x = 170; d.y = 235;
      for (const f of fighters) f.dash = 0;
      act(a, b, { ...IDLE, sword: true }, 0.001);
      for (let i = 0; i < 20; i++) act(a, b, IDLE, 0.01);
      return fighters.map(f => f.hp);
    }""")
    assert hp[0] == 100 and hp[1] < 100 and hp[2] < 100 and hp[3] == 100
    assert page.errors == []


def test_an_arrow_hits_whoever_is_in_its_way(site, context):
    page = open_game(site, context)
    host_round(page, 3)
    hp = page.evaluate("""() => {
      const [a, b, c] = fighters;
      a.x = 170; a.y = 380; b.x = 170; b.y = 60; c.x = 170; c.y = 300;
      arrows.push({ x: 170, y: 360, vx: 0, vy: -ARROW_V, from: a, life: 2 });
      for (let i = 0; i < 10; i++) step(0.02);
      return fighters.map(f => f.hp);
    }""")
    assert hp[2] < 100 and hp[1] == 100
    assert page.errors == []


def test_the_last_one_standing_wins_and_every_phone_hears_its_place(site, context):
    page = open_game(site, context)
    host_round(page, 4)
    page.evaluate("fighters[2].hp = 1; damage(fighters[2], 18, 0, 0, 0)")
    page.evaluate("fighters[1].hp = 1; damage(fighters[1], 18, 0, 0, 0)")
    # Two of four out: the round goes on, and the fallen take no part.
    assert page.evaluate("[state, fighters.filter(f => f.out).length]") == ["fight", 2]
    assert page.evaluate("nearest(me) === fighters[3]")
    page.evaluate("fighters[3].hp = 1; damage(fighters[3], 18, 0, 0, 0)")
    assert page.evaluate("state") == "ko"
    page.evaluate("stateT = 0.001; step(0.01)")
    end = page.evaluate("delivered[0]")
    assert end["w"] == page.evaluate("R.me")
    assert end["o"] == [page.evaluate("R.me"), "p3", "p1", "p2"]
    assert page.evaluate("result") == ["🏆 Minä voitti!", "win"]
    # A guest that fell second-to-last hears it was 2nd.
    page.evaluate("net.done = false; finishOnline({ ...delivered[0], w: 'p3', o: ['p3', R.me, 'p1', 'p2'] })")
    assert page.evaluate("result") == ["💀 Pelaaja 4 voitti · olit 2.", "lose"]
    assert page.errors == []


def test_when_time_runs_out_the_most_health_wins(site, context):
    page = open_game(site, context)
    host_round(page, 3)
    page.evaluate("me.hp = 40; fighters[1].hp = 70; fighters[2].hp = 55; net.left = 0.005; step(0.01)")
    assert page.evaluate("[state, net.timeUp]") == ["ko", True]
    page.evaluate("stateT = 0.001; step(0.01)")
    assert page.evaluate("delivered[0].o") == ["p1", "p2", page.evaluate("R.me")]
    assert page.evaluate("result") == ["💀 Pelaaja 2 voitti · olit 3.", "lose"]
    assert page.errors == []


def test_the_computer_fights_for_a_phone_that_is_away(site, context):
    page = open_game(site, context)
    host_round(page, 3)
    page.evaluate("byId('p2').bot = true")
    page.evaluate("for (let i = 0; i < 120; i++) step(1 / 60)")
    # Its own head moved it; the other phone's fighter, with no input, stands still.
    assert page.evaluate("[fighters[2].x !== 300 || fighters[2].y !== 380, fighters[1].x === 170 && fighters[1].y === 60]") == [True, True]
    assert page.errors == []


def test_a_guest_draws_every_fighter_from_the_hosts_state(site, context):
    page = open_game(site, context)
    host_round(page, 5)
    # The host's message for five, read by a guest (the room's fourth player).
    msg = page.evaluate("""() => {
      fighters[2].hp = 0; fighters[2].out = true; arrows.push({ x: 100, y: 100, vx: 0, vy: 300, from: fighters[4], life: 2 });
      sendState(); return sent[sent.length - 1];
    }""")
    page.evaluate("""m => {
      onlineFight({ host: false, round: 1, players: [0, 1, 2, 3, 4].map(i => ({ id: i === 3 ? R.me : 'p' + i, name: 'P' + i })) });
      heard.splice(0); guestState(m);
    }""", msg)
    assert page.evaluate("[fighters.length, fighters[2].out, me === fighters[3], arrows[0].from === fighters[4]]") == [5, True, True, True]
    # The first state a phone hears is how things are, not what just happened: no sounds.
    assert played(page) == []
    page.evaluate("draw()")
    assert page.errors == []


def test_three_phones_fight_in_one_room_and_all_hear_the_result(site, browser):
    """A real room of three phones through the test relay: each phone is its own fighter."""
    shutil.copytree(ROOT / "games" / "areena", site.games / "areena")
    site.build()
    relay, contexts = Relay(), []

    def phone(name):
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', {json.dumps(json.dumps(name))})")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(site.url + URL)
        return page

    try:
        host = phone("Eero")
        host.click("#multi")
        host.click("#aipr-create")
        host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.members.length === 1")
        code = host.evaluate("AiPelitRooms.code")
        guests = []
        for n in ["Aino", "Ville"]:
            g = phone(n)
            g.click("#multi")
            g.fill("#aipr-codeIn", code)
            g.click("#aipr-joinBtn")
            g.wait_for_function("AiPelitRooms.inRoom")
            guests.append(g)
        host.wait_for_function("AiPelitRooms.members.filter(m => m.on).length === 3")
        host.click("#aipr-start")
        everyone = [host, *guests]
        for p in everyone:
            p.wait_for_function("state === 'fight' && fighters.length === 3", timeout=10000)
        assert sorted(p.evaluate("me.name") for p in everyone) == ["Aino", "Eero", "Ville"]
        # A guest's stick moves its own fighter on the host.
        aino = guests[0]
        before = host.evaluate("byId(%s).x" % json.dumps(aino.evaluate("R.me")))
        aino.evaluate("pad.id = 1; pad.ox = 100; pad.oy = 600; pad.x = 150; pad.y = 600")
        host.wait_for_function("Math.abs(byId(%s).x - %s) > 20" % (json.dumps(aino.evaluate("R.me")), before))
        # The host knocks out both guests: every phone hears who won.
        host.evaluate("for (const f of fighters) if (f !== me) { f.dash = 0; f.hp = 1; damage(f, 18, 0, 0, 0); }")
        for p in everyone:
            p.wait_for_function("state === 'room'", timeout=10000)
        assert host.locator("#aipr-result").inner_text() == "🏆 Eero voitti!"
        for g in guests:
            assert g.locator("#aipr-result").inner_text().startswith("💀 Eero voitti · olit ")
        for p in everyone:
            assert p.errors == []
    finally:
        for ctx in contexts:
            ctx.close()
