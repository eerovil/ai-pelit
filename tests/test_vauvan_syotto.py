"""Vauvan syöttäminen in a phone-sized Chromium, driven through the game's own touch and step()."""

from conftest import ROOT

# Runs the game for `s` seconds in small steps, synchronously, so no result hangs on frame timing.
RUN = "s => { for (let i = 0; i < s * 50; i++) step(0.02); }"

# Lifts the spoon from the bowl and lets go with its bowl end at the point (px, py).
DRAG = """([px, py]) => {
  down(G.bowl.x, G.bowl.y); move(px, py + TIP); up(px, py + TIP);
}"""

# Feeds one spoonful as soon as the mouth opens, with a happy baby that never spits.
FEED = """() => {
  mood = 100;
  for (let i = 0; i < 2000 && !(baby.act === 'open' && baby.mouth > 0.8); i++) step(0.02);
  const m = mouthPos();
  down(G.bowl.x, G.bowl.y); move(m.x, m.y + TIP); up(m.x, m.y + TIP);
}"""


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(f"{site.url}games/vauvan-syotto/v1/")
    page.click("#go")
    assert page.evaluate("state") == "play"
    return page


def test_the_baby_drops_the_spoon_it_is_given(site, context):
    page = start(site, context)
    page.evaluate("baby.act = 'idle'; baby.t = 0; baby.dur = 99")
    page.evaluate(DRAG, page.evaluate("[hands()[1].x, hands()[1].y]"))
    assert page.evaluate("[spoon.where, baby.act]") == ["baby", "hold"]
    page.evaluate(RUN, 3.5)
    assert page.evaluate("spoon.where") == "floor"
    # A tap on the dropped spoon washes it and puts it back by the bowl.
    page.evaluate("down(spoon.x, spoon.y); up(spoon.x, spoon.y)")
    assert page.evaluate("spoon.where") == "wash"
    page.evaluate(RUN, 1)
    assert page.evaluate("spoon.where") == "bowl"


def test_a_spoonful_at_a_shut_mouth_splats(site, context):
    page = start(site, context)
    page.evaluate("baby.act = 'turn'; baby.t = 0; baby.dur = 99; baby.turnTo = 0; baby.mouth = 0")
    page.evaluate(DRAG, page.evaluate("[mouthPos().x, mouthPos().y]"))
    assert page.evaluate("[tummy, misses, mood < 80]") == [0, 1, True]


def test_the_video_keeps_the_mouth_open_and_the_mood_up(site, context):
    page = start(site, context)
    btn = page.evaluate("G.btns[0]")
    page.evaluate("([px, py]) => { down(px, py); up(px, py); }", [btn["x"], btn["y"]])
    mood = page.evaluate("mood")
    page.evaluate(RUN, 4)
    assert page.evaluate("[videoT > 0, baby.mouth > 0.9, power.video]") == [True, True, 0]
    assert page.evaluate("mood") == mood


def test_a_full_tummy_wins_and_the_next_level_survives_a_reload(site, context):
    page = start(site, context)
    goal = page.evaluate("goal")
    for _ in range(goal):
        page.evaluate(FEED)
    assert page.evaluate("[tummy, state, misses]") == [goal, "win", 0]
    page.evaluate(RUN, 3)
    assert page.locator("#result").inner_text() == "Vauva on kylläinen!"
    page.reload()
    assert page.evaluate("[level, stars[1]]") == [2, 3]
