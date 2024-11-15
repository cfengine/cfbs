import os
import shutil
import subprocess
import sys

from cfbs.utils import write_json
from cfbs.masterfiles.analyze import (
    finalize_vcf,
    initialize_vcf,
    versions_checksums_files,
)

DIR_PATH = "."
"""The path of the working directory."""

MPF_URL = "https://github.com/cfengine/masterfiles"
MPF_PATH = os.path.join(DIR_PATH, "masterfiles")


def check_required_command(command):
    if not shutil.which(command):
        print("`%s` was not found" % command)
        sys.exit(1)


def check_required_commands(commands):
    for c in commands:
        check_required_command(c)


def generate_vcf_git_checkout(checkout_tags):
    required_commands = ["git", "make", "automake", "autoconf"]
    check_required_commands(required_commands)

    # get the current version of the MPF repo
    if not os.path.isdir(MPF_PATH):
        subprocess.run(
            ["git", "clone", "--no-checkout", MPF_URL],
            cwd=DIR_PATH,
            check=True,
        )
    else:
        subprocess.run(
            ["git", "fetch", "--all"],
            cwd=MPF_PATH,
            check=True,
        )

    versions_dict, checksums_dict, files_dict = initialize_vcf()

    for tag in checkout_tags:
        print("Checkouting tag", tag)

        # checkout the version
        subprocess.run(
            ["git", "checkout", tag],
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

        # clean the files to prevent spillage to other versions
        subprocess.run(
            ["git", "clean", "-dfx"],
            cwd=MPF_PATH,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    versions_dict, checksums_dict, files_dict = finalize_vcf(
        versions_dict, checksums_dict, files_dict
    )

    write_json("versions-git.json", versions_dict)
    write_json("checksums-git.json", checksums_dict)
    write_json("files-git.json", files_dict)
