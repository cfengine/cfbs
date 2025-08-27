"""
commands.py - Entry points for each cfbs command.

Each cfbs command has a corresponding function named <command>_command.
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.

At a high level, each command should do something like this:
1. Open the cfbs.json file using CFBSConfig.get_instance().
2. Validate arguments and cfbs.json data before we start editing.
3. Perform the necessary operations using the CFBSConfig methods.
4. Validate cfbs.json again after editing.
5. Save changes and make commits.
6. Return an appropriate exit code.
   0 for success, 1 for failure.
   Raising exceptions is also an option and often preferred, see main.py for exception handling code.

Note that most of the business logic (step 2) should be implemented in CFBSConfig.

The command function (in this file) should have parameters which
map closely to the command line arguments.

For example, cfbs status does not take any arguments, so the signature should be:

def status_command():

On the other hand, cfbs search takes a list of search terms:

cfbs search <terms>

So, the appropriate signature is:

def search_command(terms: List[str]):

The return type (after any decoration) of the cfbs command functions is `CFBSCommandExitCode`.
This type is indistinguishably defined to be `int`.
The return type before decoration of functions decorated by `commit_after_command` is `CFBSCommandGitResult`.
The `commit_after_command` decorator then changes the return type to `CFBSCommandExitCode`.

Todos:
1. Some of these functions are getting too long, business logic should be moved into
   CFBSConfig in cfbs_config.py. Commands should generally not call other commands,
   instead they should call the correct CFBSConfig method(s).
2. Decorators, like the git ones, should not change the parameters nor types of
   the functions they decorate. This makes them much harder to read. It applies to both types and values of parameters and returns.
"""

import os
import re
import copy
import logging as log
import json
import functools
from typing import Callable, List, Optional, Union
from collections import OrderedDict
from cfbs.analyze import analyze_policyset
from cfbs.args import get_args
from typing import Iterable

from cfbs.cfbs_json import CFBSJson
from cfbs.cfbs_types import CFBSCommandExitCode, CFBSCommandGitResult
from cfbs.masterfiles.analyze import most_relevant_version
from cfbs.updates import ModuleUpdates, update_module
from cfbs.utils import (
    CFBSNetworkError,
    CFBSUserError,
    CFBSValidationError,
    cfbs_filename,
    is_cfbs_repo,
    read_json,
    CFBSExitError,
    strip_right,
    pad_right,
    CFBSProgrammerError,
    get_json,
    write_json,
    rm,
    cp,
    sh,
    is_a_commit_hash,
)

from cfbs.pretty import (
    pretty,
    pretty_check_file,
    pretty_file,
    CFBS_DEFAULT_SORTING_RULES,
)
from cfbs.build import (
    init_out_folder,
    perform_build,
)
from cfbs.cfbs_config import CFBSConfig, CFBSReturnWithoutCommit
from cfbs.validate import (
    validate_config,
    validate_config_raise_exceptions,
    validate_module_name_content,
    validate_single_module,
)
from cfbs.internal_file_management import (
    clone_url_repo,
    SUPPORTED_URI_SCHEMES,
    fetch_archive,
    get_download_path,
    local_module_copy,
    SUPPORTED_ARCHIVES,
)
from cfbs.index import _VERSION_INDEX, Index
from cfbs.git import (
    git_configure_and_initialize,
    is_git_repo,
    CFBSGitError,
    ls_remote,
)

from cfbs.git_magic import commit_after_command, git_commit_maybe_prompt
from cfbs.prompts import prompt_user, prompt_user_yesno
from cfbs.module import Module, is_module_added_manually
from cfbs.masterfiles.generate_release_information import generate_release_information

_MODULES_URL = "https://archive.build.cfengine.com/modules"

PLURAL_S = lambda args, _: "s" if len(args[0]) > 1 else ""
FIRST_ARG = lambda args, _: "'%s'" % args[0]
FIRST_ARG_SLIST = lambda args, _: ", ".join("'%s'" % module for module in args[0])

_commands = OrderedDict()


def cfbs_command(name: str):
    """
    Decorator to specify that a function is a command (verb in the CLI).
    Adds the name + function pair to the global dict of commands.
    Does not modify/wrap the function it decorates.
    Ensures cfbs command functions return a `CFBSCommandExitCode`.
    """

    def inner(function: Callable[..., CFBSCommandExitCode]):
        _commands[name] = function
        return function  # Unmodified, we've just added it to the dict

    return inner


def get_command_names():
    names = _commands.keys()
    return names


