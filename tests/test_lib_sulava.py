"""The shared smooth-movement library in public/lib/sulava-1/ (#480), run in Chromium on a made-up clock."""

import pytest

from conftest import ROOT

LIB = (ROOT / "public" / "lib" / "sulava-1" / "sulava.js").read_text()

# Feeds a track spots of a player moving at 1 unit/s, sent every `gap` s on the sender's clock and
# arriving `base` s later plus a jitter of up to `jit` s, then draws it at 60 frames a second.
# Returns the drawn x of each frame after the first second, and the track's delay.
RUN = """([gap, jit, base, secs, opts]) => {
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const tr = AiPelitSulava.track(opts || { keys: ['x', 'y'] });
  const msgs = [];
  for (let t = 0; t < secs; t += gap) msgs.push({ t, at: 100 + t + base + rnd() * jit });
  msgs.sort((a, b) => a.at - b.at);
  const xs = []; let k = 0;
  for (let f = 0; f < secs * 60; f++) {
    const now = 100 + f / 60;
    while (k < msgs.length && msgs[k].at <= now) { const m = msgs[k++]; tr.push(m.t, { x: m.t, y: 0 }, m.at); }
    const s = tr.at(now);
    if (f >= 60 && s) xs.push(s.x);
  }
  return { xs, delay: tr.delay };
}"""


@pytest.fixture
def page(context):
    p = context.new_page()
    p.set_content("<p>sulava</p>")
    p.add_script_tag(content=LIB)
    return p


def steps(xs):
    return [b - a for a, b in zip(xs, xs[1:])]


def test_uneven_messages_draw_as_even_steps(page):
    r = page.evaluate(RUN, [0.1, 0.06, 0.05, 6, None])
    st = steps(r["xs"])
    mean = sum(st) / len(st)
    # Real speed 1/s at 60 frames: 1/60 a frame. Never backwards, never a stop, never a leap.
    assert abs(mean - 1 / 60) < 0.002
    assert min(st) > 0
    assert max(st) < 1.5 / 60 and min(st) > 0.5 / 60, (min(st), max(st))
    spread = (sum((s - mean) ** 2 for s in st) / len(st)) ** 0.5
    assert spread < 0.15 * mean, spread


def test_the_old_way_jerks_on_the_same_messages(page):
    """The same messages, drawn straight at the newest spot as Last Signal v16 and Kaahari v6 do."""
    st = page.evaluate("""() => {
      let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      const msgs = []; for (let t = 0; t < 6; t += 0.1) msgs.push({ t, at: 100 + t + 0.05 + rnd() * 0.06 });
      msgs.sort((a, b) => a.at - b.at);
      let x = 0, k = 0; const xs = [];
      for (let f = 0; f < 360; f++) { const now = 100 + f / 60; while (k < msgs.length && msgs[k].at <= now) x = msgs[k++].t; if (f >= 60) xs.push(x); }
      return xs;
    }""")
    assert max(steps(st)) > 0.09  # a jump of a whole message's move in one frame


def test_delay_settles_near_the_gap_and_stays_in_bounds(page):
    steady = page.evaluate(RUN, [0.1, 0.0, 0.05, 6, None])["delay"]
    shaky = page.evaluate(RUN, [0.1, 0.15, 0.05, 6, None])["delay"]
    assert 0.09 < steady < 0.14, steady
    assert shaky > steady
    assert shaky <= 0.25
    fast = page.evaluate(RUN, [0.02, 0.0, 0.05, 6, None])["delay"]
    assert fast >= 0.06 - 1e-9


def test_halfway_between_two_spots_is_their_blend(page):
    v = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x', 'y'], minDelay: 0.1, maxDelay: 0.1 });
      tr.push(0, { x: 0, y: 10 }, 50); tr.push(0.1, { x: 2, y: 20 }, 50.1);
      return tr.at(50.15);  // drawn 0.1 s back: halfway
    }""")
    assert v["x"] == pytest.approx(1, abs=0.01) and v["y"] == pytest.approx(15, abs=0.1)


def test_an_angle_goes_the_short_way_round(page):
    a = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x', 'a'], angles: ['a'], minDelay: 0.1, maxDelay: 0.1 });
      tr.push(0, { x: 0, a: 3.1 }, 50); tr.push(0.1, { x: 0, a: -3.1 }, 50.1);
      return tr.at(50.15).a;
    }""")
    assert abs(abs(a) - 3.1416) < 0.01  # through pi, not through 0


