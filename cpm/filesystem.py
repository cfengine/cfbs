#!/usr/bin/env python3
"""Functions to save, load and convert dicts, lists, and json"""
import json
import os
import sys
from collections import deque, OrderedDict
from logging import debug, info, warning, error, critical

def print_json(data):
    """Prints a dictionary as JSON with indentation."""
    print(json.dumps(data, indent=2, ensure_ascii=False))

def dump_json(data, path):
    """Saves a data structure (dict) to file with indented JSON formatting."""
    folder = os.path.dirname(path)
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
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

def write_file(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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
        os.makedirs(directory, exist_ok=True)
    with open(path, "w") as f:
        f.write(str(data))

def empty(a):
    """Check if a value is empty list, dict, string, None, or similar."""
    return a == "" or a == [] or a == [""] or a == {} or a == None