@cfbs_command("pretty")
def pretty_command(filenames: List[str], check: bool, keep_order: bool):
    if not filenames:
        raise CFBSExitError("Filenames missing for cfbs pretty command")

    sorting_rules = CFBS_DEFAULT_SORTING_RULES if keep_order else None
    num_files = 0
    for f in filenames:
        if not f or not f.endswith(".json"):
            raise CFBSExitError(
                "cfbs pretty command can only be used with .json files, not '%s'"
                % os.path.basename(f)
            )
        try:
            if check:
                if not pretty_check_file(f, sorting_rules):
                    num_files += 1
                    print("Would reformat %s" % f)
            else:
                pretty_file(f, sorting_rules)
        except FileNotFoundError:
            raise CFBSExitError("File '%s' not found" % f)
        except json.decoder.JSONDecodeError as ex:
            raise CFBSExitError("Error reading json file '{}': {}".format(f, ex))
    if check:
        print("Would reformat %d file(s)" % num_files)
        return 1 if num_files > 0 else 0
    return 0


@cfbs_command("init")
def init_command(
    index=None,
    masterfiles=None,
    non_interactive=False,
    use_git: Union[bool, None] = None,
):
    if is_cfbs_repo():
        raise CFBSUserError("Already initialized - look at %s" % cfbs_filename())

    project_name = prompt_user(
        non_interactive,
        "Please enter the name of this CFEngine Build project",
        default="Example project",
    )
    description = prompt_user(
        non_interactive,
        "Please enter the description of this CFEngine Build project",
        default="Example description",
    )

    config = OrderedDict(
        {
            "name": project_name,
            "type": "policy-set",  # TODO: Prompt whether user wants to make a module
            "description": description,
            "build": [],
        }
    )
    if index:
        config["index"] = index

    if use_git is None:
        if is_git_repo():
            use_git = prompt_user_yesno(
                non_interactive,
                "This is a git repository. Do you want cfbs to make commits to it?",
            )
        else:
            use_git = prompt_user_yesno(
                non_interactive,
                "Do you want cfbs to initialize a git repository and make commits to it?",
            )

    if use_git is True:
        user_name = get_args().git_user_name
        user_email = get_args().git_user_email
        git_configure_and_initialize(
            user_name, user_email, non_interactive, description
        )

    config["git"] = use_git

    data = pretty(config, CFBS_DEFAULT_SORTING_RULES) + "\n"
    with open(cfbs_filename(), "w") as f:
        f.write(data)
    assert is_cfbs_repo()

    if use_git:
        try:
            git_commit_maybe_prompt(
                "Initialized a new CFEngine Build project",
                non_interactive,
                [cfbs_filename()],
            )
        except CFBSGitError:
            os.unlink(cfbs_filename())
            raise

    print(
        "Initialized an empty project called '{}' in '{}'".format(
            project_name, cfbs_filename()
        )
    )

    """
    The CFBSConfig instance was initally created in main(). Back then
    cfbs.json did not exist, thus the instance is empty. Ensure it is reloaded
    now that the JSON exists.
    """
    CFBSConfig.reload()

    branch = None
    to_add = []
    if masterfiles is None:
        if prompt_user_yesno(
            non_interactive,
            "Do you wish to build on top of the default policy set, masterfiles? (Recommended)",
        ):
            to_add = ["masterfiles"]
        else:
            answer = prompt_user(
                non_interactive,
                "Specify policy set to use instead (empty to skip)",
                default="",
            )
            if answer:
                to_add = [answer]
    elif re.match(r"[0-9]+(\.[0-9]+){2}(\-[0-9]+)?", masterfiles):
        log.debug("--masterfiles=%s appears to be a version number" % masterfiles)
        to_add = ["masterfiles@%s" % masterfiles]
    elif masterfiles != "no":
        """This appears to be a branch. Thus we'll add masterfiles normally
        and try to do the necessary modifications needed afterwards. I.e.
        changing the 'repo' attribute to be 'url' and changing the commit to
        be the current HEAD of the upstream branch."""

        log.debug("--masterfiles=%s appears to be a branch" % masterfiles)
        branch = masterfiles
        to_add = ["masterfiles"]

    if branch is not None:
        remote = "https://github.com/cfengine/masterfiles"
        commit = ls_remote(remote, branch)
        if commit is None:
            raise CFBSExitError(
                "Failed to find branch or tag %s at remote %s" % (branch, remote)
            )
        log.debug("Current commit for masterfiles branch %s is %s" % (branch, commit))
        to_add = ["%s@%s" % (remote, commit), "masterfiles"]
    if to_add:
        result = add_command(to_add, added_by="cfbs init")
        if result != 0:
            return result
        # TODO: Do we need to make commits here?

    return 0


