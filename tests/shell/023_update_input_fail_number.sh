set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/023_update_input_fail_number/example-module .
cp ../shell/023_update_input_fail_number/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update > output.log 2>&1
grep "Failed to update input data for module 'example-module'" ./output.log
