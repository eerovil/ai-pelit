"""Raketti v4 (#548): tiny bodies, one finger, short trips, the Moon base and Mars.

Every trip is flown here by following the game's own hints (FOLLOW below): the stick is set to
the hint's direction and power, exactly what a drag along the arrow does. The game itself has no
autopilot; if a hint ever leads nowhere, the trip test fails.
"""
import shutil

import pytest

from conftest import ROOT, turn

URL = 'games/raketti/v4/'
TRIP_IDS = ['kiertorata', 'asema', 'kuu-kierto', 'kuuhun', 'kotiin', 'kivi', 'paneeli', 'tankki', 'tehdas', 'mars']

# Test helpers only, never shipped. follow(trip) flies a fresh flight by the hints with the frame
# loop stopped, and counts words that changed again within 0.3 s (flicker).
FOLLOW = r"""
window.follow = function (trip, opts = {}) {
  cancelAnimationFrame(frameId); frameId = 0;
  for (const t of TRIPS) stars[t.id] = stars[t.id] || 1;
  begin(freshFlight(trip)); cancelAnimationFrame(frameId); frameId = 0;
  let last = '', hw, since = 0; const quick = [];
  for (let i = 0; i < 120 * 2000 && ship.phase === 'flight'; i++) {
    if (opts.until && opts.until()) break;
    if (i % 6 === 0 && (i % 120 === 0 || !(last === 'Odota' && (hw === undefined || hw > 4)))) path = predictPath(ship);
    const h = hint(ship, path); hw = h.wait;
    if (h.word !== last) { if (last && ship.t - since < 0.3) quick.push([since, last, h.word]); since = ship.t; last = h.word; }
    if (h.dir !== undefined) { stick.angle = h.dir; stick.power = h.power ?? 1; } else stick.power = 0;
    step(STEP);
    if (ship.phase === 'flight' && goalMet(ship)) endFlight(TRIP[ship.trip].goal, true);
  }
  stick.power = 0;
  return { phase: ship.phase, reason: ship.reason, t: ship.t, stars: ship.stars, fuel: fuelShare(),
    touch: ship.touch, quick, saved: JSON.parse(localStorage.getItem('ai-pelit:raketti:tahdet') || '{}') };
};
"""


def open_game(site, context):
    shutil.copytree(ROOT / 'games/raketti', site.games / 'raketti')
    site.build()
    page = context.new_page()
    page.errors = []
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    page.goto(site.url + URL)
    page.wait_for_function("typeof ship !== 'undefined' && !!document.querySelector('#trips .trip')")
    page.add_script_tag(content=FOLLOW)
    return page


def reopen(page):
    page.reload()
    page.wait_for_function("!!document.querySelector('#trips .trip')")
    page.add_script_tag(content=FOLLOW)


# The longest each trip may take in game seconds when the hints are followed (Mars's is a real
# journey round the Sun, #548: about 5-10 minutes).
LIMIT = {'kiertorata': 15, 'asema': 90, 'kuu-kierto': 70, 'kuuhun': 80, 'kotiin': 150, 'kivi': 110,
         'paneeli': 100, 'tankki': 120, 'tehdas': 120, 'mars': 600}


@pytest.mark.parametrize('trip', TRIP_IDS)
def test_every_trip_finishes_by_following_the_hints(site, context, trip):
    page = open_game(site, context)
    r = page.evaluate('trip => follow(trip)', trip)
    assert r['phase'] == 'done', r
    assert r['t'] < LIMIT[trip], r
    assert r['stars'] >= 2, r
    if r['touch'] is not None and trip not in ('kiertorata', 'kuu-kierto'):
        assert r['touch']['soft'], r
    assert r['saved'][trip] >= r['stars']
    # Words that come and go again at once read as a loop (#548: "Odota", "Korjaa"... forever).
    assert len(r['quick']) <= 14, r['quick']
    assert page.errors == []


@pytest.mark.parametrize('body,speed,phase', [
    ('moon', 5.5, 'crashed'), ('moon', 2.4, 'flight'), ('earth', 6.5, 'crashed'), ('rock', 1.4, 'flight'),
])
def test_landing_limits(site, context, body, speed, phase):
    page = open_game(site, context)
    r = page.evaluate("""([id, speed]) => { cancelAnimationFrame(frameId); frameId = 0;
      begin(freshFlight('kuuhun')); cancelAnimationFrame(frameId); frameId = 0;
      const b = BODY[id], p = bodyAt(b, ship.t), r = b.radius + SHIP.size + 0.01;
      Object.assign(ship, { landedOn: null, x: p.x, y: p.y + r, vx: p.vx, vy: p.vy - speed });
      step(STEP); return [ship.phase, ship.touch && ship.touch.soft, b.land]; }""", [body, speed])
    assert r[0] == phase, r
    if phase == 'flight':
        assert r[1] is (speed <= r[2] / 2)
    assert page.errors == []


