# TODO document `cfbs generate-release-information`
# it generates the .json data files in the cwd
import sys
from pathlib import Path

from masterfiles.download_all_versions import download_all_versions_enterprise
from masterfiles.check_tarball_checksums import check_tarball_checksums
from masterfiles.generate_vcf_download import generate_vcf_download
from masterfiles.generate_vcf_git_checkout import generate_vcf_git_checkout

# commented out for now as this adds an extra dependency in its current state (dictdiffer)
# from masterfiles.check_download_matches_git import check_download_matches_git

ENTERPRISE_PATH = Path("./enterprise")


def generate_release_information():
    downloaded_versions, reported_checksums = download_all_versions_enterprise()
    # TODO Community coverage:
    # downloaded_versions, reported_checksums = download_all_versions_community()

    # Enterprise 3.9.2 is downloaded but there is no reported checksum, so both args are necessary
    if check_tarball_checksums(
        ENTERPRISE_PATH, downloaded_versions, reported_checksums
    ):
        print("Every checksum matches")
    else:
        print("Checksums differ!")
        sys.exit(1)

    generate_vcf_download(ENTERPRISE_PATH, downloaded_versions)
    generate_vcf_git_checkout(downloaded_versions)

    # TODO automatic analysis of the difference between downloadable MPF data and git MPF data
    # in its current state, this generates differences-*.txt files for each version
    # check_download_matches_git(downloaded_versions)
