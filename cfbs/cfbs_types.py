from typing import List, NamedTuple, Optional

CFBSCommandExitCode = int


# The usual, not `class`-based, method of defining a `typing.NamedTuple` type does not support default values,
# and it seems that the `class`-based method's constructor does not work with the Python 3.5 PEP 484[1] comment type hints.
# Thus, for compatibility with Python 3.5, a more verbose definition of `CFBSCommandGitResult` is used.
# This commit can be reverted, and type hints returned to the PEP 526 style type hints[2], once the supported Python version becomes 3.6+.
# References:
# [1]: https://peps.python.org/pep-0484/#type-comments
# [2]: https://peps.python.org/pep-0526/#class-and-instance-variable-annotations
_CFBSCommandGitResult = NamedTuple(
    "_CFBSCommandGitResult",
    [
        ("return_code", int),
        ("do_commit", bool),
        ("commit_message", Optional[str]),
        ("commit_files", List[str]),
    ],
)


class CFBSCommandGitResult(_CFBSCommandGitResult):
    def __new__(
        cls,
        return_code: int,
        do_commit: bool = True,
        commit_message: Optional[str] = None,
        commit_files: Optional[List[str]] = None,
    ):
        if commit_files is None:
            commit_files = []
        return super(CFBSCommandGitResult, cls).__new__(
            cls, return_code, do_commit, commit_message, commit_files
        )
