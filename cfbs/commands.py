"""
Functions ending in "_command" are dynamically included in the list of commands
in main.py for -h/--help/help.
"""
import os
import re
import distutils.spawn

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

from cfbs.pretty import pretty_check_file, pretty_file, pretty
from cfbs.index import Index
from cfbs.validate import CFBSIndexException, validate_index


_SUPPORTED_TAR_TYPES = (".tar.gz", ".tgz")
_SUPPORTED_ARCHIVES = (".zip",) + _SUPPORTED_TAR_TYPES

_MODULES_URL = "https://cfbs.s3.amazonaws.com/modules"
_VERSION_INDEX = "https://raw.githubusercontent.com/cfengine/cfbs-index/master/versions.json"


definition = None


# This function is for clearing the global for pytest cases when it should be changing
def clear_definition():
    global definition
    definition = None


def get_definition() -> dict:
    global definition
    if not definition:
        definition = read_json(cfbs_filename())
    if not definition:
        user_error("Unable to read {}".format(cfbs_filename()))
    return definition


def put_definition(data: dict):
    global definition
    definition = data
    with open(cfbs_filename(), "w") as f:
        f.write(pretty(data))


def pretty_command(filenames: list, check) -> int:
    if not filenames:
        user_error("Filenames missing for cfbs pretty command")

    num_files = 0
    for f in filenames:
        if not f or not f.endswith(".json"):
            user_error(
                f"cfbs pretty command can only be used with .json files, not '{os.path.basename(f)}'"
            )
        try:
            if check:
                if not pretty_check_file(f):
                    num_files += 1
                    print("Would reformat %s" % f)
            else:
                pretty_file(f)
        except FileNotFoundError:
            user_error(f"File '{f}' not found")
    if check:
        print("Would reformat %d file(s)" % num_files)
        return 1 if num_files > 0 else 0
    return 0


def init_command(index=None) -> int:
    if is_cfbs_repo():
        user_error(f"Already initialized - look at {cfbs_filename()}")

    definition = {
        "name": "Example",
        "description": "Example description",
        "build": [],
    }
    if index:
        definition["index"] = index

    write_json(cfbs_filename(), definition)
    assert is_cfbs_repo()
    print(f"Initialized - edit name and description {cfbs_filename()}")
    print(f"To add your first module, type: cfbs add masterfiles")

    return 0


def status_command() -> int:

    definition = get_definition()
    print(f'Name:        {definition["name"]}')
    print(f'Description: {definition["description"]}')
    print(f"File:        {cfbs_filename()}")

    modules = definition["build"]
    print(f"\nModules:")
    max_length = longest_module_name()
    counter = 1
    for m in modules:
        path = get_download_path(m)
        status = "Downloaded" if os.path.exists(path) else "Not downloaded"
        name = pad_right(m["name"], max_length)
        print(f"{counter:03d} {name} @ {m['commit']} ({status})")
        counter += 1

    return 0


def get_index_from_config():
    if not os.path.isfile(cfbs_filename()):
        return None
    conf = get_definition()
    if not "index" in conf:
        return None
    return conf["index"]


def search_command(terms: list, index=None) -> int:
    if not index:
        index = get_index_from_config()
    index = Index(index)
    found = False
    # No search term, list everything:
    if not terms:
        for name, data in index.get_modules().items():
            if "alias" in data:
                continue
            print(name)
            found = True
        return 0 if found else 1

    # Print all modules which match at least 1 search term:
    for name, data in index.get_modules().items():
        if any((t for t in terms if t in name)):
            if "alias" in data:
                print(f"{name} -> {data['alias']}")
            else:
                print(name)
            found = True
    return 0 if found else 1


