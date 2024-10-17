import os
import shutil
import subprocess
import sys

from cfbs.git import git_exists
from cfbs.utils import write_json
from masterfiles.analyze import initialize_vcf, versions_checksums_files

DIR_PATH = "."
"""The path of the working directory."""

MPF_URL = "https://github.com/cfengine/masterfiles"
MPF_PATH = os.path.join(DIR_PATH, "masterfiles")


def generate_vcf_git_checkout(interesting_tags=None):
    # clone the MPF repo every time the script is run, in case there are updates
    if os.path.isdir(MPF_PATH):
        shutil.rmtree(MPF_PATH)

    subprocess.run(
        ["git", "clone", MPF_URL],
        cwd=DIR_PATH,
        check=True,
    )

    if not git_exists():
        print("`git` was not found")
        sys.exit(1)

    result = subprocess.run(
        ["git", "tag"], cwd=MPF_PATH, capture_output=True, check=True
    )
    tags = result.stdout.decode("UTF-8").splitlines()

    # if not given, choose tags to checkout - by default, only consider version releases
    if interesting_tags is None:
        interesting_tags = []

        for tag in tags:
            if "-" not in tag:
                interesting_tags.append(tag)

    versions_dict, checksums_dict, files_dict = initialize_vcf()

    for tag in interesting_tags:
        print(tag)

        # checkout the version tag
        subprocess.run(
            ["git", "checkout", "--force", tag],
            cwd=MPF_PATH,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # a clean is necessary to remove all the undesired files
        subprocess.run(
            ["git", "clean", "-dffx"],
            cwd=MPF_PATH,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # build masterfiles from git as they are in the tarball packages
        subprocess.run(
            ["./autogen.sh"],
            cwd=MPF_PATH,
            check=True,
            env=dict(os.environ.copy(), EXPLICIT_VERSION=tag),
        )
        # older masterfiles version READMEs instruct to use `make install` and newer `make` - always use `make` instead
        subprocess.run(["make"], cwd=MPF_PATH, check=True)

        # compute VCF data for all the files
        versions_dict, checksums_dict, files_dict = versions_checksums_files(
            MPF_PATH, tag, versions_dict, checksums_dict, files_dict
        )

    write_json("versions-git.json", versions_dict)
    write_json("checksums-git.json", checksums_dict)
    write_json("files-git.json", files_dict)
