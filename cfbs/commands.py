"""
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.
"""
import os
import re
import distutils.spawn
import logging as log

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
    fetch_url,
    FetchError,
    is_a_commit_hash,
)

from cfbs.pretty import pretty_check_file, pretty_file
from cfbs.index import CFBSConfig
from cfbs.validate import CFBSIndexException, validate_index


_SUPPORTED_TAR_TYPES = (".tar.gz", ".tgz")
_SUPPORTED_ARCHIVES = (".zip",) + _SUPPORTED_TAR_TYPES

_MODULES_URL = "https://cfbs.s3.amazonaws.com/modules"
_VERSION_INDEX = (
    "https://raw.githubusercontent.com/cfengine/cfbs-index/master/versions.json"
)

# TODO: Move this to CFBSConfig
definition = None


# This function is for clearing the global for pytest cases when it should be changing
# TODO: Move this to CFBSConfig
def clear_definition():
    global definition
    definition = None


# TODO: Move this to CFBSConfig
def get_definition() -> CFBSConfig:
    global definition
    if not definition:
        definition = CFBSConfig()
    if not definition:
        user_error("Unable to read {}".format(cfbs_filename()))
    return definition


# TODO: Move this to CFBSConfig
def put_definition(data=None):
    global definition
    if not definition:
        definition = CFBSConfig(data=data)
    definition.save(data)


def pretty_command(filenames: list, check) -> int:
    if not filenames:
        user_error("Filenames missing for cfbs pretty command")

    num_files = 0
    for f in filenames:
        if not f or not f.endswith(".json"):
            user_error(
                "cfbs pretty command can only be used with .json files, not '%s'"
                % os.path.basename(f)
            )
        try:
            if check:
                if not pretty_check_file(f):
                    num_files += 1
                    print("Would reformat %s" % f)
            else:
                pretty_file(f)
        except FileNotFoundError:
            user_error("File '%s' not found" % f)
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

    definition = get_definition()
    print("Name:        %s" % definition["name"])
    print("Description: %s" % definition["description"])
    print("File:        %s" % cfbs_filename())

    modules = definition["build"]
    print("\nModules:")
    max_length = longest_module_name()
    counter = 1
    for m in modules:
        path = get_download_path(m)
        status = "Downloaded" if os.path.exists(path) else "Not downloaded"
        name = pad_right(m["name"], max_length)
        print("%03d %s @ %s (%s)" % (counter, name, m["commit"], status))
        counter += 1

    return 0


def search_command(terms: list, index_path=None) -> int:
    config = CFBSConfig(index_path)
    index = config.index
    results = {}

    # in order to gather all aliases, we must iterate over everything first
    for name, data in index.get_modules().items():
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


def local_module_name(module_path):
    assert os.path.exists(module_path)
    module = module_path

    if module.endswith((".cf", ".json", "/")) and not module.startswith("./"):
        module = "./" + module
    if not module.startswith("./"):
        user_error("Please prepend local files or folders with './' to avoid ambiguity")

    for illegal in ["//", "..", " ", "\n", "\t", " "]:
        if illegal in module:
            user_error("Module path cannot contain %s" % repr(illegal))

    if os.path.isdir(module) and not module.endswith("/"):
        module = module + "/"
    while "/./" in module:
        module = module.replace("/./", "/")

    assert os.path.exists(module)
    if os.path.isfile(module):
        if not module.endswith((".cf", ".json")):
            user_error("Only .cf and .json files supported currently")
    else:
        if not os.path.isdir(module):
            user_error("'%s' must be either a directory or a file" % module)

    return module


def prettify_name(name):
    if "/" not in name:
        return name
    while name.endswith("/"):
        name = name[:-1]
    if "/" in name:
        name = name.split("/")[-1]
    assert name
    return name


def local_module_copy(module, counter, max_length):
    name = module["name"]
    assert name.startswith("./")
    assert os.path.isfile(name) or os.path.isdir(name)
    pretty_name = prettify_name(name)
    target = "out/steps/%03d_%s_local/" % (counter, pretty_name)
    module["_directory"] = target
    module["_counter"] = counter
    cp(name, target + name)
    print(
        "%03d %s @ local                                    (Copied)"
        % (counter, pad_right(name, max_length))
    )


def _get_path_from_url(url):
    if not url.startswith(("https://", "ssh://", "git://")):
        if "://" in url:
            return user_error("Unsupported URL protocol in '%s'" % url)
        else:
            # It's a path already, just remove trailing slashes (if any).
            return url.rstrip("/")

    path = None
    if url.startswith("ssh://"):
        match = re.match(r"ssh://(\w+)@(.+)", url)
        if match is not None:
            path = match[2]
    path = path or url[url.index("://") + 3 :]
    path = strip_right(path, ".git")
    path = path.rstrip("/")

    return path


