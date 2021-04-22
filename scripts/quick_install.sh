#!/usr/bin/env bash
git clone https://github.com/olehermanse/cfbs.git
cd ./cfbs || exit 1
pip3 install -r requirements.txt
chmod a+x ./cfbs/__main__.py
ln -s $PWD/cfbs/__main__.py /usr/local/bin/cfbs
ln -s $PWD/cfbs/__main__.py /usr/bin/cfbs
