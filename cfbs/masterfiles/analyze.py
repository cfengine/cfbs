# TODO merge this with ENT-12099 branch cfbs analyze.py
import os

from cfbs.utils import file_sha256

IGNORED_PATH_COMPONENTS = [".git/", ".gitignore", ".gitattributes"]
# ignore a path iff it contains a component (single file or directory) from this list
# an element of this list should be just one component
# folders should end with '/', files should not
# TODO


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
