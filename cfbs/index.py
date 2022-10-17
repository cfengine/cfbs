import sys, os
from collections import OrderedDict

from cfbs.module import Module
from cfbs.utils import get_or_read_json, user_error, get_json
from cfbs.internal_file_management import local_module_name

_DEFAULT_INDEX = (
    "https://raw.githubusercontent.com/cfengine/build-index/master/cfbs.json"
)
_VERSION_INDEX = (
    "https://raw.githubusercontent.com/cfengine/build-index/master/versions.json"
)


def _local_module_data_cf_file(module):
    dst = os.path.join("services", "cfbs", module[2:])
    return {
        "description": "Local policy file added using cfbs command line",
        "tags": ["local"],
        "steps": ["copy %s %s" % (module, dst)],
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
    assert module.endswith(("/", "/."))
    dst = os.path.join("services", "cfbs", module[2:])
    return {
        "description": "Local subdirectory added using cfbs command line",
        "tags": ["local"],
        "steps": ["directory ./ {}".format(dst)],
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

    @property
    def custom_index(self) -> str:
        # Index can be initialized with a dict or OrderedDict instead of a url string
        # in which case there would not be an index url to check against the default
        if type(self._unexpanded) is str and self._unexpanded != _DEFAULT_INDEX:
            return self._unexpanded
        else:
            return None

    def exists(self, module):
        if isinstance(module, Module):
            name = module.name
            version = module.version
        else:
            name = module
            version = None

        if os.path.exists(name):
            return True
        if not version:
            return name in self
        versions = get_json(_VERSION_INDEX)
        return name in versions and version in versions[name]

    def check_existence(self, modules: list):
        for module in modules:
            assert isinstance(module, Module)
            if not self.exists(module):
                user_error(
                    "Module '%s'%s does not exist"
                    % (
                        module.name,
                        " version '%s'" % module.version if module.version else "",
                    )
                )

    def translate_aliases(self, modules: list):
        for module in modules:
            self.translate_alias(module)

    def translate_alias(self, module: Module):
        if module.name in self:
            data = self[module.name]
            if "alias" in data:
                print("%s is an alias for %s" % (module.name, data["alias"]))
                module.name = data["alias"]
        else:
            if os.path.exists(module.name):
                module.name = local_module_name(module.name)

    def get_module_object(self, module, added_by=None):
        if isinstance(module, str):
            module = Module(module)
        name = module.name
        version = module.version
        module = module.to_dict()

        if name.startswith("./"):
            object = _generate_local_module_object(name)
        else:
            object = self[name]
            if version:
                versions = get_json(_VERSION_INDEX)
                new_values = versions[name][version]
                specifics = {
                    k: v for (k, v) in new_values.items() if k in Module.attributes()
                }
                object.update(specifics)
                object["version"] = version
        module.update(object)
        if added_by:
            module["added_by"] = added_by
        module.move_to_end("steps")
        return module
