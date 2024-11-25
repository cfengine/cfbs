import os

from cfbs.utils import dict_diff, read_json, user_error


def check_download_matches_git(versions):
    """Check that the downloadable files match the git files.

    This can be used to monitor / detect if something has been changed, accidentally or maliciously.

    Generates a `differences-*.txt` file for each version.
    """

    download_versions_dict = read_json("versions.json")
    git_versions_dict = read_json("versions-git.json")

    os.makedirs("differences", exist_ok=True)

    for version in versions:
        download_version_dict = download_versions_dict["versions"][version]["files"]
        git_version_dict = git_versions_dict["versions"][version]["files"]

        # normalize downloaded version dictionary filepaths
        # necessary because the downloaded version and git version dictionaries have filepaths of different forms
        new_download_dict = {}
        for key, value in download_version_dict.items():
            if key.startswith("masterfiles/"):
                key = key[12:]
            new_download_dict[key] = value
        download_version_dict = new_download_dict

        with open("differences/difference-" + version + ".txt", "w") as f:
            only_dl, only_git, value_diff = dict_diff(
                download_version_dict, git_version_dict
            )

            print("Files only in the downloaded version:", only_dl, file=f)
            print("Files only in the git version:", only_git, file=f)
            print("Files with different contents:", value_diff, file=f)

            if len(only_dl) > 0 or len(value_diff) > 0:
                user_error(
                    "Downloadable files of version "
                    + version
                    + " do not match git files"
                )
