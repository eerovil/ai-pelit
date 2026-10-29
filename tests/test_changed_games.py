"""Which tests a pull request runs (#37): a game's own tests only when the change touches that game."""

from conftest import changed_games, game_of_test_file


def test_a_change_inside_one_game_tests_only_that_game():
    assert changed_games(["games/hiihto/v3/index.html", "games/hiihto/game.json"]) == {"hiihto"}


def test_a_game_test_file_counts_as_its_game():
    assert changed_games(["tests/test_vauvan_syotto.py", "tests/test_voimistelu_v2.py"]) == {"vauvan-syotto", "voimistelu"}
    assert game_of_test_file("test_kirkkis_v2.py") == "kirkkis"
    assert game_of_test_file("test_site.py") is None


def test_docs_alone_test_no_game():
    assert changed_games(["docs/diagrams/hiihto.md", "README.md"]) == set()


def test_anything_shared_tests_every_game():
    for shared in ["public/scores.js", "scripts/build.py", "server/api.js", "tests/conftest.py",
                   "tests/test_site.py", ".github/workflows/ci.yml", "games/README"]:
        assert changed_games(["games/hiihto/v3/index.html", shared]) is None, shared


def test_when_git_cannot_say_every_game_is_tested():
    assert changed_games(None) is None
