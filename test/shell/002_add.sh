set -e
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

cfbs init
cfbs add masterfiles
grep masterfiles cfbs.json
