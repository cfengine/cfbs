source "$(dirname "$0")/testlib.sh"
test_init
rm -rf example-module
cp -r ../shell/024_update_input_fail_bundle/example-module .
cp ../shell/024_update_input_fail_bundle/example-cfbs.json cfbs.json

# This used to be a test about cfbs update failing due to changing fields
# which cannot be automatically updated.
# We've now added more strict validation to cfbs update,
# so the test now fails "earlier", during validation of the JSON.
# Effectively, it now tests that cfbs update does validation, and fails on
# the missing namespace field.
run cfbs --loglevel=debug --non-interactive update
assert_output_contains 'The "namespace" field is required in module input elements'

test_finish
