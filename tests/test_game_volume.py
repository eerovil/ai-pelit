"""Game volume (#336): one volume for every game, set in the menu the "‹ Pelit" chip opens
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

# A game that makes its context as the page loads, before back.js, and connects its master gain
# on the first sound, as every published game does (none connects to the speaker before back.js).
GAME = """
const ac = new AudioContext();
let master = null;
window.beep = () => {
  if (!master) { master = ac.createGain(); master.connect(ac.destination); }
  const o = ac.createOscillator(); o.connect(master); o.start(); o.stop(ac.currentTime + 0.05);
};
window.taps = 0;
addEventListener('pointerdown', () => { taps++; });
"""


def speaker_gains(page):
    return page.evaluate("() => window.__toSpeaker.map(n => n instanceof GainNode ? Math.round(n.gain.value * 1000) / 1000 : n.constructor.name)")


def test_the_back_chips_menu_sets_one_volume_for_every_game(site, context):
    make_game(site.games, "pomppu", [game_page("v1", script=GAME)])
    make_game(site.games, "hyppy", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    assert not page.is_visible("#ai-pelit-valikko")
    page.tap("#ai-pelit-back")
    assert page.is_visible("#ai-pelit-valikko")
    assert page.inner_text("#ai-pelit-aani-luku") == "100 %"
    # A tap on the setting is not a tap in the game.
    assert page.evaluate("taps") == 0
    page.locator("#ai-pelit-aani-liuku").fill("40")
    page.tap("#ai-pelit-aani-mykista")
    assert page.inner_text("#ai-pelit-aani-luku") == "Mykistetty"
    assert page.evaluate("taps") == 0
    # A tap in the game closes it.
    page.mouse.click(180, 500)
    assert not page.is_visible("#ai-pelit-valikko")
    # Another game reads the same setting.
    page.goto(f"{site.url}games/hyppy/v1/")
    page.wait_for_selector("#ai-pelit-back")
    page.tap("#ai-pelit-back")
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
    page.wait_for_selector("#ai-pelit-back")
    page.evaluate("localStorage.setItem('ai-pelit:_aani:voimakkuus', '50')")
    page.reload()
    page.wait_for_selector("#ai-pelit-back")
    # The game's master gain and a node connected straight to the speaker both go through the
    # volume, 50 % heard as 0.25.
    page.evaluate("beep()")
    page.evaluate("""() => { const o = ac.createOscillator(); o.connect(ac.destination); o.start(); o.stop(ac.currentTime + 0.05);
        o.disconnect(ac.destination); }""")
    assert speaker_gains(page) == [0.25]
    # A new context made after the page loaded, as the sound library does on the first tap.
    page.evaluate("""() => { const c = new AudioContext(); const g = c.createGain(); g.connect(c.destination); }""")
    assert speaker_gains(page) == [0.25, 0.25]
    # Muting sets every volume gain to 0.
    page.tap("#ai-pelit-back")
    page.tap("#ai-pelit-aani-mykista")
    assert speaker_gains(page) == [0, 0]
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
    page.wait_for_selector("#ai-pelit-back")
    inner = page.frames[1]
    inner.wait_for_function("window.ready && AudioNode.prototype.__aiPelitAani")
    inner.evaluate("() => { const c = new AudioContext(); c.createOscillator().connect(c.destination); }")
    assert speaker_gains(inner) == [0.04]


def test_a_change_in_another_tab_shows_at_once_and_the_panel_fits_a_390px_phone(site, browser):
    make_game(site.games, "pomppu", [game_page("v1", script=GAME)])
    site.build()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script(SPY)
    try:
        page, other = ctx.new_page(), ctx.new_page()
        for p in (page, other):
            p.goto(f"{site.url}games/pomppu/v1/")
            p.wait_for_selector("#ai-pelit-back")
        page.evaluate("beep()")
        other.tap("#ai-pelit-back")
        other.locator("#ai-pelit-aani-liuku").fill("20")
        # The first page hears of it through the storage event: its chip and its sound follow.
        page.wait_for_function("AiPelitAani.level === 20")
        assert speaker_gains(page) == [0.04]
        # The panel is whole on screen.
        assert other.evaluate("""() => { const m = document.getElementById('ai-pelit-valikko').getBoundingClientRect();
            return m.width > 0 && m.left >= 0 && m.right <= innerWidth && m.bottom <= innerHeight; }""")
        # A restart keeps it.
        other.reload()
        other.wait_for_selector("#ai-pelit-back")
    finally:
        ctx.close()


def test_unmute_at_zero_gives_the_sound_back_with_one_tap(site, context):
    make_game(site.games, "pomppu", [game_page("v1")])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/pomppu/v1/")
    page.tap("#ai-pelit-back")
    page.locator("#ai-pelit-aani-liuku").fill("0")
    assert page.inner_text("#ai-pelit-aani-mykista") == "🔊 Äänet päälle"
    page.tap("#ai-pelit-aani-mykista")
    assert page.inner_text("#ai-pelit-aani-luku") == "50 %"
    assert page.inner_text("#ai-pelit-aani-mykista") == "🔇 Mykistä"


def test_the_menu_adds_nothing_to_the_corner_fits_every_corner_and_goes_up(site, browser):
    # Jään alla v2 and Orava v2–v4 lay their sideways HUD out right beside the chip, so the chip
    # stays as it was: only "‹ Pelit". Its menu goes back up and shows whole in every corner.
    corners = ["", ' data-corner="bottom-left"', ' data-corner="top-right"']
    # One game per corner: only each game's newest version is on the site (#346).
    slugs = ["kulma", "nurkka", "pomppu"]
    for slug, c in zip(slugs, corners):
        make_game(site.games, slug, [game_page("v1").replace('back.js"', 'back.js"' + c)])
    site.build()
    for size in ({"width": 360, "height": 740}, {"width": 740, "height": 360}):
        ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
        try:
            page = ctx.new_page()
            for n, slug in enumerate(slugs, 1):
                page.goto(f"{site.url}games/{slug}/v1/")
                page.wait_for_selector("#ai-pelit-back")
                assert page.inner_text("#ai-pelit-kulma") == "‹ Pelit"
                assert page.evaluate("document.getElementById('ai-pelit-back').getBoundingClientRect().width") < 70
                page.tap("#ai-pelit-back")
                assert page.evaluate("""() => { const m = document.getElementById('ai-pelit-valikko').getBoundingClientRect();
                    return m.left >= 0 && m.top >= 0 && m.right <= innerWidth && m.bottom <= innerHeight; }"""), (size, n)
                # A second tap on the chip closes it.
                page.tap("#ai-pelit-back")
                assert not page.is_visible("#ai-pelit-valikko")
            page.tap("#ai-pelit-back")
            page.tap("#ai-pelit-takaisin")
            page.wait_for_url(f"{site.url}#/pomppu")
        finally:
            ctx.close()


def test_removed_frames_let_their_sound_go(site, context):
    # Ottelu makes a new frame for each event and removes the old one.
    script = """window.nextEvent = () => new Promise(done => {
      document.querySelectorAll('iframe').forEach(f => f.remove());
      const f = document.createElement('iframe');
      f.srcdoc = '<body>laji</body>';
      f.onload = () => { const c = new f.contentWindow.AudioContext(); c.createOscillator().connect(c.destination); setTimeout(done, 0); };
      document.body.appendChild(f);
    });"""
    make_game(site.games, "ottelu", [game_page("v1", script=script)])
    site.build()
    page = context.new_page()
    page.goto(f"{site.url}games/ottelu/v1/")
    page.wait_for_selector("#ai-pelit-back")
    for _ in range(4):
        page.evaluate("nextEvent()")
        page.wait_for_timeout(50)
        assert page.evaluate("AiPelitAani.contexts") == 1
    # The last event still follows the setting.
    page.tap("#ai-pelit-back")
    page.tap("#ai-pelit-aani-mykista")
    assert page.frames[1].evaluate("AudioNode.prototype.__aiPelitAani") is True
