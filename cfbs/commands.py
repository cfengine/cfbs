"""
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.
"""
import os
import re
import distutils.spawn
import logging as log
import shutil
import json

from cfbs.utils import (
    cfbs_dir,
    cfbs_filename,
    is_cfbs_repo,
    user_error,
    strip_left,
    strip_right,
    pad_right,
    get_json,
    write_json,
    read_json,
    merge_json,
    mkdir,
    touch,
    rm,
    cp,
    sh,
    is_a_commit_hash,
)

from cfbs.pretty import pretty_check_file, pretty_file
from cfbs.core import CFBSJson, CFBSConfig
from cfbs.validate import CFBSIndexException, validate_index
from cfbs.internal_file_management import (
    fetch_archive,
    get_download_path,
    local_module_copy,
    SUPPORTED_ARCHIVES,
)


_MODULES_URL = "https://archive.build.cfengine.com/modules"
_VERSION_INDEX = (
    "https://raw.githubusercontent.com/cfengine/build-index/master/versions.json"
)


def _item_index(iterable, item, extra_at_end=True):
    try:
        return iterable.index(item)
    except ValueError:
        if extra_at_end:
            return len(iterable)
        else:
            return -1


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
                lambda child_item: _item_index(top_level_keys, child_item[0]),
                {
                    "index": (
                        lambda child_item: child_item[0],
                        {
                            ".*": (
                                lambda child_item: _item_index(
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


def init_command(index_path=None, non_interactive=False) -> int:
    if is_cfbs_repo():
        user_error("Already initialized - look at %s" % cfbs_filename())

    definition = {
        "name": "Example",
        "type": "policy-set",  # TODO: Prompt whether user wants to make a module
        "description": "Example description",
        "build": [],  # TODO: Prompt what masterfile user wants to add
    }
    if index_path:
        definition["index_path"] = index_path

    write_json(cfbs_filename(), definition)
    assert is_cfbs_repo()
    print("Initialized - edit name and description %s" % cfbs_filename())
    print("To add your first module, type: cfbs add masterfiles")

    return 0


def status_command() -> int:

    definition = CFBSConfig()
    print("Name:        %s" % definition["name"])
    print("Description: %s" % definition["description"])
    print("File:        %s" % cfbs_filename())

    modules = definition["build"]
    if not modules:
        return 0
    print("\nModules:")
    max_length = longest_module_name(definition)
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


def search_command(terms: list, index_path=None) -> int:
    config = CFBSConfig(index=index_path)
    index = config.index
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


def add_command(
    to_add: list,
    added_by="cfbs add",
    index_path=None,
    checksum=None,
    non_interactive=False,
) -> int:
    config = CFBSConfig()
    r = config.add_command(to_add, added_by, index_path, checksum, non_interactive)
    config.save()
    return r


def remove_command(to_remove: list, non_interactive=False):
    definition = CFBSConfig()
    modules = definition["build"]

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
                answer = (
                    "yes"
                    if non_interactive
                    else input("Do you wish to remove '%s'? [y/N] " % module["name"])
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

    definition.save()
    if num_removed:
        clean_command(non_interactive=non_interactive, definition=definition)
    return 0


def clean_command(non_interactive=False, definition=None):
    if not definition:
        definition = CFBSConfig()
    modules = definition["build"]

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
        return 0

    print("The following modules were added as dependencies but are no longer needed:")
    for module in to_remove:
        name = module["name"] if "name" in module else ""
        description = module["description"] if "description" in module else ""
        added_by = module["added_by"] if "added_by" in module else ""
        print("%s - %s - added by: %s" % (name, description, added_by))

    answer = (
        "yes"
        if non_interactive
        else input("Do you wish to remove these modules? [y/N] ")
    )
    if answer.lower() in ("yes", "y"):
        for module in to_remove:
            modules.remove(module)
        definition.save()

    return 0


def update_command(non_interactive=False):
    new_deps = []
    new_deps_added_by = dict()
    definition = CFBSConfig()
    index = definition.index
    for module in definition["build"]:
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
                int(version_number) for version_number in module["version"].split(".")
            ]
            index_ver = [
                int(version_number)
                for version_number in index_info["version"].split(".")
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
                    if non_interactive:
                        ans = "yes"
                    else:
                        ans = input(
                            "Module %s has different build steps now\n" % module["name"]
                            + "old steps: %s\n" % module["steps"]
                            + "new steps: %s\n" % index_info["steps"]
                            + "Do you want to use the new build steps? [y/N]"
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

        # add new items
        for key in set(index_info.keys()) - set(module.keys()):
            module[key] = index_info[key]
            if key == "dependencies":
                extra = index_info["dependencies"]
                new_deps.extend(extra)
                new_deps_added_by.update({item: module["name"] for item in extra})

    if new_deps:
        objects = [index.get_module_object(d, new_deps_added_by[d]) for d in new_deps]
        definition.add_with_dependencies(objects)
    definition.save()


def validate_command(index_path=None):
    if index_path:
        index = CFBSJson(path=index_path).index
    elif CFBSConfig.exists():
        index = CFBSConfig().index
    else:
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


def init_build_folder(config):
    rm("out", missing_ok=True)
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


def longest_module_name(config) -> int:
    return max((len(m["name"]) for m in config["build"]))


def download_dependencies(config, prefer_offline=False, redownload=False):
    print("\nModules:")
    counter = 1
    max_length = longest_module_name(config)
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
    config = CFBSConfig()
    download_dependencies(config, redownload=force)


def build_step(module, step, max_length):
    step = step.split(" ")
    operation, args = step[0], step[1:]
    source = module["_directory"]
    counter = module["_counter"]
    destination = "out/masterfiles"

    prefix = "%03d %s :" % (counter, pad_right(module["name"], max_length))

    if operation == "copy":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s copy '%s' 'masterfiles/%s'" % (prefix, src, dst))
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        cp(src, dst)
    elif operation == "run":
        shell_command = " ".join(args)
        print("%s run '%s'" % (prefix, shell_command))
        sh(shell_command, source)
    elif operation == "delete":
        files = [args] if type(args) is str else args
        assert len(files) > 0
        as_string = " ".join(["'%s'" % f for f in files])
        print("%s delete %s" % (prefix, as_string))
        for file in files:
            rm(os.path.join(source, file))
    elif operation == "json":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s json '%s' 'masterfiles/%s'" % (prefix, src, dst))
        if not os.path.isfile(os.path.join(source, src)):
            user_error("'%s' is not a file" % src)
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        extras, original = read_json(src), read_json(dst)
        if not extras:
            print("Warning: '%s' looks empty, adding nothing" % os.path.basename(src))
        if original:
            merged = merge_json(original, extras)
        else:
            merged = extras
        write_json(dst, merged)
    elif operation == "append":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s append '%s' 'masterfiles/%s'" % (prefix, src, dst))
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        if not os.path.exists(dst):
            touch(dst)
        assert os.path.isfile(dst)
        sh("cat '%s' >> '%s'" % (src, dst))
    elif operation == "directory":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("{} directory '{}' 'masterfiles/{}'".format(prefix, src, dst))
        dstarg = dst  # save this for adding .cf files to inputs
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        defjson = os.path.join(destination, "def.json")
        merged = read_json(defjson)
        if not merged:
            merged = {}
        if "classes" not in merged:
            merged["classes"] = {}
        if "services_autorun_bundles" not in merged["classes"]:
            merged["classes"]["services_autorun_bundles"] = ["any"]
        inputs = []
        for root, dirs, files in os.walk(src):
            for f in files:
                if f.endswith(".cf"):
                    inputs.append(os.path.join(dstarg, f))
                    cp(os.path.join(root, f), os.path.join(destination, dstarg, f))
                elif f == "def.json":
                    extra = read_json(os.path.join(root, f))
                    if extra:
                        merged = merge_json(merged, extra)
                else:
                    cp(os.path.join(root, f), os.path.join(destination, dstarg, f))
        if "inputs" in merged:
            merged["inputs"].extend(inputs)
        else:
            merged["inputs"] = inputs
        write_json(defjson, merged)
    else:
        user_error("Unknown build step operation: %s" % operation)


def build_steps(config) -> int:
    print("\nSteps:")
    module_name_length = longest_module_name(config)
    for module in config["build"]:
        for step in module["steps"]:
            build_step(module, step, module_name_length)
    if os.path.isfile("out/masterfiles/def.json"):
        pretty_file("out/masterfiles/def.json")
    print("")
    print("Generating tarball...")
    sh("( cd out/ && tar -czf masterfiles.tgz masterfiles )")
    print("\nBuild complete, ready to deploy 🐿")
    print(" -> Directory: out/masterfiles")
    print(" -> Tarball:   out/masterfiles.tgz")
    print("")
    print("To install on this machine: sudo cfbs install")
    print("To deploy on remote hub(s): cf-remote deploy")
    return 0


def build_command() -> int:
    config = CFBSConfig()
    init_build_folder(config)
    download_dependencies(config, prefer_offline=True)
    build_steps(config)


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


def print_module_info(data):
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


def info_command(modules, index_path=None):
    config = CFBSConfig(index=index_path)
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
            data["status"] = "Added" if in_build else "Not Added"
        else:
            if not module.startswith("./"):
                module = "./" + module
            data = next((m for m in build if m["name"] == module), None)
            if data is None:
                print("Path {} exists but is not yet added as a module.".format(module))
                continue
            data["status"] = "Added"
        data["module"] = (module + "({})".format(alias)) if alias else module
        print_module_info(data)
    print()  # extra line for ease of reading
    return 0


# show_command here to auto-populate into help in main.py
def show_command(module):
    return info_command(module)
