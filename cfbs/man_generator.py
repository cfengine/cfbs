import os
from utils import CFBSUserError
from args import get_arg_parser

try:
    from build_manpages.manpage import Manpage  # type: ignore
except ImportError:
    raise CFBSUserError(
        "Missing dependency, install from PyPI: 'pip install argparse-manpage setuptools'"
    )


def generate_man_page():
    manpage = Manpage(get_arg_parser(whitespace_for_manual=True))
    manpage.manual = "CFEngine Build System manual"
    manpage.description = (
        "combines multiple modules into 1 policy set to deploy on your infrastructure. "
        + "Modules can be custom promise types, JSON files which enable certain functionality, or reusable CFEngine policy. "
        + "The modules you use can be written by the CFEngine team, others in the community, your colleagues, or yourself."
    )
    body = (
        str(manpage)
        + """
.br
Binary packages may be downloaded from https://cfengine.com/download/.
.br
The source code is available at https://github.com/cfengine/
.SH BUGS
Please see the public bug-tracker at https://northerntech.atlassian.net/projects/CFE/.
.br
GitHub pull-requests may be submitted to https://github.com/cfengine/cfbs.
.SH "SEE ALSO"
.BR cf-promises (8),
.BR cf-agent (8),
.BR cf-serverd (8),
.BR cf-execd (8),
.BR cf-monitord (8),
.BR cf-runagent (8),
.BR cf-key (8)
.SH AUTHOR
    Northern.tech AS
        """
    )
    with open(os.path.dirname(__file__) + "/cfbs.1", "w", encoding="utf-8") as man_file:
        man_file.write(body)
    return body


generate_man_page()
