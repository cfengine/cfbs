from cfbs.masterfiles.download_all_versions import download_all_versions
from cfbs.masterfiles.generate_vcf_download import generate_vcf_download
from cfbs.masterfiles.generate_vcf_git_checkout import generate_vcf_git_checkout

# commented out for now as this adds an extra dependency in its current state (dictdiffer)
# from cfbs.masterfiles.check_download_matches_git import check_download_matches_git


def generate_release_information():
    print("Downloading masterfiles...")

    download_path, downloaded_versions = download_all_versions()

    print("Download finished. Every reported checksum matches.")
    print("Generating release information...")

    generate_vcf_download(download_path, downloaded_versions)
    generate_vcf_git_checkout(downloaded_versions)

    # TODO automatic analysis of the difference between downloadable MPF data and git MPF data
    # in its current state, this generates differences-*.txt files for each version
    # check_download_matches_git(downloaded_versions)
