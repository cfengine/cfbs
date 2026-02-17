source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add groups@0.1.2 --non-interactive
assert_file_contains cfbs.json '"version": "0.1.2"'
assert_file_contains cfbs.json '"commit": "087a2fd81e1bbaf241dfa7bf39013efd9d8d348f"'
cfbs --non-interactive remove promise-type-groups --non-interactive

test_finish
