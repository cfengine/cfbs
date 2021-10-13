import os
import re
from cfbs.commands import info_command

os.chdir(os.path.join(os.path.dirname(__file__),"sample"))

def test_noargs(capfd):
    info_command([])
    out, err = capfd.readouterr()
    assert out == "\n"

def test_showinfo(capfd):
    info_command("autorun masterfiles foo/main.cf bar/my.json bar/baz/main.cf nosuchfile".split(" "))
    out, err = capfd.readouterr()

    assert re.search(r"""Module: autorun
Version: \d+\.\d+\.\d+
Status: Added
By: https:\/\/github.com\/cfengine
Tags: wip, untested
Repo: https:\/\/github.com\/cfengine\/modules
Commit: [a-zA-Z0-9]+
Description: Enable autorun functionality
""", out, re.M)


    assert re.search(r"""Module: masterfiles
Version: \d+\.\d+\.\d+
Status: Not Added
By: https:\/\/github.com\/cfengine
Tags: official, base
Repo: https:\/\/github.com\/cfengine\/masterfiles
Commit: [a-zA-Z0-9]+
Description: Official CFEngine Masterfiles Policy Framework \(MPF\)
""", out, re.M)

    assert """Module: ./foo/main.cf
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

""" in out

def __main__():
  test_showinfo()