def land_on_moon(page, trip, a, built):
    return page.evaluate("""([trip, a, built]) => { cancelAnimationFrame(frameId); frameId = 0;
      for (const id of ['paneeli', 'tankki', 'tehdas']) { if (built) stars[id] = 1; else delete stars[id]; }
      begin(freshFlight(trip)); cancelAnimationFrame(frameId); frameId = 0;
      const p = bodyAt(MOON, ship.t), r = MOON.radius + SHIP.size + 0.002;
      Object.assign(ship, { landedOn: null, dv: 50, x: p.x + r * Math.sin(a), y: p.y + r * Math.cos(a),
        vx: p.vx - Math.sin(a), vy: p.vy - Math.cos(a) });
      step(STEP); const met = goalMet(ship), h = hint(ship, null);
      for (let i = 0; i < 600; i++) step(STEP);
      return { met, word: h.word, refuel: ship.refuel, tanked: ship.tanked, dv: ship.dv, full: SHIP.dv }; }""",
                         [trip, a, built])


def test_a_part_lands_only_in_the_base(site, context):
    page = open_game(site, context)
    outside = land_on_moon(page, 'paneeli', 1.2, False)
    assert outside['met'] is False and outside['word'] == 'Hyppää'
    inside = land_on_moon(page, 'paneeli', 0.2, False)
    assert inside['met'] is True
    assert page.errors == []


def test_the_finished_base_fills_the_mars_ship(site, context):
    page = open_game(site, context)
    unbuilt = land_on_moon(page, 'mars', 0.1, False)
    assert unbuilt['refuel'] is False and unbuilt['tanked'] is False
    built = land_on_moon(page, 'mars', 0.1, True)
    assert built['word'] == 'Tankataan'
    assert built['tanked'] is True and built['dv'] == pytest.approx(built['full'])
    assert page.errors == []


def test_trips_unlock_in_order_mars_after_the_whole_base(site, context):
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify("
                  "{kiertorata: 3, asema: 2, 'kuu-kierto': 1, kuuhun: 1, kotiin: 1, kivi: 2, paneeli: 1, tankki: 1, x: 3, kuuhun2: 'a'}))")
    reopen(page)
    assert page.locator('.trip[data-trip="tehdas"]').is_enabled()
    assert page.locator('.trip[data-trip="mars"]').is_disabled()
    assert page.locator('.trip[data-trip="mars"] b').inner_text().startswith('🔒')
    assert page.evaluate('Object.keys(readStars()).length') == 8
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 9, asema: 1.5}))")
    assert page.evaluate('readStars()') == {}
    assert page.errors == []


def test_mars_window_wait_counts_down_and_can_be_skipped_on_the_ground(site, context):
    page = open_game(site, context)
    r = page.evaluate("""() => { cancelAnimationFrame(frameId); frameId = 0;
      begin(freshFlight('mars')); cancelAnimationFrame(frameId); frameId = 0;
      Object.assign(ship, { t: 20, tanked: true, landedOn: { id: 'moon', a: 0 } }); sitOn(ship, MOON, 0);
      const h = hint(ship, null); currentHint = h; updateHud();
      return { word: h.word, window: h.window, wait: h.wait, skip: canSkip(h), text: document.querySelector('#hint').textContent,
        open: marsWait(20 + h.wait + 1) }; }""")
    assert r['word'] == 'Odota' and r['window'] is True and r['skip'] is True
    assert 100 < r['wait'] < 200
    assert r['text'].startswith('Odota 2 min') and r['text'].endswith('⏩')
    assert r['open'] == 0
    assert page.evaluate('[waitText(4.2), waitText(99), waitText(125)]') == ['5 s', '99 s', '2 min 05 s']
    assert page.errors == []


