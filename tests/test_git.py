from cfbs.git import ls_remote
from cfbs.utils import is_a_commit_hash


def test_ls_remote():
    commit = ls_remote("https://github.com/cfengine/masterfiles.git", "master")
    print(commit)
    assert commit is not None
    assert is_a_commit_hash(commit)
