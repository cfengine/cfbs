# TODO document `cfbs generate-release-information`
# this command uses several extra deps compared to the rest of cfbs
import sys
from pathlib import Path

from masterfiles.download_all_versions import download_all_versions_enterprise
from masterfiles.check_tarball_checksums import check_tarball_checksums
from masterfiles.generate_vcf_download import generate_vcf_download
from masterfiles.generate_vcf_git_checkout import generate_vcf_git_checkout
from masterfiles.check_download_matches_git import check_download_matches_git

ENTERPRISE_PATH = Path("./enterprise")


def generate_release_information():
    # only needs to be done once (although changes could happen afterwards), and silly to do if already have access to hosted files
    downloaded_versions, reported_checksums = download_all_versions_enterprise()
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

    check_download_matches_git(downloaded_versions)
    # TODO automatic analysis of the difference-*.txts
