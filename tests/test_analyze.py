import os

from cfbs.analyze import checksums_files, mpf_normalized_path, possible_policyset_paths


# Executing the functions in particular working directories is necessary for testing relative paths.
class cwd:
    def __init__(self, new_wd):
        self.new_wd = os.path.expanduser(new_wd)

    def __enter__(self):
        self.old_wd = os.getcwd()
        os.chdir(self.new_wd)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_wd)


def ppp_scaffolded(path, masterfiles_dir="masterfiles"):
    """Testable variant of `cfbs.analyze.possible_policyset_paths` including prerequisite code."""
    is_parentpath = os.path.isdir(os.path.join(path, masterfiles_dir))

    _, files_dict = checksums_files(path, ignored_path_components=[".gitkeep"])
    files_dict = files_dict["files"]
    files_dict = {
        mpf_normalized_path(file, is_parentpath, masterfiles_dir): checksums
        for file, checksums in files_dict.items()
    }

    return possible_policyset_paths(path, masterfiles_dir, is_parentpath, files_dict)


def test_possible_policyset_paths():
    with cwd("tests/sample/analyze"):
        path = "."
        assert ppp_scaffolded(path) == ["parent_dir/mfiles"]
        assert ppp_scaffolded(path, "mfiles") == ["parent_dir/mfiles"]
        assert ppp_scaffolded(path, "wrong_dirname") == ["parent_dir/mfiles"]

        path = "parent_dir"
        assert ppp_scaffolded(path) == ["mfiles"]
        assert ppp_scaffolded(path, "mfiles") == ["mfiles"]
        assert ppp_scaffolded(path, "wrong_dirname") == ["mfiles"]

        path = "parent_dir/mfiles"
        assert ppp_scaffolded(path) == [""]
        assert ppp_scaffolded(path, "mfiles") == [""]
        assert ppp_scaffolded(path, "wrong_dirname") == [""]

        path = "parent_dir/mfiles/subdir"
        assert ppp_scaffolded(path) == [".."]
        assert ppp_scaffolded(path, "mfiles") == [".."]
        assert ppp_scaffolded(path, "wrong_dirname") == [".."]

    with cwd("tests/sample/analyze/parent_dir"):
        path = "."
        assert ppp_scaffolded(path) == ["mfiles"]
        assert ppp_scaffolded(path, "mfiles") == ["mfiles"]
        assert ppp_scaffolded(path, "wrong_dirname") == ["mfiles"]

        path = "mfiles"
        assert ppp_scaffolded(path) == [""]
        assert ppp_scaffolded(path, "mfiles") == [""]
        assert ppp_scaffolded(path, "wrong_dirname") == [""]

        path = "mfiles/subdir"
        assert ppp_scaffolded(path) == [".."]
        assert ppp_scaffolded(path, "mfiles") == [".."]
        assert ppp_scaffolded(path, "wrong_dirname") == [".."]

    with cwd("tests/sample/analyze/parent_dir/mfiles"):
        path = "."
        assert ppp_scaffolded(path) == [""]
        assert ppp_scaffolded(path, "mfiles") == [""]
        assert ppp_scaffolded(path, "wrong_dirname") == [""]

        path = "subdir"
        assert ppp_scaffolded(path) == [".."]
        assert ppp_scaffolded(path, "mfiles") == [".."]
        assert ppp_scaffolded(path, "wrong_dirname") == [".."]

    with cwd("tests/sample/analyze/parent_dir/mfiles/subdir"):
        path = "."
        assert ppp_scaffolded(path) == [".."]
        assert ppp_scaffolded(path, "mfiles") == [".."]
        assert ppp_scaffolded(path, "wrong_dirname") == [".."]
