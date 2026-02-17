source "$(dirname "$0")/testlib.sh"
test_init

# Set up the project we will build:
cp ../shell/044_replace/example-cfbs.json ./cfbs.json
cfbs validate

mkdir -p subdir
cp ../shell/044_replace/subdir/example.py ./subdir/example.py
cp ../shell/044_replace/subdir/example.expected.py ./subdir/example.expected.py

cfbs build

assert_file_exists out/masterfiles/services/cfbs/subdir/example.py

# Replace should have changed it:
assert_no_diff ./subdir/example.py out/masterfiles/services/cfbs/subdir/example.py

# This is the expected content:
assert_diff ./subdir/example.expected.py out/masterfiles/services/cfbs/subdir/example.py

test_finish
