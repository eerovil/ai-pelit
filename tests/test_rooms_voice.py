"""Voice in rooms (#322): push to talk in public/rooms.js, on the test-only game of test_rooms_lib.py.

Each phone is its own Chromium context with Chromium's fake microphone (a beeping tone), and the
phones' calls go straight between them over this machine, as on two phones on one network. A
phone's calls are counted by wrapping RTCPeerConnection, so a test can read how much sound arrived.
"""

import pytest

from conftest import make_game
from test_rooms_lib import Relay, demo_page, join, make_room, start  # noqa: F401

FAKE_MIC = ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]

COUNT_CALLS = """
(() => {
  const Real = window.RTCPeerConnection;
  window.__pcs = [];
  window.RTCPeerConnection = function (cfg) { const pc = new Real(cfg); window.__pcs.push(pc); return pc; };
  window.RTCPeerConnection.prototype = Real.prototype;
  // Bytes of sound that came in, over every call this page has had.
  window.__heard = async () => {
    let n = 0;
    for (const pc of window.__pcs) {
      if (pc.connectionState === 'closed') continue;
      (await pc.getStats()).forEach((r) => { if (r.type === 'inbound-rtp' && r.kind === 'audio') n += r.bytesReceived || 0; });
    }
    return n;
  };
})();
"""


@pytest.fixture(scope="module")
def browser(_playwright):
    b = _playwright.chromium.launch(args=FAKE_MIC)
    yield b
    b.close()


@pytest.fixture
def phones(site, browser):
    make_game(site.games, "huonetesti", [demo_page(), demo_page()])
    quiet = demo_page().replace('data-max="5"', 'data-max="5" data-voice="off"')
    make_game(site.games, "hiljainen", [quiet.replace("__GAME__", "hiljainen")])
    site.build()
    relay = Relay()
    contexts = []

    def phone(name, path="huonetesti/v2/", no_mic=False, width=360, height=740, init=None):
        ctx = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True)
        contexts.append(ctx)
        ctx.grant_permissions(["microphone"])
        ctx.add_init_script(f"localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify({name!r}))")
        ctx.add_init_script(COUNT_CALLS)
        if init:
            ctx.add_init_script(init)
        if no_mic:
            ctx.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('no', 'NotAllowedError'))")
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        relay.attach(page)
        page.goto(f"{site.url}games/{path}")
        return page

    phone.relay = relay
    yield phone
    for ctx in contexts:
        ctx.close()


def room_of_three(phones):
    host, code = make_room(phones)
    a = join(phones, "Aino", code)
    b = join(phones, "Iida", code)
    for p in (host, a, b):
        p.wait_for_function("AiPelitRooms.voice.calls === 2", timeout=15000)
    return host, a, b


def hold(page):
    box = page.locator("#aipr-mic").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()


def heard(page):
    return page.evaluate("window.__heard()")


def test_a_held_chip_is_heard_by_everyone_in_the_room_guest_to_guest_too(phones):
    host, a, b = room_of_three(phones)
    for p in (host, a, b):
        assert p.locator("#aipr-mic").is_visible()
        assert p.locator("#aipr-voice").is_checked()
    before = {p: heard(p) for p in (host, b)}
    # A quick tap says how the chip works; the next press takes the hint away.
    a.locator("#aipr-mic").click()
    a.wait_for_function("document.getElementById('aipr-talk').textContent === 'Pidä pohjassa ja puhu.'")
    hold(a)
    a.wait_for_function("AiPelitRooms.voice.talking")
    assert a.locator("#aipr-mic").get_attribute("class") == "live mid"
    assert a.evaluate("document.getElementById('aipr-talk').hidden")  # no "hold to talk" hint while holding
    for p in (host, b):
        p.wait_for_function("document.getElementById('aipr-talk').textContent === '🔊 Aino'")
        p.wait_for_function(f"window.__heard().then(n => n > {before[p]} + 2000)", polling=200)
    a.mouse.up()
    a.wait_for_function("!AiPelitRooms.voice.talking")
    for p in (host, b):
        p.wait_for_function("document.getElementById('aipr-talk').hidden")
    # The microphone is let go: nothing more comes in.
    host.wait_for_timeout(600)
    stopped = heard(host)
    host.wait_for_timeout(1200)
    assert heard(host) - stopped < 600
    for p in (host, a, b):
        assert p.errors == []


def test_the_chip_shows_over_the_round_and_the_round_plays_on(phones):
    host, a, b = room_of_three(phones)
    start(host, [a, b])
    assert host.locator("#aipr-mic").is_visible()
    hold(b)
    host.wait_for_function("AiPelitRooms.voice.speakers.join() === 'Iida'")
    b.mouse.up()
    host.wait_for_function("demo.clock > 3")


