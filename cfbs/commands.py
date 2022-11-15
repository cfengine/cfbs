"""
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.
"""
import os
import re
import copy
import logging as log
import json
from collections import OrderedDict
from cfbs.args import get_args

from cfbs.utils import (
    cfbs_dir,
    cfbs_filename,
    is_cfbs_repo,
    item_index,
    read_json,
    user_error,
    strip_right,
    pad_right,
    get_json,
    write_json,
    rm,
    cp,
    sh,
    is_a_commit_hash,
)

from cfbs.args import get_args
from cfbs.pretty import pretty, pretty_check_file, pretty_file
from cfbs.build import init_out_folder, perform_build_steps
from cfbs.cfbs_config import CFBSConfig, CFBSReturnWithoutCommit
from cfbs.validate import CFBSIndexException, validate_index
from cfbs.internal_file_management import (
    fetch_archive,
    get_download_path,
    local_module_copy,
    SUPPORTED_ARCHIVES,
)
from cfbs.index import _VERSION_INDEX, Index
from cfbs.git import (
    is_git_repo,
    git_get_config,
    git_set_config,
    git_init,
    CFBSGitError,
    ls_remote,
)
from cfbs.git_magic import Result, commit_after_command, git_commit_maybe_prompt
from cfbs.prompts import YES_NO_CHOICES, prompt_user
from cfbs.module import Module


class InputDataUpdateFailed(Exception):
    def __init__(self, message):
        super().__init__(message)


_MODULES_URL = "https://archive.build.cfengine.com/modules"

PLURAL_S = lambda args, _: "s" if len(args[0]) > 1 else ""
FIRST_ARG_SLIST = lambda args, _: ", ".join("'%s'" % module for module in args[0])


def pretty_command(filenames: list, check: bool, keep_order: bool) -> int:
    if not filenames:
        user_error("Filenames missing for cfbs pretty command")

    cfbs_sorting_rules = None
    if not keep_order:
        top_level_keys = ("name", "description", "type", "index")
        module_keys = (
            "name",
            "description",
            "tags",
            "repo",
            "by",
            "version",
            "commit",
            "subdirectory",
            "dependencies",
            "steps",
        )
        cfbs_sorting_rules = {
            None: (
                lambda child_item: item_index(top_level_keys, child_item[0]),
                {
                    "index": (
                        lambda child_item: child_item[0],
                        {
                            ".*": (
                                lambda child_item: item_index(
                                    module_keys, child_item[0]
                                ),
                                None,
                            )
                        },
                    )
                },
            ),
        }

    num_files = 0
    for f in filenames:
        if not f or not f.endswith(".json"):
            user_error(
                "cfbs pretty command can only be used with .json files, not '%s'"
                % os.path.basename(f)
            )
        try:
            if check:
                if not pretty_check_file(f, cfbs_sorting_rules):
                    num_files += 1
                    print("Would reformat %s" % f)
            else:
                pretty_file(f, cfbs_sorting_rules)
        except FileNotFoundError:
            user_error("File '%s' not found" % f)
        except json.decoder.JSONDecodeError as ex:
            user_error("Error reading json file '{}': {}".format(f, ex))
    if check:
        print("Would reformat %d file(s)" % num_files)
        return 1 if num_files > 0 else 0
    return 0


