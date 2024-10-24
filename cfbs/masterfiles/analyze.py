# TODO merge this with ENT-12099 branch cfbs analyze.py
import os

from cfbs.utils import dict_sorted_by_key, file_sha256

# TODO implement the ignoring
IGNORED_PATH_COMPONENTS = [".git/", ".gitignore", ".gitattributes"]
"""The analysis ignores paths described by this list. A path will be ignored if and only if it contains a component (a single file or directory, anywhere in the path) from this list.

Each element of this list should specify a singular component.
Folders should end with `/`, and files should not.
"""


def initialize_vcf():
    versions_dict = {"versions": {}}
    checksums_dict = {"checksums": {}}
    files_dict = {"files": {}}

    return versions_dict, checksums_dict, files_dict


def versions_checksums_files(
    files_dir_path, version, versions_dict, checksums_dict, files_dict
):
    for root, dirs, files in os.walk(files_dir_path):
        for name in files:
            full_relpath = os.path.join(root, name)
            tarball_relpath = os.path.relpath(full_relpath, files_dir_path)
            file_checksum = file_sha256(full_relpath)

            if version not in versions_dict["versions"]:
                versions_dict["versions"][version] = {}
            if "files" not in versions_dict["versions"][version]:
                versions_dict["versions"][version]["files"] = {}
            versions_dict["versions"][version]["files"][tarball_relpath] = file_checksum

            if not file_checksum in checksums_dict["checksums"]:
                checksums_dict["checksums"][file_checksum] = []
            checksums_dict["checksums"][file_checksum].append(
                {
                    "file": tarball_relpath,
                    "version": version,
                }
            )

            if not tarball_relpath in files_dict["files"]:
                files_dict["files"][tarball_relpath] = []
            files_dict["files"][tarball_relpath].append(
                {
                    "checksum": file_checksum,
                    "version": version,
                }
            )

    return versions_dict, checksums_dict, files_dict


def finalize_vcf(versions_dict, checksums_dict, files_dict):
    # sort checksums
    sorted_checksums_dict = dict_sorted_by_key(checksums_dict["checksums"])
    checksums_dict["checksums"] = sorted_checksums_dict

    # sort files, alphabetically
    sorted_files_dict = dict_sorted_by_key(files_dict["files"])
    files_dict["files"] = sorted_files_dict

    # sort files of each version
    working_dict = versions_dict["versions"]
    for k in working_dict.keys():
        sorted_dict = dict_sorted_by_key(working_dict[k]["files"])
        working_dict[k]["files"] = sorted_dict
    versions_dict["versions"] = working_dict

    return versions_dict, checksums_dict, files_dict
