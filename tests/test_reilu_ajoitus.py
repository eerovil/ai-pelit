"""Fair timing (#404): a tap is judged at its own moment, not at the last drawn frame."""

import pytest

from test_hiljaiset_aanet import real  # noqa: F401

pytestmark = pytest.mark.games(
    "moukari", "seivashyppy", "pituushyppy", "kuula", "korkeushyppy", "keihas", "makihyppy",
    "piano", "trampoliini", "sormiskeitti",
)

# Each with the key that makes the judged action, and the function that judges it.
GAMES = [
    ("games/moukari/v12", "ArrowLeft", "press"),
    ("games/seivashyppy/v15", "ArrowLeft", "press"),
    ("games/pituushyppy/v17", "ArrowLeft", "press"),
    ("games/kuula/v10", "ArrowLeft", "press"),
    ("games/korkeushyppy/v14", "ArrowLeft", "press"),
    ("games/keihas/v16", "ArrowLeft", "press"),
    ("games/makihyppy/v11", " ", "action"),
]
LETTING_GO = [
    ("games/seivashyppy/v15", "holdPtr", "letGo"),
    ("games/pituushyppy/v17", "aimPtr", "release"),
    ("games/kuula/v10", "aimPtr", "release"),
    ("games/keihas/v16", "aimPtr", "release"),
]


def opened(real, context, url, ready):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{real.url}{url}/")
    page.wait_for_function(ready)
    page.errors = errors
    return page


@pytest.mark.parametrize("url,key,judge", GAMES)
def test_a_tap_between_frames_runs_the_game_to_its_own_moment(real, context, url, key, judge):
    page = opened(real, context, url, "typeof catchUp === 'function'")
    got = page.evaluate(
        """([key, judge]) => {
          requestAnimationFrame = () => 0;
          const log = [], realStep = step;
          step = d => { log.push(d); realStep(d); };
          eval(judge + ' = () => log.push("judged")');
          const tap = (make, back) => {
            log.length = 0;
            const ev = make();
            lastT = ev.timeStamp - back;
            (ev.type === 'pointerdown' ? c : window).dispatchEvent(ev);
            return { log: [...log], left: lastT - ev.timeStamp };
          };
          const down = () => new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 7, clientX: 2, clientY: 2 });
          const keyDown = () => new KeyboardEvent('keydown', { key });
          const out = { key: tap(keyDown, 8), finger: tap(down, 8), paused: tap(keyDown, 5000), behind: tap(keyDown, -5), long: tap(keyDown, 80) };
          // A frame that started before the tap it runs after takes no time back.
          log.length = 0;
          const was = lastT;
          frame(was - 3);
          out.frame = { log: [...log], moved: lastT - was };
          return out;
        }""",
        [key, judge],
    )
    assert got["key"]["log"][0] == pytest.approx(0.008, abs=1e-6)
    assert got["key"]["log"][1:] == ["judged"]            # the game moved first, then the tap counted
    assert got["key"]["left"] == 0                        # the next frame does not count that time again
    assert got["finger"]["log"][0] == pytest.approx(0.008, abs=1e-6)
    assert got["paused"]["log"] == ["judged"]             # after a pause the game does not jump
    assert got["behind"]["log"] == ["judged"]
    # A long frame is run through whole, in steps a frame could take.
    assert got["long"]["log"][:2] == pytest.approx([0.05, 0.03], abs=1e-6)
    assert got["long"]["log"][2:] == ["judged"]
    assert got["long"]["left"] == 0
    assert got["frame"]["log"] == [0]
    assert got["frame"]["moved"] == 0
    assert page.errors == []


@pytest.mark.parametrize("url,key,judge", GAMES)
def test_two_taps_in_one_frame_count_the_time_once(real, context, url, key, judge):
    page = opened(real, context, url, "typeof catchUp === 'function'")
    got = page.evaluate(
        """([key, judge]) => {
          requestAnimationFrame = () => 0;
          const log = [], realStep = step;
          step = d => { log.push(d); realStep(d); };
          eval(judge + ' = () => {}');
          const first = new KeyboardEvent('keydown', { key }), second = new KeyboardEvent('keydown', { key: 'q' });
          const start = first.timeStamp - 8;
          lastT = start;
          dispatchEvent(first); dispatchEvent(second);
          const inOrder = { ran: log.reduce((a, b) => a + b, 0) * 1000, want: second.timeStamp - start };
          // The later one handed over first: the earlier one then moves nothing.
          log.length = 0; lastT = start;
          dispatchEvent(second); dispatchEvent(first);
          return { inOrder, swapped: { ran: log.reduce((a, b) => a + b, 0) * 1000, left: lastT - second.timeStamp, want: second.timeStamp - start } };
        }""",
        [key, judge],
    )
    assert got["inOrder"]["ran"] == pytest.approx(got["inOrder"]["want"], abs=1e-6)
    assert got["swapped"]["ran"] == pytest.approx(got["swapped"]["want"], abs=1e-6)
    assert got["swapped"]["left"] == 0
    assert page.errors == []


