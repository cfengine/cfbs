import argparse
import os
from typing import List, Optional  # noqa: F401

from cfbs import commands
from cfbs.utils import cache, CFBSExitError


class ArgsTypesNamespace(argparse.Namespace):
    """Manual type hints to args attributes"""

    # PEP 484 style type hints for compatibility with Python 3.5.
    # This commit can be reverted, and type hints returned to the PEP 526 style type hints, once the supported Python version becomes 3.6+.
    command = None  # type: Optional[str]
    args = []  # type: List[str]
    loglevel = "warning"  # type: str
    manual = False  # type: bool
    version = False  # type: bool
    force = False  # type: bool
    non_interactive = False  # type: bool
    index = None  # type: Optional[str]
    check = False  # type: bool
    checksum = None  # type: Optional[str]
    keep_order = False  # type: bool
    git = None  # type: Optional[bool]
    git_user_name = None  # type: Optional[str]
    git_user_email = None  # type: Optional[str]
    git_commit_message = None  # type: Optional[str]
    ignore_versions_json = False  # type: bool
    diffs = None  # type: Optional[str]
    omit_download = False  # type: bool
    check_against_git = False  # type: bool
    minimum_version = None  # type: Optional[str]
    to_json = None  # type: Optional[str]
    reference_version = None  # type: Optional[str]
    masterfiles_dir = None  # type: Optional[str]
    ignored_path_components = None  # type: Optional[List[str]]
    offline = False  # type: bool
    masterfiles = None  # type: Optional[str]


def get_args():
    parser = get_arg_parser()
    args = parser.parse_args(namespace=ArgsTypesNamespace())
    return args


def print_help():
    parser = get_arg_parser()
    parser.print_help()


def get_manual():
    file_path = os.path.join(os.path.dirname(__file__), "cfbs.1")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as man_file:
                man = man_file.read()
                if not man:
                    raise CFBSExitError("Manual file is empty")
                else:
                    return man
        except OSError:
            raise CFBSExitError("Error reading manual file " + file_path)
    else:
        raise CFBSExitError("Manual file does not exist")


def yesno_to_bool(s: str):
    if s == "yes":
        return True
    if s == "no":
        return False
    assert False


class YesNoToBool(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        assert type(values) is str
        values = yesno_to_bool(values)
        setattr(namespace, self.dest, values)


@cache
def get_arg_parser(whitespace_for_manual=False):
    command_list = commands.get_command_names()
    CFBS_DESCRIPTION = "CFEngine Build System."
    if whitespace_for_manual:
        parser = argparse.ArgumentParser(
            prog="cfbs",
            description=CFBS_DESCRIPTION,
            formatter_class=argparse.RawTextHelpFormatter,
        )
    else:
        parser = argparse.ArgumentParser(prog="cfbs", description=CFBS_DESCRIPTION)
    parser.add_argument(
        "command",
        metavar="cmd",
        type=str,
        nargs="?",
        help="The command to perform ({})".format(", ".join(command_list)),
    )
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument(
        "--loglevel",
        "-l",
        help="Set log level for more/less detailed output",
        type=str,
        default="warning",
    )
    parser.add_argument("-M", "--manual", help="Print manual page", action="store_true")
    parser.add_argument(
        "--version", "-V", help="Print version number", action="store_true"
    )
    parser.add_argument(
        "--force", help="Force rebuild / redownload", action="store_true"
    )
    parser.add_argument(
        "--non-interactive",
        help="Don't prompt, use defaults (only for testing)",
        action="store_true",
    )
    parser.add_argument(
        "--index",
        help="Specify alternate index (HTTPS URL or relative path to JSON file)",
        type=str,
    )
    parser.add_argument(
        "--check", help="Check if file(s) would be reformatted", action="store_true"
    )
    parser.add_argument(
        "--checksum",
        type=str,
        default=None,
        help="Expected checksum of the downloaded file",
    )
    parser.add_argument(
        "--keep-order",
        help="Keep order of items in the JSON in 'cfbs pretty'",
        action="store_true",
    )
    parser.add_argument(
        "--git",
        choices=("yes", "no"),
        action=YesNoToBool,
        help="Override git option in cfbs.json",
    )
    parser.add_argument(
        "--git-user-name",
        help="Specify git user name",
    )
    parser.add_argument(
        "--git-user-email",
        help="Specify git user email",
    )
    parser.add_argument(
        "--git-commit-message",
        help="Specify git commit message",
    )
    parser.add_argument(
        "--ignore-versions-json",
        help="Ignore versions.json. Necessary in case of a custom index or testing changes to the default index.",
        action="store_true",
    )
    parser.add_argument(
        "--diffs",
        help="Write diffs of files overwritten with a copy build step during 'cfbs build' to the specified file",
        nargs="?",
        const="diffs.txt",
        default=None,
    )
    parser.add_argument(
        "--omit-download",
        help="Use existing masterfiles instead of downloading in 'cfbs generate-release-information'",
        action="store_true",
    )
    parser.add_argument(
        "--check-against-git",
        help="Check whether masterfiles from cfengine.com and github.com match in 'cfbs generate-release-information'",
        action="store_true",
    )
    parser.add_argument(
        "--from",
        help="Specify minimum version in 'cfbs generate-release-information'",
        dest="minimum_version",
    )
    parser.add_argument(
        "--to-json",
        help="Output 'cfbs analyze' results to a JSON file; optionally specify the JSON's filename",
        nargs="?",
        const="analysis",
        default=None,
    )
    parser.add_argument(
        "--reference-version",
        help="Specify version to compare against for 'cfbs analyze'",
    )
    parser.add_argument(
        "--masterfiles-dir",
        help="If the path given to 'cfbs analyze' contains a masterfiles subdirectory, specify the subdirectory's name",
    )
    parser.add_argument(
        "--ignored-path-components",
        help="Specify path components which should be ignored during 'cfbs analyze' (the components should be passed separately, delimited by spaces)",
        nargs="*",
    )
    parser.add_argument(
        "--offline",
        help="Do not connect to the Internet to download the latest version of MPF release information during 'cfbs analyze' and 'cfbs convert'",
        action="store_true",
    )
    parser.add_argument(
        "--masterfiles",
        help='Specify masterfiles version to add during "cfbs init". This can be a branch, a full version number, or `no` to not add masterfiles at all.',
    )
    return parser
