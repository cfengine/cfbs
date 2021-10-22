import json
import os
import pytest
from cfbs.commands import (
    build_command,
    init_command,
    add_command,
)
from cfbs.utils import read_json


@pytest.mark.parametrize("chdir", ["add_folder_sample"], indirect=True)
def test_add_folders_and_build(chdir):
    os.system("rm -rf out")
    os.system("rm -f cfbs.json")
    init_command()
    add_command(["masterfiles"])
    add_command(["./foo/"])
    add_command(["./bar/"])
    add_command(["./baz/"])
    build_command()

    expected = json.loads(
        """{
  "classes": { "services_autorun_bundles": ["any"] },
  "vars": { "foo_thing": "awesome", "bazbizthing": "superlative" },
  "inputs": ["services/cfbs/foo/foo.cf", "services/cfbs/baz/bazbiz.cf"]
}"""
    )
    actual = read_json("out/masterfiles/def.json")
    assert actual == expected

    actual = []
    for root, dirs, files in os.walk("out/masterfiles/services/cfbs"):
        for dir in dirs:
            actual.append(os.path.join(root, dir))
        for file in files:
            actual.append(os.path.join(root, file))
    # sort these, different orders on different systems
    actual = sorted(actual)
    expected = [
        "out/masterfiles/services/cfbs/bar",
        "out/masterfiles/services/cfbs/bar/bar.json",
        "out/masterfiles/services/cfbs/baz",
        "out/masterfiles/services/cfbs/baz/bazbiz.cf",
        "out/masterfiles/services/cfbs/baz/bazbiz.json",
        "out/masterfiles/services/cfbs/foo",
        "out/masterfiles/services/cfbs/foo/foo.cf",
        "out/masterfiles/services/cfbs/foo/oddfile.txt",
    ]
    assert actual == expected
