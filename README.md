# Unofficial CFEngine Package Manager

Copyright Northern.tech AS.

## Installation

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
