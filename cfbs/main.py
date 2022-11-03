#!/usr/bin/env python3
"""CFEngine Build System"""

__copyright__ = ["Northern.tech AS"]

import logging as log
import sys

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

    if args.masterfiles and args.command != "init":
        user_error(
            "The option --masterfiles is only for 'cfbs init', not 'cfbs %s'"
            % args.command
        )

    if args.non_interactive and args.command not in (
        "init",
        "add",
        "remove",
        "clean",
        "update",
        "input",
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
            index=args.index,
            masterfiles=args.masterfiles,
            non_interactive=args.non_interactive,
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
    if args.command == "input":
        return commands.input_command(args.args)
    if args.command in ("set-input", "get-input"):
        filename = "stdin" if args.command == "set-input" else "stdout"
        if len(args.args) <= 0:
            log.error(
                "Missing required arguments <module> and <filename (or - for %s)>"
                % filename
            )
            return 1
        if len(args.args) == 1:
            log.error("Missing required argument <filename (or - for %s)>" % filename)
            return 1
        if len(args.args) > 2:
            log.error(
                "Too many arguments: expected <module> and <filename (or - for %s)>"
                % filename
            )
            return 1

        module, filename = args.args[0], args.args[1]

        if filename == "-":
            file = sys.stdin if args.command == "set-input" else sys.stdout
        else:
            try:
                file = open(filename, "r" if args.command == "set-input" else "w")
            except OSError as e:
                log.error("Can't open '%s': %s" % (filename, e))
                return 1
        try:
            if args.command == "set-input":
                return commands.set_input_command(module, file)
            return commands.get_input_command(module, file)
        finally:
            file.close()

    print_help()
    user_error("Command '%s' not found" % args.command)