def local_module_name(module_path):
    assert os.path.exists(module_path)
    module = module_path

    if module.endswith((".cf", ".json", "/")) and not module.startswith("./"):
        module = "./" + module
    if not module.startswith("./"):
        user_error(
            f"Please prepend local files or folders with './' to avoid ambiguity"
        )

    for illegal in ["//", "..", " ", "\n", "\t", " "]:
        if illegal in module:
            user_error(f"Module path cannot contain {repr(illegal)}")

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
            user_error(f"'{module}' must be either a directory or a file")

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
    target = f"out/steps/{counter:03d}_{pretty_name}_local/"
    module["_directory"] = target
    module["_counter"] = counter
    cp(name, target + name)
    print(
        f"{counter:03d} {pad_right(name, max_length)} @ local                                    (Copied)"
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


def _clone_index_repo(repo_url):
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

    index_path = os.path.join(commit_path, "cfbs.json")
    if os.path.exists(index_path):
        return (index_path, commit)
    else:
        user_error(
            "Repository '%s' doesn't contain a valid cfbs.json index file" % repo_url
        )


def _fetch_archive(url, checksum=None, directory=None, with_index=True):
    assert url.endswith(_SUPPORTED_ARCHIVES)

    url_path = url[url.index("://") + 3:]
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
        raise RuntimeError("Unhandled archive type: '%s'. Please report this at %s." %
                           (url, "https://github.com/cfengine/cfbs/issues"))

    os.unlink(archive_path)

    content_root_items = [os.path.join(content_dir, item) for item in os.listdir(content_dir)]
    if (with_index and len(content_root_items) == 1 and os.path.isdir(content_root_items[0]) and
        os.path.exists(os.path.join(content_root_items[0], "cfbs.json"))):
        # the archive contains a top-level folder, let's just move things one
        # level up from inside it
        sh("mv %s %s" % (os.path.join(content_root_items[0], "*"), content_dir))
        os.rmdir(content_root_items[0])

    if with_index:
        if os.path.exists(index_path):
            return (index_path, archive_checksum)
        else:
            user_error("Archive '%s' doesn't contain a valid cfbs.json index file" % url)
    else:
        if directory is not None:
            directory = directory.rstrip("/")
            mkdir(os.path.dirname(directory))
            sh("rsync -a %s/ %s/" % (content_dir, directory))
            rm(content_dir)
            return (directory, archive_checksum)
        return (content_dir, archive_checksum)

def add_command(to_add: list, added_by="cfbs add", index_path=None, checksum=None) -> int:
    if not to_add:
        user_error("Must specify at least one module to add")

    index_commit = None
    index_repo = None
    if to_add[0].endswith(_SUPPORTED_ARCHIVES):
        archive_url = index_repo = to_add.pop(0)
        index_path, index_commit = _fetch_archive(archive_url, checksum)
    elif to_add[0].startswith(("https://", "git://", "ssh://")):
        index_repo = to_add.pop(0)
        index_path, index_commit = _clone_index_repo(index_repo)

    default_index = False
    if not index_path:
        default_index = True
        index_path = get_index_from_config()

    index = Index(index_path)

    # URL specified in to_add, but no specific modules => let's add all (with a prompt)
    if len(to_add) == 0:
        modules = index.get_modules()
        answer = input(
            "Do you want to add all %d modules from '%s'? [y/N] " % (len(modules), index_repo)
        )
        if answer.lower() not in ("y", "yes"):
            return 0
        to_add = modules.keys()

    # Translate all aliases and remote paths
    translated = []
    for module in to_add:
        if not index.exists(module):
            user_error(f"Module '{module}' does not exist")
        if not module in index and os.path.exists(module):
            translated.append(local_module_name(module))
            continue
        data = index[module]
        if "alias" in data:
            print(f'{module} is an alias for {data["alias"]}')
            module = data["alias"]
        translated.append(module)
        if not default_index:
            if index_repo:
                index[module]["index"] = index_repo
                index[module]["repo"] = index_repo
            if index_commit:
                index[module]["commit"] = index_commit

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
        user_error(f"Module(s) could not be found: {', '.join(missing)}")

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
        if module in [*added, *filtered] and user_requested:
            print(f"Skipping already added module: {module}")
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
            print(f"Added module: {module}")
        else:
            print(f"Added module: {module} (Dependency of {added_by[module]})")
        added.append(module)

    put_definition(definition)


def validate_command(index=None):
    if not index:
        index = get_index_from_config()
    if not index:
        user_error("Index not found")

    index = Index(index)._get()

    try:
        validate_index(index)
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

    url = module["repo"]
    if url.endswith(_SUPPORTED_ARCHIVES):
        url = os.path.dirname(url)
    else:
        url = strip_right(url, ".git")
    repo = url[url.index("://") + 3:]
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

        url = strip_right(module["repo"], ".git")
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
                sh(f"git clone {url} {commit_dir}")
                sh(f"(cd {commit_dir} && git checkout {commit})")
            else:
                versions = get_json(_VERSION_INDEX)
                try:
                    checksum = versions[name][module["version"]]["archive_sha256"]
                except KeyError:
                    user_error("Cannot verify checksum of the '%s' module" % name)
                module_archive_url = os.path.join(_MODULES_URL, name, commit + ".tar.gz")
                _fetch_archive(module_archive_url, checksum, directory=commit_dir, with_index=False)
        target = f"out/steps/{counter:03d}_{module['name']}_{commit}/"
        module["_directory"] = target
        module["_counter"] = counter
        subdirectory = module.get("subdirectory", None)
        if not subdirectory:
            cp(commit_dir, target)
        else:
            cp(os.path.join(commit_dir, subdirectory), target)
        print(f"{counter:03d} {pad_right(name, max_length)} @ {commit} (Downloaded)")
        counter += 1


def download_command(force):
    download_dependencies(redownload=force)


def build_step(module, step, max_length):
    step = step.split(" ")
    operation, args = step[0], step[1:]
    source = module["_directory"]
    counter = module["_counter"]
    destination = "out/masterfiles"

    prefix = f"{counter:03d} {pad_right(module['name'], max_length)} :"

    if operation == "copy":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print(f"{prefix} copy '{src}' 'masterfiles/{dst}'")
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        cp(src, dst)
    elif operation == "run":
        shell_command = " ".join(args)
        print(f"{prefix} run '{shell_command}'")
        sh(shell_command, source)
    elif operation == "delete":
        files = [args] if type(args) is str else args
        assert len(files) > 0
        as_string = " ".join([f"'{f}'" for f in files])
        print(f"{prefix} delete {as_string}")
        for file in files:
            rm(os.path.join(source, file))
    elif operation == "json":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print(f"{prefix} json '{src}' 'masterfiles/{dst}'")
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        extras, original = read_json(src), read_json(dst)
        assert extras is not None
        if not extras:
            print(f"Warning: '{os.path.basename(src)}' looks empty, adding nothing")
        if original:
            merged = merge_json(original, extras)
        else:
            merged = extras
        write_json(dst, merged)
    elif operation == "append":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print(f"{prefix} append '{src}' 'masterfiles/{dst}'")
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        if not os.path.exists(dst):
            touch(dst)
        assert os.path.isfile(dst)
        sh(f"cat '{src}' >> '{dst}'")
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
        user_error(f"Unknown build step operation: {operation}")


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


def info_command(modules, index=None):
    if not index:
        index = get_index_from_config()
    index = Index(index)
    build = get_definition()["build"]
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
