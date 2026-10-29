"""Piano v2: the score is kept after every finished song, and nine songs."""

from conftest import ROOT
from test_scores import fake  # noqa: F401  (the stand-in for /api/)

URL = "games/piano/v2/"


def start(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.click("#go")
    return page


def finish_song(page):
    page.evaluate("for (const n of cur.notes) n.hit = true; now = cur.end + 1; update(0.01)")


def test_nine_songs_each_on_all_four_lanes(site, context):
    page = start(site, context)
    assert page.evaluate("SONGS.length") == 9
    lanes = page.evaluate("SONGS.map((s, i) => [...new Set(levelNotes(i + 1).notes.map(n => n.lane))].sort())")
    assert lanes == [[0, 1, 2, 3]] * 9


def test_a_finished_song_saves_the_record_with_no_miss(site, context):
    page = start(site, context)
    page.evaluate("score = 2500")
    finish_song(page)
    assert page.evaluate("[state, level, lives]") == ["play", 2, 3]
    assert page.evaluate("localStorage.getItem('ai-pelit:piano:ennatys')") == "2500"
    assert page.evaluate("banner.note") == "Tulos tallennettu: 2500 p"


def test_a_finished_song_sends_the_score_to_the_list(site, context, fake):  # noqa: F811
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:_pelaaja:nimi', JSON.stringify('Aino'))")
    page.click("#go")
    page.evaluate("score = 1800")
    finish_song(page)
    page.wait_for_function("localStorage.getItem('ai-pelit:_tulokset:jono') === '{}'")
    [(key, row)] = fake.scores.items()
    assert key[:2] == ("piano", "main")
    assert row == {"score": 1800, "version": 2, "level": 2}


def test_the_first_nickname_question_holds_the_song_still(site, context, fake):  # noqa: F811
    page = start(site, context)
    page.evaluate("score = 900")
    finish_song(page)
    page.wait_for_selector("#ai-pelit-nimi")
    t = page.evaluate("now")
    page.wait_for_timeout(400)
    assert page.evaluate("now") == t
    page.click("#ai-pelit-tulokset button:has-text('Sulje')")
    page.wait_for_function(f"now > {t}")


def test_v1_saves_are_read(site, context):
    site.build(ROOT / "games")
    page = context.new_page()
    page.goto(site.url + URL)
    page.evaluate("localStorage.setItem('ai-pelit:piano:ennatys', '4321'); localStorage.setItem('ai-pelit:piano:taso', '3')")
    page.reload()
    assert "Ennätys 4321 pistettä · paras taso 3" in page.inner_text("#stats")
