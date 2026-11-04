"""moukari v8: no crowd noise, the loudest sounds quieter (#337). v11: the computer stops at 85 m (#404)."""

from test_hiljaiset_aanet import opens_and_plays_with_the_quiet_library, real  # noqa: F401

URL = "games/moukari/v11"


def test_it_opens_and_plays_with_the_quiet_library(real, context):
    opens_and_plays_with_the_quiet_library(real, context, URL)


from test_hiljaiset_aanet import cheer_is_quiet  # noqa: E402


def test_the_cheer_chime_is_quiet():
    # #355: Eero found the cheer's chime too loud.
    cheer_is_quiet("games/moukari/v11")


def test_the_computer_never_throws_past_85_m(real, context):
    # #404: the computer's throw had no limit, and at the top levels it beat what a player can reach.
    page = context.new_page()
    page.goto(f"{real.url}{URL}/")
    page.wait_for_function("typeof cpuMark === 'function'")
    marks = page.evaluate("Array.from({ length: 20000 }, () => cpuMark({ skill: 81.5 }))")
    good = [m for m in marks if m >= 0]
    assert max(good) <= 85
    assert max(good) > 84                       # it still reaches the top
    assert len(set(good)) > 100                 # drawn again, not cut to one result
    assert 0.1 < marks.count(-1) / len(marks) < 0.18   # fouls as before
    # Lower down nothing changes: the throw scatters round the thrower's skill.
    low = [m for m in page.evaluate("Array.from({ length: 5000 }, () => cpuMark({ skill: 50 }))") if m >= 0]
    assert 49 < sum(low) / len(low) < 51
