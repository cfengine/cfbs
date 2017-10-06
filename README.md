# Testing some stuff

```
curl -L https://github.com/nickanderson/cfengine-cis/archive/master.zip -o /tmp/master.zip
sudo unzip /tmp/master.zip -d /
sudo mv /.setup-bash-master/ /.setup-bash
sudo rm -f /tmp/master.zip

curl -L https://github.com/nickanderson/cfengine-cis/archive/master.zip -o /tmp/master.zip && sudo unzip /tmp/master.zip -d /tmp/ && sudo make -C cfengine-cis-master install
```
