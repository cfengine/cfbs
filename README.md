# CFEngine Build System

This is a command line tool for combining multiple modules into 1 policy set to deploy on your infrastructure.
Modules can be custom promise types, JSON files which enable certain functionality, or reusable CFEngine policy.
The modules you use can be written by the CFEngine team, others in the community, your colleagues, or yourself.

## CFEngine Build Repositories

* [build-index](https://github.com/cfengine/build-index) - Index of modules
* [build-website](https://github.com/cfengine/build-website) - Website
* [cfbs](https://github.com/cfengine/cfbs) - Command line client
* [modules](https://github.com/cfengine/modules) - Official modules provided by the CFEngine team
* [module-template](https://github.com/cfengine/build-example) - Template for creating new modules

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

### Dependencies

`cfbs` is implemented in Python and has a few dependencies:

* Python 3.5 or newer
* `requests` python library
* `git` CLI installed and in PATH

## Usage

Here are the basic commands to set up a repo, add dependencies, build and deploy.

### Initialize a new repo

```
cfbs init
```

### List or search available packages

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

### Deploy your policy set to a remote hub

```
cf-remote deploy -H hub out/masterfiles.tgz
```

(Replace `hub` with the cf-remote group name or IP of your hub).

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

## Build Steps

The standard commands for adding content such as `cfbs add` will handle most common needs.
If you are creating a new module or needing more control you can edit `cfbs.json` and the `steps` entry.

An example of the result of `cfbs add ./policy.cf`:

```
    {
      "name": "./policy.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "dependencies": ["autorun"],
      "steps": ["copy ./policy.cf services/autorun/policy.cf"],
      "added_by": "cfbs add"
    }
```

In most cases the steps are designed to copy something locally to the resulting `out/masterfiles` output directory created when running `cfbs build`.

The `source` parameters in each step are relative either to the local cfbs project directory or the `subdirectory` specified in the module definition.

Here is an example from the `client-initiated-reporting` module

```
    {
      "name": "client-initiated-reporting",
      "description": "Enable client initiated reporting and disable pull collection",
      "tags": ["experimental", "reporting"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/cfengine",
      "version": "0.1.1",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "subdirectory": "reporting/client-initiated-reporting",
      "steps": ["json def.json def.json"],
      "added_by": "cfbs add"
    }
```

The source `def.json` to be merged above will be located at `reporting/client-initiated-reporting/def.json`.

During `cfbs build` either the local contents or the repository contents are copied to an auto-generated numeric directory of the form: `out/steps/<step#>_<module_name>_<commit_sha>`.
This is the working directory where commands are run and where `source` paths should be specified relative to.

```
out/steps/001_masterfiles_5c7dc5b43088e259a94de4e5a9f17c0ce9781a0f/
```

The `destination` parameter below should all be relative paths to `out/masterfiles`.



### Available steps are:

#### `copy <source> <destination>`
- Copy a single file or a directory recursively.

#### `run <command>`
- Run a command in the module's `out/steps` directory as mentioned above.

#### `delete <paths ...>`
- Delete multiple files or paths recursively.

#### `json <source> <destination>`
- Merge the source json file into the destination json file.

#### `append <source> <destination>`
- Append the source file to the end of destination file.

#### `directory <source> <destination>`
- Copy any .cf policy files recursively and add their paths to `def.json`'s `inputs`.
- Enable `services_autorun_bundles` class in `def.json`.
- Merge any `def.json` recursively into `out/masterfiles/def.json`.
- Copy any other files with their existing directory structure to destination.
