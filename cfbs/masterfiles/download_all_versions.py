import os
import shutil

from cfbs.utils import fetch_url, get_json, mkdir

ENTERPRISE_URL = "https://cfengine.com/release-data/enterprise/releases.json"
COMMUNITY_URL = "https://cfengine.com/release-data/community/releases.json"

ENTERPRISE_DOWNLOAD_PATH = "enterprise"


def get_download_urls_enterprise():
    download_urls = {}
    reported_checksums = {}

    data = get_json(ENTERPRISE_URL)

    for release_data in data["releases"]:
        version = release_data["version"]

        if version == "3.10.0":
            # for 3.10.0, for some reason, the masterfiles download link points to the .tar.gz tarball, rather than the .pkg.tar.gz tarball
            # download the .pkg.tar.gz from an unlisted analoguous URL instead
            download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.10.0.pkg.tar.gz"
            download_urls[version] = download_url
            continue
        if version == "3.9.2":
            # for 3.9.2, no masterfiles are listed, but an unlisted analoguous URL exists
            download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.9.2.pkg.tar.gz"
            download_urls[version] = download_url
            continue

        release_url = release_data["URL"]
        subdata = get_json(release_url)
        artifacts_data = subdata["artifacts"]

        if "Additional Assets" not in artifacts_data:
            # happens for 3.9.0b1, 3.8.0b1, 3.6.1, 3.6.0
            continue

        assets_data = artifacts_data["Additional Assets"]
        masterfiles_data = None

        for asset in assets_data:
            if asset["Title"] == "Masterfiles ready-to-install tarball":
                masterfiles_data = asset

        if masterfiles_data is None:
            # happens for 3.9.2, 3.9.0, 3.8.2, 3.8.1, 3.8.0, 3.7.4--3.6.2
            # 3.9.2: see above
            # 3.9.0 and below: no masterfiles listed, and analogous unlisted URLs seemingly do not exist
            continue

        download_urls[version] = masterfiles_data["URL"]
        reported_checksums[version] = masterfiles_data["SHA256"]

    return download_urls, reported_checksums


def download_versions_from_urls(output_path, download_urls):
    downloaded_versions = []

    mkdir(output_path)

    for version, url in download_urls.items():
        # ignore master and .x versions
        if url.startswith("http://buildcache"):
            continue

        print("Downloading from", url)
        downloaded_versions.append(version)

        version_path = os.path.join(output_path, version)
        mkdir(version_path)

        filename = url.split("/")[-1]
        tarball_path = os.path.join(version_path, filename)
        fetch_url(url, tarball_path)

        tarball_dir_path = os.path.join(version_path, "tarball")
        shutil.unpack_archive(tarball_path, tarball_dir_path)

    return output_path, downloaded_versions


# TODO
# def download_all_versions_community():
#     data = get_json(COMMUNITY_URL)


def download_all_versions_enterprise():
    download_urls, reported_checksums = get_download_urls_enterprise()

    output_path, downloaded_versions = download_versions_from_urls(
        ENTERPRISE_DOWNLOAD_PATH, download_urls
    )

    # for local verification of the reported (Enterprise) (.pkg.tar.gz) checksums
    return output_path, downloaded_versions, reported_checksums
