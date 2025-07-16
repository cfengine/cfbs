# CFEngine Build System

This is a command line tool for combining multiple modules into 1 policy set to deploy on your infrastructure.
Modules can be custom promise types, JSON files which enable certain functionality, or reusable CFEngine policy.
The modules you use can be written by the CFEngine team, others in the community, your colleagues, or yourself.

## CFEngine Build Repositories

- [build-index](https://github.com/cfengine/build-index) - Index of modules
- [build-website](https://github.com/cfengine/build-website) - Website
- [cfbs](https://github.com/cfengine/cfbs) - Command line client
- [modules](https://github.com/cfengine/modules) - Official modules provided by the CFEngine team
- [module-template](https://github.com/cfengine/build-example) - Template for creating new modules

## Installation

Requires Python 3.5 or newer and `pip`.

```
pip install cfbs
```

(or `sudo pip3 install cfbs` or whatever works with Python 3 on your system).

It is also **recommended** to install `cf-remote` if you want to deploy the policy set to remote hub(s):

```
pip install cf-remote
```

### Install from sources

If you want to install an unreleased version of `cfbs`, such as the master branch, just run this inside [the git repo](https://github.com/cfengine/cfbs):

```
pip install .
```

### Dependencies

`cfbs` is implemented in Python and has a few dependencies:

- Python 3.5 or newer
- `git` CLI installed and in PATH
- `rsync`
- `autoconf` for configuring masterfiles module (typical usage but not required)

## Usage

Here are the basic commands to set up a repo, add dependencies, build and deploy.

### Initialize a new repo

```
cfbs init
```

### List or search available modules

```
cfbs search
```

Or more specific:

```
cfbs search masterfiles
```

(`masterfiles` is the name of a module and can be replaced with whatever you are looking for).

### Add a module

```
cfbs add masterfiles
```

### Build your policy set

```
cfbs build
```

### Install your policy set locally

```
cfbs install /var/cfengine/masterfiles
```

### Remove added modules

```
cfbs remove promise-type-git
```

### Remove unused dependencies

```
cfbs clean
```

### Add module input

```
cfbs input delete-files
```

This command prompts the user for module input to configure what the module should do.

Only works for modules which accept input, indicated by the `"input"` key.
This `input` key contains the specification for what input the module accepts, if any.

User's responses are stored in `<module-name>/input.json`.
For completeness, the input specification is also stored with the responses.
Here is an example of a `input.json` file with responses:

```json
[
  {
    "type": "list",
    "variable": "files",
    "bundle": "delete_files",
    "label": "Files",
    "subtype": [
      {
        "key": "path",
        "type": "string",
        "label": "Path",
        "question": "Enter path to file"
      },
      {
        "key": "why",
        "type": "string",
        "label": "Why",
        "question": "Why should this file be deleted?",
        "default": "It's malicious."
      }
    ],
    "while": "Do you want the module to delete more files?",
    "response": [
      { "path": "/tmp/virus", "why": "It's malicious." },
      {
        "path": "/home/alice/.ssh/authorized_keys",
        "why": "She left the company."
      }
    ]
  }
]
```

The `input.json` file is converted and merged into the main `def.json` during the build, using the `input` build step.

### Deploy your policy set to a remote hub

```
cf-remote deploy
```

This will default to the hub(s) you have spawned or saved in `cf-remote`.
To specify a hub manually:

```
cf-remote deploy --hub hub
```

where `hub` is a `cf-remote` group name, or:

```
cf-remote deploy --hub root@1.2.3.4
```

## Examples

There is an example project available here:

https://github.com/cfengine/cfbs-example

### Creating a project from scratch

These commands and output shows how you can use `cfbs` to create a new project from scratch:

```
$ mkdir demo-project
$ cd demo-project
$ cfbs --version
cfbs 0.4.4
$ cfbs init
Initialized - edit name and description cfbs.json
To add your first module, type: cfbs add masterfiles
$ cfbs add masterfiles
Added module: masterfiles
$ cfbs add git
git is an alias for promise-type-git
Added module: library-for-promise-types-in-python (Dependency of promise-type-git)
Added module: promise-type-git
$ cfbs build
Modules:
001 masterfiles                         @ 28d9b933db5fc8e1dea4338669cc4fd6677646f1 (Downloaded)
002 library-for-promise-types-in-python @ 1438ad8515267b3dd4b862cfcd63c1b9ccfb42e1 (Downloaded)
003 promise-type-git                    @ 1438ad8515267b3dd4b862cfcd63c1b9ccfb42e1 (Downloaded)
Steps:
001 masterfiles                         : run './autogen.sh'
001 masterfiles                         : delete './autogen.sh'
001 masterfiles                         : copy './' 'masterfiles/'
002 library-for-promise-types-in-python : copy 'cfengine.py' 'masterfiles/modules/promise_types/'
003 promise-type-git                    : copy 'git.py' 'masterfiles/modules/promise_types/'
003 promise-type-git                    : append 'enable.cf' 'masterfiles/services/init.cf'
Generating tarball...
Build complete, ready to deploy 🐿
 -> Directory: out/masterfiles
 -> Tarball:   out/masterfiles.tgz
To install on this machine: cfbs install
To deploy on remote hub(s): cf-remote deploy
$ head out/masterfiles/modules/promise_types/git.py
import os
import subprocess
from typing import Dict, Optional
from cfengine import PromiseModule, ValidationError, Result
from pydantic import (
    BaseModel,
    ValidationError as PydanticValidationError,
    validator,
$
```

## Reproducible builds

When you run `cfbs build` locally, and when your hub runs it after pulling the latest changes from git, the resulting policy sets will be identical.
(This does not extend to providing reproducibility after running arbitrary combinations of `cfbs init`, `cfbs add` commands, etc.).
This gives you some assurance, that what you've tested actually matches what is running on your hub(s) and thus the rest of your machines.
Currently, two `masterfiles.tgz` gzipped tarballs of policy sets are not bit-by-bit identical due to file metadata (modification time, etc.).
The file contents themselves are (should be) identical.
There is also no testing of reproducible builds or checking to enforce that what you built locally and what your hub built are the same.
We'd like to improve all of this.
To see the progress in this area, take a look at this JIRA ticket:

https://northerntech.atlassian.net/browse/CFE-4102

## Available commands

We expect policy writers and module authors to use the `cfbs` tooling from the command line, when working on projects, in combination with their editor of choice, much in a similar way to `git`, `cargo`, or `npm`.
When humans are running the tool in a shell, manually typing in commands, we want it to be intuitive, and have helpful prompts to make it easy to use.
However, we also expect some of the commands to be run inside scripts, and as part of the code and automation which deploys your policy to your hosts.
In these situations, prompts are undesireable, and stability is very important (you don't want the deployment to start failing).
For these reasons, we've outlined 2 categories of commands below.

**Note:** The 2 categories below are not strict rules.
They are here to communicate our development philosophy and set expectations in terms of what changes to expect (and how frequent).
We run both user-oriented and automation-oriented commands in automated tests as well as inside Build in Mission Portal.

### User-oriented / Interactive commands

These commands are centered around a user making changes to a project (manually from the shell / command line), not a computer building/deploying it:

- `cfbs add`: Add a module to the project (local files/folders, prepended with `./` are also considered modules).
- `cfbs analyse`: Same as `cfbs analyze`.
- `cfbs analyze`: Analyze the policy set specified by the given path.
- `cfbs clean`: Remove modules which were added as dependencies, but are no longer needed.
- `cfbs convert`: Initialize a new CFEngine Build project based on an existing policy set.
- `cfbs help`: Print the help menu.
- `cfbs info`: Print information about a module.
- `cfbs init`: Initialize a new CFEngine Build project.
- `cfbs input`: Enter input for a module which accepts input.
- `cfbs remove`: Remove a module from the project.
- `cfbs search`: Search for modules in the index.
- `cfbs show`: Same as `cfbs info`.
- `cfbs status`: Show the status of the current project, including name, description, and modules.
- `cfbs update`: Update modules to newer versions.

They try to help the user with interactive prompts / menus.
You can always add the `--non-interactive` to skip all interactive prompts (equivalent to pressing enter to use defaults).
In order to improve the user experience we change the behavior of these, especially when it comes to how prompts work, how they are presented to the user, what options are available, etc.

**Note:** Some of the commands above are not interactive yet, but they might be in the future.

### Automation-oriented / Non-interactive commands

These commands are intended to be run as part of build systems / deployment pipelines (in addition to being run by human users):

- `cfbs download`: Download all modules / dependencies for the project.
  Modules are skipped if already downloaded.
- `cfbs build`: Build the project, combining all the modules into 1 output policy set.
  Download modules if necessary.
  Should work offline if things are already downloaded (by `cfbs download`).
- `cfbs get-input`: Get input data for a module.
  Includes both the specification for what the module accepts as well as the user's responses.
  Can be used on modules not yet added to project to get just the specification.
  Empty list `[]` is returned if the module was found, but it does not accept any input.
- `cfbs install`: Run this on a hub as root to install the policy set (copy the files from `out/masterfiles` to `/var/cfengine/masterfiles`).
- `cfbs pretty`: Run on a JSON file to pretty-format it. (May be expanded to other formats in the future).
- `cfbs set-input`: Set input data for a module.
  Non-interactive version of `cfbs input`, takes the input as a JSON, validates it and stores it.
  `cfbs set-input` and `cfbs get-input` can be thought of as ways to save and load the input file.
  Similar to `cfbs get-input` the JSON contains both the specification (what the module accepts and how it's presented to the user) as well as the user's responses (if present).
  Expected usage is to run `cfbs get-input` to get the JSON, and then fill out the response part and run `cfbs set-input`.
- `cfbs generate-release-information`: An internal command used to generate JSON release information files from the [official CFEngine masterfiles](https://github.com/cfengine/masterfiles/).
- `cfbs validate`: Used to validate the [index JSON file](https://github.com/cfengine/build-index/blob/master/cfbs.json).
  May be expanded to validate other files and formats in the future.
  **Note:** If you use `cfbs validate` as part of your automation, scripts, and build systems, be aware that we might add more strict validation rules in the future, so be prepared to sometimes have it fail after upgrading the version of cfbs.

They don't have interactive prompts, you can expect fewer changes to them, and backwards compatibility is much more important than with the interactive commands above.

## Environment variables

`cfbs` respects the following environment variables:

- `CFBS_GLOBAL_DIR`: Directory where `cfbs` stores global information, such as its cache of downloaded modules.
  - **Default:** `~/.cfengine/cfbs/`.
  - **Usage:** `CFBS_GLOBAL_DIR=/tmp/cfbs cfbs build`.
  - **Note:** `cfbs` still uses the current working directory for finding and building a project (`./cfbs.json`, `./out/`, etc.).

Additionally, `cfbs` runs some commands in a shell, utilizing a few programs / shell built-ins, which may be affected by environment variables:

- `git`
- `tar`
- `unzip`
- `rsync`
- `mv`
- `cat`
- `cd`
- `rm`
- Commands / scripts specified in the `run` build step.

## The cfbs.json format

More advanced users and module authors may need to understand, write, or edit `cfbs.json` files.
The format of those files and how `cfbs` uses them is explained in detail in [JSON.md](./JSON.md).
