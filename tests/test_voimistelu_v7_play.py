"""Voimistelu v7: every new task level (21–32) is played through to a pass with the controls alone (#133).

Only what a finger does: hold (pull in on the bar, tuck in the air), a flick up (`release()`) and a sideways
flick (`twist()`). For each move the player tries release points and tuck lengths until one works, as a
player would; the game's own `step()` runs the physics and `finish()` judges the level.
"""

import pytest

from conftest import ROOT

PLAY = r"""
window.PLAY = {
  dt: 1 / 240,
  TW: [[], [[0.08, 1]], [[0.08, 1], [0.35, 1]], [[0.08, 1], [0.35, 1], [0.6, 1]]],
  snap() { return structuredClone({ mode, bar, th, Lb, s, pk, tau, tauT, facing, arm, armT, armK, jt, flight, lastCross,
    elements, deductions, popups, link, pir, pos, vel, phi, L, hold, touch }); },
  load(o) { ({ mode, bar, th, Lb, s, pk, tau, tauT, facing, arm, armT, armK, jt, flight, lastCross, elements, deductions,
    popups, link, pir, pos, vel, phi, L, hold, touch } = structuredClone(o)); },
  // The pumping finger: down through the bottom of the swing, up at its ends.
  swing() { hold = Math.abs(wrap(th)) < 1; step(this.dt); },
  pumpUntil(done, T = 40) { for (let t = 0; t < T; t += this.dt) { if (done()) return true; this.swing(); } return false; },
  giants() { return elements.filter(e => e.name.startsWith('Jättikierto')); },
  // Swing on until the body passes angle a about the bar, then flick up.
  releaseAt(a, T) {
    for (let t = 0; t < T; t += this.dt) {
      const prev = th; this.swing();
      if (mode !== 'bar') return false;
      if (!jt && Math.floor((prev - a) / TAU) !== Math.floor((th - a) / TAU)) { hold = false; release(); return true; }
    }
    return false;
  },
  // In the air: hold a finger (tuck) for t2 seconds, flick sideways at the given times.
  fly(t2, twists) {
    let t = 0; const tw = twists.slice();
    while (mode === 'air' && t < 4) { hold = t < t2; while (tw.length && t >= tw[0][0]) twist(tw.shift()[1]); step(this.dt); t += this.dt; }
    hold = false; return mode;
  },
  // Tries release points and tuck lengths until the flight ends as wanted; keeps that try.
  attempt(ok, T) {
    const base = this.snap();
    for (const tw of this.TW) for (let t2 = 0; t2 <= 1.31; t2 += 0.1) for (let a = 0; a < TAU; a += 0.08) {
      this.load(base);
      const n0 = elements.length;
      if (!this.releaseAt(a, T)) continue;
      const m = this.fly(t2, tw);
      if (ok(m, elements.slice(n0).map(e => e.name))) return true;
    }
    this.load(base); return false;
  },
  catchMove(want, T = 6) { return this.attempt((m, names) => m === 'bar' && names.some(want), T); },
  // A dismount to the feet, and what the landing must be; then the score board.
  dismount(want = () => true) {
    const ok = this.attempt(m => m === 'land' && !touch.fall && want(touch), 6);
    for (let t = 0; t < 3 && mode !== 'result'; t += 1 / 60) step(1 / 60);
    return ok && mode === 'result';
  },
  // Swing up to the handstand and flick sideways there.
  handstand() { return this.pumpUntil(() => !jt && Math.abs(wrap(th - Math.PI)) < 0.3); },
};
"""

# Each level's routine, as the player's actions; each step must succeed.
ROUTINES = {
    21: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.handstand() && (twist(1), true)
           && PLAY.pumpUntil(() => new Set(PLAY.giants().map(e => e.name)).size >= 2) && PLAY.dismount()""",
    22: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Tkatchev')
           && PLAY.catchMove(n => n === 'Jäger') && PLAY.dismount()""",
    23: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.handstand()
           && (twist(1), step(1 / 60), twist(1), true) && PLAY.dismount()""",
    24: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Tkatchev')
           && PLAY.catchMove(n => n.startsWith('Yhdistelmä'), 3) && PLAY.dismount()""",
    25: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.dismount(t => t.saltos >= 2 && t.halves >= 2)""",
    26: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => DOWN.includes(n))
           && PLAY.pumpUntil(() => false, 6) !== null && PLAY.catchMove(n => UP.includes(n)) && PLAY.dismount()""",
    27: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Kolman') && PLAY.dismount()""",
    28: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.dismount(t => t.saltos >= 2 && t.stuck)""",
    29: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Tkatchev')
           && PLAY.catchMove(n => n === 'Jäger') && PLAY.catchMove(n => DOWN.includes(n)) && PLAY.dismount()""",
    30: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Tkatchev')
           && PLAY.catchMove(n => n === 'Yhdistelmä: Tkatchev + Tkatchev', 3)
           && PLAY.catchMove(n => n === 'Yhdistelmä: Tkatchev + Jäger', 3) && PLAY.dismount()""",
    31: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.catchMove(n => n === 'Tkatchev')
           && PLAY.catchMove(n => n === 'Yhdistelmä: Tkatchev + Kolman', 3) && PLAY.catchMove(n => n === 'Kovacs')
           && PLAY.catchMove(n => n === 'Pak-voltti') && PLAY.pumpUntil(() => false, 6) !== null
           && PLAY.catchMove(n => n === 'Shaposhnikova') && PLAY.dismount(t => t.saltos >= 2)""",
    32: """PLAY.pumpUntil(() => PLAY.giants().length >= 1) && PLAY.dismount(t => t.saltos >= 3 && t.stuck)""",
}


@pytest.mark.parametrize("size", [{"width": 360, "height": 740}, {"width": 740, "height": 360}])
def test_every_new_task_level_can_be_passed_with_the_controls(site, browser, size):
    site.build(ROOT / "games")
    ctx = browser.new_context(viewport=size, is_mobile=True, has_touch=True)
    ctx.add_init_script("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Testi'))")
    page = ctx.new_page()
    page.goto(f"{site.url}games/voimistelu/v7/")
    page.wait_for_function("S > 0")
    page.add_script_tag(content=PLAY)
    for n, routine in ROUTINES.items():
        played = page.evaluate(f"""() => {{ level = {n}; newRoutine();
          const done = !!({routine});
          return {{ done, mode, passed: result && result.passed, names: elements.map(e => e.name),
                    d: result && result.d, level }}; }}""")
        assert played["done"] and played["passed"], (n, played)
        assert played["level"] == n + 1, (n, played)
    ctx.close()
