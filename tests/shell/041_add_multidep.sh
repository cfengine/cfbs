set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init

cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo > output.log 2>&1

# All four modules were correctly added
grep -F "Added module: test-library-parsed-local-users" ./output.log
grep -F "Added module: test-library-parsed-etc-group" ./output.log
grep -F "Added module: test-inventory-local-groups" ./output.log
grep -F "Added module: test-inventory-local-users" ./output.log

# Adding modules together with their dependencies should not display skipping messages (CFE-3841):
! ( grep -F "Skipping already added" ./output.log )

