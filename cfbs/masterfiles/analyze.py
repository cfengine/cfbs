from collections import OrderedDict
import os
from typing import Iterable, List

from cfbs.utils import dict_sorted_by_key, file_sha256

Version = str


def initialize_vcf():
    versions_dict = {"versions": {}}
    checksums_dict = {"checksums": {}}
    files_dict = {"files": {}}

    return versions_dict, checksums_dict, files_dict


def versions_checksums_files(
    files_dir_path, version, versions_dict, checksums_dict, files_dict
):
    for root, _, files in os.walk(files_dir_path):
        for name in files:
            full_relpath = os.path.join(root, name)
            tarball_relpath = os.path.relpath(full_relpath, files_dir_path)
            file_checksum = file_sha256(full_relpath)

            if version not in versions_dict["versions"]:
                versions_dict["versions"][version] = {}
            versions_dict["versions"][version][tarball_relpath] = file_checksum

            if file_checksum not in checksums_dict["checksums"]:
                checksums_dict["checksums"][file_checksum] = {}
            if tarball_relpath not in checksums_dict["checksums"][file_checksum]:
                checksums_dict["checksums"][file_checksum][tarball_relpath] = []
            checksums_dict["checksums"][file_checksum][tarball_relpath].append(version)

            if tarball_relpath not in files_dict["files"]:
                files_dict["files"][tarball_relpath] = {}
            if file_checksum not in files_dict["files"][tarball_relpath]:
                files_dict["files"][tarball_relpath][file_checksum] = []
            files_dict["files"][tarball_relpath][file_checksum].append(version)

    return versions_dict, checksums_dict, files_dict


def finalize_vcf(versions_dict, checksums_dict, files_dict):
    # explicitly sort VCF data to ensure determinism

    # checksums.json:
    working_dict = checksums_dict["checksums"]
    for c in working_dict.keys():
        for f in working_dict[c].keys():
            # sort each version list, descending
            working_dict[c][f] = sorted(
                working_dict[c][f],
                key=lambda v: version_as_comparable_list(v),
                reverse=True,
            )
        # sort filepaths, alphabetically
        working_dict[c] = dict_sorted_by_key(working_dict[c])
    # sort checksums
    checksums_dict["checksums"] = dict_sorted_by_key(working_dict)

    # files.json:
    working_dict = files_dict["files"]
    # sort each list, first by version descending, then by checksum
    for f in working_dict.keys():
        for c in working_dict[f].keys():
            # sort each version list, descending
            working_dict[f][c] = sorted(
                working_dict[f][c],
                key=lambda v: version_as_comparable_list(v),
                reverse=True,
            )
        # sort checksums
        working_dict[f] = dict_sorted_by_key(working_dict[f])
    # sort files, alphabetically
    files_dict["files"] = dict_sorted_by_key(working_dict)

    # versions.json:
    working_dict = versions_dict["versions"]
    # sort files of each version
    for v in working_dict.keys():
        working_dict[v] = dict_sorted_by_key(working_dict[v])
    # sort version numbers, in decreasing order
    versions_dict["versions"] = OrderedDict(
        sorted(
            working_dict.items(),
            key=lambda p: version_as_comparable_list(p[0]),
            reverse=True,
        )
    )

    return versions_dict, checksums_dict, files_dict


def version_as_comparable_list(version: str):
    """Also supports versions containing exactly one of `b` or `-`.

    Example of the version ordering: `3.24.0b1 < 3.24.0 < 3.24.0-1`.

    Examples:
    * `version_as_comparable_list("3.24.0b1")` is `[[3, 24, 0], [-1, 1]]`
    * `version_as_comparable_list("3.24.0-2")` is `[[3, 24, 0], [1, 2]]`
    * `version_as_comparable_list("3.24.x")` is `[[3, 24, 99999], [0, 0]]`"""
    if version == "master":
        version = "x"

    if "b" not in version:
        if "-" not in version:
            version += "|0.0"
    version = version.replace("x", "99999").replace("-", "|1.").replace("b", "|-1.")
    versionpair = version.split("|")
    versions_str = [versionpair[0].split("."), versionpair[1].split(".")]

    versions_int = [
        [int(s) for s in versions_str[0]],
        [int(s) for s in versions_str[1]],
    ]

    return versions_int


def version_as_comparable_list_negated(version):
    vcl = version_as_comparable_list(version)

    vcl[0] = [-x for x in vcl[0]]
    vcl[1] = [-x for x in vcl[1]]

    return vcl


def version_is_at_least(version, min_version):
    return min_version is None or (
        version_as_comparable_list(version) >= version_as_comparable_list(min_version)
    )


def sort_versions(versions: list, reverse: bool = True):
    """Sorts a list of versions, in descending order by default."""
    versions.sort(
        key=version_as_comparable_list,
        reverse=reverse,
    )


def highest_version(versions: Iterable[Version]):
    return max(versions, key=version_as_comparable_list, default=None)


def lowest_version(versions: Iterable[Version]):
    return min(versions, key=version_as_comparable_list, default=None)


def is_lower_version(version_a: Version, version_b: Version):
    """Returns `True` if and only if `version_a` is lower than `version_b`."""

    return version_as_comparable_list(version_a) < version_as_comparable_list(version_b)


def most_relevant_version(
    other_versions: List[Version], reference_version: Version
) -> Version:
    """
    The most relevant version is the highest version among older other versions,
    or if there are no older other versions, the lowest version among other versions.

    `other_versions` is assumed to be non-empty and not contain `reference_version`."""
    assert len(other_versions) > 0
    assert reference_version not in other_versions

    highest_other_version = highest_version(other_versions)
    lowest_other_version = lowest_version(other_versions)
    # Unfortunately, Pyright can not infer that these can't be `None` when `other_versions` is non-empty.
    assert highest_other_version is not None
    assert lowest_other_version is not None

    if is_lower_version(highest_other_version, reference_version):
        # all other versions are older
        return highest_other_version
    if is_lower_version(reference_version, lowest_other_version):
        # all other versions are newer
        return lowest_other_version
    # there are both older and newer versions
    lower_other_versions = [
        o_v for o_v in other_versions if is_lower_version(o_v, reference_version)
    ]
    highest_lower = highest_version(lower_other_versions)
    assert highest_lower is not None
    return highest_lower
