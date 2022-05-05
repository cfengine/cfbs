"""
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.
"""
import os
import re
import logging as log
import json

from cfbs.utils import (
    cfbs_dir,
    cfbs_filename,
    is_cfbs_repo,
    item_index,
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

from cfbs.pretty import pretty_check_file, pretty_file
from cfbs.build import init_out_folder, perform_build_steps
from cfbs.cfbs_config import CFBSConfig, CFBSReturnWithoutCommit
from cfbs.cfbs_json import CFBSJson
from cfbs.validate import CFBSIndexException, validate_index
from cfbs.internal_file_management import (
    fetch_archive,
    get_download_path,
    local_module_copy,
    SUPPORTED_ARCHIVES,
)
from cfbs.index import _VERSION_INDEX
from cfbs.git import (
    is_git_repo,
    git_get_config,
    git_set_config,
    git_init,
    CFBSGitError,
)
from cfbs.git_magic import commit_after_command, git_commit_maybe_prompt
from cfbs.prompts import YES_NO_CHOICES, prompt_user


_MODULES_URL = "https://archive.build.cfengine.com/modules"

PLURAL_S = lambda args, kwargs: "s" if len(args[0]) > 1 else ""
FIRST_ARG_SLIST = lambda args, kwargs: ", ".join("'%s'" % module for module in args[0])


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


def init_command(index=None, non_interactive=False) -> int:
    if is_cfbs_repo():
        user_error("Already initialized - look at %s" % cfbs_filename())

    name = prompt_user("Please enter name of this CFBS repository", default="Example")
    description = prompt_user(
        "Please enter description of this CFBS repository",
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

    is_git = is_git_repo()
    if is_git:
        git_ans = prompt_user(
            "This is a git repository. Do you want cfbs to make commits to it?",
            choices=YES_NO_CHOICES,
            default="yes",
        )
    else:
        git_ans = prompt_user(
            "Do you want cfbs to initialize a git repository and make commits to it?",
            choices=YES_NO_CHOICES,
            default="yes",
        )
    do_git = git_ans.lower() in ("yes", "y")

    if do_git:
        user_name = git_get_config("user.name")
        user_email = git_get_config("user.email")
        user_name = prompt_user(
            "Please enter user name to use for git commits", default=user_name or "cfbs"
        )

        node_name = os.uname().nodename
        user_email = prompt_user(
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
    cfbs.json did not exist, thus the instance is empty. By manually deleting
    this instance, a new instance will be created loading the now existing
    cfbs.json.
    """
    CFBSConfig.instance = None

    if prompt_user(
        "Do you wish to build on top of the default policy set, masterfiles? (Recommended)",
        choices=YES_NO_CHOICES,
        default="yes",
    ) in ("yes", "y"):
        to_add = "masterfiles"
    else:
        to_add = prompt_user(
            "Specify policy set to use instead (empty to skip)", default=""
        )

    if to_add:
        return add_command([to_add])

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
    for name in to_remove:
        if name.startswith(("https://", "ssh://", "git://")):
            matches = _get_modules_by_url(name)
            if not matches:
                user_error("Could not find module with URL '%s'" % name)
            for module in matches:
                answer = prompt_user(
                    "Do you wish to remove '%s'?" % module["name"],
                    choices=YES_NO_CHOICES,
                    default="yes",
                )
                if answer.lower() in ("yes", "y"):
                    print("Removing module '%s'" % module["name"])
                    modules.remove(module)
                    num_removed += 1
        else:
            module = _get_module_by_name(name)
            if module:
                print("Removing module '%s'" % name)
                modules.remove(module)
                num_removed += 1
            else:
                print("Module '%s' not found" % name)

    config.save()
    if num_removed:
        _clean_unused_modules(config)
        return 0
    else:
        raise CFBSReturnWithoutCommit(0)


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
        "Do you wish to remove these modules?", choices=YES_NO_CHOICES, default="yes"
    )
    if answer.lower() in ("yes", "y"):
        for module in to_remove:
            modules.remove(module)
        config.save()

    return 0


@commit_after_command("Updated all modules")
def update_command():
    new_deps = []
    new_deps_added_by = dict()
    config = CFBSConfig.get_instance()
    index = config.index
    changes_made = False
    for module in config["build"]:
        if "index" in module:
            # not a module from the default index, not updating
            continue

        index_info = index.get(module["name"])
        if not index_info:
            log.warning(
                "Module '%s' not present in the index, cannot update it", module["name"]
            )
            continue

        if (
            "version" in module
            and module["version"] != index_info["version"]
            and module["commit"] == index_info["commit"]
        ):
            log.warning(
                "Version and commit mismatch detected."
                + " The module %s has the same commit but different version"
                + " locally (%s) and in the index (%s)."
                + " Skipping its update.",
                module["name"],
                module["version"],
                index_info["version"],
            )
            continue

        if "version" in module:
            local_ver = [
                int(version_number)
                for version_number in re.split("[-\.]", module["version"])
            ]
            index_ver = [
                int(version_number)
                for version_number in re.split("[-\.]", index_info["version"])
            ]
            if local_ver > index_ver:
                print(
                    (
                        "Locally installed version of module %s (%s)"
                        + " is newer than the version in index (%s), not updating."
                    )
                    % (module["name"], module["version"], index_info["version"])
                )
                continue

        commit_differs = module["commit"] != index_info["commit"]
        for key, value in module.items():
            if key not in index_info or module[key] == index_info[key]:
                continue
            if key == "steps":
                # same commit => user modifications, don't revert them
                if commit_differs:
                    ans = prompt_user(
                        "Module %s has different build steps now\n" % module["name"]
                        + "old steps: %s\n" % module["steps"]
                        + "new steps: %s\n" % index_info["steps"]
                        + "Do you want to use the new build steps?",
                        choices=YES_NO_CHOICES,
                        default="yes",
                    )
                    if ans.lower() in ["y", "yes"]:
                        module["steps"] = index_info["steps"]
                    else:
                        print(
                            "Please make sure the old build steps work"
                            + " with the new version of the module"
                        )
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

    if new_deps:
        objects = [index.get_module_object(d, new_deps_added_by[d]) for d in new_deps]
        config.add_with_dependencies(objects)
    config.save()

    return 0 if changes_made else 2


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


def _download_dependencies(config, prefer_offline=False, redownload=False):
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
            elif "index" in module:
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


def download_command(force):
    config = CFBSConfig.get_instance()
    _download_dependencies(config, redownload=force)


def build_command() -> int:
    config = CFBSConfig.get_instance()
    init_out_folder()
    _download_dependencies(config, prefer_offline=True)
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
