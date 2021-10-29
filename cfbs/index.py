#!/usr/bin/env python3
import os
import sys

from cfbs.utils import (
    cfbs_dir,
    user_error,
    strip_left,
    strip_right,
    pad_right,
    get_json,
    write_json,
    read_json,
    get_or_read_json,
    merge_json,
    mkdir,
    touch,
    rm,
    cp,
    sh,
    cfengine_dir,
)


def _local_module_data_cf_file(module):
    target = os.path.basename(module)
    return {
        "description": "Local policy file added using cfbs command line",
        "tags": ["local"],
        "dependencies": ["autorun"],
        "steps": ["copy %s services/autorun/%s" % (module, target)],
        "added_by": "cfbs add",
    }


def _local_module_data_json_file(module):
    return {
        "description": "Local augments file added using cfbs command line",
        "tags": ["local"],
        "steps": ["json %s def.json" % module],
        "added_by": "cfbs add",
    }


def _local_module_data_subdir(module):
    assert module.startswith("./")
    dst = os.path.join("services", "cfbs", module[2:])
    return {
        "description": "Local subdirectory added using cfbs command line",
        "tags": ["local"],
        "steps": ["directory {} {}".format(module, dst)],
        "added_by": "cfbs add",
    }


def generate_index_for_local_module(module):
    assert module.startswith("./")
    assert module.endswith((".cf", ".json", "/"))
    assert os.path.isfile(module) or os.path.isdir(module)

    if os.path.isdir(module):
        return _local_module_data_subdir(module)
    if module.endswith(".cf"):
        return _local_module_data_cf_file(module)
    if module.endswith(".json"):
        return _local_module_data_json_file(module)


class Index:
    def __init__(self, path=None, data=None):
        """If data is not None, path is ignored"""
        self._data = {"index": data} if data else None

        if not self._data:
            if path:
                self.path = path
            else:
                self.path = "https://raw.githubusercontent.com/cfengine/cfbs-index/master/cfbs.json"

    def __contains__(self, key):
        return key in self.get_modules()

    def __getitem__(self, key):
        return self.get_modules()[key]

    def _cache_path(self) -> str:
        return cfbs_dir("cache.json")

    def _get(self) -> dict:
        path = self.path
        if path.startswith("https://"):
            index = get_json(path)
            if not index:
                index = read_json(self._cache_path())
                if index:
                    print("Warning: Downloading index failed, using cache")
        else:
            if not os.path.isfile(path):
                sys.exit("Index does not exist at: '%s'" % path)
            index = read_json(path)
        if not index:
            sys.exit("Could not download or find module index")
        if "index" not in index:
            sys.exit("Empty or invalid module index")
        return index

    def get(self) -> dict:
        if not self._data:
            self._data = self._get()
        return self._data

    def get_modules(self) -> dict:
        return self.get()["index"]

    def exists(self, module):
        return os.path.exists(module) or (module in self)

    def get_build_step(self, module):
        return (
            self.get_modules()[module]
            if not module.startswith("./")
            else generate_index_for_local_module(module)
        )


def _expand_index(thing):
    assert type(thing) in (dict, list, str)
    if type(thing) is str:
        return get_or_read_json(thing)["index"]
    return thing


class CFBSConfig:
    def __init__(self, index_argument=None, path="./cfbs.json"):
        if not os.path.exists(path):
            user_error("Could not find required configuration file: '{}'".format(path))
        self.path = path
        self._data = read_json(self.path)
        self._default_index = "https://raw.githubusercontent.com/cfengine/cfbs-index/master/cfbs.json"
        if index_argument:
            self._unexpanded_index = index_argument
        elif "index" in self._data:
            self._unexpanded_index = self._data["index"]
        else:
            self._unexpanded_index = self._default_index

        self._index = None

    @property
    def index(self):
        if not self._index:
            self._index = Index(data = _expand_index(self._unexpanded_index))
        return self._index

    @property
    def using_default_index(self):
        return (self._unexpanded_index == self._default_index)

    def __getitem__(self, key):
        if key == "index":
            return self.index
        return self._data[key]