def init_command(index=None, masterfiles=None, non_interactive=False) -> int:
    if is_cfbs_repo():
        user_error("Already initialized - look at %s" % cfbs_filename())

    name = prompt_user(
        non_interactive,
        "Please enter the name of this CFEngine Build project",
        default="Example project",
    )
    description = prompt_user(
        non_interactive,
        "Please enter the description of this CFEngine Build project",
        default="Example description",
    )

    config = {
        "name": name,
        "type": "policy-set",  # TODO: Prompt whether user wants to make a module
        "description": description,
        "build": [],
    }
    if index:
        config["index"] = index

    do_git = get_args().git
    is_git = is_git_repo()
    if do_git is None:
        if is_git:
            git_ans = prompt_user(
                non_interactive,
                "This is a git repository. Do you want cfbs to make commits to it?",
                choices=YES_NO_CHOICES,
                default="yes",
            )
        else:
            git_ans = prompt_user(
                non_interactive,
                "Do you want cfbs to initialize a git repository and make commits to it?",
                choices=YES_NO_CHOICES,
                default="yes",
            )
        do_git = git_ans.lower() in ("yes", "y")
    else:
        assert do_git in ("yes", "no")
        do_git = True if do_git == "yes" else False

    if do_git is True:
        user_name = get_args().git_user_name
        if not user_name:
            user_name = git_get_config("user.name")
            user_name = prompt_user(
                non_interactive,
                "Please enter user name to use for git commits",
                default=user_name or "cfbs",
            )

        user_email = get_args().git_user_email
        if not user_email:
            user_email = git_get_config("user.email")
            node_name = os.uname().nodename
            user_email = prompt_user(
                non_interactive,
                "Please enter user email to use for git commits",
                default=user_email or ("cfbs@%s" % node_name),
            )

        if not is_git:
            try:
                git_init(user_name, user_email, description)
            except CFBSGitError as e:
                print(str(e))
                return 1
        else:
            if not git_set_config("user.name", user_name) or not git_set_config(
                "user.email", user_email
            ):
                print("Failed to set Git user name and email")
                return 1

    config["git"] = do_git

    write_json(cfbs_filename(), config)
    assert is_cfbs_repo()

    if do_git:
        try:
            git_commit_maybe_prompt(
                "Initialized a new CFEngine Build project",
                non_interactive,
                [cfbs_filename()],
            )
        except CFBSGitError as e:
            print(str(e))
            os.unlink(cfbs_filename())
            return 1

    print(
        "Initialized an empty project called '{}' in '{}'".format(name, cfbs_filename())
    )

    """
    The CFBSConfig instance was initally created in main(). Back then
    cfbs.json did not exist, thus the instance is empty. Ensure it is reloaded
    now that the JSON exists.
    """
    CFBSConfig.reload()

    branch = None
    to_add = ""
    if masterfiles is None:
        if prompt_user(
            non_interactive,
            "Do you wish to build on top of the default policy set, masterfiles? (Recommended)",
            choices=YES_NO_CHOICES,
            default="yes",
        ) in ("yes", "y"):
            to_add = "masterfiles"
        else:
            to_add = prompt_user(
                non_interactive,
                "Specify policy set to use instead (empty to skip)",
                default="",
            )
    elif re.match(r"[0-9]+(\.[0-9]+){2}(\-[0-9]+)?", masterfiles):
        log.debug("--masterfiles=%s appears to be a version number" % masterfiles)
        to_add = "masterfiles@%s" % masterfiles
    elif masterfiles != "no":
        """This appears to be a branch. Thus we'll add masterfiles normally
        and try to do the necessary modifications needed afterwards. I.e.
        changing the 'repo' attribute to be 'url' and changing the commit to
        be the current HEAD of the upstream branch."""

        log.debug("--masterfiles=%s appears to be a branch" % masterfiles)
        branch = masterfiles
        to_add = "masterfiles"

    if to_add:
        ret = add_command([to_add])
        if ret != 0:
            return ret

    if branch is not None:
        config = CFBSConfig.get_instance()
        module = config.get_module_from_build("masterfiles")
        remote = module["repo"]
        commit = ls_remote(remote, branch)
        if commit is None:
            user_error("Failed to add masterfiles from branch %s" % branch)
        log.debug("Current commit for masterfiles branch %s is %s" % (branch, commit))
        module["url"] = remote
        del module["repo"]
        module["commit"] = commit
        config.save()

    return 0


def status_command() -> int:

    config = CFBSConfig.get_instance()
    print("Name:        %s" % config["name"])
    print("Description: %s" % config["description"])
    print("File:        %s" % cfbs_filename())

    modules = config["build"]
    if not modules:
        return 0
    print("\nModules:")
    max_length = config.longest_module_name()
    counter = 1
    for m in modules:
        if m["name"].startswith("./"):
            status = "Copied"
            commit = pad_right("local", 40)
        else:
            path = get_download_path(m)
            status = "Downloaded" if os.path.exists(path) else "Not downloaded"
            commit = m["commit"]
        name = pad_right(m["name"], max_length)
        print("%03d %s @ %s (%s)" % (counter, name, commit, status))
        counter += 1

    return 0


