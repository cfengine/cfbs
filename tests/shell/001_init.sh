source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
assert_file_exists cfbs.json

test_finish
