# CFEngine Build JSON file format

The `cfbs` command line tool uses `cfbs.json` configuration files.
We call the folder / git repo which has a `cfbs.json` file (and optionally other files and folders) a _project_, and the end result after combining modules in a project into policy a _policy set_.
The _policy set_ is what you deploy to your CFEngine hub / policy server, in `/var/cfengine/masterfiles`.

See the [README](https://github.com/cfengine/cfbs/blob/master/README.md) for general documentation on the `cfbs` tool and its commands.
This file is specifically about the `cfbs.json` file format, it should serve as detailed and useful information for more advanced users who are making their own modules or contributing to CFEngine Build.

The type of a project is specified in a top-level `type` key in `cfbs.json`.
There are 3 types of projects:

* `policy-set`: For projects which build a policy set (which will be deployed to a hub).
  This is the default when running `cfbs init`, and what most users encounter when first using the tool and CFEngine.
  You then need to use the `build` key to specify which modules to use in `cfbs build`.
* `index`: For defining an index of all available modules for `cfbs add <module-name>`.
  The available modules must be in a dictionary in the `index` field.
  By default, [this index available in GitHub](https://github.com/cfengine/build-index/blob/master/cfbs.json) is used.
* `module`: For developing your own reusable modules to use in other projects.

When `cfbs` is using the default index and when we build the [build.cfengine.com](https://build.cfengine.com) website, we use a separate [`versions.json`](https://github.com/cfengine/build-index/blob/master/versions.json) file to keep track of all the versions of modules, their tarballs and checksums.
When contributors edit the index ([like this](https://github.com/cfengine/build-index/pull/465/files)), an automated PR is generated to make the appropriate edit to `versions.json` ([like this](https://github.com/cfengine/build-index/pull/466/files)), (after downloading and uploading the module), so users don't have to update `versions.json` manually.

Note that while the 3 types above add some requirements to which fields you must use, the file format and `cfbs` tool is quite flexible.
It is for example entirely possible, and encouraged, to use the `build` field and `cfbs build` command to build and test a policy set, while you are working on a module in a project with type `module`.

## The process of building modules from a project into a policy set

This section gives you an introduction to how `cfbs build` works, while the complete details of all keys, operations, etc. are explained further in sections below.

When you build a project with the `cfbs build` command, it loops through all modules in the project (`"build"` key), in order.
Within each module it runs the individual build steps, specified in the `"steps"` key.

As an example, you might set up a basic project like this:

```
$ mkdir my_project
$ cd my_project
$ cfbs init --non-interactive
Initialized empty Git repository in /Users/olehermanse/my_project/.git/
Committing using git:

[main (root-commit) a0e1365] Initialized a new CFEngine Build project
 1 file changed, 7 insertions(+)
 create mode 100644 cfbs.json

Initialized an empty project called 'Example project' in 'cfbs.json'
Added module: masterfiles
Committing using git:

[main cee639a] Added module 'masterfiles'
 1 file changed, 16 insertions(+), 1 deletion(-)

$ echo "
bundle agent my_bundle
{
  reports:
    "Hello, world";
}" > my_policy.cf
$ cfbs --non-interactive add ./my_policy.cf
Added module: ./my_policy.cf
Committing using git:

[main 9c1f7c8] Added module './my_policy.cf'
 2 files changed, 17 insertions(+)
 create mode 100644 my_policy.cf
$ cfbs pretty cfbs.json
```

This project has 2 modules, the default policy set (`masterfiles`) and one additional policy file we've written (`my_policy.cf`).

We can now take a look at the project we made (`cfbs.json`):

```json
{
  "name": "Example project",
  "description": "Example description",
  "type": "policy-set",
  "git": true,
  "build": [
    {
      "name": "masterfiles",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF).",
      "tags": ["supported", "base"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "version": "3.21.3",
      "commit": "ca637d4e6148432a90b7db598a4137956c0e0282",
      "added_by": "cfbs add",
      "steps": [
        "run EXPLICIT_VERSION=3.21.3 EXPLICIT_RELEASE=1 ./prepare.sh -y",
        "copy ./ ./"
      ]
    },
    {
      "name": "./my_policy.cf",
      "description": "Local policy file added using cfbs command line",
      "tags": ["local"],
      "added_by": "cfbs add",
      "steps": [
        "copy ./my_policy.cf services/cfbs/my_policy.cf",
        "policy_files services/cfbs/my_policy.cf",
        "bundles my_bundle"
      ]
    }
  ]
}
```

If we now run `cfbs build` it will loop through all the modules inside the `"build"` field, downloading them if necessary, and then running the _build steps_ inside sequentially, in a temporary _step folder_.

Taking a look at the second module (`./my_policy.cf`) we see 3 quite common build steps:

```
copy ./my_policy.cf services/cfbs/my_policy.cf
policy_files services/cfbs/my_policy.cf
bundles my_bundle
```

The 3 build steps above achieve 3 distinct things:
1. The policy file `policy.cf` is included in the policy set (`out/masterfiles`).
   It will be deployed to `/var/cfengine/masterfiles/services/cfbs/policy.cf` on the hub.
2. The path to `policy.cf` is added to `"inputs"` making cf-agent and other binaries aware of it and parse it.
3. The bundle `my_bundle` within `policy.cf` is added to the bundle sequence, making `cf-agent` find the correct bundle to run (commonly called the entry point of a policy).
   In the end, this causes `cf-agent` to actually evaluate the promises within the bundle and enforce your desired state (potentially making changes to the system).

After the build has been completed the policy set is available at `out/masterfiles` and `out/masterfiles.tgz`.
It is ready to be deployed to a remote hub with `cf-remote deploy` or locally (if running commands on a hub) with `sudo cfbs install`.

## The keys of a cfbs.json file

Below, there is a short explanation of each field you can find in a `cfbs.json` file.
Some of the examples further down in this file might help understand how each one is used.
All fields are required unless otherwise noted.
Please use `cfbs validate` while editing `cfbs.json` files manually - we won't attempt to list absolutely all the validation rules here.

### Top level keys

At the top level of a `cfbs.json` file, these fields are available:

* `name` (string): The human readable name of the project.
  An example could be: `Northern.tech production policy`
* `description` (string): Human readable description of what this project is for.
  For example: `This project builds the policy set we deploy to all production hosts.`
* `type` (string): What kind of project this is.
  One of:
  * `policy-set` (default): For projects which build a policy set (to deploy on a hub).
  * `module`: For developing a new module (or multiple) to publish on [build.cfengine.com](https://build.cfengine.com), or to use in your other projects.
  * `index`: For setting up an alternate list of modules (instead of relying on [the default one on GitHub](https://github.com/cfengine/build-index/blob/master/cfbs.json)).
* `index` (string or dictionary): URL, relative path, or inline dictionary.
  Used by `cfbs add` and `cfbs search`, to know where to look for modules.
  Required and must be dictionary if the `type` is `index`, optional otherwise.
  When it's a dictionary, the keys must be the unique module name which will be converted to the module's `name` field when added to the `build` array.
* `git` (true or false): Whether `cfbs` should make git commits after editing `./cfbs.json` and related files.
  Optional, defaults to false.
* `provides` (dictionary of modules): Which modules this repo provides when someone tries to add it by URL (`cfbs add https://github.com/some/repo`).
  Required for `cfbs add <URL>` to work, optional otherwise.
  Most commonly used for projects with type `module`.
  The keys must be the unique module name which will be converted to the module's `name` field when added to the `build` array.
* `build` (list of modules): The modules to combine into a policy set when running `cfbs build`.
  Required and must be non-empty for `policy-set` type and also for `cfbs build` command to work, optional otherwise.
  (Even if you are developing a `module`, it is useful to be able to put modules in `build`, to build and deploy a policy set to test).

### Module level keys

The modules inside `build`, `provides`, and `index` use these fields:

* `alias` (string): Used to rename a module in an index, or to provide a short name alternative.
  Gets translated to the value (real module name) by `cfbs add`.
  Only valid inside `index`.
  Optional, must be the only field if used.
* `name` (string): The unique name of the module (unique within project and within index).
  For `provides` and `index` dictionaries, this name must be the key of each entry (not a field inside).
  For the `build` array, it must be inside each module object (with `name` as the key).
  Local modules (files and folders in same directory as `cfbs.json`), must start with `./`, and end with `/` if it's a directory.
* `description` (string): Human readable description of what this module does.
* `tags` (array of strings): Mostly used for information / finding modules on [build.cfengine.com](https://build.cfengine.com).
  Some common examples include `supported`, `experimental`, `security`, `library`, `promise-type`.
  Try to look at what tags are in use already and fit your module, instead of inventing new ones.
* `repo` (string): Git repository URL where the module comes from.
  Note that by default, `cfbs` downloads tarballs from `build.cfengine.com`, not directly from other git repos.
  When your module is added to the index, we snapshot (download) your module and create this tarball.
  Required for modules in an index, or modules added from an index, not accepted otherwise.
* `url` (string): This field is added automatically when using `cfbs add <URL>` to directly add a module (not via index).
  It is required for non-local, non-index modules, and not accepted otherwise.
* `by` (string): Author information for display on [build.cfengine.com](https://build.cfengine.com), URL to GitHub profile.
* `version` (string): Version number of module used in `cfbs add`, `cfbs update`, as well as for display on the [build.cfengine.com](https://build.cfengine.com) website.
  Used in `index` and modules added from an index.
  Must be updated together with `commit`.
* `commit` (string): Commit hash used when we download and snapshot the version of a module.
  Used in `index` and modules added from an index.
  Must be updated together with `version`.
* `subdirectory` (string): Used if the module is inside a subdirectory of a repo.
  See for example [the `cfbs.json` of our modules repo](https://github.com/cfengine/modules/blob/master/cfbs.json).
  Not used for local modules (policy files or folders) - the name is the path to the module in this case.
  Optional.
* `dependencies` (array of strings): List of modules (by name) required to make this module work correctly.
  Dependencies are added automatically by `cfbs add` when attempting to add a module with dependencies.
  For modules in `index`, must refer to other modules in `index`.
  For modules in `provides`, must refer to other modules in `provides` or `index` (default one if not specified).
  For modules in `build`, must refer to other modules in `build`.
* `added_by` (string): Information about how the module was added to `build`.
  Name of the module which added it as a dependency, or `"cfbs add"` if the user added the module itself.
  Optional in `build` modules, not accepted in `provides` or `index`.
* `steps` (array of strings): The operations performed (in order) to build the module.
  See the section below on build steps.
* `input` (array of objects): Used for modules which accept input, allowing users of the module to change it's behavior by entering values in the interactive CLI, via a JSON file, via MP API or GUI.
  See the section below on [modules with input](#modules-with-input) for keys inside `input`, explanations of how this works and examples.
  Optional.

## Step folders

As a project is built, `cfbs` creates intermediate folders for each module, for example:

```
out/steps/001_masterfiles_5c7dc5b43088e259a94de4e5a9f17c0ce9781a0f/
```

These are copies of the module directories, where it's more "safe" to do things like run scripts or delete files.
`cfbs build` should not edit files in your project / git repository, only the generated / temporary files inside the `out/` directory.

## All available build steps

The build steps below manipulate the temporary files in the steps directories and write results to the output policy set, in `out/masterfiles`.
Unless otherwise noted, all steps are run inside the module's folder (`out/steps/...`) with sources / file paths relative to that folder, and targets / destinations mentioned below are relative to the output policy set (`out/masterfiles`, which in the end will be deployed as `/var/cfengine/masterfiles`). In `cfbs.json`'s `"steps"`, the build step name must be separated from the rest of the build step by a regular space.

* `copy <source> <destination>`
  * Copy a single file or a directory recursively.
* `json <source> <destination>`
  * Merge the source json file into the destination json file.
* `append <source> <destination>`
  * Append the source file to the end of destination file.
* `run <command ...>`
  * Run a shell command / script.
  * Usually used to prepare the module directory, delete files, etc. before a copy step.
  * Running scripts should be avoided if possible.
  * Script is run inside the module directory (the step folder).
  * Additional space separated arguments are passed as arguments.
* `delete <paths ...>`
  * Delete multiple files or paths recursively.
  * Files are deleted from the step folder.
  * Typically used before copying files to the output policy set with the `copy` step.
* `directory <source> <destination>`
  * Copy any .cf policy files recursively and add their paths to `def.json`'s `inputs`.
  * Enable `services_autorun_bundles` class in `def.json`.
  * Merge any `def.json` recursively into `out/masterfiles/def.json`.
  * Copy any other files with their existing directory structure to destination.
* `bundles <bundles ...>`
  * Ensure bundles are evaluated by adding them to the bundle sequence, using `def.json`.
    * Note that this relies on using the default policy set from the CFEngine team, the Masterfiles Policy Framework, commonly added as the first module (`masterfiles`).
    Specifically, this build step adds the bundles to the variable `default:def.control_common_bundlesequence_end`, which the MPF looks for.
  * Only manipulates the bundle sequence, to ensure policy files are copied and parsed, use other build steps, for example `copy` and `policy_files`.
* `policy_files <paths ...>`
  * Add policy (`.cf`) files to `inputs` key in `def.json`, ensuring they are parsed.
    * Note that this relies on using the default policy set from the CFEngine team, the Masterfiles Policy Framework, commonly added as the first module (`masterfiles`).
    * Only edits `def.json`, does not copy files. Should be used after a `copy` or `directory` build step.
    * Does not add any bundles to the bundle sequence, to ensure a bundle is evaluated, use the `bundles` build step or the autorun mechanism.
  * All paths are relative to `out/masterfiles`.
  * If any of the paths are directories (end with `/`), the folder(s) are recursively searched and all `.cf` files are added.
    * **Note:** Directories should be module-specific, otherwise this build step can find policy files from other modules (when they are mixed in the same directory).
* `input <source input.json> <target def.json>`
  * Converts the input data for a module into the augments format and merges it with the target augments file.
  * Source is relative to module directory and target is relative to `out/masterfiles`.
    * In most cases, the build step should be: `input ./input.json def.json`

When `def.json` is modified during a `json`, `input`, `directory`, `bundles`, or `policy_files` build step, the values of some lists of strings are deduplicated, when this does not make any difference in behavior.
These cases are:

1. Policy files and augments files in the `"inputs"` and `"augments"` top level keys.
2. `"tags"` inside variables in `"variables"` and classes in `"classes"`.
3. Class expressions for each class in `"classes"`.
   These are in the subkey `"class_expressions"` when the class is defined using an object, and if the class is defined using just a list, that list is the list of class expressions implicitly.

### A note on reproducibility and backwards compatibility

As mentioned in [the README](./README.md), our main focus when it comes to reproducibility and backwards compatibility of `cfbs` is the `cfbs build` command.
(This also extends to `cfbs download` since that is the first part of `cfbs build`).
Anyone who has a working CFEngine Build project, should expect it to keep working (keep building) after upgrading their hub or their version of cfbs.
Ideally, the resulting policy set tarball should be bit-by-bit identical (reproducible), including metadata, so that checksums are easy to compare.
We are not there yet, see this ticket for more progress in this area:

https://northerntech.atlassian.net/browse/CFE-4102

Conversely, for other commands, we might choose to make changes where we think it's a good idea (for example for the user experience, performance or security of the tool).
Some examples of where you might experience changes are:

* The commands which edit `cfbs.json`, or other files, might produce different JSON files in future versions.
  (`cfbs init`, `cfbs add`, etc.).
* We might add more strict validation, so `cfbs validate` and `cfbs status` could start giving warnings or errors after upgrading to a new version.
* The interactive prompts might be drastically changed to help the user experience and give more advanced options.
  Don't rely on the exact prompts, order of prompts, or output of `cfbs init`, `cfbs add`, etc.

## Examples

### New project

Starting in an empty folder you can create a new project with the `init` command:

```
cfbs init
```

Which creates a file like this:

```json
{
  "name": "Example",
  "description": "Example description",
  "type": "policy-set",
  "build": []
}
```

### Adding a module

Continuing from the previous project, we can add a module:

```
cfbs add mpf
```

Which results in:

```json
{
  "name": "Example",
  "description": "Example description",
  "type": "policy-set",
  "build": [
    {
      "name": "masterfiles",
      "description": "Official CFEngine Masterfiles Policy Framework (MPF)",
      "tags": ["official", "base", "supported"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "version": "0.1.1",
      "commit": "5c7dc5b43088e259a94de4e5a9f17c0ce9781a0f",
      "steps": [
        "run ./autogen.sh",
        "delete ./autogen.sh",
        "run ./cfbs/cleanup.sh",
        "delete ./cfbs/cleanup.sh",
        "copy ./ ./"
      ],
      "added_by": "cfbs add"
    }
  ]
}
```

## Alternate index

You can start a project with an alternate index:

```
cfbs init --index blah
```

```json
{
  "name": "Example",
  "description": "Example description",
  "type": "policy-set",
  "index": "blah",
  "build": []
}
```

`blah` can be a URL or a relative file path (inside project).

## Index file

The index file used by `cfbs` also follows the same format:

```json
{
  "name": "Official CFEngine Build Index (default)",
  "description": "File used by tooling and website to find modules",
  "type": "index",
  "index": {
    "masterfiles": {
      "description": "Official CFEngine Masterfiles Policy Framework (MPF)",
      "tags": ["official", "base", "supported"],
      "repo": "https://github.com/cfengine/masterfiles",
      "by": "https://github.com/cfengine",
      "version": "0.1.1",
      "commit": "5c7dc5b43088e259a94de4e5a9f17c0ce9781a0f",
      "steps": [
        "run ./autogen.sh",
        "delete ./autogen.sh",
        "run ./cfbs/cleanup.sh",
        "delete ./cfbs/cleanup.sh",
        "copy ./ ./"
      ]
    }
  }
}
```

(Only showing 1 module here, the real file has many more).

Note that it is reusing the `index` key, but this time with a dictionary (inline index).

## A separate repo which provides modules

If you put your modules in a repo and don't have them in the index (yet), you can use the `provides` key:

```json
{
  "name": "Example module in separate repo",
  "description": "Example description",
  "type": "module",
  "provides": {
    "example-module": {
      "description": "Just an example",
      "tags": ["local"],
      "dependencies": ["autorun"],
      "steps": ["copy ./test.cf services/autorun/test.cf"]
    }
  }
}
```

## Adding a module from repo URL

```
cfbs init && cfbs add https://github.com/cfengine/some-repo
```

```json
{
  "name": "Example",
  "description": "Example description",
  "type": "policy-set",
  "build": [
    {
      "name": "example-module",
      "description": "Just an example",
      "tags": ["local"],
      "url": "https://github.com/cfengine/some-repo",
      "commit": "be3bc015f6a19e945bb7a9fa0ed78c97e2cecf61",
      "dependencies": ["autorun"],
      "steps": ["copy ./test.cf services/autorun/test.cf"],
      "added_by": "cfbs add"
    }
  ]
}
```


## Modules with input

Some modules allow for users to add module input by responding to questions
expressed under the `"input"` attribute in `cfbs.json`. User input can be added
using the `cfbs input <module-name>` command, which stores responses in
`./<module-name>/input.json`. These responses are translated into augments which
will be added to `./out/masterfiles/def.json` during `cfbs build`.

### Create single file example

The `"input"` attribute takes a list of input definitions as illustrated below.

```json
{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "build": [
    {
      "name": "create-single-file",
      "description": "Create a single file.",
      "url": "https://github.com/cfengine/example-module.git",
      "commit": "d95774c8c59a2895c677624851ef4ad9d5e0d02d",
      "dependencies": ["autorun"],
      "added_by": "cfbs add",
      "steps": [
        "copy ./create-single-file.cf services/autorun/create-single-file.cf",
        "input ./input.json def.json"
      ],
      "input": [
        {
          "type": "string",
          "variable": "filename",
          "label": "Filename",
          "question": "What file should this module create?"
        }
      ]
    }
  ]
}
```

From the example above, we can see that the `"input"` list contains one input
definition. By running the command `cfbs input create-single-file`, the input
definition will be copied into `./create-single-file/input.json` along with the
user responses.

```
$ cfbs input create-single-file
Adding input for module 'create-single-file':
What file should this module create? /tmp/create-single-file.txt
$ cat ./create-single-file/input.json
[
  {
    "type": "string",
    "variable": "filename",
    "label": "Filename",
    "question": "What file should this module create?",
    "response": "/tmp/create-single-file.txt"
  }
]
```

By running `cfbs build`, augments will be generated from
`./create-single-file/input.json` and added to `./out/masterfiles/def.json`.
Note that this is dependant on the `"input ./input.json def.json"` build step in
`cfbs.json`.

```
$ cfbs build
--snip--
Build complete, ready to deploy 🐿
 -> Directory: out/masterfiles
 -> Tarball:   out/masterfiles.tgz
To install on this machine: sudo cfbs install
To deploy on remote hub(s): cf-remote deploy
$ cat ./out/masterfiles/def.json
{
  "classes": {
    "services_autorun": ["any"]
  },
  "variables": {
    "cfbs:create_single_file.filename": {
      "value": "/tmp/create-single-file.txt",
      "comment": "Added by 'cfbs input'"
    }
  }
}
```

From the example above we can see our beloved `filename`-variable along with a
class generated by the autorun dependency. Studying our variable closer, we can
see that a namespace, bundle, and a comment, were automatically assigned some
default values.  I.e. `cfbs`, the module name canonified, and `Added by 'cfbs
input'` respectivy.  These defaults can easily be overridden using the
`namespace`, `bundle`, and `comment` attributes in the variable definition. E.g.
the following variable definition;

```json
      "input": [
        {
          "type": "string",
          "namespace": "my_namespace",
          "bundle": "my_bundle",
          "variable": "filename",
          "comment": "Example comment.",
          "label": "Filename",
          "question": "What file should this module create?"
        }
      ]
```

would produce the following augment;

```json
{
  "variables": {
    "my_namespace:my_bundle.filename": {
      "value": "/tmp/create-single-file.txt",
      "comment": "Example comment."
    }
  }
}
```

### Create a single file with content example

A module that creates empty files is not too impressive on its own. Let us
instead try to extend our previous example by having the module also ask for
file contents.

```json
{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "build": [
    {
      "name": "create-single-file-with-content",
      "description": "Create a single file with content.",
      "url": "https://github.com/cfengine/example-module.git",
      "commit": "d95774c8c59a2895c677624851ef4ad9d5e0d02d",
      "dependencies": ["autorun"],
      "added_by": "cfbs add",
      "steps": [
        "copy ./create-single-file-with-content.cf services/autorun/create-single-file-with-content.cf",
        "input ./input.json def.json"
      ],
      "input": [
        {
          "type": "string",
          "variable": "filename",
          "label": "Filename",
          "question": "What file should this module create?"
        },
        {
          "type": "string",
          "variable": "content",
          "label": "Content",
          "question": "What content should this file have?"
        }
      ]
    }
  ]
}
```

As you can see from the example above, the extension would only require us to
add another variable to the input definition. Let's have a look at the results
from running `cfbs input` with our extension module.

```
$ cfbs input create-single-file-with-content
Adding input for module 'create-single-file-with-content':
What file should this module create? /tmp/create-single-file-with-content.txt
What content should this file have? Hello CFEngine!
$ cfbs build
--snip--
Build complete, ready to deploy 🐿
 -> Directory: out/masterfiles
 -> Tarball:   out/masterfiles.tgz
To install on this machine: sudo cfbs install
To deploy on remote hub(s): cf-remote deploy
$ cat ./out/masterfiles/def.json
{
  "classes": {
    "services_autorun": ["any"]
  },
  "variables": {
    "cfbs:create_single_file_with_content.filename": {
      "value": "/tmp/create-single-file-with.content.txt",
      "comment": "Added by 'cfbs input'"
    }
    "cfbs:create_single_file_with_content.content": {
      "value": "Hello CFEngine!",
      "comment": "Added by 'cfbs input'"
    }
  }
}
```

### Create multiple files example

Sometimes we would like a module to support taking an arbritary number of
inputs. This can be done using a variable definition of type list. Let's extend
our first example from creating a single to multiple files.

```json
{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "build": [
    {
      "name": "create-multiple-files",
      "description": "Create multiple files.",
      "url": "https://github.com/cfengine/example-module.git",
      "commit": "d95774c8c59a2895c677624851ef4ad9d5e0d02d",
      "dependencies": ["autorun"],
      "added_by": "cfbs add",
      "steps": [
        "copy ./create-multiple-files.cf services/autorun/create-multiple-files.cf",
        "input ./input.json def.json"
      ],
      "input": [
        {
          "type": "list",
          "variable": "files",
          "label": "Files",
          "subtype": {
            "type": "string",
            "label": "Filename",
            "question": "What file should this module create?"
          },
          "while": "Do you want to create another file?"
        }
      ]
    }
  ]
}
```

Running `cfbs input` with our module supporting multiple files, we can expect
the following interaction:

```
$ cfbs input create-multiple-files
Adding input for module 'create-multiple-files':
What file should this module create? /tmp/create-multiple-files-1.txt
Do you want to create another file? yes
What file should this module create? /tmp/create-multiple-files-2.txt
Do you want to create another file? no
```

The *_./create-multiple-files/input.json_* file would look similar to the
following JSON:

```json
[
  {
    "type": "list",
    "variable": "files",
    "label": "Files",
    "subtype": {
      "type": "string",
      "label": "Filename",
      "question": "What file should this module create?",
    },
    "while": "Do you want to create another file?",
    "response": [
      "/tmp/create-multiple-files-1.txt",
      "/tmp/create-multiple-files-2.txt"
    ]
  }
]
```

And if we build our project we can expect something similar to the following
output:

```
$ cfbs build
--snip--
Build complete, ready to deploy 🐿
 -> Directory: out/masterfiles
 -> Tarball:   out/masterfiles.tgz
To install on this machine: sudo cfbs install
To deploy on remote hub(s): cf-remote deploy
$ cat ./out/masterfiles/def.json
{
  "classes": {
    "services_autorun": ["any"]
  },
  "variables": {
    "cfbs:create_multiple_files.files": {
      "value": [
        "/tmp/create-multiple-files-1.txt",
        "/tmp/create-multiple-files-2.txt"
      ],
      "comment": "Added by 'cfbs input'"
    }
  }
}
```

### Create multiple files with content example

As a final example, let's see how we can build a module that takes an arbritary
number of filename and content pairs as input.

```json
{
  "name": "Example",
  "type": "policy-set",
  "description": "Example description",
  "build": [
    {
      "name": "create-multiple-files-with-content",
      "description": "Create multiple files with content.",
      "url": "https://github.com/cfengine/example-module.git",
      "commit": "d95774c8c59a2895c677624851eb4ad9d5e0d02d",
      "dependencies": ["autorun"],
      "added_by": "cfbs add",
      "steps": [
        "copy ./create-multiple-files-with-content.cf services/autorun/create-multiple-files-with-content.cf",
        "input ./input.json def.json"
      ],
      "input": [
        {
          "type": "list",
          "variable": "files",
          "label": "Files",
          "subtype": [
            {
              "key": "name",
              "type": "string",
              "label": "Name",
              "question": "What file should this module create?"
            },
            {
              "key": "content",
              "type": "string",
              "label": "Content",
              "question": "What content should this file have?"
            }
          ],
          "while": "Do you want to create another file?"
        }
      ]
    }
  ]
}
```

Just like before we add input, build and look at the result:

```
$ cfbs input create-multiple-files-with-content
Adding input for module 'create-multiple-files-with-content':
What file should this module create? /tmp/create-multiple-files-with-content-1.txt
What content should this file have? Hello CFEngine!
Do you want to create another file? yes
What file should this module create? /tmp/create-multiple-files-with-content-2.txt
What content should this file have? Bye CFEngine!
Do you want to create another file? no
$ cfbs build
--snip--
Build complete, ready to deploy 🐿
 -> Directory: out/masterfiles
 -> Tarball:   out/masterfiles.tgz
To install on this machine: sudo cfbs install
To deploy on remote hub(s): cf-remote deploy
$ cat ./out/masterfiles/def.json
{
  "classes": {
    "services_autorun": ["any"]
  },
  "variables": {
    "cfbs:create_multiple_files_with_content.file": {
      "value": [
        {
          "name": "/tmp/create-multiple-files-with.content-1.txt",
          "content": "Hello CFEngine!"
        },
        {
          "name": "/tmp/create-multiple-files-with.content-2.txt",
          "content": "Bye CFEngine!"
        }
      ]
      "comment": "Added by 'cfbs input'"
    }
  }
}
```
