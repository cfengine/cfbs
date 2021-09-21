import os
import sys
import json
import copy
from collections import OrderedDict
from shutil import rmtree

import requests

from cfbs.pretty import pretty


def _sh(cmd: str):
    # print(cmd)
    r = os.system(cmd)
    if r != 0:
        user_error(f"Command failed - {cmd}")


def sh(cmd: str, directory=None):
    if directory:
        _sh(f"( cd {directory} && {cmd} ) 1>/dev/null 2>/dev/null")
        return
    _sh(f"( {cmd} ) 1>/dev/null 2>/dev/null")


def mkdir(path: str):
    sh(f"mkdir -p {path}")


def touch(path: str):
    if "/" in path:
        above = os.path.dirname(path)
        if not os.path.exists(above):
            mkdir(above)
    sh(f"touch {path}")


def rm(path: str, missing_ok=False):
    if not missing_ok:
        assert os.path.exists(path)
    if os.path.isdir(path):
        rmtree(path)
    if os.path.isfile(path):
        os.remove(path)


def cp(src, dst):
    above = os.path.dirname(dst)
    if not os.path.exists(above):
        mkdir(above)
    if dst.endswith("/") and not os.path.exists(dst):
        mkdir(dst)
    if os.path.isfile(src):
        sh(f"rsync -r {src} {dst}")
        return
    sh(f"rsync -r {src}/ {dst}")


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


def read_json(path):
    try:
        with open(path, "r") as f:
            return json.loads(f.read(), object_pairs_hook=OrderedDict)
    except FileNotFoundError:
        return None
    except json.decoder.JSONDecodeError as ex:
        print("Error reading json file {} : {}".format(path, ex))
        sys.exit(1)


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
