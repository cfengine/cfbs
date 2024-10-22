from cfbs.utils import file_sha256, immediate_files


def check_tarball_checksums(dir_path, downloaded_versions, reported_checksums):
    does_match = True

    for version in downloaded_versions:
        print(version)

        version_path = dir_path / version

        versions_files = immediate_files(version_path)
        # the tarball should be the only file in the version's directory
        tarball_name = versions_files[0]

        tarball_path = version_path / tarball_name

        tarball_checksum = file_sha256(tarball_path)

        if version in ("3.10.0", "3.9.2"):
            # 3.10.0 lists a .tar.gz, not a .pkg.tar.gz
            # 3.9.2 lists no masterfiles
            continue

        reported_checksum = reported_checksums[version]

        if tarball_checksum != reported_checksum:
            does_match = False
            print("* checksum difference:")
            print(version)
            print(tarball_checksum)
            print(reported_checksum)

    return does_match
