#!/usr/bin/env python3
"""CFEngine Package Manager"""

__authors__    = ["Ole Herman Schumacher Elgesem"]

import os
import sys
import argparse
import json
from bs4 import BeautifulSoup
from collections import OrderedDict

def dump_to_file(data, filename):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)

def load_from_file(filename):
    with open(filename) as f:
        return json.load(f, object_pairs_hook=OrderedDict)
    return None

def getargs():
    parser = argparse.ArgumentParser(description='CFEngine package manager.')
    parser.add_argument('commands', metavar='cmd', type=str, nargs='+',
                        help='the command words')
    parser.add_argument('--verbose', '-v', help='Download TSV files', action="store_true")

    args = parser.parse_args()
    return args

def cfpm(commands, verbose):
    if verbose:
        print("Executing command: "+(" ".join(commands)))
    cfpm_path   = os.path.realpath(__file__)
    cfpm_folder = os.path.dirname(os.path.abspath(cfpm_path))
    packages = load_from_file(cfpm_folder + "/package_list.json")
    if verbose:
        print(json.dumps(packages, indent=True))
    if commands[0] == "list":
        for key in packages:
            print(key)
    if commands[0] == "install":
        package_name = commands[1]
        url = packages[package_name]["url"]
        curl_monster = "curl -L " + url + " -o /tmp/master.zip && unzip /tmp/master.zip -d /tmp/ && make -C /tmp/" + package_name +  "-master install"
        os.system(curl_monster)


if __name__ == '__main__':
    args = getargs()
    cfpm(args.commands, args.verbose)
