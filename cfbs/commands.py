#!/usr/bin/env python3
import os
import sys

from cf_remote.paths import cfengine_dir

from cfbs.utils import (
    user_error,
    get_json,
    strip_left,
    strip_right,
    pad_right,
    write_json,
    read_json,
    merge_json,
    mkdir,
    touch,
    rm,
    cp,
    sh,
)

from cfbs.pretty import (pretty_file, pretty)


def cfbs_filename() -> str:
    return "cfbs.json"


def is_cfbs_repo() -> bool:
    return os.path.isfile(cfbs_filename())


def cfbs_dir(append=None) -> str:
    return os.path.join(cfengine_dir("cfbs"), append if append else "")


definition = None


def get_definition() -> dict:
    global definition
    if not definition:
        definition = read_json(cfbs_filename())
    return definition


def put_definition(data: dict):
    global definition
    definition = data
    with open(cfbs_filename(), "w") as f:
        f.write(pretty(data))


index = None


def index_url() -> str:
    return "https://raw.githubusercontent.com/cfengine/cfbs-index/master/index.json"


def index_path() -> str:
    return cfbs_dir("index.json")


def get_index(prefer_offline=False) -> dict:
    global index
    if not index and prefer_offline:
        index = read_json(index_path())
    if not index:
        index = get_json(index_url())
        if not index:
            assert not prefer_offline
            index = read_json(index_path())
            if index:
                print("Warning: Downloading index failed, using cache")
    if not index:
        sys.exit("Could not download or find module index")
    if "modules" not in index:
        sys.exit("Empty or invalid module index")
    return index["modules"]

def pretty_command(filenames: list) -> int:
    if not filenames:
        user_error("Filenames missing for cfbs pretty command")
    for f in filenames:
        if not f or not f.endswith(".json"):
            user_error(f"cfbs pretty command can only be used with .json files, not '{os.path.basename(f)}'")
        try:
            pretty_file(f)
        except FileNotFoundError:
            user_error(f"File '{f}' not found")
    return 0


def init_command() -> int:
    if is_cfbs_repo():
        user_error(f"Already initialized - look at {cfbs_filename()}")

    definition = {
        "name": "Example",
        "description": "Example description",
        "build": [],
    }

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


def search_command(terms: list) -> int:
    found = False
    # No search term, list everything:
    if not terms:
        for name, data in get_index().items():
            if "alias" in data:
                continue
            print(name)
            found = True
        return 0 if found else 1

    # Print all modules which match at least 1 search term:
    for name, data in get_index().items():
        if any((t for t in terms if t in name)):
            if "alias" in data:
                print(f"{name} -> {data['alias']}")
            else:
                print(name)
            found = True
    return 0 if found else 1


def module_exists(module_name):
    return os.path.exists(module_name) or (module_name in get_index())

def local_module_name(module_path):
    assert os.path.exists(module_path)
    module = module_path

    if module.endswith((".cf", ".json", "/")) and not module.startswith("./"):
        module = "./" + module
    if not module.startswith("./"):
        user_error(f"Please prepend local files or folders with './' to avoid ambiguity")

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

def local_module_data_cf_file(module):
    target = os.path.basename(module)
    return {
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "dependencies": [ "autorun" ],
      "steps": [f"copy {module} services/autorun/{target}"],
      "added_by": "cfbs add"
    }

def local_module_data_json_file(module):
    return {
      "description": "Local augments file added using cfbs command line",
      "tags": ["local"],
      "steps": [f"json {module} def.json"],
      "added_by": "cfbs add"
    }

def local_module_data_subdir(module):
    return {
      "description": "Local subdirectory added using cfbs command line",
      "tags": ["local"],
      "dependencies": [ "autorun" ],
      "steps": [f"copy {module} services/autorun/"],
      "added_by": "cfbs add"
    }

def local_module_data(module):
    assert module.startswith("./")
    assert module.endswith((".cf", ".json", "/"))
    assert os.path.isfile(module) or os.path.isdir(module)

    if os.path.isdir(module):
        return local_module_data_subdir(module)
    if module.endswith(".cf"):
        return local_module_data_cf_file(module)
    if module.endswith(".json"):
        return local_module_data_json_file(module)

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
    print(f"{counter:03d} {pad_right(name, max_length)} @ local                                    (Copied)")

def get_build_step(module):
    return get_index()[module] if not module.startswith("./") else local_module_data(module)

def add_command(to_add: list, added_by="cfbs add") -> int:
    if not to_add:
        user_error("Must specify at least one module to add")

    # Translate all aliases:
    translated = []
    for module in to_add:
        if not module_exists(module):
            user_error(f"Module '{module}' does not exist")
        if (not module in get_index() and os.path.exists(module)):
            translated.append(local_module_name(module))
            continue
        data = get_index()[module]
        if "alias" in data:
            print(f'{module} is an alias for {data["alias"]}')
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
    missing = [m for m in to_add if not m.startswith("./") and m not in get_index()]
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
        assert module_exists(module)
        data = get_build_step(module)
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
        assert module_exists(module)
        data = get_build_step(module)
        new_module = {"name": module, **data, "added_by": added_by[module]}
        definition["build"].append(new_module)
        if user_requested:
            print(f"Added module: {module}")
        else:
            print(f"Added module: {module} (Dependency of {added_by[module]})")
        added.append(module)

    put_definition(definition)


def init_build_folder():
    rm("out", missing_ok=True)
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


def longest_module_name() -> int:
    return max((len(m["name"]) for m in get_definition()["build"]))


def get_download_path(module) -> str:
    downloads = os.path.join(cfbs_dir(), "downloads")
    github = os.path.join(downloads, "github.com")
    commit = module["commit"]
    url = module["repo"]
    url = strip_right(url, ".git")
    assert url.startswith("https://github.com/")
    user_repo = strip_left(url, "https://github.com/")
    user, repo = user_repo.split("/")
    repo_dir = os.path.join(github, user, repo)
    mkdir(repo_dir)
    return os.path.join(repo_dir, commit)


def download_dependencies(prefer_offline=False, redownload=False):
    print("\nModules:")
    counter = 1
    definition = get_definition()
    max_length = longest_module_name()
    for module in definition["build"]:
        name = module["name"]
        if name.startswith("./"):
            local_module_copy(module, counter, max_length)
            counter += 1
            continue
        commit = module["commit"]
        url = strip_right(module["repo"], ".git")
        commit_dir = get_download_path(module)
        if redownload:
            rm(commit_dir, missing_ok=True)
        if not os.path.exists(commit_dir):
            sh(f"git clone {url} {commit_dir}")
            sh(f"(cd {commit_dir} && git checkout {commit})")
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