def test_tap_on_the_wait_skips_it(site, context):
    page = open_game(site, context)
    page.evaluate("""() => { follow('kuu-kierto', { until: () => { if (ship.t < 6 || !path) return false;
      const h = hint(ship, path); return canSkip(h) && h.wait > 5; } });
      currentWord = ''; paused = false; ship.phase = 'flight'; play(); }""")
    page.wait_for_function("document.querySelector('#hint').textContent.includes('⏩')")
    before = page.evaluate('ship.t')
    page.locator('#hint').click()
    page.wait_for_function('!warp', timeout=10000)
    assert page.evaluate('ship.t') - before > 4
    assert page.errors == []


def test_the_camera_holds_mars_still_through_uneven_frames(site, context):
    page = open_game(site, context)
    # Mars's place on screen, against a straight line between the frames before and after, through
    # frames of uneven length (#548: the camera chasing Mars round the Sun shook it by about 7 px).
    wobble = page.evaluate(CAMERA, 'f % 3 === 0 ? 0.033 : 0.012')
    assert wobble[1] > 50 and wobble[2] == 'done', wobble
    assert wobble[0] < 0.5, wobble
    assert page.errors == []


CAMERA = """frames => {
      follow('mars', { until: () => refBody(ship) === MARS });
      // The game's own frame loop, called by hand with the frame times given.
      camReady = false; paused = false; lastFrame = 0; acc = 0; let f = 0, now = 1000; const pts = [], devs = [];
      while (ship.phase === 'flight' && f < 20000) {
        now += eval(frames) * 1000; f++;
        frame(now); cancelAnimationFrame(frameId); frameId = 0;
        const h = currentHint; if (h && h.dir !== undefined) { stick.angle = h.dir; stick.power = h.power ?? 1; } else stick.power = 0;
        if (ship.phase === 'flight' && goalMet(ship)) endFlight('ok', true);
        const m = bodyAt(MARS, ship.t);
        if (f > 120 && nearestSurface(ship).alt < 60 && !ship.landedOn) pts.push([sx(m.x), sy(m.y), now]);
      }
      for (let i = 1; i + 1 < pts.length; i++) {
        const [a, b, c] = [pts[i - 1], pts[i], pts[i + 1]], u = (b[2] - a[2]) / Math.max(1e-9, c[2] - a[2]);
        devs.push(Math.hypot(b[0] - a[0] - (c[0] - a[0]) * u, b[1] - a[1] - (c[1] - a[1]) * u));
      }
      devs.sort((p, q) => p - q);
      return [devs[Math.floor(devs.length * 0.9)], pts.length, ship.phase, devs[Math.floor(devs.length * 0.5)], devs[devs.length - 1]]; }"""



def test_the_path_round_the_moon_holds_still(site, context):
    # The path is worked out every 4th frame; in between it must move with the Moon, or round
    # the Moon it jumps back each time and shakes (#548). The ship coasts, so the path is fixed.
    page = open_game(site, context)
    out = page.evaluate("""() => {
      // Tanked for Mars in a round orbit 8 m above the Moon, as on the owner's phone.
      follow('kiertorata'); begin(freshFlight('mars')); cancelAnimationFrame(frameId); frameId = 0;
      const m0 = bodyAt(MOON, ship.t), r = MOON.radius + 8, v = Math.sqrt(MOON.mu / r);
      Object.assign(ship, { x: m0.x, y: m0.y + r, vx: m0.vx + v, vy: m0.vy, landedOn: null, tanked: true, dv: ROCKETS.raketti.dv, visited: ['earth', 'moon'] });
      camReady = false; paused = false; lastFrame = 0; acc = 0; stick.power = 0; let now = 1000; const pts = [], devs = [];
      // Where the path says the ship will be at one fixed time: the same spot round the Moon each frame.
      const T = ship.t + 20, at = () => { const ps = path.points, i = ps.findIndex(p => p.t >= T), a = ps[i - 1], b = ps[i], u = (T - a.t) / (b.t - a.t);
        return { x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u }; };
      for (let f = 0; f < 240 && ship.phase === 'flight'; f++) {
        now += (f % 3 === 0 ? 0.033 : 0.012) * 1000;
        frame(now); cancelAnimationFrame(frameId); frameId = 0;
        const q = at(), m = bodyAt(MOON, ship.t);
        if (f > 20 && path.frame === MOON) pts.push([sx(q.x) - sx(m.x), sy(q.y) - sy(m.y), now]);
      }
      for (let i = 1; i + 1 < pts.length; i++) {
        const [a, b, c] = [pts[i - 1], pts[i], pts[i + 1]], u = (b[2] - a[2]) / Math.max(1e-9, c[2] - a[2]);
        devs.push(Math.hypot(b[0] - a[0] - (c[0] - a[0]) * u, b[1] - a[1] - (c[1] - a[1]) * u));
      }
      devs.sort((p, q) => p - q);
      return [devs[Math.floor(devs.length * 0.9)], pts.length, cam.scale]; }""")
    assert out[1] > 150, out
    assert out[0] < 0.5, out
    assert page.errors == []

