"""Tikanheitto v8 (#539): the thrower's sight glides on the other phones (lib/sulava-1, as in #480).

Through v7 each phone drew the friend's sight straight at the newest 'a' spot, ten times a second,
so it jumped. Here the thrower's hand is held still (no sway) while a frame-by-frame script slides
its sight across the board at an even speed; the watching phone records every spot it draws.
"""

from test_tikka_v8 import room, start

# Records each sight the watching phone draws from a friend's track: [ms, x].
SPY = """() => {
  window.drawn = [];
  const make = AiPelitSulava.track;
  AiPelitSulava.track = o => {
    const tr = make(o), at = tr.at;
    tr.at = a => { const r = at(a); if (r) drawn.push([performance.now(), r.x]); return r; };
    return tr;
  };
}"""

# The thrower holds a finger down with a still hand and slides the sight 60 mm/s for 2.5 s.
SLIDE = """() => new Promise(done => {
  HAND.shaky = 0; HAND.steady = 0; HAND.tiring = 0;
  aim = { x: -80, y: 0 };
  hold = { id: 99, lx: 0, ly: 0, t: 0.5 };
  const t0 = performance.now();
  (function go() {
    const k = (performance.now() - t0) / 1000;
    aim.x = -80 + 60 * Math.min(k, 2.5);
    if (k < 2.5) requestAnimationFrame(go); else done();
  })();
})"""


def steps(page):
    """How far the drawn sight moved each frame, in the second half of the slide (mm)."""
    drawn = page.evaluate("drawn")
    xs = [x for _, x in drawn[len(drawn) // 2:]]
    return [b - a for a, b in zip(xs, xs[1:])]


def check_glides(thrower, watcher):
    watcher.evaluate(SPY)
    thrower.evaluate(SLIDE)
    moves = steps(watcher)
    assert len(moves) > 40, moves
    # 60 mm/s is 1 mm a frame at 60 frames a second. Jumping to each 'a' spot ten times a second
    # draws about 6 mm once and nothing on the five frames between.
    assert max(moves) < 3.5, moves
    assert sum(1 for d in moves if abs(d) < 0.05) < len(moves) / 5, moves
    # It is a moment behind, not far off: by the end it is nearly where the thrower aims.
    last = watcher.evaluate("drawn[drawn.length - 1][1]")
    assert 40 < last <= 70.5, last
    thrower.evaluate("hold = null")


def test_a_friends_sight_glides_on_the_guest_and_on_the_host(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, guest = pages
    start(pages)
    # The host throws: the guest draws its sight from the host's 'a' messages.
    host.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    check_glides(host, guest)
    # Aino's turn: the host draws her sight from what she sends, and passes it on unchanged.
    host.evaluate("() => { for (let i = 0; i < 3; i++) { release(0, 0); while (flying) step(1 / 60); } }")
    guest.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    check_glides(guest, host)
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_each_dart_starts_a_new_glide(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino"])
    host, guest = pages
    start(pages)
    # Aino's turn: the host watches her sight, and its own throwAt() of her dart drops the track.
    host.evaluate("() => { for (let i = 0; i < 3; i++) { release(0, 0); while (flying) step(1 / 60); } }")
    guest.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    host.evaluate(SPY)
    guest.evaluate("() => { HAND.shaky = 0; HAND.steady = 0; HAND.tiring = 0; aim = { x: -80, y: 0 }; hold = { id: 99, lx: 0, ly: 0, t: 0.5 }; }")
    host.wait_for_function("seen && seen.size() > 2", timeout=5000)
    guest.evaluate("() => { hold = null; release(-80, 0); aim = { x: 80, y: 0 }; }")
    host.wait_for_function("turnDarts.length === 1 && seen === null", timeout=5000)
    host.evaluate("drawn.splice(0)")
    guest.evaluate("hold = { id: 99, lx: 0, ly: 0, t: 0.5 }")
    host.wait_for_function("drawn.length > 0", timeout=5000)
    # The next dart's first sight is drawn where it is, not on a glide from -80.
    assert host.evaluate("drawn[0][1]") > 75
    for p in pages:
        assert p.errors == []
        p.context.close()


def test_the_computer_taking_a_turn_starts_a_new_track(site, browser):
    relay, pages = room(site, browser, ["Eero", "Aino", "Ville"])
    host, aino, ville = pages
    start(pages)
    host.evaluate("() => { for (let i = 0; i < 3; i++) { release(0, 0); while (flying) step(1 / 60); } }")
    aino.wait_for_function("mine() && !banner && !flying && dartsLeft === 3", timeout=8000)
    aino.evaluate("() => { HAND.shaky = 0; HAND.steady = 0; HAND.tiring = 0; aim = { x: -80, y: 0 }; hold = { id: 99, lx: 0, ly: 0, t: 0.5 }; }")
    ville.wait_for_function("seen && seen.size() > 2", timeout=5000)
    # The host's computer sends for the same turn: Ville's phone starts a new track for it.
    aino.evaluate("hold = null")
    host.evaluate("R.send({ t: 'a', round: net.round, x: 50, y: 0, s: stamp(), w: R.me })")
    ville.wait_for_function("seen && seen.size() === 1", timeout=5000)
    assert ville.evaluate("seenBy") == host.evaluate("R.me")
    for p in pages:
        assert p.errors == []
        p.context.close()
