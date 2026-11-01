"""Game volume (#336): one volume for every game, set from the 🔊 chip beside "‹ Pelit"
(public/back.js). It sits between each game's Web Audio and the speaker, so it reaches published
versions unchanged; the friends' voice in a room plays through <audio> elements and is not touched."""

from conftest import game_page, make_game

# Records, under back.js's patch, every node connected straight to a speaker, and the gain on it.
SPY = """(() => {
  const connect = AudioNode.prototype.connect;
  window.__toSpeaker = [];
  AudioNode.prototype.connect = function (to) {
    if (to instanceof AudioDestinationNode) window.__toSpeaker.push(this);
    return connect.apply(this, arguments);
  };
})()"""

# A game that makes its context and its own master gain as the page loads, before back.js, and
# plays a beep on each tap.
GAME = """
const ac = new AudioContext();
const master = ac.createGain();
master.connect(ac.destination);
window.beep = () => { const o = ac.createOscillator(); o.connect(master); o.start(); o.stop(ac.currentTime + 0.05); };
window.taps = 0;
addEventListener('pointerdown', () => { taps++; });
"""


def speaker_gains(page):
    return page.evaluate("() => window.__toSpeaker.map(n => n instanceof GainNode ? Math.round(n.gain.value * 1000) / 1000 : n.constructor.name)")


def test_the_volume_chip_sets_one_volume_for_every_game(site, context):
    make_game(site.games, "pomppu", [game_page("v1", script=GAME)])
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-aani")
    assert page.inner_text("#ai-pelit-aani") == "🔊"
    assert not page.is_visible("#ai-pelit-aani-paneeli")
    page.tap("#ai-pelit-aani")
    assert page.is_visible("#ai-pelit-aani-paneeli")
    assert page.inner_text("#ai-pelit-aani-luku") == "100 %"
    # A tap on the setting is not a tap in the game.
    assert page.evaluate("taps") == 0
    page.locator("#ai-pelit-aani-liuku").fill("40")
    assert page.inner_text("#ai-pelit-aani") == "🔉"
    page.tap("#ai-pelit-aani-mykista")
    assert page.inner_text("#ai-pelit-aani") == "🔇"
    assert page.inner_text("#ai-pelit-aani-luku") == "Mykistetty"
    assert page.evaluate("taps") == 0
    # A tap in the game closes it.
    page.mouse.click(180, 500)
    assert not page.is_visible("#ai-pelit-aani-paneeli")
    # Another game reads the same setting.
    page.goto(f"{site.url}games/hyppy/v1/")
    page.wait_for_selector("#ai-pelit-aani")
    assert page.inner_text("#ai-pelit-aani") == "🔇"
    page.tap("#ai-pelit-aani")
    page.tap("#ai-pelit-aani-mykista")
    assert page.inner_text("#ai-pelit-aani-luku") == "40 %"
    assert page.evaluate("localStorage.getItem('ai-pelit:_aani:voimakkuus')") == "40"
    assert page.evaluate("localStorage.getItem('ai-pelit:_aani:mykistetty')") is None


def test_every_sound_of_the_game_goes_through_the_volume(site, context):
    make_game(site.games, "pomppu", [game_page("v1", script=GAME)])
    site.build()
    context.add_init_script(SPY)
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-aani")
    page.evaluate("localStorage.setItem('ai-pelit:_aani:voimakkuus', '50')")
    page.reload()
    page.wait_for_selector("#ai-pelit-aani")
    # The game's master gain, connected before back.js, is the one node on the speaker until a
    # sound plays; from then on everything goes through the volume, 50 % heard as 0.25.
    page.evaluate("beep()")
    page.evaluate("""() => { const o = ac.createOscillator(); o.connect(ac.destination); o.start(); o.stop(ac.currentTime + 0.05);
        o.disconnect(ac.destination); }""")
    assert speaker_gains(page) == [1, 0.25]
    # A new context made after the page loaded, as the sound library does on the first tap.
    page.evaluate("""() => { const c = new AudioContext(); const g = c.createGain(); g.connect(c.destination); }""")
    assert speaker_gains(page) == [1, 0.25, 0.25]
    # Muting sets every volume gain to 0.
    page.tap("#ai-pelit-aani")
    page.tap("#ai-pelit-aani-mykista")
    assert speaker_gains(page) == [1, 0, 0]
    # A context drawn offline (no speaker) is left as it is.
    assert page.evaluate("""() => { const c = new OfflineAudioContext(1, 128, 44100); const o = c.createOscillator();
        return o.connect(c.destination) === c.destination; }""")


def test_a_frame_without_back_js_follows_the_page_around_it(site, context):
    # Ottelu loads each event's page into a frame of its own, without back.js.
    event = "<body><script>window.ready = true;<\\/script></body>"
    frame = f"<script>const f = document.createElement('iframe'); f.srcdoc = '{event}'; document.body.appendChild(f);</script>"
    make_game(site.games, "ottelu", [game_page("v1", body=frame)])
    site.build()
    context.add_init_script("localStorage.setItem('ai-pelit:_aani:voimakkuus', '20')")
    context.add_init_script(SPY)
    page = context.new_page()
    page.goto(f"{site.url}games/ottelu/v1/")
    page.wait_for_selector("#ai-pelit-aani")
    inner = page.frames[1]
    inner.wait_for_function("window.ready && AudioNode.prototype.__aiPelitAani")
    inner.evaluate("() => { const c = new AudioContext(); c.createOscillator().connect(c.destination); }")
    assert speaker_gains(inner) == [0.04]
