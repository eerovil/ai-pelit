"""The head's pose through a jump that flies (#469, helper check of #470).

After a flight Korkeushyppy and Seiväshyppy draw the jumper with their flight code, which turned
the head only for the air. On the mat it now cheers after a clear and drops its chin after a miss
(AiPelitOutfits.headPose 'cheer' / 'land'), as on the attempts that never left the ground.
"""

import pytest

from conftest import ROOT

pytestmark = pytest.mark.games("korkeushyppy", "seivashyppy")

SPY = """() => {
  window.poses = [];
  const P = AiPelitOutfits.headPose;
  AiPelitOutfits.headPose = (st, t) => { poses.push(th.phase + ':' + st); return P(st, t); };
}"""


def open_game(site, context, url):
    site.build(ROOT / "games")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(site.url + url)
    page.click("#go")
    page.wait_for_function("th && th.mine", timeout=8000)
    page.evaluate("th.t = BOARD_T; step(0.001)")
    page.evaluate(SPY)
    return page, errors


def landed_poses(page):
    return sorted({p.split(":")[1] for p in page.evaluate("poses") if p.startswith("land:")})


@pytest.mark.parametrize("arch,bar,ok", [((0.35, 0.55), 1.5, True), ((None, None), 2.2, False)])
def test_the_high_jumper_cheers_or_drops_its_chin_on_the_mat(site, context, arch, bar, ok):
    page, errors = open_game(site, context, "games/korkeushyppy/v17/")
    page.evaluate("""([a, k, bar]) => {
      th.bar = bar; th.phase = 'run'; th.x = -1.1; th.v = 12; takeOff(1.1, 12); th.f.archT = a; th.f.kickT = k;
      for (let i = 0; i < 2000 && !(th.phase === 'land' && th.t > 0.6); i++) { step(1 / 60); draw(); }
    }""", [*arch, bar])
    assert page.evaluate("[th.phase, !!th.f, th.mark]") == ["land", True, "O" if ok else "X"]
    assert landed_poses(page) == (["cheer"] if ok else ["land"])
    assert errors == []


def test_the_vaulter_lifts_its_chin_on_the_pole_and_cheers_or_drops_it_on_the_mat(site, context):
    seen = {}
    for v, tau in ((10, 1.8), (8, 1.8), (6, 1.8), (10, 1.2), (10, 2.4)):
        page, errors = open_game(site, context, "games/seivashyppy/v18/")
        res = page.evaluate("""([v, tau]) => {
          th.phase = 'run'; th.x = TAKEOFF; th.v = v; plantNow(TAKEOFF, v); th.held = true;
          for (let i = 0; i < 3000 && !(th.phase === 'land' && th.t > 0.6); i++) {
            if (th.phase === 'pole' && th.tau >= tau) letGoPole();
            step(1 / 60); draw();
            if (th.phase !== 'pole' && th.phase !== 'fly' && th.phase !== 'land') break;
          }
          return th.phase === 'land' && th.fly ? th.res : null;
        }""", [v, tau])
        if res is None:
            page.close()
            continue
        poses = page.evaluate("poses")
        assert any(p == "pole:takeoff" for p in poses)
        assert any(p == "fly:air" for p in poses)
        assert landed_poses(page) == (["cheer"] if res == "O" else ["land"])
        assert errors == []
        seen[res] = (v, tau)
        page.close()
    assert set(seen) == {"O", "X"}, seen
