from pathlib import Path
from requests_cache import CachedSession
from shutil import unpack_archive
from urllib.request import urlretrieve

DOWNLOAD = True
DEBUG = False

ENTERPRISE_URL = "https://cfengine.com/release-data/enterprise/releases.json"
COMMUNITY_URL = "https://cfengine.com/release-data/community/releases.json"


def print_debug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def check_url_downloadable(session, url):
    headers = session.head(url).headers
    downloadable = "attachment" in headers.get("Content-Disposition", "")

    content_type = headers.get("content-type")
    if "xml" in content_type.lower():
        downloadable = False
    elif "gzip" in content_type.lower():
        downloadable = True

    return downloadable


def check_analogous_urls(session, version):
    url_tarballs = (
        "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-"
        + version
        + ".pkg.tar.gz"
    )

    url_downloadable = check_url_downloadable(session, url_tarballs)
    print_debug("Checking tarballs URL: ", url_downloadable)
    print_debug(url_tarballs)
    if url_downloadable:
        return url_tarballs

    url_enterprise = (
        "https://cfengine-package-repos.s3.amazonaws.com/enterprise/Enterprise-"
        + version
        + "/misc/cfengine-masterfiles-"
        + version
    )

    url_enterprise_0 = url_enterprise + ".pkg.tar.gz"
    url_enterprise_1 = url_enterprise + "-1.pkg.tar.gz"
    url_enterprise_2 = url_enterprise + "-2.pkg.tar.gz"
    url_enterprise_3 = url_enterprise + "-3.pkg.tar.gz"

    print_debug(
        "Checking enterprise-0 URL: ", check_url_downloadable(session, url_enterprise_0)
    )
    print_debug(
        "Checking enterprise-1 URL: ", check_url_downloadable(session, url_enterprise_1)
    )
    print_debug(
        "Checking enterprise-2 URL: ", check_url_downloadable(session, url_enterprise_2)
    )
    print_debug(
        "Checking enterprise-3 URL: ", check_url_downloadable(session, url_enterprise_3)
    )

    return None


# TODO
# def download_all_versions_community():
#     response = session.get(COMMUNITY_URL)
#     # "masterfiles is at a different index" in 3.10.1 happens only for Enterprise, not Community


def download_all_versions_enterprise():
    session = CachedSession()
    response = session.get(ENTERPRISE_URL)
    data = response.json()

    urls_dict = {}
    reported_checksums = {}

    for dd in data["releases"]:
        version = dd["version"]
        print_debug(version)
        release_url = dd["URL"]
        print_debug(release_url)

        subresponse = session.get(release_url)
        subdata = subresponse.json()

        subdd = subdata["artifacts"]
        if "Additional Assets" not in subdd:
            print_debug("Warning: no Additional Assets!")
            # happens for 3.9.0b1, 3.8.0b1, 3.6.1, 3.6.0
            if DEBUG:
                check_analogous_urls(session, version)

            download_url = None

        else:
            # for 3.10.0, for some reason, the masterfiles download link points to the .tar.gz tarball, rather than the .pkg.tar.gz tarball
            # here, download the .pkg.tar.gz from a hidden analoguous URL instead
            if version == "3.10.0":
                download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.10.0.pkg.tar.gz"
            else:
                # there's precisely one version (3.10.1) for which masterfiles is at a different index
                if version == "3.10.1":
                    subdd = subdd["Additional Assets"][1]
                else:
                    subdd = subdd["Additional Assets"][0]

                if subdd["Title"] != "Masterfiles ready-to-install tarball":
                    print_debug("Warning: not masterfiles!")
                    # happens for 3.10.1, 3.9.2, 3.9.0, 3.8.2, 3.8.1, 3.8.0, 3.6.2--3.7.4
                    if DEBUG:
                        check_analogous_urls(session, version)
                    # 3.10.1: see above
                    # 3.9.2: no masterfiles listed, but an analogous hidden URL exists
                    # 3.9.0 and others: no masterfiles listed, and an analogous hidden URLs seemingly do not exist
                    if version == "3.9.2":
                        download_url = "https://cfengine-package-repos.s3.amazonaws.com/tarballs/cfengine-masterfiles-3.9.2.pkg.tar.gz"
                    else:
                        download_url = None
                else:
                    download_url = subdd["URL"]
                    reported_checksums[version] = subdd["SHA256"]

        print_debug(download_url)
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
            urlretrieve(url, tarball_path)

            unpack_archive(tarball_path, version_path / "tarball")

    # for local verification of the reported (Enterprise) (.pkg.tar.gz) checksums
    return downloaded_versions, reported_checksums
