source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles=master
assert_file_contains cfbs.json '"name": "masterfiles"'
assert_file_contains cfbs.json '"url": "https://github.com/cfengine/masterfiles"'
cfbs build

test_finish