def test_the_stick_grows_as_the_square_of_the_drag(site, context):
    page = open_game(site, context)
    page.locator('.trip[data-trip="kiertorata"]').click()
    page.mouse.move(180, 400)
    page.mouse.down()
    page.mouse.move(180, 395)
    assert page.evaluate('stick.power') == 0
    page.mouse.move(180, 356)
    assert page.evaluate('[stick.power, stick.angle]') == pytest.approx([0.25, 0], abs=1e-6)
    page.mouse.move(300, 400)
    assert page.evaluate('[stick.power, stick.angle]') == pytest.approx([1, 1.5707963], abs=1e-6)
    page.mouse.up()
    assert page.evaluate('stick.power') == 0
    assert page.errors == []


def test_flight_resumes_after_reload_and_turning(site, context):
    page = open_game(site, context)
    page.evaluate("follow('kuuhun', { until: () => ship.t > 20 }); saveFlight(); saveStars()")
    before = page.evaluate('[ship.t, ship.x, ship.y]')
    reopen(page)
    assert page.locator('#resume').inner_text() == 'Jatka: Kuuhun'
    page.locator('#resume').click()
    page.evaluate('paused = true')
    turn(page, {'width': 740, 'height': 360})
    # A frame or two may run between the tap and the pause.
    assert page.evaluate('[ship.t, ship.x, ship.y]') == pytest.approx(before, abs=1)
    assert page.evaluate("ship.trip") == 'kuuhun'
    page.locator('#pause').click()
    page.locator('#to-menu').click()
    assert page.locator('#resume').is_visible()
    assert page.errors == []


def test_looking_at_the_menu_saves_no_flight(site, context):
    page = open_game(site, context)
    reopen(page)
    assert page.locator('#resume').is_hidden()
    assert page.evaluate("localStorage.getItem('ai-pelit:raketti:matka')") is None


@pytest.mark.parametrize('mutation', [
    "", "s.x = null", "s.trip = 'ufo'", "s.dv = 1e9", "s.visited = ['pluto']", "s.landedOn = { id: 'moon', a: 'x' }",
    "s.x = 1e6", "s.vx = 1e200", "Object.assign(s, { throttle: 1, point: 'pro', fuel: 3 }); delete s.dv",
    "localStorage.removeItem('ai-pelit:raketti:tahdet')",
])
def test_corrupt_or_old_saves_are_not_resumed(site, context, mutation):
    page = open_game(site, context)
    # kuuhun is open, so only the mutation (a lost star store locks it again) makes the save unusable.
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 1, asema: 1, 'kuu-kierto': 1}))")
    page.evaluate(f"""() => {{ const s = freshFlight('kuuhun'); {mutation};
      localStorage.setItem('ai-pelit:raketti:matka', JSON.stringify(s)); }}""")
    reopen(page)
    # The unchanged save resumes, which shows the others fail for their own reason.
    assert page.locator('#resume').is_visible() == (mutation == "")
    assert page.errors == []


FITS = """sel => { const r = document.querySelector(sel).getBoundingClientRect();
  return r.width > 0 && r.top >= -1 && r.left >= -1 && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1; }"""


@pytest.mark.parametrize('width,height', [(360, 640), (360, 740), (390, 844), (740, 360)])
def test_menus_and_flight_fit_the_screen(site, browser, width, height):
    context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify("
                  "{kiertorata: 3, asema: 2, 'kuu-kierto': 1, kuuhun: 1, kotiin: 1, kivi: 1, paneeli: 1, tankki: 1, tehdas: 1}))")
    reopen(page)
    for sel in ['#menu', '.trip[data-trip="kiertorata"]', '#star-total']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    page.locator('.trip[data-trip="mars"]').click()
    page.wait_for_function("document.querySelector('#hint').textContent !== ''")
    for sel in ['#hint', '#pause', '#fuel', '#trip-name', '#c']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    page.locator('#pause').click()
    for sel in ['#continue', '#to-menu']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    # Back in the menu with a flight to resume: every trip still shows without scrolling.
    page.locator('#to-menu').click()
    for sel in ['#resume'] + [f'.trip[data-trip="{t}"]' for t in LIMIT]:
        assert page.evaluate(FITS, sel), (sel, width, height)
    assert page.evaluate("(m => m.scrollHeight <= m.clientHeight + 1)(document.querySelector('#menu'))")
    page.evaluate("follow('kiertorata'); paused = false; endShownAt = 0; play()")
    page.wait_for_selector('#result:not([hidden])')
    for sel in ['#result', '#result-next', '#retry', '#result-menu']:
        assert page.evaluate(FITS, sel), (sel, width, height)
    assert page.evaluate('document.documentElement.scrollHeight <= innerHeight + 1')
    assert page.errors == []
    context.close()


