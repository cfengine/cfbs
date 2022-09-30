set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp ../shell/025_add_input_remove/example-cfbs.json cfbs.json

cfbs --non-interactive add example-module
cfbs --non-interactive input example-module
grep '"response": "/tmp/testfile.txt"' ./example-module/input.json
cfbs --non-interactive remove example-module
