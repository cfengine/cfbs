from cfbs.masterfiles.download_all_versions import download_all_versions
from cfbs.masterfiles.generate_vcf_download import generate_vcf_download
from cfbs.masterfiles.generate_vcf_git_checkout import generate_vcf_git_checkout
from cfbs.masterfiles.check_download_matches_git import check_download_matches_git
from cfbs.utils import immediate_subdirectories

DOWNLOAD_PATH = "downloaded_masterfiles"


def generate_release_information(omit_download=False):
    if not omit_download:
        print("Downloading masterfiles...")

        downloaded_versions = download_all_versions(DOWNLOAD_PATH)

        print("Download finished. Every reported checksum matches.")
    else:
        downloaded_versions = immediate_subdirectories(DOWNLOAD_PATH)

    print("Generating release information...")

    generate_vcf_download(DOWNLOAD_PATH, downloaded_versions)
    generate_vcf_git_checkout(downloaded_versions)

    print("Candidate release information generated.")
    print("Checking that downloadable files match git files...")

    check_download_matches_git(downloaded_versions)

    print("Downloadable files match git files.")
    print("Release information generation successfully finished.")
