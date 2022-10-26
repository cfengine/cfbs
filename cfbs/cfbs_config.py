#!/usr/bin/env python3
import os
import copy
import glob
import logging as log
from collections import OrderedDict

from cfbs.result import Result
from cfbs.utils import (
    user_error,
    read_file,
    write_json,
    load_bundlenames,
)
from cfbs.internal_file_management import (
    clone_url_repo,
    fetch_archive,
    SUPPORTED_ARCHIVES,
)
from cfbs.pretty import pretty
from cfbs.cfbs_json import CFBSJson
from cfbs.module import Module
from cfbs.prompts import prompt_user, YES_NO_CHOICES


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
        return max((len(m["name"]) for m in self["build"])) if self["build"] else 0

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

    def _handle_local_module(self, module):
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

        for file in policy_files:
            if _has_autorun_tag(file):
                log.warning(
                    "Found bundle tagged with autorun in local policy file '%s': "
                    % file
                    + "Note that the autorun tag is ignored when adding local policy files or subdirectories."
                )
                # TODO: Support adding local modules with autorun tag

        self._add_policy_files_build_step(module)
        self._add_bundles_build_step(module, policy_files)

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
            self._handle_local_module(module)

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

        before = {m["name"] for m in self["build"]}

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

        added = {m["name"] for m in self["build"]}.difference(before)

        msg = ""
        count = 0
        files = []
        for name in added:
            msg += "\n - Added module '%s'" % name
            count += 1

            module = self.get_module_from_build(name)
            input_path = os.path.join(".", name, "input.json")
            if "input" in module:
                if os.path.isfile(input_path):
                    log.warning(
                        "There seems to already be input for module '%s'. " % name
                        + "Note that old input may break the module. "
                        + "Please make sure to run 'cfbs input' to re-enter input "
                        + "before building and depolying/installing your project."
                    )
                elif prompt_user(
                    self.non_interactive,
                    "The added module '%s' accepts user input. " % name
                    + "Do you want to add it now?",
                    YES_NO_CHOICES,
                    "no",
                ).lower() in ("yes", "y"):
                    input_data = copy.deepcopy(module["input"])
                    self.input_command(name, input_data)
                    write_json(input_path, input_data)
                    files.append(input_path)
                    msg += "\n - Added input for module '%s'" % name
        if count > 1:
            msg = "Added %d modules\n" % count + msg
        else:
            msg = msg[4:]  # Remove the '\n - ' part of the message

        changes_made = count > 0
        return Result(0, changes_made, msg, files)

    def input_command(self, module_name, input_data):
        def _check_keys(keys, input_data):
            for key in keys:
                if key not in input_data:
                    user_error(
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
                    user_error(
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
                while prompt_user(
                    self.non_interactive,
                    input_data["while"],
                    choices=YES_NO_CHOICES,
                    default="no",
                ).lower() in ("yes", "y"):
                    result.append(_input_elements(subtype))
                return result

            elif isinstance(subtype, dict):
                _check_keys(["type", "label", "question"], subtype)
                if subtype["type"] != "string":
                    user_error(
                        "Subtype of type '%s' not supported for type list"
                        % subtype["type"]
                    )
                result = [_input_string(subtype)]
                while prompt_user(
                    self.non_interactive,
                    input_data["while"],
                    choices=YES_NO_CHOICES,
                    default="no",
                ).lower() in ("yes", "y"):
                    result.append(_input_string(subtype))
                return result
            user_error(
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
                user_error("Unsupported input type '%s'" % definition["type"])