def search_command(terms: list) -> int:
    index = CFBSConfig.get_instance().index
    results = {}

    # in order to gather all aliases, we must iterate over everything first
    for name, data in index.items():
        if "alias" in data:
            realname = data["alias"]
            if realname not in results:
                results[realname] = {}
            if "aliases" in results[realname]:
                results[realname]["aliases"].append(name)
            else:
                results[realname]["aliases"] = [name]
            continue
        if name in results:
            results[name]["description"] = data["description"]
        else:
            results[name] = {"description": data["description"], "aliases": []}

    filtered = {}
    if terms:
        for name in (
            name
            for name, data in results.items()
            if any((t for t in terms if t in name))
            or any((t for t in terms if any((s for s in data["aliases"] if t in s))))
        ):
            filtered[name] = results[name]
    else:
        filtered = results

    results = filtered
    for k, v in results.items():
        print("{}".format(k), end="")
        if any(v["aliases"]):
            print(" ({})".format(", ".join(v["aliases"])), end="")
        print(" - {}".format(v["description"]))

    return 0 if any(results) else 1


@commit_after_command("Added module%s %s", [PLURAL_S, FIRST_ARG_SLIST])
def add_command(
    to_add: list,
    added_by="cfbs add",
    checksum=None,
) -> int:
    config = CFBSConfig.get_instance()
    r = config.add_command(to_add, added_by, checksum)
    config.save()
    return r


@commit_after_command("Removed module%s %s", [PLURAL_S, FIRST_ARG_SLIST])
def remove_command(to_remove: list):
    config = CFBSConfig.get_instance()
    modules = config["build"]

    def _get_module_by_name(name) -> dict:
        if not name.startswith("./") and name.endswith(".cf") and os.path.exists(name):
            name = "./" + name

        for module in modules:
            if module["name"] == name:
                return module
        return None

    def _get_modules_by_url(name) -> list:
        r = []
        for module in modules:
            if "url" in module and module["url"] == name:
                r.append(module)
        return r

    num_removed = 0
    msg = ""
    files = []
    for name in to_remove:
        if name.startswith(("https://", "ssh://", "git://")):
            matches = _get_modules_by_url(name)
            if not matches:
                user_error("Could not find module with URL '%s'" % name)
            for module in matches:
                answer = prompt_user(
                    config.non_interactive,
                    "Do you wish to remove '%s'?" % module["name"],
                    choices=YES_NO_CHOICES,
                    default="yes",
                )
                if answer.lower() in ("yes", "y"):
                    print("Removing module '%s'" % module["name"])
                    modules.remove(module)
                    msg += "\n - Removed module '%s'" % module["name"]
                    num_removed += 1
        else:
            module = _get_module_by_name(name)
            if module:
                print("Removing module '%s'" % name)
                modules.remove(module)
                msg += "\n - Removed module '%s'" % module["name"]
                num_removed += 1
            else:
                print("Module '%s' not found" % name)
        input_path = os.path.join(".", name, "input.json")
        if os.path.isfile(input_path) and prompt_user(
            config.non_interactive,
            "Module '%s' has input data '%s'. Do you want to remove it?"
            % (name, input_path),
            choices=YES_NO_CHOICES,
            default="no",
        ).lower() in ("yes", "y"):
            rm(input_path)
            files.append(input_path)
            msg += "\n - Removed input data for module '%s'" % name
            log.debug("Deleted module data '%s'" % input_path)

    num_lines = len(msg.strip().splitlines())
    changes_made = num_lines > 0
    if num_lines > 1:
        msg = "Removed %d modules\n" % num_removed + msg
    else:
        msg = msg[4:]  # Remove the '\n - ' part of the message

    config.save()
    if num_removed:
        try:
            _clean_unused_modules(config)
        except CFBSReturnWithoutCommit:
            pass
    return Result(0, changes_made, msg, files)


