source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles=3.18.2
assert_file_contains cfbs.json '"name": "masterfiles"'
assert_file_contains cfbs.json '"version": "3.18.2"'
assert_file_contains cfbs.json '"commit": "a87b7fea6f7a88808b327730a4ba784a3dc664eb"'
cfbs build

test_finish
