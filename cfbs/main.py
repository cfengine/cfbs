#!/usr/bin/env python3
"""CFEngine Build System"""

__copyright__ = ["Northern.tech AS"]

import logging as log
import sys
import os
import traceback
import pathlib

from cfbs.git import CFBSGitError
from cfbs.validate import validate_index_string
from cfbs.version import string as version
from cfbs.utils import (
    CFBSValidationError,
    CFBSExitError,
    CFBSUserError,
    is_cfbs_repo,
    CFBSProgrammerError,
    CFBSNetworkError,
)
from cfbs.cfbs_config import CFBSConfig
from cfbs import commands
from cfbs.args import get_args, print_help, get_manual


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


def does_log_info(level):
    return level == "info" or level == "debug"


def _main() -> int:
    """Actual body of main function.

    Mainly for getting command line arguments and calling the appropriate
    functions based on command line arguments.

    Actual logic should be implemented elsewhere (primarily in commands.py).

    This function is wrapped by main() which catches exceptions.
    """
    args = get_args()
    init_logging(args.loglevel)
    if args.manual:
        print(get_manual())
        return 0
    if args.version:
        print("cfbs %s" % version())
        return 0

    if not args.command:
        print_help()
        print("")
        raise CFBSUserError("No command given")

    if args.command not in commands.get_command_names():
        print_help()
        raise CFBSUserError("Command '%s' not found" % args.command)

    if args.index is not None:
        if args.command not in ["init", "add", "search", "validate"]:
            raise CFBSUserError(
                "'--index' option can not be used with the '%s' command" % args.command
            )
        validate_index_string(args.index)

    if args.masterfiles and args.command != "init":
        raise CFBSUserError(
            "The option --masterfiles is only for 'cfbs init', not 'cfbs %s'"
            % args.command
        )

    if args.omit_download and args.command != "generate-release-information":
        raise CFBSUserError(
            "The option --omit-download is only for 'cfbs generate-release-information', not 'cfbs %s'"
            % args.command
        )

    if args.check_against_git and args.command != "generate-release-information":
        raise CFBSUserError(
            "The option --check-against-git is only for 'cfbs generate-release-information', not 'cfbs %s'"
            % args.command
        )

    if args.minimum_version and args.command != "generate-release-information":
        raise CFBSUserError(
            "The option --from is only for 'cfbs generate-release-information', not 'cfbs %s'"
            % args.command
        )

    if args.masterfiles_dir and args.command not in ("analyze", "analyse"):
        raise CFBSUserError(
            "The option --masterfiles-dir is only for 'cfbs analyze', not 'cfbs %s'"
            % args.command
        )

    if args.reference_version and args.command not in ("analyze", "analyse"):
        raise CFBSUserError(
            "The option --reference-version is only for 'cfbs analyze', not 'cfbs %s'"
            % args.command
        )

    if args.to_json and args.command not in ("analyze", "analyse"):
        raise CFBSUserError(
            "The option --to-json is only for 'cfbs analyze', not 'cfbs %s'"
            % args.command
        )

    if args.ignored_path_components and args.command not in ("analyze", "analyse"):
        raise CFBSUserError(
            "The option --ignored-path-components is only for 'cfbs analyze', not 'cfbs %s'"
            % args.command
        )

    if args.offline and args.command not in ("analyze", "analyse", "convert"):
        raise CFBSUserError(
            "The option --offline is only for 'cfbs analyze', not 'cfbs %s'"
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
        raise CFBSUserError(
            "The option --non-interactive is not for cfbs %s" % (args.command)
        )

    # Commands you can run outside a cfbs repo:
    if args.command == "help":
        print_help()
        return 0

    CFBSConfig.get_instance(index=args.index, non_interactive=args.non_interactive)

    if args.command == "init":
        return commands.init_command(
            index=args.index,
            masterfiles=args.masterfiles,
            non_interactive=args.non_interactive,
            use_git=args.git,
        )

    if args.command == "search":
        return commands.search_command(args.args)
    if args.command == "pretty":
        return commands.pretty_command(args.args, args.check, args.keep_order)
    if args.command == "validate":
        return commands.validate_command(args.args, args.index)
    if args.command in ("info", "show"):
        return commands.info_command(args.args)

    if args.command in ("analyze", "analyse"):
        return commands.analyze_command(
            args.args,
            args.to_json,
            args.reference_version,
            args.masterfiles_dir,
            args.ignored_path_components,
            args.offline,
            does_log_info(args.loglevel),
        )
    if args.command == "convert":
        return commands.convert_command(args.non_interactive, args.offline)

    if args.command == "generate-release-information":
        return commands.generate_release_information_command(
            omit_download=args.omit_download,
            check=args.check_against_git,
            min_version=args.minimum_version,
        )

    # Commands you cannot run outside a cfbs repo:
    if not is_cfbs_repo():
        raise CFBSExitError("This is not a cfbs repo, to get started, type: cfbs init")

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

    raise CFBSProgrammerError(
        "Command '%s' not handled appropriately by the code above" % args.command
    )


def main() -> int:
    """Entry point

    The only thing we want to do here is call _main() and handle exceptions (errors).
    """
    if os.getenv("CFBACKTRACE") == "1":
        r = _main()
        return r
    try:
        r = _main()
        return r
    except CFBSValidationError as e:
        print("Error: " + str(e))
        return 1
    except CFBSExitError as e:
        print("Error: " + str(e))
        return 1
    except CFBSUserError as e:
        print("Error: " + str(e))
        return 1
    except CFBSNetworkError as e:
        print("Error: " + str(e))
        return 1
    except CFBSGitError as e:
        print("Error: " + str(e))
        return 1
    # AssertionError and CFBSProgrammerError are not expected, print extra info:
    except AssertionError as e:
        tb = traceback.extract_tb(e.__traceback__)
        frame = tb[-1]
        this_file = pathlib.Path(__file__)
        cfbs_prefix = os.path.abspath(this_file.parent.parent.resolve())
        filename = os.path.abspath(frame.filename)
        # Opportunistically cut off beginning of path if possible:
        if filename.startswith(cfbs_prefix):
            filename = filename[len(cfbs_prefix) :]
            if filename.startswith("/"):
                filename = filename[1:]
        line = frame.lineno
        # Avoid using frame.colno - it was not available in python 3.5,
        # and even in the latest version, it is not declared in the
        # docstring, so you will get linting warnings;
        # https://github.com/python/cpython/blob/v3.13.5/Lib/traceback.py#L276-L288
        # column = frame.colno
        assertion = frame.line
        explanation = str(e)
        message = "Assertion failed - %s%s (%s:%s)" % (
            assertion,
            (" - " + explanation) if explanation else "",
            filename,
            line,
        )
        print("Error: " + message)
    except CFBSProgrammerError as e:
        print("Error: " + str(e))
    print("This is an unexpected error indicating a bug, please create a ticket at:")
    print("https://northerntech.atlassian.net/")
    print(
        "(Rerun with CFBACKTRACE=1 in front of your command to show the full backtrace)"
    )

    # TODO: Handle other exceptions
    return 1