@cfbs_command("status")
def status_command():
    config = CFBSConfig.get_instance()
    validate_config_raise_exceptions(config, empty_build_list_ok=True)
    print("Name:        %s" % config["name"])
    print("Description: %s" % config["description"])
    print("File:        %s" % cfbs_filename())
    if "index" in config:
        assert config.raw_data is not None
        index = config.raw_data["index"]

        if type(index) is str:
            print("Index:       %s" % index)
        else:
            print("Index:       %s" % "inline index in cfbs.json")

    modules = config.get("build")
    if not modules:
        return 0
    print("\nModules:")
    max_name_length = config.longest_module_key_length("name")
    max_version_length = config.longest_module_key_length("version")
    counter = 1
    for m in modules:
        if m["name"].startswith("./"):
            status = "Copied"
            version = "local"
            commit = pad_right("", 40)
        else:
            path = get_download_path(m)
            status = "Downloaded" if os.path.exists(path) else "Not downloaded"
            version = m.get("version", "")
            commit = m["commit"]
        name = pad_right(m["name"], max_name_length)
        version = pad_right(version, max_version_length)
        version_with_commit = version + " "
        if m["name"].startswith("./"):
            version_with_commit += " "
        else:
            version_with_commit += "/"
        version_with_commit += " " + commit
        print("%03d %s @ %s (%s)" % (counter, name, version_with_commit, status))
        counter += 1

    return 0


@cfbs_command("search")
def search_command(terms: List[str]):
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


@cfbs_command("add")
@commit_after_command("Added module%s %s", [PLURAL_S, FIRST_ARG_SLIST])
def add_command(
    to_add: List[str],
    added_by="cfbs add",
    checksum=None,
    explicit_build_steps: Optional[List[str]] = None,
):
    config = CFBSConfig.get_instance()
    validate_config_raise_exceptions(config, empty_build_list_ok=True)
    r = config.add_command(to_add, added_by, checksum, explicit_build_steps)
    config.save()
    return r


@cfbs_command("remove")
@commit_after_command("Removed module%s %s", [PLURAL_S, FIRST_ARG_SLIST])
def remove_command(to_remove: List[str]):
    config = CFBSConfig.get_instance()
    validate_config_raise_exceptions(config, empty_build_list_ok=True)
    if "build" not in config:
        raise CFBSExitError(
            'Cannot remove any modules because the "build" key is missing from cfbs.json'
        )
    modules = config["build"]

    def _get_dependents(dependency) -> list:
        if len(modules) < 2:
            return []

        def reduce_dependencies(a, b):
            result_b = [b["name"]] if dependency in b.get("dependencies", []) else []
            if type(a) is list:
                return a + result_b
            else:
                return (
                    [a["name"]] if dependency in a.get("dependencies", []) else []
                ) + result_b

        return functools.reduce(reduce_dependencies, modules)

    def _get_module_by_name(name) -> Union[dict, None]:
        if not name.startswith("./") and name.endswith(".cf") and os.path.exists(name):
            name = "./" + name

        for module in modules:
            if module["name"] == name:
                return module
        return None

    def _remove_module_user_prompt(module):
        dependents = _get_dependents(module["name"])
        return prompt_user_yesno(
            config.non_interactive,
            "Do you wish to remove '%s'?" % module["name"]
            + (
                " (The module is a dependency of the following module%s: %s)"
                % ("s" if len(dependents) > 1 else "", ", ".join(dependents))
                if dependents
                else ""
            ),
        )

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
        if name.startswith(SUPPORTED_URI_SCHEMES):
            matches = _get_modules_by_url(name)
            if not matches:
                raise CFBSExitError("Could not find module with URL '%s'" % name)
            for module in matches:
                if _remove_module_user_prompt(module):
                    print("Removing module '%s'" % module["name"])
                    modules.remove(module)
                    msg += "\n - Removed module '%s'" % module["name"]
                    num_removed += 1
        else:
            module = _get_module_by_name(name)
            if module:
                if _remove_module_user_prompt(module):
                    print("Removing module '%s'" % name)
                    modules.remove(module)
                    msg += "\n - Removed module '%s'" % module["name"]
                    num_removed += 1
            else:
                print("Module '%s' not found" % name)
        input_path = os.path.join(".", name, "input.json")
        if os.path.isfile(input_path) and prompt_user_yesno(
            config.non_interactive,
            "Module '%s' has input data '%s'. Do you want to remove it?"
            % (name, input_path),
            default="no",
        ):
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
    return CFBSCommandGitResult(0, changes_made, msg, files)


