#!/usr/bin/env bash
git clone https://github.com/olehermanse/cpm.git
cd ./cpm || exit 1
pip3 install -r requirements.txt
chmod a+x ./cpm/__main__.py
ln -s $PWD/cpm/__main__.py /usr/local/bin/cpm
ln -s $PWD/cpm/__main__.py /usr/bin/cpm
