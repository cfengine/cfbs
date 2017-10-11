# Unofficial CFEngine Package Manager

Copyright Northern.tech AS.

CFEngine Package Manager (cpm) comes with **no warranty** and is **not supported**.
Use at your own risk!

## Installation

### One-liner
This will install cpm to a subfolder in `cwd` (`./cpm`):
```
bash <(curl -L -s bit.ly/cpminstall)
```
The install script runs the commands listed below (including symlink!).

### Download
Navigate to where you want to install cpm (it is self contained), then use git to download:
```
git clone https://github.com/olehermanse/cpm.git
cd ./cpm
pip3 install -r requirements.txt
chmod a+x ./cpm/__main__.py
```

### Symlink

#### Mac OS X
```
ln -s $PWD/cpm/__main__.py /usr/local/bin/cpm
```

#### Linux (CentOS)
```
ln -s $PWD/cpm/__main__.py /usr/bin/cpm
```

## Usage

After you have imported `def.json` (or not) do not edit it directly.
Multiple `cpm` packges/installers will overwrite the `masterfiles/def.json` file.
Instead, put your custom things in `<cpm repo dir>/user/def.json`.
This file will be merged with packages' `def.json` files, before overwriting `masterfiles/def.json`.

### (WIP!) Configuration
cpm will run an interactive configuration the first time it is invoked.
Alternately, you can redo the config step:
```
$ cpm config
```
This will prompt you for paths to cfengine/masterfiles locations.
It will also ask you to import your existing `def.json` file.
Finally it will ask if you want `cpm` to automatically install apply changes to the system, when you run `cpm install`.
It is recommended that you answer yes to both these questions, for ease of use.
Beware that this is an unfinished project - do not use it on mission critical machines.

### List installed packages

```
$ cpm list
```

### Search for downloadable packages

```
$ cpm search [query]
```

### Download/Install package
```
$ cpm install <package name | package alias>
```
(If `auto_apply` is not enabled, it will only be downloaded, no installers will be run)

### Apply package
Only needed if `auto_apply` is disabled.
This is used to explicitly run installers and apply changes to cfengine/masterfiles folders.
```
$ cpm install <package name | package alias>
$ cpm apply <package name | package alias>
```
