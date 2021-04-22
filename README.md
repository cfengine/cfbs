# Unofficial CFEngine Build System

The CFEngine Build System (cfbs) comes with **no warranty** and is **not supported**.
This is a work in progress, everything will change.
Use at your own risk!

## CFEngine Build System Repositories

* [cfbs](https://github.com/olehermanse/cfbs) - Command line client
* [cfbs-index](https://github.com/olehermanse/cfbs-index) - Index of modules
* [cfbs-modules](https://github.com/olehermanse/cfbs-modules) - Some modules / examples of modules
* [cfbs-web](https://github.com/olehermanse/cfbs-web) - Website
* [cfbs-example](https://github.com/olehermanse/cfbs-example) - Example project using cfbs

## Installation

### One-liner
This will install cfbs to a subfolder in `cwd` (`./cfbs`):
```
curl -L -s bit.ly/cfbsinstall | bash
```
The install script runs the commands listed below (including symlink!).

### Download
Navigate to where you want to install cfbs (it is self contained), then use git to download:
```
git clone https://github.com/olehermanse/cfbs.git
cd ./cfbs
pip3 install -r requirements.txt
chmod a+x ./cfbs/__main__.py
```

### Symlink

#### Mac OS X
```
ln -s $PWD/cfbs/__main__.py /usr/local/bin/cfbs
```

#### Linux (CentOS)
```
ln -s $PWD/cfbs/__main__.py /usr/bin/cfbs
```

## Usage

After you have imported `def.json` (or not) do not edit it directly.
Multiple `cfbs` packges/installers will overwrite the `masterfiles/def.json` file.
Instead, put your custom things in `<cfbs repo dir>/user/def.json`.
This file will be merged with packages' `def.json` files, before overwriting `masterfiles/def.json`.

### (WIP!) Configuration
cfbs will run an interactive configuration the first time it is invoked.
Alternately, you can redo the config step:
```
$ cfbs config
```
This will prompt you for paths to cfengine/masterfiles locations.
It will also ask you to import your existing `def.json` file.
Finally it will ask if you want `cfbs` to automatically install apply changes to the system, when you run `cfbs install`.
It is recommended that you answer yes to both these questions, for ease of use.
Beware that this is an unfinished project - do not use it on mission critical machines.

### List installed packages

```
$ cfbs list
```

### Search for downloadable packages

```
$ cfbs search [query]
```

### Download/Install package
```
$ cfbs install <package name | package alias>
```
(If `auto_apply` is not enabled, it will only be downloaded, no installers will be run)

### Apply package
Only needed if `auto_apply` is disabled.
This is used to explicitly run installers and apply changes to cfengine/masterfiles folders.
```
$ cfbs install <package name | package alias>
$ cfbs apply <package name | package alias>
```
