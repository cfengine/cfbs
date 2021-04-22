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

## Usage

Here are the basic commands to set up a repo, add dependencies, build and deploy.

### Initialize a new repo (Not implemented yet)

```
cfbs init
```

### List or search available packages (Not implemented yet)

```
cfbs search
```

Or more specific:

```
cfbs search masterfiles
```

(`masterfiles` is the name of a module and can be replaced with whatever you are looking for).

### Add a module (Not implemented yet)

```
cfbs add masterfiles
```

### Build your policy set (Not implemented yet)

```
cfbs build
```

### Deploy your policy set (Not implemented yet)

```
cfbs deploy /var/cfengine/masterfiles
```
