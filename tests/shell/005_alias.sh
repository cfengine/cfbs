source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
run cfbs --non-interactive add groups

assert_output_contains "alias"
assert_output_contains "Added module"

test_finish