def test_a_muted_player_and_a_phone_with_voice_off_hear_nothing(phones):
    host, a, b = room_of_three(phones)
    # Iida mutes Aino on her phone.
    b.locator("#aipr-members li", has_text="Aino").locator("button.mute").click()
    assert b.locator("#aipr-members li", has_text="Aino").locator("button.mute").inner_text() == "🔇"
    hold(a)
    host.wait_for_function("AiPelitRooms.voice.speakers.join() === 'Aino'")
    b.wait_for_timeout(500)
    assert b.evaluate("AiPelitRooms.voice.speakers") == []
    # Aino's sound plays muted on Iida's phone; Eero's does not.
    assert b.evaluate("[...document.querySelectorAll('audio')].map(x => x.muted).sort().join()") == "false,true"
    a.mouse.up()
    # Eero switches voice off: no chip, no calls, and the others call him no more.
    host.locator("#aipr-voice").uncheck()
    host.wait_for_function("AiPelitRooms.voice.calls === 0 && !AiPelitRooms.voice.on")
    assert not host.locator("#aipr-mic").is_visible()
    for p in (a, b):
        p.wait_for_function("AiPelitRooms.voice.calls === 1")
    host.reload()
    host.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 3")
    assert host.evaluate("AiPelitRooms.voice.on") is False  # kept on this phone
    host.locator("#aipr-voice").check()
    for p in (host, a, b):
        p.wait_for_function("AiPelitRooms.voice.calls === 2", timeout=15000)


def test_a_reloaded_phone_is_called_again(phones):
    host, a, b = room_of_three(phones)
    a.reload()
    a.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.members.length === 3")
    for p in (host, a, b):
        p.wait_for_function("AiPelitRooms.voice.calls === 2", timeout=15000)
    before = heard(a)
    hold(b)
    a.wait_for_function(f"window.__heard().then(n => n > {before} + 2000)", polling=200)
    b.mouse.up()


def test_without_a_microphone_the_chip_says_so_and_the_game_plays(phones):
    host, code = make_room(phones)
    page = phones("Aino", no_mic=True)
    page.click("#multi")
    page.fill("#aipr-codeIn", code)
    page.click("#aipr-joinBtn")
    page.wait_for_function("AiPelitRooms.inRoom && AiPelitRooms.voice.calls === 1", timeout=15000)
    hold(page)
    page.wait_for_function("document.getElementById('aipr-talk').textContent === 'Mikrofoni ei ole sallittu.'")
    page.mouse.up()
    assert page.evaluate("AiPelitRooms.voice.talking") is False
    start(host, [page])
    assert page.errors == []


def test_a_version_may_leave_voice_out(phones):
    host, code = make_room(phones, "hiljainen/v1/")
    a = join(phones, "Aino", code, "hiljainen/v1/")
    a.wait_for_timeout(800)
    for p in (host, a):
        assert p.evaluate("AiPelitRooms.voice") == {"on": False, "talking": False, "speakers": [], "calls": 0}
        assert p.locator("#aipr-mic").count() == 0
        assert not p.locator("#aipr-voiceRow").is_visible()


def test_two_phones_talk_on_a_room_from_before_voice(phones):
    # Until the new room is deployed, the room passes the host's `_rtc` on without `from`, and a
    # guest's only to the host: two phones still talk.
    phones.relay.old = True
    host, code = make_room(phones)
    a = join(phones, "Aino", code)
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=15000)
    before = heard(a)
    hold(host)
    a.wait_for_function("AiPelitRooms.voice.speakers.join() === 'Eero'")
    a.wait_for_function(f"window.__heard().then(n => n > {before} + 2000)", polling=200)
    host.mouse.up()


def test_lost_greetings_heal_by_themselves(phones):
    # Both phones' first greetings are lost (as in a reconnect): neither knows the other takes
    # calls until one greets again, which it does while no call is up.
    host, code = make_room(phones)
    phones.relay.lose_hi = 2
    a = join(phones, "Aino", code)
    a.wait_for_timeout(2000)
    assert host.evaluate("AiPelitRooms.voice.calls") == 0
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=20000)


def test_two_talking_at_once_are_both_heard(phones):
    host, a, b = room_of_three(phones)
    hold(a)
    hold(b)
    host.wait_for_function("AiPelitRooms.voice.speakers.slice().sort().join() === 'Aino,Iida'")
    assert host.locator("#aipr-talk").inner_text() in ("🔊 Aino, Iida", "🔊 Iida, Aino")
    a.mouse.up()
    host.wait_for_function("AiPelitRooms.voice.speakers.join() === 'Iida'")
    b.mouse.up()
    host.wait_for_function("document.getElementById('aipr-talk').hidden")


