set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles no
cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo/@update-test-branch test-library-parsed-local-users

# check that cfbs.json contains the right commit hash (ideally for testing, different than the default branch's commit hash):
grep '"commit": "2152eb5a39fbf9b051105b400639b436bd53ab87"' cfbs.json
# check that branch key is correctly set:
grep '"branch": "update-test-branch"' cfbs.json

cfbs update test-library-parsed-local-users | grep "Module 'test-library-parsed-local-users' already up to date"
