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
import io
import zipfile
import requests
import shutil
from collections import OrderedDict
from contextlib import closing

# Folder discovery and path insertion:

def package_location(module_file_path):
    return abspath( dirname(realpath(module_file_path)) + "/../" )

sys.path.insert(0, package_location(__file__))

from cpm.filesystem import File, Folder

def user_error(msg):
    print("Error: {}".format(msg))
    sys.exit(-1)

def yes_or_no(msg):
    x = input("{}(y/n) ".format(msg)).lower()
    while x not in ["y", "n", "yes", "no"]:
        x = input("Please answer yes or no: ")
    if x == "yes" or x == "y":
        return "yes"
    else:
        return "no"

def get_index(seq, index):
    try:
        return seq[index]
    except IndexError:
        return None

class CPM:
    def __init__(self, root_path):
        self.root = Folder(root_path)
        self.package_index  = self.root.file("package_index.json")
        self.package_alias  = self.root.file("package_alias.json")

        self.user           = self.root.folder("user")
        self.user.def_json  = self.user.file("def.json")
        self.user.installed = self.user.file("installed.json")
        self.user.config    = self.user.file("config.json")
        self.user.packages  = self.user.folder("packages")

        self.user.install   = self.user.folder("install")
        self.user.download  = self.user.folder("download")

        self.cfe            = Folder("/var/cfengine")
        self.cfe.mpf        = self.cfe.folder("masterfiles")
        self.cfe.mpf.def_json = self.cfe.mpf.file("def.json")
        self.cfe.cfe        = self.cfe.folder("masterfiles")
        self.cfe.mpf.services = self.cfe.folder("services")

    def search(self, query=None, data=None):
        if data is None:
            data = self.package_index.data
        results = []
        for k in data:
            if not query or query in k:
                results.append(k)
        return results

    def system_apply(self):
        self.user.def_json.copy(self.cfe.mpf.def_json)

    def run(self, commands):
        cmd = commands[0]
        if cmd == "search":
            query = get_index(commands, 1)
            results = self.search(query)
            [print(x) for x in results]
            if not results:
                print("No remote packages found, check your query or update using 'cpm update'")
        elif cmd == "list":
            query = get_index(commands, 1)
            results = self.search(query, self.user.installed.data)
            [print(x) for x in results]
            if not results:
                print("No installed packages found, use 'cpm search' to find new packages")
        elif cmd == "install":
            if len(commands) <= 1:
                user_error("No package specified!")
            for pkg in commands[1:]:
                self.install(pkg)
        elif cmd == "apply":
            if len(commands) <= 1:
                for pkg_name in self.user.installed.data:
                    self.apply(pkg_name)
            else:
                for pkg_name in commands[1:]:
                    self.apply(pkg_name)
            self.system_apply()
        else:
            user_error("Command not found: '{}'".format(cmd))

    def download_zip(self, pkg):
        url = pkg["zip"]
        name = pkg["name"]
        r = requests.get(url, stream=True)
        with closing(r), zipfile.ZipFile(io.BytesIO(r.content)) as archive:
            tmp_dir = self.user.folder("tmp")
            archive.extractall(path=tmp_dir.path)
            folder_name = [member for member in archive.infolist()][0].filename[:-1]

        src = tmp_dir.folder(folder_name)
        dst = self.user.packages.folder(name, create=False)

        src.copy(dst)
        src.rm()
        self.user.installed.data[name] = pkg
        self.user.installed.save()
        return dst

    def download_git(self, pkg):
        url = pkg["git"]
        name = pkg["name"]
        git_folder = pkg["git_folder"]
        download_loc = self.user.download.sub_path(git_folder)
        if os.path.exists(download_loc):
            os.system("cd {} && git pull".format(download_loc))
        else:
            os.system("cd {} && git clone {}".format(self.user.download.path,
                                                     url))
        pkg_folder = Folder(download_loc)
        if "subfolder" in pkg:
            pkg_folder = pkg_folder.folder(pkg["subfolder"])

        dst = self.user.packages.folder(name)
        pkg_folder.copy(dst)
        return dst


    def download(self, pkg):
        print("Downloading '{}'...".format(pkg["name"]))
        if "zip" in pkg:
            return self.download_zip(pkg)
        elif "git" in pkg:
            return self.download_git(pkg)
        else:
            raise NotImplementedError()

    def config_auto_apply(self):
        m = "Do you want cpm to automatically apply installed packages to CFEngine folders?"
        self.user.config.data["auto_apply"] = yes_or_no(m)
        self.user.config.save()

    def import_def_json(self):
        self.cfe.mpf.def_json.copy(self.user.def_json)

    def config_import_def_json(self):
        m = "Do you want to import your existing def.json file?"
        self.user.config.data["import_def_json"] = x = yes_or_no(m)
        self.user.config.save()
        if x == "yes":
            self.import_def_json()

    def config_prompts(self):
        if "auto_apply" not in self.user.config.data:
            self.config_auto_apply()
        if ("import_def_json" not in self.user.config.data
            and not self.user.def_json
            and self.cfe.mpf.def_json.data):
            self.config_import_def_json()

    def get_pkg_name(self, pkg_name):
        if pkg_name in self.package_index.data:
            return pkg_name
        if pkg_name in self.package_alias.data:
            return self.package_alias.data[pkg_name]
        return None

    def install_make(self, folder_path):
        os.system("make -C {} install".format(folder_path))

    def install_def(self, folder_path):
        target_def = self.user.install.file("def.json")
        source_def = Folder(folder_path).file("def.json")
        source_def.apply(target_def)

    def apply(self, pkg_name_user):
        pkg_name = self.get_pkg_name(pkg_name_user)
        if not pkg_name:
            user_error("Package '{}' not found!".format(pkg_name_user))

        print("Installing '{}'...".format(pkg_name))
        pkg = self.package_index.data[pkg_name]
        folder = self.user.packages.folder(pkg_name)
        for installer in pkg["installers"]:
            if installer == "make":
                self.install_make(folder.path)
            elif installer == "def":
                self.install_def(folder.path)
            else:
                print("Installer '{}' is not implemented.".format(installer))
        print("Finished installer(s) for '{}'.".format(pkg_name))

    def install(self, pkg_name_user):
        self.config_prompts()
        pkg_name = self.get_pkg_name(pkg_name_user)
        if not pkg_name:
            user_error("Package '{}' not found!".format(pkg_name_user))
        pkg = self.package_index.data[pkg_name]
        self.download(pkg)
        if "installers" not in pkg or not pkg["installers"]:
            print("Warning: The package '{}' has no automatic installer.".format(pkg["name"]))
            print("         Consult the package README for installation instructions.")
            return
        auto = self.user.config.data["auto_apply"]
        if auto == "yes" or auto == "y" or auto == True:
            self.apply(pkg_name)
        else:
            print("Package installers skipped (auto_apply is off).")
            print("Use 'cpm apply {}' to run the installer for this package".format(pkg_name_user))

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
