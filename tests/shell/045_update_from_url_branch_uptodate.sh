source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles no
cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo/@update-test-branch test-library-parsed-local-users

# check that cfbs.json contains the right commit hash (ideally for testing, different than the default branch's commit hash):
assert_file_contains cfbs.json '"commit": "2152eb5a39fbf9b051105b400639b436bd53ab87"'
# check that branch key is correctly set:
assert_file_contains cfbs.json '"branch": "update-test-branch"'

cfbs update test-library-parsed-local-users | grep "Module 'test-library-parsed-local-users' already up to date"

test_finish
