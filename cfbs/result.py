from collections import namedtuple

Result = namedtuple(
    "Result", ("return_code", "do_commit", "commit_message", "commit_files")
)
