#!/usr/bin/env python3
import os
import logging as log

from cfbs.utils import (
    user_error,
    read_file,
    find,
)
from cfbs.internal_file_management import (
    clone_url_repo,
    fetch_archive,
    SUPPORTED_ARCHIVES,
)
from cfbs.pretty import pretty
from cfbs.cfbs_json import CFBSJson
from cfbs.module import Module


# Legacy; do not use. Use the 'Result' namedtuple instead.
class CFBSReturnWithoutCommit(Exception):
    def __init__(self, r):
        self.retval = r


def _has_autorun_tag(filename):
    assert os.path.isfile(filename)
    content = read_file(filename)

    return (
        "meta:" in content
        and "tags" in content
        and "slist" in content
        and "autorun" in content
    )


class CFBSConfig(CFBSJson):
    """A singleton class representing the current config"""

    instance = None

    @staticmethod
    def exists(path="./cfbs.json"):
        return os.path.exists(path)

    @staticmethod
    def validate_added_module(module):
        """Try to help the user with warnings in appropriate cases"""

        name = module["name"]
        if name.startswith("./") and name.endswith(".cf"):
            assert os.path.isfile(name)
            if not _has_autorun_tag(name):
                log.warning("No autorun tag found in policy file: '%s'" % name)
                log.warning("Tag the bundle(s) you want evaluated:")
                log.warning('  meta: "tags" slist => { "autorun" };')
            return
        if name.startswith("./") and name.endswith("/"):
            assert os.path.isdir(name)
            policy_files = list(find(name, extension=".cf"))
            with_autorun = (x for x in policy_files if _has_autorun_tag(x))
            if any(policy_files) and not any(with_autorun):
                log.warning("No bundles tagged with autorun found in: '%s'" % name)
                log.warning("Tag the bundle(s) you want evaluated in .cf policy files:")
                log.warning('  meta: "tags" slist => { "autorun" };')

    @classmethod
    def get_instance(cls, index=None, non_interactive=False):
        if cls.instance is not None:
            if index is not None:
                raise RuntimeError(
                    "Instance of %s already exists, cannot specify index" % cls.__name__
                )
        else:
            cls.instance = cls(index, non_interactive)
        return cls.instance

    @classmethod
    def reload(cls):
        if not cls.instance:
            return
        # Create a new instance with the same __init__ args as last time:
        index, non_interactive = cls.instance._reload_args
        cls.instance = cls(index, non_interactive)

    def __init__(self, index=None, non_interactive=False):
        self._reload_args = (index, non_interactive)
        super().__init__(path="./cfbs.json", index_argument=index)
        self.non_interactive = non_interactive

    def save(self):
        data = pretty(self._data) + "\n"
        with open(self.path, "w") as f:
            f.write(data)

    def longest_module_name(self) -> int:
        return max((len(m["name"]) for m in self["build"]))

    def add_with_dependencies(self, module, remote_config=None, dependent=None):
        if type(module) is list:
            # TODO: reuse logic from _add_modules instead
            for m in module:
                self.add_with_dependencies(m, remote_config, dependent)
            return
        if type(module) is str:
            module_str = module
            module = (remote_config or self).get_module_for_build(module, dependent)
        if not module:
            user_error("Module '%s' not found" % module_str)
        assert "name" in module
        assert "steps" in module
        if self._module_is_in_build(module):
            print("Skipping already added module '%s'" % module["name"])
            return
        if "dependencies" in module:
            for dep in module["dependencies"]:
                self.add_with_dependencies(dep, remote_config, module["name"])
        self._data["build"].append(module)
        if dependent:
            print("Added module: %s (Dependency of %s)" % (module["name"], dependent))
        else:
            print("Added module: %s" % module["name"])
        self.validate_added_module(module)

    def _add_using_url(
        self,
        url,
        to_add: list,
        added_by="cfbs add",
        checksum=None,
    ):
        url_commit = None
        if url.endswith(SUPPORTED_ARCHIVES):
            config_path, url_commit = fetch_archive(url, checksum)
        else:
            assert url.startswith(("https://", "git://", "ssh://"))
            config_path, url_commit = clone_url_repo(url)

        if "@" in url and (url.rindex("@") > url.rindex(".")):
            assert url.split("@")[-1] == url_commit
            url = url[0 : url.rindex("@")]

        remote_config = CFBSJson(path=config_path, url=url, url_commit=url_commit)

        provides = remote_config.get_provides()
        # URL specified in to_add, but no specific modules => let's add all (with a prompt)
        if len(to_add) == 0:
            modules = list(provides.values())
            print("Found %d modules in '%s':" % (len(modules), url))
            for m in modules:
                print("  - " + m["name"])
            if not any(modules):
                user_error("no modules available, nothing to do")
            if not self.non_interactive:
                answer = input(
                    "Do you want to add all %d of them? [y/N] " % (len(modules))
                )
                if answer.lower() not in ("y", "yes"):
                    return
        else:
            missing = [k for k in to_add if k not in provides]
            if missing:
                user_error("Missing modules: " + ", ".join(missing))
            modules = [provides[k] for k in to_add]

        for module in modules:
            self.add_with_dependencies(module, remote_config)

    @staticmethod
    def _convert_added_by(added_by, to_add):
        # Convert string -> list:
        if type(added_by) is str:
            added_by = [added_by] * len(to_add)

        # Convert list -> dict:
        if not isinstance(added_by, dict):
            assert len(added_by) == len(to_add)
            added_by = {k.name: v for k, v in zip(to_add, added_by)}

        # Should have a dict with keys for everything in to_add:
        assert not any((k.name not in added_by for k in to_add))

        return added_by

    def _update_added_by(self, requested, added_by):
        for req in requested:
            for mod in self["build"]:
                if req.name == mod["name"]:
                    if added_by[req.name] == "cfbs add":
                        mod["added_by"] = "cfbs add"

    def _filter_modules_to_add(self, modules):
        added = [m["name"] for m in self["build"]]
        filtered = []
        for module in modules:
            assert module not in filtered
            if module.name in added:
                print("Skipping already added module: %s" % module.name)
            else:
                filtered.append(module)
        return filtered

    def _find_dependencies(self, modules, exclude):
        assert type(modules) is list
        assert type(exclude) is list
        exclude = modules + exclude
        exclude_names = [m["name"] for m in exclude]
        index = self.index
        dependencies = []
        for module in modules:
            for dep in module.get("dependencies", []):
                if dep in exclude_names:
                    continue
                m = index.get_module_object(dep, module["name"])
                dependencies.append(m)
                exclude_names.append(dep)
        assert not any(d for d in dependencies if "alias" in d)
        if dependencies:
            dependencies += self._find_dependencies(dependencies, exclude)
        return dependencies

    def _add_without_dependencies(self, modules):
        assert modules
        assert len(modules) > 0
        assert modules[0]["name"]

        for module in modules:
            name = module["name"]
            assert name not in (m["name"] for m in self["build"])
            if self.index.custom_index != None:
                module["index"] = self.index.custom_index
            self["build"].append(module)
            self.validate_added_module(module)

            added_by = module["added_by"]
            if added_by == "cfbs add":
                print("Added module: %s" % name)
            else:
                print("Added module: %s (Dependency of %s)" % (name, added_by))

    def _add_modules(
        self,
        to_add: list,
        added_by="cfbs add",
        checksum=None,
    ) -> int:
        index = self.index

        modules = [Module(m) for m in to_add]
        index.translate_aliases(modules)
        index.check_existence(modules)

        # Convert added_by to dictionary:
        added_by = self._convert_added_by(added_by, modules)

        # If some modules were added as deps previously, mark them as user requested:
        self._update_added_by(modules, added_by)

        # Filter modules which are already added:
        to_add = self._filter_modules_to_add(modules)
        if not to_add:
            return  # Everything already added

        # Convert names to objects:
        modules_to_add = [index.get_module_object(m, added_by[m.name]) for m in to_add]
        modules_already_added = self["build"]

        assert not any(m for m in modules_to_add if "name" not in m)
        assert not any(m for m in modules_already_added if "name" not in m)

        # Find all unmet dependencies:
        dependencies = self._find_dependencies(modules_to_add, modules_already_added)

        if dependencies:
            self._add_without_dependencies(dependencies)

        self._add_without_dependencies(modules_to_add)

    def add_command(
        self,
        to_add: list,
        added_by="cfbs add",
        checksum=None,
    ) -> int:
        if not to_add:
            user_error("Must specify at least one module to add")

        before_adding = len(self["build"])

        if to_add[0].endswith(SUPPORTED_ARCHIVES) or to_add[0].startswith(
            ("https://", "git://", "ssh://")
        ):
            self._add_using_url(
                url=to_add[0],
                to_add=to_add[1:],
                added_by=added_by,
                checksum=checksum,
            )
        else:
            self._add_modules(to_add, added_by, checksum)

        if len(self["build"]) == before_adding:
            # Not an error, we just want to exit successfully without
            # making a git commit
            raise CFBSReturnWithoutCommit(0)

        return 0
