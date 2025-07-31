import copy
import os
import logging as log

from cfbs.prompts import prompt_user_yesno
from cfbs.utils import read_json, CFBSExitError, write_json


class ModuleUpdates:

    def __init__(self, config):
        self.new_deps = []
        self.new_deps_added_by = dict()
        self.changes_made = False
        self.files = []
        self.config = config
        self.msg = ""


class InputDataUpdateFailed(Exception):
    def __init__(self, message):
        super().__init__(message)


def update_input_data(module, input_data) -> bool:
    """
    Update input data from module definition

    :param module: Module with updated input definition
    :param input_data: Input data to update
    :return: True if changes are made
    """
    module_name = module["name"]
    input_def = module["input"]

    if len(input_def) != len(input_data):
        raise InputDataUpdateFailed(
            "Failed to update input data for module '%s': " % module_name
            + "Input definition has %d variables, " % len(input_def)
            + "while current input data has %d variables." % len(input_data)
        )

    def _update_keys(input_def, input_data, keys):
        """
        Update keys that can be safily updated in input data.
        """
        changes_made = False
        for key in keys:
            new = input_def.get(key)
            old = input_data.get(key)
            if new != old:
                # Make sure that one of the keys are not 'None'
                if new is None or old is None:
                    raise InputDataUpdateFailed(
                        "Failed to update input data for module '%s': " % module_name
                        + "Missing matching attribute '%s'." % key
                    )
                input_data[key] = input_def[key]
                changes_made = True
                log.warning(
                    "Updated attribute '%s' from '%s' to '%s' in module '%s'."
                    % (key, old, new, module_name)
                )
        return changes_made

    def _check_keys(input_def, input_data, keys):
        """
        Compare keys that cannot safily be updated for equality.
        """
        for key in keys:
            new = input_def.get(key)
            old = input_data.get(key)
            if new != old:
                raise InputDataUpdateFailed(
                    "Failed to update input data for module '%s': " % module_name
                    + "Updating attribute '%s' from '%s' to '%s'," % (key, old, new)
                    + "may cause module to break."
                )

    def _update_variable(input_def, input_data):
        _check_keys(input_def, input_data, ("type", "namespace", "bundle", "variable"))
        changes_made = _update_keys(
            input_def, input_data, ("label", "comment", "question", "while", "default")
        )

        if input_def["type"] == "list":
            def_subtype = input_def["subtype"]
            data_subtype = input_data["subtype"]
            if type(def_subtype) is not type(data_subtype):
                raise InputDataUpdateFailed(
                    "Failed to update input data for module '%s': " % module_name
                    + "Different subtypes in list ('%s' != '%s')."
                    % (type(def_subtype).__name__, type(data_subtype).__name__)
                )
            if isinstance(def_subtype, list):
                if len(def_subtype) != len(data_subtype):
                    raise InputDataUpdateFailed(
                        "Failed to update input data for module '%s': " % module_name
                        + "Different amount of elements in list ('%s' != '%s')."
                        % (len(def_subtype), len(data_subtype))
                    )
                for i in range(len(def_subtype)):
                    _check_keys(def_subtype[i], data_subtype[i], ("key", "type"))
                    changes_made |= _update_keys(
                        def_subtype[i],
                        data_subtype[i],
                        ("label", "question", "default"),
                    )
            elif isinstance(def_subtype, dict):
                _check_keys(def_subtype, data_subtype, ("type",))
                changes_made |= _update_keys(
                    def_subtype, data_subtype, ("label", "question", "default")
                )
            else:
                raise CFBSExitError(
                    "Unsupported subtype '%s' in input definition for module '%s'."
                    % (type(def_subtype).__name__, module_name)
                )
        return changes_made

    changes_made = False
    for i in range(len(input_def)):
        changes_made |= _update_variable(input_def[i], input_data[i])
    return changes_made


def update_module(old_module, new_module, module_updates, update):
    commit_differs = old_module["commit"] != new_module["commit"]
    old_version = old_module.get("version")
    local_changes_made = False
    for key in list(old_module.keys()):
        if key == "subdirectory" and old_module[key] == "" and key not in new_module:
            # Handle special case of old modules having "" subdirectory:
            # no longer allowed, but can be safely removed
            del old_module[key]
            local_changes_made = True
            continue
        if key not in new_module or old_module[key] == new_module[key]:
            continue
        if key == "steps":
            # same commit => user modifications, don't revert them
            if commit_differs:
                if prompt_user_yesno(
                    module_updates.config.non_interactive,
                    "Module %s has different build steps now\n" % old_module["name"]
                    + "old steps: %s\n" % old_module["steps"]
                    + "new steps: %s\n" % new_module["steps"]
                    + "Do you want to use the new build steps?",
                ):
                    old_module["steps"] = new_module["steps"]
                    local_changes_made = True
                else:
                    print(
                        "Please make sure the old build steps work"
                        + " with the new version of the module"
                    )
        elif key == "input":
            if commit_differs:
                old_module["input"] = new_module["input"]

                input_path = os.path.join(".", old_module["name"], "input.json")
                input_data = read_json(input_path)
                if input_data is None:
                    log.debug(
                        "Skipping input update for module '%s': " % old_module["name"]
                        + "No input found in '%s'" % input_path
                    )
                else:
                    try:
                        local_changes_made |= update_input_data(old_module, input_data)
                    except InputDataUpdateFailed as e:
                        log.warning(e)
                        if not prompt_user_yesno(
                            module_updates.config.non_interactive,
                            "Input for module '%s' has changed " % old_module["name"]
                            + "and may no longer be compatible. "
                            + "Do you want to re-enter input now?",
                            default="no",
                        ):
                            continue
                        input_data = copy.deepcopy(old_module["input"])
                        module_updates.config.input_command(
                            old_module["name"], input_data
                        )
                        local_changes_made = True

                if local_changes_made:
                    write_json(input_path, input_data)
                    module_updates.files.append(input_path)
        else:
            if key == "dependencies":
                extra = set(new_module["dependencies"]) - set(
                    old_module["dependencies"]
                )
                module_updates.new_deps.extend(extra)
                module_updates.new_deps_added_by.update(
                    {item: old_module["name"] for item in extra}
                )

            old_module[key] = new_module[key]
            local_changes_made = True

    for key in set(new_module.keys()) - set(old_module.keys()):
        old_module[key] = new_module[key]
        if key == "dependencies":
            extra = new_module["dependencies"]
            module_updates.new_deps.extend(extra)
            module_updates.new_deps_added_by.update(
                {item: old_module["name"] for item in extra}
            )

    if local_changes_made:
        if new_module.get("version"):
            module_updates.msg += (
                "\n - Updated module '%s' from version %s to version %s"
                % (
                    update.name,
                    old_version,
                    update.version if update.version else new_module["version"],
                )
            )
        else:
            module_updates.msg += "\n - Updated module '%s' from url" % (update.name)
    else:
        print("Module '%s' already up to date" % old_module["name"])

    module_updates.changes_made |= local_changes_made
