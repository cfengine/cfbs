#!/usr/bin/env python3
"""cfbs_config.py - Logic for manipulating a project / cfbs.json config file.

TODOs:
- A lot of the code which is currently inside some long commands in commands.py
  should be moved here.
- CFBSConfig.add() logic needs a good refactoring. It has a lot more code than
  necessary duplicated for slightly different cases (URL vs index vs provides
  vs dependencies). It should be rewritten / unified, and split up into a few
  discrete steps:
  1. Collect modules to add (and filter)
  2. Validate modules and abort if the new modules fail validation
  3. Add modules and make commits
"""


import os
import copy
import glob
import logging as log
from collections import OrderedDict
from typing import List, Optional

from cfbs.cfbs_types import CFBSCommandGitResult
from cfbs.utils import (
    CFBSExitError,
    CFBSUserError,
    read_file,
    write_json,
    load_bundlenames,
)
from cfbs.internal_file_management import (
    SUPPORTED_URI_SCHEMES,
    clone_url_repo,
    fetch_archive,
    SUPPORTED_ARCHIVES,
)
from cfbs.pretty import pretty, CFBS_DEFAULT_SORTING_RULES
from cfbs.cfbs_json import CFBSJson
from cfbs.module import Module, is_module_added_manually, is_module_local
from cfbs.prompts import prompt_user, prompt_user_yesno
from cfbs.validate import validate_single_module


# Legacy; do not use. Use the 'CFBSCommandGitResult' namedtuple instead.
class CFBSReturnWithoutCommit(Exception):
    def __init__(self, r: int):
        self.retval = r


