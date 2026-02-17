source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add promise-type-git
assert_file_contains cfbs.json '"name": "library-for-promise-types-in-python"'
assert_file_contains cfbs.json '"name": "promise-type-git"'
cfbs --non-interactive remove promise-type-git --non-interactive
assert_file_not_contains cfbs.json '"name": "library-for-promise-types-in-python"'
assert_file_not_contains cfbs.json '"name": "promise-type-git"'

# Check that clean does nothing:
cat cfbs.json > before.json
cfbs --non-interactive clean
assert_diff cfbs.json before.json

test_finish
