set -e
set -x
cd test
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json

curl https://raw.githubusercontent.com/cfengine/build-index/master/cfbs.json -o cfbs.json
cfbs validate --index ./cfbs.json
