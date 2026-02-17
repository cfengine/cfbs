source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/020_update_input_list/example-module .
cp ../shell/020_update_input_list/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
assert_file_contains example-module/input.json '"label": "Filepaths"'
assert_file_contains example-module/input.json '"while": "Create another file?"'
assert_file_contains example-module/input.json '"label": "Path"'
assert_file_contains example-module/input.json '"question": "Path of file?"'
assert_file_contains example-module/input.json '"default": "/tmp/test.txt"'
assert_file_contains example-module/input.json '"response":'
assert_file_contains example-module/input.json '"/tmp/create-multiple-files-1.txt"'
assert_file_contains example-module/input.json '"/tmp/create-multiple-files-2.txt"'

test_finish