@commit_after_command("Cleaned unused modules")
def clean_command(config=None):
    return _clean_unused_modules(config)


def _clean_unused_modules(config=None):
    if not config:
        config = CFBSConfig.get_instance()
    modules = config["build"]

    def _someone_needs_me(this) -> bool:
        if "added_by" not in this or this["added_by"] == "cfbs add":
            return True
        for other in modules:
            if not "dependencies" in other:
                continue
            if this["name"] in other["dependencies"]:
                return _someone_needs_me(other)
        return False

    to_remove = list()
    for module in modules:
        if not _someone_needs_me(module):
            to_remove.append(module)

    if not to_remove:
        raise CFBSReturnWithoutCommit(0)

    print("The following modules were added as dependencies but are no longer needed:")
    for module in to_remove:
        name = module["name"] if "name" in module else ""
        description = module["description"] if "description" in module else ""
        added_by = module["added_by"] if "added_by" in module else ""
        print("%s - %s - added by: %s" % (name, description, added_by))

    answer = prompt_user(
        config.non_interactive,
        "Do you wish to remove these modules?",
        choices=YES_NO_CHOICES,
        default="yes",
    )
    if answer.lower() in ("yes", "y"):
        for module in to_remove:
            modules.remove(module)
        config.save()

    return 0


def update_input_data(module, input_data):
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
            if type(def_subtype) != type(data_subtype):
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
                user_error(
                    "Unsupported subtype '%s' in input definition for module '%s'."
                    % (type(def_subtype).__name__, module_name)
                )
        return changes_made

    changes_made = False
    for i in range(len(input_def)):
        changes_made |= _update_variable(input_def[i], input_data[i])
    return changes_made