@cfbs_command("clean")
@commit_after_command("Cleaned unused modules")
def clean_command(config=None):
    r = _clean_unused_modules(config)
    return CFBSCommandGitResult(r)


def _clean_unused_modules(config=None):
    if not config:
        config = CFBSConfig.get_instance()
    config.warn_about_unknown_keys()
    if "build" not in config:
        log.warning('No "build" key with modules - nothing to clean')
        return 0
    modules = config["build"]
    if len(modules) == 0:
        return 0

    def _someone_needs_me(this) -> bool:
        if ("added_by" not in this) or is_module_added_manually(this["added_by"]):
            return True
        for other in modules:
            if "dependencies" not in other:
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

    if prompt_user_yesno(
        config.non_interactive,
        "Do you wish to remove these modules?",
    ):
        for module in to_remove:
            modules.remove(module)
        config.save()

    return 0


@cfbs_command("update")
@commit_after_command("Updated module%s", [PLURAL_S])
def update_command(to_update):
    config = CFBSConfig.get_instance()
    r = validate_config(config, empty_build_list_ok=True)
    valid_before = r == 0
    if not valid_before:
        log.warning(
            "Your cfbs.json fails validation before update "
            + "(see messages above) - "
            + "We will attempt update anyway, hoping newer "
            + "versions of modules might fix the issues"
        )
    build = config["build"]

    # Update all modules in build if none specified
    to_update = (
        [Module(m) for m in to_update]
        if to_update
        else [Module(m["name"]) for m in build]
    )

    updated = []
    module_updates = ModuleUpdates(config)
    index = None

    old_modules = []
    new_modules = []
    update_objects = []
    for update in to_update:
        old_module = config.get_module_from_build(update.name)
        assert (
            old_module is not None
        ), 'We\'ve already checked that modules are in config["build"]'

        custom_index = old_module is not None and "index" in old_module
        index = Index(old_module["index"]) if custom_index else config.index

        if not old_module:
            index.translate_alias(update)
            old_module = config.get_module_from_build(update.name)

        if not old_module:
            log.warning(
                "old_Module '%s' not in build. Skipping its update." % update.name
            )
            continue

        custom_index = old_module is not None and "index" in old_module
        index = Index(old_module["index"]) if custom_index else config.index

        if not old_module:
            index.translate_alias(update)
            old_module = config.get_module_from_build(update.name)

        if not old_module:
            log.warning("Module '%s' not in build. Skipping its update." % update.name)
            continue
        if "url" in old_module:
            path, commit = clone_url_repo(old_module["url"])
            remote_config = CFBSJson(
                path=path, url=old_module["url"], url_commit=commit
            )

            module_name = old_module["name"]
            provides = remote_config.get_provides()

            if not module_name or module_name not in provides:
                continue

            new_module = provides[module_name]
        else:

            if "version" not in old_module:
                log.warning(
                    "Module '%s' not updatable. Skipping its update."
                    % old_module["name"]
                )
                log.debug("Module '%s' has no version attribute." % old_module["name"])
                continue

            index_info = index.get_module_object(update.name)
            if not index_info:
                log.warning(
                    "Module '%s' not present in the index, cannot update it."
                    % old_module["name"]
                )
                continue

            local_ver = [
                int(version_number)
                for version_number in re.split(r"[-\.]", old_module["version"])
            ]
            index_ver = [
                int(version_number)
                for version_number in re.split(r"[-\.]", index_info["version"])
            ]
            if local_ver == index_ver:
                print("Module '%s' already up to date" % old_module["name"])
                continue
            elif local_ver > index_ver:
                log.warning(
                    "The requested version of module '%s' is older than current version (%s < %s)."
                    " Skipping its update."
                    % (old_module["name"], index_info["version"], old_module["version"])
                )
                continue

            new_module = index_info
        update_objects.append(update)
        old_modules.append(old_module)
        new_modules.append(new_module)

    assert len(old_modules) == len(update_objects)
    assert len(old_modules) == len(new_modules)

    # We don't validate old modules here because we want to allow
    # cfbs update to fix invalid modules with a newer valid version.

    # Validate new modules, we don't want to add them unless they are valid:
    for update, module in zip(update_objects, new_modules):
        validate_single_module(
            context="build",
            name=update.name,
            module=module,
            config=None,
            local_check=True,
        )

    for old_module, new_module, update in zip(old_modules, new_modules, update_objects):
        update_module(old_module, new_module, module_updates, update)
        updated.append(update)

    if module_updates.new_deps:
        assert index is not None
        objects = [
            index.get_module_object(d, module_updates.new_deps_added_by[d])
            for d in module_updates.new_deps
        ]
        config.add_with_dependencies(objects)
    r = validate_config(config, empty_build_list_ok=False)
    valid_after = r == 0
    if not valid_after:
        if valid_before:
            raise CFBSValidationError(
                "The cfbs.json was valid before update, "
                + "but is invalid after adding new versions "
                + "of modules - aborting update "
                + "(see validation error messages above)"
            )
        raise CFBSValidationError(
            "The cfbs.json was invalid before update, "
            + "but updating modules did not fix it - aborting update"
            + "(see validation error messages above)"
        )
    config.save()

    if module_updates.changes_made:
        if len(updated) > 1:
            module_updates.msg = (
                "Updated %d modules\n" % len(updated) + module_updates.msg
            )
        else:
            # Remove the '\n - ' part of the message
            module_updates.msg = module_updates.msg[len("\n - ") :]
        print("%s\n" % module_updates.msg)
    else:
        print("Modules are already up to date")

    return CFBSCommandGitResult(
        0, module_updates.changes_made, module_updates.msg, module_updates.files
    )


