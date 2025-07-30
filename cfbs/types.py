from typing import List, NamedTuple, Union


class CFBSCommandGitResult(NamedTuple):
    return_code: int
    do_commit: bool = True
    commit_message: Union[str, None] = None
    commit_files: List[str] = []