@commit_after_command("Updated module%s", [PLURAL_S])
def update_command(to_update):
    config = CFBSConfig.get_instance()
    build = config["build"]

    # Update all modules in build if none specified
    to_update = (
        [Module(m) for m in to_update]
        if to_update
        else [Module(m["name"]) for m in build]
    )

    new_deps = []
    new_deps_added_by = dict()
    changes_made = False
    msg = ""
    files = []
    updated = []

    for update in to_update:
        module = config.get_module_from_build(update.name)

        custom_index = module is not None and "index" in module
        index = Index(module["index"]) if custom_index else config.index

        if not module:
            index.translate_alias(update)
            module = config.get_module_from_build(update.name)

        if not module:
            log.warning("Module '%s' not in build. Skipping its update." % update.name)
            continue

        custom_index = module is not None and "index" in module
        index = Index(module["index"]) if custom_index else config.index

        if not module:
            index.translate_alias(update)
            module = config.get_module_from_build(update.name)

        if not module:
            log.warning("Module '%s' not in build. Skipping its update." % update.name)
            continue

        if "version" not in module:
            log.warning(
                "Module '%s' not updatable. Skipping its update." % module["name"]
            )
            log.debug("Module '%s' has no version attribute." % module["name"])
            continue
        old_version = module["version"]

        index_info = index.get_module_object(update.name)
        if not index_info:
            log.warning(
                "Module '%s' not present in the index, cannot update it."
                % module["name"]
            )
            continue

        local_ver = [
            int(version_number)
            for version_number in re.split(r"[-\.]", module["version"])
        ]
        index_ver = [
            int(version_number)
            for version_number in re.split(r"[-\.]", index_info["version"])
        ]
        if local_ver == index_ver:
            print("Module '%s' already up to date" % module["name"])
            continue
        elif local_ver > index_ver:
            log.warning(
                "The requested version of module '%s' is older than current version (%s < %s)."
                " Skipping its update."
                % (module["name"], index_info["version"], module["version"])
            )
            continue

        commit_differs = module["commit"] != index_info["commit"]
        for key in module.keys():
            if key not in index_info or module[key] == index_info[key]:
                continue
            if key == "steps":
                # same commit => user modifications, don't revert them
                if commit_differs:
                    ans = prompt_user(
                        config.non_interactive,
                        "Module %s has different build steps now\n" % module["name"]
                        + "old steps: %s\n" % module["steps"]
                        + "new steps: %s\n" % index_info["steps"]
                        + "Do you want to use the new build steps?",
                        choices=YES_NO_CHOICES,
                        default="yes",
                    )
                    if ans.lower() in ["y", "yes"]:
                        module["steps"] = index_info["steps"]
                        changes_made = True
                    else:
                        print(
                            "Please make sure the old build steps work"
                            + " with the new version of the module"
                        )
            elif key == "input":
                if commit_differs:
                    module["input"] = index_info["input"]

                    input_path = os.path.join(".", module["name"], "input.json")
                    input_data = read_json(input_path)
                    if input_data == None:
                        log.debug(
                            "Skipping input update for module '%s': "
                            + "No input found in '%s'" % (module["name"], input_path)
                        )
                    else:
                        try:
                            changes_made |= update_input_data(module, input_data)
                        except InputDataUpdateFailed as e:
                            log.warning(e)
                            if prompt_user(
                                config.non_interactive,
                                "Input for module '%s' has changed " % module["name"]
                                + "and may no longer be compatible. "
                                + "Do you want to re-enter input now?",
                                YES_NO_CHOICES,
                                "no",
                            ).lower() in ("no", "n"):
                                continue
                            input_data = copy.deepcopy(module["input"])
                            config.input_command(module["name"], input_data)
                            changes_made = True

                    if changes_made:
                        write_json(input_path, input_data)
                        files.append(input_path)
            else:
                if key == "dependencies":
                    extra = set(index_info["dependencies"]) - set(
                        module["dependencies"]
                    )
                    new_deps.extend(extra)
                    new_deps_added_by.update({item: module["name"] for item in extra})

                module[key] = index_info[key]
                changes_made = True

        # add new items
        for key in set(index_info.keys()) - set(module.keys()):
            module[key] = index_info[key]
            if key == "dependencies":
                extra = index_info["dependencies"]
                new_deps.extend(extra)
                new_deps_added_by.update({item: module["name"] for item in extra})

        if not update.version:
            update.version = index_info["version"]
        updated.append(update)
        msg += "\n - Updated module '%s' from version %s to version %s" % (
            update.name,
            old_version,
            update.version,
        )

    if new_deps:
        objects = [index.get_module_object(d, new_deps_added_by[d]) for d in new_deps]
        config.add_with_dependencies(objects)
    config.save()

    if changes_made:
        msg = "Updated %d module%s\n" % (len(updated), "s" if updated else "") + msg
        print("%s\n" % msg)
    else:
        print("Modules are already up to date")

    return Result(0, changes_made, msg, files)


def validate_command():
    index = CFBSConfig.get_instance().index
    if not index:
        user_error("Index not found")

    data = index.data
    if "type" not in data:
        user_error("Index is missing a type field")

    if data["type"] != "index":
        user_error("Only validation of index files is currently implemented")

    try:
        validate_index(data)
    except CFBSIndexException as e:
        print(e)
        return 1
    return 0


