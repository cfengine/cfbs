#!/usr/bin/env python3
"""CFEngine Build System"""

__authors__ = ["Ole Herman Schumacher Elgesem"]
__copyright__ = ["Northern.tech AS"]

import argparse
import logging as log

from cfbs.version import string as version
from cfbs.utils import user_error
from cfbs import commands


def get_args():
    parser = argparse.ArgumentParser(description="CFEngine Build System.")
    parser.add_argument(
        "command",
        metavar="cmd",
        type=str,
        nargs="?",
        help="The command to perform (init, status, search, add, download, build, install, pretty)",
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

    args = parser.parse_args()
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
    if args.command == "init":
        return commands.init_command()
    if args.command == "search":
        return commands.search_command(args.args)
    if args.command == "pretty":
        return commands.pretty_command(args.args)

    if not commands.is_cfbs_repo():
        user_error("This is not a cfbs repo, to get started, type: cfbs init")

    if args.command == "status":
        return commands.status_command()
    if args.command == "add":
        return commands.add_command(args.args)
    if args.command == "download":
        return commands.download_command(args.force)
    if args.command == "build":
        return commands.build_command()
    if args.command == "install":
        return commands.install_command(args.args)

    user_error(f"Command '{args.command}' not found")