def _get_git_repo_commit_sha(repo_path):
    assert os.path.isdir(os.path.join(repo_path, ".git"))

    with open(os.path.join(repo_path, ".git", "HEAD"), "r") as f:
        head_ref_info = f.read()

    assert head_ref_info.startswith("ref: ")
    head_ref = head_ref_info[5:].strip()

    with open(os.path.join(repo_path, ".git", head_ref)) as f:
        return f.read().strip()


def _clone_url_repo(repo_url):
    assert repo_url.startswith(("https://", "ssh://", "git://"))

    commit = None
    if "@" in repo_url and (repo_url.rindex("@") > repo_url.rindex(".")):
        # commit specified in the url
        repo_url, commit = repo_url.rsplit("@", 1)
        if not is_a_commit_hash(commit):
            user_error("'%s' is not a commit reference" % commit)

    downloads = os.path.join(cfbs_dir(), "downloads")

    repo_path = _get_path_from_url(repo_url)
    repo_dir = os.path.join(downloads, repo_path)
    os.makedirs(repo_dir, exist_ok=True)

    if commit is not None:
        commit_path = os.path.join(repo_dir, commit)
        sh("git clone --no-checkout %s %s" % (repo_url, commit_path))
        sh("cd %s; git checkout %s" % (commit_path, commit))
    else:
        master_path = os.path.join(repo_dir, "master")
        sh("git clone %s %s" % (repo_url, master_path))
        commit = _get_git_repo_commit_sha(master_path)

        commit_path = os.path.join(repo_dir, commit)
        if os.path.exists(commit_path):
            # Already cloned in the commit dir, just remove the 'master' clone
            sh("rm -rf %s" % master_path)
        else:
            sh("mv %s %s" % (master_path, commit_path))

    json_path = os.path.join(commit_path, "cfbs.json")
    if os.path.exists(json_path):
        return (json_path, commit)
    else:
        user_error(
            "Repository '%s' doesn't contain a valid cfbs.json index file" % repo_url
        )


def _fetch_archive(url, checksum=None, directory=None, with_index=True):
    assert url.endswith(_SUPPORTED_ARCHIVES)

    url_path = url[url.index("://") + 3 :]
    archive_dirname = os.path.dirname(url_path)
    archive_filename = os.path.basename(url_path)

    for ext in _SUPPORTED_ARCHIVES:
        if archive_filename.endswith(ext):
            archive_type = ext
            break
    else:
        user_error("Unsupported archive type: '%s'" % url)

    archive_name = strip_right(archive_filename, archive_type)
    downloads = os.path.join(cfbs_dir(), "downloads")

    archive_dir = os.path.join(downloads, archive_dirname)
    mkdir(archive_dir)

    archive_path = os.path.join(downloads, archive_dir, archive_filename)
    try:
        archive_checksum = fetch_url(url, archive_path, checksum)
    except FetchError as e:
        user_error(str(e))

    content_dir = os.path.join(downloads, archive_dir, archive_checksum)
    index_path = os.path.join(content_dir, "cfbs.json")
    if with_index and os.path.exists(index_path):
        # available already
        return (index_path, archive_checksum)
    else:
        mkdir(content_dir)

    # TODO: use Python modules instead of CLI tools?
    if archive_type.startswith(_SUPPORTED_TAR_TYPES):
        if distutils.spawn.find_executable("tar"):
            sh("cd %s; tar -xf %s" % (content_dir, archive_path))
        else:
            user_error("Working with .tar archives requires the 'tar' utility")
    elif archive_type == (".zip"):
        if distutils.spawn.find_executable("unzip"):
            sh("cd %s; unzip %s" % (content_dir, archive_path))
        else:
            user_error("Working with .zip archives requires the 'unzip' utility")
    else:
        raise RuntimeError(
            "Unhandled archive type: '%s'. Please report this at %s."
            % (url, "https://github.com/cfengine/cfbs/issues")
        )

    os.unlink(archive_path)

    content_root_items = [
        os.path.join(content_dir, item) for item in os.listdir(content_dir)
    ]
    if (
        with_index
        and len(content_root_items) == 1
        and os.path.isdir(content_root_items[0])
        and os.path.exists(os.path.join(content_root_items[0], "cfbs.json"))
    ):
        # the archive contains a top-level folder, let's just move things one
        # level up from inside it
        sh("mv %s %s" % (os.path.join(content_root_items[0], "*"), content_dir))
        os.rmdir(content_root_items[0])

    if with_index:
        if os.path.exists(index_path):
            return (index_path, archive_checksum)
        else:
            user_error(
                "Archive '%s' doesn't contain a valid cfbs.json index file" % url
            )
    else:
        if directory is not None:
            directory = directory.rstrip("/")
            mkdir(os.path.dirname(directory))
            sh("rsync -a %s/ %s/" % (content_dir, directory))
            rm(content_dir)
            return (directory, archive_checksum)
        return (content_dir, archive_checksum)