def _has_autorun_tag(filename):
    assert os.path.isfile(filename)
    content = read_file(filename)
    assert content is not None
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

    @classmethod
    def get_instance(cls, filename="./cfbs.json", index=None, non_interactive=False):
        if cls.instance is not None:
            if index is not None:
                raise RuntimeError(
                    "Instance of %s already exists, cannot specify index" % cls.__name__
                )
        else:
            cls.instance = cls(
                filename=filename, index=index, non_interactive=non_interactive
            )
        return cls.instance

    @classmethod
    def reload(cls):
        if not cls.instance:
            return
        # Create a new instance with the same __init__ args as last time:
        cls.instance = cls(*cls.instance._reload_args)

    def __init__(self, filename="./cfbs.json", index=None, non_interactive=False):
        self._reload_args = (filename, index, non_interactive)
        super().__init__(path=filename, index_argument=index)
        self.non_interactive = non_interactive

    def save(self):
        data = pretty(self._data, CFBS_DEFAULT_SORTING_RULES) + "\n"
        with open(self.path, "w") as f:
            f.write(data)

    def longest_module_key_length(self, key) -> int:
        return (
            max((len(m.get(key, "")) for m in self["build"]))
            if self.get("build")
            else 0
        )

    def add_with_dependencies(self, module, remote_config=None, added_by="cfbs add"):
        if type(module) is list:
            # TODO: reuse logic from _add_modules instead
            for m in module:
                self.add_with_dependencies(m, remote_config, added_by)
            return
        if type(module) is str:
            module_str = module
            module = (remote_config or self).get_module_for_build(module, added_by)
            if not module:
                raise CFBSExitError("Module '%s' not found" % module_str)
        if not module:
            raise CFBSExitError("Module '%s' not found" % str(module))
        assert "name" in module
        name = module["name"]
        assert "steps" in module
        if self._module_is_in_build(module):
            if is_module_added_manually(added_by):
                print("Skipping already added module '%s'" % name)
            return
        if "dependencies" in module:
            for dep in module["dependencies"]:
                self.add_with_dependencies(dep, remote_config, name)
        assert self._data is not None
        if "build" not in self._data:
            self._data["build"] = []
        self._data["build"].append(module)

        assert "added_by" in module
        added_by = module["added_by"]
        if not is_module_added_manually(added_by):
            print("Added module: %s (Dependency of %s)" % (name, added_by))
        else:
            print("Added module: %s" % name)

    def _add_using_url(
        self,
        url: str,
        to_add: list,
        added_by="cfbs add",
        checksum=None,
        explicit_build_steps=None,
    ):
        url_commit = None
        if url.endswith(SUPPORTED_ARCHIVES):
            config_path, url_commit = fetch_archive(url, checksum)
        else:
            assert url.startswith(SUPPORTED_URI_SCHEMES)
            config_path, url_commit = clone_url_repo(url)

        if "@" in url and (url.rindex("@") > url.rindex(".")):
            assert url.split("@")[-1] == url_commit
            url = url[0 : url.rindex("@")]

        remote_config = CFBSJson(path=config_path, url=url, url_commit=url_commit)

        provides = remote_config.get_provides(added_by)
        add_all = True
        # URL specified in to_add, but no specific modules => let's add all (with a prompt)
        if len(to_add) == 0:
            modules = list(provides.values())
            if not any(modules):
                raise CFBSExitError("no modules available, nothing to do")
            print("Found %d modules in '%s':" % (len(modules), url))
            for m in modules:
                deps = m.get("dependencies", [])
                deps = "" if not deps else " (Depends on: " + ", ".join(deps) + ")"
                print("  - " + m["name"] + deps)
            if len(modules) > 1 and not self.non_interactive:
                if not prompt_user_yesno(
                    non_interactive=self.non_interactive,
                    prompt="Do you want to add all %d of them?" % (len(modules)),
                ):
                    add_all = False
        else:
            missing = [k for k in to_add if k not in provides]
            if missing:
                raise CFBSExitError("Missing modules: " + ", ".join(missing))
            modules = [provides[k] for k in to_add]

        for i, module in enumerate(modules, start=1):
            if not add_all:
                if not prompt_user_yesno(
                    non_interactive=self.non_interactive,
                    prompt="(%d/%d) Do you want to add '%s'?"
                    % (i, len(modules), module["name"]),
                ):
                    continue
            self.add_with_dependencies(module, remote_config, added_by)

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

    def _add_policy_files_build_step(self, module):
        name = module["name"]
        step = "policy_files services/cfbs/" + (
            name[2:] if name.startswith("./") else name
        )
        module["steps"].append(step)
        log.debug("Added build step '%s' for module '%s'" % (step, name))

    def _add_bundles_build_step(self, module, policy_files):
        name = module["name"]
        choices = []
        first = True
        prompt_str = "Which bundle should be evaluated (added to bundle sequence)?"

        for file in policy_files:
            log.debug("Looking for bundles in policy file '%s'" % file)
            for bundle in load_bundlenames(file):
                log.debug("Found bundle '%s'" % bundle)
                choices.append(bundle)
                prompt_str += "\n%2d. %s:%s" % (len(choices), file, bundle)
                if first:
                    prompt_str += " (default)"
                    first = False

        if not choices:
            log.warning("Did not find any bundles to add to bundlesequence")
            return

        choices.append(None)
        prompt_str += "\n%2d. (None)\n" % (len(choices))

        response = prompt_user(
            self.non_interactive,
            prompt_str,
            [str(i + 1) for i in range(len(choices))],
            1,
        )
        bundle = choices[int(response) - 1]
        if bundle is None:
            log.debug("User chose not to add any bundles to the bundlesequence")
            return
        log.debug("User chose to add '%s' to the bundlesequence" % bundle)

        step = "bundles %s" % bundle
        module["steps"].append(step)
        log.debug("Added build step '%s' for module '%s'" % (step, name))

    def _handle_local_module(self, module, use_default_build_steps=True):
        name = module["name"]
        if not (
            name.startswith("./")
            and name.endswith((".cf", "/"))
            and "local" in module["tags"]
        ):
            log.debug("Module '%s' does not appear to be a local module" % name)
            return

        if name.endswith(".cf"):
            policy_files = [name]
        else:
            pattern = "%s/**/*.cf" % name
            policy_files = glob.glob(pattern, recursive=True)

        modules_in_build_key = self.get("build", [])
        assert type(modules_in_build_key) is list
        modules_available = [m.get("name", "") for m in modules_in_build_key]
        is_autorun_enabled = any(
            m in modules_available for m in ["autorun", "./def.json"]
        )  # only a heuristic

        for file in policy_files:
            if _has_autorun_tag(file):
                if not is_autorun_enabled:
                    log.warning(
                        "Found autorun tag in '%s', " % file
                        + "but it looks like the autorun feature is not enabled, consider enabling it via 'cfbs add autorun' or a custom './def.json' file."
                    )
                # TODO: Support adding local modules with autorun tag

        if use_default_build_steps:
            self._add_policy_files_build_step(module)
            self._add_bundles_build_step(module, policy_files)

    def _add_without_dependencies(self, modules, use_default_build_steps=True):
        """Note: `use_default_build_steps` is only relevant for local modules."""
        if not use_default_build_steps:
            assert len(modules) == 1 and modules[0]["name"].startswith(
                "./"
            ), "`use_default_build_steps` is currently only expected to be explicitly used for adding a single local module"

        assert modules
        assert len(modules) > 0
        assert modules[0]["name"]

        for module in modules:
            name = module["name"]
            assert name not in (m["name"] for m in self["build"])
            if "subdirectory" in module and module["subdirectory"] == "":
                del module["subdirectory"]
            if self.index.custom_index is not None:
                module["index"] = self.index.custom_index
            # TODO: This validation could probably be done in a better place,
            #       after we refactor the add logic:
            validate_single_module(
                context="build", name=name, module=module, config=None, local_check=True
            )
            self["build"].append(module)
            self._handle_local_module(module, use_default_build_steps)

            assert "added_by" in module
            added_by = module["added_by"]
            if not is_module_added_manually(added_by):
                print("Added module: %s (Dependency of %s)" % (name, added_by))
            else:
                print("Added module: %s" % name)

    def _add_modules(
        self,
        to_add: list,
        added_by="cfbs add",
        checksum=None,
        explicit_build_steps: Optional[List[str]] = None,
    ):
        """Note: explicit build steps are currently limited to single local modules without dependencies, see the asserts."""
        if explicit_build_steps is not None:
            assert (
                len(to_add) == 1
            ), "explicit_build_steps is only for adding a single module"
            assert is_module_local(
                to_add[0]
            ), "explicit_build_steps is only for adding a local module"

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
            # Everything already added
            return

        # Convert names to objects:
        modules_to_add = [
            index.get_module_object(m, added_by[m.name], explicit_build_steps)
            for m in to_add
        ]
        modules_already_added = self["build"]

        assert not any(m for m in modules_to_add if "name" not in m)
        assert not any(m for m in modules_already_added if "name" not in m)

        # Find all unmet dependencies:
        dependencies = self._find_dependencies(modules_to_add, modules_already_added)

        if dependencies:
            assert (
                explicit_build_steps is None
            ), "explicit build steps do not apply to dependencies"
            self._add_without_dependencies(dependencies)

        self._add_without_dependencies(
            modules_to_add, use_default_build_steps=explicit_build_steps is None
        )

    def add_command(
        self,
        to_add: List[str],
        added_by="cfbs add",
        checksum=None,
        explicit_build_steps: Optional[List[str]] = None,
    ) -> CFBSCommandGitResult:
        if not to_add:
            raise CFBSUserError("Must specify at least one module to add")

        modules_in_build_key = self.get("build", [])
        assert type(modules_in_build_key) is list
        before = {m["name"] for m in modules_in_build_key}

        if to_add[0].startswith(SUPPORTED_URI_SCHEMES):
            self._add_using_url(
                url=to_add[0],
                to_add=to_add[1:],
                added_by=added_by,
                checksum=checksum,
                explicit_build_steps=explicit_build_steps,
            )
        else:
            # for this `if` to be valid, module names containing `://` should be illegal
            if "://" in to_add[0]:
                raise CFBSUserError(
                    "URI scheme not supported. The supported URI schemes are: "
                    + ", ".join(SUPPORTED_URI_SCHEMES)
                )
            self._add_modules(to_add, added_by, checksum, explicit_build_steps)

        added = {m["name"] for m in self["build"]}.difference(before)

        msg = ""
        count = 0
        files = []
        for name in added:
            msg += "\n - Added module '%s'" % name
            count += 1
            if name.startswith("./"):
                files.append(name)

            module = self.get_module_from_build(name)
            assert module is not None, "All added modules should exist in build"
            input_path = os.path.join(".", name, "input.json")
            if "input" in module:
                if os.path.isfile(input_path):
                    log.warning(
                        "There seems to already be input for module '%s'. " % name
                        + "Note that old input may break the module. "
                        + "Please make sure to run 'cfbs input' to re-enter input "
                        + "before building and deploying/installing your project."
                    )
                elif prompt_user_yesno(
                    self.non_interactive,
                    "The added module '%s' accepts user input. " % name
                    + "Do you want to add it now?",
                    default="no",
                ):
                    input_data = copy.deepcopy(module["input"])
                    self.input_command(name, input_data)
                    write_json(input_path, input_data)
                    files.append(input_path)
                    msg += "\n - Added input for module '%s'" % name
        if count > 1:
            msg = "Added %d modules\n" % count + msg
        else:
            msg = msg[4:]  # Remove the '\n - ' part of the message
            # If there are multiple lines, add an additional newline between
            # the short- & long description.
            msg = msg.replace("\n", "\n\n", 1)

        changes_made = count > 0
        return CFBSCommandGitResult(0, changes_made, msg, files)

    def input_command(self, module_name, input_data):
        def _check_keys(keys, input_data):
            for key in keys:
                if key not in input_data:
                    raise CFBSExitError(
                        "Expected attribute '%s' in input definition: %s"
                        % (key, pretty(input_data))
                    )

        def _input_string(input_data):
            _check_keys(["question"], input_data)
            response = prompt_user(
                self.non_interactive,
                input_data["question"],
                default=input_data.get("default"),
            )
            return response

        def _input_elements(subtype):
            result = OrderedDict()
            for element in subtype:
                _check_keys(["type", "label", "question", "key"], element)
                if element["type"] != "string":
                    raise CFBSExitError(
                        "Subtype of type '%s' not supported for type list"
                        % element["type"]
                    )
                result[element["key"]] = _input_string(element)
            return result

        def _input_list(input_data):
            _check_keys(["subtype", "while"], input_data)
            subtype = input_data["subtype"]

            if isinstance(subtype, list):
                result = []

                result.append(_input_elements(subtype))
                while prompt_user_yesno(
                    self.non_interactive, input_data["while"], default="no"
                ):
                    result.append(_input_elements(subtype))
                return result

            elif isinstance(subtype, dict):
                _check_keys(["type", "label", "question"], subtype)
                if subtype["type"] != "string":
                    raise CFBSExitError(
                        "Subtype of type '%s' not supported for type list"
                        % subtype["type"]
                    )
                result = [_input_string(subtype)]
                while prompt_user_yesno(
                    self.non_interactive, input_data["while"], default="no"
                ):
                    result.append(_input_string(subtype))
                return result
            raise CFBSExitError(
                "Expected the value of attribute 'subtype' to be a JSON list or object, not: %s"
                % pretty(input_data["subtype"])
            )

        print("Collecting input for module '%s'" % module_name)
        for definition in input_data:
            _check_keys(["type", "variable", "label"], definition)

            if definition["type"] == "string":
                definition["response"] = _input_string(definition)
            elif definition["type"] == "list":
                definition["response"] = _input_list(definition)
            else:
                raise CFBSExitError("Unsupported input type '%s'" % definition["type"])

        return None