def _download_dependencies(
    config, prefer_offline=False, redownload=False, ignore_versions=False
):
    # TODO: This function should be split in 2:
    #       1. Code for downloading things into ~/.cfengine
    #       2. Code for copying things into ./out
    print("\nModules:")
    counter = 1
    max_length = config.longest_module_name()
    downloads = os.path.join(cfbs_dir(), "downloads")
    for module in config["build"]:
        name = module["name"]
        if name.startswith("./"):
            local_module_copy(module, counter, max_length)
            counter += 1
            continue
        if "commit" not in module:
            user_error("module %s must have a commit property" % name)
        commit = module["commit"]
        if not is_a_commit_hash(commit):
            user_error("'%s' is not a commit reference" % commit)

        url = module.get("url") or module["repo"]
        url = strip_right(url, ".git")
        commit_dir = get_download_path(module)
        if redownload:
            rm(commit_dir, missing_ok=True)
        if "subdirectory" in module:
            module_dir = os.path.join(commit_dir, module["subdirectory"])
        else:
            module_dir = commit_dir
        if not os.path.exists(module_dir):
            if url.endswith(SUPPORTED_ARCHIVES):
                fetch_archive(url, commit)
            # a couple of cases where there will not be an archive available:
            # - using an alternate index (index property in module data)
            # - added by URL instead of name (no version property in module data)
            elif "index" in module or "url" in module or ignore_versions:
                sh("git clone %s %s" % (url, commit_dir))
                sh("(cd %s && git checkout %s)" % (commit_dir, commit))
            else:
                versions = get_json(_VERSION_INDEX)
                try:
                    checksum = versions[name][module["version"]]["archive_sha256"]
                except KeyError:
                    user_error("Cannot verify checksum of the '%s' module" % name)
                module_archive_url = os.path.join(
                    _MODULES_URL, name, commit + ".tar.gz"
                )
                fetch_archive(
                    module_archive_url, checksum, directory=commit_dir, with_index=False
                )
        target = "out/steps/%03d_%s_%s/" % (counter, module["name"], commit)
        module["_directory"] = target
        module["_counter"] = counter
        subdirectory = module.get("subdirectory", None)
        if not subdirectory:
            cp(commit_dir, target)
        else:
            cp(os.path.join(commit_dir, subdirectory), target)
        print(
            "%03d %s @ %s (Downloaded)" % (counter, pad_right(name, max_length), commit)
        )
        counter += 1


def download_command(force, ignore_versions=False):
    config = CFBSConfig.get_instance()
    _download_dependencies(config, redownload=force, ignore_versions=ignore_versions)


def build_command(ignore_versions=False) -> int:
    config = CFBSConfig.get_instance()
    init_out_folder()
    _download_dependencies(config, prefer_offline=True, ignore_versions=ignore_versions)
    perform_build_steps(config)


def install_command(args) -> int:
    if len(args) > 1:
        user_error(
            "Only one destination is allowed for command: cfbs install [destination]"
        )
    if not os.path.exists("out/masterfiles"):
        r = build_command()
        if r != 0:
            return r

    if os.getuid() == 0:
        destination = "/var/cfengine/masterfiles"
    if len(args) > 0:
        destination = args[0]
    elif os.getuid() == 0:
        destination = "/var/cfengine/masterfiles"
    else:
        destination = os.path.join(os.environ["HOME"], ".cfagent/inputs")
    if not destination.startswith("/") and not destination.startswith("./"):
        destination = "./" + destination
    rm(destination, missing_ok=True)
    cp("out/masterfiles", destination)
    print("Installed to %s" % destination)
    return 0


def help_command():
    pass  # no-op here, all *_command functions are presented in help contents


def _print_module_info(data):
    ordered_keys = [
        "module",
        "version",
        "status",
        "by",
        "tags",
        "repo",
        "index",
        "commit",
        "subdirectory",
        "dependencies",
        "added_by",
        "description",
    ]
    for key in ordered_keys:
        if key in data:
            if key in ["tags", "dependencies"]:
                value = ", ".join(data[key])
            else:
                value = data[key]
            print("{}: {}".format(key.title().replace("_", " "), value))


def info_command(modules):
    if not modules:
        user_error("info/show command requires one or more module names as arguments")
    config = CFBSConfig.get_instance()
    index = config.index

    build = config.get("build", {})

    alias = None

    for module in modules:
        print()  # whitespace for readability
        in_build = any(m for m in build if m["name"] == module)
        if not index.exists(module) and not in_build:
            print("Module '{}' does not exist".format(module))
            continue
        if in_build:
            # prefer information from the local source
            data = next(m for m in build if m["name"] == module)
            data["status"] = "Added"
        elif module in index:
            data = index[module]
            if "alias" in data:
                alias = module
                module = data["alias"]
                data = index[module]
            data["status"] = "Added" if in_build else "Not added"
        else:
            if not module.startswith("./"):
                module = "./" + module
            data = next((m for m in build if m["name"] == module), None)
            if data is None:
                print("Path {} exists but is not yet added as a module.".format(module))
                continue
            data["status"] = "Added"
        data["module"] = (module + "({})".format(alias)) if alias else module
        _print_module_info(data)
    print()  # extra line for ease of reading
    return 0


