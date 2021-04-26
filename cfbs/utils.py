import os
import sys
import json
import copy
from collections import OrderedDict

import requests


def _sh(cmd: str):
    # print(cmd)
    os.system(cmd)


def sh(cmd: str, directory=None):
    if directory:
        _sh(f"( cd {directory} && {cmd} ) 1>/dev/null 2>/dev/null")
        return
    _sh(f"( {cmd} ) 1>/dev/null 2>/dev/null")


def mkdir(path: str):
    os.system(f"mkdir -p {path}")


def touch(path: str):
    os.system(f"touch {path}")


def rm(path: str):
    os.system(f'rm -rf "{path}"')


def cp(src, dst):
    if os.path.isfile(src):
        os.system(f"rsync -r {src} {dst}")
        return
    os.system(f"rsync -r {src}/ {dst}")


def pad_left(s, n) -> int:
    return s if len(s) >= n else " " * (n - len(s)) + s


def pad_right(s, n) -> int:
    return s if len(s) >= n else s + " " * (n - len(s))


def user_error(msg: str):
    sys.exit("Error: " + msg)


def get_json(url: str) -> dict:
    r = requests.get(url)
    assert r.status_code >= 200 and r.status_code < 300
    return r.json()


def strip_right(string, ending):
    if not string.endswith(ending):
        return string
    return string[0 : -len(ending)]


def strip_left(string, beginning):
    if not string.startswith(beginning):
        return string
    return string[len(beginning) :]


def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


def save_file(path, data):
    if "/" in path:
        mkdir("/".join(path.split("/")[0:-1]))
    with open(path, "w") as f:
        f.write(data)


def pretty(data):
    return json.dumps(data, indent=2)


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.loads(f.read(), object_pairs_hook=OrderedDict)
    except FileNotFoundError:
        return None


def write_json(path, data):
    data = pretty(data) + "\n"
    return save_file(path, data)


def merge_json(a, b, overwrite_callback=None, stack=None):
    if not stack:
        stack = []
    a, b = copy.deepcopy(a), copy.deepcopy(b)
    for k, v in b.items():
        if k not in a:
            a[k] = v
        elif isinstance(a[k], dict) and isinstance(v, dict):
            a[k] = merge_json(a[k], v, overwrite_callback, [*stack, k])
        elif type(a[k]) is not type(v):
            if overwrite_callback:
                overwrite_callback(k, stack, "type mismatch")
            a[k] = v
        elif type(v) is list:
            a[k].extend(v)
        else:
            if overwrite_callback:
                overwrite_callback(k, stack, "primitive overwrite")
            a[k] = v

    return a
