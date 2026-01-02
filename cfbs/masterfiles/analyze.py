from collections import OrderedDict
import os

from cfbs.utils import dict_sorted_by_key, file_sha256, version_as_comparable_list

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
