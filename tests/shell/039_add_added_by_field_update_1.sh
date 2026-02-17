source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init

# Ensure adding a module during initialization is treated as adding manually
assert_file_matches cfbs.json '"added_by".*"cfbs init"'
# TODO: the case of custom non-masterfiles module(s) should also be tested

# Manually adding a module then manually adding its dependency should update the latter's `"added_by"` field in `cfbs.json`

cfbs --non-interactive add package-method-winget
assert_file_matches cfbs.json '"added_by".*"package-method-winget"'
assert_count 1 cfbs.json '"cfbs add"'

cfbs --non-interactive add powershell-execution-policy
assert_file_not_contains cfbs.json '"added_by": "package-method-winget"'
assert_count 2 cfbs.json '"cfbs add"'

test_finish
