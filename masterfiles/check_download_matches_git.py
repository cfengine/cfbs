# check that the downloadable files match the git files, mitigating a build system supply-chain attack
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

        for diff in list(dictdiffer.diff(download_version_dict, git_version_dict)):
            with open("differences/difference-" + version + ".txt", "w") as f:
                print(diff, file=f)