def _add_modules(
    to_add: list,
    added_by="cfbs add",
    index_path=None,
    checksum=None,
    non_interactive=False,
) -> int:
    config = CFBSConfig(index_path)
    index = config.index

    # Translate all aliases and remote paths
    translated = []
    for module in to_add:
        if not index.exists(module):
            user_error("Module '%s' does not exist" % module)
        if not module in index and os.path.exists(module):
            translated.append(local_module_name(module))
            continue
        data = index[module]
        if "alias" in data:
            print("%s is an alias for %s" % (module, data["alias"]))
            module = data["alias"]
        translated.append(module)

    to_add = translated

    # added_by can be string, list of strings, or dictionary

    # Convert string -> list:
    if type(added_by) is str:
        added_by = [added_by] * len(to_add)

    # Convert list -> dict:
    if not isinstance(added_by, dict):
        assert len(added_by) == len(to_add)
        added_by = {k: v for k, v in zip(to_add, added_by)}

    # Should have a dict with keys for everything in to_add:
    assert not any((k not in added_by for k in to_add))

    # Print error and exit if there are unknown modules:
    missing = [m for m in to_add if not m.startswith("./") and m not in index]
    if missing:
        user_error("Module(s) could not be found: %s" % ", ".join(missing))

    definition = get_definition()

    # If some modules were added as deps previously, mark them as user requested:
    for module in definition["build"]:
        if module["name"] in to_add:
            new_added_by = added_by[module["name"]]
            if new_added_by == "cfbs add":
                module["added_by"] = "cfbs add"
                put_definition(definition)

    # Filter modules which are already added:
    added = [m["name"] for m in definition["build"]]
    filtered = []
    for module in to_add:
        user_requested = added_by[module] == "cfbs add"
        if module in [*added, *filtered]:
            if user_requested:
                print("Skipping already added module: %s" % module)
            continue
        filtered.append(module)

    # Find all unmet dependencies:
    dependencies = []
    dependencies_added_by = []
    for module in filtered:
        assert index.exists(module)
        data = index.get_build_step(module)
        assert "alias" not in data
        if "dependencies" in data:
            for dep in data["dependencies"]:
                if dep not in [*added, *filtered, *dependencies]:
                    dependencies.append(dep)
                    dependencies_added_by.append(module)

    if dependencies:
        add_command(dependencies, dependencies_added_by)
        definition = get_definition()

    for module in filtered:
        assert index.exists(module)
        data = index.get_build_step(module)
        new_module = {"name": module, **data, "added_by": added_by[module]}
        definition["build"].append(new_module)
        if user_requested:
            print("Added module: %s" % module)
        else:
            print("Added module: %s (Dependency of %s)" % (module, added_by[module]))
        added.append(module)

    put_definition(definition)
    return 0


def _add_using_url(
    url,
    to_add: list,
    added_by="cfbs add",
    index_path=None,
    checksum=None,
    non_interactive=False,
):
    url_commit = None
    if url.endswith(_SUPPORTED_ARCHIVES):
        config_path, url_commit = _fetch_archive(url, checksum)
    else:
        assert url.startswith(("https://", "git://", "ssh://"))
        config_path, url_commit = _clone_url_repo(url)

    remote_config = CFBSConfig(path=config_path, url=url, url_commit=url_commit)
    config = CFBSConfig(index_argument=index_path)

    provides = remote_config.get_provides()
    # URL specified in to_add, but no specific modules => let's add all (with a prompt)
    if len(to_add) == 0:
        modules = list(provides.values())
        print("Found %d modules in '%s':" % (len(modules), url))
        for m in modules:
            print("  - " + m["name"])
        if not non_interactive:
            answer = input("Do you want to add all %d of them? [y/N] " % (len(modules)))
            if answer.lower() not in ("y", "yes"):
                return 0
    else:
        missing = [k for k in to_add if k not in provides]
        if missing:
            user_error("Missing modules: " + ", ".join(missing))
        modules = [provides[k] for k in to_add]

    for module in modules:
        config.add(module, remote_config)

    return 0


