source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp ../shell/025_add_input_remove/example-cfbs.json cfbs.json

cfbs --non-interactive add example-module
cfbs --non-interactive input example-module
assert_file_contains ./example-module/input.json '"response": "/tmp/testfile.txt"'
cfbs --non-interactive remove example-module

test_finish
