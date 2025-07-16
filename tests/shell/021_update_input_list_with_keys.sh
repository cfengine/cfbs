set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git
rm -rf example-module
cp -r ../shell/021_update_input_list_with_keys/example-module .
cp ../shell/021_update_input_list_with_keys/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
grep '"while": "Create another file?"' example-module/input.json
grep '"label": "Path"' example-module/input.json
grep '"question": "Path of file?"' example-module/input.json
grep '"default": "/tmp/test.txt"' example-module/input.json
grep '"label": "Contents"' example-module/input.json
grep '"question": "File contents?"' example-module/input.json
grep '"default": "Hello CFEngine!"' example-module/input.json
grep '"response":' example-module/input.json
grep '{ "name": "/tmp/test-1.txt", "content": "Hello CFEngine!" }' example-module/input.json
grep '{ "name": "/tmp/test-2.txt", "content": "Bye CFEngine!" }' example-module/input.json
