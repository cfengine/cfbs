"""Git related code that is more specific to CFBS than git.py

Here it's okay to depend on other parts of the CFBS codebase,
do prompts, etc.
"""

from cfbs.prompts import YES_NO_CHOICES, prompt_user
from cfbs.cfbs_config import CFBSConfig, CFBSReturnWithoutCommit
from cfbs.git import git_commit, git_discard_changes_in_file, CFBSGitError, is_git_repo
from cfbs.args import get_args
from cfbs.result import Result
import logging as log
from functools import partial


first_commit = True


def git_commit_maybe_prompt(commit_msg, non_interactive, scope="all"):
    edit_commit_msg = False
    args = get_args()

    # Override message if --git-commit-message option is used
    if args.git_commit_message:
        global first_commit
        if first_commit:
            commit_msg = args.git_commit_message
            non_interactive = True
            first_commit = False
        else:
            log.warning(
                "Commit message specified, but command produced multiple commits, using default commit message"
            )

    if not non_interactive:
        prompt = "The default commit message is '{}' - edit it?".format(commit_msg)
        if "\n" in commit_msg:
            prompt = "The default commit message is:\n\n"
            for line in commit_msg.split("\n"):
                prompt += "\n" if line == "" else "\t" + line + "\n"
            prompt += "\nEdit it?"

        ans = prompt_user(
            non_interactive,
            prompt,
            choices=YES_NO_CHOICES,
            default="no",
        )
        edit_commit_msg = ans.lower() in ("yes", "y")

    git_commit(
        commit_msg,
        edit_commit_msg,
        args.git_user_name,
        args.git_user_email,
        scope,
    )


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
                result = fn(*args, **kwargs)
            except CFBSReturnWithoutCommit as e:
                # Legacy; do not use. Use the Result namedtuple instead.
                return e.retval
            ret, should_commit, msg, files = (
                result if isinstance(result, Result) else (result, True, None, [])
            )
            files += files_to_commit

            # Message from the Result namedtuple overrides message from decorator
            if not msg:
                if positional_args_lambdas:
                    positional_args = (
                        l_fn(args, kwargs) for l_fn in positional_args_lambdas
                    )
                    msg = commit_msg % tuple(positional_args)
                else:
                    msg = commit_msg

            if not should_commit:
                return ret

            config = CFBSConfig.get_instance()
            do_git = get_args().git
            if do_git == "yes":
                if not is_git_repo():
                    log.error(
                        "Used '--git=yes' option on what appears to not be a git repository"
                    )
                    return ret
            elif do_git == "no":
                return ret
            else:
                assert do_git is None
                if not config.get("git", False):
                    return ret

            if ret not in successful_returns:
                return ret

            try:
                git_commit_maybe_prompt(msg, config.non_interactive, files)
            except CFBSGitError as e:
                print(str(e))
                try:
                    for file_name in files:
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
