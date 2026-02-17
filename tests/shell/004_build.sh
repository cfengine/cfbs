source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs --non-interactive add autorun
cfbs --non-interactive add systemd
cfbs --non-interactive add git
cfbs --non-interactive add ansible
cfbs build

assert_file_exists out/

test_finish
