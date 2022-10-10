from collections import OrderedDict

from cfbs.index import Index
from cfbs.utils import read_json, user_error
from cfbs.pretty import pretty


def _construct_provided_module(name, data, url, commit):
    # At this point the @commmit part should be removed from url so:
    # either url should not have an @,
    # or the @ should be for user@host.something
    assert "@" not in url or url.rindex(".") > url.rindex("@")

    module = OrderedDict()
    module["name"] = name
    if "description" not in data:
        user_error(
            "missing required key 'description' in module definition: %s" % pretty(data)
        )
    module["description"] = data["description"]
    module["url"] = url
    module["commit"] = commit
    subdirectory = data.get("subdirectory")
    if subdirectory:
        module["subdirectory"] = subdirectory
    dependencies = data.get("dependencies")
    if dependencies:
        module["dependencies"] = dependencies
    if "input" in data:
        module["input"] = data["input"]
    if "steps" not in data:
        user_error(
            "missing required key 'steps' in module definition: %s" % pretty(data)
        )
    module["steps"] = data["steps"]
    module["added_by"] = "cfbs add"
    return module


class CFBSJson:
    def __init__(
        self,
        path,
        index_argument=None,
        data=None,
        url=None,
        url_commit=None,
    ):
        assert path
        self.path = path
        self.url = url
        self.url_commit = url_commit
        if data:
            self._data = data
        else:
            self._data = read_json(self.path)

        if index_argument:
            self.index = Index(index_argument)
        elif self._data and "index" in self._data:
            self.index = Index(self._data["index"])
        else:
            self.index = Index()

    def get(self, key, default=None):
        if not self._data:  # If the specified JSON file does not exist
            return default
        return self._data.get(key, default)

    def __getitem__(self, key):
        assert key != "index"
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get_provides(self):
        modules = OrderedDict()
        if "provides" not in self._data:
            user_error(
                "missing required key 'provides' in module definition: %s"
                % pretty(self._data)
            )
        for k, v in self._data["provides"].items():
            module = _construct_provided_module(k, v, self.url, self.url_commit)
            modules[k] = module
        return modules

    def get_module_for_build(self, name, dependent):
        if "provides" in self._data and name in self._data["provides"]:
            module = self._data["provides"][name]
            return _construct_provided_module(name, module, self.url, self.url_commit)
        if name in self.index:
            return self.index.get_module_object(name)
        return None

    def _module_is_in_build(self, module):
        return module["name"] in (m["name"] for m in self["build"])

    def get_module_from_build(self, module):
        for m in self["build"]:
            if m["name"] == module:
                return m
        return None
