source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
assert_file_contains cfbs.json '"name": "masterfiles"'
cfbs --non-interactive remove masterfiles --non-interactive
assert_file_not_contains cfbs.json '"name": "masterfiles"'

test_finish
