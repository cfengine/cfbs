"""Business logic related to downloading, copying, extracting files

The functions here use git clone, rsync, tar, etc. to make the necessary
file system changes for cfbs add / cfbs download / cfbs build to work.

The functions here are quite "contained", they don't rely on the
global config (read and writen to cfbs.json), just their parameters
and what is on the file system (in ~/.cfengine and ./out).
"""

import os
import re
import shutil

from cfbs.utils import (
    cfbs_dir,
    cp,
    fetch_url,
    FetchError,
    is_a_commit_hash,
    mkdir,
    pad_right,
    rm,
    sh,
    strip_right,
    user_error,
)

_SUPPORTED_TAR_TYPES = (".tar.gz", ".tgz")
SUPPORTED_ARCHIVES = (".zip",) + _SUPPORTED_TAR_TYPES


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


def get_download_path(module) -> str:
    downloads = os.path.join(cfbs_dir(), "downloads")

    commit = module["commit"]
    if not is_a_commit_hash(commit):
        user_error("'%s' is not a commit reference" % commit)

    url = module.get("url") or module["repo"]
    if url.endswith(SUPPORTED_ARCHIVES):
        url = os.path.dirname(url)
    else:
        url = strip_right(url, ".git")
    repo = url[url.index("://") + 3 :]
    repo_dir = os.path.join(downloads, repo)
    mkdir(repo_dir)
    return os.path.join(repo_dir, commit)


def _prettify_name(name):
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
    if not name.startswith("./"):
        user_error("module %s must start with ./" % name)
    if not os.path.isfile(name) and not os.path.isdir(name):
        user_error("module %s does not exist" % name)
    pretty_name = _prettify_name(name)
    target = "out/steps/%03d_%s_local/" % (counter, pretty_name)
    module["_directory"] = target
    module["_counter"] = counter
    if name.endswith(("/", "/.")):
        # If this is a local folder, the target should be a copy of the folder
        # (Don't create an extra unnecessary subfolder)
        cp(name, target)
    else:
        # If this is not a folder it is a file
        # create a copy of that file in the target folder
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


def _clone_and_checkout(url, path, commit):
    # NOTE: If any of these shell (git) commands fail, we will exit
    if not os.path.exists(os.path.join(path, ".git")):
        sh("git clone --no-checkout %s %s" % (url, path))
    sh("git checkout " + commit, directory=path)


def clone_url_repo(repo_url):
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
        _clone_and_checkout(repo_url, commit_path, commit)
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


def fetch_archive(url, checksum=None, directory=None, with_index=True):
    assert url.endswith(SUPPORTED_ARCHIVES)

    url_path = url[url.index("://") + 3 :]
    archive_dirname = os.path.dirname(url_path)
    archive_filename = os.path.basename(url_path)

    for ext in SUPPORTED_ARCHIVES:
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
        if shutil.which("tar"):
            sh("cd %s; tar -xf %s" % (content_dir, archive_path))
        else:
            user_error("Working with .tar archives requires the 'tar' utility")
    elif archive_type == (".zip"):
        if shutil.which("unzip"):
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
        shutil.rmtree(content_root_items[0])

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
