set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

curl https://raw.githubusercontent.com/cfengine/build-index/master/cfbs.json -o cfbs.json
cfbs validate --index ./cfbs.json
