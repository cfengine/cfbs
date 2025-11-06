set -e
set -x
cd tests/
mkdir -p ./tmp/
cd ./tmp/
touch cfbs.json && rm cfbs.json
rm -rf .git

cfbs --non-interactive init --masterfiles no
cfbs --non-interactive add https://github.com/cfengine/test-cfbs-static-repo/@update-test-branch test-library-parsed-local-users

cp ../shell/046_update_from_url_branch/cfbs.json .

cfbs update test-library-parsed-local-users | grep "Updated module 'test-library-parsed-local-users' from url"
# check that the commit hash changed:
grep '"commit": "2152eb5a39fbf9b051105b400639b436bd53ab87"' cfbs.json
