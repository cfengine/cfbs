source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init --masterfiles no
cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo/@update-test-branch test-library-parsed-local-users

cp ../shell/046_update_from_url_branch/cfbs.json .

cfbs update test-library-parsed-local-users | grep "Updated module 'test-library-parsed-local-users' from url"
# check that the commit hash changed:
assert_file_contains cfbs.json '"commit": "2152eb5a39fbf9b051105b400639b436bd53ab87"'

test_finish
