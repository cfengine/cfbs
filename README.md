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

Requires Python 3.6 or newer and `pip`.

```
pip install cfbs
```

(or `sudo pip3 install cfbs` or whatever works with Python 3 on your system).

### Dependencies

`cfbs` is implemented in Python and has some dependencies on python version and libraries:

* Python 3.6 or newer
* `cf-remote` and its dependencies
  * Installed automatically by `pip`

Additionally, some command line tools are required (not installed by pip):

* `git` CLI installed and in PATH
* `prettier` CLI installed and in PATH
  * **Note:** Must be installed manually, for example using `npm`.

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

### Deploy your policy set to a remote hub

```
cf-remote deploy -H hub out/masterfiles.tgz
```

(Replace `hub` with the cf-remote group name or IP of your hub).
