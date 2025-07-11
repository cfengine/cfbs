import os
import re
import sys
import json
import copy
import subprocess
import hashlib
import urllib
import urllib.request  # needed on some platforms
import urllib.error
from collections import OrderedDict
from shutil import rmtree
from typing import Union

from cfbs.pretty import pretty

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CFBSProgrammerError(RuntimeError):
    """Exception to use for cases where we as developers made a mistake.

    Situations which should never happen - similar to assertions.
    """

    pass


class CFBSExitError(Exception):
    """Generic errors which make the program exit.

    Most of these should be converted to more specific exception types."""

    pass


class CFBSUserError(Exception):
    """Exception for when the user did something wrong, such as specifying a file which does not exist."""

    pass


class CFBSNetworkError(Exception):
    """Errors which generally can be attributed to a server or router being offline.

    Usually we'll advise the user to check their Wifi / network settings and/or try again later.
    """

    pass


class CFBSValidationError(Exception):
    """Exception for when validation fails.

    Commonly this means some fields / values are wrong in cfbs.json, or that the referenced
    files / modules don't exist.

    Mostly used by validate.py / cfbs validate command, but can be used in other places for
    the same purpose.

    For example: If you inside the cfbs build logic want to check that "steps" exists,
    you can raise a validation error if it doesn't. However, if you believe other
    validation logic should have already checked this and it's not possible,
    an assertion or programmer error is more appropriate."""

    def __init__(self, name_or_message, message=None) -> None:
        assert name_or_message
        if message:
            name = name_or_message
        else:
            name = None
            message = name_or_message
        if name is None:
            super().__init__("Error in cfbs.json: " + message)
        elif type(name) is int:
            super().__init__(
                "Error in cfbs.json for module at index %d: " % name + message
            )
        else:
            super().__init__("Error in cfbs.json for module '%s': " % name + message)


def _sh(cmd: str):
    # print(cmd)
    try:
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        raise CFBSExitError("Command failed - %s\n%s" % (cmd, e.stdout.decode("utf-8")))


def sh(cmd: str, directory=None):
    if directory:
        _sh("cd %s && %s" % (directory, cmd))
        return
    _sh("%s" % cmd)


def mkdir(path: str, exist_ok=True):
    os.makedirs(path, exist_ok=exist_ok)


def touch(path: str):
    if "/" in path:
        above = os.path.dirname(path)
        if not os.path.exists(above):
            mkdir(above)
    sh("touch %s" % path)


def rm(path: str, missing_ok=False):
    if not missing_ok:
        assert os.path.exists(path)
    if missing_ok and not os.path.exists(path):
        return False
    if os.path.isdir(path):
        rmtree(path)
    else:  # Assume path is a file
        os.remove(path)  # Will raise exception if missing
    return True


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


def pad_left(s, n):
    return s.rjust(n)


def pad_right(s, n):
    return s.ljust(n)


def get_json(url: str) -> OrderedDict:
    try:
        with urllib.request.urlopen(url) as r:
            assert r.status >= 200 and r.status < 300
            return json.loads(r.read().decode(), object_pairs_hook=OrderedDict)
    except urllib.error.URLError as e:
        raise CFBSNetworkError("Failed to get JSON from '%s'" % url) from e


def get_or_read_json(path: str) -> Union[OrderedDict, None]:
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
    # can be replaced with str.removesuffix from Python 3.9 onwards
    if not string.endswith(ending):
        return string
    return string[0 : -len(ending)]


def strip_left(string, beginning):
    # can be replaced with str.removeprefix from Python 3.9 onwards
    if not string.startswith(beginning):
        return string
    return string[len(beginning) :]


def strip_right_any(string, suffixes):
    for suffix in suffixes:
        if string.endswith(suffix):
            return string[0 : -len(suffix)]

    return string


def strip_left_any(string, prefixes):
    for prefix in prefixes:
        if string.startswith(prefix):
            return string[len(prefix) :]

    return string


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


def read_json(path) -> Union[OrderedDict, None]:
    try:
        with open(path, "r") as f:
            return json.loads(f.read(), object_pairs_hook=OrderedDict)
    except FileNotFoundError:
        return None
    except IsADirectoryError:
        return None
    except NotADirectoryError:
        return None
    except json.decoder.JSONDecodeError as ex:
        print("Error reading json file '{}': {}".format(path, ex))
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


