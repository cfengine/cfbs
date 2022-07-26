#!/usr/bin/env python3
"""CFEngine Build System"""

__copyright__ = ["Northern.tech AS"]

import logging as log

from cfbs.version import string as version
from cfbs.utils import user_error, is_cfbs_repo
from cfbs.cfbs_config import CFBSConfig
from cfbs import commands
from cfbs.args import get_args, print_help


def init_logging(level):
    # Warning: logging.basicConfig() cannot be called multiple times to set
    #          different parameters. We have to set both format and level in
    #          the same call
    format = "%(levelname)s: %(message)s"
    level = level.strip().lower()
    if level == "critical":
        log.basicConfig(level=log.CRITICAL, format=format)
    elif level == "error":
        log.basicConfig(level=log.ERROR, format=format)
    elif level == "warning":
        log.basicConfig(level=log.WARNING, format=format)
    elif level == "info":
        log.basicConfig(level=log.INFO, format=format)
    elif level == "debug":
        log.basicConfig(level=log.DEBUG, format=format)
    else:
        raise ValueError("Unknown log level: {}".format(level))


def main() -> int:
    args = get_args()
    init_logging(args.loglevel)

    if args.version:
        print("cfbs %s" % version())
        return 0

    if not args.command:
        print_help()
        print("")
        user_error("No command given")

    if args.non_interactive and args.command not in (
        "init",
        "add",
        "remove",
        "clean",
        "update",
    ):
        user_error("The option --non-interactive is not for cfbs %s" % (args.command))

    if args.non_interactive:
        print(
            """
Warning: The --non-interactive option is only meant for testing (!)
         DO NOT run commands with --non-interactive as part of your deployment
         pipeline. Instead, run cfbs commands manually, commit the resulting
         cfbs.json and only run cfbs build + cfbs install when deploying your
         policy set. Thank you for your cooperation.
""".strip()
        )

    # Commands you can run outside a cfbs repo:
    if args.command == "help":
        print_help()
        return 0

    CFBSConfig.get_instance(args.index, args.non_interactive)

    if args.command == "init":
        return commands.init_command(
            index=args.index, non_interactive=args.non_interactive
        )

    if args.command == "search":
        return commands.search_command(args.args)
    if args.command == "pretty":
        return commands.pretty_command(args.args, args.check, args.keep_order)
    if args.command == "validate":
        return commands.validate_command()
    if args.command in ("info", "show"):
        return commands.info_command(args.args)

    if not is_cfbs_repo():
        user_error("This is not a cfbs repo, to get started, type: cfbs init")

    if args.command == "status":
        return commands.status_command()
    if args.command == "add":
        return commands.add_command(
            args.args,
            checksum=args.checksum,
        )
    if args.command == "remove":
        return commands.remove_command(args.args)
    if args.command == "clean":
        return commands.clean_command()
    if args.command == "download":
        return commands.download_command(args.force)
    if args.command == "build":
        return commands.build_command(ignore_versions=args.ignore_versions_json)
    if args.command == "install":
        return commands.install_command(args.args)
    if args.command == "update":
        return commands.update_command(args.args)

    print_help()
    user_error("Command '%s' not found" % args.command)
