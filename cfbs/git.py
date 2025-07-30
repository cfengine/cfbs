"""Module for running creating / interacting with a git repository

Uses the subprocess module to run the git command line tool.

Should be fairly reusable, not depending on other parts
of the CFBS codebase.

See git_magic.py for more git related code.
"""

import os
import itertools
import tempfile
from subprocess import check_call, check_output, run, PIPE, DEVNULL, CalledProcessError
from typing import Iterable, Union

from cfbs.prompts import prompt_user
from cfbs.utils import CFBSExitError, are_paths_equal


class CFBSGitError(Exception):
    pass


def git_exists():
    try:
        check_call(["git", "--version"], stdout=DEVNULL)
        return True
    except FileNotFoundError:
        return False


def ls_remote(remote, branch):
    """Returns the hash of the commit that the current HEAD of a given branch
    on a given remote is pointing to.

    :param remote: the remote to list
    :param branch: the branch on the remote
    """
    try:
        return (
            check_output(["git", "ls-remote", remote, branch])
            .decode()
            .strip()
            .split()[0]
        )
    except:
        return None


def is_git_repo(path=None):
    """Is the given path a Git repository?)

    :param:`path` defaults to CWD (if `None`)

    """

    if path is None:
        path = os.getcwd()
    return os.path.isdir(os.path.join(path, ".git"))


def git_get_config(key):
    try:
        return check_output(["git", "config", key]).decode().strip()
    except CalledProcessError:
        return None


def git_set_config(key, value):
    try:
        check_call(["git", "config", key, value])
    except CalledProcessError:
        return False
    else:
        return True


def git_init(user_name=None, user_email=None, description=None, initial_branch="main"):
    """Initialize git repo in CWD

    Also initializes `user.name` and `user.email` Git config for the repo if
    given.

    ..note::
      Either both :param:`user_name` and :param:`user_email` must be given (not
      `None`) or none can be given (both must be `None`).

    """
    if (user_name is None and user_email is not None) or (
        user_name is not None and user_email is None
    ):
        raise AttributeError(
            "Both user_name and user_email must be given or none can be given"
        )

    if is_git_repo():
        raise CFBSGitError("Already an initialized git repository")

    try:
        # Suppress noisy hint output on stderr:
        check_call(["git", "init", "-b", initial_branch], stderr=DEVNULL)
    except CalledProcessError as cpe:
        raise CFBSGitError("Failed to initialize git repository") from cpe

    if user_name is not None:
        assert user_email is not None
        try:
            check_call(["git", "config", "user.name", user_name])
            check_call(["git", "config", "user.email", user_email])
        except CalledProcessError as cpe:
            raise CFBSGitError("Failed to set user name and email") from cpe

    if description is not None:
        with open(os.path.join(".git", "description"), "w") as f:
            f.write(description + "\n")


def git_configure_and_initialize(
    user_name=None, user_email=None, non_interactive=False, description=None
):
    if not git_exists():
        raise CFBSExitError("Command 'git' was not found")

    if not user_name:
        user_name = git_get_config("user.name")
        user_name = prompt_user(
            non_interactive,
            "Please enter user name to use for git commits",
            default=user_name or "cfbs",
        )

    if not user_email:
        user_email = git_get_config("user.email")
        node_name = os.uname().nodename
        user_email = prompt_user(
            non_interactive,
            "Please enter user email to use for git commits",
            default=user_email or ("cfbs@%s" % node_name),
        )

    if not is_git_repo():
        git_init(user_name, user_email, description)
    else:
        if not git_set_config("user.name", user_name) or not git_set_config(
            "user.email", user_email
        ):
            raise CFBSExitError("Failed to set Git user name and email")


def git_commit(
    commit_msg,
    edit_commit_msg=False,
    user_name=None,
    user_email=None,
    scope: Union[str, Iterable[str]] = "all",
):
    """Create a commit in the CWD Git repository

    :param commit_msg: commit message to use for the commit
    :param scope: files to include in the commit or `"all"` (`git commit -a`)
    :param edit_commit_msg: whether the user should be prompted to edit and save the commit message or not
    :param user_name: override git config user name
    :param user_email: override git config user email

    """

    print("Committing using git:\n")

    if not is_git_repo():
        raise CFBSGitError("Not a git repository")

    if scope == "all":
        try:
            check_call(["git", "add", "--all"])
        except CalledProcessError as cpe:
            raise CFBSGitError("Failed to add all to commit") from cpe
    else:
        for item in scope:
            try:
                check_call(["git", "add", item])
            except CalledProcessError as cpe:
                raise CFBSGitError("Failed to add %s to commit" % item) from cpe

    # Override git config user name and email if specified
    u_name = ["-c", "user.name=%s" % user_name] if user_name else []
    u_email = ["-c", "user.email=%s" % user_email] if user_email else []

    if edit_commit_msg:
        fd, name = tempfile.mkstemp(dir=".git", prefix="commit-msg")
        with os.fdopen(fd, "w") as f:
            f.write(commit_msg)

        # If the user doesn't edit the message, the commit fails. In such case
        # we need to make the commit the same way as in non-interactive mode.
        result = run(
            ["git"] + u_name + u_email + ["commit", "--template", name],
            check=False,
            stderr=PIPE,
        )
        os.unlink(name)
        if result.returncode == 0:
            print("")
            return
        elif "did not edit the message" not in result.stderr.decode():
            raise CFBSGitError("Failed to commit changes")

    # else
    try:
        run(
            ["git"] + u_name + u_email + ["commit", "-F-"],
            input=commit_msg.encode("utf-8"),
            check=True,
        )
        print("")
    except CalledProcessError as cpe:
        raise CFBSGitError("Failed to commit changes") from cpe


def git_discard_changes_in_file(file_name):
    try:
        check_call(["git", "checkout", "--", file_name])
    except CalledProcessError as cpe:
        raise CFBSGitError(
            "Failed to discard changes in file '%s'" % file_name
        ) from cpe


def git_check_tracked_changes(scope=["all"]):
    should_commit = False
    try:
        result = run(["git", "status", "-s", "-u"], check=True, stdout=PIPE)
        if "all" in scope:
            if len(result.stdout) > 0:
                should_commit = True
        else:
            lines = result.stdout.decode("utf-8").split("\n")
            changes = [line.strip().split(" ")[1] for line in lines if line]
            should_commit = any(
                # paths given in `git status` are of different form than the paths we use
                are_paths_equal(p[0], p[1])
                for p in itertools.product(changes, scope)
            )
        if not should_commit:
            print("No changes to commit")
        return should_commit
    except CalledProcessError as cpe:
        raise CFBSGitError(
            "Failed to run 'git status -s -u' to check for changes."
        ) from cpe
