#!/usr/bin/env python3
import os
import logging as log

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
    read_file,
    mkdir,
    touch,
    rm,
    cp,
    sh,
)


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
    write_json(cfbs_filename(), data)
    sh(f"prettier --write '{cfbs_filename()}'")


index = None


def index_url() -> str:
    return "https://raw.githubusercontent.com/olehermanse/cfbs-index/master/index.json"


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


def add_command(to_add: list) -> int:
    if not to_add:
        user_error("Must specify at least one module to add")

    missing = [m for m in to_add if m not in get_index()]
    if missing:
        user_error(f"Modules could not be found: {', '.join(missing)}")

    definition = get_definition()

    added = [m["name"] for m in definition["build"]]

    for module in to_add:
        if module in added:
            print(f"Skipping already added module - {module}")
            continue
        new_module = {"name": module, **get_index()[module]}
        definition["build"].append(new_module)
        added.append(module)

    for module in definition["build"]:
        if module["name"] in to_add:
            module["user_requested"] = True
    put_definition(definition)


def init_build_folder():
    rm("out")
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


def longest_module_name() -> int:
    return max((len(m["name"]) for m in get_definition()["build"]))


def download_dependencies(prefer_offline=False, redownload=False):
    print("\nModules:")
    counter = 1
    downloads = os.path.join(cfbs_dir(), "downloads")
    github = os.path.join(downloads, "github.com")
    definition = get_definition()
    max_length = longest_module_name()
    for module in definition["build"]:
        name = module["name"]
        commit = module["commit"]
        url = module["repo"]
        url = strip_right(url, ".git")
        assert url.startswith("https://github.com/")
        user_repo = strip_left(url, "https://github.com/")
        user, repo = user_repo.split("/")
        repo_dir = os.path.join(github, user, repo)
        mkdir(repo_dir)
        commit_dir = os.path.join(repo_dir, commit)
        if redownload and os.path.exists(commit_dir):
            rm(commit_dir)
        if not os.path.exists(commit_dir):
            sh(f"git clone {url} {commit_dir}")
            sh(f"(cd {commit_dir} && git checkout {commit})")
        target = f"out/steps/{counter:03d}_{module['name']}_{commit}"
        module["_directory"] = target
        module["_counter"] = counter
        subdirectory = module.get("subdirectory", None)
        if not subdirectory:
            cp(commit_dir, target)
        else:
            cp(os.path.join(commit_dir, subdirectory), target)
        print(f"{counter:03d} {pad_right(name, max_length)} @ {commit}")
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
            rm(file)
    elif operation == "json":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print(f"{prefix} json '{src}' 'masterfiles/{dst}'")
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        extras, original = read_json(src), read_json(dst)
        assert extras
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
        sh("prettier --write out/masterfiles/def.json")
    print("Generating tarball...")
    sh("( cd out/ && tar -czf masterfiles.tgz masterfiles )")
    print("\nBuild complete, ready to deploy 🐿")
    print(" -> Directory: out/masterfiles")
    print(" -> Tarball:   out/masterfiles.tgz")
    print("")
    print("To install on this machine: cfbs install")
    print("To deploy on remote hub(s): cf-remote deploy")
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
    rm(destination)
    cp("out/masterfiles", destination)
    return 0
