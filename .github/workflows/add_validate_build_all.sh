#!/usr/bin/env

# Requires / expects cfbs to already be installed
# Run from project root (will look for ./cfbs.json)
# in current working directory

set -e
set -x

rm -rf ./tmp/
mkdir -p ./tmp/

# This script is written to also work in for example cfengine/cfbs
# where we'd need to downooad cfbs.json.
if [ ! -f ./cfbs.json ] ; then
    echo "No cfbs.json found in current working directory, downloading from GitHub"
    curl -L https://raw.githubusercontent.com/cfengine/build-index/refs/heads/master/cfbs.json -o ./tmp/cfbs.json
else
    cp ./cfbs.json ./tmp/cfbs.json
fi

cd ./tmp/

# Move the index to another filename
mv cfbs.json index.json

# Initialize cfbs project
cfbs --non-interactive --index ./index.json init --masterfiles=no

# Add masterfiles
cfbs --non-interactive add masterfiles

# Validate the minimal project
cfbs validate

# Add all modules
cfbs search --index ./index.json | \
awk '{print $1}' | \
xargs -n1 cfbs --index ./index.json add

# Validate all modules
cfbs validate

# Build
cfbs build --ignore-versions-json

# Status
cfbs status

# Here we use root for everything to avoid permissions problems in policy that accesses files
# TODO: Enable later
#- name: Validate built policy
#  run: |
#    sudo pip3 install cfbs
#    wget https://s3.amazonaws.com/cfengine.packages/quick-install-cfengine-enterprise.sh  && sudo bash ./quick-install-cfengine-enterprise.sh agent
#    sudo cfbs install
#    # fake a bootstrap, lib-fim module expects stdlib to be in inputs with $(sys.libdir)
#    sudo cp -r /var/cfengine/masterfiles/lib /var/cfengine/inputs
#    sudo cf-promises -f /var/cfengine/masterfiles/promises.cf
#    sudo cf-promises -vf /var/cfengine/masterfiles/update.cf
