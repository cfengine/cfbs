source "$(dirname "$0")/testlib.sh"
test_init

cfbs --non-interactive init
cfbs download

assert_file_exists ~/.cfengine/cfbs/downloads/*

test_finish
