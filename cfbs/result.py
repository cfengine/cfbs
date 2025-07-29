from typing import List, NamedTuple, Union

Result = NamedTuple(
    "Result",
    (
        ("return_code", int),
        ("do_commit", bool),
        ("commit_message", Union[str, None]),
        ("commit_files", List[str]),
    ),
)
