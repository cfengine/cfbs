import argparse
import os

from cfbs import commands
from cfbs.utils import cache, user_error


def get_args():
    parser = get_arg_parser()
    args = parser.parse_args()
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
                    user_error("Manual file is empty")
                else:
                    return man
        except OSError:
            user_error("Error reading manual file " + file_path)
    else:
        user_error("Manual file does not exist")


@cache
def get_arg_parser():
    command_list = commands.get_command_names()
    parser = argparse.ArgumentParser(prog="cfbs", description="CFEngine Build System.")
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
    parser.add_argument("--index", help="Specify alternate index", type=str)
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
        "--masterfiles", help="Add masterfiles on cfbs init choose between"
    )
    return parser
