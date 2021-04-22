#!/usr/bin/env python3
"""CFEngine Build System"""

__authors__    = ["Ole Herman Schumacher Elgesem"]
__copyright__  = ["Northern.tech AS"]

import argparse
import logging as log

from cfbs import version

def get_args():
    parser = argparse.ArgumentParser(description='CFEngine Build System.')
    parser.add_argument('commands', metavar='cmd', type=str, nargs='?',
                        help='The command to perform')
    parser.add_argument('--loglevel', '-l',
                        help='Set log level for more/less detailed output',
                        type=str, default="error")

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


def main():
    args = get_args()
    set_log_level(args.loglevel)
    print(f"Welcome to cfbs version {version.string()}")