@pytest.mark.parametrize("url,finger,judge", LETTING_GO)
def test_letting_go_between_frames_counts_at_its_own_moment(real, context, url, finger, judge):
    page = opened(real, context, url, "typeof catchUp === 'function'")
    log = page.evaluate(
        """([finger, judge]) => {
          requestAnimationFrame = () => 0;
          const log = [], realStep = step;
          step = d => { log.push(d); realStep(d); };
          eval(judge + ' = () => log.push("judged")');
          eval(finger + ' = 7');
          const ev = new PointerEvent('pointerup', { pointerId: 7 });
          lastT = ev.timeStamp - 8;
          window.dispatchEvent(ev);
          return log;
        }""",
        [finger, judge],
    )
    assert log[0] == pytest.approx(0.008, abs=1e-6)
    assert log[1:] == ["judged"]


def test_piano_a_press_between_frames_hits_the_note_it_reached(real, context):
    # The note is just out of reach at the last frame and in reach when the finger touches.
    page = opened(real, context, "games/piano/v11", "typeof catchUp === 'function'")
    page.evaluate("document.getElementById('go').click()")
    page.wait_for_function("state === 'play' && cur && cur.notes.length")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const n = cur.notes[0];
          const ev = new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 7,
            clientX: laneX + (n.lane + 0.5) * laneW, clientY: innerHeight - 5 });
          now = n.t - GOOD - 0.004; prev = ev.timeStamp - 8;
          const at = now;
          c.dispatchEvent(ev);
          return { hit: n.hit, moved: now - at, left: prev - ev.timeStamp };
        }"""
    )
    assert got["hit"] is True
    assert got["moved"] == pytest.approx(0.008, abs=1e-6)
    assert got["left"] == 0
    assert page.errors == []


def test_piano_a_long_frame_is_run_through_whole(real, context):
    page = opened(real, context, "games/piano/v11", "typeof catchUp === 'function'")
    page.evaluate("document.getElementById('go').click()")
    page.wait_for_function("state === 'play' && cur && cur.notes.length")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const ev = new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 7, clientX: 2, clientY: 2 });
          cur.notes = []; cur.end = 99; now = 1; prev = ev.timeStamp - 80;
          c.dispatchEvent(ev);
          return { moved: now - 1, left: prev - ev.timeStamp };
        }"""
    )
    assert got["moved"] == pytest.approx(0.08, abs=1e-6)
    assert got["left"] == 0


def test_makihyppy_a_short_hold_steers_until_the_finger_lifts(real, context):
    page = opened(real, context, "games/makihyppy/v11", "typeof catchUp === 'function'")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          padAt = () => 1;
          const log = [], realStep = step;
          step = d => { log.push(holding.size); realStep(d); };
          const finger = type => new PointerEvent(type, { bubbles: true, cancelable: true, pointerId: 7, clientX: 2, clientY: 400 });
          const down = finger('pointerdown');
          lastT = down.timeStamp;
          c.dispatchEvent(down);
          const up = finger('pointerup');
          lastT = up.timeStamp - 6;
          c.dispatchEvent(up);
          const pointer = { log: [...log], left: holding.size };
          log.length = 0;
          dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
          const lift = new KeyboardEvent('keyup', { key: 'ArrowLeft' });
          lastT = lift.timeStamp - 6;
          dispatchEvent(lift);
          return { pointer, key: { log: [...log], left: holding.size } };
        }"""
    )
    assert got["pointer"] == {"log": [1], "left": 0}    # one step, the finger still down
    assert got["key"]["log"][-1] == 1
    assert got["key"]["left"] == 0
    assert page.errors == []


def test_trampoliini_a_short_press_lasts_until_the_finger_lifts(real, context):
    page = opened(real, context, "games/trampoliini/v11", "typeof catchUp === 'function'")
    page.evaluate("startGo()")
    page.wait_for_function("J && (phase === 'air' || phase === 'mat')")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const seen = [], realStep = step;
          step = d => { seen.push({ held, twistHeld, squat }); realStep(d); };
          const finger = (type, id = 7) => new PointerEvent(type, { bubbles: true, cancelable: true, pointerId: id, clientX: 2, clientY: 2 });
          const lift = (act, set) => {
            seen.length = 0; set(); acc = 0;
            const ev = finger('pointerup');
            lastT = ev.timeStamp - 20;
            pad.querySelector(`[data-act="${act}"]`).dispatchEvent(ev);
            return seen[0];
          };
          const flip = lift('taakse', () => { held = 1; });
          const twist = lift('kierre', () => { twistHeld = true; });
          const afterFlip = held, afterTwist = twistHeld;
          // Bending the legs starts when the finger touched, not before.
          seen.length = 0; squat = false; acc = 0; phase = 'air';
          const ev = finger('pointerdown');
          lastT = ev.timeStamp - 20;
          c.dispatchEvent(ev);
          return { flip, twist, afterFlip, afterTwist, legs: seen[0], bent: squat };
        }"""
    )
    assert got["flip"]["held"] == 1
    assert got["twist"]["twistHeld"] is True
    assert got["afterFlip"] == 0 and got["afterTwist"] is False
    assert got["legs"]["squat"] is False
    assert got["bent"] is True
    assert page.errors == []


