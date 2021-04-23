import sys
import json
from collections import OrderedDict

import requests


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
    data = pretty(data)
    return save_file(path, data)
