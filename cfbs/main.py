#!/usr/bin/env python3
"""CFEngine Build System"""

__authors__ = ["Ole Herman Schumacher Elgesem"]
__copyright__ = ["Northern.tech AS"]

import argparse
import logging as log

from cfbs.version import string as version
from cfbs.utils import user_error, is_cfbs_repo
from cfbs import commands


def get_args():
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
        default="error",
    )
    parser.add_argument(
        "--version", "-V", help="Print version number", action="store_true"
    )
    parser.add_argument(
        "--force", help="Force rebuild / redownload", action="store_true"
    )
    parser.add_argument("--index", help="Specify alternate index", type=str)
    parser.add_argument(
        "--check", help="Check if file(s) would be reformatted", action="store_true"
    )
    parser.add_argument("--checksum", type=str, default=None,
                        help="Expected checksum of the downloaded file")

    args = parser.parse_args()
    if args.command == "help":
        parser.print_help()
    return args


def set_log_level(level):
    level = level.strip().lower()
    if level == "critical":
        log.basicConfig(level=log.CRITICAL)
    elif level == "error":
        log.basicConfig(level=log.ERROR)
    elif level == "warning":
        log.basicConfig(level=log.WARNING)
    elif level == "info":
        log.basicConfig(level=log.INFO)
    elif level == "debug":
        log.basicConfig(level=log.DEBUG)
    else:
        raise ValueError("Unknown log level: {}".format(level))


def main() -> int:
    args = get_args()
    set_log_level(args.loglevel)

    if args.version:
        print(f"cfbs {version()}")
        return 0

    if not args.command:
        user_error("Usage: cfbs COMMAND")

    # Commands you can run outside a cfbs repo:
    if args.command == "help":
        return 0
    if args.command == "init":
        return commands.init_command(index=args.index)
    if args.command == "search":
        return commands.search_command(args.args, index=args.index)
    if args.command == "pretty":
        return commands.pretty_command(args.args, args.check)
    if args.command == "validate":
        return commands.validate_command(index=args.index)
    if args.command in ("info", "show"):
        return commands.info_command(args.args, index=args.index)

    if not is_cfbs_repo():
        user_error("This is not a cfbs repo, to get started, type: cfbs init")

    if args.command == "status":
        return commands.status_command()
    if args.command == "add":
        return commands.add_command(args.args, index_path=args.index, checksum=args.checksum)
    if args.command == "download":
        return commands.download_command(args.force)
    if args.command == "build":
        return commands.build_command()
    if args.command == "install":
        return commands.install_command(args.args)

    user_error(f"Command '{args.command}' not found")