def add_command(
    to_add: list,
    added_by="cfbs add",
    index_path=None,
    checksum=None,
    non_interactive=False,
) -> int:
    if not to_add:
        user_error("Must specify at least one module to add")

    if to_add[0].endswith(_SUPPORTED_ARCHIVES) or to_add[0].startswith(
        ("https://", "git://", "ssh://")
    ):
        return _add_using_url(
            to_add[0], to_add[1:], added_by, index_path, checksum, non_interactive
        )

    return _add_modules(to_add, added_by, index_path, checksum, non_interactive)


def remove_command(to_remove: list, non_interactive=False):
    definition = get_definition()
    modules = definition["build"]

    def _get_module_by_name(name) -> dict:
        for module in modules:
            if module["name"] == name:
                return module
        return None

    num_removed = 0
    for name in to_remove:
        module = _get_module_by_name(name)
        if module:
            print("Removing module '%s'" % name)
            modules.remove(module)
            num_removed += 1
        else:
            print("Module '%s' not found" % name)

    put_definition(definition)
    if num_removed:
        clean_command(non_interactive=non_interactive)
    return 0


def clean_command(non_interactive=False):
    definition = get_definition()
    modules = definition["build"]

    def _someone_needs_me(this) -> bool:
        if this["added_by"] == "cfbs add":
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
        print(
            "%s - %s - added by: %s"
            % (module["name"], module["description"], module["added_by"])
        )

    answer = (
        "yes"
        if non_interactive
        else input("Do you wish to remove these modules? [y/N] ")
    )
    if answer.lower() in ("yes", "y"):
        for module in to_remove:
            modules.remove(module)
        put_definition(definition)

    return 0


def update_command(non_interactive=False):
    config = CFBSConfig()
    index = config.index

    new_deps = []
    new_deps_added_by = dict()
    definition = get_definition()
    index_modules = index.get_modules()
    for module in definition["build"]:
        if "index" in module:
            # not a module from the default index, not updating
            continue

        index_info = index_modules.get(module["name"])
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

    put_definition(definition)

    if new_deps:
        add_command(new_deps, new_deps_added_by)


def validate_command(index_path=None):
    config = CFBSConfig(index_path)
    index = config.index
    if not index:
        user_error("Index not found")

    try:
        validate_index(index.get())
    except CFBSIndexException as e:
        print(e)
        return 1
    return 0


def init_build_folder():
    rm("out", missing_ok=True)
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


def longest_module_name() -> int:
    return max((len(m["name"]) for m in get_definition()["build"]))


def get_download_path(module) -> str:
    downloads = os.path.join(cfbs_dir(), "downloads")

    commit = module["commit"]
    if not is_a_commit_hash(commit):
        user_error("'%s' is not a commit reference" % commit)

    url = module.get("url") or module["repo"]
    if url.endswith(_SUPPORTED_ARCHIVES):
        url = os.path.dirname(url)
    else:
        url = strip_right(url, ".git")
    repo = url[url.index("://") + 3 :]
    repo_dir = os.path.join(downloads, repo)
    mkdir(repo_dir)
    return os.path.join(repo_dir, commit)


def download_dependencies(prefer_offline=False, redownload=False):
    print("\nModules:")
    counter = 1
    definition = get_definition()
    max_length = longest_module_name()
    downloads = os.path.join(cfbs_dir(), "downloads")
    for module in definition["build"]:
        name = module["name"]
        if name.startswith("./"):
            local_module_copy(module, counter, max_length)
            counter += 1
            continue
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
            if url.endswith(_SUPPORTED_ARCHIVES):
                _fetch_archive(url, commit)
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
                _fetch_archive(
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
    download_dependencies(redownload=force)


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
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        extras, original = read_json(src), read_json(dst)
        assert extras is not None
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


def build_steps() -> int:
    print("\nSteps:")
    module_name_length = longest_module_name()
    for module in get_definition()["build"]:
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
    print("To install on this machine: cfbs install")
    print("To deploy on remote hub(s): cf-remote deploy --hub hub out/masterfiles.tgz")
    return 0


def build_command() -> int:
    init_build_folder()
    download_dependencies(prefer_offline=True)
    build_steps()


def install_command(destination=None) -> int:
    if not os.path.exists("out/masterfiles"):
        r = build_command()
        if r != 0:
            return r

    if not destination:
        destination = "/var/cfengine/masterfiles"
    rm(destination, missing_ok=True)
    cp("out/masterfiles", destination)
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
    config = CFBSConfig(index_path)
    index = config.index

    if os.path.isfile(cfbs_filename()):
        build = get_definition()["build"]
    else:
        build = {}

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
