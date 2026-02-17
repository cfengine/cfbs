source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init

# Manually adding a dependency of a module then manually adding that module should not update the latter's `"added_by"` field in `cfbs.json`

cfbs --non-interactive add powershell-execution-policy
assert_file_matches cfbs.json '"added_by".*"cfbs add"'

cfbs --non-interactive add package-method-winget
assert_file_not_contains cfbs.json '"added_by": "package-method-winget"'

test_finish
