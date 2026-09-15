set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init
grep '"name": "masterfiles"' cfbs.json
cfbs --non-interactive remove masterfiles --non-interactive
if grep '"name": "masterfiles"' cfbs.json; then exit 1; fi
