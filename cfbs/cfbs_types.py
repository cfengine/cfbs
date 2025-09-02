from typing import List, NamedTuple, Optional

CFBSCommandExitCode = int


class CFBSCommandGitResult(NamedTuple):
    return_code: int
    do_commit: bool = True
    commit_message: Optional[str] = None
    commit_files: List[str] = []
