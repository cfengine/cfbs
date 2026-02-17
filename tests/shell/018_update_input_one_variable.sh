source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/018_update_input_one_variable/example-module .
cp ../shell/018_update_input_one_variable/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
assert_file_contains example-module/input.json '"label": "Filepath"'
assert_file_contains example-module/input.json '"question": "Path of file?"'
assert_file_contains example-module/input.json '"response": "/tmp/create-single-file.txt"'
assert_file_contains example-module/input.json '"default": "/tmp/test.txt"'

test_finish
