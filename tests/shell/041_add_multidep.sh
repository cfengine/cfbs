source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init

run cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo

# All four modules were correctly added
assert_output_contains "Added module: test-library-parsed-local-users"
assert_output_contains "Added module: test-library-parsed-etc-group"
assert_output_contains "Added module: test-inventory-local-groups"
assert_output_contains "Added module: test-inventory-local-users"

# Adding modules together with their dependencies should not display skipping messages (CFE-3841):
assert_output_not_contains "Skipping already added"

test_finish
