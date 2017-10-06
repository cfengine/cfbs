#!/usr/bin/env python3
"""CFEngine Package Manager"""

__authors__    = ["Ole Herman Schumacher Elgesem"]
__copyright__  = ["Northern.tech AS"]

import os
from os.path import dirname, realpath, abspath
import sys
import argparse
import json
import logging as log
from collections import OrderedDict

# Folder discovery and path insertion:

def package_location(module_file_path):
    return abspath( dirname(realpath(module_file_path)) + "/../" )

sys.path.insert(0, package_location(__file__))

from cpm.filesystem import dump_json, print_json, load_json

def user_error(msg):
    print("Error: {}".format(msg))
    sys.exit(-1)

class Folder:
    def __init__(self, path, *args):
        self.path = abspath(realpath(path))
        if len(args) > 0:
            self.path = os.path.join(self.path, *args)
        if os.path.isfile(self.path):
            raise TypeError("'{}' is a file, not folder!".format(self.path))
        os.makedirs(self.path, exist_ok=True)

    def file(self, path, *args):
        return File(self.path, path, *args)

    def folder(self, path, *args):
        return Folder(self.path, path, *args)

class File:
    def __init__(self, path, *args, save=False):
        self.path = abspath(realpath(path))
        if len(args) > 0:
            self.path = os.path.join(self.path, *args)
        if os.path.exists(self.path) and not os.path.isfile(self.path):
            raise TypeError("'{}' is not a file!".format(self.path))
        self.load()
        if save:
            self.save()

    def load(self):
        self.data = load_json(self.path)

    def save(self):
        dump_json(self.data, self.path)

class CPM:
    def __init__(self, root_path):
        self.root = Folder(root_path)
        self.user = Folder(self.root.path, "user")
        self.user.augments = self.user.file("def.json")
        self.user.installed = self.user.file(self.user.path, "installed.json")
        self.packages = Folder(self.root.path, "packages")
        self.package_index = File(self.root.path, "package_index.json")

    def run(self, commands):
        found_result = False
        if commands[0] == "search":
            query = None
            if len(commands) > 1:
                query = commands[1]
            for k in self.package_index.data:
                if not query or query in k:
                    print(k)
                    found_result = True
            if not found_result:
                print("No remote packages found, check your query or update using 'cpm update'")
        elif commands[0] == "list":
            query = None
            if len(commands) > 1:
                query = commands[1]
            for k in self.user.installed.data:
                if not query or query in k:
                    print(k)
                    found_result = True
            if not found_result:
                print("No installed packages found, use 'cpm search' to find new packages")
        elif commands[0] == "install":
            if len(commands) <= 1:
                user_error("No package specified!")
            for pkg in commands[1:]:
                self.install(pkg)

    def download(self, pkg_name):
        print("Downloading '{}'...".format(pkg_name))

    def install(self, pkg_name):
        if pkg_name not in self.package_index.data:
            user_error("Package '{}' not found!".format(pkg_name))
        self.download(pkg_name)
        print("Installing '{}'...".format(pkg_name))


def main(commands):
    c = CPM(package_location(__file__))
    c.run(commands)

def get_args():
    parser = argparse.ArgumentParser(description='CFEngine package manager.')
    parser.add_argument('commands', metavar='cmd', type=str, nargs='+',
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


if __name__ == '__main__':
    args = get_args()
    set_log_level(args.loglevel)
    main(args.commands)
