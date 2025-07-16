set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/020_update_input_list/example-module .
cp ../shell/020_update_input_list/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
grep '"label": "Filepaths"' example-module/input.json
grep '"while": "Create another file?"' example-module/input.json
grep '"label": "Path"' example-module/input.json
grep '"question": "Path of file?"' example-module/input.json
grep '"default": "/tmp/test.txt"' example-module/input.json
grep '"response":' example-module/input.json
grep '"/tmp/create-multiple-files-1.txt"' example-module/input.json
grep '"/tmp/create-multiple-files-2.txt"' example-module/input.json
