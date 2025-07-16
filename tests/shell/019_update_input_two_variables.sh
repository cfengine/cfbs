set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/019_update_input_two_variables/example-module .
cp ../shell/019_update_input_two_variables/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
grep '"label": "Path"' example-module/input.json
grep '"question": "Path of file?"' example-module/input.json
grep '"default": "/tmp/test.txt"' example-module/input.json
grep '"label": "Contents"' example-module/input.json
grep '"question": "File contents?"' example-module/input.json
grep '"default": "Hello CFEngine!"' example-module/input.json
grep '"response": "/tmp/create-single-file-with-content.txt"' example-module/input.json