@cfbs_command("validate")
def validate_command(paths=None, index_arg=None):
    if paths:
        ret_value = 0

        for path in paths:
            # Exit out early if we find anything wrong like missing files:
            if not os.path.exists(path):
                raise CFBSUserError("Specified path '{}' does not exist".format(path))
            if path.endswith(".json") and not os.path.isfile(path):
                raise CFBSUserError(
                    "'{}' is not a file - Please specify a path to a cfbs project file, ending in .json, or a folder containing a cfbs.json".format(
                        path
                    )
                )
            if not path.endswith(".json") and not os.path.isfile(
                os.path.join(path, "cfbs.json")
            ):
                raise CFBSUserError(
                    "No CFBS project file found at '{}'".format(
                        os.path.join(path, "cfbs.json")
                    )
                )

            # Convert folder to folder/cfbs.json if appropriate:
            if not path.endswith(".json"):
                assert os.path.isdir(path)
                path = os.path.join(path, "cfbs.json")
            assert os.path.isfile(path)

            # Actually open the file and perform validation:
            config = CFBSJson(path=path, index_argument=index_arg)

            r = validate_config(config)
            if r != 0:
                log.warning("Validation of project at path %s failed" % path)
                ret_value = 1
            else:
                print("Successfully validated the project at path", path)

        return ret_value

    if not is_cfbs_repo():
        # TODO change CFBSExitError to CFBSUserError here
        raise CFBSExitError(
            "Cannot validate: this is not a CFBS project. "
            + "Use `cfbs init` to start a new project in this directory, or provide a path to a CFBS project to validate."
        )

    config = CFBSConfig.get_instance()
    return validate_config(config)


def _download_dependencies(
    config, prefer_offline=False, redownload=False, ignore_versions=False
):
    # TODO: This function should be split in 2:
    #       1. Code for downloading things into ~/.cfengine
    #       2. Code for copying things into ./out
    print("\nModules:")
    counter = 1
    max_length = config.longest_module_key_length("name")
    for module in config.get("build", []):
        name = module["name"]
        if name.startswith("./"):
            local_module_copy(module, counter, max_length)
            counter += 1
            continue
        if "commit" not in module:
            raise CFBSExitError("module %s must have a commit property" % name)
        commit = module["commit"]
        if not is_a_commit_hash(commit):
            raise CFBSExitError("'%s' is not a commit reference" % commit)

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
                if os.path.exists(commit_dir) and "subdirectory" in module:
                    raise CFBSExitError(
                        "Subdirectory '%s' for module '%s' was not found in fetched archive '%s': "
                        % (module["subdirectory"], name, url)
                        + "Please check cfbs.json for possible typos."
                    )
                fetch_archive(url, commit)
            # a couple of cases where there will not be an archive available:
            # - using an alternate index (index property in module data)
            # - added by URL instead of name (no version property in module data)
            elif "index" in module or "url" in module or ignore_versions:
                if os.path.exists(commit_dir) and "subdirectory" in module:
                    raise CFBSExitError(
                        "Subdirectory '%s' for module '%s' was not found in cloned repository '%s': "
                        % (module["subdirectory"], name, url)
                        + "Please check cfbs.json for possible typos."
                    )
                sh("git clone %s %s" % (url, commit_dir))
                sh("(cd %s && git checkout %s)" % (commit_dir, commit))
            else:
                try:
                    versions = get_json(_VERSION_INDEX)
                except CFBSNetworkError:
                    raise CFBSExitError(
                        "Downloading CFEngine Build Module Index failed - check your Wi-Fi / network settings."
                    )
                try:
                    checksum = versions[name][module["version"]]["archive_sha256"]
                except KeyError:
                    raise CFBSExitError(
                        "Cannot verify checksum of the '%s' module" % name
                    )
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


