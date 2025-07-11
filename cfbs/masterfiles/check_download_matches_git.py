import os
from collections import OrderedDict

from cfbs.masterfiles.analyze import version_as_comparable_list
from cfbs.utils import dict_diff, read_json, CFBSExitError, write_json


def check_download_matches_git(versions):
    """Check that the downloadable files match the git files.

    This can be used to monitor / detect if something has been changed, accidentally or maliciously.

    Generates a `differences-*.txt` file for each version.
    """
    assert os.path.isfile("versions.json")
    assert os.path.isfile("versions-git.json")

    download_versions_dict = read_json("versions.json")
    git_versions_dict = read_json("versions-git.json")

    assert download_versions_dict is not None
    assert git_versions_dict is not None

    diffs_dict = {"differences": {}}

    nonmatching_versions = []
    extraneous_count = 0
    differing_count = 0

    for version in versions:
        dl_version_files_dict = download_versions_dict["versions"][version]
        git_version_files_dict = git_versions_dict["versions"][version]

        # normalize downloaded version dictionary filepaths
        # necessary because the downloaded version and git version dictionaries have filepaths of different forms
        new_download_dict = {}
        for key, value in dl_version_files_dict.items():
            if key.startswith("masterfiles/"):
                key = key[12:]
            new_download_dict[key] = value
        dl_version_files_dict = new_download_dict

        version_diffs_dict = {}
        version_diffs_dict["files_only_in_downloads"] = []
        version_diffs_dict["files_only_in_git"] = []
        version_diffs_dict["files_with_different_content"] = []

        only_dl, only_git, value_diff = dict_diff(
            dl_version_files_dict, git_version_files_dict
        )

        for filepath in only_dl:
            version_diffs_dict["files_only_in_downloads"].append(filepath)
        for filepath in only_git:
            version_diffs_dict["files_only_in_git"].append(filepath)
        for filepath, _, _ in value_diff:
            version_diffs_dict["files_with_different_content"].append(filepath)

        diffs_dict["differences"][version] = version_diffs_dict

        if len(only_dl) > 0 or len(value_diff) > 0:
            nonmatching_versions.append(version)
            extraneous_count += len(only_dl)
            differing_count += len(value_diff)

    nonmatching_versions.sort(key=lambda v: version_as_comparable_list(v), reverse=True)

    # fully sort differences.json:
    working_dict = diffs_dict["differences"]
    # sort filepaths of each version, alphabetically
    for k in working_dict.keys():
        working_dict[k]["files_only_in_downloads"].sort()
        working_dict[k]["files_only_in_git"].sort()
        working_dict[k]["files_with_different_content"].sort()
    # sort version numbers, in decreasing order
    diffs_dict["differences"] = OrderedDict(
        sorted(
            working_dict.items(),
            key=lambda p: version_as_comparable_list(p[0]),
            reverse=True,
        )
    )

    write_json("differences.json", diffs_dict)

    if len(nonmatching_versions) > 0:
        raise CFBSExitError(
            "The masterfiles downloaded from github.com and cfengine.com do not match - found "
            + str(extraneous_count)
            + " extraneous file"
            + ("" if extraneous_count == 1 else "s")
            + " and "
            + str(differing_count)
            + " differing file"
            + ("" if differing_count == 1 else "s")
            + " across "
            + str(len(nonmatching_versions))
            + " version"
            + ("" if len(nonmatching_versions) == 1 else "s")
            + " ("
            + ", ".join(nonmatching_versions)
            + "). See ./differences.json"
        )
