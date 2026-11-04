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
          const out = { key: tap(keyDown, 8), finger: tap(down, 8), paused: tap(keyDown, 5000), behind: tap(keyDown, -5) };
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
    assert got["frame"]["log"] == [0]
    assert got["frame"]["moved"] == 0
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