def test_a_new_trip_asks_before_replacing_a_saved_one(site, browser):
    context = browser.new_context(viewport={'width': 360, 'height': 740}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 1}))")
    reopen(page)
    page.locator('.trip[data-trip="asema"]').click()
    page.wait_for_function("document.querySelector('#hint').textContent !== ''")
    page.locator('#pause').click()
    page.locator('#to-menu').click()
    page.locator('.trip[data-trip="kiertorata"]').click()
    assert page.locator('#replace-panel').is_visible()
    assert 'Avaruusasemalle' in page.locator('#replace-text').text_content()
    page.locator('#replace-no').click()
    assert page.locator('#menu').is_visible()
    assert page.evaluate("JSON.parse(localStorage.getItem('ai-pelit:raketti:matka')).trip") == 'asema'
    page.locator('.trip[data-trip="kiertorata"]').click()
    page.locator('#replace-yes').click()
    page.wait_for_function("ship && ship.trip === 'kiertorata' && $('menu').hidden")
    assert page.errors == []
    context.close()


def test_v2_saves_are_left_alone(site, browser):
    context = browser.new_context(viewport={'width': 360, 'height': 740}, is_mobile=True, has_touch=True)
    page = open_game(site, context)
    old = {'ai-pelit:raketti:lento': '{"trip":"kuuhun","x":1}', 'ai-pelit:raketti:saavutukset': '{"kuuhun":3}'}
    for k, v in old.items():
        page.evaluate("([k, v]) => localStorage.setItem(k, v)", [k, v])
    reopen(page)
    page.evaluate("follow('kiertorata')")
    reopen(page)
    for k, v in old.items():
        assert page.evaluate("k => localStorage.getItem(k)", k) == v
    assert page.errors == []
    context.close()



def test_stars_won_in_another_tab_are_kept(site, context):
    page = open_game(site, context)
    # Another tab (or phone window) finishes Avaruusasemalle after this one loaded its stars.
    page.evaluate("localStorage.setItem('ai-pelit:raketti:tahdet', JSON.stringify({kiertorata: 1, asema: 2}))")
    # follow() opens every trip at one star in this tab's memory; the other tab's two must win.
    out = page.evaluate("follow('kiertorata')")
    assert out['phase'] == 'done' and out['stars'] == 3, out
    assert out['saved']['kiertorata'] == 3 and out['saved']['asema'] == 2, out
    assert page.errors == []


def test_mars_needs_the_moon_base_fuel_first(site, context):
    page = open_game(site, context)
    out = page.evaluate("""() => {
      begin(freshFlight('mars')); cancelAnimationFrame(frameId); frameId = 0;
      ship.landedOn = { id: 'mars', a: 0 }; ship.visited = ['earth', 'moon', 'mars'];
      const without = goalMet(ship); ship.tanked = true; return [without, goalMet(ship)]; }""")
    assert out == [False, True]


def test_the_game_stops_drawing_while_nothing_moves(site, context):
    # A still game must not draw every frame (docs/making-games.md): menus and the pause panel rest.
    page = open_game(site, context)
    count = "frames"
    page.wait_for_timeout(300)
    a = page.evaluate(count); page.wait_for_timeout(500)
    assert page.evaluate(count) == a, 'the first menu keeps drawing'
    page.locator('.trip[data-trip="kiertorata"]').click()
    a = page.evaluate(count); page.wait_for_timeout(500)
    assert page.evaluate(count) > a + 5, 'a flight must draw'
    page.locator('#pause').click()
    page.wait_for_timeout(100)
    a = page.evaluate(count); page.wait_for_timeout(500)
    assert page.evaluate(count) == a, 'the pause panel keeps drawing'
    page.locator('#continue').click()
    a = page.evaluate(count); page.wait_for_timeout(500)
    assert page.evaluate(count) > a + 5, 'Jatka must start the loop again'
    # A resize behind the menu (the phone turned) redraws it once, then rests.
    page.locator('#pause').click(); page.locator('#to-menu').click()
    page.wait_for_timeout(100)
    a = page.evaluate(count)
    page.evaluate("document.getElementById('c').style.width = '300px'")
    page.wait_for_timeout(300)
    b = page.evaluate(count)
    assert a < b <= a + 3, (a, b)
    page.wait_for_timeout(400)
    assert page.evaluate(count) == b
    assert page.errors == []



