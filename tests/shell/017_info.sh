source "$(dirname "$0")/testlib.sh"
test_init

run cfbs info masterfiles
assert_output_contains "MPF"

cfbs --non-interactive init

run cfbs info autorun
assert_output_contains "Not added"

cfbs --non-interactive add autorun
run cfbs info autorun
assert_output_contains "Added"

test_finish