def test_a_late_player_goes_on_a_moment_then_stops(page):
    xs = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x'], minDelay: 0.1, maxDelay: 0.1 });
      for (let i = 0; i <= 10; i++) tr.push(i * 0.1, { x: i * 0.1 }, 50 + i * 0.1);
      const xs = []; for (let f = 0; f <= 120; f++) xs.push(tr.at(51 + f / 60).x);
      return xs;
    }""")
    # The newest spot (x 1.0) is drawn 0.1 s after it came; it keeps going 0.25 s past it, then holds.
    assert max(xs) == pytest.approx(1.25, abs=0.02)
    assert xs[-1] == xs[-30]


def test_a_jump_and_a_snap_are_drawn_at_once(page):
    r = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x', 'y'], jump: 5 });
      for (let i = 0; i < 10; i++) { tr.push(i * 0.1, { x: i * 0.1, y: 0 }, 50 + i * 0.1); tr.at(50 + i * 0.1); }
      tr.push(1.0, { x: 50, y: 0 }, 51.0);
      const jumped = tr.at(51.01).x;
      tr.snap(1.1, { x: -20, y: 3 }, 51.1);
      const snapped = { ...tr.at(51.11) };
      tr.push(0.0, { x: 7, y: 7 }, 51.2);  // the sender's clock went back (its page reloaded)
      const restarted = { ...tr.at(51.21) };
      return { jumped, snapped, restarted };
    }""")
    assert r["jumped"] == 50
    assert r["snapped"] == {"x": -20, "y": 3}
    assert r["restarted"] == {"x": 7, "y": 7}


def test_a_repeated_spot_is_heard_once_and_no_spot_draws_nothing(page):
    r = page.evaluate("""() => {
      const tr = AiPelitSulava.track();
      const none = tr.at(50);
      tr.push(0, { x: 0, y: 0 }, 50); tr.push(0.1, { x: 1, y: 0 }, 50.1); tr.push(0.1, { x: 9, y: 9 }, 50.15);
      return { none, size: tr.size() };
    }""")
    assert r == {"none": None, "size": 2}


def test_a_sleeping_page_wakes_on_the_newest_spot(page):
    x = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x'], minDelay: 0.1, maxDelay: 0.1 });
      for (let i = 0; i <= 10; i++) { tr.push(i * 0.1, { x: i }, 50 + i * 0.1); tr.at(50 + i * 0.1); }
      for (let i = 11; i <= 60; i++) tr.push(i * 0.1, { x: i }, 50 + i * 0.1);  // hidden: no frames
      return tr.at(56.0).x;
    }""")
    assert x == pytest.approx(59, abs=0.2)


def test_a_wrong_guess_is_drawn_away_without_a_jump(page):
    """A player standing still starts to walk (4 m/s) while their spots come late: the library goes on past the
    newest spot at the speed it last knew (none), and the spot that then comes says they were ahead. The
    difference (0.6 m) is drawn away over a tenth of a second, not in one frame."""
    st = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x'], minDelay: 0.1, maxDelay: 0.1 });
      const msgs = [];
      for (let i = 0; i <= 40; i++) {
        const t = i * 0.1, x = t < 1 ? 0 : (t - 1) * 4;
        msgs.push({ t, x, at: 50 + t + (i === 11 ? 0.15 : i === 12 ? 0.05 : 0) });  // two spots come late, together
      }
      msgs.sort((a, b) => a.at - b.at);
      const xs = []; let k = 0;
      for (let f = 0; f < 240; f++) {
        const now = 50 + f / 60;
        while (k < msgs.length && msgs[k].at <= now) { const m = msgs[k++]; tr.push(m.t, { x: m.x }, m.at); }
        xs.push(tr.at(now).x);
      }
      return xs.map((x, i) => i ? x - xs[i - 1] : 0);
    }""")
    walk = 4 / 60
    assert max(st) < 0.25, max(st)  # drawn in one frame, the 0.6 m would be a leap
    assert sum(1 for s in st if s > 1.2 * walk) >= 4  # over a few frames
    assert min(st) > -1e-9


def test_a_page_that_slept_with_no_new_spot_waits_at_the_newest(page):
    """No spot came while the page was hidden: it wakes with the player at the newest spot, not 0.25 s on
    past it, and goes on from there once a spot comes."""
    r = page.evaluate("""() => {
      const tr = AiPelitSulava.track({ keys: ['x'], minDelay: 0.1, maxDelay: 0.1 });
      for (let i = 0; i <= 10; i++) { tr.push(i * 0.1, { x: i }, 50 + i * 0.1); tr.at(50 + i * 0.1); }
      const woke = [tr.at(55.0).x, tr.at(55.02).x];
      tr.push(5.0, { x: 50 }, 55.03);
      return { woke, after: tr.at(55.05).x };
    }""")
    assert r["woke"] == [10, 10]
    assert 10 < r["after"] <= 50
