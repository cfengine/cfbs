import os
import shutil

from cfbs.masterfiles.analyze import version_is_at_least
from cfbs.utils import CFBSNetworkError, fetch_url, get_json, mkdir, CFBSExitError

ENTERPRISE_RELEASES_URL = "https://cfengine.com/release-data/enterprise/releases.json"


COMMUNITY_ONLY_VERSIONS = ["3.12.0b1", "3.10.0b1"]
"""Masterfiles versions which do not appear in Enterprise releases but appear in Community releases."""

MISSING_DATA_VERSIONS = ["3.10.0", "3.9.2"]
"""Rationale for each version:
* 3.10.0:\\
    For some reason, the `"Masterfiles ready-to-install tarball"` is a .tar.gz tarball, rather than a .pkg.tar.gz tarball.
    However, an unlisted analoguous URL for the .pkg.tar.gz tarball does exist.
* 3.9.2:\\
    No masterfiles are listed in the release data, but an unlisted analoguous URL does exist."""

HARDCODED_VERSIONS = COMMUNITY_ONLY_VERSIONS + MISSING_DATA_VERSIONS

HARDCODED_URLS = {
    "3.12.0b1": "https://cfengine-package-repos.s3.amazonaws.com/community_binaries/Community-3.12.0b1/misc/cfengine-masterfiles-3.12.0b1.pkg.tar.gz",
    "3.10.0b1": "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.10.0b1.pkg.tar.gz",
    "3.10.0": "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.10.0.pkg.tar.gz",
    "3.9.2": "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.9.2.pkg.tar.gz",
}
HARDCODED_CHECKSUMS = {
    "3.12.0b1": "ede305dae7be3edfac04fc5b7f63b46adb3a5b1612f4755e855ee8e6b8d344d7",
    "3.10.0b1": "09291617254705d79dea2531b23dbd0754f09029e90ce0b43b275aa02c1223a3",
    "3.10.0": "7b5e237529e11ce4ae295922dad1a681f13b95f3a7d247d39d3f5088f1a1d7d3",
    "3.9.2": "ae1a758530d4a4aad5b6812b61fc37ad1b5900b755f88a1ab98da7fd05a9f5cc",
}


def get_download_urls_enterprise(min_version=None):
    download_urls = {}
    reported_checksums = {}

    print("* gathering download URLs...")

    try:
        data = get_json(ENTERPRISE_RELEASES_URL)
    except CFBSNetworkError:
        raise CFBSExitError(
            "Downloading CFEngine release data failed - check your Wi-Fi / network settings."
        )

    for release_data in data["releases"]:
        version = release_data["version"]

        if not version_is_at_least(version, min_version):
            continue

        if version in MISSING_DATA_VERSIONS:
            download_urls[version] = HARDCODED_URLS[version]
            reported_checksums[version] = HARDCODED_CHECKSUMS[version]
            continue

        release_url = release_data["URL"]
        try:
            subdata = get_json(release_url)
        except CFBSNetworkError:
            raise CFBSExitError(
                "Downloading CFEngine release data for version %s failed - check your Wi-Fi / network settings."
                % version
            )
        artifacts_data = subdata["artifacts"]

        if "Additional Assets" not in artifacts_data:
            # happens for 3.9.0b1, 3.8.0b1, 3.6.1, 3.6.0
            continue

        masterfiles_data = None
        for asset in artifacts_data["Additional Assets"]:
            if asset["Title"] == "Masterfiles ready-to-install tarball":
                masterfiles_data = asset

        if masterfiles_data is None:
            # happens for 3.9.2, 3.9.0, 3.8.2, 3.8.1, 3.8.0, 3.7.4--3.6.2
            # 3.9.2: see above
            # 3.9.0 and below: no masterfiles listed, and unlisted analogous URLs seemingly do not exist
            continue

        download_urls[version] = masterfiles_data["URL"]
        reported_checksums[version] = masterfiles_data["SHA256"]

    return download_urls, reported_checksums


def get_all_download_urls(min_version=None):
    download_urls, reported_checksums = get_download_urls_enterprise(min_version)

    for version in COMMUNITY_ONLY_VERSIONS:
        if version_is_at_least(version, min_version):
            download_urls[version] = HARDCODED_URLS[version]
            reported_checksums[version] = HARDCODED_CHECKSUMS[version]

    return download_urls, reported_checksums


def get_single_download_url(version):
    if version in HARDCODED_VERSIONS:
        download_url = HARDCODED_URLS[version]
        reported_checksum = HARDCODED_CHECKSUMS[version]
        return (download_url, reported_checksum)

    try:
        data = get_json(ENTERPRISE_RELEASES_URL)
    except CFBSNetworkError:
        raise CFBSExitError(
            "Downloading CFEngine release data failed - check your Wi-Fi / network settings."
        )

    for release_data in data["releases"]:
        release_version = release_data["version"]

        if release_version == version:
            release_url = release_data["URL"]
            try:
                subdata = get_json(release_url)
            except CFBSNetworkError:
                raise CFBSExitError(
                    "Downloading CFEngine release data for version %s failed - check your Wi-Fi / network settings."
                    % version
                )
            artifacts_data = subdata["artifacts"]

            if "Additional Assets" not in artifacts_data:
                break

            for asset in artifacts_data["Additional Assets"]:
                if asset["Title"] == "Masterfiles ready-to-install tarball":
                    download_url = asset["URL"]
                    reported_checksum = asset["SHA256"]

                    return (download_url, reported_checksum)

    raise CFBSExitError("Download URL of given MPF version was not found")


def download_versions_from_urls(download_path, download_urls, reported_checksums):
    downloaded_versions = []

    mkdir(download_path)

    for version, url in download_urls.items():
        # ignore master and .x versions
        if url.startswith("http://buildcache"):
            continue

        print("* downloading from", url)
        downloaded_versions.append(version)

        version_path = os.path.join(download_path, version)
        mkdir(version_path)

        # download a version, and verify the reported checksum matches
        filename = url.split("/")[-1]
        tarball_path = os.path.join(version_path, filename)
        checksum = reported_checksums[version]
        try:
            fetch_url(url, tarball_path, checksum)
        except CFBSNetworkError as e:
            raise CFBSExitError("For version " + version + ": " + str(e))

        tarball_dir_path = os.path.join(version_path, "tarball")
        shutil.unpack_archive(tarball_path, tarball_dir_path)

    return downloaded_versions


def download_all_versions(download_path, min_version=None):
    download_urls, reported_checksums = get_all_download_urls(min_version)

    downloaded_versions = download_versions_from_urls(
        download_path, download_urls, reported_checksums
    )

    return downloaded_versions


def download_single_version(download_path, version):
    download_url, reported_checksum = get_single_download_url(version)

    download_urls = {version: download_url}
    reported_checksums = {version: reported_checksum}

    download_versions_from_urls(download_path, download_urls, reported_checksums)
