# Unofficial CFEngine Package Manager

Copyright Northern.tech AS.

## Installation

### Download
```
cit clone git@github.com:olehermanse/cpm.git
```
Clone it wherever you like, it is completely self contained, and can update `/var/cfengine/` from anywhere.

### Dependencies
```
pip3 install -r requirements.txt
```

### Symlink
```
ln -s $PWD/cpm/__main__.py /usr/local/bin/cpm
```

### Curl experiments

```
curl -L https://github.com/nickanderson/cfengine-cis/archive/master.zip -o /tmp/master.zip
sudo unzip /tmp/master.zip -d /
sudo mv /.setup-bash-master/ /.setup-bash
sudo rm -f /tmp/master.zip

curl -L https://github.com/nickanderson/cfengine-cis/archive/master.zip -o /tmp/master.zip && sudo unzip /tmp/master.zip -d /tmp/ && sudo make -C cfengine-cis-master install
```
