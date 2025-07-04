from cfbs.masterfiles.analyze import version_is_at_least
from cfbs.masterfiles.download_all_versions import download_all_versions
from cfbs.masterfiles.generate_vcf_download import generate_vcf_download
from cfbs.masterfiles.generate_vcf_git_checkout import generate_vcf_git_checkout
from cfbs.masterfiles.check_download_matches_git import check_download_matches_git
from cfbs.utils import immediate_subdirectories

DOWNLOAD_PATH = "downloaded_masterfiles"


def generate_release_information(omit_download=False, check=False, min_version=None):
    if not omit_download:
        print("Downloading masterfiles...")

        downloaded_versions = download_all_versions(DOWNLOAD_PATH, min_version)

        print("Download finished. Every reported checksum matches.")
    else:
        downloaded_versions = immediate_subdirectories(DOWNLOAD_PATH)

        downloaded_versions = list(
            filter(
                lambda v: version_is_at_least(v, min_version),
                downloaded_versions,
            )
        )

    print(
        "Downloading releases of masterfiles from cfengine.com and generating release information..."
    )
    generate_vcf_download(DOWNLOAD_PATH, downloaded_versions)

    if check:
        print(
            "Downloading releases of masterfiles from git (github.com) and generating "
            + "additional release information for comparison..."
        )
        generate_vcf_git_checkout(downloaded_versions)
        print("Candidate release information generated.")
        print("Comparing files from cfengine.com and github.com...")

        check_download_matches_git(downloaded_versions)

        print("The masterfiles downloaded from github.com and cfengine.com match.")
    else:
        print("Release information successfully generated.")
        print("See the results in ./versions.json, ./checksums.json, and ./files.json")
        print(
            "(Run again with --check-against-git to download and compare with files "
            + "from git, and generate -git.json files)"
        )