@pytest.mark.parametrize("width,height", [(390, 844), (360, 640)])
def test_the_chip_and_label_fit_a_phone(phones, width, height):
    host = phones("Eero", width=width, height=height)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.code")
    code = host.evaluate("AiPelitRooms.code")
    a = join(phones, "Aino", code)
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=15000)
    hold(a)
    host.wait_for_function("AiPelitRooms.voice.speakers.join() === 'Aino'")
    for part in ("#aipr-mic", "#aipr-talk"):
        box = host.locator(part).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= width, part
        assert box["y"] >= 0 and box["y"] + box["height"] <= height, part
    # The room screen still fits without scrolling, with the voice switch.
    assert host.evaluate("document.getElementById('aipr').scrollHeight") <= height
    assert host.locator("#aipr-voice").is_visible()
    a.mouse.up()


def test_a_chip_with_no_one_to_hear_never_opens_the_microphone(phones):
    page = phones("Eero")
    page.evaluate("""(() => { window.__mic = 0; const gum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = (c) => { window.__mic++; return gum(c); }; })()""")
    page.click("#multi")
    page.click("#aipr-create")
    page.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.code")
    assert page.locator("#aipr-mic").get_attribute("class") == "none mid"
    hold(page)
    page.wait_for_function("document.getElementById('aipr-talk').textContent === 'Kukaan ei kuule vielä.'")
    page.wait_for_timeout(300)
    page.mouse.up()
    assert page.evaluate("[window.__mic, AiPelitRooms.voice.talking]") == [0, False]
    # A friend joins: now it opens.
    a = join(phones, "Aino", page.evaluate("AiPelitRooms.code"))
    page.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=15000)
    hold(page)
    page.wait_for_function("AiPelitRooms.voice.talking")
    assert page.evaluate("window.__mic") == 1
    page.mouse.up()
    assert a.errors == []


SLOW_ICE = """(() => { const f = window.fetch; window.fetch = (u, o) => String(u).includes('/api/voice/ice')
  ? new Promise((ok) => setTimeout(ok, 1500)).then(() => f(u, o)) : f(u, o); })()"""

HOST_CANDIDATES = """(async () => { let n = 0; for (const pc of window.__pcs) { if (pc.connectionState !== 'connected') continue;
  (await pc.getStats()).forEach((r) => { if (r.type === 'remote-candidate' && r.candidateType === 'host') n++; }); } return n; })()"""


def test_candidates_that_arrive_while_the_servers_are_read_are_kept(phones):
    # The servers' list comes slowly, so the answering phone hears the offer's candidates before
    # it has made its call: they wait, and are added once the offer is in.
    host = phones("Eero", init=SLOW_ICE)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.code")
    a = phones("Aino", f"huonetesti/v2/?huone={host.evaluate('AiPelitRooms.code')}", init=SLOW_ICE)
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=20000)
    # Both phones know the other's own (host) candidates, not only addresses learnt from checks.
    for p in (host, a):
        assert p.evaluate(HOST_CANDIDATES) >= 1


# The phone holds the sound back until a tap on the page, as Chrome does on a phone with no tap yet.
HOLD_SOUND = """
HTMLMediaElement.prototype.play = function () { return Promise.reject(new DOMException('no', 'NotAllowedError')); };
Object.defineProperty(HTMLMediaElement.prototype, 'paused', { get() { return true; } });
"""


@pytest.mark.parametrize("width,height", [(360, 740), (320, 640), (740, 360), (640, 360)])
def test_the_tap_to_hear_hint_shows_whole_on_a_narrow_phone(phones, width, height):
    # #333: "🔊 Aino – napauta ruutua" was cut to "napauta ru…" at 360 px wide.
    host = phones("Eero", width=width, height=height, init=HOLD_SOUND)
    host.click("#multi")
    host.click("#aipr-create")
    host.wait_for_function("AiPelitRooms.isHost && AiPelitRooms.code")
    a = join(phones, "Aino", host.evaluate("AiPelitRooms.code"))
    for p in (host, a):
        p.wait_for_function("AiPelitRooms.voice.calls === 1", timeout=15000)
    hold(a)
    host.wait_for_function("document.getElementById('aipr-talk').textContent === '🔊 Aino\\nNapauta ruutua'")
    talk = host.locator("#aipr-talk")
    assert talk.inner_text() == "🔊 Aino\nNapauta ruutua"
    assert host.evaluate("(e => e.scrollWidth <= e.clientWidth && e.scrollHeight <= e.clientHeight)(document.getElementById('aipr-talk'))")
    box, mic = talk.bounding_box(), host.locator("#aipr-mic").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= height
    # It does not cover the 🎤 chip.
    assert box["x"] + box["width"] <= mic["x"] or box["y"] >= mic["y"] + mic["height"]
    host.screenshot(path=f"/var/tmp/issue333-{width}x{height}.png")
    a.mouse.up()
