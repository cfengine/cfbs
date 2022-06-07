import argparse

from cfbs import commands
from cfbs.utils import cache


def get_args():
    parser = _get_arg_parser()
    args = parser.parse_args()
    return args


def print_help():
    parser = _get_arg_parser()
    parser.print_help()


@cache
def _get_arg_parser():
    command_list = [
        cmd.split("_")[0] for cmd in dir(commands) if cmd.endswith("_command")
    ]
    parser = argparse.ArgumentParser(description="CFEngine Build System.")
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
    return parser