# show_command here to auto-populate into help in main.py
def show_command(module):
    return info_command(module)


@commit_after_command("Added input for module%s", [PLURAL_S])
def input_command(args, input_from="cfbs input"):
    config = CFBSConfig.get_instance()
    do_commit = False
    files_to_commit = []
    for module_name in args:
        module = config.get_module_from_build(module_name)
        if not module:
            print("Skipping module '%s', module not found" % module_name)
            continue
        if "input" not in module:
            print("Skipping module '%s', no input needed" % module_name)
            continue

        input_path = os.path.join(".", module_name, "input.json")
        if os.path.isfile(input_path):
            if prompt_user(
                config.non_interactive,
                "Input already exists for this module, do you want to overwrite it?",
                YES_NO_CHOICES,
                "no",
            ).lower() in ("no", "n"):
                continue

        input_data = copy.deepcopy(module["input"])
        config.input_command(module_name, input_data)

        write_json(input_path, input_data)
        do_commit = True
        files_to_commit.append(input_path)
    config.save()
    return Result(0, do_commit, None, files_to_commit)


def set_input_command(name, infile):
    config = CFBSConfig.get_instance()
    module = config.get_module_from_build(name)
    if module is None:
        log.error("Module '%s' not found" % name)
        return 1

    spec = module.get("input")
    if spec is None:
        log.error("Module '%s' does not accept input" % name)
        return 1
    log.debug("Input spec for module '%s': %s" % (name, pretty(spec)))

    try:
        data = json.load(infile, object_pairs_hook=OrderedDict)
    except json.decoder.JSONDecodeError as e:
        log.error("Error reading json from stdin: %s" % e)
        return 1
    log.debug("Input data for module '%s': %s" % (name, pretty(data)))

    def _compare_dict(a, b, ignore=set()):
        assert isinstance(a, dict) and isinstance(b, dict)
        if set(a.keys()) != set(b.keys()) - ignore:
            return False
        # Avoid code duplication by converting the values of the two dicts
        # into two lists in the same order and compare the lists instead
        keys = a.keys()
        return _compare_list([a[key] for key in keys], [b[key] for key in keys])

    def _compare_list(a, b):
        assert isinstance(a, list) and isinstance(b, list)
        if len(a) != len(b):
            return False
        for x, y in zip(a, b):
            if type(x) != type(y):
                return False
            if isinstance(x, dict) and not _compare_dict(x, y):
                return False
            if isinstance(x, list) and not _compare_list(x, y):
                return False
            if x != y:
                return False
        return True

    for a, b in zip(spec, data):
        if (
            not isinstance(a, dict)
            or not isinstance(b, dict)
            or not _compare_dict(a, b, ignore=set({"response"}))
        ):
            log.error(
                "Input data for module '%s' does not conform with input definition"
                % name
            )
            return 1

    path = os.path.join(name, "input.json")
    log.debug("Writing json to file '%s'" % path)
    write_json(path, data)

    return 0


def get_input_command(name, outfile):
    config = CFBSConfig.get_instance()
    module = config.get_module_from_build(name)
    if module is None:
        module = config.index.get_module_object(name)
    if module is None:
        log.error("Module '%s' not found" % name)
        return 1

    if "input" not in module:
        log.error("Module '%s' does not accept input" % name)
        return 1

    path = os.path.join(name, "input.json")
    data = read_json(path)
    if data is None:
        log.debug("Loaded input from module '%s' definition" % name)
        data = module["input"]
    else:
        log.debug("Loaded input from '%s'" % path)

    data = pretty(data) + "\n"
    try:
        outfile.write(data)
    except OSError as e:
        log.error("Failed to write json: %s" % e)
        return 1
    return 0
