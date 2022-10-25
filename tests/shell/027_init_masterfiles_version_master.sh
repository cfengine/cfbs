set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles=master
grep '"name": "masterfiles"' cfbs.json
grep '"url": "https://github.com/cfengine/masterfiles"' cfbs.json
cfbs build
