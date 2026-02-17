source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
run_expect_failure cfbs --non-interactive add bollocks
assert_output_contains "Error: Module 'bollocks' does not exist"

test_finish
