set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/018_update_input_one_variable/example-module .
cp ../shell/018_update_input_one_variable/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
grep '"label": "Filepath"' example-module/input.json
grep '"question": "Path of file?"' example-module/input.json
grep '"response": "/tmp/create-single-file.txt"' example-module/input.json
grep '"default": "/tmp/test.txt"' example-module/input.json
