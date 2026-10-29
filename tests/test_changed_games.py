"""Which tests a pull request runs (#37): a game's own tests only when the change touches that game."""

from conftest import changed_games, game_of_test_file


def test_a_change_inside_one_game_tests_only_that_game():
    assert changed_games(["games/hiihto/v3/index.html", "games/hiihto/game.json"]) == {"hiihto"}


def test_a_game_test_file_counts_as_its_game():
    assert changed_games(["tests/test_vauvan_syotto.py", "tests/test_voimistelu_v2.py"]) == {"vauvan-syotto", "voimistelu"}
    assert game_of_test_file("test_kirkkis_v2.py") == "kirkkis"
    assert game_of_test_file("test_site.py") is None


def test_docs_and_python_caches_alone_test_no_game():
    assert changed_games(["docs/diagrams/hiihto.md", "README.md", "tests/__pycache__/conftest.cpython-312.pyc"]) == set()


def test_anything_shared_tests_every_game():
    for shared in ["public/scores.js", "scripts/build.py", "server/api.js", "tests/conftest.py",
                   "tests/test_site.py", ".github/workflows/ci.yml", "games/README"]:
        assert changed_games(["games/hiihto/v3/index.html", shared]) is None, shared


def test_when_git_cannot_say_every_game_is_tested():
    assert changed_games(None) is None


def selection(tmp_path, change: str) -> tuple[list[str], str]:
    """Collect a small repository's tests after `change`, as CI does on a pull request."""
    import shutil
    import subprocess
    import sys

    from conftest import ROOT

    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "tests" / "conftest.py", repo / "tests")
    shutil.copy(ROOT / "scripts" / "build.py", repo / "scripts")
    for slug in ("alpha", "beta-gamma"):
        (repo / "games" / slug / "v1").mkdir(parents=True)
        (repo / "games" / slug / "v1" / "index.html").write_text("<p>v1</p>")
    tests = {
        "test_alpha.py": "def test_alpha(): pass\n",
        "test_beta_gamma_v2.py": "def test_beta(): pass\n",
        "test_shared.py": "import pytest\n\n"
                          "@pytest.mark.games('alpha')\ndef test_shared_alpha(): pass\n\n"
                          "@pytest.mark.games('beta-gamma')\ndef test_shared_beta(): pass\n\n"
                          "def test_shared_any(): pass\n",
    }
    for name, body in tests.items():
        (repo / "tests" / name).write_text(body)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], cwd=repo, check=True)
    subprocess.run([*git, "add", "-A"], cwd=repo, check=True)
    subprocess.run([*git, "commit", "-qm", "base"], cwd=repo, check=True)
    (repo / change).parent.mkdir(parents=True, exist_ok=True)
    with open(repo / change, "a") as f:
        f.write("\n")
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--co", "--changed-since", "HEAD"],
                         cwd=repo, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    kept = sorted(line.split("::")[1] for line in run.stdout.splitlines() if "::" in line)
    return kept, run.stdout


def test_a_pull_request_on_one_game_keeps_its_tests_and_the_shared_ones(tmp_path):
    kept, out = selection(tmp_path, "games/alpha/v1/index.html")
    assert kept == ["test_alpha", "test_shared_alpha", "test_shared_any"]
    assert "games changed: alpha; other games' own tests were skipped" in out


def test_file_names_with_spaces_or_letters_like_a_still_count_as_their_game(tmp_path):
    for name in ("games/alpha/v1/iso ääni.mp3", "games/alpha/v1/ääni.mp3"):
        kept, _ = selection(tmp_path / str(len(name)), name)
        assert kept == ["test_alpha", "test_shared_alpha", "test_shared_any"], name


def test_a_pull_request_on_a_game_s_tests_keeps_that_game(tmp_path):
    kept, _ = selection(tmp_path, "tests/test_beta_gamma_v2.py")
    assert kept == ["test_beta", "test_shared_any", "test_shared_beta"]


def test_a_pull_request_on_a_shared_file_keeps_every_test(tmp_path):
    kept, out = selection(tmp_path, "public/scores.js")
    assert kept == ["test_alpha", "test_beta", "test_shared_alpha", "test_shared_any", "test_shared_beta"]
    assert "tested every game" in out
