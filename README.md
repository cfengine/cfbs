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
ln -s $PWD/cpm/__main__.py /usr/local/bin/cpm
```
(`chmod` and `ln` is just one way to do it, I might provide an install script at some point)
