set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles=3.18.1-1
grep '"name": "masterfiles"' cfbs.json
grep '"version": "3.18.1-1"' cfbs.json
cfbs build