def test_piano_two_fingers_at_once_are_both_judged_and_the_time_counts_once(real, context):
    page = opened(real, context, "games/piano/v11", "typeof catchUp === 'function'")
    page.evaluate("document.getElementById('go').click()")
    page.wait_for_function("state === 'play' && cur && cur.notes.length")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const a = { t: 5, lane: 0, pitch: 60, beats: 1 }, b = { t: 5, lane: 3, pitch: 64, beats: 1 };
          cur.notes = [a, b]; now = 5 - 0.008;
          const finger = (lane, id) => new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: id,
            clientX: laneX + (lane + 0.5) * laneW, clientY: innerHeight - 5 });
          const one = finger(0, 7), two = finger(3, 8), start = one.timeStamp - 8, at = now;
          prev = start;
          c.dispatchEvent(one); c.dispatchEvent(two);
          return { hits: [a.hit, b.hit], moved: (now - at) * 1000, want: two.timeStamp - start };
        }"""
    )
    assert got["hits"] == [True, True]
    assert got["moved"] == pytest.approx(got["want"], abs=1e-6)
    assert page.errors == []


def test_trampoliini_the_push_counts_the_time_since_the_last_step(real, context):
    page = opened(real, context, "games/trampoliini/v11", "typeof catchUp === 'function'")
    page.evaluate("startGo()")
    page.wait_for_function("J && (phase === 'air' || phase === 'mat')")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const push = back => {
            phase = 'mat'; J.pumpT = null; J.matT = 0.01; acc = 0; squat = true; squatId = 7;
            const ev = new PointerEvent('pointerup', { bubbles: true, pointerId: 7 });
            lastT = ev.timeStamp - back;
            c.dispatchEvent(ev);
            return J.pumpT;
          };
          const within = push(8), past = push(20);
          phase = 'air'; J.vy = -5; J.y = COMH + 0.6; acc = 0.005;
          const toMat = timeToMat();
          acc = 0.01; lastT = 1e9;
          frame(lastT - 3);
          return { within, past, toMat, acc, lastT };
        }"""
    )
    assert got["within"] == pytest.approx(0.018, abs=1e-6)
    assert got["past"] == pytest.approx(0.03, abs=1e-6)      # one whole step ran, the rest is added
    assert got["toMat"] == pytest.approx(0.115, abs=1e-6)
    assert got["acc"] == pytest.approx(0.01)                 # a frame behind the tap takes no time back
    assert got["lastT"] == 1e9
    assert page.errors == []


def test_sormiskeitti_the_tap_reads_the_board_at_its_own_moment(real, context):
    page = opened(real, context, "games/sormiskeitti/v10", "typeof catchUp === 'function'")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          const tapAt = () => {
            acc = 0;
            const ev = new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 7 });
            last = ev.timeStamp - 12;     // 0.72 of a physics step
            window.dispatchEvent(ev);
            return { part: part(), text: ollieText };
          };
          // Just short of the perfect angle at the last step, past it at the tap.
          st = 'roll'; v = 6; ollie = 0; s = L + R * OLLIE_PERFECT - v * 0.5;
          const lip = tapAt();
          // Over the flight's top by the tap, still rising too fast at the last step.
          st = 'air'; ollie = 1; airF = 99; letGo = null; bonk = false; avy = 1 + G * 0.36;
          const top = tapAt();
          return { lip, top, ollie };
        }"""
    )
    assert got["lip"]["part"] == pytest.approx(0.72, abs=1e-6)
    assert got["lip"]["text"] == "TÄYDELLINEN OLLIE!"
    assert got["top"]["text"] == "TÄYDELLINEN IRROTUS!"
    assert page.errors == []


def test_sormiskeitti_a_new_run_starts_clean_with_time_left_in_the_step(real, context):
    page = opened(real, context, "games/sormiskeitti/v10", "typeof catchUp === 'function'")
    got = page.evaluate(
        """() => {
          requestAnimationFrame = () => 0;
          st = 'end'; endT = -1e9; acc = 15;
          dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' }));   // back to the start
          const after = st;
          dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' }));   // the first push
          return { after, st, kicks: kicks.length, ollie };
        }"""
    )
    assert got == {"after": "ready", "st": "roll", "kicks": 1, "ollie": 0}
    assert page.errors == []
