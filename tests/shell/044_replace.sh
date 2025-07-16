set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/

# Set up the project we will build:
cp ../shell/044_replace/example-cfbs.json ./cfbs.json
cfbs validate

mkdir -p subdir
cp ../shell/044_replace/subdir/example.py ./subdir/example.py
cp ../shell/044_replace/subdir/example.expected.py ./subdir/example.expected.py

cfbs build

ls out/masterfiles/services/cfbs/subdir/example.py

# Replace should have changed it:
! diff ./subdir/example.py out/masterfiles/services/cfbs/subdir/example.py > /dev/null

# This is the expected content:
diff ./subdir/example.expected.py out/masterfiles/services/cfbs/subdir/example.py
