set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/022_update_input_fail_variable/example-module .
cp ../shell/022_update_input_fail_variable/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update > output.log 2>&1
grep "Failed to update input data for module 'example-module'" ./output.log