def deduplicate_def_json(d):
    if "inputs" in d:
        d["inputs"] = deduplicate_list(d["inputs"])
    if "augments" in d:
        d["augments"] = deduplicate_list(d["augments"])

    for variable in d.get("variables", {}).values():
        if type(variable) is not dict:
            continue
        if "tags" in variable:
            variable["tags"] = deduplicate_list(variable["tags"])

    for class_name, class_v in d.get("classes", {}).items():
        if type(class_v) is dict:
            if "class_expressions" in class_v:
                class_v["class_expressions"] = deduplicate_list(
                    class_v["class_expressions"]
                )
            if "tags" in class_v:
                class_v["tags"] = deduplicate_list(class_v["tags"])
        elif type(class_v) is list:
            d["classes"][class_name] = deduplicate_list(class_v)

    # TODO: "vars" can have "augments_inputs", perhaps it could be deduplicated too

    return d


def deduplicate_list(original):
    return list(OrderedDict.fromkeys(original))


def dict_sorted_by_key(the_dict):
    sorted_dict = OrderedDict(sorted(the_dict.items()))

    return sorted_dict


def dict_diff(A, B):
    """Returns three sorted lists:
    * first: list of keys only in `A`
    * second: list of keys only in `B`
    * third: list of tuples `(k, A[k], B[k])` for keys `k` in both with differing values
    """
    keys_A = set(A.keys())
    keys_B = set(B.keys())
    keys_in_both = keys_A & keys_B
    keys_only_A = keys_A - keys_in_both
    keys_only_B = keys_B - keys_in_both

    values_different = set((k, A[k], B[k]) for k in keys_in_both if A[k] != B[k])

    keys_only_A = sorted(keys_only_A)
    keys_only_B = sorted(keys_only_B)
    values_different = sorted(values_different)

    return keys_only_A, keys_only_B, values_different


def cfbs_filename() -> str:
    return "cfbs.json"


def is_cfbs_repo() -> bool:
    return os.path.isfile(cfbs_filename())


def immediate_subdirectories(path):
    foldernames = [f.name for f in os.scandir(path) if f.is_dir()]

    # `os.scandir` returns the entries in arbitrary order, so sort for determinism
    return sorted(foldernames)


def immediate_files(path):
    filenames = [f.name for f in os.scandir(path) if not f.is_dir()]

    # `os.scandir` returns the entries in arbitrary order, so sort for determinism
    return sorted(filenames)


def path_append(dir, subdir):
    return dir if not subdir else os.path.join(dir, subdir)


def canonical_path(path):
    return os.path.normcase(os.path.realpath(path))


def are_paths_equal(path_a, path_b) -> bool:
    canon_path_a = canonical_path(path_a)
    canon_path_b = canonical_path(path_b)

    return canon_path_a == canon_path_b


def cfengine_dir(subdir=None):
    CFENGINE_DIR = "~/.cfengine/"
    cfengine_dir_abspath = os.path.abspath(os.path.expanduser(CFENGINE_DIR))

    return path_append(cfengine_dir_abspath, subdir)


def cfbs_dir(append=None) -> str:
    directory = os.getenv("CFBS_GLOBAL_DIR")
    if directory:
        # Env var was set, make it absolute,
        # same as in cfengine_dir() / path_append() above.
        directory = os.path.abspath(os.path.expanduser(directory))
    else:
        # Env var not set, use default.
        directory = cfengine_dir("cfbs")  # Already absolute
    if not append:
        return directory
    return os.path.join(directory, append)


def string_sha256(input):
    return hashlib.sha256(input.encode("utf-8")).hexdigest()


def file_sha256(file):
    h = hashlib.sha256()

    with open(file, "rb") as f:
        h.update(f.read())

    return h.hexdigest()


def fetch_url(url, target, checksum=None):
    if checksum is not None:
        if SHA1_RE.match(checksum):
            sha = hashlib.sha1()
        elif SHA256_RE.match(checksum):
            sha = hashlib.sha256()
        else:
            raise CFBSNetworkError(
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
                    raise CFBSNetworkError("Failed to fetch '%s': %s" % (url, u.reason))
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
                raise CFBSNetworkError(
                    "Checksum mismatch in fetched '%s': %s != %s"
                    % (url, digest, checksum)
                )
        else:
            return digest
    except urllib.error.URLError as e:
        if os.path.exists(target):
            os.unlink(target)
        raise CFBSNetworkError("Failed to fetch '%s': %s" % (url, e)) from e
    except OSError as e:
        if os.path.exists(target):
            os.unlink(target)
        raise CFBSNetworkError(
            "Failed to fetch '%s' to '%s': %s" % (url, target, e)
        ) from e


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
