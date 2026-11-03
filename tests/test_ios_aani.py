"""iPhone silent switch (#381): Safari mutes a page's Web Audio while the ringer switch is on silent,
unless the page says it plays media (navigator.audioSession.type = 'playback', Safari 17 / iOS 17).
public/back.js says so for every game; rooms.js asks for 'play-and-record' while its microphone is on.

Chromium has no navigator.audioSession, so these tests give the page a stand-in, as Safari has it.
Whether an iPhone then really sounds can only be heard on one."""

from conftest import game_page, make_game
from test_rooms_lib import make_room, join  # noqa: F401
from test_rooms_voice import browser, phones, hold  # noqa: F401

SESSION = "Object.defineProperty(navigator, 'audioSession', { value: { type: 'auto' }, configurable: true });"


def test_every_game_tells_safari_it_plays_media(site, context):
    make_game(site.games, "pomppu", [game_page("v1", script="window.ready = true;")])
    site.build()
    context.add_init_script(SESSION)
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    assert page.evaluate("navigator.audioSession.type") == "playback"
    # Something else reset it (a game, Safari after a call): the next tap sets it again.
    page.evaluate("navigator.audioSession.type = 'auto'")
    page.mouse.click(180, 500)
    assert page.evaluate("navigator.audioSession.type") == "playback"


def test_a_type_chosen_by_something_else_is_kept(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    context.add_init_script(SESSION)
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.evaluate("navigator.audioSession.type = 'play-and-record'")
    page.mouse.click(180, 500)
    assert page.evaluate("navigator.audioSession.type") == "play-and-record"


def test_a_browser_without_audio_session_plays_on(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.mouse.click(180, 500)
    assert page.evaluate("'audioSession' in navigator") is False
    assert errors == []


def test_ottelus_event_frames_play_media_too(site, context):
    # Ottelu loads each event into a frame of its own, without back.js; a tap in the frame stays there.
    event = "<body style=\"margin:0;height:100%\"><script>window.ready = true;<\\/script></body>"
    frame = (f"<script>const f = document.createElement('iframe'); f.srcdoc = '{event}';"
             "f.style.cssText = 'position:fixed;left:0;top:300px;width:360px;height:300px;border:0';"
             "document.body.appendChild(f);</script>")
    make_game(site.games, "ottelu", [game_page("v1", body=frame)])
    site.build()
    context.add_init_script(SESSION)
    page = context.new_page()
    page.goto(f"{site.url}games/ottelu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    inner = page.frames[1]
    inner.wait_for_function("window.ready && navigator.audioSession.type === 'playback'")
    inner.evaluate("navigator.audioSession.type = 'auto'")
    page.mouse.click(180, 450)
    assert inner.evaluate("navigator.audioSession.type") == "playback"


def test_talking_in_a_room_asks_for_play_and_record(phones):  # noqa: F811
    def phone(name, path="huonetesti/v2/"):
        return phones(name, path, init=SESSION)

    host, code = make_room(phone)
    a = join(phone, "Aino", code)
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=15000)
        assert p.evaluate("navigator.audioSession.type") == "playback"
    a.locator("#aipr-mic").click()
    hold(a)
    a.wait_for_function("AiPelitRooms.voice.talking")
    assert a.evaluate("navigator.audioSession.type") == "play-and-record"
    a.mouse.up()
    a.wait_for_function("!AiPelitRooms.voice.talking")
    # Game sound plays on: play-and-record ignores the silent switch as well, and a tap keeps it.
    a.mouse.click(180, 600)
    assert a.evaluate("navigator.audioSession.type") == "play-and-record"


def test_a_reload_and_each_next_event_frame_set_it_again(site, context):
    # Ottelu removes each event's frame and makes a new one; a player may reload mid-match.
    script = """window.nextEvent = () => new Promise(done => {
      document.querySelectorAll('iframe').forEach(f => f.remove());
      const f = document.createElement('iframe');
      f.srcdoc = '<body>laji</body>';
      f.onload = () => setTimeout(() => done(f.contentWindow.navigator.audioSession.type), 0);
      document.body.appendChild(f);
    });"""
    make_game(site.games, "ottelu", [game_page("v1", script=script)])
    site.build()
    context.add_init_script(SESSION)
    page = context.new_page()
    for _ in range(2):
        page.goto(f"{site.url}games/ottelu/v1/")
        page.wait_for_selector("#ai-pelit-back")
        assert page.evaluate("navigator.audioSession.type") == "playback"
        assert [page.evaluate("nextEvent()") for _ in range(3)] == ["playback"] * 3
        page.reload()


# Like Piano v10: the context is made on the start button and resumed only while 'suspended'.
PIANO_LIKE = """
let ac = null;
document.addEventListener('click', () => { if (!ac) ac = new AudioContext(); });
window.note = () => { const o = ac.createOscillator(), g = ac.createGain(); o.connect(g); g.connect(ac.destination);
  o.start(); o.stop(ac.currentTime + 0.05); };
"""


def test_a_tap_or_coming_back_resumes_a_game_sound_the_phone_stopped(site, context):
    # An iPhone stops a page's sound on a lock, a call or another app; Piano never resumed it (#381).
    make_game(site.games, "soitin", [game_page("v1", script=PIANO_LIKE)])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/soitin/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.mouse.click(180, 500)
    page.evaluate("note()")
    page.wait_for_function("ac.state === 'running'")
    page.evaluate("ac.suspend()")
    page.wait_for_function("ac.state === 'suspended'")
    page.mouse.click(180, 500)
    page.wait_for_function("ac.state === 'running'", timeout=3000)
    # Coming back on screen resumes it too, with no tap.
    page.evaluate("ac.suspend()")
    page.wait_for_function("ac.state === 'suspended'")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function("ac.state === 'running'", timeout=3000)


def test_a_hidden_page_stays_asleep_and_a_frames_stopped_sound_wakes_on_a_tap_in_it(site, context):
    # The sound library puts its context to sleep while the page is hidden: back.js leaves it so.
    event = ("<body style=\"margin:0;height:100%\"><script>window.ac = new AudioContext(); window.ready = true;<\\/script></body>")
    frame = (f"<script>const f = document.createElement('iframe'); f.srcdoc = '{event}';"
             "f.style.cssText = 'position:fixed;left:0;top:300px;width:360px;height:300px;border:0';"
             "document.body.appendChild(f);</script>")
    make_game(site.games, "ottelu", [game_page("v1", body=frame, script=PIANO_LIKE)])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/ottelu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.mouse.click(180, 100)
    page.evaluate("note()")
    page.wait_for_function("ac.state === 'running'")
    page.evaluate("ac.suspend()")
    page.wait_for_function("ac.state === 'suspended'")
    page.evaluate("Object.defineProperty(document, 'hidden', { value: true, configurable: true })")
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_timeout(300)
    assert page.evaluate("ac.state") == "suspended"
    page.evaluate("delete document.hidden")
    # Two contexts stopped at once, the page's and the frame's: a tap in the frame wakes the frame's.
    inner = page.frames[1]
    inner.wait_for_function("window.ready && AudioNode.prototype.__aiPelitAani")
    inner.evaluate("ac.createGain().connect(ac.destination)")
    inner.evaluate("ac.suspend()")
    inner.wait_for_function("ac.state === 'suspended'")
    page.mouse.click(180, 450)
    inner.wait_for_function("ac.state === 'running'", timeout=3000)
    page.mouse.click(180, 100)
    page.wait_for_function("ac.state === 'running'", timeout=3000)
