"""cfbs_json.py - Simple read-only abstraction of a cfbs.json file

Don't put code which makes changes to cfbs.json here, that should
go in cfbs_config.py.

TODOs:
1. Code related to validation should be moved to validate.py.
   For example warn_about_unknown_keys(). Validation code
   should just take "raw data" (JSON dicts) and not be coupled
   with cfbs_json.py nor cfbs_config.py.
"""

from collections import OrderedDict
from copy import deepcopy
import logging as log

from cfbs.index import Index
from cfbs.pretty import pretty, TOP_LEVEL_KEYS, MODULE_KEYS
from cfbs.utils import CFBSValidationError, read_json, CFBSExitError


def _construct_provided_module(name, data, url, commit, added_by="cfbs add"):
    # At this point the @commit part should be removed from url so:
    # either url should not have an @,
    # or the @ should be for user@host.something
    assert "@" not in url or url.rindex(".") > url.rindex("@")

    module = OrderedDict()
    module["name"] = name
    if "description" not in data:
        raise CFBSExitError(
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
        raise CFBSExitError(
            "missing required key 'steps' in module definition: %s" % pretty(data)
        )
    module["steps"] = data["steps"]
    module["added_by"] = added_by
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

    @property
    def raw_data(self):
        """Read-only access to the original data, for validation purposes"""
        return deepcopy(self._data)

    def _find_all_module_objects(self):
        data = self.raw_data
        assert data is not None
        modules = []
        if "index" in data and type(data["index"]) in (dict, OrderedDict):
            modules += data["index"].values()
        if "provides" in data and type(data["provides"]) in (dict, OrderedDict):
            modules += data["provides"].values()
        if "build" in data and type(data["build"]) is list:
            modules += data["build"]
        return modules

    def warn_about_unknown_keys(self, raise_exceptions=False):
        """Basic validation to warn the user when a cfbs.json has unknown keys.

        Unknown keys are typically due to
        typos, or an outdated version of cfbs. This basic type of
        validation only produces warnings (we want cfbs build to still work),
        and is run for various cfbs commands, not just cfbs build / validate.
        For the more complete validation, see validate.py.
        """

        data = self.raw_data
        if not data:
            return  # No data, no unknown keys

        for key in data:
            if key not in TOP_LEVEL_KEYS:
                msg = (
                    'The top level key "%s" is not known to this version of cfbs.\n'
                    + "Is it a typo? If not, try upgrading cfbs:\n"
                    + "pip3 install --upgrade cfbs"
                )
                if raise_exceptions:
                    raise CFBSValidationError(msg)
                log.warning(msg)
        already_printed = []
        for module in self._find_all_module_objects():
            for key in module:
                if key in already_printed:
                    continue
                if key not in MODULE_KEYS:
                    msg = (
                        'The module level key "%s" is not known to this version of cfbs.\n'
                        % key
                        + "Is it a typo? If not, try upgrading cfbs:\n"
                        + "pip3 install --upgrade cfbs"
                    )
                    if raise_exceptions:
                        raise CFBSValidationError(msg)
                    log.warning(msg)
                    already_printed.append(key)

    def _get_all_module_names(self, search_in=("build", "provides", "index")):
        modules = []

        if "build" in search_in and "build" in self:
            modules.extend((x["name"] for x in self["build"]))
        if "provides" in search_in and "provides" in self:
            modules.extend(self["provides"].keys())
        if "index" in search_in:
            modules.extend(self.index.keys())

        return modules

    def can_reach_dependency(self, name, search_in=("build", "provides", "index")):
        return name in self._get_all_module_names(search_in)

    def find_module(self, name, search_in=("build", "provides", "index")):
        if "build" in search_in and "build" in self:
            for module in self["build"]:
                if module["name"] == name:
                    return module
        if "provides" in search_in and "provides" in self and name in self["provides"]:
            return self["provides"][name]
        if "index" in search_in and name in self.index:
            return self.index[name]

    def get(self, key, default=None):
        if not self._data:  # If the specified JSON file does not exist
            return default
        return self._data.get(key, default)

    def __getitem__(self, key):
        assert key != "index"
        assert self._data is not None
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def get_provides(self, added_by="cfbs add"):
        modules = OrderedDict()
        assert self._data is not None
        if "provides" not in self._data:
            raise CFBSExitError(
                "missing required key 'provides' in module definition: %s"
                % pretty(self._data)
            )
        for k, v in self._data["provides"].items():
            module = _construct_provided_module(
                k, v, self.url, self.url_commit, added_by
            )
            modules[k] = module
        return modules

    def get_module_for_build(self, name, added_by="cfbs add"):
        assert self._data is not None
        if "provides" in self._data and name in self._data["provides"]:
            module = self._data["provides"][name]
            return _construct_provided_module(
                name, module, self.url, self.url_commit, added_by
            )
        if name in self.index:
            return self.index.get_module_object(name, added_by)
        return None

    def _module_is_in_build(self, module):
        return "build" in self and module["name"] in (m["name"] for m in self["build"])

    def get_module_from_build(self, module):
        for m in self["build"]:
            if m["name"] == module:
                return m
        return None
