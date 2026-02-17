source "$(dirname "$0")/testlib.sh"
skip_unless_unsafe
test_init
rm -rf ~/.cfagent/inputs/

cfbs --non-interactive init
cfbs --non-interactive add autorun
cfbs install

assert_file_exists ~/.cfagent/inputs/def.json
rm -rf ~/.cfagent/inputs/

test_finish
