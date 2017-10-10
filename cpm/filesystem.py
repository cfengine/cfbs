#!/usr/bin/env python3
"""Functions to save, load and convert dicts, lists, and json"""
import json
import os
from os.path import abspath, realpath, dirname
import sys
from collections import deque, OrderedDict
import logging
from logging import debug, warning, error, critical
from copy import deepcopy, copy
import shutil

def info(msg):
    logging.info(" "+str(msg))

def print_json(data):
    """Prints a dictionary as JSON with indentation."""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def dump_json(data, path):
    """Saves a data structure (dict) to file with indented JSON formatting."""
    folder = os.path.dirname(path)
    if not os.path.exists(folder):
        make_dir(folder)
    with open(path, 'w', encoding="utf-8") as out_file:
        json.dump(data, out_file, indent=2, ensure_ascii=False)

def load_json(path):
    """Opens and reads a JSON file.

    Returns empty dict if file not found.
    Exits if JSON is invalid.
    """
    try:
        with open(path, 'r', encoding="utf-8") as in_file:
            return json.load(in_file, object_pairs_hook=OrderedDict)
    except:
        return OrderedDict()

def jsonify(data):
    return json.dumps(data, indent=2)

def make_dir(folder):
    try:
        os.makedirs(folder, exist_ok=True)
    except PermissionError:
        sys.exit("Permission denied: '{}'".format(folder))

def write_file(data, path):
    make_dir(dirname(path))
    with open(path, "w") as f:
        f.write(str(data))

def is_dict(obj):
    """Returns True if obj is dict or OrderedDict."""
    return type(obj) == dict or type(obj) == OrderedDict

def is_list(obj):
    """Returns True if obj is a list or deque."""
    return type(obj) == list or type(obj) == deque

def jsonify(data):
    return json.dumps(data, indent=2)

def dictify(lst):
    """Create a dictionary based on a list of dicts.

    Keys on the top level are based on the "name" fields
    of each item(dict) in list.
    """
    dictionary = OrderedDict()
    for item in lst:
        dictionary[item["name"]] = item
    return dictionary

def listify(data):
    """Converts a comma separated string into a list.

    Can be passed a string or list of strings.
    In case of list, whitespace is stripped from each element.
    """
    if type(data) == str:
        if "," in data:
            data = data.split(",")
        else:
            data = [data]
    assert type(data) is list
    if len(data) > 0 and type(data[0]) == str:
        data = [x.strip() for x in data]
    data = filter(lambda x: not empty(x), data)
    return list(data)

def write_file(data, path):
    directory = os.path.dirname(path)
    if directory != "" and directory != "./":
        make_dir(directory)
    with open(path, "w") as f:
        f.write(str(data))

def empty(a):
    """Check if a value is empty list, dict, string, None, or similar."""
    return a == "" or a == [] or a == [""] or a == {} or a == None

def combine(a,b):
    if a is None:
        return b
    elif b is None:
        return a
    elif is_dict(a) and is_dict(b):
        res = copy(a)
        for k,v in b.items():
            if k not in res:
                res[k] = v
            else:
                res[k] = combine(v, res[k])
        return res
    elif is_list(a) and is_list(b):
        r = []
        for e in a + b:
            if e not in r:
                r.append(e)
        return r
    elif a == b:
        return a
    else:
        raise TypeError()


class Folder:
    def __init__(self, path, *args, create=True):
        self.path = abspath(realpath(path))
        if args:
            self.path = self.sub_path(*args)
        if os.path.isfile(self.path):
            raise TypeError("'{}' is a file, not folder!".format(self.path))
        if create:
            make_dir(self.path)

    def file(self, path, *args, create=True):
        return File(self.path, path, *args, create=create)

    def folder(self, path, *args, create=True):
        return Folder(self.path, path, *args, create=create)

    def sub_path(self, sub, *args):
        return abspath(os.path.join(self.path, sub, *args))

    def exists(self, sub, *args):
        p = self.sub_path(sub, *args)
        return os.path.exists(p)

    def rm(self):
        shutil.rmtree(self.path)

    def copy(self, dst):
        if os.path.exists(dst.path):
            dst.rm()
        shutil.copytree(self.path, dst.path)

class File:
    def __init__(self, path, *args, create=True):
        self.path = abspath(realpath(path))
        if len(args) > 0:
            self.path = os.path.join(self.path, *args)
        if os.path.exists(self.path) and not os.path.isfile(self.path):
            raise TypeError("'{}' is not a file!".format(self.path))
        self.load()
        if create and not os.path.exists(self.path):
            self.save()

    def copy(self, dst):
        dst.data = self.data
        info("Copy: {} -> {}".format(self.path, dst.path))
        dst.save()

    def apply(self, target_file):
        source = deepcopy(self.data)
        target = deepcopy(target_file.data)
        target_file.data = combine(source, target)
        info("Apply: {} -> {}.".format(self.path, target_file.path))
        info("Result:\n{}".format(json.dumps(target_file.data, indent=2)))
        target_file.save()

    def load(self):
        info("Load: {}".format(self.path))
        self.data = load_json(self.path)

    def save(self):
        info("Save: {}".format(self.path))
        dump_json(self.data, self.path)
