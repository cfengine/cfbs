source "$(dirname "$0")/testlib.sh"
test_init

# Set up the project we will build:
cp ../shell/043_replace_version/example-cfbs.json ./cfbs.json
cfbs validate

mkdir -p subdir
cp ../shell/043_replace_version/subdir/example.py ./subdir/example.py

# Before building, version number is 0.0.0:
assert_file_contains ./subdir/example.py 'print("Version: 0.0.0")'
assert_file_not_contains ./subdir/example.py 'print("Version: 1.2.3")'

cfbs build

# After building, input and output should be different:
assert_no_diff ./subdir/example.py ./out/masterfiles/services/cfbs/subdir/example.py

# Check that version number is correct in output:
assert_file_contains ./out/masterfiles/services/cfbs/subdir/example.py 'print("Version: 1.2.3")'
assert_file_not_contains ./out/masterfiles/services/cfbs/subdir/example.py 'print("Version: 0.0.0")'

# Also check that the input was not modified:
assert_file_contains ./subdir/example.py 'print("Version: 0.0.0")'
assert_file_not_contains ./subdir/example.py 'print("Version: 1.2.3")'

test_finish
