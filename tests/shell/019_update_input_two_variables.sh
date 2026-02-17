source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/019_update_input_two_variables/example-module .
cp ../shell/019_update_input_two_variables/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
assert_file_contains example-module/input.json '"label": "Path"'
assert_file_contains example-module/input.json '"question": "Path of file?"'
assert_file_contains example-module/input.json '"default": "/tmp/test.txt"'
assert_file_contains example-module/input.json '"label": "Contents"'
assert_file_contains example-module/input.json '"question": "File contents?"'
assert_file_contains example-module/input.json '"default": "Hello CFEngine!"'
assert_file_contains example-module/input.json '"response": "/tmp/create-single-file-with-content.txt"'

test_finish
