source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles=no
assert_file_not_contains cfbs.json '"name": "masterfiles"'
cfbs status
assert_failure cfbs build

test_finish
