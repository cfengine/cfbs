import os

from cfbs.utils import write_json
from cfbs.masterfiles.analyze import (
    finalize_vcf,
    initialize_vcf,
    versions_checksums_files,
)


def generate_vcf_download(dir_path, downloaded_versions):
    """`dir_path`: the path of the directory containing masterfiles versions
                   subdirectories in the form `dir_path/x.y.z/tarball/`

    The `tarball` folder should contain the `masterfiles` folder (older
    tarballs also have a `modules` folder alongside the `masterfiles` folder).
    """
    versions_dict, checksums_dict, files_dict = initialize_vcf()

    for version in downloaded_versions:
        files_dir_path = os.path.join(dir_path, version, "tarball")

        versions_dict, checksums_dict, files_dict = versions_checksums_files(
            files_dir_path, version, versions_dict, checksums_dict, files_dict
        )

    versions_dict, checksums_dict, files_dict = finalize_vcf(
        versions_dict, checksums_dict, files_dict
    )

    write_json("versions.json", versions_dict)
    write_json("checksums.json", checksums_dict)
    write_json("files.json", files_dict)
