source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/021_update_input_list_with_keys/example-module .
cp ../shell/021_update_input_list_with_keys/example-cfbs.json cfbs.json
cfbs validate

cfbs --loglevel=debug --non-interactive update
assert_file_contains example-module/input.json '"while": "Create another file?"'
assert_file_contains example-module/input.json '"label": "Path"'
assert_file_contains example-module/input.json '"question": "Path of file?"'
assert_file_contains example-module/input.json '"default": "/tmp/test.txt"'
assert_file_contains example-module/input.json '"label": "Contents"'
assert_file_contains example-module/input.json '"question": "File contents?"'
assert_file_contains example-module/input.json '"default": "Hello CFEngine!"'
assert_file_contains example-module/input.json '"response":'
assert_file_contains example-module/input.json '{ "name": "/tmp/test-1.txt", "content": "Hello CFEngine!" }'
assert_file_contains example-module/input.json '{ "name": "/tmp/test-2.txt", "content": "Bye CFEngine!" }'

test_finish
