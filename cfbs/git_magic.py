"""Git related code that is more specific to CFBS than git.py

Here it's okay to depend on other parts of the CFBS codebase,
do prompts, etc.
"""

from cfbs.prompts import YES_NO_CHOICES, prompt_user
from cfbs.cfbs_config import CFBSConfig, CFBSReturnWithoutCommit
from cfbs.git import git_commit, git_discard_changes_in_file, CFBSGitError
from functools import partial


def git_commit_maybe_prompt(commit_msg, non_interactive, scope="all"):
    edit_commit_msg = False

    if not non_interactive:
        ans = prompt_user(
            "The default commit message is '{}' - edit it?".format(commit_msg),
            choices=YES_NO_CHOICES,
            default="no",
        )
        edit_commit_msg = ans.lower() in ("yes", "y")
    git_commit(commit_msg, edit_commit_msg, scope)


def with_git_commit(
    successful_returns,
    files_to_commit,
    commit_msg,
    positional_args_lambdas=None,
    failed_return=False,
):
    def decorator(fn):
        def decorated_fn(*args, **kwargs):
            try:
                ret = fn(*args, **kwargs)
            except CFBSReturnWithoutCommit as e:
                return e.retval

            config = CFBSConfig.get_instance()
            if not config["git"]:
                return ret

            if ret in successful_returns:
                if positional_args_lambdas:
                    positional_args = (
                        l_fn(args, kwargs) for l_fn in positional_args_lambdas
                    )
                    msg = commit_msg % tuple(positional_args)
                else:
                    msg = commit_msg

                try:
                    git_commit_maybe_prompt(
                        msg, config.non_interactive, files_to_commit
                    )
                except CFBSGitError as e:
                    print(str(e))
                    try:
                        for file_name in files_to_commit:
                            git_discard_changes_in_file(file_name)
                    except CFBSGitError as e:
                        print(str(e))
                    else:
                        print("Failed to commit changes, discarding them...")
                        return failed_return
            return ret

        return decorated_fn

    return decorator


commit_after_command = partial(with_git_commit, (0,), ("cfbs.json",), failed_return=1)
