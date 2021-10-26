import os
import re
import pytest
from cfbs.commands import info_command, clear_definition


@pytest.mark.parametrize("chdir", ["sample"], indirect=True)
def test_noargs(capfd, chdir):
    clear_definition()
    info_command([])
    out, _ = capfd.readouterr()
    assert out == "\n"


@pytest.mark.parametrize("chdir", ["sample"], indirect=True)
def test_showinfo(capfd, chdir):
    clear_definition()
    assert os.path.exists("cfbs.json")
    info_command(
        "autorun masterfiles foo/main.cf bar/my.json bar/baz/main.cf nosuchfile".split(
            " "
        )
    )
    out, _ = capfd.readouterr()

    assert re.search(
        r"""Module: autorun
Version: \d+\.\d+\.\d+
Status: Added
By: https:\/\/github.com\/cfengine
Tags: wip, untested
Repo: https:\/\/github.com\/cfengine\/modules
Commit: [a-zA-Z0-9]+
Subdirectory: management\/autorun
Added By: ./foo/main.cf
Description: Enable autorun functionality
""",
        out,
        re.M,
    ), out

    assert re.search(
        r"""Module: masterfiles
Version: \d+\.\d+\.\d+
Status: Not Added
By: https:\/\/github.com\/cfengine
Tags: official, base, supported
Repo: https:\/\/github.com\/cfengine\/masterfiles
Commit: [a-zA-Z0-9]+
Description: Official CFEngine Masterfiles Policy Framework \(MPF\)
""",
        out,
        re.M,
    ), out

    assert (
        """Module: ./foo/main.cf
Status: Added
Tags: local
Dependencies: autorun
Added By: cfbs add
Description: Local policy file added using cfbs command line

Module: ./bar/my.json
Status: Added
Tags: local
Added By: cfbs add
Description: Local augments file added using cfbs command line

Module: ./bar/baz/main.cf
Status: Added
Tags: local
Dependencies: autorun
Added By: cfbs add
Description: Local policy file added using cfbs command line

Module 'nosuchfile' does not exist

"""
        in out
    )