@cfbs_command("download")
def download_command(force, ignore_versions=False):
    config = CFBSConfig.get_instance()
    r = validate_config(config)
    if r != 0:
        log.warning(
            "At least one error encountered while validating your cfbs.json file."
            + "\nPlease see the error messages above and apply fixes accordingly."
            + "\nIf not fixed, these errors will cause your project to not build in future cfbs versions."
        )
    _download_dependencies(config, redownload=force, ignore_versions=ignore_versions)
    return 0


@cfbs_command("build")
def build_command(ignore_versions=False):
    config = CFBSConfig.get_instance()
    r = validate_config(config)
    if r != 0:
        log.warning(
            "At least one error encountered while validating your cfbs.json file."
            + "\nPlease see the error messages above and apply fixes accordingly."
            + "\nIf not fixed, these errors will cause your project to not build in future cfbs versions."
        )
        # We want the cfbs build command to be as backwards compatible as possible,
        # so we try building anyway and don't return error(s)
    init_out_folder()
    _download_dependencies(config, prefer_offline=True, ignore_versions=ignore_versions)
    r = perform_build(config)
    return r


@cfbs_command("install")
def install_command(args):
    if len(args) > 1:
        raise CFBSExitError(
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


@cfbs_command("help")
def help_command():
    raise CFBSProgrammerError("help_command should not be called, as we use argparse")


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


@cfbs_command("show")
@cfbs_command("info")
def info_command(modules):
    if not modules:
        raise CFBSExitError(
            "info/show command requires one or more module names as arguments"
        )
    config = CFBSConfig.get_instance()
    config.warn_about_unknown_keys()
    index = config.index

    build = config.get("build", [])
    assert isinstance(build, list)

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


@cfbs_command("analyze")
@cfbs_command("analyse")
def analyze_command(
    policyset_paths,
    json_filename=None,
    reference_version=None,
    masterfiles_dir=None,
    user_ignored_path_components=None,
    offline=False,
    verbose=False,
):
    if len(policyset_paths) == 0:
        # no policyset path is a shorthand for using the current directory as the policyset path
        log.info(
            "No path was provided. Using the current directory as the policy set path."
        )
        path = "."
    else:
        # currently, only support analyzing only one path
        path = policyset_paths[0]

        if len(policyset_paths) > 1:
            log.warning(
                "More than one path to analyze provided. Analyzing the first one and ignoring the others."
            )

    if not os.path.isdir(path):
        raise CFBSExitError("the provided policy set path is not a directory")

    if masterfiles_dir is None:
        masterfiles_dir = "masterfiles"
    # override masterfiles directory name (e.g. "inputs")
    # strip trailing path separators
    masterfiles_dir = masterfiles_dir.rstrip(os.sep)
    # we assume the modules directory is always called "modules"
    # thus `masterfiles_dir` can't be set to "modules"
    if masterfiles_dir == "modules":
        log.warning(
            'The masterfiles directory cannot be named "modules". Using the name "masterfiles" instead.'
        )
        masterfiles_dir = "masterfiles"

    # the policyset path can either contain only masterfiles (masterfiles-path), or contain folders containing modules and masterfiles (parent-path)
    # try to automatically determine which one it is (by checking whether `path` contains `masterfiles_dir`)
    is_parentpath = os.path.isdir(os.path.join(path, masterfiles_dir))

    print("Policy set path:", path, "\n")

    analyzed_files, versions_data = analyze_policyset(
        path,
        is_parentpath,
        reference_version,
        masterfiles_dir,
        user_ignored_path_components,
        offline,
    )

    versions_data.display(verbose)
    analyzed_files.display()

    if json_filename is not None:
        json_dict = OrderedDict()

        json_dict["policy_set_path"] = path
        json_dict["versions_data"] = versions_data.to_json_dict()
        json_dict["analyzed_files"] = analyzed_files.to_json_dict()

        write_json(json_filename + ".json", json_dict)

    return 0


@cfbs_command("convert")
def convert_command(non_interactive=False, offline=False):
    def cfbs_convert_cleanup():
        os.unlink(cfbs_filename())
        rm(".git", missing_ok=True)

    def cfbs_convert_git_commit(
        commit_message: str, add_scope: Union[str, Iterable[str]] = "all"
    ):
        try:
            git_commit_maybe_prompt(commit_message, non_interactive, scope=add_scope)
        except CFBSGitError:
            cfbs_convert_cleanup()
            raise

    dir_content = [f.name for f in os.scandir(".")]

    if not (len(dir_content) == 1 and dir_content[0].startswith("masterfiles-")):
        raise CFBSUserError(
            "cfbs convert must be run in a directory containing only one item, a subdirectory named masterfiles-<some-name>"
        )

    dir_name = dir_content[0]
    path_string = "./" + dir_name + "/"

    # validate the local module
    validate_module_name_content(path_string)

    promises_cf_path = os.path.join(dir_name, "promises.cf")
    if not os.path.isfile(promises_cf_path):
        raise CFBSUserError(
            "The file '"
            + promises_cf_path
            + "' does not exist - make sure '"
            + path_string
            + "' is a policy set based on masterfiles."
        )

    print(
        "Found policy set in '%s' with 'promises.cf' in the expected location."
        % path_string
    )

    print("Analyzing '" + path_string + "'...")
    analyzed_files, _ = analyze_policyset(
        path=dir_name,
        is_parentpath=False,
        reference_version=None,
        masterfiles_dir=dir_name,
        ignored_path_components=None,
        offline=offline,
    )

    current_index = CFBSConfig.get_instance().index
    default_version = current_index.get_module_object("masterfiles")["version"]

    reference_version = analyzed_files.reference_version
    if reference_version is None:
        print(
            "Did not detect any version of masterfiles, proceeding using the default version (%s)."
            % default_version
        )
        masterfiles_version = default_version
    else:
        print("Detected version %s of masterfiles." % reference_version)
        masterfiles_version = reference_version

    if not prompt_user_yesno(
        non_interactive,
        "Do you want to continue making a new CFEngine Build project based on masterfiles %s?"
        % masterfiles_version,
    ):
        raise CFBSExitError("User did not proceed, exiting.")

    print("Initializing a new CFBS project...")
    # since there should be no other files than the masterfiles-name directory, there shouldn't be a .git directory
    assert not is_git_repo()
    r = init_command(masterfiles="no", non_interactive=non_interactive, use_git=True)
    # the cfbs-init should've created a Git repository
    assert is_git_repo()
    if r != 0:
        print("Initializing a new CFBS project failed, aborting conversion.")
        cfbs_convert_cleanup()
        return r

    print("Adding masterfiles %s to the project..." % masterfiles_version)
    masterfiles_to_add = ["masterfiles@%s" % masterfiles_version]
    r = add_command(masterfiles_to_add, added_by="cfbs convert")
    if r != 0:
        print("Adding the masterfiles module failed, aborting conversion.")
        cfbs_convert_cleanup()
        return r

    print("Adding the policy files...")
    local_module_to_add = [path_string]
    r = add_command(
        local_module_to_add,
        added_by="cfbs convert",
        explicit_build_steps=["copy ./ ./"],
    )
    if r != 0:
        print("Adding the policy files module failed, aborting conversion.")
        cfbs_convert_cleanup()
        return r

    # here, matching files are files that have identical (filepath, checksum)
    if len(analyzed_files.unmodified) != 0:
        print(
            "Deleting matching files between masterfiles %s and '%s'..."
            % (masterfiles_version, path_string)
        )
        for unmodified_mpf_file in analyzed_files.unmodified:
            rm(os.path.join(dir_name, unmodified_mpf_file))

        print("Creating Git commit...")
        cfbs_convert_git_commit("Deleted unmodified policy files")

    print(
        "Your project is now functional, can be built, and will produce a version of masterfiles %s with your modifications."
        % masterfiles_version
    )
    print(
        "The next conversion step is to handle files from other versions of masterfiles."
    )
    if not prompt_user_yesno(non_interactive, "Do you want to continue?"):
        raise CFBSExitError("User did not proceed, exiting.")
    other_versions_files = analyzed_files.different
    if len(other_versions_files) > 0:
        print(
            "The following files are taken from other versions of masterfiles (not %s):"
            % masterfiles_version
        )
        other_versions_files = sorted(other_versions_files)
        files_to_delete = []
        for other_version_file, other_versions in other_versions_files:
            # don't display all versions (which is an arbitrarily-shaped sequence), instead choose the most relevant one:
            relevant_version_text = most_relevant_version(
                other_versions, masterfiles_version
            )
            if len(other_versions) > 1:
                relevant_version_text += ", ..."
            print("-", other_version_file, "(%s)" % relevant_version_text)

            files_to_delete.append(other_version_file)
        print(
            "This usually indicates that someone made mistakes during past upgrades and it's recommended to delete these."
        )
        print(
            "Your policy set will include the versions from %s instead (if they exist)."
            % masterfiles_version
        )
        print(
            "(Deletions will be visible in Git history so you can review or revert later)."
        )
        if prompt_user_yesno(
            non_interactive, "Delete files from other versions? (Recommended)"
        ):
            print("Deleting %s files." % len(files_to_delete))
            for file_d in files_to_delete:
                rm(os.path.join(dir_name, file_d))

            print(
                "Creating Git commit with deletion of policy files from other versions..."
            )
            cfbs_convert_git_commit("Deleted policy files from other versions")
            print("Done.", end=" ")
    else:
        print("There are no files from other versions of masterfiles.")
    print(
        "The next conversion step is to handle files which have custom modifications."
    )
    print("This is not implemented yet.")
    return 0


@cfbs_command("input")
@commit_after_command("Added input for module%s", [PLURAL_S])
def input_command(args, input_from="cfbs input"):
    config = CFBSConfig.get_instance()
    validate_config_raise_exceptions(config, empty_build_list_ok=True)
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
            if not prompt_user_yesno(
                config.non_interactive,
                "Input already exists for this module, do you want to overwrite it?",
                default="no",
            ):
                continue

        input_data = copy.deepcopy(module["input"])
        config.input_command(module_name, input_data)

        write_json(input_path, input_data)
        do_commit = True
        files_to_commit.append(input_path)
    config.save()
    return CFBSCommandGitResult(0, do_commit, None, files_to_commit)


@cfbs_command("set-input")
@commit_after_command("Set input for module %s", [FIRST_ARG])
def set_input_command(name, infile):
    config = CFBSConfig.get_instance()
    config.warn_about_unknown_keys()
    module = config.get_module_from_build(name)
    if module is None:
        log.error("Module '%s' not found" % name)
        return CFBSCommandGitResult(1)

    spec = module.get("input")
    if spec is None:
        log.error("Module '%s' does not accept input" % name)
        return CFBSCommandGitResult(1)
    log.debug("Input spec for module '%s': %s" % (name, pretty(spec)))

    try:
        data = json.load(infile, object_pairs_hook=OrderedDict)
    except json.decoder.JSONDecodeError as e:
        log.error("Error reading json from stdin: %s" % e)
        return CFBSCommandGitResult(1)
    log.debug("Input data for module '%s': %s" % (name, pretty(data)))

    def _compare_dict(a, b, ignore=None):
        assert isinstance(a, dict) and isinstance(b, dict)
        ignore = ignore or set()
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
            if type(x) is not type(y):
                return False
            if isinstance(x, dict):
                if not _compare_dict(x, y):
                    return False
            elif isinstance(x, list):
                if not _compare_list(x, y):
                    return False
            else:
                assert x is None or isinstance(
                    x, (int, float, str, bool)
                ), "Illegal value type"
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
            return CFBSCommandGitResult(1)

    path = os.path.join(name, "input.json")

    log.debug("Comparing with data already in file '%s'" % path)
    old_data = read_json(path)
    changes_made = old_data != data

    if changes_made:
        write_json(path, data)
        log.debug(
            "Input data for '%s' changed, writing json to file '%s'" % (name, path)
        )
    else:
        log.debug("Input data for '%s' unchanged, nothing to write / commit" % name)

    return CFBSCommandGitResult(0, changes_made, None, [path])


@cfbs_command("get-input")
def get_input_command(name, outfile):
    config = CFBSConfig.get_instance()
    config.warn_about_unknown_keys()
    module = config.get_module_from_build(name)
    if module is None:
        module = config.index.get_module_object(name)
    if module is None:
        log.error("Module '%s' not found" % name)
        return 1

    if "input" not in module:
        data = []
    else:
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


@cfbs_command("generate-release-information")
def generate_release_information_command(
    omit_download=False, check=False, min_version=None
):
    generate_release_information(omit_download, check, min_version)
    return 0
