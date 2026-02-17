source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init

run cfbs search
assert_output_contains "python"

run cfbs search mpf
assert_output_not_contains "python"
assert_output_contains "masterfiles"

run cfbs search masterfiles
assert_output_contains "masterfiles"

test_finish
