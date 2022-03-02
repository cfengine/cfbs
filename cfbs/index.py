import sys, os
from collections import OrderedDict

from cfbs.utils import get_or_read_json, user_error
from cfbs.internal_file_management import local_module_name

_DEFAULT_INDEX = (
    "https://raw.githubusercontent.com/cfengine/build-index/master/cfbs.json"
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


def _generate_local_module_object(module):
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
    """Class representing the cfbs.json containing the index of available modules"""

    def __init__(self, index=_DEFAULT_INDEX):
        self._unexpanded = index
        self._data = None

    def __contains__(self, key):
        return key in self.data["index"]

    def __getitem__(self, key):
        return self.data["index"][key]

    def items(self):
        return self.data["index"].items()

    def get(self, key, default=None):
        return self.data["index"].get(key, default)

    def _expand_index(self):
        index = self._unexpanded
        if type(index) in (dict, OrderedDict):
            self._data = {"type": "index", "index": index}
            return

        assert type(index) is str

        self._data = get_or_read_json(index)

        if not self._data:
            sys.exit("Could not download or find module index")
        if "index" not in self._data:
            sys.exit("Empty or invalid module index")

    @property
    def data(self) -> dict:
        if not self._data:
            self._expand_index()
        return self._data

    def exists(self, module):
        return os.path.exists(module) or (module in self)

    def check_existence(self, modules):
        for module in modules:
            if not self.exists(module):
                user_error("Module '%s' does not exist" % module)

    def translate_aliases(self, modules):
        translated = []
        for module in modules:
            if not module in self and os.path.exists(module):
                translated.append(local_module_name(module))
                continue
            if module not in self:
                translated.append(module)
                continue  # Will error later
            data = self[module]
            if "alias" in data:
                print("%s is an alias for %s" % (module, data["alias"]))
                module = data["alias"]
            translated.append(module)
        return translated

    def get_module_object(self, name, added_by=None):
        module = OrderedDict({"name": name})
        if name.startswith("./"):
            object = _generate_local_module_object(name)
        else:
            object = self[name]
        module.update(object)
        if added_by:
            module["added_by"] = added_by
        module.move_to_end("steps")
        return module
