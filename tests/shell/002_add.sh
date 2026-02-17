source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add autorun
assert_file_contains cfbs.json masterfiles

test_finish
