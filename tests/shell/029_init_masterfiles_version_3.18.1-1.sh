source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles=3.18.1-1
assert_file_contains cfbs.json '"name": "masterfiles"'
assert_file_contains cfbs.json '"version": "3.18.1-1"'
assert_file_contains cfbs.json '"commit": "b6e9eacc65c797f4c2b4a59056293636c320d0c9"'
cfbs build
cfbs --non-interactive update
assert_file_not_contains cfbs.json '"version": "3.18.1-1"'
assert_file_not_contains cfbs.json '"commit": "b6e9eacc65c797f4c2b4a59056293636c320d0c9"'

test_finish
