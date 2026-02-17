source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/022_update_input_fail_variable/example-module .
cp ../shell/022_update_input_fail_variable/example-cfbs.json cfbs.json
cfbs validate

run cfbs --loglevel=debug --non-interactive update
assert_output_contains "Failed to update input data for module 'example-module'"

test_finish
