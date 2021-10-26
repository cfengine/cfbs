#!/usr/bin/env python3
import os
import sys

from cf_remote.paths import cfengine_dir

from cfbs.utils import (
    cfbs_dir,
    user_error,
    get_json,
    strip_left,
    strip_right,
    pad_right,
    write_json,
    read_json,
    merge_json,
    mkdir,
    touch,
    rm,
    cp,
    sh,
)

from cfbs.pretty import pretty_file, pretty


class Index:
    def __init__(self, path):
        self.path = path
        if not self.path:
            self.path = "https://raw.githubusercontent.com/cfengine/cfbs-index/master/cfbs.json"
        self._data = None

    def __contains__(self, key):
        return key in self.get_modules()

    def __getitem__(self, key):
        return self.get_modules()[key]

    def _cache_path(self) -> str:
        return cfbs_dir("index.json")

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
                sys.exit(f"Index does not exist at: '{path}'")
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
            else local_module_data(module)
        )
