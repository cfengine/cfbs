set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/

# Set up the project we will build:
cp ../shell/043_replace_version/example-cfbs.json ./cfbs.json
cfbs validate

mkdir -p subdir
cp ../shell/043_replace_version/subdir/example.py ./subdir/example.py

# Before building, version number is 0.0.0:
grep 'print("Version: 0.0.0")' ./subdir/example.py
! grep 'print("Version: 1.2.3")' ./subdir/example.py

cfbs build

# After building, input and output should be different:
! diff ./subdir/example.py ./out/masterfiles/services/cfbs/subdir/example.py

# Check that version number is correct in output:
grep 'print("Version: 1.2.3")' ./out/masterfiles/services/cfbs/subdir/example.py
! grep 'print("Version: 0.0.0")' ./out/masterfiles/services/cfbs/subdir/example.py

# Also check that the input was not modified:
grep 'print("Version: 0.0.0")' ./subdir/example.py
! grep 'print("Version: 1.2.3")' ./subdir/example.py
