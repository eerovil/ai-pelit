"""Which tests a pull request runs (#37): a game's own tests only when the change touches that game."""

from conftest import changed_games, changed_versions, game_of_test_file, is_3d, versions_of_test_file, whole_games_changed


def test_a_change_inside_one_game_tests_only_that_game():
    assert changed_games(["games/hiihto/v3/index.html", "games/hiihto/game.json"]) == {"hiihto"}


def test_a_game_test_file_counts_as_its_game():
    assert changed_games(["tests/test_vauvan_syotto.py", "tests/test_voimistelu_v2.py"]) == {"vauvan-syotto", "voimistelu"}
    assert game_of_test_file("test_kirkkis_v2.py") == "kirkkis"
    assert game_of_test_file("test_site.py") is None


def test_docs_and_python_caches_alone_test_no_game():
    assert changed_games(["docs/diagrams/hiihto.md", "README.md", "tests/__pycache__/conftest.cpython-312.pyc"]) == set()


def test_anything_shared_adds_no_game():
    # Never the full suite (#65): a shared change runs the shared tests only.
    for shared in ["public/scores.js", "scripts/build.py", "server/api.js", "tests/conftest.py",
                   "tests/test_site.py", ".github/workflows/ci.yml", "games/README"]:
        assert changed_games(["games/hiihto/v3/index.html", shared]) == {"hiihto"}, shared
        assert changed_games([shared]) == set(), shared


def test_a_change_names_the_versions_it_touches():
    paths = ["games/hiihto/v9/index.html", "games/hiihto/v9/a/b.js", "games/hiihto/game.json", "games/piano/v2/x"]
    assert changed_versions(paths) == {"hiihto": {9}, "piano": {2}}


def test_a_game_s_test_file_or_odd_file_runs_the_whole_game_but_its_game_json_and_thumbnail_do_not():
    # #116: a game's test files import each other's helpers, so changing one runs them all.
    assert whole_games_changed(["tests/test_kirkkis_v3.py", "games/piano/notes.js"]) == {"kirkkis", "piano"}
    assert whole_games_changed(["games/hiihto/game.json", "games/hiihto/thumb.webp", "games/hiihto/v9/index.html"]) == set()


def test_a_test_file_s_versions_come_from_its_name_and_the_folders_it_names(tmp_path):
    named = tmp_path / "test_hiihto_v8.py"
    named.write_text('URL = "games/hiihto/v8/"\nOLD = "games/hiihto/v7/"\nX = "games/piano/v3/"\n')
    assert versions_of_test_file(named, "hiihto") == {7, 8}
    plain = tmp_path / "test_areena.py"
    plain.write_text('URL = "games/areena/v3/"\n')
    assert versions_of_test_file(plain, "areena") == {3}
    neither = tmp_path / "test_orava.py"
    neither.write_text('page.goto(f"games/orava/v{v}/")\n')
    assert versions_of_test_file(neither, "orava") == set()


def test_a_3d_game_s_tests_run_alone_and_the_others_side_by_side():
    # #116: is_3d marks a test file `alone` when a version it tests loads lib/three.
    from conftest import ROOT
    assert is_3d(ROOT / "tests" / "test_hiihto_v9.py", "hiihto")
    assert not is_3d(ROOT / "tests" / "test_hiihto_v6.py", "hiihto")
    assert is_3d(ROOT / "tests" / "test_pallorata.py", "pallorata")
    assert not is_3d(ROOT / "tests" / "test_piano.py", "piano")


def test_when_git_cannot_say_no_game_is_tested():
    assert changed_games([]) == set()


