set -e
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
cfbs init
ls cfbs.json