# Each burn the hints ask for, as followed: its word, how long it ran, the share of it the hint
# showed left at its first and last moment, and the real seconds it took on screen, whole and
# from "melkein" on (#548: burns last tenths of a second, and players went past their end).
BURNS = r"""
window.burns = function (trip) {
  const runs = []; let cur = null;
  const real = hint;
  window.hint = function (s, p) {
    const h = real(s, p);
    const key = h.left !== undefined ? h.word : null;
    if (cur && cur.word !== key) { cur.next = h.word; runs.push(cur); cur = null; }
    if (key) {
      if (!cur) cur = { word: key, from: s.t, first: h.left, real: 0, tail: 0 };
      cur.to = s.t; cur.last = h.left;
      // The target scale; the game eases toward it (down within a few frames).
      const k = timeScale(h);
      cur.real += STEP / k;
      if (nearEnd(h)) cur.tail += STEP / k;
    }
    return h;
  };
  try { follow(trip); } finally { window.hint = real; }
  if (cur) runs.push(cur);
  return runs.map(r => ({ ...r, long: r.to - r.from }));
};
"""


@pytest.mark.parametrize('trip', TRIP_IDS)
def test_a_burn_shows_how_much_is_left_and_ends_slowly(site, context, trip):
    page = open_game(site, context)
    page.add_script_tag(content=BURNS)
    runs = page.evaluate('trip => burns(trip)', trip)
    # A burn that ends by itself, not handed on to another push or begun already done.
    ends = [r for r in runs if r['long'] >= 0.1 and r['first'] == 1 and r.get('next') in ('Odota', 'Päästä irti', 'Valmis!')]
    assert ends, runs
    # Never an empty bar, "melkein" and the slowest time from a burn's first moment.
    assert all(r['first'] > 0 for r in runs), runs
    for r in ends:
        # The bar starts full and is about empty when the word changes.
        assert r['last'] < 0.2, r
        # However short in game time, its end lasts most of a second or more on screen (a push of
        # a few hundredths of a second, all of it its end, runs at the slowest time, SLOWEST).
        assert r['tail'] > 0.75, r
        # It never crawls: at most a few seconds more than at the fine moves' own pace (0.35).
        assert r['real'] < r['long'] / 0.35 + 8, r
    assert page.errors == []


def test_the_hint_says_when_a_burn_is_nearly_done_and_when_to_let_go(site, context):
    page = open_game(site, context)
    # Fly the first trip by the hints until its "Sivulle" burn is nearly done, the push still held.
    r = page.evaluate("""() => { follow('kiertorata', { until: () => { const h = hint(ship, path);
        return h.word === 'Sivulle' && nearEnd(h); } });
      stick.power = 1; ship.thrust = 1; currentHint = hint(ship, path); updateHud();
      const el = document.querySelector('#hint');
      const out = { text: el.textContent, near: el.classList.contains('near'), bar: el.style.getPropertyValue('--left'),
        scale: timeScale(currentHint) };
      // The burn done and the push still held: the hint says to let go.
      currentHint = { word: 'Odota' }; updateHud();
      out.stop = el.textContent; out.red = el.classList.contains('stop');
      // On the first trip the hint itself says it, held on past the end of "Sivulle".
      for (let i = 0; i < 240 && currentHint.word === 'Sivulle'; i++) { step(STEP); currentHint = hint(ship, path = predictPath(ship)); }
      updateHud(); out.own = el.textContent; out.ownRed = el.classList.contains('stop');
      ship.thrust = 0; updateHud(); out.after = el.textContent;
      return out; }""")
    assert r['text'].endswith('Sivulle – melkein') and r['near'], r
    assert 0 <= int(r['bar'].rstrip('%')) < 40, r
    assert r['scale'] < 0.35, r
    assert r['stop'].endswith('Päästä irti') and r['red'], r
    assert r['own'].endswith('Päästä irti') and r['ownRed'], r
    assert 'Päästä irti' not in r['after'], r
    assert page.errors == []