def selection(tmp_path, *changes: str | tuple[str, str]) -> tuple[list[str], str]:
    """Collect a small repository's tests after `changes`, as CI does on a pull request."""
    import shutil
    import subprocess
    import sys

    from conftest import ROOT

    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "tests" / "conftest.py", repo / "tests")
    shutil.copy(ROOT / "scripts" / "build.py", repo / "scripts")
    shutil.copy(ROOT / "scripts" / "check_immutable.py", repo / "scripts")  # build.py reads WITHDRAWN from it
    for slug in ("alpha", "beta-gamma", "delta"):
        for v in (1, 2, 3):
            (repo / "games" / slug / f"v{v}").mkdir(parents=True)
            (repo / "games" / slug / f"v{v}" / "index.html").write_text(f"<p>v{v}</p>")
        (repo / "games" / slug / "game.json").write_text("{}")
    tests = {
        "test_alpha.py": "def test_alpha(): pass\n",
        "test_beta_gamma_v2.py": "def test_beta(): pass\n",
        # delta (#116): v1 by its folder, v2 by its name and v1 too, and one that names no version.
        "test_delta.py": "URL = 'games/delta/v1/'\ndef test_delta_v1(): pass\n",
        "test_delta_v2.py": "OLD = 'games/delta/v1/'\ndef test_delta_v2(): pass\n",
        "test_delta_any.py": "def test_delta_any(): pass\n",
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
    for change in changes:
        # A change is a path to touch, or (path, text) for a new file.
        change, text = change if isinstance(change, tuple) else (change, "\n")
        (repo / change).parent.mkdir(parents=True, exist_ok=True)
        with open(repo / change, "a") as f:
            f.write(text)
    run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--co", "--changed-since", "HEAD"],
                         cwd=repo, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    kept = sorted(line.split("::")[1] for line in run.stdout.splitlines() if "::" in line)
    return kept, run.stdout


def test_a_pull_request_on_one_game_keeps_its_tests_and_the_shared_ones(tmp_path):
    kept, out = selection(tmp_path, "games/alpha/v1/index.html")
    assert kept == ["test_alpha", "test_shared_alpha", "test_shared_any"]
    assert "games changed: alpha (v1); other games' and versions' own tests were skipped" in out


def test_file_names_with_spaces_or_letters_like_a_still_count_as_their_game(tmp_path):
    for name in ("games/alpha/v1/iso ääni.mp3", "games/alpha/v1/ääni.mp3"):
        kept, _ = selection(tmp_path / str(len(name)), name)
        assert kept == ["test_alpha", "test_shared_alpha", "test_shared_any"], name


def test_a_pull_request_on_a_game_s_tests_keeps_that_game(tmp_path):
    kept, _ = selection(tmp_path, "tests/test_beta_gamma_v2.py")
    assert kept == ["test_beta", "test_shared_any", "test_shared_beta"]


def test_a_pull_request_on_a_shared_file_keeps_only_the_shared_tests(tmp_path):
    kept, out = selection(tmp_path, "public/scores.js")
    assert kept == ["test_shared_any"]
    assert "games changed: none; other games' and versions' own tests were skipped" in out


def test_a_new_version_runs_only_its_own_tests_not_the_older_versions(tmp_path):
    kept, out = selection(tmp_path, "games/delta/v2/index.html")
    assert kept == ["test_delta_any", "test_delta_v2", "test_shared_any"]
    assert "games changed: delta (v2);" in out


def test_a_version_named_by_several_files_runs_them_all(tmp_path):
    kept, _ = selection(tmp_path, "games/delta/v1/index.html")
    assert kept == ["test_delta_any", "test_delta_v1", "test_delta_v2", "test_shared_any"]


def test_a_version_no_test_file_names_runs_all_of_its_game(tmp_path):
    kept, _ = selection(tmp_path, "games/delta/v3/index.html")
    assert kept == ["test_delta_any", "test_delta_v1", "test_delta_v2", "test_shared_any"]


def test_a_change_to_one_of_a_game_s_test_files_runs_all_of_them(tmp_path):
    kept, _ = selection(tmp_path, "tests/test_delta_v2.py")
    assert kept == ["test_delta_any", "test_delta_v1", "test_delta_v2", "test_shared_any"]


def test_a_new_version_with_its_own_new_test_file_runs_only_that_file(tmp_path):
    # As every new version comes: its folder and a new test file. The new file is imported by no
    # other test yet, so it does not run the game's older tests.
    kept, _ = selection(tmp_path, "games/delta/v4/index.html", ("tests/test_delta_v4.py", "def test_delta_v4(): pass\n"))
    assert kept == ["test_delta_any", "test_delta_v4", "test_shared_any"]


def test_only_game_json_or_the_thumbnail_runs_none_of_the_game_s_own_tests(tmp_path):
    kept, _ = selection(tmp_path, "games/delta/game.json", "games/delta/thumb.webp")
    assert kept == ["test_shared_any"]


def test_a_marked_shared_test_still_runs_for_any_change_to_its_game(tmp_path):
    kept, _ = selection(tmp_path, "games/alpha/game.json")
    assert kept == ["test_shared_alpha", "test_shared_any"]
