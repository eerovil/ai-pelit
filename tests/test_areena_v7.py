"""Areena v5: recorded sounds from the shared library public/lib/aanet-2/ (#212)."""

import shutil

from conftest import ROOT

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
    # Play the friend's side: a state message as the host sends it, then the next ones.
    page.evaluate("""() => {
      net = { host: false, fresh: true, round: 1 };
      window.msg = (st, a, b) => guestState({ t: 's', round: 1, st, T: 1, a, b, ar: [] });
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
    page.evaluate("net.done = false; finishOnline({ w: R.me })")
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
