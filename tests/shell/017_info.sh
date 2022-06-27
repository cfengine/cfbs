set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs info masterfiles
cfbs info masterfiles | grep "MPF"

cfbs --non-interactive init

cfbs info autorun
cfbs info autorun | grep "Not added"

cfbs --non-interactive add autorun
cfbs info autorun
cfbs info autorun | grep "Added"
