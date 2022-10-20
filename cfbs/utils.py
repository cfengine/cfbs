import os
import re
import sys
import json
import copy
import subprocess
import hashlib
import urllib
import urllib.request  # needed on some platforms
from collections import OrderedDict
from shutil import rmtree

from cfbs.pretty import pretty

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sh(cmd: str):
    # print(cmd)
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        user_error("Command failed - %s\n%s" % (cmd, e.stdout.decode("utf-8")))


def sh(cmd: str, directory=None):
    if directory:
        _sh("cd %s && %s" % (directory, cmd))
        return
    _sh("%s" % cmd)


def mkdir(path: str):
    sh("mkdir -p %s" % path)


def touch(path: str):
    if "/" in path:
        above = os.path.dirname(path)
        if not os.path.exists(above):
            mkdir(above)
    sh("touch %s" % path)


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
        sh("rsync -r %s %s" % (src, dst))
        return
    sh("rsync -r %s/ %s" % (src, dst))


def pad_left(s, n) -> int:
    return s if len(s) >= n else " " * (n - len(s)) + s


def pad_right(s, n) -> int:
    return s if len(s) >= n else s + " " * (n - len(s))


def user_error(msg: str):
    sys.exit("Error: " + msg)


def get_json(url: str) -> OrderedDict:
    with urllib.request.urlopen(url) as r:
        assert r.status >= 200 and r.status < 300
        return json.loads(r.read().decode(), object_pairs_hook=OrderedDict)


def get_or_read_json(path: str) -> OrderedDict:
    if path.startswith("https://"):
        return get_json(path)
    return read_json(path)


def item_index(iterable, item, extra_at_end=True):
    try:
        return iterable.index(item)
    except ValueError:
        if extra_at_end:
            return len(iterable)
        else:
            return -1


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
    except NotADirectoryError:
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


def cfbs_filename() -> str:
    return "cfbs.json"


def is_cfbs_repo() -> bool:
    return os.path.isfile(cfbs_filename())


def path_append(dir, subdir):
    dir = os.path.abspath(os.path.expanduser(dir))
    return dir if not subdir else os.path.join(dir, subdir)


def cfengine_dir(subdir=None):
    return path_append("~/.cfengine/", subdir)


def cfbs_dir(append=None) -> str:
    return os.path.join(cfengine_dir("cfbs"), append if append else "")


class FetchError(Exception):
    pass


def fetch_url(url, target, checksum=None):
    if checksum is not None:
        if SHA1_RE.match(checksum):
            sha = hashlib.sha1()
        elif SHA256_RE.match(checksum):
            sha = hashlib.sha256()
        else:
            raise FetchError(
                "Invalid checksum or unsupported checksum algorithm: '%s'" % checksum
            )
    else:
        sha = hashlib.sha1()

    headers = dict()
    user_agent = os.environ.get("CFBS_USER_AGENT")
    if user_agent is not None:
        headers["User-Agent"] = user_agent
    request = urllib.request.Request(url, headers=headers)
    try:
        with open(target, "wb") as f:
            with urllib.request.urlopen(request) as u:
                if not (200 <= u.status <= 300):
                    raise FetchError("Failed to fetch '%s': %s" % (url, u.reason))
                done = False
                while not done:
                    chunk = u.read(512 * 1024)  # 512 KiB
                    if len(chunk) == 0:
                        done = True
                    else:
                        f.write(chunk)
                        sha.update(chunk)
        digest = sha.digest().hex()
        if checksum is not None:
            if checksum == digest:
                return digest
            else:
                if os.path.exists(target):
                    os.unlink(target)
                raise FetchError(
                    "Checksum mismatch in fetched '%s': %s != %s"
                    % (url, digest, checksum)
                )
        else:
            return digest
    except urllib.error.URLError as e:
        if os.path.exists(target):
            os.unlink(target)
        raise FetchError("Failed to fetch '%s': %s" % (url, e)) from e
    except OSError as e:
        if os.path.exists(target):
            os.unlink(target)
        raise FetchError("Failed to fetch '%s' to '%s': %s" % (url, target, e)) from e


def is_a_commit_hash(commit):
    return bool(SHA1_RE.match(commit) or SHA256_RE.match(commit))


def find(name, recursive=True, directories=False, files=True, extension=None):
    assert files or directories
    assert os.path.isdir(name)
    for root, subdirs, subfiles in os.walk(name):
        if directories:
            for dir in subdirs:
                if not extension or (extension and dir.endswith(extension)):
                    yield os.path.join(root, dir) + "/"
        if files:
            for file in subfiles:
                if not extension or (extension and file.endswith(extension)):
                    yield os.path.join(root, file)
        if not recursive:
            return  # End iteration after looking through first (top) level


def cache(func):
    """Memoization decorator similar to functools.cache (Python 3.9+)"""
    memo = {}

    def wrapper(*args, **kwargs):
        kwargs = OrderedDict(sorted(kwargs.items()))
        key = str({"args": args, "kwargs": kwargs})
        if key not in memo:
            memo[key] = func(*args, **kwargs)
        return memo[key]

    return wrapper


def canonify(s: str):
    s = "".join([c if c.isalnum() else "_" for c in s])
    return s


def load_bundlenames(file: str):
    with open(file, "r") as f:
        policy = f.read()
    return loads_bundlenames(policy)


def loads_bundlenames(policy: str):
    # The lookbehind only supports fixed length strings
    policy = re.sub(r"[ \t]+", " ", policy)

    regex = r"(?<=^bundle agent )[a-zA-Z0-9_\200-\377]+"
    return re.findall(regex, policy, re.MULTILINE)
