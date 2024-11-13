"""Check that the downloadable files match the git files.

This can be used to monitor / detect if something has been changed, accidentally or maliciously.
"""

import os
import dictdiffer

from cfbs.utils import read_json


def check_download_matches_git(versions):
    download_versions_dict = read_json("versions.json")
    git_versions_dict = read_json("versions-git.json")

    os.makedirs("differences", exist_ok=True)

    for version in versions:
        download_version_dict = download_versions_dict["versions"][version]["files"]
        git_version_dict = git_versions_dict["versions"][version]["files"]

        with open("differences/difference-" + version + ".txt", "w") as f:
            for diff in dictdiffer.diff(download_version_dict, git_version_dict):
                print(diff, file=f)
