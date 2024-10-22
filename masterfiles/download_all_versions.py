from pathlib import Path
import shutil
import urllib.request

from cfbs.utils import get_json

DOWNLOAD = True

ENTERPRISE_URL = "https://cfengine.com/release-data/enterprise/releases.json"
COMMUNITY_URL = "https://cfengine.com/release-data/community/releases.json"

# TODO
# def download_all_versions_community():
#     data = get_json(COMMUNITY_URL)
#     # "masterfiles is at a different index" in 3.10.1 happens only for Enterprise, not Community


def download_all_versions_enterprise():
    data = get_json(ENTERPRISE_URL)

    urls_dict = {}
    reported_checksums = {}

    for releases_data in data["releases"]:
        version = releases_data["version"]
        release_url = releases_data["URL"]

        subdata = get_json(release_url)

        artifacts_data = subdata["artifacts"]
        if "Additional Assets" not in artifacts_data:
            # happens for 3.9.0b1, 3.8.0b1, 3.6.1, 3.6.0
            download_url = None

        else:
            # for 3.10.0, for some reason, the masterfiles download link points to the .tar.gz tarball, rather than the .pkg.tar.gz tarball
            # here, download the .pkg.tar.gz from a hidden analoguous URL instead
            if version == "3.10.0":
                download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.10.0.pkg.tar.gz"
            else:
                # there's precisely one version (3.10.1) for which masterfiles is at a different index
                if version == "3.10.1":
                    artifacts_data = artifacts_data["Additional Assets"][1]
                else:
                    artifacts_data = artifacts_data["Additional Assets"][0]

                if artifacts_data["Title"] != "Masterfiles ready-to-install tarball":
                    # happens for 3.10.1, 3.9.2, 3.9.0, 3.8.2, 3.8.1, 3.8.0, 3.6.2--3.7.4
                    # 3.10.1: see above
                    # 3.9.2: no masterfiles listed, but an analogous hidden URL exists
                    # 3.9.0 and others: no masterfiles listed, and analogous hidden URLs seemingly do not exist
                    if version == "3.9.2":
                        download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.9.2.pkg.tar.gz"
                    else:
                        download_url = None
                else:
                    download_url = artifacts_data["URL"]
                    reported_checksums[version] = artifacts_data["SHA256"]

        if download_url is not None:
            urls_dict[version] = download_url

    downloaded_versions = []
    if DOWNLOAD:
        root_path = Path("./enterprise")
        Path.mkdir(root_path, exist_ok=True)

        for version, url in urls_dict.items():
            # ignore master and .x versions
            if url.startswith("http://buildcache"):
                continue

            downloaded_versions.append(version)
            print(url)

            version_path = root_path / version
            Path.mkdir(version_path, exist_ok=True)

            filename = url.split("/")[-1]
            tarball_path = version_path / filename
            urllib.request.urlretrieve(url, tarball_path)

            shutil.unpack_archive(tarball_path, version_path / "tarball")

    # for local verification of the reported (Enterprise) (.pkg.tar.gz) checksums
    return downloaded_versions, reported_checksums
